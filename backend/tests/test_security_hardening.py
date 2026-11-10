"""Kiểm thử toàn diện cho An ninh, Kiểm duyệt nội dung & Giám sát hệ thống (Issue #16)."""
import time
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.requests import Request

from app.core.logging import JSONLogFormatter, setup_logging
from app.core.rate_limiter import (
    check_job_creation_rate_limit,
    check_user_concurrent_jobs,
    reset_job_rate_limits,
)
from app.core.security_validation import (
    SecurityValidationError,
    safe_path_join,
    sanitize_filename,
    validate_audio_magic_bytes,
    validate_input_text,
    validate_password_strength,
)
from app.core.sentry import init_sentry
from app.core.totp import (
    generate_totp_code,
    generate_totp_secret,
    get_totp_uri,
    setup_admin_2fa,
    verify_totp_code,
)
from app.db import AsyncSessionLocal
from app.main import app
from app.models.generation import Generation
from app.models.user import User
from app.services.content_moderation_service import ContentModerationService

# ==============================================================================
# 1. Input Validation, Magic Bytes & Path Traversal Tests
# ==============================================================================

def test_audio_magic_bytes_validation():
    """Kiểm tra xác thực magic bytes file âm thanh thực tế, chống đổi đuôi file."""
    # 1. MP3 có ID3
    valid_id3 = b"ID3\x03\x00\x00\x00\x00\x00\x00" + b"\x00" * 50
    is_valid, mime, ext = validate_audio_magic_bytes(valid_id3)
    assert is_valid is True
    assert mime == "audio/mpeg"
    assert ext == ".mp3"

    # 2. MP3 frame sync (0xFF 0xFB)
    valid_sync = b"\xff\xfb\x90\x44" + b"\x00" * 50
    is_valid, mime, ext = validate_audio_magic_bytes(valid_sync)
    assert is_valid is True
    assert mime == "audio/mpeg"

    # 3. WAV (RIFF....WAVE)
    valid_wav = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 30
    is_valid, mime, ext = validate_audio_magic_bytes(valid_wav)
    assert is_valid is True
    assert mime == "audio/wav"
    assert ext == ".wav"

    # 4. OGG (OggS)
    valid_ogg = b"OggS\x00\x02\x00\x00" + b"\x00" * 30
    is_valid, mime, ext = validate_audio_magic_bytes(valid_ogg)
    assert is_valid is True
    assert mime == "audio/ogg"

    # 5. FLAC (fLaC)
    valid_flac = b"fLaC\x00\x00\x00\x22" + b"\x00" * 30
    is_valid, mime, ext = validate_audio_magic_bytes(valid_flac)
    assert is_valid is True
    assert mime == "audio/flac"

    # 6. M4A / MP4 (....ftyp)
    valid_m4a = b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 30
    is_valid, mime, ext = validate_audio_magic_bytes(valid_m4a)
    assert is_valid is True
    assert mime == "audio/mp4"

    # 7. WEBM (EBML \x1a\x45\xdf\xa3)
    valid_webm = b"\x1a\x45\xdf\xa3\x93\x42\x86" + b"\x00" * 30
    is_valid, mime, ext = validate_audio_magic_bytes(valid_webm)
    assert is_valid is True
    assert mime == "audio/webm"

    # 8. File giả mạo (Text script, PHP, Exe, Shell) đổi đuôi thành .mp3
    fake_exe = b"MZ\x90\x00\x03\x00\x00\x00"
    is_valid, _, _ = validate_audio_magic_bytes(fake_exe)
    assert is_valid is False

    fake_sh = b"#!/bin/bash\necho hack"
    is_valid, _, _ = validate_audio_magic_bytes(fake_sh)
    assert is_valid is False

    fake_php = b"<?php phpinfo(); ?>"
    is_valid, _, _ = validate_audio_magic_bytes(fake_php)
    assert is_valid is False

    # 9. Tệp rỗng hoặc quá ngắn
    assert validate_audio_magic_bytes(b"")[0] is False
    assert validate_audio_magic_bytes(b"12")[0] is False


def test_sanitize_filename_and_path_traversal():
    """Kiểm tra làm sạch tên file và chống tấn công Path Traversal."""
    # 1. Sanitize filename
    assert sanitize_filename("") == "upload.mp3"
    assert sanitize_filename("safe_voice.mp3") == "safe_voice.mp3"
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32\\cmd.exe") == "cmd.exe"
    assert sanitize_filename("my voice (sample) [1] #2!.mp3") == "my voice _sample_ _1_ _2_.mp3"
    assert sanitize_filename("....hack....mp3") == "hack.mp3"

    # 2. Safe path join
    base_dir = "/tmp/voxify_test_storage"
    safe_path = safe_path_join(base_dir, "samples", "user_1.mp3")
    assert str(safe_path) == "/tmp/voxify_test_storage/samples/user_1.mp3"

    # Chống Path Traversal cố tình thoát khỏi base_dir
    with pytest.raises(SecurityValidationError):
        safe_path_join(base_dir, "../../etc/shadow")

    with pytest.raises(SecurityValidationError):
        safe_path_join(base_dir, "sub", "..", "..", "secrets.json")


def test_password_strength_and_text_validation():
    """Kiểm tra chính sách mật khẩu mạnh và chuẩn hóa văn bản đầu vào."""
    # 1. Password strength
    assert validate_password_strength("short")[0] is False
    assert validate_password_strength("onlyletters")[0] is False
    assert validate_password_strength("123456789")[0] is False
    assert validate_password_strength("ValidPass123")[0] is True
    assert validate_password_strength("Password123!")[0] is True

    # 2. Text validation
    assert validate_input_text("  Xin chào thế giới  ") == "Xin chào thế giới"
    with pytest.raises(SecurityValidationError):
        validate_input_text("Hello\x00Hacked")

    with pytest.raises(SecurityValidationError):
        validate_input_text("a" * 1000, max_chars=500)


# ==============================================================================
# 2. TOTP (RFC 6238) 2FA Unit Tests
# ==============================================================================

def test_totp_rfc6238_generator_and_verifier():
    """Kiểm tra sinh và xác thực mã TOTP 6 số theo chuẩn RFC 6238."""
    secret = generate_totp_secret()
    assert len(secret) >= 16

    now = time.time()
    code = generate_totp_code(secret, timestamp=now)
    assert len(code) == 6
    assert code.isdigit()

    # Mã đúng
    assert verify_totp_code(secret, code, timestamp=now) is True

    # Mã đúng trong cửa sổ lệch ±30s
    assert verify_totp_code(secret, code, timestamp=now + 25) is True
    assert verify_totp_code(secret, code, timestamp=now - 25) is True

    # Mã sai hoàn toàn hoặc hết hạn quá lâu
    assert verify_totp_code(secret, "000000" if code != "000000" else "111111", timestamp=now) is False
    assert verify_totp_code(secret, code, timestamp=now + 120) is False
    assert verify_totp_code(secret, "short", timestamp=now) is False
    assert verify_totp_code("", code) is False

    # URI provisioning
    uri = get_totp_uri(secret, "admin@voxify.app", issuer="Voxify")
    assert "otpauth://totp/Voxify:admin%40voxify.app" in uri
    assert f"secret={secret}" in uri

    s_res, u_res = setup_admin_2fa("admin@voxify.app")
    assert len(s_res) >= 16
    assert "otpauth://" in u_res


# ==============================================================================
# 3. Content Moderation & 3-Strikes Auto-Ban Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_content_moderation_categories_and_evasion_bypass():
    """Kiểm tra bộ lọc từ khóa cấm, khử dấu và chống lách ký tự (leetspeak)."""
    # 1. Bạo lực / Vũ khí
    res1 = ContentModerationService.check_text("Hướng dẫn cách chế tạo bom xăng tự chế")
    assert res1.is_flagged is True
    assert res1.category == "VIOLENCE"

    # Lách ký tự dấu chấm: c.h.ế t.ạ.o b.o.m
    res1_evasion = ContentModerationService.check_text("c.h.e t.a.o b.o.m")
    assert res1_evasion.is_flagged is True

    # 2. Lừa đảo OTP / Ngân hàng
    res2 = ContentModerationService.check_text("Yêu cầu khách hàng cung cấp mã OTP ngay lập tức")
    assert res2.is_flagged is True
    assert res2.category == "FRAUD_SCAM"

    res2_scam = ContentModerationService.check_text("Chuyển tiền vào tài khoản an toàn của cơ quan điều tra")
    assert res2_scam.is_flagged is True

    # 3. Mạo danh chính trị gia / Nguyên thủ
    res3 = ContentModerationService.check_text("Thông điệp từ Thủ tướng Chính phủ gửi nhân dân")
    assert res3.is_flagged is True
    assert res3.category == "IMPERSONATION"

    # 4. Văn bản lành mạnh
    res_safe = ContentModerationService.check_text("Hôm nay trời rất đẹp, chúc bạn một ngày làm việc hiệu quả.")
    assert res_safe.is_flagged is False


@pytest.mark.asyncio
async def test_content_moderation_auto_ban_on_three_strikes():
    """Kiểm tra ghi log vi phạm và tự động khóa tài khoản sau 3 lần vi phạm."""
    async with AsyncSessionLocal() as db:
        user_email = f"abuser_{time.time()}@example.com"
        user = User(
            email=user_email,
            full_name="Bad Actor",
            role="user",
            is_active=True,
            violation_count=0,
            is_banned=False,
            credit_balance=5000,
            credits=5000,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Vi phạm lần 1: Bị chặn và cảnh báo 1/3
        with pytest.raises(Exception) as exc1:
            await ContentModerationService.check_and_enforce(
                db=db,
                text="Chế tạo bom tự chế",
                user=user,
                ip_address="192.168.1.50",
            )
        assert "1/3" in str(exc1.value.detail)  # type: ignore[attr-defined]
        assert user.violation_count == 1
        assert user.is_banned is False

        # Vi phạm lần 2: Bị chặn và cảnh báo 2/3
        with pytest.raises(Exception) as exc2:
            await ContentModerationService.check_and_enforce(
                db=db,
                text="Chuyển tiền vào tài khoản an toàn",
                user=user,
                ip_address="192.168.1.50",
            )
        assert "2/3" in str(exc2.value.detail)  # type: ignore[attr-defined]
        assert user.violation_count == 2
        assert user.is_banned is False

        # Vi phạm lần 3: Tự động KHÓA TÀI KHOẢN (Banned & Inactive)
        with pytest.raises(Exception) as exc3:
            await ContentModerationService.check_and_enforce(
                db=db,
                text="Cung cấp mã OTP ngân hàng",
                user=user,
                ip_address="192.168.1.50",
            )
        assert "đã bị khóa" in str(exc3.value.detail)  # type: ignore[attr-defined]
        assert user.violation_count == 3
        assert user.is_banned is True
        assert user.is_active is False


# ==============================================================================
# 4. Rate Limiting & Concurrency Controls
# ==============================================================================

@pytest.mark.asyncio
async def test_job_creation_rate_limiting_and_concurrency():
    """Kiểm tra giới hạn tần suất tạo job và số job đồng thời."""
    reset_job_rate_limits()

    # Giả lập request
    mock_request = Request({"type": "http", "method": "POST", "headers": [], "client": ("127.0.0.1", 12345)})

    # Gọi trong giới hạn 5 lần
    for _ in range(5):
        check_job_creation_rate_limit(mock_request, user_id=999, max_requests=5, window_seconds=60)

    # Lần thứ 6: Vượt ngưỡng -> HTTP 429
    with pytest.raises(Exception) as exc:
        check_job_creation_rate_limit(mock_request, user_id=999, max_requests=5, window_seconds=60)
    assert exc.value.status_code == 429  # type: ignore[attr-defined]

    # Kiểm tra giới hạn concurrent jobs trong DB
    async with AsyncSessionLocal() as db:
        test_uid = int(time.time()) % 1000000 + 1000
        # Tạo 2 jobs đang xử lý
        j1 = Generation(user_id=test_uid, text="t1", voice="v1", char_count=2, status="queued")
        j2 = Generation(user_id=test_uid, text="t2", voice="v1", char_count=2, status="processing")
        db.add_all([j1, j2])
        await db.commit()

        # Free tier giới hạn tối đa 2 job đồng thời -> ném HTTP 429
        with pytest.raises(Exception) as exc_conc:
            await check_user_concurrent_jobs(db, user_id=test_uid, plan_tier="free")
        assert exc_conc.value.status_code == 429  # type: ignore[attr-defined]
        assert "tác vụ cùng lúc" in str(exc_conc.value.detail)  # type: ignore[attr-defined]

        # Pro tier (giới hạn 5) -> cho phép bình thường
        await check_user_concurrent_jobs(db, user_id=test_uid, plan_tier="pro")


# ==============================================================================
# 5. Integration API Tests: Security Headers, Health & Metrics, 2FA
# ==============================================================================

@pytest.mark.asyncio
async def test_security_headers_and_health_and_metrics():
    """Kiểm tra Security Headers, endpoint /health chi tiết và /metrics Prometheus."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health check chi tiết
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        h_data = res_health.json()
        assert h_data["status"] == "ok"
        assert "database" in h_data
        assert h_data["database"]["status"] == "ok"
        assert "uptime_seconds" in h_data
        assert "storage" in h_data

        # 2. Security Headers có mặt trong phản hồi HTTP
        headers = res_health.headers
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert "max-age=31536000" in headers.get("Strict-Transport-Security", "")
        assert "default-src" in headers.get("Content-Security-Policy", "")

        # 3. Prometheus metrics
        res_metrics = await client.get("/metrics")
        assert res_metrics.status_code == 200
        assert "text/plain" in res_metrics.headers["content-type"]
        metrics_text = res_metrics.text
        assert "voxify_http_requests_total" in metrics_text
        assert "voxify_active_jobs_current" in metrics_text


@pytest.mark.asyncio
async def test_admin_2fa_full_lifecycle():
    """Kiểm tra toàn bộ chu trình 2FA: setup, verify code sai, enable, login 2fa và disable."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Đăng ký tài khoản
        email = f"admin2fa_{time.time()}@example.com"
        reg_res = await client.post(
            "/api/auth/register",
            json={"email": email, "password": "StrongPassword123!", "full_name": "Admin 2FA"},
        )
        assert reg_res.status_code == 200

        # Đăng nhập lấy token ban đầu
        login_res = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "StrongPassword123!"},
        )
        token = login_res.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}

        # 2. Setup 2FA
        setup_res = await client.post("/api/auth/2fa/setup", headers=auth_headers)
        assert setup_res.status_code == 200
        setup_data = setup_res.json()
        secret = setup_data["secret"]
        assert "qr_uri" in setup_data
        assert len(secret) >= 16

        # 3. Kích hoạt với mã sai -> Bị từ chối
        bad_enable = await client.post("/api/auth/2fa/enable", json={"code": "000000"}, headers=auth_headers)
        assert bad_enable.status_code == 400

        # 4. Kích hoạt với mã đúng
        valid_code = generate_totp_code(secret)
        good_enable = await client.post("/api/auth/2fa/enable", json={"code": valid_code}, headers=auth_headers)
        assert good_enable.status_code == 200

        # 5. Đăng nhập lại khi đã bật 2FA -> Trả về requires_2fa=True kèm temp_token
        login_2fa_prompt = await client.post(
            "/api/auth/login",
            json={"email": email, "password": "StrongPassword123!"},
        )
        assert login_2fa_prompt.status_code == 200
        p_data = login_2fa_prompt.json()
        assert p_data["requires_2fa"] is True
        temp_token = p_data["temp_token"]
        assert temp_token is not None

        # 6. Xác thực bước 2 qua /2fa/verify
        login_verify_res = await client.post(
            "/api/auth/2fa/verify",
            json={"code": generate_totp_code(secret), "temp_token": temp_token},
        )
        assert login_verify_res.status_code == 200
        final_token = login_verify_res.json()["access_token"]
        assert final_token != ""

        # 7. Tắt 2FA
        disable_res = await client.post(
            "/api/auth/2fa/disable",
            json={"code": generate_totp_code(secret)},
            headers={"Authorization": f"Bearer {final_token}"},
        )
        assert disable_res.status_code == 200


@pytest.mark.asyncio
async def test_structured_logging_and_sentry_init():
    """Kiểm tra Structured JSON Logging formatter và Sentry initialization."""
    # 1. JSONLogFormatter
    formatter = JSONLogFormatter()
    import logging
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test structured log message",
        args=(),
        exc_info=None,
    )
    formatted_json = formatter.format(record)
    assert '"level": "INFO"' in formatted_json
    assert '"message": "Test structured log message"' in formatted_json
    assert '"timestamp":' in formatted_json

    # setup_logging with json format
    setup_logging(level="INFO", log_format="json")
    setup_logging(level="INFO", log_format="text")

    # 2. Sentry
    assert init_sentry(None) is False
    assert init_sentry("") is False
    # Giả lập Sentry DSN hợp lệ
    from unittest.mock import MagicMock
    mock_sentry = MagicMock()
    with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
        assert init_sentry("https://public@sentry.example.com/1") is True
