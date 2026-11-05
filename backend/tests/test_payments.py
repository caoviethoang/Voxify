"""Kiểm thử tính năng Thanh toán & Gói dịch vụ (VietQR / PayOS / Stripe) và Idempotency."""
import time
from typing import Tuple

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.main import app
from app.models.credit import CreditTransaction


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
        pack = plans_res.json()[0]

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

