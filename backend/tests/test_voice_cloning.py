"""Unit & Integration tests cho tính năng Clone giọng nói (Issue #12 / Prompt 10)."""
import asyncio
import io
import os
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.voice_anti_abuse import (
    check_voice_name_against_blocklist,
)
from app.db import AsyncSessionLocal
from app.main import app
from app.models.cloned_voice import ClonedVoice, VoiceConsentLog
from app.models.user import User
from app.providers.clone_elevenlabs import ElevenLabsCloneProvider
from app.providers.clone_factory import get_clone_provider
from app.providers.clone_mock import MockCloneProvider
from app.providers.clone_xtts import XTTSCloneProvider
from app.schemas.voice_clone import VoiceCloneQuota
from app.services.audio_service import AudioService
from app.services.credit_service import CreditService


def create_dummy_audio_bytes(duration_sec: float = 10.0) -> bytes:
    """Tạo byte audio giả lập có kích thước tương ứng để kiểm tra."""
    # Giả sử MP3 6000 bytes/giây
    size = int(duration_sec * 6000)
    return b"ID3" + b"\x00" * max(100, size - 3)


@pytest.mark.asyncio
async def test_anti_abuse_celebrity_and_politician_blocklist():
    """Kiểm tra chặn clone giọng người nổi tiếng & chính trị gia theo danh sách chuẩn hóa."""
    # 1. Chính trị gia Việt Nam
    blocked, detected, reason = check_voice_name_against_blocklist("Hồ Chí Minh")
    assert blocked is True
    assert detected == "ho chi minh"
    assert "chính trị gia" in reason

    blocked, detected, _ = check_voice_name_against_blocklist("Bác Hồ kính yêu")
    assert blocked is True
    assert detected == "bac ho"

    blocked, detected, _ = check_voice_name_against_blocklist("Giọng đọc Phạm Minh Chính")
    assert blocked is True
    assert detected == "pham minh chinh"

    # 2. Chính trị gia quốc tế
    blocked, detected, _ = check_voice_name_against_blocklist("Donald Trump voice")
    assert blocked is True
    assert detected == "donald trump"

    blocked, detected, _ = check_voice_name_against_blocklist("Joe Biden Official")
    assert blocked is True
    assert detected == "joe biden"

    # 3. Người nổi tiếng / Nghệ sĩ
    blocked, detected, reason = check_voice_name_against_blocklist("Sơn Tùng M-TP")
    assert blocked is True
    assert "bản quyền" in reason

    blocked, detected, _ = check_voice_name_against_blocklist("Trấn Thành MC")
    assert blocked is True

    blocked, detected, _ = check_voice_name_against_blocklist("Taylor Swift Pop")
    assert blocked is True

    # 4. Tên thông thường hợp lệ
    blocked, detected, reason = check_voice_name_against_blocklist("Nguyễn Văn Hoàng")
    assert blocked is False
    assert detected is None
    assert reason is None

    blocked, detected, _ = check_voice_name_against_blocklist("Giọng đọc tin tức của tôi")
    assert blocked is False


@pytest.mark.asyncio
async def test_audio_service_sample_validation(tmp_path, monkeypatch):
    """Kiểm tra thẩm định chất lượng mẫu âm thanh (5s – 3 phút, độ ồn, độ dài)."""
    # 1. File trống
    empty_file = tmp_path / "empty.mp3"
    empty_file.write_bytes(b"")
    val_empty = await AudioService.validate_voice_sample(str(empty_file))
    assert val_empty["valid"] is False

    # 2. File quá ngắn (< 5s)
    short_file = tmp_path / "short.mp3"
    short_file.write_bytes(create_dummy_audio_bytes(3.0))
    monkeypatch.setattr(AudioService, "measure_duration", lambda path: 3.0)
    val_short = await AudioService.validate_voice_sample(str(short_file))
    assert val_short["valid"] is False
    assert "quá ngắn" in val_short["error"]

    # 3. File quá dài (> 180s / 3 phút)
    long_file = tmp_path / "long.mp3"
    long_file.write_bytes(create_dummy_audio_bytes(190.0))
    monkeypatch.setattr(AudioService, "measure_duration", lambda path: 190.0)
    val_long = await AudioService.validate_voice_sample(str(long_file))
    assert val_long["valid"] is False
    assert "quá dài" in val_long["error"]

    # 4. File hợp lệ (49.7s - file thực tế của user)
    valid_file = tmp_path / "valid.mp3"
    valid_file.write_bytes(create_dummy_audio_bytes(49.7))
    monkeypatch.setattr(AudioService, "measure_duration", lambda path: 49.7)
    val_valid = await AudioService.validate_voice_sample(str(valid_file))
    assert val_valid["valid"] is True
    assert val_valid["duration"] == 49.7
    assert val_valid["quality_score"] >= 3.5


@pytest.mark.asyncio
async def test_clone_providers_architecture(tmp_path):
    """Kiểm tra Provider pattern: Mock, ElevenLabs, XTTS."""
    sample_file = tmp_path / "test_sample.mp3"
    sample_file.write_bytes(create_dummy_audio_bytes(10.0))

    # Mock Provider
    mock_p = MockCloneProvider()
    res = await mock_p.clone_voice("Giọng mẫu", str(sample_file), "Mô tả test")
    assert res["provider_voice_id"].startswith("mock_")
    audio = await mock_p.synthesize("Xin chào bạn", res["provider_voice_id"])
    assert len(audio) > 0
    deleted = await mock_p.delete_cloned_voice(res["provider_voice_id"])
    assert deleted is True

    # ElevenLabs fallback mock
    el_p = ElevenLabsCloneProvider(api_key="")
    res_el = await el_p.clone_voice("Giọng EL", str(sample_file))
    assert res_el["provider_voice_id"].startswith("mock_")

    # XTTS fallback mock
    xtts_p = XTTSCloneProvider(api_url="")
    res_xtts = await xtts_p.clone_voice("Giọng XTTS", str(sample_file))
    assert res_xtts["provider_voice_id"].startswith("mock_")


@pytest.mark.asyncio
async def test_credit_cost_multiplier_for_cloned_voice():
    """Kiểm tra chi phí credit của giọng clone có hệ số nhân riêng (1.5x)."""
    # Giọng thông thường: 1000 ký tự = 1000 credit
    std_cost = CreditService.calculate_cost(1000, provider="edge", voice="vi-VN-HoaiMyNeural")
    assert std_cost == 1000

    # Giọng clone: 1000 ký tự * 1.5 = 1500 credit
    clone_cost = CreditService.calculate_cost(1000, provider="edge", voice="clone_user1_test")
    assert clone_cost == 1500


@pytest.mark.asyncio
async def test_voice_cloning_full_lifecycle_api(monkeypatch):
    """
    Kiểm tra luồng trọn vẹn:
    1. Kiểm tra giới hạn quota ban đầu
    2. Thiếu checkbox đồng ý bản quyền -> bị chặn (400)
    3. Tên người nổi tiếng -> bị chặn (400)
    4. Tạo giọng clone hợp lệ thành công -> kiểm tra trừ credit 1 lần (500) & audit log
    5. Nghe thử mẫu preview và sample
    6. Tổng hợp văn bản bằng giọng clone thành công
    7. Báo cáo lạm dụng abuse report
    8. Đổi tên giọng clone
    9. Xóa giọng clone -> xóa file mẫu, thử tổng hợp lại bị từ chối (404/400).
    """
    import time

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Tạo user test
        email = f"clone_user_{time.time()}@example.com"
        password = "ClonePassword123!"
        reg = await client.post("/api/auth/register", json={
            "email": email,
            "password": password,
            "full_name": "Cao Việt Hoàng",
        })
        assert reg.status_code == 200

        login = await client.post("/api/auth/login", json={
            "email": email,
            "password": password,
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Đảm bảo AudioService trả về thời lượng hợp lệ 12 giây trong môi trường test
        monkeypatch.setattr(AudioService, "measure_duration", lambda path: 12.0)

        # 1. Kiểm tra limits quota
        lim_res = await client.get("/api/voices/clone/limits", headers=headers)
        assert lim_res.status_code == 200
        limits_data = lim_res.json()
        assert limits_data["used"] == 0
        assert limits_data["max_allowed"] >= 1
        assert limits_data["creation_fee"] == 500
        assert limits_data["multiplier"] == 1.5

        dummy_audio = create_dummy_audio_bytes(12.0)

        # 2. Thiếu checkbox cam kết bản quyền
        fail_consent_res = await client.post(
            "/api/voices/clone",
            headers=headers,
            data={
                "name": "Giọng Cá Nhân",
                "consent_accepted": "false",
            },
            files={"audio_file": ("sample.mp3", io.BytesIO(dummy_audio), "audio/mpeg")},
        )
        assert fail_consent_res.status_code == 400
        assert "chủ giọng" in fail_consent_res.json()["detail"]

        # 3. Nhập tên người nổi tiếng bị chặn
        fail_celeb_res = await client.post(
            "/api/voices/clone",
            headers=headers,
            data={
                "name": "Clone Trấn Thành",
                "consent_accepted": "true",
            },
            files={"audio_file": ("sample.mp3", io.BytesIO(dummy_audio), "audio/mpeg")},
        )
        assert fail_celeb_res.status_code == 400
        assert "bản quyền" in fail_celeb_res.json()["detail"] or "nghệ sĩ" in fail_celeb_res.json()["detail"]

        # 4. Tạo giọng clone hợp lệ thành công
        create_res = await client.post(
            "/api/voices/clone",
            headers=headers,
            data={
                "name": "Giọng Đọc Cá Nhân Hoàng",
                "description": "Giọng tự nhiên đọc sách",
                "consent_accepted": "true",
                "gender": "male",
                "language": "vi-VN",
            },
            files={"audio_file": ("sample.mp3", io.BytesIO(dummy_audio), "audio/mpeg")},
        )
        assert create_res.status_code == 201
        created_data = create_res.json()
        voice_id = created_data["voice_id"]
        assert voice_id.startswith("clone_")
        assert created_data["name"] == "Giọng Đọc Cá Nhân Hoàng"
        assert created_data["quality_score"] is not None

        # Kiểm tra audit log đồng ý trong DB
        async with AsyncSessionLocal() as db:
            consent_stmt = select(VoiceConsentLog).where(VoiceConsentLog.cloned_voice_id == created_data["id"])
            c_log = (await db.execute(consent_stmt)).scalar_one_or_none()
            assert c_log is not None
            assert "chủ giọng" in c_log.consent_text
            assert c_log.voice_name == "Giọng Đọc Cá Nhân Hoàng"

            # Kiểm tra file mẫu đã được tạo trên đĩa
            voice_rec = (await db.execute(select(ClonedVoice).where(ClonedVoice.voice_id == voice_id))).scalar_one()
            assert os.path.exists(voice_rec.audio_sample_path)
            sample_path = voice_rec.audio_sample_path

        # 5. Liệt kê danh sách giọng clone
        list_res = await client.get("/api/voices/cloned", headers=headers)
        assert list_res.status_code == 200
        cloned_list = list_res.json()
        assert cloned_list["total"] == 1
        assert cloned_list["voices"][0]["voice_id"] == voice_id
        assert cloned_list["quota"]["used"] == 1

        # 6. Nghe thử mẫu preview và sample
        preview_res = await client.get(f"/api/voices/cloned/{voice_id}/preview", headers=headers)
        assert preview_res.status_code == 200
        assert len(preview_res.content) > 0

        sample_res = await client.get(f"/api/voices/cloned/{voice_id}/sample", headers=headers)
        assert sample_res.status_code == 200
        assert len(sample_res.content) > 0

        # 7. Đọc văn bản trong Studio với giọng clone vừa tạo (Synchronous TTS)
        tts_res = await client.post(
            "/api/tts",
            headers=headers,
            json={
                "text": "Chào mừng các bạn đã đến với giọng đọc clone mới tạo của tôi.",
                "voice": voice_id,
                "preview": False,
            },
        )
        assert tts_res.status_code == 200
        assert len(tts_res.content) > 0

        # 8. Đọc văn bản trong Studio với giọng clone (Background Job)
        job_res = await client.post(
            "/api/tts/jobs",
            headers=headers,
            json={
                "text": "Đoạn văn bản xử lý ngầm với giọng clone kiểm tra tiến độ.",
                "voice": voice_id,
                "format": "mp3",
            },
        )
        assert job_res.status_code == 202
        job_id = job_res.json()["id"]
        assert job_id > 0

        # Chờ background job hoàn tất để giải phóng giao dịch và tránh xung đột khoá SQLite
        for _ in range(30):
            await asyncio.sleep(0.1)
            p_res = await client.get(f"/api/tts/jobs/{job_id}", headers=headers)
            if p_res.status_code == 200 and p_res.json()["status"] in ("done", "failed"):
                break

        # 9. Báo cáo lạm dụng
        report_res = await client.post(
            f"/api/voices/cloned/{voice_id}/report",
            headers=headers,
            json={
                "reason": "no_consent",
                "description": "Nghi ngờ sử dụng mẫu giọng không xin phép người khác.",
            },
        )
        assert report_res.status_code == 200
        assert report_res.json()["reason"] == "no_consent"

        # 10. Đổi tên giọng clone
        rename_res = await client.patch(
            f"/api/voices/cloned/{voice_id}",
            headers=headers,
            json={"name": "Giọng Studio Chuyên Nghiệp"},
        )
        assert rename_res.status_code == 200
        assert rename_res.json()["name"] == "Giọng Studio Chuyên Nghiệp"

        # 11. Xóa giọng clone
        del_res = await client.delete(f"/api/voices/cloned/{voice_id}", headers=headers)
        assert del_res.status_code == 200
        assert del_res.json()["success"] is True

        # Kiểm tra file mẫu gốc trên đĩa đã bị xóa
        assert not os.path.exists(sample_path)

        # 12. Khi xóa voice thì không còn dùng được nữa (Tiêu chuẩn nghiệm thu)
        retry_tts = await client.post(
            "/api/tts",
            headers=headers,
            json={
                "text": "Thử đọc lại bằng giọng vừa bị xóa.",
                "voice": voice_id,
            },
        )
        assert retry_tts.status_code in (404, 400)
        assert "đã bị xóa" in retry_tts.json()["detail"] or "không tồn tại" in retry_tts.json()["detail"]


@pytest.mark.asyncio
async def test_voice_clone_service_edge_cases_and_quotas(monkeypatch, tmp_path):
    """Kiểm thử chi tiết các nhánh quota, credit, quyền truy cập và các tình huống lỗi."""
    import time
    from unittest.mock import AsyncMock

    from app.core.errors import AppError
    from app.models.payment import Order, PricingPlan
    from app.services.voice_clone_service import VoiceCloneService

    service = VoiceCloneService()

    async with AsyncSessionLocal() as db:
        # 1. User admin -> quota 100, fee 0
        admin_user = User(
            email=f"admin_{time.time()}@example.com",
            full_name="Admin Boss",
            role="admin",
            is_admin=True,
            credit_balance=10000,
        )
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

        admin_quota = await service.get_user_quota(db, admin_user)
        assert admin_quota.max_allowed == 100
        assert admin_quota.creation_fee == 0

        # 2. User thường có gói Pro
        pro_user = User(
            email=f"pro_{time.time()}@example.com",
            full_name="Pro User",
            credit_balance=50000,
        )
        db.add(pro_user)
        await db.flush()

        pro_plan = PricingPlan(
            code=f"plan_pro_{time.time()}",
            name="Gói Pro",
            type="subscription",
            price=199000,
            credits=600000,
            duration_days=30,
            storage_days=30,
            is_active=True,
        )
        db.add(pro_plan)
        await db.flush()

        pro_order = Order(
            order_code=f"ORD_PRO_{time.time()}",
            order_number=int(time.time() * 1000) % 1000000000,
            user_id=pro_user.id,
            plan_id=pro_plan.id,
            original_amount=199000,
            final_amount=199000,
            credits_to_add=600000,
            status="paid",
            expires_at=datetime.now(UTC),
        )
        db.add(pro_order)
        await db.commit()

        pro_quota = await service.get_user_quota(db, pro_user)
        assert pro_quota.max_allowed == 5

        # 3. User có gói Business
        biz_plan = PricingPlan(
            code=f"plan_business_{time.time()}",
            name="Gói Business",
            type="subscription",
            price=799000,
            credits=3000000,
            duration_days=30,
            storage_days=365,
            is_active=True,
        )
        db.add(biz_plan)
        await db.flush()

        biz_order = Order(
            order_code=f"ORD_BIZ_{time.time()}",
            order_number=(int(time.time() * 1000) + 1) % 1000000000,
            user_id=pro_user.id,
            plan_id=biz_plan.id,
            original_amount=799000,
            final_amount=799000,
            credits_to_add=3000000,
            status="paid",
            expires_at=datetime.now(UTC),
        )
        db.add(biz_order)
        await db.commit()

        biz_quota = await service.get_user_quota(db, pro_user)
        assert biz_quota.max_allowed == 20

        # 4. Kiểm tra lỗi thiếu tên
        with pytest.raises(AppError) as exc_name:
            await service.create_cloned_voice(
                db=db,
                user=pro_user,
                name="   ",
                description=None,
                file_bytes=b"123",
                filename="a.mp3",
                consent_accepted=True,
            )
        assert exc_name.value.code == "INVALID_NAME"

        # 5. Kiểm tra lỗi vượt quá quota
        monkeypatch.setattr(service, "get_user_quota", AsyncMock(return_value=VoiceCloneQuota(
            used=5,
            max_allowed=5,
            plan_name="Gói Pro",
            creation_fee=500,
            multiplier=1.5,
        )))
        with pytest.raises(AppError) as exc_quota:
            await service.create_cloned_voice(
                db=db,
                user=pro_user,
                name="Giọng Mới",
                description=None,
                file_bytes=b"123",
                filename="a.mp3",
                consent_accepted=True,
            )
        assert exc_quota.value.code == "QUOTA_EXCEEDED"

        # 6. Kiểm tra lỗi số dư không đủ
        poor_user = User(
            email=f"poor_{time.time()}@example.com",
            full_name="Poor User",
            credit_balance=100,
        )
        db.add(poor_user)
        await db.commit()
        await db.refresh(poor_user)

        with pytest.raises(Exception):
            await service.create_cloned_voice(
                db=db,
                user=poor_user,
                name="Giọng Mới",
                description=None,
                file_bytes=b"123",
                filename="a.mp3",
                consent_accepted=True,
            )

        # 7. Kiểm tra lỗi nhà cung cấp clone
        monkeypatch.setattr(AudioService, "validate_voice_sample", AsyncMock(return_value={"valid": True, "duration": 10.0, "quality_score": 4.5}))
        failing_provider = MockCloneProvider()
        monkeypatch.setattr(failing_provider, "clone_voice", AsyncMock(side_effect=RuntimeError("Provider timeout")))
        service_fail = VoiceCloneService(provider=failing_provider)

        rich_user = User(
            email=f"rich_{time.time()}@example.com",
            full_name="Rich User",
            credit_balance=10000,
        )
        db.add(rich_user)
        await db.commit()
        await db.refresh(rich_user)

        with pytest.raises(AppError) as exc_prov:
            await service_fail.create_cloned_voice(
                db=db,
                user=rich_user,
                name="Giọng Đọc",
                description=None,
                file_bytes=create_dummy_audio_bytes(10.0),
                filename="sample.mp3",
                consent_accepted=True,
            )
        assert exc_prov.value.code == "PROVIDER_CLONE_ERROR"

        # 8. Update voice không tồn tại & đổi tên vi phạm người nổi tiếng
        with pytest.raises(AppError) as exc_up_not_found:
            await service.update_cloned_voice(db, "non_existent", rich_user.id, name="Test")
        assert exc_up_not_found.value.code == "VOICE_NOT_FOUND"

        # 9. Delete voice không tồn tại
        with pytest.raises(AppError) as exc_del_not_found:
            await service.delete_cloned_voice(db, "non_existent", rich_user)
        assert exc_del_not_found.value.code == "VOICE_NOT_FOUND"

        # 10. Báo cáo lạm dụng với lý do không hợp lệ
        with pytest.raises(AppError) as exc_report_reason:
            await service.report_abuse(db, "voice_123", reason="invalid_reason", description="ABC")
        assert exc_report_reason.value.code == "INVALID_REASON"

        # 11. Báo cáo lạm dụng voice không tồn tại
        with pytest.raises(AppError) as exc_report_nf:
            await service.report_abuse(db, "voice_not_found", reason="copyright", description="Chi tiết vi phạm bản quyền")
        assert exc_report_nf.value.code == "VOICE_NOT_FOUND"


@pytest.mark.asyncio
async def test_external_clone_providers_http(monkeypatch, tmp_path):
    """Kiểm tra gọi HTTP API tới ElevenLabs và XTTS thông qua AsyncClient mock."""
    sample = tmp_path / "voice.mp3"
    sample.write_bytes(create_dummy_audio_bytes(10.0))

    class DummyResponse:
        def __init__(self, status_code: int, json_data: dict = None, content: bytes = b""):
            self.status_code = status_code
            self._json = json_data or {}
            self.content = content
            self.text = str(json_data or "")

        def json(self):
            return self._json

    async def mock_post(client, url, *args, **kwargs):
        u = str(url)
        if "voices/add" in u:
            return DummyResponse(200, json_data={"voice_id": "el_voice_999"})
        elif "text-to-speech" in u:
            return DummyResponse(200, content=b"AUDIO_EL")
        elif "/api/clone" in u:
            return DummyResponse(200, json_data={"speaker_id": "xtts_speaker_1"})
        elif "/api/tts" in u:
            return DummyResponse(200, content=b"AUDIO_XTTS")
        return DummyResponse(404)

    async def mock_delete(client, url, *args, **kwargs):
        return DummyResponse(200)

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    monkeypatch.setattr(httpx.AsyncClient, "delete", mock_delete)

    # 1. ElevenLabs API mock
    el = ElevenLabsCloneProvider(api_key="sk-test-key-123")
    cloned = await el.clone_voice("Giọng EL Mock", str(sample))
    assert cloned["provider_voice_id"] == "el_voice_999"

    audio_bytes = await el.synthesize("Hello ElevenLabs", "el_voice_999")
    assert audio_bytes == b"AUDIO_EL"

    deleted = await el.delete_cloned_voice("el_voice_999")
    assert deleted is True

    # 2. XTTS API mock
    xtts = XTTSCloneProvider(api_url="http://xtts.local:8000")
    cloned_x = await xtts.clone_voice("Giọng XTTS Mock", str(sample))
    assert cloned_x["provider_voice_id"] == "xtts_speaker_1"

    audio_x = await xtts.synthesize("Hello XTTS", "xtts_speaker_1")
    assert audio_x == b"AUDIO_XTTS"

    del_x = await xtts.delete_cloned_voice("xtts_speaker_1")
    assert del_x is True

    # 3. Kiểm tra Factory function
    p_mock = get_clone_provider()
    assert p_mock.provider_name in ("mock", "elevenlabs", "xtts")


@pytest.mark.asyncio
async def test_routes_voice_clone_extra_coverage():
    """Kiểm tra các nhánh phân quyền và lỗi trong routes /api/voices/cloned."""
    import time
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Tạo 2 user khác nhau
        u1_res = await client.post("/api/auth/register", json={
            "email": f"u1_{time.time()}@example.com",
            "password": "Password123!",
            "full_name": "User One",
        })
        u1_token = (await client.post("/api/auth/login", json={
            "email": u1_res.json()["email"],
            "password": "Password123!",
        })).json()["access_token"]
        u1_headers = {"Authorization": f"Bearer {u1_token}"}

        u2_res = await client.post("/api/auth/register", json={
            "email": f"u2_{time.time()}@example.com",
            "password": "Password123!",
            "full_name": "User Two",
        })
        u2_token = (await client.post("/api/auth/login", json={
            "email": u2_res.json()["email"],
            "password": "Password123!",
        })).json()["access_token"]
        u2_headers = {"Authorization": f"Bearer {u2_token}"}

        # Kiểm tra validation route /api/voices/clone: tên trống và file nhỏ
        bad_name = await client.post(
            "/api/voices/clone",
            headers=u1_headers,
            data={"name": "   ", "consent_accepted": "true"},
            files={"audio_file": ("s.mp3", io.BytesIO(create_dummy_audio_bytes(10.0)), "audio/mpeg")},
        )
        assert bad_name.status_code == 400

        bad_file = await client.post(
            "/api/voices/clone",
            headers=u1_headers,
            data={"name": "Test Name", "consent_accepted": "true"},
            files={"audio_file": ("s.mp3", io.BytesIO(b"short"), "audio/mpeg")},
        )
        assert bad_file.status_code == 400

        # User 1 tạo voice với header x-forwarded-for
        c_res = await client.post(
            "/api/voices/clone",
            headers={**u1_headers, "X-Forwarded-For": "10.0.0.1, 192.168.1.1"},
            data={"name": "Giọng User 1", "consent_accepted": "true"},
            files={"audio_file": ("s.mp3", io.BytesIO(create_dummy_audio_bytes(10.0)), "audio/mpeg")},
        )
        assert c_res.status_code == 201
        voice_id = c_res.json()["voice_id"]

        # User 2 cố gắng truy cập chi tiết voice của User 1 -> 403
        detail_403 = await client.get(f"/api/voices/cloned/{voice_id}", headers=u2_headers)
        assert detail_403.status_code == 403

        # User 2 cố gắng nghe file sample gốc của User 1 -> 403
        sample_403 = await client.get(f"/api/voices/cloned/{voice_id}/sample", headers=u2_headers)
        assert sample_403.status_code == 403

        # Truy cập voice không tồn tại -> 404
        not_found = await client.get("/api/voices/cloned/non_existent_123", headers=u1_headers)
        assert not_found.status_code == 404

        not_found_prev = await client.get("/api/voices/cloned/non_existent_123/preview", headers=u1_headers)
        assert not_found_prev.status_code == 404

        not_found_sample = await client.get("/api/voices/cloned/non_existent_123/sample", headers=u1_headers)
        assert not_found_sample.status_code == 404

        # User 2 cố tổng hợp TTS với giọng clone của User 1 -> 403
        synth_403 = await client.post(
            "/api/tts",
            headers=u2_headers,
            json={"text": "Thử dùng trộm giọng", "voice": voice_id},
        )
        assert synth_403.status_code == 403

        # User 1 đổi tên với tên trống -> 400
        empty_name = await client.patch(
            f"/api/voices/cloned/{voice_id}",
            headers=u1_headers,
            json={"name": "   "},
        )
        assert empty_name.status_code == 400

        # User 1 đổi tên và mô tả thành công
        up_ok = await client.patch(
            f"/api/voices/cloned/{voice_id}",
            headers=u1_headers,
            json={"name": "Giọng User 1 Đổi Tên", "description": "Mô tả mới"},
        )
        assert up_ok.status_code == 200
        assert up_ok.json()["name"] == "Giọng User 1 Đổi Tên"

        # Báo cáo với X-Forwarded-For
        rep_ok = await client.post(
            f"/api/voices/cloned/{voice_id}/report",
            headers={**u2_headers, "X-Forwarded-For": "11.22.33.44"},
            json={"reason": "copyright", "description": "Vi phạm bản quyền nghiêm trọng"},
        )
        assert rep_ok.status_code == 200

        # Xóa voice không tồn tại -> 404
        del_404 = await client.delete("/api/voices/cloned/non_existent_del", headers=u1_headers)
        assert del_404.status_code == 404


@pytest.mark.asyncio
async def test_voice_clone_service_direct_units_and_providers(tmp_path, monkeypatch):
    """Kiểm tra trực tiếp các unit method của VoiceCloneService và các providers."""
    from app.core.errors import AppError
    from app.services.voice_clone_service import VoiceCloneService

    service = VoiceCloneService()

    # 1. Test MockCloneProvider
    mock_prov = MockCloneProvider()
    res = await mock_prov.clone_voice("Test Mock", "/path/to/sample.mp3")
    assert res["provider_voice_id"].startswith("mock_")
    audio = await mock_prov.synthesize("Xin chào", "mock_123")
    assert len(audio) > 0
    assert await mock_prov.delete_cloned_voice("mock_123") is True

    # 2. Test ElevenLabsCloneProvider offline fallback & mock
    el_prov = ElevenLabsCloneProvider(api_key="test_api_key")
    assert el_prov.provider_name == "elevenlabs"
    # Clone with dummy sample
    dummy_sample = tmp_path / "sample.mp3"
    dummy_sample.write_bytes(create_dummy_audio_bytes(6.0))
    # When httpx fails / mock fallback
    el_res = await el_prov.clone_voice("EL Voice", str(dummy_sample))
    assert el_res["provider_voice_id"].startswith(("el_", "mock_"))
    el_audio = await el_prov.synthesize("EL text", el_res["provider_voice_id"])
    assert len(el_audio) > 0
    await el_prov.delete_cloned_voice(el_res["provider_voice_id"])

    # 3. Test XTTSCloneProvider
    xtts_prov = XTTSCloneProvider(api_url="http://127.0.0.1:8020")
    assert xtts_prov.provider_name == "xtts"
    xtts_res = await xtts_prov.clone_voice("XTTS Voice", str(dummy_sample))
    assert xtts_res["provider_voice_id"].startswith(("xtts_", "mock_"))
    xtts_audio = await xtts_prov.synthesize("XTTS text", xtts_res["provider_voice_id"], audio_sample_path=str(dummy_sample))
    assert len(xtts_audio) > 0
    await xtts_prov.delete_cloned_voice(xtts_res["provider_voice_id"])

    # 4. Test provider factory
    import app.providers.clone_factory as cf
    from app.config import Settings
    cf._cached_clone_provider = None
    assert get_clone_provider(Settings(clone_provider="elevenlabs")).provider_name == "elevenlabs"
    cf._cached_clone_provider = None
    assert get_clone_provider(Settings(clone_provider="xtts")).provider_name == "xtts"
    cf._cached_clone_provider = None
    assert get_clone_provider(Settings(clone_provider="mock")).provider_name == "mock"
    cf._cached_clone_provider = None
    assert get_clone_provider(Settings(clone_provider="unknown")).provider_name == "mock"
    cf._cached_clone_provider = None

    async with AsyncSessionLocal() as session:
        # Create test users
        admin_user = User(
            email=f"admin_cl_{datetime.now(UTC).timestamp()}@example.com",
            hashed_password="hash",
            full_name="Admin Cloner",
            role="admin",
            is_active=True,
            is_admin=True,
            credit_balance=10000,
        )
        norm_user = User(
            email=f"norm_cl_{datetime.now(UTC).timestamp()}@example.com",
            hashed_password="hash",
            full_name="Norm Cloner",
            role="user",
            is_active=True,
            credit_balance=10000,
        )
        other_user = User(
            email=f"other_cl_{datetime.now(UTC).timestamp()}@example.com",
            hashed_password="hash",
            full_name="Other Cloner",
            role="user",
            is_active=True,
            credit_balance=10000,
        )
        session.add_all([admin_user, norm_user, other_user])
        await session.commit()
        await session.refresh(admin_user)
        await session.refresh(norm_user)
        await session.refresh(other_user)

        # Quota checks
        admin_quota = await service.get_user_quota(session, admin_user)
        assert admin_quota.max_allowed >= 100
        norm_quota = await service.get_user_quota(session, norm_user)
        assert norm_quota.max_allowed >= 1

        # Create voice for norm user
        voice = await service.create_cloned_voice(
            db=session,
            user=norm_user,
            name="Pro Singer Voice",
            file_bytes=create_dummy_audio_bytes(8.0),
            filename="pro.mp3",
            consent_accepted=True,
            gender="female",
            description="Ca sĩ chuyên nghiệp",
            ip_address="127.0.0.1",
        )
        assert voice.name == "Pro Singer Voice"

        # Update errors
        with pytest.raises(AppError) as exc_info:
            await service.update_cloned_voice(session, voice.voice_id, norm_user.id, name="   ")
        assert exc_info.value.code == "INVALID_NAME"

        with pytest.raises(AppError) as exc_info:
            await service.update_cloned_voice(session, voice.voice_id, norm_user.id, name="Donald Trump Voice")
        assert exc_info.value.code == "CELEBRITY_VOICE_BLOCKED"

        with pytest.raises(AppError) as exc_info:
            await service.update_cloned_voice(session, "non_existent", norm_user.id, name="Valid")
        assert exc_info.value.code == "VOICE_NOT_FOUND"

        # Report abuse errors and flow
        with pytest.raises(AppError) as exc_info:
            await service.report_abuse(session, voice.voice_id, "invalid_reason", "details")
        assert exc_info.value.code == "INVALID_REASON"

        with pytest.raises(AppError) as exc_info:
            await service.report_abuse(session, "non_existent", "copyright", "details")
        assert exc_info.value.code == "VOICE_NOT_FOUND"

        # Add 2 abuse reports -> status becomes "reported"
        rep1 = await service.report_abuse(
            session, voice.voice_id, "copyright", "Vi phạm bản quyền 1", reporter_user=other_user
        )
        assert rep1.status == "pending"
        rep2 = await service.report_abuse(
            session, voice.voice_id, "celebrity_impersonation", "Giả mạo người khác", reporter_email="anonymous@gmail.com"
        )
        assert rep2.status == "pending"

        await session.refresh(voice)
        assert voice.status == "reported"

        # When status is "reported", synthesizing throws 404
        with pytest.raises(AppError) as exc_info:
            await service.synthesize_cloned_voice(session, voice.voice_id, norm_user, "Thử đọc khi reported")
        assert exc_info.value.code == "VOICE_NOT_FOUND"

        # Admin restores status to "ready" to test forbidden synthesis by another user
        voice.status = "ready"
        await session.commit()

        # Other user cannot synthesize
        with pytest.raises(AppError) as exc_info:
            await service.synthesize_cloned_voice(session, voice.voice_id, other_user, "Dùng trái phép")
        assert exc_info.value.code == "FORBIDDEN_VOICE"

        # Admin can synthesize any voice
        synth_admin = await service.synthesize_cloned_voice(session, voice.voice_id, admin_user, "Admin synthesize")
        assert len(synth_admin) > 0

        # Admin can delete norm_user's voice
        del_admin_res = await service.delete_cloned_voice(session, voice.voice_id, admin_user)
        assert del_admin_res is True

        # Deleting again raises not found
        with pytest.raises(AppError) as exc_info:
            await service.delete_cloned_voice(session, voice.voice_id, admin_user)
        assert exc_info.value.code == "VOICE_NOT_FOUND"

