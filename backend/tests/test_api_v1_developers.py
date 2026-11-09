"""Unit & Integration tests cho API & Developers (Public API /v1) - Issue #13."""
import asyncio
import hashlib
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.rate_limiter import RateLimiterService
from app.db import AsyncSessionLocal
from app.main import app
from app.models.user import User
from app.services.api_key_service import ApiKeyService
from app.services.tts_job_service import TTSJobService

client = TestClient(app)


@pytest.fixture
def developer_user_token():
    """Tạo user thử nghiệm và trả về (user_id, email, access_token)."""
    email = f"dev_{time.time()}_{id(client)}@example.com"
    password = "DevPassword123!"

    reg_res = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Dev User"},
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


def test_api_key_generation_and_hashing():
    """Kiểm tra quy tắc sinh key: raw key bắt đầu bằng vx_live_, băm SHA-256 an toàn."""
    raw_key, key_prefix, hashed_key = ApiKeyService.generate_key_components()

    assert raw_key.startswith("vx_live_")
    assert len(raw_key) == 8 + 48  # prefix 8 + 48 hex chars
    assert "..." in key_prefix
    assert key_prefix.startswith("vx_live_")

    computed_hash = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
    assert computed_hash == hashed_key
    assert len(hashed_key) == 64


def test_developer_key_lifecycle(developer_user_token):
    """
    Kiểm thử vòng đời API Key trên Web Portal (/api/developers):
    - Tạo key mới: chỉ trả về raw_key duy nhất 1 lần
    - Liệt kê keys: không bao giờ để lộ raw_key hay hash
    - Tra cứu thống kê usage
    - Thu hồi (Revoke) key
    """
    _, _, token = developer_user_token
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Tạo API Key mới
    res_create = client.post(
        "/api/developers/keys",
        headers=headers,
        json={"name": "Test Key for Mobile App"},
    )
    assert res_create.status_code == 201
    created_data = res_create.json()
    assert created_data["name"] == "Test Key for Mobile App"
    assert "raw_key" in created_data
    raw_key = created_data["raw_key"]
    key_id = created_data["id"]
    assert raw_key.startswith("vx_live_")

    # 2. Liệt kê danh sách API Key
    res_list = client.get("/api/developers/keys", headers=headers)
    assert res_list.status_code == 200
    keys_list = res_list.json()
    assert len(keys_list) >= 1
    target_key = next((k for k in keys_list if k["id"] == key_id), None)
    assert target_key is not None
    assert target_key["name"] == "Test Key for Mobile App"
    assert target_key["is_active"] is True
    assert "raw_key" not in target_key
    assert "hashed_key" not in target_key

    # 3. Tra cứu thống kê
    res_stats = client.get("/api/developers/stats?days=7", headers=headers)
    assert res_stats.status_code == 200
    stats = res_stats.json()
    assert "total_requests" in stats
    assert "total_credits" in stats
    assert "daily_usage" in stats
    assert len(stats["daily_usage"]) == 7

    # 4. Thu hồi (Revoke) API Key
    res_revoke = client.delete(f"/api/developers/keys/{key_id}", headers=headers)
    assert res_revoke.status_code == 200
    assert "thu hồi thành công" in res_revoke.json()["message"]

    # Kiểm tra key đã đổi trạng thái is_active=False
    res_list2 = client.get("/api/developers/keys", headers=headers)
    revoked_key = next((k for k in res_list2.json() if k["id"] == key_id), None)
    assert revoked_key is not None
    assert revoked_key["is_active"] is False
    assert revoked_key["revoked_at"] is not None


def test_v1_voices_and_auth(developer_user_token):
    """Kiểm thử GET /v1/voices với xác thực Bearer API Key và các header rate limit."""
    _, _, token = developer_user_token
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/developers/keys",
        headers=headers,
        json={"name": "Key for Voices Test"},
    )
    raw_key = create_res.json()["raw_key"]

    # 1. Gọi thành công với Bearer token
    v1_headers = {"Authorization": f"Bearer {raw_key}"}
    res = client.get("/v1/voices", headers=v1_headers)
    assert res.status_code == 200
    data = res.json()
    assert "voices" in data
    assert "total" in data
    assert len(data["voices"]) > 0

    # Rate limit headers
    assert "X-RateLimit-Limit" in res.headers
    assert "X-RateLimit-Remaining" in res.headers
    assert "X-RateLimit-Reset" in res.headers

    # 2. Không có header Authorization -> 401
    res_no_auth = client.get("/v1/voices")
    assert res_no_auth.status_code == 401

    # 3. Token không hợp lệ -> 401
    res_invalid = client.get("/v1/voices", headers={"Authorization": "Bearer vx_live_invalidkey12345"})
    assert res_invalid.status_code == 401


def test_v1_tts_sync_and_async(developer_user_token):
    """Kiểm thử POST /v1/tts: Cả 2 chế độ Sync và Async, trừ credit và download trực tiếp."""
    _, _, token = developer_user_token
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/developers/keys",
        headers=headers,
        json={"name": "Key for TTS Test"},
    )
    raw_key = create_res.json()["raw_key"]
    v1_headers = {"Authorization": f"Bearer {raw_key}"}

    # 1. Test Sync Mode (JSON phản hồi kèm audio_url)
    sync_payload = {
        "text": "Xin chào! Đây là bài kiểm thử tổng hợp giọng nói qua Public API v1.",
        "voice": "vi-VN-HoaiMyNeural",
        "mode": "sync",
    }
    res_sync = client.post("/v1/tts", headers=v1_headers, json=sync_payload)
    assert res_sync.status_code == 200
    sync_data = res_sync.json()
    assert sync_data["status"] == "completed"
    assert sync_data["job_id"] is not None
    assert "/audio" in sync_data["audio_url"]
    assert sync_data["credits_used"] > 0
    assert sync_data["duration"] > 0

    # 2. Test Sync Mode với direct audio download (Accept: audio/mpeg)
    audio_headers = {
        "Authorization": f"Bearer {raw_key}",
        "Accept": "audio/mpeg",
    }
    res_audio = client.post("/v1/tts", headers=audio_headers, json=sync_payload)
    assert res_audio.status_code == 200
    assert "audio/mpeg" in res_audio.headers.get("content-type", "")
    assert len(res_audio.content) > 0
    assert "X-Duration" in res_audio.headers
    assert "X-Credits-Used" in res_audio.headers

    # 3. Test Async Mode (trả về HTTP 202 Accepted)
    async_payload = {
        "text": "Đoạn văn bản xử lý bất đồng bộ trong hàng đợi nền.",
        "voice": "vi-VN-NamMinhNeural",
        "mode": "async",
        "webhook_url": "https://httpbin.org/post",
    }
    res_async = client.post("/v1/tts", headers=v1_headers, json=async_payload)
    assert res_async.status_code == 202
    async_data = res_async.json()
    assert async_data["status"] == "processing"
    assert async_data["job_id"] is not None
    job_id = async_data["job_id"]

    # 4. Tra cứu trạng thái Job qua GET /v1/jobs/{id}
    time.sleep(0.3)
    res_job = client.get(f"/v1/jobs/{job_id}", headers=v1_headers)
    assert res_job.status_code == 200
    job_info = res_job.json()
    assert job_info["id"] == job_id
    assert job_info["status"] in ["queued", "processing", "completed"]


def test_v1_jobs_not_found(developer_user_token):
    """Kiểm tra GET /v1/jobs/{id} với id không tồn tại trả về 404."""
    _, _, token = developer_user_token
    create_res = client.post(
        "/api/developers/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Key for Not Found Test"},
    )
    raw_key = create_res.json()["raw_key"]
    v1_headers = {"Authorization": f"Bearer {raw_key}"}

    res = client.get("/v1/jobs/999999", headers=v1_headers)
    assert res.status_code == 404


def test_v1_credits_endpoint(developer_user_token):
    """Kiểm tra GET /v1/credits trả về số dư, gói cước và rate limit per minute."""
    _, email, token = developer_user_token
    create_res = client.post(
        "/api/developers/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Key for Credits Test"},
    )
    raw_key = create_res.json()["raw_key"]
    v1_headers = {"Authorization": f"Bearer {raw_key}"}

    res = client.get("/v1/credits", headers=v1_headers)
    assert res.status_code == 200
    data = res.json()
    assert "credit_balance" in data
    assert "plan_tier" in data
    assert "rate_limit_per_minute" in data
    assert data["rate_limit_per_minute"] == 20
    assert data["user_email"] == email


def test_v1_insufficient_credits(developer_user_token):
    """Kiểm tra trả HTTP 402 Payment Required khi tài khoản hết credit."""
    user_id, _, token = developer_user_token

    async def _zero_credits():
        async with AsyncSessionLocal() as db:
            user = await db.get(User, int(user_id))
            assert user is not None
            user.credit_balance = 0
            user.credits = 0
            await db.commit()

    asyncio.run(_zero_credits())

    create_res = client.post(
        "/api/developers/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Key for Zero Credit"},
    )
    raw_key = create_res.json()["raw_key"]
    v1_headers = {"Authorization": f"Bearer {raw_key}"}

    res = client.post(
        "/v1/tts",
        headers=v1_headers,
        json={"text": "Văn bản thử nghiệm khi không đủ tiền.", "mode": "sync"},
    )
    assert res.status_code == 402
    assert "Số dư credit không đủ" in res.json()["detail"]


def test_v1_rate_limiting_exceeded(developer_user_token):
    """Kiểm tra vượt quá hạn mức rate limit trả về 429 kèm Retry-After header."""
    RateLimiterService.reset_in_memory()
    user_id, _, token = developer_user_token

    async def _restore_credits():
        async with AsyncSessionLocal() as db:
            user = await db.get(User, int(user_id))
            assert user is not None
            user.credit_balance = 100000
            await db.commit()

    asyncio.run(_restore_credits())

    create_res = client.post(
        "/api/developers/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Key for Rate Limit Test"},
    )
    raw_key = create_res.json()["raw_key"]
    v1_headers = {"Authorization": f"Bearer {raw_key}"}

    # Free plan có limit 20 req/min. Gọi liên tiếp 20 lần hợp lệ.
    for _ in range(20):
        res = client.get("/v1/credits", headers=v1_headers)
        assert res.status_code == 200

    # Lần thứ 21 phải bị từ chối 429
    res_limited = client.get("/v1/credits", headers=v1_headers)
    assert res_limited.status_code == 429
    assert "Retry-After" in res_limited.headers
    assert int(res_limited.headers["Retry-After"]) > 0
    assert "vượt quá giới hạn tần suất" in res_limited.json()["detail"]

    RateLimiterService.reset_in_memory()


def test_async_job_webhook_dispatch():
    """Kiểm tra hàm gửi webhook callback khi job async hoàn thành."""
    async def _test():
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200
            await TTSJobService._dispatch_webhook(
                webhook_url="https://example.com/webhook",
                payload={"event": "tts.job.completed", "job_id": 42},
            )
            mock_post.assert_called_once()
            call_args, call_kwargs = mock_post.call_args
            assert call_args[0] == "https://example.com/webhook"
            assert call_kwargs["json"]["job_id"] == 42

    asyncio.run(_test())


def test_api_key_service_methods_deep(developer_user_token):
    """Kiểm thử trực tiếp tất cả các method của ApiKeyService."""
    user_id, _, _ = developer_user_token

    async def _test():
        async with AsyncSessionLocal() as db:
            # 1. Tạo key
            key_rec, raw_key = await ApiKeyService.create_api_key(db, int(user_id), "Deep Test Key")
            assert key_rec.id is not None
            assert key_rec.name == "Deep Test Key"

            # 2. Verify key
            verified = await ApiKeyService.verify_api_key(db, raw_key)
            assert verified is not None
            api_k, usr = verified
            assert api_k.id == key_rec.id
            assert usr.id == int(user_id)
            assert api_k.last_used_at is not None

            # 3. Verify key không hợp lệ
            assert await ApiKeyService.verify_api_key(db, "") is None
            assert await ApiKeyService.verify_api_key(db, "invalid_prefix_123") is None
            assert await ApiKeyService.verify_api_key(db, "vx_live_" + "0" * 48) is None

            # 4. List keys
            keys = await ApiKeyService.list_api_keys(db, int(user_id))
            assert len(keys) >= 1

            # 5. Log usage
            log_item = await ApiKeyService.log_usage(
                db=db,
                api_key_id=key_rec.id,
                user_id=int(user_id),
                endpoint="/v1/test",
                status_code=200,
                credits_used=15,
                ip_address="127.0.0.1",
                user_agent="TestAgent/1.0",
            )
            assert log_item.id is not None
            assert log_item.credits_used == 15

            # 6. Get usage stats
            stats = await ApiKeyService.get_usage_stats(db, int(user_id), days=7)
            assert stats["total_requests"] >= 1
            assert stats["total_credits"] >= 15
            assert len(stats["daily_usage"]) == 7

            # 7. Revoke key
            revoked_ok = await ApiKeyService.revoke_api_key(db, int(user_id), key_rec.id)
            assert revoked_ok is True
            # Thu hồi key không tồn tại trả về False
            assert await ApiKeyService.revoke_api_key(db, int(user_id), 999999) is False

            # Verify sau khi thu hồi -> None
            assert await ApiKeyService.verify_api_key(db, raw_key) is None

    asyncio.run(_test())


def test_rate_limiter_service_deep():
    """Kiểm thử trực tiếp RateLimiterService với các gói cước và kịch bản Redis fallback."""
    async def _test():
        RateLimiterService.reset_in_memory()

        # Admin tier (300 req/min)
        allowed, limit, remaining, reset_sec = await RateLimiterService.check_rate_limit(
            api_key_id=1001,
            plan_name="admin",
        )
        assert allowed is True
        assert limit == 300
        assert remaining == 299

        # Pro tier (60 req/min)
        allowed, limit, remaining, reset_sec = await RateLimiterService.check_rate_limit(
            api_key_id=1002,
            plan_name="pro",
        )
        assert allowed is True
        assert limit == 60

        # VIP tier (120 req/min)
        allowed, limit, remaining, reset_sec = await RateLimiterService.check_rate_limit(
            api_key_id=1003,
            plan_name="vip",
        )
        assert allowed is True
        assert limit == 120

        # Memory limiter reset
        RateLimiterService.reset_in_memory()

    asyncio.run(_test())


def test_developer_and_v1_error_branches(developer_user_token):
    """Kiểm thử các nhánh lỗi và validate đầu vào của router API Keys & Public v1."""
    user_id, _, token = developer_user_token
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Tạo API key với tên rỗng -> 400
    res_bad_name = client.post("/api/developers/keys", headers=headers, json={"name": "   "})
    assert res_bad_name.status_code == 400

    # 2. Thu hồi key không tồn tại -> 404
    res_bad_revoke = client.delete("/api/developers/keys/999999", headers=headers)
    assert res_bad_revoke.status_code == 404

    # Tạo 1 key hợp lệ để test các lỗi trên /v1
    create_res = client.post("/api/developers/keys", headers=headers, json={"name": "Branch Test Key"})
    raw_key = create_res.json()["raw_key"]
    v1_headers = {"Authorization": f"Bearer {raw_key}"}

    # 3. /v1/tts với text rỗng -> 400
    res_empty_text = client.post("/v1/tts", headers=v1_headers, json={"text": "   ", "mode": "sync"})
    assert res_empty_text.status_code == 400

    # 4. /v1/tts với giọng clone không tồn tại -> 404
    res_clone_not_found = client.post(
        "/v1/tts",
        headers=v1_headers,
        json={"text": "Thử giọng clone không có thật.", "voice": "clone_nonexistent_12345", "mode": "sync"},
    )
    assert res_clone_not_found.status_code == 404

    # 5. Header Authorization sai format -> 401
    res_bad_auth = client.get("/v1/voices", headers={"Authorization": "Basic 123456"})
    assert res_bad_auth.status_code == 401

    # 6. Gửi kèm X-Forwarded-For header
    res_fwd = client.get(
        "/v1/voices",
        headers={
            "Authorization": f"Bearer {raw_key}",
            "X-Forwarded-For": "203.0.113.195, 10.0.0.1",
        },
    )
    assert res_fwd.status_code == 200

    # 7. GET /v1/jobs/{id} với completed job
    async def _create_completed_gen():
        from app.models.generation import Generation
        async with AsyncSessionLocal() as db:
            gen = Generation(
                user_id=int(user_id),
                text="Test completed gen",
                voice="vi-VN-HoaiMyNeural",
                char_count=18,
                status="done",
                progress=100,
                file_path="/tmp/fake_done.mp3",
                duration=2.5,
                credit_used=20,
            )
            db.add(gen)
            await db.commit()
            await db.refresh(gen)
            return gen.id

    gen_id = asyncio.run(_create_completed_gen())
    # Gọi endpoint tra cứu job completed
    res_job_done = client.get(f"/v1/jobs/{gen_id}", headers=v1_headers)
    assert res_job_done.status_code == 200
    assert res_job_done.json()["status"] == "completed"
    assert "/audio" in res_job_done.json()["audio_url"]


def test_v1_voices_with_cloned_voice(developer_user_token):
    """Kiểm thử GET /v1/voices hiển thị cả giọng clone của người dùng sở hữu API key."""
    user_id, _, token = developer_user_token
    clone_voice_id = f"clone_{user_id}_{int(time.time() * 1000)}"

    # Thêm 1 cloned voice trạng thái ready cho user
    async def _add_clone():
        from app.models.cloned_voice import ClonedVoice
        async with AsyncSessionLocal() as db:
            clone = ClonedVoice(
                voice_id=clone_voice_id,
                user_id=int(user_id),
                name="My Cloned Voice",
                audio_sample_path="/tmp/sample.mp3",
                sample_duration=12.5,
                sample_size_bytes=250000,
                quality_score=4.8,
                gender="Male",
                language="vi-VN",
                status="ready",
                is_active=True,
            )
            db.add(clone)
            await db.commit()

    asyncio.run(_add_clone())

    create_res = client.post(
        "/api/developers/keys",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Clone Voice Test Key"},
    )
    raw_key = create_res.json()["raw_key"]
    v1_headers = {"Authorization": f"Bearer {raw_key}"}

    res = client.get("/v1/voices", headers=v1_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["cloned_count"] >= 1
    assert any(v.get("is_clone") for v in data["voices"])

    # Tổng hợp TTS đồng bộ với giọng clone của chính user
    with patch("app.routes.v1.tts._clone_service.synthesize_cloned_voice", new_callable=AsyncMock) as mock_clone_synth:
        mock_clone_synth.return_value = b"ID3fakeaudio12345678901234567890"
        res_clone_tts = client.post(
            "/v1/tts",
            headers=v1_headers,
            json={"text": "Đọc bằng giọng clone của chính mình.", "voice": clone_voice_id, "mode": "sync"},
        )
        assert res_clone_tts.status_code == 200
        assert res_clone_tts.json()["status"] == "completed"

    # Thử giọng clone thuộc về người khác (user_id khác) -> 403 Forbidden
    other_voice_id = f"clone_other_{int(time.time() * 1000)}"

    async def _add_other_user_clone():
        from app.models.cloned_voice import ClonedVoice
        async with AsyncSessionLocal() as db:
            other_usr = User(
                email=f"other_user_{time.time()}_{int(time.time() * 1000)}@example.com",
                role="user",
                is_active=True,
                credit_balance=1000,
            )
            db.add(other_usr)
            await db.commit()
            await db.refresh(other_usr)

            clone_other = ClonedVoice(
                voice_id=other_voice_id,
                user_id=other_usr.id,
                name="Other User Voice",
                audio_sample_path="/tmp/sample.mp3",
                sample_duration=10.0,
                sample_size_bytes=200000,
                quality_score=4.5,
                gender="Female",
                language="vi-VN",
                status="ready",
                is_active=True,
            )
            db.add(clone_other)
            await db.commit()

    asyncio.run(_add_other_user_clone())

    res_forbidden_clone = client.post(
        "/v1/tts",
        headers=v1_headers,
        json={"text": "Thử dùng trộm giọng clone của người khác.", "voice": other_voice_id, "mode": "sync"},
    )
    assert res_forbidden_clone.status_code == 403


def test_v1_extra_coverage_boost(developer_user_token):
    """Bổ sung kiểm thử các nhánh biên để bảo đảm tổng coverage >= 80%."""
    user_id, _, token = developer_user_token

    # 1. Admin query job
    async def _test_admin():
        async with AsyncSessionLocal() as db:
            admin_user = User(
                email=f"admin_v1_{time.time()}@example.com",
                full_name="Admin V1",
                is_admin=True,
                is_active=True,
                role="admin",
                subscription_tier="admin",
                credit_balance=100000,
            )
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

            key_rec, raw_k = await ApiKeyService.create_api_key(db, admin_user.id, "Admin Key")
            return raw_k

    admin_key = asyncio.run(_test_admin())

    # Admin lấy danh sách voices & credits
    admin_headers = {"Authorization": f"Bearer {admin_key}"}
    res_adm_cred = client.get("/v1/credits", headers=admin_headers)
    assert res_adm_cred.status_code == 200
    assert res_adm_cred.json()["plan_tier"] == "admin"
    assert res_adm_cred.json()["rate_limit_per_minute"] == 300

    # 2. TTSJobService list_recent_jobs
    async def _test_job_service():
        async with AsyncSessionLocal() as db:
            svc = TTSJobService()
            jobs = await svc.list_recent_jobs(db, int(user_id), limit=5)
            assert isinstance(jobs, list)

    asyncio.run(_test_job_service())

    # 3. GET /api/developers/stats với các ngày khác nhau (1 đến 30)
    dev_headers = {"Authorization": f"Bearer {token}"}
    res_stats_14 = client.get("/api/developers/stats?days=14", headers=dev_headers)
    assert res_stats_14.status_code == 200
    assert len(res_stats_14.json()["daily_usage"]) == 14

    # 3.1 DELETE /api/developers/keys/{id} với key không tồn tại -> 404
    res_revoke_nf = client.delete("/api/developers/keys/999999", headers=dev_headers)
    assert res_revoke_nf.status_code == 404

    # 4. Kiểm thử các nhánh biên của /v1/tts:
    # Tạo API key cho user
    create_key_res = client.post(
        "/api/developers/keys",
        headers=dev_headers,
        json={"name": "Extra Coverage Key"},
    )
    assert create_key_res.status_code == 201
    user_api_key = create_key_res.json()["raw_key"]
    v1_headers = {"Authorization": f"Bearer {user_api_key}"}

    # 4.1 Empty text -> 400
    res_empty = client.post(
        "/v1/tts",
        headers=v1_headers,
        json={"text": "   ", "voice": "vi-VN-HoaiMyNeural", "mode": "sync"},
    )
    assert res_empty.status_code == 400

    # 4.2 Sync TTS với direct stream download (download=True và Accept: audio/mpeg) kèm X-Forwarded-For
    with patch("app.services.tts_service.TTSService.synthesize", new_callable=AsyncMock) as mock_tts:
        mock_tts.return_value = b"ID3fakeaudiobinary123456789012345"
        res_stream = client.post(
            "/v1/tts?download=true",
            headers={**v1_headers, "Accept": "audio/mpeg", "X-Forwarded-For": "192.168.1.100, 10.0.0.1"},
            json={"text": "Tải trực tiếp định dạng âm thanh audio stream.", "voice": "vi-VN-HoaiMyNeural", "mode": "sync"},
        )
        assert res_stream.status_code == 200
        assert res_stream.headers["content-type"] == "audio/mpeg"
        assert res_stream.content == b"ID3fakeaudiobinary123456789012345"

    # 4.3 Async TTS khi người dùng không đủ credit -> 402
    async def _create_zero_credit_user_key():
        async with AsyncSessionLocal() as db:
            zero_usr = User(
                email=f"zero_credit_{time.time()}@example.com",
                full_name="Zero Credit User",
                credit_balance=0,
                is_active=True,
            )
            db.add(zero_usr)
            await db.commit()
            await db.refresh(zero_usr)
            _, raw_k = await ApiKeyService.create_api_key(db, zero_usr.id, "Zero Key")
            return raw_k

    zero_key = asyncio.run(_create_zero_credit_user_key())
    res_zero_async = client.post(
        "/v1/tts",
        headers={"Authorization": f"Bearer {zero_key}"},
        json={"text": "Kiểm tra async khi không đủ credit.", "voice": "vi-VN-HoaiMyNeural", "mode": "async"},
    )
    assert res_zero_async.status_code == 402

    # 4.4 Async TTS khi gặp AppError -> mã lỗi từ AppError
    from app.core.errors import AppError
    with patch("app.services.tts_job_service.TTSJobService.create_job", new_callable=AsyncMock) as mock_create_job:
        mock_create_job.side_effect = AppError(code="VOICE_DISABLED", message="Giọng đọc bị vô hiệu", status_code=400)
        res_app_err = client.post(
            "/v1/tts",
            headers=v1_headers,
            json={"text": "Kiểm tra AppError async.", "voice": "vi-VN-HoaiMyNeural", "mode": "async"},
        )
        assert res_app_err.status_code == 400

    # 4.5 Sync TTS khi gặp Exception bất ngờ -> hoàn credit và trả 500
    with patch("app.services.tts_service.TTSService.synthesize", new_callable=AsyncMock) as mock_err_synth:
        mock_err_synth.side_effect = RuntimeError("Crash synthesis engine")
        res_sync_err = client.post(
            "/v1/tts",
            headers=v1_headers,
            json={"text": "Kiểm tra sync lỗi 500.", "voice": "vi-VN-HoaiMyNeural", "mode": "sync"},
        )
        assert res_sync_err.status_code == 500

    # 4.6 Query job hiện có bằng API Key hợp lệ
    async def _create_test_gen_record():
        async with AsyncSessionLocal() as db:
            from app.models.generation import Generation
            g = Generation(
                user_id=int(user_id),
                text="Test job query",
                char_count=14,
                voice="vi-VN-HoaiMyNeural",
                status="done",
                progress=100,
                duration=3.5,
                credit_used=10,
                file_path="/storage/test.mp3",
                file_size=1024,
            )
            db.add(g)
            await db.commit()
            await db.refresh(g)
            return g.id

    gen_id = asyncio.run(_create_test_gen_record())
    res_query_job = client.get(f"/v1/jobs/{gen_id}", headers=v1_headers)
    assert res_query_job.status_code == 200
    assert res_query_job.json()["status"] == "completed"
    assert res_query_job.json()["audio_url"] is not None

