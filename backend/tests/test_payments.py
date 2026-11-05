"""Kiểm thử tính năng Thanh toán & Gói dịch vụ (VietQR / PayOS / Stripe) và Idempotency."""
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Tuple
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.errors import AppError
from app.core.security import hash_password
from app.db import AsyncSessionLocal
from app.main import app
from app.models.credit import CreditTransaction
from app.models.payment import Coupon, DiscountType, Order, OrderStatus
from app.models.user import User
from app.services.payment_service import PaymentService


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def register_and_login(client: AsyncClient, prefix: str = "test") -> Tuple[str, int]:
    """Helper đăng ký và đăng nhập trả về (token, user_id)."""
    email = f"{prefix}_{time.time()}@example.com"
    password = "Password123!"
    reg_res = await client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": "Test User",
    })
    user_id = reg_res.json()["id"]

    login_res = await client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    })
    token = login_res.json()["access_token"]
    return token, user_id


async def create_admin_and_login(client: AsyncClient) -> Tuple[str, int]:
    """Tạo user có quyền admin và trả về (token, user_id)."""
    email = f"admin_{time.time()}@example.com"
    password = "AdminPassword123!"
    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Admin User",
            role="admin",
            is_active=True,
            is_admin=True,
            is_verified=True,
            credit_balance=100000,
            credits=100000,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    login_res = await client.post("/api/auth/login", json={"email": email, "password": password})
    return login_res.json()["access_token"], user_id



@pytest.mark.asyncio
async def test_pricing_plans_list():
    """Kiểm tra API lấy danh sách gói cước và seed dữ liệu mặc định."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/payments/plans")
        assert res.status_code == 200
        plans = res.json()
        assert len(plans) >= 6
        codes = [p["code"] for p in plans]
        assert "credit_100k" in codes
        assert "credit_500k" in codes
        assert "plan_pro" in codes


@pytest.mark.asyncio
async def test_coupon_validation_and_discount():
    """Kiểm tra xác thực mã giảm giá (phần trăm và số tiền cố định)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, user_id = await register_and_login(client, "coupon")
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 1. Mã không tồn tại
        res = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": "NON_EXISTENT", "order_amount": 100000},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is False

        # 2. Mã WELCOME20 (giảm 20% đơn từ 50k)
        res = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": "WELCOME20", "order_amount": 100000},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["valid"] is True
        assert data["discount_amount"] == 20000
        assert data["final_amount"] == 80000

        # 3. Mã VOXIFY50K (giảm 50k đơn từ 200k)
        res_fail = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": "VOXIFY50K", "order_amount": 100000},
        )
        assert res_fail.json()["valid"] is False  # Chưa đạt 200k

        res_ok = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": "VOXIFY50K", "order_amount": 250000},
        )
        assert res_ok.json()["valid"] is True
        assert res_ok.json()["discount_amount"] == 50000
        assert res_ok.json()["final_amount"] == 200000


@pytest.mark.asyncio
async def test_order_creation_and_vietqr():
    """Kiểm tra tạo đơn hàng VietQR và lấy trạng thái đơn hàng."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, user_id = await register_and_login(client, "order")
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Lấy plan_id của gói 100k
        plans_res = await client.get("/api/payments/plans")
        plans = plans_res.json()
        pack = next(p for p in plans if p["code"] == "credit_100k")

        # Tạo đơn hàng
        create_res = await client.post(
            "/api/payments/orders",
            headers=auth_headers,
            json={
                "plan_id": pack["id"],
                "payment_method": "vietqr",
                "coupon_code": "WELCOME20",
            },
        )
        assert create_res.status_code == 200
        order_data = create_res.json()
        assert order_data["status"] == "pending"
        assert order_data["credits_to_add"] == 100000
        assert order_data["original_amount"] == 59000
        # 59000 - 20% (11800) = 47200
        assert order_data["discount_amount"] == 11800
        assert order_data["final_amount"] == 47200
        assert "img.vietqr.io" in order_data["qr_url"]
        assert order_data["transfer_content"].startswith("VOX")

        order_id = order_data["id"]

        # Lấy trạng thái đơn hàng
        status_res = await client.get(f"/api/payments/orders/{order_id}", headers=auth_headers)
        assert status_res.status_code == 200
        assert status_res.json()["order_code"] == order_data["order_code"]

        # Danh sách đơn hàng của tôi
        list_res = await client.get("/api/payments/orders", headers=auth_headers)
        assert list_res.status_code == 200
        assert list_res.json()["total"] >= 1


@pytest.mark.asyncio
async def test_idempotent_webhook_processing_3_times():
    """
    Tiêu chuẩn nghiệm thu Issue 11:
    Thanh toán sandbox VietQR cộng credit chính xác 1 lần duy nhất dù webhook gọi lặp 3 lần.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, user_id = await register_and_login(client, "idempotent")
        auth_headers = {"Authorization": f"Bearer {token}"}

        # Số dư ban đầu (bonus đăng ký = 10,000)
        me_res = await client.get("/api/me", headers=auth_headers)
        initial_balance = me_res.json()["credit_balance"]
        assert initial_balance == 10000

        # Lấy gói 500k credit (249,000 VND)
        plans_res = await client.get("/api/payments/plans")
        pack = next(p for p in plans_res.json() if p["code"] == "credit_500k")

        # Tạo đơn hàng
        create_res = await client.post(
            "/api/payments/orders",
            headers=auth_headers,
            json={"plan_id": pack["id"], "payment_method": "vietqr"},
        )
        assert create_res.status_code == 200
        order = create_res.json()
        order_code = order["order_code"]
        amount = order["final_amount"]

        tx_id = f"BANK_TX_{int(time.time() * 1000)}"
        webhook_payload = {
            "id": tx_id,
            "gateway": "MB",
            "transactionDate": "2026-11-05 14:00:00",
            "accountNumber": "0333888999",
            "transferType": "in",
            "transferAmount": amount,
            "accumulated": 10000000,
            "content": f"Thanh toan don hang {order_code}",
        }

        # === LẦN GỌI WEBHOOK 1 ===
        wh1 = await client.post("/api/payments/webhook/vietqr", json=webhook_payload)
        assert wh1.status_code == 200
        wh1_data = wh1.json()
        assert wh1_data["success"] is True
        assert wh1_data["already_processed"] is False

        # Kiểm tra số dư sau lần 1: đã được cộng đúng 500,000 credits
        me_after_1 = await client.get("/api/me", headers=auth_headers)
        balance_1 = me_after_1.json()["credit_balance"]
        assert balance_1 == initial_balance + 500000

        # === LẦN GỌI WEBHOOK 2 (LẶP LẠI) ===
        wh2 = await client.post("/api/payments/webhook/vietqr", json=webhook_payload)
        assert wh2.status_code == 200
        wh2_data = wh2.json()
        assert wh2_data["success"] is True
        assert wh2_data["already_processed"] is True

        # Kiểm tra số dư sau lần 2: KHÔNG BỊ CỘNG LẦN NỮA!
        me_after_2 = await client.get("/api/me", headers=auth_headers)
        balance_2 = me_after_2.json()["credit_balance"]
        assert balance_2 == balance_1

        # === LẦN GỌI WEBHOOK 3 (LẶP LẠI) ===
        wh3 = await client.post("/api/payments/webhook/vietqr", json=webhook_payload)
        assert wh3.status_code == 200
        wh3_data = wh3.json()
        assert wh3_data["success"] is True
        assert wh3_data["already_processed"] is True

        # Kiểm tra số dư sau lần 3: VẪN CHÍNH XÁC NHƯ CŨ!
        me_after_3 = await client.get("/api/me", headers=auth_headers)
        balance_3 = me_after_3.json()["credit_balance"]
        assert balance_3 == balance_1

        # Kiểm tra trong DB: chỉ có đúng 1 giao dịch credit PURCHASE cho đơn hàng này
        async with AsyncSessionLocal() as session:
            tx_stmt = select(CreditTransaction).where(
                CreditTransaction.user_id == user_id,
                CreditTransaction.ref_id == f"order_{order['id']}",
            )
            tx_res = await session.execute(tx_stmt)
            tx_list = tx_res.scalars().all()
            assert len(tx_list) == 1
            assert tx_list[0].amount == 500000
            assert tx_list[0].type == "purchase"


@pytest.mark.asyncio
async def test_payos_webhook_and_sandbox_simulation():
    """Kiểm tra webhook PayOS và endpoint giả lập thanh toán Sandbox."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, user_id = await register_and_login(client, "payos")
        auth_headers = {"Authorization": f"Bearer {token}"}

        plans_res = await client.get("/api/payments/plans")
        pack = next(p for p in plans_res.json() if p["code"] == "credit_100k")

        # Tạo đơn
        create_res = await client.post(
            "/api/payments/orders",
            headers=auth_headers,
            json={"plan_id": pack["id"], "payment_method": "payos"},
        )
        order = create_res.json()

        # Giả lập thanh toán qua sandbox simulation endpoint
        sim_res = await client.post(
            "/api/payments/sandbox/simulate-payment",
            headers=auth_headers,
            json={"order_id": order["id"]},
        )
        assert sim_res.status_code == 200
        sim_data = sim_res.json()
        assert sim_data["success"] is True
        assert sim_data["already_processed"] is False
        assert sim_data["order"]["status"] == "paid"

        # Gọi lại simulate lần 2 trên cùng đơn hàng
        sim_res_2 = await client.post(
            "/api/payments/sandbox/simulate-payment",
            headers=auth_headers,
            json={"order_id": order["id"]},
        )
        assert sim_res_2.status_code == 200
        assert sim_res_2.json()["already_processed"] is True


@pytest.mark.asyncio
async def test_download_pdf_receipt():
    """Kiểm tra tải biên lai hóa đơn định dạng PDF."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, user_id = await register_and_login(client, "receipt")
        auth_headers = {"Authorization": f"Bearer {token}"}

        plans_res = await client.get("/api/payments/plans")
        pack = next(p for p in plans_res.json() if p["price"] > 0)

        # Tạo và thanh toán đơn
        create_res = await client.post(
            "/api/payments/orders",
            headers=auth_headers,
            json={"plan_id": pack["id"], "payment_method": "vietqr"},
        )
        order = create_res.json()

        # Tải biên lai khi chưa thanh toán -> 400
        res_fail = await client.get(f"/api/payments/orders/{order['id']}/receipt", headers=auth_headers)
        assert res_fail.status_code == 400

        # Thanh toán đơn
        await client.post(
            "/api/payments/sandbox/simulate-payment",
            headers=auth_headers,
            json={"order_id": order["id"]},
        )

        # Tải biên lai sau khi thanh toán -> 200 PDF
        res_ok = await client.get(f"/api/payments/orders/{order['id']}/receipt", headers=auth_headers)
        assert res_ok.status_code == 200
        assert res_ok.headers["content-type"] == "application/pdf"
        assert res_ok.content.startswith(b"%PDF-1.4")


@pytest.mark.asyncio
async def test_card_payment_stripe_flow():
    """Kiểm tra quy trình thanh toán thẻ tín dụng quốc tế (Visa/Mastercard/Stripe)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, user_id = await register_and_login(client, "cardpay")
        auth_headers = {"Authorization": f"Bearer {token}"}

        plans_res = await client.get("/api/payments/plans")
        pack = next(p for p in plans_res.json() if p["code"] == "credit_100k")

        me_init = await client.get("/api/me", headers=auth_headers)
        initial_balance = me_init.json()["credit_balance"]

        # 1. Tạo đơn hàng chọn cổng stripe
        create_res = await client.post(
            "/api/payments/orders",
            headers=auth_headers,
            json={"plan_id": pack["id"], "payment_method": "stripe"},
        )
        assert create_res.status_code == 200
        order = create_res.json()
        assert order["payment_method"] == "stripe"
        assert order["status"] == "pending"

        # 2. Thử thanh toán với số thẻ không hợp lệ (< 12 số) -> 422 (Schema validation)
        invalid_card_res = await client.post(
            f"/api/payments/orders/{order['id']}/pay-card",
            headers=auth_headers,
            json={
                "card_number": "12345",
                "cardholder_name": "TEST USER",
                "exp_month": "12",
                "exp_year": "28",
                "cvc": "123",
            },
        )
        assert invalid_card_res.status_code == 422

        # 3. Khởi tạo thanh toán thẻ hợp lệ -> Yêu cầu 3D-Secure OTP
        valid_card_res = await client.post(
            f"/api/payments/orders/{order['id']}/pay-card",
            headers=auth_headers,
            json={
                "card_number": "4242424242424242",
                "cardholder_name": "TEST USER",
                "exp_month": "12",
                "exp_year": "28",
                "cvc": "123",
            },
        )
        assert valid_card_res.status_code == 200
        card_init_result = valid_card_res.json()
        assert card_init_result["requires_otp"] is True
        assert card_init_result["phone_hint"] is not None
        assert card_init_result["expires_in"] > 0

        # 4. Kiểm tra tính năng Gửi lại mã OTP (Resend OTP)
        resend_res = await client.post(
            f"/api/payments/orders/{order['id']}/resend-otp",
            headers=auth_headers,
        )
        assert resend_res.status_code == 200
        assert resend_res.json()["success"] is True

        # 5. Xác thực OTP sai -> 400 Bad Request
        wrong_otp_res = await client.post(
            f"/api/payments/orders/{order['id']}/verify-otp",
            headers=auth_headers,
            json={"otp": "000000"},
        )
        assert wrong_otp_res.status_code == 400
        assert "không chính xác" in wrong_otp_res.json()["error"]["message"]

        # 6. Xác thực OTP đúng (123456) -> Hoàn tất thanh toán & cộng credit
        verify_res = await client.post(
            f"/api/payments/orders/{order['id']}/verify-otp",
            headers=auth_headers,
            json={"otp": "123456"},
        )
        assert verify_res.status_code == 200
        paid_order = verify_res.json()
        assert paid_order["status"] == "paid"
        assert paid_order["paid_at"] is not None

        # 7. Kiểm tra số dư credit của user đã được cộng chính xác
        me_res = await client.get("/api/me", headers=auth_headers)
        assert me_res.status_code == 200
        assert me_res.json()["credit_balance"] == initial_balance + pack["credits"]

        # 8. Xác thực lại lần 2 đơn đã trả tiền -> Idempotent, giữ nguyên status paid và không cộng trùng
        repeat_otp_res = await client.post(
            f"/api/payments/orders/{order['id']}/verify-otp",
            headers=auth_headers,
            json={"otp": "123456"},
        )
        assert repeat_otp_res.status_code == 200
        assert repeat_otp_res.json()["status"] == "paid"

        me_res2 = await client.get("/api/me", headers=auth_headers)
        assert me_res2.json()["credit_balance"] == initial_balance + pack["credits"]


@pytest.mark.asyncio
async def test_admin_plans_crud_and_permissions():
    """Kiểm tra quyền hạn và CRUD gói cước dành cho Admin."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_token, _ = await register_and_login(client, "normal_user")
        admin_token, _ = await create_admin_and_login(client)

        plan_payload = {
            "code": f"custom_plan_{int(time.time())}",
            "name": "Gói Custom Siêu VIP",
            "type": "credit_pack",
            "price": 149000,
            "currency": "VND",
            "credits": 300000,
            "duration_days": 0,
            "storage_days": 45,
            "has_premium_voices": True,
            "has_api_access": True,
            "queue_priority": "high",
            "concurrency_limit": 2,
            "badge": "Mới",
            "description": "Gói test tự động",
            "display_order": 99,
            "is_active": True,
        }

        # 1. User thường gọi API admin -> 403 Forbidden
        user_create_res = await client.post(
            "/api/payments/admin/plans",
            headers={"Authorization": f"Bearer {user_token}"},
            json=plan_payload,
        )
        assert user_create_res.status_code == 403

        # 2. Admin gọi API tạo gói -> 200 OK
        admin_create_res = await client.post(
            "/api/payments/admin/plans",
            headers={"Authorization": f"Bearer {admin_token}"},
            json=plan_payload,
        )
        assert admin_create_res.status_code == 200
        created_plan = admin_create_res.json()
        assert created_plan["code"] == plan_payload["code"]

        # 3. Admin cập nhật gói -> 200 OK
        update_res = await client.put(
            f"/api/payments/admin/plans/{created_plan['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Gói Custom Đã Đổi Tên", "price": 159000},
        )
        assert update_res.status_code == 200
        assert update_res.json()["name"] == "Gói Custom Đã Đổi Tên"
        assert update_res.json()["price"] == 159000

        # 4. Admin cập nhật gói không tồn tại -> 404
        update_not_found = await client.put(
            "/api/payments/admin/plans/999999",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"name": "Gói Không Tồn Tại"},
        )
        assert update_not_found.status_code == 404


@pytest.mark.asyncio
async def test_orders_lifecycle_and_security():
    """Kiểm tra chi tiết vòng đời đơn hàng, phân trang và bảo mật truy cập."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_a, _ = await register_and_login(client, "user_a")
        token_b, _ = await register_and_login(client, "user_b")

        plans_res = await client.get("/api/payments/plans")
        pack = next(p for p in plans_res.json() if p["price"] > 0)

        # 1. User A tạo đơn hàng
        create_res = await client.post(
            "/api/payments/orders",
            headers={"Authorization": f"Bearer {token_a}"},
            json={"plan_id": pack["id"], "payment_method": "vietqr"},
        )
        assert create_res.status_code == 200
        order_a = create_res.json()

        # 2. User A xem đơn hàng của mình -> 200 OK
        get_res = await client.get(
            f"/api/payments/orders/{order_a['id']}",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert get_res.status_code == 200
        assert get_res.json()["id"] == order_a["id"]

        # 3. User B xem trộm đơn hàng của User A -> 403 Forbidden
        forbidden_res = await client.get(
            f"/api/payments/orders/{order_a['id']}",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert forbidden_res.status_code == 403

        # 4. Xem đơn hàng không tồn tại -> 404 Not Found
        not_found_res = await client.get(
            "/api/payments/orders/999999",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert not_found_res.status_code == 404

        # 5. Xem danh sách đơn hàng có phân trang
        list_res = await client.get(
            "/api/payments/orders?page=1&limit=5",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert "orders" in list_data
        assert list_data["total"] >= 1

        # 6. User B thử hủy đơn của User A -> 403 Forbidden
        cancel_forbid = await client.post(
            f"/api/payments/orders/{order_a['id']}/cancel",
            headers={"Authorization": f"Bearer {token_b}"},
        )
        assert cancel_forbid.status_code == 403

        # 7. User A hủy đơn của mình -> status chuyển thành cancelled
        cancel_ok = await client.post(
            f"/api/payments/orders/{order_a['id']}/cancel",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert cancel_ok.status_code == 200
        assert cancel_ok.json()["status"] == "cancelled"

        # 8. Hủy lại đơn đã hủy -> 400
        cancel_again = await client.post(
            f"/api/payments/orders/{order_a['id']}/cancel",
            headers={"Authorization": f"Bearer {token_a}"},
        )
        assert cancel_again.status_code == 400


@pytest.mark.asyncio
async def test_coupons_edge_cases_and_discounts():
    """Kiểm tra tất cả nhánh điều kiện của mã giảm giá (Coupon)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await register_and_login(client, "coupon_user")
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 1. Mã không tồn tại
        res_non = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": "KHONG_CO_THUC", "order_amount": 100000},
        )
        assert res_non.status_code == 200
        assert res_non.json()["valid"] is False

        # 2. Tạo các loại coupon mẫu trong DB để test điều kiện
        now = datetime.now(UTC)
        t = int(time.time() * 1000)
        code_exp = f"EXP_{t}"
        code_ina = f"INA_{t}"
        code_max = f"MAX_{t}"
        code_min = f"MIN_{t}"
        code_fix = f"FIX_{t}"

        async with AsyncSessionLocal() as db:
            # Coupon hết hạn
            cp_expired = Coupon(
                code=code_exp,
                discount_type=DiscountType.PERCENT.value,
                discount_value=20,
                expires_at=now - timedelta(days=2),
                is_active=True,
                max_uses=10,
                used_count=0,
            )
            # Coupon bị vô hiệu hóa
            cp_inactive = Coupon(
                code=code_ina,
                discount_type=DiscountType.PERCENT.value,
                discount_value=20,
                expires_at=now + timedelta(days=2),
                is_active=False,
                max_uses=10,
                used_count=0,
            )
            # Coupon hết lượt dùng
            cp_max_used = Coupon(
                code=code_max,
                discount_type=DiscountType.PERCENT.value,
                discount_value=20,
                expires_at=now + timedelta(days=2),
                is_active=True,
                max_uses=5,
                used_count=5,
            )
            # Coupon yêu cầu giá trị tối thiểu
            cp_min_amount = Coupon(
                code=code_min,
                discount_type=DiscountType.FIXED.value,
                discount_value=30000,
                min_order_amount=200000,
                expires_at=now + timedelta(days=2),
                is_active=True,
                max_uses=10,
                used_count=0,
            )
            # Coupon giảm số tiền cố định (VND)
            cp_fixed = Coupon(
                code=code_fix,
                discount_type=DiscountType.FIXED.value,
                discount_value=50000,
                min_order_amount=50000,
                expires_at=now + timedelta(days=2),
                is_active=True,
                max_uses=10,
                used_count=0,
            )
            db.add_all([cp_expired, cp_inactive, cp_max_used, cp_min_amount, cp_fixed])
            await db.commit()

        # Kiểm tra coupon hết hạn
        res_exp = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": code_exp, "order_amount": 100000},
        )
        assert res_exp.json()["valid"] is False
        assert "hết hạn" in res_exp.json()["message"]

        # Kiểm tra coupon vô hiệu hóa
        res_ina = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": code_ina, "order_amount": 100000},
        )
        assert res_ina.json()["valid"] is False

        # Kiểm tra coupon hết lượt dùng
        res_max = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": code_max, "order_amount": 100000},
        )
        assert res_max.json()["valid"] is False
        assert "hết lượt" in res_max.json()["message"]

        # Kiểm tra chưa đạt giá trị tối thiểu
        res_min = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": code_min, "order_amount": 100000},
        )
        assert res_min.json()["valid"] is False
        assert "tối thiểu" in res_min.json()["message"]

        # Kiểm tra coupon giảm số tiền cố định thành công
        res_fixed = await client.post(
            "/api/payments/coupons/validate",
            headers=auth_headers,
            json={"code": code_fix, "order_amount": 120000},
        )
        assert res_fixed.json()["valid"] is True
        assert res_fixed.json()["discount_amount"] == 50000
        assert res_fixed.json()["final_amount"] == 70000


@pytest.mark.asyncio
async def test_webhooks_variations_and_errors():
    """Kiểm tra xử lý các biến thể webhook PayOS, Stripe và VietQR."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await register_and_login(client, "wh_user")
        auth_headers = {"Authorization": f"Bearer {token}"}

        plans_res = await client.get("/api/payments/plans")
        pack = next(p for p in plans_res.json() if p["price"] > 0)

        # Tạo 1 order để nhận webhook
        create_res = await client.post(
            "/api/payments/orders",
            headers=auth_headers,
            json={"plan_id": pack["id"], "payment_method": "stripe"},
        )
        order = create_res.json()

        # 1. PayOS webhook với chữ ký sai -> 400
        with patch.object(PaymentService, "verify_payos_signature", return_value=False):
            payos_bad_sig = await client.post(
                "/api/payments/webhook/payos",
                json={
                    "code": "00",
                    "desc": "success",
                    "data": {"orderCode": order["order_number"], "amount": order["final_amount"]},
                    "signature": "INVALID_SIGNATURE_HASH",
                },
            )
            assert payos_bad_sig.status_code == 400

        # 2. PayOS webhook với order không tồn tại
        payos_not_found = await client.post(
            "/api/payments/webhook/payos",
            json={
                "code": "00",
                "desc": "success",
                "data": {"orderCode": 88888888, "amount": 50000},
                "signature": "",
            },
        )
        assert payos_not_found.status_code == 200
        assert payos_not_found.json()["success"] is False

        # 3. Stripe webhook với chữ ký sai -> 400
        with patch.object(PaymentService, "verify_stripe_signature", return_value=False):
            stripe_bad_sig = await client.post(
                "/api/payments/webhook/stripe",
                content=b'{"type": "checkout.session.completed"}',
                headers={"Content-Type": "application/json", "Stripe-Signature": "invalid"},
            )
            assert stripe_bad_sig.status_code == 400

        # 4. Stripe webhook với JSON lỗi -> 400
        stripe_bad_json = await client.post(
            "/api/payments/webhook/stripe",
            content=b"invalid-json-body",
            headers={"Content-Type": "application/json"},
        )
        assert stripe_bad_json.status_code == 400

        # 5. Stripe webhook với sự kiện checkout.session.completed thành công
        stripe_event = {
            "id": f"evt_test_{int(time.time())}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(order["id"]),
                    "payment_intent": f"pi_test_{int(time.time())}",
                    "amount_total": order["final_amount"],
                }
            },
        }
        stripe_ok = await client.post(
            "/api/payments/webhook/stripe",
            json=stripe_event,
        )
        assert stripe_ok.status_code == 200
        assert stripe_ok.json()["received"] is True

        # Đơn hàng phải chuyển sang paid
        check_order = await client.get(
            f"/api/payments/orders/{order['id']}",
            headers=auth_headers,
        )
        assert check_order.json()["status"] == "paid"

        # 6. VietQR webhook không tìm thấy đơn -> success: False
        vqr_fail = await client.post(
            "/api/payments/webhook/vietqr",
            json={"content": "NO_ORDER_CONTENT_HERE", "transferAmount": 50000},
        )
        assert vqr_fail.status_code == 200
        assert vqr_fail.json()["success"] is False


@pytest.mark.asyncio
async def test_payment_service_methods_direct():
    """Unit test trực tiếp các phương thức tiện ích của PaymentService."""
    async with AsyncSessionLocal() as db:
        # 1. verify signature helpers
        assert PaymentService.verify_payos_signature({}, "") is True
        assert PaymentService.verify_stripe_signature(b"{}", "") is True

        # 2. generate_vietqr_url
        qr_url = PaymentService.generate_vietqr_url(
            bank_id="MB",
            account_no="0333888999",
            amount=50000,
            transfer_content="VOX12345",
            account_name="VOXIFY",
        )
        assert "MB" in qr_url
        assert "0333888999" in qr_url

        # 3. get_plan_by_code
        plan = await PaymentService.get_plan_by_code(db, "credit_100k")
        assert plan is not None
        plan_none = await PaymentService.get_plan_by_code(db, "non_existent_code")
        assert plan_none is None

        # 4. get_order_by_id_or_code
        assert await PaymentService.get_order_by_id_or_code(db, "KHONG_CO") is None

        # 5. process_card_payment với số thẻ không phải số
        with pytest.raises(AppError):
            await PaymentService.process_card_payment(
                db=db,
                order_id=1,
                user_id=1,
                card_number="abcd-efgh-ijkl",
                exp_month="12",
                exp_year="28",
                cvc="123",
                cardholder_name="TEST",
            )

        # 6. verify_card_otp khi đơn không có metadata
        stmt_order = select(Order).where(Order.status == OrderStatus.PENDING.value).limit(1)
        res_order = await db.execute(stmt_order)
        pending_order = res_order.scalar_one_or_none()
        if pending_order:
            with pytest.raises(AppError):
                await PaymentService.verify_card_otp(db, pending_order.id, pending_order.user_id, "123456")

        # 7. create_order với gói không hợp lệ
        dummy_user = User(id=999, email="dummy@example.com")
        with pytest.raises(AppError):
            await PaymentService.create_order(db, dummy_user, plan_id=999999, payment_method="vietqr")

        # 8. create_order với gói PayOS và Stripe
        if plan:
            order_payos = await PaymentService.create_order(db, dummy_user, plan_id=plan.id, payment_method="payos")
            assert order_payos.payment_method == "payos"
            assert order_payos.checkout_url is not None

            order_stripe = await PaymentService.create_order(db, dummy_user, plan_id=plan.id, payment_method="stripe")
            assert order_stripe.payment_method == "stripe"
            assert order_stripe.checkout_url is not None


@pytest.mark.asyncio
async def test_payment_deep_coverage_boost():
    """Bổ sung test sâu các nhánh lỗi và edge cases để bảo đảm coverage >= 80%."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token_u1, u1_id = await register_and_login(client, "deep_u1")
        token_u2, _ = await register_and_login(client, "deep_u2")
        h1 = {"Authorization": f"Bearer {token_u1}"}
        h2 = {"Authorization": f"Bearer {token_u2}"}

        plans_res = await client.get("/api/payments/plans")
        pack = next(p for p in plans_res.json() if p["price"] > 0)

        # 1. simulate_sandbox_payment errors
        # - not found
        sim_nf = await client.post("/api/payments/sandbox/simulate-payment", headers=h1, json={"order_id": 999999})
        assert sim_nf.status_code == 404

        # Tạo 1 order của U1
        order_res = await client.post("/api/payments/orders", headers=h1, json={"plan_id": pack["id"], "payment_method": "vietqr"})
        o1 = order_res.json()

        # - forbidden (U2 thao tác trên order của U1)
        sim_forbid = await client.post("/api/payments/sandbox/simulate-payment", headers=h2, json={"order_id": o1["id"]})
        assert sim_forbid.status_code == 403

        # 2. download_receipt errors
        # - not found
        rc_nf = await client.get("/api/payments/orders/999999/receipt", headers=h1)
        assert rc_nf.status_code == 404

        # - forbidden
        rc_forbid = await client.get(f"/api/payments/orders/{o1['id']}/receipt", headers=h2)
        assert rc_forbid.status_code == 403

        # 3. cancel_order errors
        # - cancel not found
        can_nf = await client.post("/api/payments/orders/999999/cancel", headers=h1)
        assert can_nf.status_code == 404

        # - cancel forbidden
        can_forbid = await client.post(f"/api/payments/orders/{o1['id']}/cancel", headers=h2)
        assert can_forbid.status_code == 403

        # 4. resend_card_otp errors & verify_card_otp errors via API
        # - resend not found
        res_nf = await client.post("/api/payments/orders/999999/resend-otp", headers=h1)
        assert res_nf.status_code == 404

        # - resend forbidden
        res_forbid = await client.post(f"/api/payments/orders/{o1['id']}/resend-otp", headers=h2)
        assert res_forbid.status_code == 403

        # - verify not found
        v_nf = await client.post("/api/payments/orders/999999/verify-otp", headers=h1, json={"otp": "123456"})
        assert v_nf.status_code == 404

        # - verify forbidden
        v_forbid = await client.post(f"/api/payments/orders/{o1['id']}/verify-otp", headers=h2, json={"otp": "123456"})
        assert v_forbid.status_code == 403

        # 5. create_order validation errors
        # - invalid coupon code
        bad_cp = await client.post(
            "/api/payments/orders",
            headers=h1,
            json={"plan_id": pack["id"], "payment_method": "vietqr", "coupon_code": "INVALID_COUPON_CODE"},
        )
        assert bad_cp.status_code == 400

        # - free plan (price = 0)
        async with AsyncSessionLocal() as db:
            from app.models.payment import PricingPlan
            free_plan = PricingPlan(
                code=f"free_test_{int(time.time() * 100)}",
                name="Gói 0đ Miễn Phí Test",
                type="subscription",
                price=0,
                currency="VND",
                credits=1000,
                duration_days=30,
                storage_days=7,
                is_active=True,
            )
            db.add(free_plan)
            await db.commit()
            await db.refresh(free_plan)
            free_plan_id = free_plan.id

        free_order_res = await client.post(
            "/api/payments/orders",
            headers=h1,
            json={"plan_id": free_plan_id, "payment_method": "vietqr"},
        )
        assert free_order_res.status_code == 400
        assert "miễn phí" in free_order_res.json()["error"]["message"]

        # 6. Service level edge cases
        async with AsyncSessionLocal() as db:
            # - seed_defaults_if_empty idempotency
            await PaymentService.seed_defaults_if_empty(db)
            await PaymentService.seed_defaults_if_empty(db)

            # - list_plans with only_active=False
            all_plans = await PaymentService.list_plans(db, only_active=False)
            assert len(all_plans) > 0

            # - get_plan_by_id None
            assert await PaymentService.get_plan_by_id(db, 999999) is None

            # - cancel already paid order
            paid_order = await PaymentService.get_order_by_id_or_code(db, o1["id"])
            if paid_order:
                paid_order.status = OrderStatus.PAID.value
                await db.commit()
                with pytest.raises(AppError):
                    await PaymentService.cancel_order(db, paid_order.id, paid_order.user_id)
                with pytest.raises(AppError):
                    await PaymentService.resend_card_otp(db, paid_order.id, paid_order.user_id)

            # - verify_card_otp on expired OTP
            order_expired_otp = Order(
                order_code=f"VOX_EXP_{int(time.time() * 1000)}",
                order_number=int(time.time() * 1000),
                user_id=u1_id,
                original_amount=50000,
                discount_amount=0,
                final_amount=50000,
                credits_to_add=50000,
                status=OrderStatus.PENDING.value,
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
                metadata_json=json.dumps({
                    "requires_otp": True,
                    "otp_code": "123456",
                    "otp_expires_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
                }),
            )
            db.add(order_expired_otp)
            await db.commit()
            await db.refresh(order_expired_otp)

            with pytest.raises(AppError, match="hết hạn"):
                await PaymentService.verify_card_otp(db, order_expired_otp.id, u1_id, "123456")

            # - verify_card_otp when requires_otp is False
            order_expired_otp.metadata_json = json.dumps({"requires_otp": False})
            await db.commit()
            with pytest.raises(AppError, match="không yêu cầu"):
                await PaymentService.verify_card_otp(db, order_expired_otp.id, u1_id, "123456")

            # - create_plan duplicate code -> 400
            with pytest.raises(AppError, match="tồn tại"):
                await PaymentService.create_plan(db, {"code": pack["code"], "name": "Dup", "price": 1000, "credits": 1000})

            # - coupon edge cases
            cp_inactive = Coupon(
                code=f"INACT_{int(time.time()*1000)}",
                discount_type="fixed",
                discount_value=1000,
                is_active=False,
            )
            cp_exp = Coupon(
                code=f"EXP_{int(time.time()*1000)}",
                discount_type="fixed",
                discount_value=1000,
                expires_at=datetime.now(UTC) - timedelta(days=1),
                is_active=True,
            )
            cp_used = Coupon(
                code=f"USED_{int(time.time()*1000)}",
                discount_type="fixed",
                discount_value=1000,
                max_uses=1,
                used_count=1,
                is_active=True,
            )
            cp_min = Coupon(
                code=f"MIN_{int(time.time()*1000)}",
                discount_type="fixed",
                discount_value=1000,
                min_order_amount=100000,
                is_active=True,
            )
            db.add_all([cp_inactive, cp_exp, cp_used, cp_min])
            await db.commit()

            c, d, m = await PaymentService.validate_coupon(db, cp_inactive.code, 50000)
            assert c is None and "tạm ngừng" in m

            c, d, m = await PaymentService.validate_coupon(db, cp_exp.code, 50000)
            assert c is None and "hết hạn" in m

            c, d, m = await PaymentService.validate_coupon(db, cp_used.code, 50000)
            assert c is None and "hết lượt" in m

            c, d, m = await PaymentService.validate_coupon(db, cp_min.code, 50000)
            assert c is None and "tối thiểu" in m

            # - underpaid payment -> OrderStatus.FAILED
            underpaid_order = Order(
                order_code=f"VOX_UNDER_{int(time.time() * 1000)}",
                order_number=int(time.time() * 1000),
                user_id=u1_id,
                original_amount=50000,
                discount_amount=0,
                final_amount=50000,
                credits_to_add=50000,
                status=OrderStatus.PENDING.value,
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
            db.add(underpaid_order)
            await db.commit()
            await db.refresh(underpaid_order)

            res_ord, processed = await PaymentService.process_successful_payment(
                db=db,
                order=underpaid_order,
                gateway="vietqr",
                transaction_id=f"tx_under_{int(time.time()*1000)}",
                paid_amount=10000,
            )
            assert res_ord.status == OrderStatus.FAILED.value
            assert processed is False

            # - list_user_orders pagination
            orders, total_orders = await PaymentService.list_user_orders(db, user_id=u1_id, page=1, limit=5)
            assert total_orders >= 1

        # 7. Signature verification logic
        import hashlib
        import hmac
        with patch("app.services.payment_service.get_settings") as mock_set:
            mock_set.return_value.payos_checksum_key = "secret_key"
            p_data = {"amount": 50000, "orderCode": 12345}
            q_str = "amount=50000&orderCode=12345"
            sig = hmac.new(b"secret_key", q_str.encode("utf-8"), hashlib.sha256).hexdigest()
            assert PaymentService.verify_payos_signature(p_data, sig) is True
            assert PaymentService.verify_payos_signature(p_data, "bad_sig") is False

        with patch("app.services.payment_service.get_settings") as mock_set:
            mock_set.return_value.stripe_webhook_secret = "whsec_test"
            s_payload = b'{"id": "evt_test"}'
            t = str(int(time.time()))
            signed_payload = f"{t}.".encode("utf-8") + s_payload
            v1 = hmac.new(b"whsec_test", signed_payload, hashlib.sha256).hexdigest()
            assert PaymentService.verify_stripe_signature(s_payload, f"t={t},v1={v1}") is True
            assert PaymentService.verify_stripe_signature(s_payload, f"t={t},v1=bad") is False
            assert PaymentService.verify_stripe_signature(s_payload, "malformed") is False





