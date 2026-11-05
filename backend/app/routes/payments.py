"""Routes cho Thanh toán, Gói cước, Đơn hàng, Webhook và Biên lai PDF."""
import json
import logging
from datetime import UTC, datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.receipt import generate_receipt_pdf
from app.db import get_db
from app.dependencies import get_current_active_user, get_current_admin_user
from app.models.payment import OrderStatus
from app.models.user import User
from app.schemas.payment import (
    CardPaymentRequest,
    CardPaymentResult,
    CouponValidateRequest,
    CouponValidateResponse,
    OrderCreateRequest,
    OrderListResponse,
    OrderOut,
    PricingPlanCreate,
    PricingPlanOut,
    PricingPlanUpdate,
    ResendOtpResponse,
    SandboxPaymentSimulateRequest,
    VerifyOtpRequest,
    WebhookPayOSPayload,
)
from app.services.payment_service import PaymentService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/payments", tags=["Thanh toán & Gói cước"])


# --- Helper mapping Order to OrderOut ---

def _format_order(order) -> OrderOut:
    plan_name = order.plan.name if order.plan else None
    plan_code = order.plan.code if order.plan else None
    return OrderOut(
        id=order.id,
        order_code=order.order_code,
        order_number=order.order_number,
        user_id=order.user_id,
        plan_id=order.plan_id,
        plan_name=plan_name,
        plan_code=plan_code,
        original_amount=order.original_amount,
        discount_amount=order.discount_amount,
        final_amount=order.final_amount,
        credits_to_add=order.credits_to_add,
        payment_method=order.payment_method,
        status=order.status,
        qr_url=order.qr_url,
        checkout_url=order.checkout_url,
        transfer_content=order.transfer_content,
        bank_name=order.bank_name,
        bank_account_no=order.bank_account_no,
        bank_account_name=order.bank_account_name,
        expires_at=order.expires_at,
        paid_at=order.paid_at,
        created_at=order.created_at,
    )


# --- 1. Gói cước (Pricing Plans) ---

@router.get("/plans", response_model=List[PricingPlanOut], summary="Danh sách các gói cước đang mở")
async def get_pricing_plans(db: AsyncSession = Depends(get_db)):
    """Lấy danh sách các gói nạp credit và gói tháng đang hoạt động."""
    await PaymentService.seed_defaults_if_empty(db)
    plans = await PaymentService.list_plans(db, only_active=True)
    return plans


@router.post("/admin/plans", response_model=PricingPlanOut, summary="[Admin] Tạo gói dịch vụ mới")
async def admin_create_plan(
    payload: PricingPlanCreate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin tạo thêm gói cước mới."""
    plan = await PaymentService.create_plan(db, payload.model_dump())
    return plan


@router.put("/admin/plans/{plan_id}", response_model=PricingPlanOut, summary="[Admin] Chỉnh sửa gói dịch vụ")
async def admin_update_plan(
    plan_id: int,
    payload: PricingPlanUpdate,
    current_admin: User = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin cập nhật giá, quyền lợi, tính năng của gói dịch vụ."""
    plan = await PaymentService.update_plan(db, plan_id, payload.model_dump(exclude_unset=True))
    return plan


# --- 2. Mã giảm giá (Coupons) ---

@router.post("/coupons/validate", response_model=CouponValidateResponse, summary="Kiểm tra mã giảm giá")
async def validate_coupon(
    payload: CouponValidateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Kiểm tra và tính toán giảm giá trước khi thanh toán."""
    coupon, discount, msg = await PaymentService.validate_coupon(
        db, payload.code, payload.order_amount
    )
    if not coupon:
        return CouponValidateResponse(
            valid=False,
            code=payload.code,
            discount_type="none",
            discount_value=0,
            discount_amount=0,
            final_amount=payload.order_amount,
            message=msg,
        )

    final = max(0, payload.order_amount - discount)
    return CouponValidateResponse(
        valid=True,
        code=coupon.code,
        discount_type=coupon.discount_type,
        discount_value=coupon.discount_value,
        discount_amount=discount,
        final_amount=final,
        message=msg,
    )


# --- 3. Đơn hàng (Orders) ---

@router.post("/orders", response_model=OrderOut, summary="Tạo đơn hàng thanh toán")
async def create_order(
    payload: OrderCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Khởi tạo đơn hàng thanh toán qua VietQR, PayOS hoặc Stripe."""
    order = await PaymentService.create_order(
        db=db,
        user=current_user,
        plan_id=payload.plan_id,
        payment_method=payload.payment_method,
        coupon_code=payload.coupon_code,
    )
    return _format_order(order)


@router.get("/orders", response_model=OrderListResponse, summary="Lịch sử đơn hàng của tôi")
async def get_my_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=50),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Xem lại danh sách các hóa đơn, đơn hàng thanh toán."""
    orders, total = await PaymentService.list_user_orders(
        db, user_id=current_user.id, page=page, limit=limit
    )
    formatted = [_format_order(o) for o in orders]
    return OrderListResponse(orders=formatted, total=total, page=page, limit=limit)


@router.get("/orders/{order_id}", response_model=OrderOut, summary="Trạng thái realtime của đơn hàng")
async def get_order_status(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Lấy thông tin và trạng thái thanh toán hiện tại của đơn hàng (dùng cho trang chờ thanh toán realtime)."""
    order = await PaymentService.get_order_by_id_or_code(db, order_id)
    if not order:
        raise AppError(code="NOT_FOUND", message="Không tìm thấy đơn hàng", status_code=404)
    if order.user_id != current_user.id and not current_user.is_admin:
        raise AppError(code="FORBIDDEN", message="Bạn không có quyền truy cập đơn hàng này", status_code=403)

    return _format_order(order)


@router.post("/orders/{order_id}/cancel", response_model=OrderOut, summary="Hủy đơn hàng đang chờ")
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Hủy đơn hàng nếu người dùng không muốn thanh toán tiếp."""
    order = await PaymentService.cancel_order(db, order_id, current_user.id)
    return _format_order(order)


@router.post("/orders/{order_id}/pay-card", response_model=CardPaymentResult, summary="Khởi tạo thanh toán thẻ và xác thực 3DS OTP")
async def pay_order_with_card(
    order_id: int,
    payload: CardPaymentRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Khởi tạo thanh toán thẻ quốc tế qua Stripe / Napas và tạo yêu cầu 3D-Secure OTP."""
    updated_order, requires_otp, phone_hint, expires_in = await PaymentService.process_card_payment(
        db=db,
        order_id=order_id,
        user_id=current_user.id,
        card_number=payload.card_number,
        exp_month=payload.exp_month,
        exp_year=payload.exp_year,
        cvc=payload.cvc,
        cardholder_name=payload.cardholder_name,
    )
    return CardPaymentResult(
        order=_format_order(updated_order),
        requires_otp=requires_otp,
        phone_hint=phone_hint,
        expires_in=expires_in,
        message="Vui lòng nhập mã OTP được gửi đến số điện thoại của bạn để xác thực giao dịch.",
    )


@router.post("/orders/{order_id}/verify-otp", response_model=OrderOut, summary="Xác thực OTP và hoàn tất đơn hàng thẻ")
async def verify_order_card_otp(
    order_id: int,
    payload: VerifyOtpRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Xác thực mã 3D-Secure OTP và kích hoạt cộng credit cho tài khoản."""
    paid_order, _ = await PaymentService.verify_card_otp(
        db=db,
        order_id=order_id,
        user_id=current_user.id,
        otp=payload.otp,
    )
    return _format_order(paid_order)


@router.post("/orders/{order_id}/resend-otp", response_model=ResendOtpResponse, summary="Gửi lại mã xác thực OTP")
async def resend_order_card_otp(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Gửi lại mã OTP xác thực thẻ nếu hết hạn."""
    message, phone_hint, expires_in = await PaymentService.resend_card_otp(
        db=db,
        order_id=order_id,
        user_id=current_user.id,
    )
    return ResendOtpResponse(
        success=True,
        message=message,
        phone_hint=phone_hint,
        expires_in=expires_in,
    )



@router.get("/orders/{order_id}/receipt", summary="Tải biên lai thanh toán PDF")
async def download_receipt(
    order_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Xuất file PDF biên lai thanh toán chính thức."""
    order = await PaymentService.get_order_by_id_or_code(db, order_id)
    if not order:
        raise AppError(code="NOT_FOUND", message="Không tìm thấy đơn hàng", status_code=404)
    if order.user_id != current_user.id and not current_user.is_admin:
        raise AppError(code="FORBIDDEN", message="Bạn không có quyền tải biên lai này", status_code=403)
    if order.status != OrderStatus.PAID.value:
        raise AppError(code="ORDER_NOT_PAID", message="Đơn hàng chưa hoàn tất thanh toán, không thể tạo biên lai", status_code=400)

    plan_name = order.plan.name if order.plan else "Goi Credit"
    pdf_bytes = generate_receipt_pdf(
        order_code=order.order_code,
        user_email=order.user.email if order.user else current_user.email,
        plan_name=plan_name,
        original_amount=order.original_amount,
        discount_amount=order.discount_amount,
        final_amount=order.final_amount,
        credits=order.credits_to_add,
        payment_method=order.payment_method,
        paid_at=order.paid_at or order.updated_at,
    )

    filename = f"voxify-receipt-{order.order_code}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- 4. Webhooks (Xử lý giao dịch tự động) ---

@router.post("/webhook/payos", summary="Webhook tiếp nhận từ PayOS")
async def payos_webhook(
    payload: WebhookPayOSPayload,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook tiếp nhận từ cổng PayOS.
    Bảo mật bằng kiểm tra chữ ký HMAC-SHA256 và bảo đảm Idempotency.
    """
    # 1. Xác thực chữ ký
    if not PaymentService.verify_payos_signature(payload.data, payload.signature):
        logger.warning(f"Chữ ký PayOS không hợp lệ: {payload.signature}")
        raise HTTPException(status_code=400, detail="Chữ ký không hợp lệ")

    data = payload.data
    order_code_num = data.get("orderCode")
    amount = data.get("amount", 0)
    ref = data.get("reference") or f"payos_{order_code_num}_{data.get('transactionDateTime', '')}"

    # 2. Tìm đơn hàng
    order = await PaymentService.get_order_by_id_or_code(db, str(order_code_num))
    if not order:
        logger.warning(f"PayOS Webhook: Không tìm thấy đơn hàng orderCode={order_code_num}")
        return {"success": False, "message": "Order not found"}

    # 3. Xử lý thanh toán Idempotent
    updated_order, already_processed = await PaymentService.process_successful_payment(
        db=db,
        order=order,
        gateway="payos",
        transaction_id=str(ref),
        paid_amount=amount,
        raw_payload=payload.model_dump(),
    )

    return {"success": True, "already_processed": already_processed}


@router.post("/webhook/stripe", summary="Webhook tiếp nhận từ Stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook tiếp nhận sự kiện thanh toán quốc tế từ Stripe.
    """
    body = await request.body()
    if stripe_signature and not PaymentService.verify_stripe_signature(body, stripe_signature):
        logger.warning("Chữ ký Stripe Webhook không hợp lệ")
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")

    try:
        event = json.loads(body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = event.get("type")
    if event_type == "checkout.session.completed":
        session = event.get("data", {}).get("object", {})
        client_reference_id = session.get("client_reference_id")
        tx_id = session.get("payment_intent") or session.get("id")

        if client_reference_id:
            order = await PaymentService.get_order_by_id_or_code(db, client_reference_id)
            if order:
                await PaymentService.process_successful_payment(
                    db=db,
                    order=order,
                    gateway="stripe",
                    transaction_id=str(tx_id),
                    paid_amount=order.final_amount,
                    raw_payload=event,
                )

    return {"received": True}


@router.post("/webhook/vietqr", summary="Webhook VietQR / SePay tự động")
async def vietqr_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Webhook từ VietQR Hub hoặc SePay khi phát hiện biến động tài khoản ngân hàng.
    Khớp mã chuyển khoản và cộng credit chuẩn xác.
    """
    body_bytes = await request.body()
    try:
        data = json.loads(body_bytes.decode("utf-8"))
    except Exception:
        data = {}

    content = data.get("content") or data.get("transferContent") or data.get("code") or ""
    amount = int(data.get("transferAmount") or data.get("amount") or 0)
    tx_id = str(data.get("id") or data.get("transactionId") or data.get("referenceCode") or int(datetime.now(UTC).timestamp()))

    # Tìm đơn hàng qua mã chuyển khoản (content thường chứa VOX123456)
    order = None
    import re
    vox_match = re.search(r"VOX\d+", content, re.IGNORECASE)
    if vox_match:
        matched_code = vox_match.group(0).upper()
        order = await PaymentService.get_order_by_id_or_code(db, matched_code)

    if not order and content:
        order = await PaymentService.get_order_by_id_or_code(db, content.strip())

    if not order:
        logger.info(f"VietQR Webhook: Không tìm thấy đơn hàng khớp nội dung '{content}'")
        return {"success": False, "message": "Order not found"}

    updated_order, already_processed = await PaymentService.process_successful_payment(
        db=db,
        order=order,
        gateway="vietqr",
        transaction_id=tx_id,
        paid_amount=amount,
        raw_payload=data,
    )

    return {"success": True, "already_processed": already_processed, "order_code": updated_order.order_code}


# --- 5. Sandbox / Simulation Endpoint (Cho kiểm thử và nghiệm thu) ---

@router.post("/sandbox/simulate-payment", summary="[Sandbox] Giả lập thanh toán đơn hàng thành công")
async def simulate_sandbox_payment(
    payload: SandboxPaymentSimulateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    API giả lập thanh toán dành cho sandbox testing.
    Cho phép thử nghiệm quy trình thanh toán VietQR / PayOS và kiểm tra tính chất Idempotent.
    """
    order = await PaymentService.get_order_by_id_or_code(db, payload.order_id)
    if not order:
        raise AppError(code="NOT_FOUND", message="Không tìm thấy đơn hàng", status_code=404)
    if order.user_id != current_user.id and not current_user.is_admin:
        raise AppError(code="FORBIDDEN", message="Bạn không có quyền thao tác trên đơn hàng này", status_code=403)

    simulated_tx = f"SANDBOX_TX_{order.order_code}_{int(order.final_amount)}"
    updated_order, already_processed = await PaymentService.process_successful_payment(
        db=db,
        order=order,
        gateway="sandbox",
        transaction_id=simulated_tx,
        paid_amount=order.final_amount,
        raw_payload={"simulated": True, "by_user": current_user.id},
    )

    return {
        "success": True,
        "already_processed": already_processed,
        "order": _format_order(updated_order),
    }
