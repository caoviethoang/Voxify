"""Unit and integration tests for History API (Issue #8)."""
import time

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db import AsyncSessionLocal
from app.main import app
from app.models.generation import Generation
from app.routes.history import cleanup_old_generations


@pytest.mark.asyncio
async def test_history_crud_and_filters(tmp_path):
    """Kiểm tra toàn bộ luồng GET, PATCH, DELETE, DELETE bulk của History API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Đăng ký và đăng nhập người dùng
        email = f"history_test_{time.time()}@example.com"
        reg = await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "History Test User",
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

        # 2. Tạo một số Generation mẫu trong DB
        test_file = tmp_path / "sample.mp3"
        test_file.write_bytes(b"dummy audio content")

        async with AsyncSessionLocal() as db:
            gen1 = Generation(
                user_id=user_id,
                text="Bài thuyết trình về Trí tuệ nhân tạo thế hệ mới",
                voice="vi-VN-HoaiMyNeural",
                char_count=46,
                file_path=str(test_file),
                format="mp3",
                duration=12.5,
                status="done",
                progress=100,
                credit_used=46,
                is_preview=False,
            )
            gen2 = Generation(
                user_id=user_id,
                text="Bản tin tài chính chứng khoán tuần này",
                voice="vi-VN-NamMinhNeural",
                char_count=38,
                format="wav",
                duration=8.0,
                status="done",
                progress=100,
                credit_used=38,
                is_preview=False,
            )
            gen_preview = Generation(
                user_id=user_id,
                text="Đoạn nghe thử 200 ký tự đầu",
                voice="vi-VN-HoaiMyNeural",
                char_count=27,
                format="mp3",
                status="done",
                is_preview=True,
            )
            db.add_all([gen1, gen2, gen_preview])
            await db.commit()
            await db.refresh(gen1)
            await db.refresh(gen2)
            gen1_id = gen1.id
            gen2_id = gen2.id

        # 3. Test GET /api/history (mặc định không lấy is_preview)
        res = await client.get("/api/history", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["title"] is not None

        # 4. Test Lọc theo search
        res_search = await client.get("/api/history?search=Trí tuệ", headers=headers)
        assert res_search.status_code == 200
        assert res_search.json()["total"] == 1
        assert res_search.json()["items"][0]["id"] == gen1_id

        # 5. Test Lọc theo format
        res_format = await client.get("/api/history?format=wav", headers=headers)
        assert res_format.status_code == 200
        assert res_format.json()["total"] == 1
        assert res_format.json()["items"][0]["id"] == gen2_id

        # 6. Test PATCH /api/history/{id} (sửa tiêu đề)
        res_patch = await client.patch(
            f"/api/history/{gen1_id}",
            headers=headers,
            json={"title": "Tiêu đề mới cho AI Podcast"},
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["title"] == "Tiêu đề mới cho AI Podcast"

        # 7. Test DELETE /api/history/{id}
        res_del = await client.delete(f"/api/history/{gen1_id}", headers=headers)
        assert res_del.status_code == 200
        assert res_del.json()["deleted"] == 1
        # File vật lý cũng đã được xóa
        assert not test_file.exists()

        # 8. Test DELETE /api/history/bulk
        res_bulk = await client.request(
            "DELETE",
            "/api/history/bulk",
            headers=headers,
            json={"ids": [gen2_id]},
        )
        assert res_bulk.status_code == 200
        assert res_bulk.json()["deleted"] == 1

        # Kiểm tra lại DB sau khi xóa
        res_after = await client.get("/api/history", headers=headers)
        assert res_after.json()["total"] == 0


@pytest.mark.asyncio
async def test_cleanup_old_generations():
    """Kiểm tra hàm dọn dẹp các bản ghi preview cũ."""
    from datetime import datetime, timedelta, timezone

    async with AsyncSessionLocal() as db:
        unique_suffix = str(time.time())
        old_preview = Generation(
            user_id=None,
            text=f"Old preview text {unique_suffix}",
            voice="vi-VN-HoaiMyNeural",
            char_count=16,
            format="mp3",
            status="done",
            is_preview=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        recent_preview = Generation(
            user_id=None,
            text=f"Recent preview text {unique_suffix}",
            voice="vi-VN-HoaiMyNeural",
            char_count=19,
            format="mp3",
            status="done",
            is_preview=True,
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add_all([old_preview, recent_preview])
        await db.commit()
        await db.refresh(old_preview)
        await db.refresh(recent_preview)
        old_id = old_preview.id
        recent_id = recent_preview.id

        # Chạy cleanup retention 7 ngày
        await cleanup_old_generations(db, retention_days=7)

        # Kiểm tra old_preview đã bị xóa, recent_preview vẫn còn
        stmt = select(Generation).where(Generation.id == old_id)
        res = await db.execute(stmt)
        assert res.scalar_one_or_none() is None

        stmt2 = select(Generation).where(Generation.id == recent_id)
        res2 = await db.execute(stmt2)
        assert res2.scalar_one_or_none() is not None
