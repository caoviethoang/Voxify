"""Kiểm thử toàn diện cho hệ thống Admin Portal (Issue #15)."""
import time
from datetime import UTC, datetime, timedelta
from typing import Tuple

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.db import AsyncSessionLocal
from app.main import app
from app.models.admin import AffiliateWithdrawal
from app.models.generation import Generation
from app.models.payment import Order
from app.models.user import User


async def create_user(client: AsyncClient, role: str = "user") -> Tuple[str, int, str]:
    """Helper tạo user và trả về (token, user_id, email) mà không bị giới hạn rate limit."""
    email = f"{role}_{time.time()}_{id(client)}@example.com"
    password = "Password123!"

    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=f"Test {role.capitalize()}",
            role=role,
            is_active=True,
            is_admin=(role == "admin"),
            is_verified=True,
            credit_balance=50000,
            credits=50000,
        )
        db.add(user)
        await db.flush()
        user_id = user.id
        await db.commit()

    token = create_access_token(data={"sub": str(user_id), "email": email, "role": role})
    return token, user_id, email

@pytest.mark.asyncio
async def test_admin_access_control():
    """Kiểm tra quyền truy cập: user thường bị 403, admin truy cập 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_token, _, _ = await create_user(client, role="user")
        admin_token, _, _ = await create_user(client, role="admin")

        # 1. User thường gọi dashboard -> 403
        res_forbidden = await client.get(
            "/api/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert res_forbidden.status_code == 403

        # 2. Không đăng nhập -> 401
        res_unauth = await client.get("/api/admin/dashboard/stats")
        assert res_unauth.status_code == 401

        # 3. Admin gọi dashboard -> 200
        res_ok = await client.get(
            "/api/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert res_ok.status_code == 200
        data = res_ok.json()
        assert "total_users" in data
        assert "total_jobs" in data
        assert "daily_metrics" in data


@pytest.mark.asyncio
async def test_admin_user_management():
    """Kiểm tra quản lý người dùng: tìm kiếm, chi tiết, chỉnh credit, khóa/mở, đổi quyền, impersonate."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        user_token, target_user_id, target_email = await create_user(client, role="user")
        admin_token, _, _ = await create_user(client, role="admin")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Danh sách user
        res_list = await client.get(
            f"/api/admin/users?page=1&limit=10&query={target_email}",
            headers=admin_headers,
        )
        assert res_list.status_code == 200
        list_data = res_list.json()
        assert list_data["total"] >= 1

        # 2. Chi tiết user
        res_detail = await client.get(
            f"/api/admin/users/{target_user_id}",
            headers=admin_headers,
        )
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert detail_data["email"] == target_email

        # 3. Điều chỉnh credits (+5000 và -1000)
        res_add_credit = await client.post(
            f"/api/admin/users/{target_user_id}/credits",
            headers=admin_headers,
            json={"amount": 5000, "reason": "Tặng credit bù do lỗi mạng"},
        )
        assert res_add_credit.status_code == 200
        assert res_add_credit.json()["new_balance"] >= 5000

        res_sub_credit = await client.post(
            f"/api/admin/users/{target_user_id}/credits",
            headers=admin_headers,
            json={"amount": -1000, "reason": "Thu hồi credit cấp nhầm"},
        )
        assert res_sub_credit.status_code == 200

        # 4. Khóa và mở khóa tài khoản
        res_lock = await client.patch(
            f"/api/admin/users/{target_user_id}/status",
            headers=admin_headers,
            json={"is_active": False, "reason": "Tạm khóa kiểm tra vi phạm"},
        )
        assert res_lock.status_code == 200
        assert res_lock.json()["is_active"] is False

        res_unlock = await client.patch(
            f"/api/admin/users/{target_user_id}/status",
            headers=admin_headers,
            json={"is_active": True, "reason": "Mở lại sau xác minh"},
        )
        assert res_unlock.status_code == 200
        assert res_unlock.json()["is_active"] is True

        # 5. Thay đổi Role (user -> admin -> user)
        res_role_admin = await client.patch(
            f"/api/admin/users/{target_user_id}/role",
            headers=admin_headers,
            json={"role": "admin", "reason": "Thăng cấp quản trị viên"},
        )
        assert res_role_admin.status_code == 200
        assert res_role_admin.json()["role"] == "admin"

        res_role_user = await client.patch(
            f"/api/admin/users/{target_user_id}/role",
            headers=admin_headers,
            json={"role": "user", "reason": "Hạ cấp về user thường"},
        )
        assert res_role_user.status_code == 200
        assert res_role_user.json()["role"] == "user"

        # 6. Impersonate login
        res_impersonate = await client.post(
            f"/api/admin/users/{target_user_id}/impersonate",
            headers=admin_headers,
        )
        assert res_impersonate.status_code == 200
        imp_data = res_impersonate.json()
        assert "access_token" in imp_data
        assert imp_data["user_id"] == target_user_id


@pytest.mark.asyncio
async def test_admin_jobs_management():
    """Kiểm tra quản lý jobs: danh sách, lọc, retry và hoàn tiền thủ công."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        _, user_id, _ = await create_user(client, role="user")
        admin_token, _, _ = await create_user(client, role="admin")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Tạo 1 job giả lập bị lỗi
        async with AsyncSessionLocal() as db:
            job = Generation(
                user_id=user_id,
                text="Văn bản kiểm thử cho admin job test",
                voice="vi-VN-HoaiMyNeural",
                char_count=50,
                credit_used=50,
                status="failed",
                error_message="Lỗi giả lập",
                is_preview=False,
            )
            db.add(job)
            await db.flush()
            job_id = job.id
            await db.commit()

        # 1. Danh sách Jobs
        res_jobs = await client.get(
            "/api/admin/jobs?status=failed&limit=10",
            headers=admin_headers,
        )
        assert res_jobs.status_code == 200
        jobs_data = res_jobs.json()
        assert jobs_data["total"] >= 1

        # 2. Retry Job
        res_retry = await client.post(
            f"/api/admin/jobs/{job_id}/retry",
            headers=admin_headers,
        )
        assert res_retry.status_code == 200
        assert res_retry.json()["status"] == "queued"

        # 3. Hoàn credit thủ công
        res_refund = await client.post(
            f"/api/admin/jobs/{job_id}/refund",
            headers=admin_headers,
        )
        assert res_refund.status_code == 200
        assert res_refund.json()["success"] is True

        # Hoàn lại lần 2 -> 400
        res_refund_again = await client.post(
            f"/api/admin/jobs/{job_id}/refund",
            headers=admin_headers,
        )
        assert res_refund_again.status_code == 400


@pytest.mark.asyncio
async def test_admin_voices_management():
    """Kiểm tra quản lý giọng đọc hệ thống: danh sách, cập nhật multiplier, tier, toggle active."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token, _, _ = await create_user(client, role="admin")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Danh sách giọng
        res_voices = await client.get("/api/admin/voices", headers=admin_headers)
        assert res_voices.status_code == 200
        voices = res_voices.json()
        assert len(voices) > 0
        voice_id = voices[0]["voice_id"]

        # 2. Cập nhật giọng
        res_update = await client.put(
            f"/api/admin/voices/{voice_id}",
            headers=admin_headers,
            json={
                "is_active": True,
                "tier": "premium",
                "credit_multiplier": 1.5,
                "display_name": "Giọng Đặc Biệt",
            },
        )
        assert res_update.status_code == 200
        data = res_update.json()
        assert data["tier"] == "premium"
        assert data["credit_multiplier"] == 1.5


@pytest.mark.asyncio
async def test_admin_business_management():
    """Kiểm tra quản lý kinh doanh: Coupons, Orders, Withdrawals."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        _, user_id, _ = await create_user(client, role="user")
        admin_token, _, _ = await create_user(client, role="admin")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Coupons
        coupon_code = f"SALE{int(time.time())}"
        res_create_coupon = await client.post(
            "/api/admin/coupons",
            headers=admin_headers,
            json={
                "code": coupon_code,
                "discount_percent": 20,
                "max_uses": 50,
                "is_active": True,
            },
        )
        assert res_create_coupon.status_code == 201
        coupon_id = res_create_coupon.json()["id"]

        res_list_coupons = await client.get("/api/admin/coupons", headers=admin_headers)
        assert res_list_coupons.status_code == 200

        res_update_coupon = await client.put(
            f"/api/admin/coupons/{coupon_id}",
            headers=admin_headers,
            json={"discount_percent": 25, "is_active": True},
        )
        assert res_update_coupon.status_code == 200

        # 2. Orders: Tạo 1 order pending và duyệt thủ công
        order_num = int(time.time() * 1000) % 100000000
        async with AsyncSessionLocal() as db:
            order = Order(
                order_code=f"ORD_ADM_{order_num}",
                order_number=order_num,
                user_id=user_id,
                original_amount=100000,
                discount_amount=0,
                final_amount=100000,
                credits_to_add=100000,
                payment_method="vietqr",
                status="pending",
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
            db.add(order)
            await db.flush()
            order_id = order.id
            await db.commit()

        res_list_orders = await client.get("/api/admin/orders?status=pending", headers=admin_headers)
        assert res_list_orders.status_code == 200

        res_approve_order = await client.post(
            f"/api/admin/orders/{order_id}/approve",
            headers=admin_headers,
        )
        assert res_approve_order.status_code == 200
        assert res_approve_order.json()["status"] == "paid"

        # 3. Affiliate Withdrawals
        async with AsyncSessionLocal() as db:
            withdrawal = AffiliateWithdrawal(
                user_id=user_id,
                amount=500000,
                bank_name="Vietcombank",
                bank_account_number="1234567890",
                bank_account_holder="NGUYEN VAN A",
                status="pending",
            )
            db.add(withdrawal)
            await db.flush()
            with_id = withdrawal.id
            await db.commit()

        res_list_w = await client.get("/api/admin/affiliates/withdrawals", headers=admin_headers)
        assert res_list_w.status_code == 200

        res_approve_w = await client.post(
            f"/api/admin/affiliates/withdrawals/{with_id}/approve",
            headers=admin_headers,
            json={"note": "Đã chuyển khoản thành công"},
        )
        assert res_approve_w.status_code == 200
        assert res_approve_w.json()["status"] == "approved"

        # 4. Xóa coupon
        res_del_coupon = await client.delete(f"/api/admin/coupons/{coupon_id}", headers=admin_headers)
        assert res_del_coupon.status_code == 200


@pytest.mark.asyncio
async def test_admin_settings_and_audit_logs():
    """Kiểm tra cấu hình hệ thống động và truy vấn nhật ký kiểm toán (Audit Logs)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        admin_token, _, _ = await create_user(client, role="admin")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Lấy cài đặt hệ thống
        res_settings = await client.get("/api/admin/settings", headers=admin_headers)
        assert res_settings.status_code == 200
        data = res_settings.json()
        assert "tts_provider" in data

        # 2. Cập nhật cài đặt
        res_update_settings = await client.put(
            "/api/admin/settings",
            headers=admin_headers,
            json={
                "settings": {
                    "signup_bonus_credits": "15000",
                    "max_chars": "25000",
                    "maintenance_mode": "false",
                }
            },
        )
        assert res_update_settings.status_code == 200
        assert res_update_settings.json()["success"] is True

        # 3. Kiểm tra Audit Logs và bộ lọc
        res_logs = await client.get("/api/admin/audit-logs?page=1&limit=20", headers=admin_headers)
        assert res_logs.status_code == 200
        logs_data = res_logs.json()
        assert logs_data["total"] > 0
        assert "admin_email" in logs_data["items"][0]
        assert "action" in logs_data["items"][0]

        # Lọc audit log theo action và target_type
        res_filt_log = await client.get("/api/admin/audit-logs?action=update_settings&target_type=system_settings", headers=admin_headers)
        assert res_filt_log.status_code == 200


@pytest.mark.asyncio
async def test_admin_edge_cases_and_error_handling():
    """Kiểm tra các trường hợp ngoại lệ 400, 404 và bộ lọc nâng cao."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        _, user_id, user_email = await create_user(client, role="user")
        admin_token, admin_id, _ = await create_user(client, role="admin")
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Lọc users theo role, is_active, tier
        res_u_filter = await client.get(
            f"/api/admin/users?role=user&is_active=true&tier=free&q={user_email}",
            headers=admin_headers,
        )
        assert res_u_filter.status_code == 200

        # 2. User 404
        assert (await client.get("/api/admin/users/999999", headers=admin_headers)).status_code == 404
        assert (await client.post("/api/admin/users/999999/credits", headers=admin_headers, json={"amount": 100, "reason": "test"})).status_code == 404
        assert (await client.patch("/api/admin/users/999999/status", headers=admin_headers, json={"is_active": False})).status_code == 404
        assert (await client.patch("/api/admin/users/999999/role", headers=admin_headers, json={"role": "admin"})).status_code == 404
        assert (await client.post("/api/admin/users/999999/impersonate", headers=admin_headers)).status_code == 404

        # 3. Job filters và 404
        res_j_filter = await client.get(
            f"/api/admin/jobs?user_id={user_id}&q=kiểm+thử&status=failed",
            headers=admin_headers,
        )
        assert res_j_filter.status_code == 200
        assert (await client.post("/api/admin/jobs/999999/retry", headers=admin_headers)).status_code == 404
        assert (await client.post("/api/admin/jobs/999999/refund", headers=admin_headers)).status_code == 404

        # 4. Coupon edge cases (tạo coupon với fixed discount, duplicate, xóa 404)
        c_code = f"FIXED_{int(time.time())}"
        res_c_fixed = await client.post(
            "/api/admin/coupons",
            headers=admin_headers,
            json={"code": c_code, "discount_amount": 50000, "is_active": True},
        )
        assert res_c_fixed.status_code == 201
        c_id = res_c_fixed.json()["id"]

        # Duplicate coupon
        assert (await client.post(
            "/api/admin/coupons",
            headers=admin_headers,
            json={"code": c_code, "discount_percent": 10},
        )).status_code == 400

        # Update fixed coupon
        res_c_up = await client.put(
            f"/api/admin/coupons/{c_id}",
            headers=admin_headers,
            json={"discount_amount": 60000, "max_uses": 200},
        )
        assert res_c_up.status_code == 200
        assert (await client.put("/api/admin/coupons/999999", headers=admin_headers, json={"max_uses": 10})).status_code == 404
        assert (await client.delete("/api/admin/coupons/999999", headers=admin_headers)).status_code == 404

        # 5. Order 404
        assert (await client.post("/api/admin/orders/999999/approve", headers=admin_headers)).status_code == 404

        # 6. Withdrawal reject và 404
        async with AsyncSessionLocal() as db:
            w_reject = AffiliateWithdrawal(
                user_id=user_id,
                amount=200000,
                bank_name="MBBank",
                bank_account_number="999888777",
                bank_account_holder="TEST REJECT",
                status="pending",
            )
            db.add(w_reject)
            await db.flush()
            w_rej_id = w_reject.id
            await db.commit()

        res_rej = await client.post(
            f"/api/admin/affiliates/withdrawals/{w_rej_id}/reject",
            headers=admin_headers,
            json={"note": "Thông tin tài khoản không hợp lệ"},
        )
        assert res_rej.status_code == 200
        assert res_rej.json()["status"] == "rejected"

        # Thử duyệt hoặc từ chối lại yêu cầu đã xử lý -> 400
        assert (await client.post(f"/api/admin/affiliates/withdrawals/{w_rej_id}/approve", headers=admin_headers, json={})).status_code == 400
        assert (await client.post(f"/api/admin/affiliates/withdrawals/{w_rej_id}/reject", headers=admin_headers, json={})).status_code == 400
        assert (await client.post("/api/admin/affiliates/withdrawals/999999/approve", headers=admin_headers, json={})).status_code == 404
        assert (await client.post("/api/admin/affiliates/withdrawals/999999/reject", headers=admin_headers, json={})).status_code == 404

        # 7. Voices update tắt bật và nhãn tùy biến
        res_voice_deact = await client.put(
            "/api/admin/voices/vi-VN-HoaiMyNeural",
            headers=admin_headers,
            json={"is_active": False, "tier": "free", "credit_multiplier": 1.0, "display_name": "Hoài My (Tắt)"},
        )
        assert res_voice_deact.status_code == 200
        assert res_voice_deact.json()["is_active"] is False

        # Bật lại
        res_voice_act = await client.put(
            "/api/admin/voices/vi-VN-HoaiMyNeural",
            headers=admin_headers,
            json={"is_active": True, "tier": "free", "credit_multiplier": 1.0, "display_name": "Hoài My Chuẩn"},
        )
        assert res_voice_act.status_code == 200
        assert res_voice_act.json()["is_active"] is True
