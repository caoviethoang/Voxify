"""Unit tests cho Dashboard stats API (Issue #9)."""
import time
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db import AsyncSessionLocal
from app.models.generation import Generation


@pytest.mark.asyncio
async def test_dashboard_stats():
    """Kiểm tra endpoint /api/dashboard/stats trả về dữ liệu thống kê chính xác."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Đăng ký & đăng nhập
        email = f"dashboard_test_{time.time()}@example.com"
        reg = await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Dashboard Tester",
        })
        assert reg.status_code == 200
        user_id = reg.json()["id"]

        login = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Khi chưa có generation nào: stats rỗng nhưng hợp lệ
        res_empty = await client.get("/api/dashboard/stats", headers=headers)
        assert res_empty.status_code == 200
        data_empty = res_empty.json()
        assert data_empty["chars_used_this_month"] == 0
        assert data_empty["total_audio_generated"] == 0
        assert data_empty["total_duration_seconds"] == 0.0
        assert data_empty["credit_balance"] == 10000
        assert data_empty["latest_generation"] is None
        assert data_empty["recent_activities"] == []

        # 3. Tạo 2 generation mẫu
        async with AsyncSessionLocal() as db:
            gen1 = Generation(
                user_id=user_id,
                text="Đoạn văn bản đầu tiên cho dashboard",
                voice="vi-VN-HoaiMyNeural",
                char_count=35,
                duration=10.5,
                status="done",
                progress=100,
                credit_used=35,
                is_preview=False,
            )
            gen2 = Generation(
                user_id=user_id,
                text="Đoạn văn bản thứ hai cho dashboard",
                voice="vi-VN-NamMinhNeural",
                char_count=34,
                duration=8.0,
                status="done",
                progress=100,
                credit_used=34,
                is_preview=False,
            )
            db.add_all([gen1, gen2])
            await db.commit()

        # 4. Kiểm tra lại stats sau khi tạo audio
        res_populated = await client.get("/api/dashboard/stats", headers=headers)
        assert res_populated.status_code == 200
        data = res_populated.json()
        assert data["chars_used_this_month"] == 69
        assert data["total_audio_generated"] == 2
        assert data["total_duration_seconds"] == 18.5
        assert len(data["recent_activities"]) == 2
        assert data["latest_generation"] is not None
        assert "Đoạn văn bản" in data["latest_generation"]["text"]
