"""Unit and integration tests for Affiliate Program (Issue #14 / Prompt 12)."""
import time
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.db import AsyncSessionLocal
from app.main import app
from app.models.admin import SecurityViolationLog
from app.models.affiliate import (
    AffiliateClick,
    AffiliateCommission,
    CommissionStatus,
)
from app.models.payment import Order, OrderStatus, PaymentMethod
from app.models.user import User
from app.services.affiliate_service import AffiliateService, mask_email, normalize_email_for_anti_fraud
from app.services.payment_service import PaymentService


def unique_email(prefix: str = "aff_test") -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}@example.com"


def unique_code(prefix: str = "REF") -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


@pytest.mark.asyncio
async def test_mask_email_and_normalize_email():
    """Kiểm tra logic che giấu email và chuẩn hóa chống gian lận."""
    assert mask_email("hoang@gmail.com") == "h***g@gmail.com"
    assert mask_email("ab@domain.com") == "a*@domain.com"
    assert mask_email("user.name@yahoo.com") == "u*******e@yahoo.com"
    assert mask_email("invalid") == "***"

    # Normalize Gmail aliases
    assert normalize_email_for_anti_fraud("user+123@gmail.com") == "user@gmail.com"
    assert normalize_email_for_anti_fraud("u.s.e.r@gmail.com") == "user@gmail.com"
    assert normalize_email_for_anti_fraud("test@customdomain.com") == "test@customdomain.com"


@pytest.mark.asyncio
async def test_affiliate_tracking_and_cookie():
    """Kiểm tra endpoint track lượt click link affiliate và thiết lập cookie 30 ngày."""
    ref_code = unique_code("TRACK")
    async with AsyncSessionLocal() as db:
        user = User(
            email=unique_email("referrer_track"),
            hashed_password=hash_password("Password123!"),
            referral_code=ref_code,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Track mã hợp lệ
        res = await client.post(f"/api/affiliate/track?ref={ref_code}", headers={"User-Agent": "Mozilla/5.0 TestBrowser"})
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["referral_code"] == ref_code
        assert "voxify_ref" in res.cookies

        # 2. Kiểm tra click được lưu trong database
        async with AsyncSessionLocal() as db:
            clicks = (await db.execute(select(AffiliateClick).where(AffiliateClick.referral_code == ref_code))).scalars().all()
            assert len(clicks) == 1
            assert clicks[0].user_agent == "Mozilla/5.0 TestBrowser"

        # 3. Track mã không tồn tại
        res_fail = await client.post("/api/affiliate/track?ref=NONEXISTENT999")
        assert res_fail.status_code == 200
        assert res_fail.json()["success"] is False


@pytest.mark.asyncio
async def test_registration_with_referral_code_and_cookie():
    """Kiểm tra đăng ký tài khoản có gắn referrer qua body hoặc cookie."""
    ref_code = unique_code("PARTNER")
    async with AsyncSessionLocal() as db:
        ref_user = User(
            email=unique_email("partner_user"),
            hashed_password=hash_password("Password123!"),
            referral_code=ref_code,
            registration_ip="192.168.1.100",
            device_fingerprint="fp-device-partner",
            is_active=True,
            is_verified=True,
        )
        db.add(ref_user)
        await db.commit()
        await db.refresh(ref_user)
        ref_user_id = ref_user.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Đăng ký với ref_code qua body
        buyer_email = unique_email("buyer_referral")
        reg_payload = {
            "email": buyer_email,
            "password": "SecurePassword123!",
            "full_name": "Referred Buyer",
            "ref_code": ref_code,
        }
        res_reg = await client.post("/api/auth/register", json=reg_payload)
        assert res_reg.status_code == 200
        buyer_data = res_reg.json()
        assert buyer_data["email"] == buyer_email
        assert buyer_data["referred_by_id"] == ref_user_id
        assert buyer_data["referral_code"] is not None  # Người dùng mới cũng tự động có mã giới thiệu riêng


@pytest.mark.asyncio
async def test_anti_fraud_mechanisms():
    """Kiểm tra các cơ chế chống gian lận (Anti-fraud Requirement #5)."""
    ref_code = unique_code("FRAUD")
    main_email = unique_email("hoang_affiliate")
    async with AsyncSessionLocal() as db:
        referrer = User(
            email=main_email,
            hashed_password=hash_password("Password123!"),
            referral_code=ref_code,
            registration_ip="10.20.30.40",
            device_fingerprint="device-fp-unique-123",
            is_active=True,
            is_verified=True,
        )
        db.add(referrer)
        await db.commit()
        await db.refresh(referrer)

    # 1. Tự giới thiệu chính mình (trùng email hoặc alias)
    async with AsyncSessionLocal() as db:
        # Giả lập candidate email alias:
        local, domain = main_email.split("@")
        candidate_alias = f"{local}+clone1@{domain}"
        valid_email, reason_email = await AffiliateService.validate_referral_anti_fraud(
            db=db,
            referrer=referrer,
            candidate_email=candidate_alias,
            client_ip="11.22.33.44",
            device_fingerprint="different-device",
        )
        assert valid_email is False
        assert "trùng với người giới thiệu" in reason_email

    # 2. Tự giới thiệu từ cùng địa chỉ IP
    async with AsyncSessionLocal() as db:
        valid_ip, reason_ip = await AffiliateService.validate_referral_anti_fraud(
            db=db,
            referrer=referrer,
            candidate_email=unique_email("different_person"),
            client_ip="10.20.30.40",  # Trùng registration_ip của referrer
            device_fingerprint="different-device",
        )
        assert valid_ip is False
        assert "địa chỉ IP" in reason_ip

    # 3. Tự giới thiệu từ cùng thiết bị (device fingerprint)
    async with AsyncSessionLocal() as db:
        valid_dev, reason_dev = await AffiliateService.validate_referral_anti_fraud(
            db=db,
            referrer=referrer,
            candidate_email=unique_email("another_friend"),
            client_ip="55.66.77.88",
            device_fingerprint="device-fp-unique-123",  # Trùng device fingerprint
        )
        assert valid_dev is False
        assert "vân tay thiết bị" in reason_dev

    # Kiểm tra log vi phạm an ninh SecurityViolationLog
    async with AsyncSessionLocal() as db:
        logs = (await db.execute(select(SecurityViolationLog).where(SecurityViolationLog.user_id == referrer.id))).scalars().all()
        assert len(logs) >= 3


@pytest.mark.asyncio
async def test_order_commission_lifecycle_pending_settle_refund():
    """Kiểm tra toàn bộ vòng đời hoa hồng: thanh toán -> pending -> settle approved -> refund thu hồi."""
    ref_code = unique_code("LIFE")
    order_code = f"ORD_AFF_{int(time.time() * 1000)}"
    order_num = int(time.time() * 1000) % 1000000000

    async with AsyncSessionLocal() as db:
        referrer = User(
            email=unique_email("partner_lifecycle"),
            hashed_password=hash_password("Password123!"),
            referral_code=ref_code,
            is_active=True,
            is_verified=True,
        )
        db.add(referrer)
        await db.flush()

        buyer = User(
            email=unique_email("buyer_lifecycle"),
            hashed_password=hash_password("Password123!"),
            referred_by_id=referrer.id,
            is_active=True,
            is_verified=True,
        )
        db.add(buyer)
        await db.flush()

        order = Order(
            order_code=order_code,
            order_number=order_num,
            user_id=buyer.id,
            original_amount=249000,
            discount_amount=0,
            final_amount=249000,
            credits_to_add=500000,
            payment_method=PaymentMethod.VIETQR.value,
            status=OrderStatus.PENDING.value,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)
        order_id = order.id
        referrer_id = referrer.id

    # 1. Giả lập đơn hàng được thanh toán thành công qua PaymentService
    async with AsyncSessionLocal() as db:
        res_order = await db.get(Order, order_id)
        assert res_order is not None
        await PaymentService.process_successful_payment(
            db=db,
            order=res_order,
            gateway="vietqr",
            transaction_id=f"tx_test_{order_num}",
            paid_amount=249000,
        )

    # 2. Kiểm tra hoa hồng được tạo tự động với trạng thái PENDING
    async with AsyncSessionLocal() as db:
        comm = (await db.execute(select(AffiliateCommission).where(AffiliateCommission.order_id == order_id))).scalar_one_or_none()
        assert comm is not None
        assert comm.affiliate_user_id == referrer_id
        assert comm.status == CommissionStatus.PENDING.value
        # Mặc định 25% của 249.000 = 62.250 VND
        assert comm.amount == 62250
        h_utc = comm.hold_until if comm.hold_until.tzinfo else comm.hold_until.replace(tzinfo=UTC)
        assert h_utc > datetime.now(UTC)

    # 3. Giả lập hết 14 ngày hold -> Quyết toán sang APPROVED
    async with AsyncSessionLocal() as db:
        comm = (await db.execute(select(AffiliateCommission).where(AffiliateCommission.order_id == order_id))).scalar_one()
        # Tua ngược thời gian hold_until
        comm.hold_until = datetime.now(UTC) - timedelta(days=1)
        await db.commit()

        settled_count = await AffiliateService.settle_pending_commissions(db)
        assert settled_count >= 1

        await db.refresh(comm)
        assert comm.status == CommissionStatus.APPROVED.value
        assert comm.approved_at is not None

    # 4. Khi đơn hàng bị refund / hủy -> Thu hồi hoa hồng
    async with AsyncSessionLocal() as db:
        await PaymentService.refund_order(db=db, order_id=order_id, reason="Customer chargeback")
        comm = (await db.execute(select(AffiliateCommission).where(AffiliateCommission.order_id == order_id))).scalar_one()
        assert comm.status == CommissionStatus.CANCELLED.value
        assert comm.cancel_reason == "Customer chargeback"
        assert comm.cancelled_at is not None


@pytest.mark.asyncio
async def test_affiliate_dashboard_and_withdrawals_flow():
    """Kiểm tra Dashboard thống kê và luồng gửi yêu cầu rút tiền (Withdrawal Flow)."""
    boss_code = unique_code("BOSS")
    async with AsyncSessionLocal() as db:
        user = User(
            email=unique_email("affiliate_boss"),
            hashed_password=hash_password("Password123!"),
            referral_code=boss_code,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    token = create_access_token({"sub": str(user_id), "email": user.email, "role": "user"})
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Lấy thông tin Dashboard khi mới tạo
        res_dash = await client.get("/api/affiliate/dashboard", headers=headers)
        assert res_dash.status_code == 200
        dash_data = res_dash.json()
        assert dash_data["referral_code"] == boss_code
        assert dash_data["stats"]["available_commission"] == 0

        # 2. Tùy chỉnh mã giới thiệu
        new_custom_code = unique_code("STAR")
        res_code = await client.put("/api/affiliate/code", headers=headers, json={"referral_code": new_custom_code})
        assert res_code.status_code == 200
        assert res_code.json()["referral_code"] == new_custom_code

        # 3. Tạo 1 hoa hồng đã duyệt trị giá 500.000 VND
        async with AsyncSessionLocal() as db:
            buyer = User(email=unique_email("buyer_boss"), hashed_password=hash_password("pass123"), is_active=True)
            db.add(buyer)
            await db.flush()

            dummy_order = Order(
                order_code=f"ORD_BOSS_{int(time.time() * 1000)}",
                order_number=int(time.time() * 1000) % 1000000000,
                user_id=buyer.id,
                original_amount=2000000,
                final_amount=2000000,
                credits_to_add=2000000,
                payment_method=PaymentMethod.VIETQR.value,
                status=OrderStatus.PAID.value,
                expires_at=datetime.now(UTC),
            )
            db.add(dummy_order)
            await db.flush()

            comm = AffiliateCommission(
                affiliate_user_id=user_id,
                referred_user_id=buyer.id,
                order_id=dummy_order.id,
                order_amount=2000000,
                commission_rate=0.25,
                amount=500000,
                status=CommissionStatus.APPROVED.value,
                hold_until=datetime.now(UTC) - timedelta(days=1),
                approved_at=datetime.now(UTC),
            )
            db.add(comm)
            await db.commit()

        # 4. Kiểm tra lại Dashboard -> available_commission = 500.000 VNĐ
        res_dash2 = await client.get("/api/affiliate/dashboard", headers=headers)
        assert res_dash2.status_code == 200
        assert res_dash2.json()["stats"]["available_commission"] == 500000
        assert len(res_dash2.json()["commissions"]) == 1

        # 5. Rút tiền vượt quá số dư khả dụng (vd: 600.000 VNĐ) -> Lỗi 400
        res_over = await client.post(
            "/api/affiliate/withdraw",
            headers=headers,
            json={
                "amount": 600000,
                "bank_name": "Vietcombank",
                "bank_account_number": "1234567890",
                "bank_account_holder": "TRAN VAN BOSS",
            },
        )
        assert res_over.status_code == 400

        # 6. Rút tiền dưới mức tối thiểu 200.000 VNĐ (vd: 50.000 VNĐ) -> Lỗi 400
        res_min = await client.post(
            "/api/affiliate/withdraw",
            headers=headers,
            json={
                "amount": 50000,
                "bank_name": "Vietcombank",
                "bank_account_number": "1234567890",
                "bank_account_holder": "TRAN VAN BOSS",
            },
        )
        assert res_min.status_code == 400

        # 7. Rút tiền hợp lệ 300.000 VNĐ
        res_w = await client.post(
            "/api/affiliate/withdraw",
            headers=headers,
            json={
                "amount": 300000,
                "bank_name": "Vietcombank",
                "bank_account_number": "1234567890",
                "bank_account_holder": "TRAN VAN BOSS",
            },
        )
        assert res_w.status_code == 201
        w_data = res_w.json()
        assert w_data["amount"] == 300000
        assert w_data["status"] == "pending"
        w_id = w_data["id"]

        # Số dư khả dụng còn lại phải là 500.000 - 300.000 = 200.000 VNĐ
        res_dash3 = await client.get("/api/affiliate/dashboard", headers=headers)
        assert res_dash3.json()["stats"]["available_commission"] == 200000

        # 8. Xem danh sách lịch sử rút tiền
        res_w_list = await client.get("/api/affiliate/withdrawals", headers=headers)
        assert res_w_list.status_code == 200
        assert len(res_w_list.json()) == 1

        # 9. Admin duyệt rút tiền -> available_commission vẫn là 200.000, withdrawn_commission tăng lên 300.000
        async with AsyncSessionLocal() as db:
            admin_user = User(
                email=unique_email("admin_aff"),
                hashed_password=hash_password("adminpass123"),
                role="admin",
                is_admin=True,
                is_active=True,
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            admin_id = admin_user.id

        admin_token = create_access_token({"sub": str(admin_id), "email": admin_user.email, "role": "admin"})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        res_approve = await client.post(
            f"/api/admin/affiliates/withdrawals/{w_id}/approve",
            headers=admin_headers,
            json={"note": "Đã chuyển khoản qua VCB thành công"},
        )
        assert res_approve.status_code == 200

        res_dash4 = await client.get("/api/affiliate/dashboard", headers=headers)
        assert res_dash4.json()["stats"]["withdrawn_commission"] == 300000
        assert res_dash4.json()["stats"]["available_commission"] == 200000
