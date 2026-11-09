"""Pytest configuration and global fixtures for Voxify tests.

NGUYÊN TẮC:
- Mọi test chạy ngoại tuyến hoàn toàn, không gọi provider thật (Edge-TTS, ElevenLabs...).
- Sử dụng FakeTTSProvider cho toàn bộ test tổng hợp giọng nói.
- Tự động thiết lập database và dọn dẹp sau mỗi phiên test.
"""
import asyncio
import os
import time
from typing import AsyncGenerator, Dict

import pytest
from httpx import ASGITransport, AsyncClient

# Thiết lập biến môi trường test trước khi import app
os.environ["TTS_PROVIDER"] = "fake"
os.environ["DEBUG"] = "true"
if os.environ.get("DATABASE_URL") in ("sqlite+aiosqlite:///:memory:", "sqlite:///:memory:"):
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_ci.sqlite"

from pathlib import Path

import app.routes.tts as tts_route
from app.db import AsyncSessionLocal, create_tables
from app.dependencies import get_tts_service
from app.main import app
from app.models.user import User
from app.providers.fake import FakeTTSProvider
from app.services.auth_service import hash_password
from app.services.tts_job_service import TTSJobService
from app.services.tts_service import TTSService


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Đảm bảo bảng và các cột SQLite được khởi tạo và migrate đầy đủ trước khi chạy test."""
    loop = asyncio.new_event_loop()
    loop.run_until_complete(create_tables())
    loop.close()
    yield
    # Dọn dẹp test db nếu dùng test_ci.sqlite
    for test_file in [Path("./test_ci.sqlite"), Path("./test_ci.sqlite-wal"), Path("./test_ci.sqlite-shm")]:
        if test_file.exists():
            try:
                test_file.unlink()
            except Exception:
                pass


@pytest.fixture(autouse=True)
def use_fake_tts(monkeypatch):
    """
    Tự động ghi đè TTSService và TTSJobService bằng FakeTTSProvider
    cho MỌI test để đảm bảo không có request nào ra ngoài internet.
    """
    fake_provider = FakeTTSProvider()
    fake_tts_service = TTSService(provider=fake_provider)

    # Override dependency trong FastAPI
    app.dependency_overrides[get_tts_service] = lambda: fake_tts_service

    # Override _job_service trong route tts
    monkeypatch.setattr(
        tts_route,
        "_job_service",
        TTSJobService(tts_service=fake_tts_service),
    )

    yield fake_provider

    app.dependency_overrides.pop(get_tts_service, None)


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Client bất đồng bộ để gọi API kiểm thử."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_user(async_client: AsyncClient) -> Dict[str, str]:
    """Tạo user thử nghiệm và trả về email, password, token và headers."""
    email = f"user_{time.time()}_{id(async_client)}@example.com"
    password = "UserPassword123!"

    reg_res = await async_client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test Standard User"},
    )
    assert reg_res.status_code == 200
    user_id = reg_res.json()["id"]

    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    return {
        "id": str(user_id),
        "email": email,
        "password": password,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
async def admin_user(async_client: AsyncClient) -> Dict[str, str]:
    """Tạo admin user thử nghiệm và trả về token và headers."""
    email = f"admin_{time.time()}@example.com"
    password = "AdminPassword123!"

    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Test Administrator",
            role="admin",
            is_active=True,
            is_admin=True,
            is_verified=True,
            credit_balance=50000,
            credits=50000,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        admin_id = user.id

    login_res = await async_client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    return {
        "id": str(admin_id),
        "email": email,
        "password": password,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }
