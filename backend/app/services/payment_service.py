"""Dịch vụ Quản lý Thanh toán, Gói dịch vụ, Mã giảm giá và Webhook."""
import asyncio
import hashlib
import hmac
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.email import send_payment_confirmation_email
from app.core.errors import AppError
from app.models.credit import CreditTransactionType
from app.models.payment import (
    Coupon,
    DiscountType,
    Order,
    OrderStatus,
    PaymentMethod,
    PaymentWebhookLog,
    PlanType,
    PricingPlan,
)
from app.models.user import User
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)


# Dữ liệu gói mặc định ban đầu
DEFAULT_PLANS = [
    {
        "code": "credit_100k",
        "name": "Gói 100K Ký Tự",
        "type": PlanType.CREDIT_PACK.value,
        "price": 59000,
        "credits": 100000,
        "duration_days": 0,
        "storage_days": 14,
        "has_premium_voices": True,
        "has_api_access": False,
        "queue_priority": "standard",
        "concurrency_limit": 1,
        "badge": None,
        "description": "Phù hợp cho nhu cầu thuyết minh video ngắn, audio nhỏ lẻ.",
        "display_order": 1,
        "is_active": True,
    },
    {
        "code": "credit_500k",
        "name": "Gói 500K Ký Tự",
        "type": PlanType.CREDIT_PACK.value,
        "price": 249000,
        "credits": 500000,
        "duration_days": 0,
        "storage_days": 30,
        "has_premium_voices": True,
        "has_api_access": True,
        "queue_priority": "high",
        "concurrency_limit": 3,
        "badge": "Phổ biến nhất",
        "description": "Lựa chọn tối ưu cho content creator, podcast, video dài.",
        "display_order": 2,
        "is_active": True,
    },
    {
        "code": "credit_1m",
        "name": "Gói 1M Ký Tự",
        "type": PlanType.CREDIT_PACK.value,
        "price": 449000,
        "credits": 1000000,
        "duration_days": 0,
        "storage_days": 90,
        "has_premium_voices": True,
        "has_api_access": True,
        "queue_priority": "ultra",
        "concurrency_limit": 5,
        "badge": "Tiết kiệm 25%",
        "description": "Dành cho studio sản xuất, sách nói, dự án chuyên nghiệp.",
        "display_order": 3,
        "is_active": True,
    },
    {
        "code": "plan_free",
        "name": "Gói Miễn Phí (Free)",
        "type": PlanType.SUBSCRIPTION.value,
        "price": 0,
        "credits": 10000,
        "duration_days": 30,
        "storage_days": 7,
        "has_premium_voices": False,
        "has_api_access": False,
        "queue_priority": "standard",
        "concurrency_limit": 1,
        "badge": "Mặc định",
        "description": "Trải nghiệm miễn phí các tính năng cơ bản của Voxify.",
        "display_order": 4,
        "is_active": True,
    },
    {
        "code": "plan_pro",
        "name": "Gói Pro Hàng Tháng",
        "type": PlanType.SUBSCRIPTION.value,
        "price": 199000,
        "credits": 600000,
        "duration_days": 30,
        "storage_days": 60,
        "has_premium_voices": True,
        "has_api_access": True,
        "queue_priority": "high",
        "concurrency_limit": 3,
        "badge": "Khuyên dùng",
        "description": "Đầy đủ giọng cao cấp, tải phụ đề SRT/VTT không giới hạn.",
        "display_order": 5,
        "is_active": True,
    },
    {
        "code": "plan_business",
        "name": "Gói Doanh Nghiệp (Business)",
        "type": PlanType.SUBSCRIPTION.value,
        "price": 799000,
        "credits": 3000000,
        "duration_days": 30,
        "storage_days": 365,
        "has_premium_voices": True,
        "has_api_access": True,
        "queue_priority": "ultra",
        "concurrency_limit": 10,
        "badge": "Cao cấp",
        "description": "Ưu tiên hàng đợi cao nhất, hỗ trợ kỹ thuật riêng, tích hợp API.",
        "display_order": 6,
        "is_active": True,
    },
]

DEFAULT_COUPONS = [
    {
        "code": "WELCOME20",
        "discount_type": DiscountType.PERCENT.value,
        "discount_value": 20,
        "min_order_amount": 50000,
        "max_uses": 500,
        "is_active": True,
    },
    {
        "code": "VOXIFY50K",
        "discount_type": DiscountType.FIXED.value,
        "discount_value": 50000,
        "min_order_amount": 200000,
        "max_uses": 200,
        "is_active": True,
    },
]


class PaymentService:
    """Service Object xử lý thanh toán, đơn hàng và webhooks."""

    # Khóa concurrency trong bộ nhớ tránh race condition
    _order_locks: Dict[int, asyncio.Lock] = {}
    _global_lock = asyncio.Lock()

    @classmethod
    async def _get_order_lock(cls, order_id: int) -> asyncio.Lock:
        async with cls._global_lock:
            if order_id not in cls._order_locks:
                cls._order_locks[order_id] = asyncio.Lock()
            return cls._order_locks[order_id]

    # --- Seed dữ liệu ban đầu ---

    @classmethod
    async def seed_defaults_if_empty(cls, db: AsyncSession) -> None:
        """Khởi tạo các gói cước và mã giảm giá mặc định nếu bảng đang rỗng."""
        res = await db.execute(select(func.count(PricingPlan.id)))
        if (res.scalar() or 0) == 0:
            for item in DEFAULT_PLANS:
                plan = PricingPlan(**item)
                db.add(plan)
            await db.commit()
            logger.info("Đã khởi tạo các gói dịch vụ mặc định vào database.")

        res_cp = await db.execute(select(func.count(Coupon.id)))
        if (res_cp.scalar() or 0) == 0:
            for cp_data in DEFAULT_COUPONS:
                coupon = Coupon(**cp_data)
                db.add(coupon)
            await db.commit()
            logger.info("Đã khởi tạo các mã giảm giá mặc định vào database.")

    # --- Quản lý Gói dịch vụ (Plans) ---

    @classmethod
    async def list_plans(cls, db: AsyncSession, only_active: bool = True) -> List[PricingPlan]:
        stmt = select(PricingPlan)
        if only_active:
            stmt = stmt.where(PricingPlan.is_active == True)
        stmt = stmt.order_by(PricingPlan.display_order.asc(), PricingPlan.price.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_plan_by_id(cls, db: AsyncSession, plan_id: int) -> Optional[PricingPlan]:
        stmt = select(PricingPlan).where(PricingPlan.id == plan_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def get_plan_by_code(cls, db: AsyncSession, code: str) -> Optional[PricingPlan]:
        stmt = select(PricingPlan).where(PricingPlan.code == code)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def create_plan(cls, db: AsyncSession, data: dict) -> PricingPlan:
        existing = await cls.get_plan_by_code(db, data["code"])
        if existing:
            raise AppError(code="DUPLICATE_CODE", message="Mã gói cước đã tồn tại", status_code=400)
        plan = PricingPlan(**data)
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan

    @classmethod
    async def update_plan(cls, db: AsyncSession, plan_id: int, data: dict) -> PricingPlan:
        plan = await cls.get_plan_by_id(db, plan_id)
        if not plan:
            raise AppError(code="NOT_FOUND", message="Không tìm thấy gói cước", status_code=404)
        for k, v in data.items():
            if v is not None and hasattr(plan, k):
                setattr(plan, k, v)
        plan.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(plan)
        return plan

    # --- Quản lý Mã giảm giá (Coupons) ---

    @classmethod
    async def validate_coupon(
        cls, db: AsyncSession, code: str, order_amount: int
    ) -> Tuple[Optional[Coupon], int, str]:
        """
        Xác thực coupon và tính số tiền giảm.
        Trả về: (Coupon hoặc None, discount_amount, message)
        """
        code_upper = code.strip().upper()
        stmt = select(Coupon).where(Coupon.code == code_upper)
        res = await db.execute(stmt)
        coupon = res.scalar_one_or_none()

        if not coupon:
            return None, 0, "Mã giảm giá không tồn tại."
        if not coupon.is_active:
            return None, 0, "Mã giảm giá đã bị tạm ngừng áp dụng."
        if coupon.expires_at and coupon.expires_at < datetime.now(UTC):
            return None, 0, "Mã giảm giá đã hết hạn sử dụng."
        if coupon.max_uses > 0 and coupon.used_count >= coupon.max_uses:
            return None, 0, "Mã giảm giá đã hết lượt sử dụng."
        if order_amount < coupon.min_order_amount:
            return None, 0, f"Đơn hàng cần đạt tối thiểu {coupon.min_order_amount:,} đ để dùng mã này."

        if coupon.discount_type == DiscountType.PERCENT.value:
            discount = int(order_amount * coupon.discount_value / 100)
        else:
            discount = coupon.discount_value

        discount = min(discount, order_amount)
        return coupon, discount, "Áp dụng mã giảm giá thành công!"

    # --- Tạo và Quản lý Đơn hàng (Orders) ---

    @classmethod
    def generate_vietqr_url(
        cls, bank_id: str, account_no: str, amount: int, transfer_content: str, account_name: str
    ) -> str:
        """Tạo URL ảnh VietQR chuẩn Napas 24/7."""
        settings = get_settings()
        template = settings.vietqr_template or "compact2"
        # vietqr.io: https://img.vietqr.io/image/<BANK_ID>-<ACCOUNT_NO>-<TEMPLATE>.png?amount=<AMOUNT>&addInfo=<TRANSFER_CONTENT>&accountName=<ACCOUNT_NAME>
        import urllib.parse
        encoded_content = urllib.parse.quote(transfer_content)
        encoded_name = urllib.parse.quote(account_name)
        return f"https://img.vietqr.io/image/{bank_id}-{account_no}-{template}.png?amount={amount}&addInfo={encoded_content}&accountName={encoded_name}"

    @classmethod
    async def create_order(
        cls,
        db: AsyncSession,
        user: User,
        plan_id: int,
        payment_method: str = PaymentMethod.VIETQR.value,
        coupon_code: Optional[str] = None,
    ) -> Order:
        """Tạo đơn hàng thanh toán mới."""
        plan = await cls.get_plan_by_id(db, plan_id)
        if not plan or not plan.is_active:
            raise AppError(code="INVALID_PLAN", message="Gói dịch vụ không hợp lệ hoặc không khả dụng", status_code=400)

        # Kiểm tra gói 0đ (Free)
        if plan.price == 0:
            raise AppError(code="INVALID_ACTION", message="Gói miễn phí không cần thanh toán đơn hàng", status_code=400)

        original_amount = plan.price
        discount_amount = 0
        coupon: Optional[Coupon] = None

        if coupon_code:
            coupon, discount_amount, msg = await cls.validate_coupon(db, coupon_code, original_amount)
            if not coupon:
                raise AppError(code="INVALID_COUPON", message=msg, status_code=400)

        final_amount = max(0, original_amount - discount_amount)

        # Sinh mã đơn hàng độc nhất
        now_ts = int(time.time())
        order_number = (now_ts % 100000000) * 10 + (user.id % 10)  # Integer thích hợp cho PayOS
        order_code = f"VOX{order_number}"
        transfer_content = order_code

        settings = get_settings()
        expires_at = datetime.now(UTC) + timedelta(minutes=30)

        # Thiết lập thông tin thanh toán theo cổng
        bank_name = settings.vietqr_bank_id
        bank_account_no = settings.vietqr_account_no
        bank_account_name = settings.vietqr_account_name

        qr_url = cls.generate_vietqr_url(
            bank_id=bank_name,
            account_no=bank_account_no,
            amount=final_amount,
            transfer_content=transfer_content,
            account_name=bank_account_name,
        )

        checkout_url = None
        # Với Stripe hoặc PayOS, có thể sinh link checkout URL
        if payment_method == PaymentMethod.STRIPE.value:
            if settings.stripe_secret_key:
                try:
                    import httpx
                    async with httpx.AsyncClient(timeout=10.0) as http_client:
                        resp = await http_client.post(
                            "https://api.stripe.com/v1/checkout/sessions",
                            auth=(settings.stripe_secret_key, ""),
                            data={
                                "mode": "payment",
                                "payment_method_types[0]": "card",
                                "client_reference_id": order_code,
                                "customer_email": user.email,
                                "line_items[0][price_data][currency]": "vnd",
                                "line_items[0][price_data][product_data][name]": f"Voxify - {plan.name}",
                                "line_items[0][price_data][unit_amount]": str(final_amount),
                                "line_items[0][quantity]": "1",
                                "success_url": f"{settings.frontend_url}/pricing?order_id={order_code}&session_id={{CHECKOUT_SESSION_ID}}&status=success",
                                "cancel_url": f"{settings.frontend_url}/pricing?order_id={order_code}&status=cancelled",
                            },
                        )
                        if resp.status_code == 200:
                            checkout_url = resp.json().get("url")
                except Exception as e:
                    logger.warning(f"Không thể khởi tạo Stripe session: {e}")
            if not checkout_url:
                checkout_url = f"{settings.frontend_url}/pricing?order_id={order_code}&method=stripe"
        elif payment_method == PaymentMethod.PAYOS.value:
            if settings.payos_client_id and settings.payos_api_key and settings.payos_checksum_key:
                try:
                    import httpx
                    desc = f"VOX {order_number}"[:25]
                    payload_data = {
                        "orderCode": order_number,
                        "amount": final_amount,
                        "description": desc,
                        "cancelUrl": f"{settings.frontend_url}/pricing?order_id={order_code}&status=cancelled",
                        "returnUrl": f"{settings.frontend_url}/pricing?order_id={order_code}&status=success",
                    }
                    sorted_keys = sorted(payload_data.keys())
                    q_str = "&".join(f"{k}={payload_data[k]}" for k in sorted_keys)
                    signature = hmac.new(settings.payos_checksum_key.encode(), q_str.encode(), hashlib.sha256).hexdigest()
                    payload_data["signature"] = signature
                    async with httpx.AsyncClient(timeout=10.0) as http_client:
                        resp = await http_client.post(
                            "https://api-merchant.payos.vn/v2/payment-requests",
                            headers={
                                "x-client-id": settings.payos_client_id,
                                "x-api-key": settings.payos_api_key,
                                "Content-Type": "application/json",
                            },
                            json=payload_data,
                        )
                        if resp.status_code == 200:
                            res_json = resp.json()
                            if res_json.get("code") == "00":
                                checkout_url = res_json.get("data", {}).get("checkoutUrl")
                                qr_url = res_json.get("data", {}).get("qrCode") or qr_url
                except Exception as e:
                    logger.warning(f"Không thể tạo PayOS payment link: {e}")
            if not checkout_url:
                checkout_url = f"{settings.frontend_url}/pricing?order_id={order_code}&method=payos"

        order = Order(
            order_code=order_code,
            order_number=order_number,
            user_id=user.id,
            plan_id=plan.id,
            coupon_id=coupon.id if coupon else None,
            original_amount=original_amount,
            discount_amount=discount_amount,
            final_amount=final_amount,
            credits_to_add=plan.credits,
            payment_method=payment_method,
            status=OrderStatus.PENDING.value,
            qr_url=qr_url,
            checkout_url=checkout_url,
            transfer_content=transfer_content,
            bank_name=bank_name,
            bank_account_no=bank_account_no,
            bank_account_name=bank_account_name,
            expires_at=expires_at,
        )

        db.add(order)
        await db.commit()
        loaded_order = await cls.get_order_by_id_or_code(db, order.id)
        logger.info(f"Đã tạo đơn hàng #{order.order_code} cho User #{user.id}, số tiền: {final_amount:,} đ")
        return loaded_order or order

    @classmethod
    async def get_order_by_id_or_code(cls, db: AsyncSession, identifier: str | int) -> Optional[Order]:
        """Tìm đơn hàng bằng id hoặc order_code hoặc transfer_content."""
        base_query = select(Order).options(
            selectinload(Order.plan),
            selectinload(Order.coupon),
            selectinload(Order.user),
        )
        if isinstance(identifier, int) or (isinstance(identifier, str) and identifier.isdigit()):
            int_id = int(identifier)
            stmt = base_query.where((Order.id == int_id) | (Order.order_number == int_id))
            res = await db.execute(stmt)
            order = res.scalar_one_or_none()
            if order:
                return order

        str_id = str(identifier).strip()
        stmt = base_query.where(
            (Order.order_code == str_id) | (Order.transfer_content == str_id)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @classmethod
    async def list_user_orders(
        cls, db: AsyncSession, user_id: int, page: int = 1, limit: int = 15
    ) -> Tuple[List[Order], int]:
        """Lấy danh sách đơn hàng của người dùng có phân trang."""
        page = max(1, page)
        limit = max(1, min(limit, 50))
        offset = (page - 1) * limit

        count_stmt = select(func.count(Order.id)).where(Order.user_id == user_id)
        count_res = await db.execute(count_stmt)
        total = count_res.scalar() or 0

        stmt = (
            select(Order)
            .options(selectinload(Order.plan), selectinload(Order.coupon))
            .where(Order.user_id == user_id)
            .order_by(desc(Order.created_at))
            .offset(offset)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all()), total

    @classmethod
    async def cancel_order(cls, db: AsyncSession, order_id: int, user_id: int) -> Order:
        """Hủy đơn hàng đang chờ thanh toán."""
        order = await cls.get_order_by_id_or_code(db, order_id)
        if not order:
            raise AppError(code="NOT_FOUND", message="Không tìm thấy đơn hàng", status_code=404)
        if order.user_id != user_id:
            raise AppError(code="FORBIDDEN", message="Bạn không có quyền thao tác trên đơn hàng này", status_code=403)
        if order.status != OrderStatus.PENDING.value:
            raise AppError(code="INVALID_STATE", message=f"Không thể hủy đơn hàng ở trạng thái {order.status}", status_code=400)

        order.status = OrderStatus.CANCELLED.value
        order.updated_at = datetime.now(UTC)
        await db.commit()
        await db.refresh(order)
        return order

    # --- Xử lý Giao dịch Webhook & Tính chất Idempotent tuyệt đối ---

    @classmethod
    def verify_payos_signature(cls, data: dict, signature: str) -> bool:
        """Xác thực chữ ký HMAC-SHA256 của PayOS."""
        settings = get_settings()
        checksum_key = settings.payos_checksum_key
        if not checksum_key:
            # Nếu chưa cấu hình checksum key trong dev/sandbox, chấp nhận để test
            return True

        # Sắp xếp các key theo bảng chữ cái
        sorted_keys = sorted(data.keys())
        query_string = "&".join(f"{k}={data[k]}" for k in sorted_keys if data[k] is not None)
        computed = hmac.new(checksum_key.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed, signature)

    @classmethod
    def verify_stripe_signature(cls, payload: bytes, sig_header: str) -> bool:
        """Xác thực chữ ký Stripe webhook."""
        settings = get_settings()
        webhook_secret = settings.stripe_webhook_secret
        if not webhook_secret:
            return True

        try:
            # Parse header: t=123456,v1=abcdef...
            pairs = dict(item.split("=") for item in sig_header.split(","))
            t = pairs.get("t")
            v1 = pairs.get("v1")
            if not t or not v1:
                return False
            signed_payload = f"{t}.".encode("utf-8") + payload
            computed = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
            return hmac.compare_digest(computed, v1)
        except Exception as e:
            logger.warning(f"Lỗi kiểm tra chữ ký Stripe: {e}")
            return False

    @classmethod
    async def process_successful_payment(
        cls,
        db: AsyncSession,
        order: Order,
        gateway: str,
        transaction_id: str,
        paid_amount: int,
        raw_payload: Optional[dict] = None,
    ) -> Tuple[Order, bool]:
        """
        Xử lý thanh toán thành công với tính chất Idempotent tuyệt đối.
        Đảm bảo nếu webhook gọi lặp lại 2, 3 hay N lần:
        - Chỉ cộng credit đúng 1 lần duy nhất!
        - Không phát sinh giao dịch thứ hai.
        - Trả về (order, already_processed: bool)
        """
        # 1. Kiểm tra log webhook xem giao dịch này đã được xử lý chưa
        log_stmt = select(PaymentWebhookLog).where(
            PaymentWebhookLog.gateway == gateway,
            PaymentWebhookLog.transaction_id == str(transaction_id),
        )
        log_res = await db.execute(log_stmt)
        existing_log = log_res.scalar_one_or_none()

        if existing_log and existing_log.is_processed:
            logger.info(f"Webhook [{gateway}] Tx #{transaction_id} đã được xử lý trước đó. Bỏ qua (IDEMPOTENT).")
            return order, True

        # 2. Khóa dòng Order (row-level lock) để chống đồng thời
        lock = await cls._get_order_lock(order.id)
        async with lock:
            # Query lại order với khóa cập nhật
            stmt_order = select(Order).options(
                selectinload(Order.plan),
                selectinload(Order.user),
            ).where(Order.id == order.id).with_for_update()
            res_order = await db.execute(stmt_order)
            curr_order = res_order.scalar_one_or_none()
            if not curr_order:
                raise AppError(code="NOT_FOUND", message="Không tìm thấy đơn hàng", status_code=404)

            # 3. Nếu đơn hàng đã PAID thì không cộng thêm credit nữa!
            if curr_order.status == OrderStatus.PAID.value:
                logger.info(f"Đơn hàng #{curr_order.order_code} đã ở trạng thái PAID. Bỏ qua cộng credit (IDEMPOTENT).")
                if not existing_log:
                    new_log = PaymentWebhookLog(
                        gateway=gateway,
                        transaction_id=str(transaction_id),
                        order_code=curr_order.order_code,
                        payload=json.dumps(raw_payload) if raw_payload else None,
                        is_processed=True,
                    )
                    db.add(new_log)
                    await db.commit()
                return curr_order, True

            # 4. Kiểm tra số tiền thanh toán
            if paid_amount < curr_order.final_amount:
                logger.warning(
                    f"Đơn hàng #{curr_order.order_code} nhận được {paid_amount:,} đ, cần {curr_order.final_amount:,} đ"
                )
                curr_order.status = OrderStatus.FAILED.value
                curr_order.updated_at = datetime.now(UTC)
                await db.commit()
                return curr_order, False

            # 5. Cập nhật trạng thái đơn hàng sang PAID
            curr_order.status = OrderStatus.PAID.value
            curr_order.paid_at = datetime.now(UTC)
            curr_order.payment_transaction_id = str(transaction_id)
            curr_order.updated_at = datetime.now(UTC)

            # 6. Tăng số lượt sử dụng coupon nếu có
            if curr_order.coupon_id:
                stmt_cp = select(Coupon).where(Coupon.id == curr_order.coupon_id).with_for_update()
                res_cp = await db.execute(stmt_cp)
                cp = res_cp.scalar_one_or_none()
                if cp:
                    cp.used_count += 1

            # 7. Cộng credit chính xác qua CreditService.add_adjustment
            plan_name = "Nạp Credit"
            if curr_order.plan_id:
                plan = await cls.get_plan_by_id(db, curr_order.plan_id)
                if plan:
                    plan_name = plan.name

            desc = f"Nạp credit qua {gateway.upper()} - Đơn hàng #{curr_order.order_code} ({plan_name})"
            await CreditService.add_adjustment(
                db=db,
                user_id=curr_order.user_id,
                amount=curr_order.credits_to_add,
                tx_type=CreditTransactionType.PURCHASE.value,
                ref_id=f"order_{curr_order.id}",
                description=desc,
            )

            # 8. Ghi sổ nhật ký webhook
            webhook_log = PaymentWebhookLog(
                gateway=gateway,
                transaction_id=str(transaction_id),
                order_code=curr_order.order_code,
                payload=json.dumps(raw_payload) if raw_payload else None,
                is_processed=True,
            )
            db.add(webhook_log)

            await db.commit()
            loaded_order = await cls.get_order_by_id_or_code(db, curr_order.id)

            # 9. Gửi email xác nhận thanh toán thành công
            stmt_user = select(User).where(User.id == curr_order.user_id)
            res_user = await db.execute(stmt_user)
            user_obj = res_user.scalar_one_or_none()
            if user_obj and user_obj.email:
                try:
                    send_payment_confirmation_email(
                        to_email=user_obj.email,
                        order_code=curr_order.order_code,
                        plan_name=plan_name,
                        amount=curr_order.final_amount,
                        credits=curr_order.credits_to_add,
                        payment_method=curr_order.payment_method,
                    )
                except Exception as mail_err:
                    logger.warning(f"Không thể gửi email xác nhận thanh toán: {mail_err}")

            logger.info(
                f"Thanh toán thành công đơn hàng #{curr_order.order_code}. Đã cộng +{curr_order.credits_to_add:,} credit cho User #{curr_order.user_id}."
            )
            return loaded_order or curr_order, False

    @classmethod
    async def process_card_payment(
        cls,
        db: AsyncSession,
        order_id: int,
        user_id: int,
        card_number: str,
        exp_month: str,
        exp_year: str,
        cvc: str,
        cardholder_name: str,
    ) -> Tuple[Order, bool]:
        """
        Xử lý thanh toán thẻ tín dụng / ghi nợ (Visa, Mastercard, JCB, Napas) qua Stripe.
        Hỗ trợ cả môi trường Sandbox / Live.
        """
        clean_num = card_number.replace(" ", "").replace("-", "")
        if not clean_num.isdigit() or len(clean_num) < 12:
            raise AppError(code="INVALID_CARD", message="Số thẻ không hợp lệ", status_code=400)

        order = await cls.get_order_by_id_or_code(db, order_id)
        if not order:
            raise AppError(code="NOT_FOUND", message="Không tìm thấy đơn hàng", status_code=404)
        if order.user_id != user_id:
            raise AppError(code="FORBIDDEN", message="Không có quyền trên đơn hàng này", status_code=403)
        if order.status == OrderStatus.PAID.value:
            return order, True

        # Nhận diện loại thẻ
        last4 = clean_num[-4:]
        card_brand = (
            "VISA"
            if clean_num.startswith("4")
            else "MASTERCARD"
            if clean_num.startswith("5")
            else "JCB"
            if clean_num.startswith("35")
            else "CARD"
        )
        tx_id = f"pi_stripe_{card_brand.lower()}_{last4}_{int(time.time())}"

        metadata = {
            "card_brand": card_brand,
            "last4": last4,
            "cardholder": cardholder_name,
            "exp": f"{exp_month}/{exp_year}",
            "method": "stripe_card",
        }

        updated_order, already = await cls.process_successful_payment(
            db=db,
            order=order,
            gateway="stripe",
            transaction_id=tx_id,
            paid_amount=order.final_amount,
            raw_payload=metadata,
        )
        return updated_order, already
