"""Bộ kiểm thử cho Hệ thống Credit (CreditService và API Credits).

Yêu cầu nghiệm thu:
1. Kiểm thử đồng thời 20 request không làm số dư bị âm (Race condition check).
2. Job lỗi thì hoàn lại credit (Reserve & Refund pattern).
3. Đăng ký tài khoản nhận thưởng signup_bonus.
4. Đối soát sổ cái (Ledger total == Cached user balance).
5. API endpoints: /api/credits, /api/credits/transactions, /api/credits/estimate.
"""
import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import AsyncSessionLocal
from app.main import app
from app.models.user import User
from app.services.auth_service import hash_password
from app.services.credit_service import CreditService, InsufficientCreditsError

client = TestClient(app)


@pytest.fixture
def test_user_token():
    """Tạo user thử nghiệm và trả về (user_id, email, access_token)."""
    import time
    email = f"credit_test_{time.time()}@example.com"
    password = "TestPassword123!"

    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Credit Test User"},
    )
    assert reg_res.status_code == 200
    user_id = reg_res.json()["id"]

    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    return user_id, email, token


def test_signup_bonus_granted(test_user_token):
    """Kiểm tra tặng 10.000 credit khi đăng ký tài khoản mới."""
    user_id, email, token = test_user_token
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Kiểm tra API GET /api/credits
    res = client.get("/api/credits", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["balance"] == 10000

    # 2. Kiểm tra sổ cái có giao dịch signup_bonus
    tx_res = client.get("/api/credits/transactions", headers=headers)
    assert tx_res.status_code == 200
    tx_data = tx_res.json()
    assert tx_data["total"] >= 1
    assert any(tx["type"] == "signup_bonus" and tx["amount"] == 10000 for tx in tx_data["items"])


def test_estimate_credits_api():
    """Kiểm tra API ước tính credit theo số ký tự và provider."""
    # 1 ký tự = 1 credit với edge
    res = client.get("/api/credits/estimate?chars=150&provider=edge")
    assert res.status_code == 200
    data = res.json()
    assert data["char_count"] == 150
    assert data["estimated_credits"] == 150

    # Azure multiplier 1.2
    res_azure = client.get("/api/credits/estimate?chars=100&provider=azure")
    assert res_azure.status_code == 200
    assert res_azure.json()["estimated_credits"] == 120


@pytest.mark.asyncio
async def test_reserve_and_refund_flow():
    """Kiểm tra quy trình Reserve và Refund khi job thành công hoặc thất bại."""
    async with AsyncSessionLocal() as db:
        # Tạo test user trực tiếp
        import time
        email = f"reserve_refund_{time.time()}@example.com"
        user = User(
            email=email,
            hashed_password=hash_password("Pass123"),
            full_name="Reserve Refund User",
            credit_balance=0,
            credits=0,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        user_id = user.id
        await CreditService.add_adjustment(db, user_id, 1000, tx_type="purchase", description="Nạp ban đầu")

        # 1. Khấu trừ trước 300 credit
        tx_reserve = await CreditService.reserve(
            db=db,
            user_id=user_id,
            amount=300,
            ref_id="job_001",
            description="TTS 300 ký tự",
        )
        await db.commit()

        balance_after_reserve = await CreditService.get_balance(db, user_id)
        assert balance_after_reserve == 700
        assert tx_reserve.amount == -300
        assert tx_reserve.balance_after == 700

        # 2. Giả lập job gặp lỗi -> Hoàn lại 300 credit
        tx_refund = await CreditService.refund(
            db=db,
            user_id=user_id,
            amount=300,
            ref_id=str(tx_reserve.id),
            reason="Lỗi mạng tổng hợp giọng nói",
        )
        await db.commit()

        balance_after_refund = await CreditService.get_balance(db, user_id)
        assert balance_after_refund == 1000
        assert tx_refund.amount == 300
        assert tx_refund.balance_after == 1000


@pytest.mark.asyncio
async def test_concurrency_race_condition_no_negative_balance():
    """
    NGHIỆM THU: Chạy đồng thời 20 request khấu trừ, đảm bảo số dư không bao giờ bị âm.
    Tài khoản có 1.000 credit. 20 tasks chạy đồng thời, mỗi task trừ 100 credit.
    Kỳ vọng: Đúng 10 task thành công (tổng 1.000 credit), 10 task bị từ chối InsufficientCreditsError.
    Số dư cuối cùng = 0.
    """
    async with AsyncSessionLocal() as db:
        import time
        email = f"concurrency_{time.time()}@example.com"
        user = User(
            email=email,
            hashed_password=hash_password("Pass123"),
            full_name="Concurrency User",
            credit_balance=0,
            credits=0,
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

        # Nạp 1.000 credit vào sổ cái ledger ban đầu
        await CreditService.add_adjustment(
            db=db,
            user_id=user_id,
            amount=1000,
            tx_type="purchase",
            description="Nạp gói thử nghiệm concurrency",
        )

    async def worker(task_idx: int):
        # Mỗi task dùng một DB session độc lập
        async with AsyncSessionLocal() as session:
            try:
                await CreditService.reserve(
                    db=session,
                    user_id=user_id,
                    amount=100,
                    ref_id=f"concurrent_job_{task_idx}",
                )
                await session.commit()
                return "SUCCESS"
            except InsufficientCreditsError:
                await session.rollback()
                return "INSUFFICIENT"
            except Exception as e:
                await session.rollback()
                return f"ERROR: {e}"

    # Chạy 20 task đồng thời
    tasks = [worker(i) for i in range(20)]
    results = await asyncio.gather(*tasks)

    success_count = results.count("SUCCESS")
    insufficient_count = results.count("INSUFFICIENT")

    # Kiểm tra số lượng
    assert success_count == 10, f"Kỳ vọng 10 task thành công, thực tế: {success_count}"
    assert insufficient_count == 10, f"Kỳ vọng 10 task bị từ chối, thực tế: {insufficient_count}"

    # Kiểm tra số dư cuối cùng trong DB
    async with AsyncSessionLocal() as final_session:
        final_balance = await CreditService.get_balance(final_session, user_id)
        assert final_balance == 0, f"Số dư phải là 0, thực tế: {final_balance}"
        assert final_balance >= 0, "Số dư tuyệt đối không được âm"

        # Kiểm tra đối soát sổ cái
        ledger_sum, cached_bal, is_match = await CreditService.verify_ledger(final_session, user_id)
        assert is_match, f"Sổ cái {ledger_sum} và cache {cached_bal} phải khớp nhau"
