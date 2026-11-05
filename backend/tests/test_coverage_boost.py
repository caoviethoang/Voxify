"""Comprehensive tests to boost coverage >= 80% (CreditService >= 90%)."""
import asyncio
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.email import _send_email_or_log, send_password_reset_email, send_verification_email
from app.core.errors import AppError
from app.core.security import create_timed_token, hash_password
from app.db import AsyncSessionLocal
from app.main import app
from app.models.user import User
from app.providers.edge import EdgeTTSProvider, _split_into_micro_chunks
from app.services.audio_service import AudioService
from app.services.auth_service import AuthService
from app.services.credit_service import CreditService, CreditTransactionType, InsufficientCreditsError
from app.services.dictionary_service import DictionaryService
from app.services.payment_service import PaymentService
from app.services.storage_service import StorageService
from app.services.text_splitter import split_text_into_chunks
from app.storage.local import LocalStorage


@pytest.mark.unit
@pytest.mark.asyncio
async def test_credit_service_edge_cases():
    """Kiểm tra toàn bộ các nhánh edge case của CreditService để đạt >= 90% coverage."""
    async with AsyncSessionLocal() as db:
        # 1. calculate_cost với ký tự <= 0
        assert CreditService.calculate_cost(0) == 0
        assert CreditService.calculate_cost(-10) == 0

        # Hệ số nhân
        assert CreditService.calculate_cost(100, provider="edge") == 100
        assert CreditService.calculate_cost(100, provider="azure") >= 100
        assert CreditService.calculate_cost(100, provider="elevenlabs") >= 200

        # 2. Tạo user mẫu với balance = 0
        email = f"credit_edge_{time.time()}@example.com"
        user = User(
            email=email,
            hashed_password=hash_password("Pass123!"),
            full_name="Credit Edge User",
            credit_balance=0,
            credits=0,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Nạp ban đầu 1000 qua adjustment
        await CreditService.add_adjustment(
            db, user.id, 1000, tx_type=CreditTransactionType.SIGNUP_BONUS.value, description="Init"
        )

        # 3. reserve với amount < 0 -> ValueError
        with pytest.raises(ValueError, match="số dương"):
            await CreditService.reserve(db, user.id, -50)

        # 4. reserve với amount == 0 (miễn phí)
        tx_free = await CreditService.reserve(db, user.id, 0, description="Free preview")
        assert tx_free.amount == 0
        assert tx_free.balance_after == 1000

        # 5. reserve với user_id không tồn tại
        with pytest.raises(AppError):
            await CreditService.reserve(db, 999999, 100)

        # 6. refund với amount <= 0 -> ValueError
        with pytest.raises(ValueError, match="lớn hơn 0"):
            await CreditService.refund(db, user.id, 0)
        with pytest.raises(ValueError, match="lớn hơn 0"):
            await CreditService.refund(db, user.id, -20)

        # 7. refund với user_id không tồn tại
        with pytest.raises(AppError):
            await CreditService.refund(db, 999999, 50)

        # 8. add_signup_bonus với user_id không tồn tại
        with pytest.raises(AppError):
            await CreditService.add_signup_bonus(db, 999999)

        # 9. add_adjustment nạp tiền purchase (+500)
        tx_adj = await CreditService.add_adjustment(
            db, user.id, 500, tx_type=CreditTransactionType.PURCHASE.value, description="Top-up"
        )
        assert tx_adj.amount == 500
        assert tx_adj.balance_after == 1500

        # 10. add_adjustment trừ tiền hợp lệ (-200)
        tx_sub = await CreditService.add_adjustment(
            db, user.id, -200, tx_type=CreditTransactionType.ADMIN_ADJUST.value, description="Deduct"
        )
        assert tx_sub.amount == -200
        assert tx_sub.balance_after == 1300

        # 11. add_adjustment làm âm số dư -> InsufficientCreditsError
        with pytest.raises(InsufficientCreditsError):
            await CreditService.add_adjustment(db, user.id, -5000)

        # 12. add_adjustment với user_id không tồn tại
        with pytest.raises(AppError):
            await CreditService.add_adjustment(db, 999999, 100)

        # 13. get_balance với user không tồn tại -> 0
        assert await CreditService.get_balance(db, 999999) == 0

        # 14. verify_ledger khớp
        ledger_sum, cached, is_match = await CreditService.verify_ledger(db, user.id)
        assert is_match is True
        assert cached == 1300
        assert ledger_sum == 1300

        # 15. list_transactions
        txs, total_count = await CreditService.list_transactions(db, user.id, page=1, limit=10)
        assert total_count >= 3
        assert len(txs) >= 3

        # list_transactions lọc theo type
        txs_purchase, p_count = await CreditService.list_transactions(
            db, user.id, page=1, limit=10, tx_type=CreditTransactionType.PURCHASE.value
        )
        assert p_count >= 1
        assert all(t.type == CreditTransactionType.PURCHASE.value for t in txs_purchase)

        # 16. verify_ledger không khớp khi database bị can thiệp
        user.credit_balance = 9999
        await db.commit()
        l_sum, c_bal, mismatch = await CreditService.verify_ledger(db, user.id)
        assert mismatch is False
        assert l_sum == 1300
        assert c_bal == 9999


@pytest.mark.unit
def test_text_splitter_edge_cases():
    """Kiểm tra toàn diện thuật toán ngắt đoạn văn bản."""
    # Văn bản rỗng / whitespace
    assert split_text_into_chunks("") == []
    assert split_text_into_chunks("   \n\t  ") == []

    # Văn bản ngắn hơn max_chunk_size
    short = "Xin chào các bạn."
    assert split_text_into_chunks(short, max_chunk_size=100) == [short]

    # Văn bản nhiều câu có dấu tiếng Việt
    vietnamese_text = (
        "Hôm nay trời rất đẹp ở Hà Nội! Bạn có muốn đi dạo quanh Hồ Gươm không? "
        "Chắc chắn sẽ có nhiều kỷ niệm đáng nhớ… Hãy cùng chuẩn bị nhé."
    )
    chunks = split_text_into_chunks(vietnamese_text, max_chunk_size=70)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 70

    # Một câu siêu dài không có dấu chấm nhưng có dấu cách
    long_sentence = "từ " * 50
    chunks_long = split_text_into_chunks(long_sentence, max_chunk_size=40)
    assert len(chunks_long) >= 2
    for c in chunks_long:
        assert len(c) <= 40

    # Một từ siêu dài vượt max_chunk_size (không có khoảng trắng)
    ultra_word = "A" * 150
    chunks_word = split_text_into_chunks(ultra_word, max_chunk_size=50)
    assert len(chunks_word) == 3
    assert "".join(chunks_word) == ultra_word


@pytest.mark.unit
@pytest.mark.asyncio
async def test_audio_service_utilities(tmp_path):
    """Kiểm tra các hàm đo thời lượng, tạo phụ đề và xử lý âm thanh."""
    # measure_duration trên file không tồn tại
    assert AudioService.measure_duration("/non/existent/path.mp3") == 0.0

    # measure_duration trên file có thật (fallback đo kích thước)
    sample_file = tmp_path / "dummy.mp3"
    sample_file.write_bytes(b"\x00" * 12000)
    duration = AudioService.measure_duration(str(sample_file))
    assert duration == 2.0  # 12000 / 6000 = 2.0s

    # generate_subtitles và generate_estimated_subtitles
    srt_out = str(tmp_path / "test.srt")
    vtt_out = str(tmp_path / "test.vtt")

    segments = [
        {"text": "Câu thứ nhất.", "start": 0.0, "end": 1.5},
        {"text": "Câu thứ hai.", "start": 1.5, "end": 3.0},
    ]
    AudioService.generate_subtitles(segments, srt_out, vtt_out)
    assert Path(srt_out).exists()
    assert Path(vtt_out).exists()
    assert "00:00:00,000 --> 00:00:01,500" in Path(srt_out).read_text(encoding="utf-8")
    assert "WEBVTT" in Path(vtt_out).read_text(encoding="utf-8")

    # generate_estimated_subtitles
    srt_est = str(tmp_path / "est.srt")
    vtt_est = str(tmp_path / "est.vtt")
    AudioService.generate_estimated_subtitles("Chào buổi sáng! Hôm nay thế nào?", 4.0, srt_est, vtt_est)
    assert Path(srt_est).exists()
    assert Path(vtt_est).exists()

    # generate_silence
    silence_out = str(tmp_path / "silence.mp3")
    await AudioService.generate_silence(0.5, silence_out)
    assert Path(silence_out).exists()
    assert Path(silence_out).stat().st_size > 0

    # concat_audio_files với 1 file
    concat_out = str(tmp_path / "concat.mp3")
    res_path, dur, sz = await AudioService.concat_audio_files([silence_out], concat_out, target_format="mp3")
    assert Path(res_path).exists()
    assert sz > 0

    # concat_audio_files với danh sách rỗng -> ValueError
    with pytest.raises(ValueError):
        await AudioService.concat_audio_files([], concat_out)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_and_permissions_contract():
    """Kiểm tra hợp đồng phân quyền và các trường hợp lỗi xác thực API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Gọi endpoint yêu cầu auth không kèm token -> 401
        res_no_auth = await client.get("/api/me")
        assert res_no_auth.status_code == 401

        res_history_no_auth = await client.get("/api/history")
        assert res_history_no_auth.status_code == 401

        res_dashboard_no_auth = await client.get("/api/dashboard/stats")
        assert res_dashboard_no_auth.status_code == 401

        # 2. Token không hợp lệ -> 401
        res_bad_token = await client.get("/api/me", headers={"Authorization": "Bearer invalid_jwt_token"})
        assert res_bad_token.status_code == 401

        # 3. Đăng nhập sai mật khẩu -> 401
        email = f"auth_test_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": email,
            "password": "CorrectPassword123!",
            "full_name": "Auth Tester",
        })
        res_wrong_pw = await client.post("/api/auth/login", json={
            "email": email,
            "password": "WrongPassword!",
        })
        assert res_wrong_pw.status_code == 401

        # 4. Đăng nhập email không tồn tại -> 401
        res_no_user = await client.post("/api/auth/login", json={
            "email": "notfound@example.com",
            "password": "Password123!",
        })
        assert res_no_user.status_code == 401

        # 5. Đăng ký email không hợp lệ -> 422
        res_bad_email = await client.post("/api/auth/register", json={
            "email": "not-an-email",
            "password": "Password123!",
        })
        assert res_bad_email.status_code == 422

        # 6. Đăng ký mật khẩu quá ngắn -> 422
        res_short_pw = await client.post("/api/auth/register", json={
            "email": f"short_{time.time()}@example.com",
            "password": "123",
        })
        assert res_short_pw.status_code == 422

        # 7. Đăng nhập thành công và lấy token
        login_res = await client.post("/api/auth/login", json={
            "email": email,
            "password": "CorrectPassword123!",
        })
        assert login_res.status_code == 200
        user_token = login_res.json()["access_token"]
        headers_user = {"Authorization": f"Bearer {user_token}"}

        # 8. Người dùng bình thường không thể truy cập tài nguyên của người khác
        # Tạo bản ghi history của user khác
        async with AsyncSessionLocal() as db:
            from app.models.generation import Generation
            gen_other = Generation(
                user_id=999998,
                text="Private text of other user",
                voice="vi-VN-HoaiMyNeural",
                char_count=26,
                status="done",
            )
            db.add(gen_other)
            await db.commit()
            await db.refresh(gen_other)
            other_gen_id = gen_other.id

        # User cố tình PATCH tiêu đề của user khác -> 403
        res_patch_other = await client.patch(
            f"/api/history/{other_gen_id}",
            headers=headers_user,
            json={"title": "Hacked Title"},
        )
        assert res_patch_other.status_code == 403

        # User cố tình DELETE của user khác -> 403
        res_del_other = await client.delete(
            f"/api/history/{other_gen_id}",
            headers=headers_user,
        )
        assert res_del_other.status_code == 403

        # 9. Healthcheck endpoint công khai -> 200
        res_health = await client.get("/health")
        assert res_health.status_code == 200
        assert res_health.json()["status"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_advanced_flows():
    """Kiểm tra luồng xác thực: refresh, logout, me, reset pass và verify email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"auth_adv_{time.time()}@example.com"
        # 1. Đăng ký & Đăng nhập
        reg = await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Adv User",
        })
        assert reg.status_code == 200

        login = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        assert login.status_code == 200
        data = login.json()
        token = data["access_token"]
        refresh_token = login.cookies.get("refresh_token")
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Lấy thông tin me
        me_res = await client.get("/api/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == email

        # 3. Refresh token flow
        if refresh_token:
            client.cookies.set("refresh_token", refresh_token)
            ref_res = await client.post("/api/auth/refresh")
            assert ref_res.status_code == 200
            assert "access_token" in ref_res.json()

        # 4. Refresh token rỗng -> 401
        client_no_cookie = AsyncClient(transport=transport, base_url="http://test")
        res_no_rf = await client_no_cookie.post("/api/auth/refresh")
        assert res_no_rf.status_code == 401

        # 5. Forgot password
        forgot_res = await client.post("/api/auth/forgot-password", json={"email": email})
        assert forgot_res.status_code == 200

        # 6. Đăng xuất
        logout_res = await client.post("/api/auth/logout", headers=headers)
        assert logout_res.status_code == 200

    # 7. AuthService direct unit tests for Google login, reset password, verify email
    async with AsyncSessionLocal() as db:
        # Mock Google auth
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_google:
            mock_google.return_value = {
                "sub": f"google_{time.time()}",
                "email": f"google_{time.time()}@example.com",
                "name": "Google User",
            }
            g_user = await AuthService.authenticate_google(db, "fake_google_credential")
            assert g_user.email.startswith("google_")
            assert g_user.is_verified is True

        # Test reset password with valid token
        reset_email = f"reset_{time.time()}@example.com"
        user_to_reset = await AuthService.register(db, reset_email, "OldPass123!", "Reset User")
        reset_tok = create_timed_token({"sub": reset_email}, token_type="reset_password", expires_minutes=15)
        await AuthService.reset_password(db, reset_tok, "NewPasswordPass999!")

        # Verify new password
        auth_reset = await AuthService.authenticate(db, reset_email, "NewPasswordPass999!")
        assert auth_reset.id == user_to_reset.id

        # Test reset password with invalid token -> ValueError
        with pytest.raises(ValueError):
            await AuthService.reset_password(db, "invalid_reset_token", "Foo123!")

        # Test email verification token
        verify_tok = create_timed_token({"sub": reset_email}, token_type="verify_email", expires_minutes=15)
        await AuthService.verify_email_token(db, verify_tok)

        # Test invalid email verification token
        with pytest.raises(ValueError):
            await AuthService.verify_email_token(db, "invalid_verify_token")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dictionary_full_lifecycle():
    """Kiểm tra toàn bộ CRUD và nghiệp vụ từ điển quy tắc phát âm."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"dict_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Dict User",
        })
        login_res = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Tạo từ điển mới
        create_res = await client.post("/api/dictionary", headers=headers, json={
            "word": "AI",
            "replacement": "Ây Ai",
        })
        assert create_res.status_code == 201
        entry = create_res.json()
        entry_id = entry["id"]
        assert entry["word"] == "AI"
        assert entry["replacement"] == "Ây Ai"

        # 2. Tạo từ rỗng -> 422
        bad_res = await client.post("/api/dictionary", headers=headers, json={
            "word": "",
            "replacement": "Rỗng",
        })
        assert bad_res.status_code == 422

        # 3. Lấy danh sách từ điển
        list_res = await client.get("/api/dictionary", headers=headers)
        assert list_res.status_code == 200
        items = list_res.json()
        assert any(item["id"] == entry_id for item in items)

        # 4. Sửa từ điển
        update_res = await client.put(f"/api/dictionary/{entry_id}", headers=headers, json={
            "replacement": "Trí thông minh nhân tạo",
        })
        assert update_res.status_code == 200
        assert update_res.json()["replacement"] == "Trí thông minh nhân tạo"

        # 5. Xoá từ điển
        del_res = await client.delete(f"/api/dictionary/{entry_id}", headers=headers)
        assert del_res.status_code == 200

        # Xoá từ không tồn tại -> 404
        del_404 = await client.delete(f"/api/dictionary/{entry_id}", headers=headers)
        assert del_404.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tts_job_downloads_and_subtitles():
    """Kiểm tra tải về audio, phụ đề SRT, VTT và quản lý tiến trình job."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"tts_download_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "TTS Download User",
        })
        login_res = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Tạo job tổng hợp bất đồng bộ
        create_res = await client.post("/api/tts/jobs", headers=headers, json={
            "text": "Chào bạn, đây là bản thử nghiệm tải phụ đề và file âm thanh.",
            "voice": "vi-VN-HoaiMyNeural",
            "rate": "+0%",
            "pitch": "+0Hz",
            "format": "mp3",
        })
        assert create_res.status_code == 202
        job_data = create_res.json()
        job_id = job_data["id"]

        # Chờ job hoàn thành
        for _ in range(25):
            status_res = await client.get(f"/api/tts/jobs/{job_id}", headers=headers)
            assert status_res.status_code == 200
            st = status_res.json()["status"]
            if st in ("completed", "failed"):
                break
            await asyncio.sleep(0.3)

        # Tải audio
        audio_res = await client.get(f"/api/tts/jobs/{job_id}/audio", headers=headers)
        assert audio_res.status_code in (200, 206)

        # Tải SRT phụ đề
        srt_res = await client.get(f"/api/tts/jobs/{job_id}/subtitles?format=srt", headers=headers)
        assert srt_res.status_code == 200

        # Tải VTT phụ đề
        vtt_res = await client.get(f"/api/tts/jobs/{job_id}/subtitles?format=vtt", headers=headers)
        assert vtt_res.status_code == 200

        # Lấy danh sách jobs
        jobs_res = await client.get("/api/tts/jobs", headers=headers)
        assert jobs_res.status_code == 200
        assert any(j["id"] == job_id for j in jobs_res.json())


@pytest.mark.integration
@pytest.mark.asyncio
async def test_history_bulk_delete_and_filters():
    """Kiểm tra xóa hàng loạt và các bộ lọc lịch sử (status, search, format, date, preview)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"history_bulk_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "History User",
        })
        login_res = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Tạo 2 bản ghi qua DB
        async with AsyncSessionLocal() as db:
            from app.models.generation import Generation
            user = (await AuthService.get_user_by_email(db, email))
            g1 = Generation(
                user_id=user.id,
                text="Học tiếng Anh mỗi ngày",
                voice="vi-VN-HoaiMyNeural",
                status="done",
                format="mp3",
                is_preview=False,
                char_count=23,
            )
            g2 = Generation(
                user_id=user.id,
                text="Nghe thử đoạn ngắn",
                voice="vi-VN-HoaiMyNeural",
                status="done",
                format="mp3",
                is_preview=True,
                char_count=18,
            )
            db.add_all([g1, g2])
            await db.commit()
            await db.refresh(g1)
            await db.refresh(g2)
            g1_id, g2_id = g1.id, g2.id

        # Lọc theo search
        res_search = await client.get("/api/history?search=tiếng+Anh", headers=headers)
        assert res_search.status_code == 200
        assert any(item["id"] == g1_id for item in res_search.json()["items"])

        # Lọc theo preview=True
        res_prev = await client.get("/api/history?is_preview=true", headers=headers)
        assert res_prev.status_code == 200
        assert any(item["id"] == g2_id for item in res_prev.json()["items"])

        # Lọc theo status và format
        res_flt = await client.get("/api/history?status=done&format=mp3", headers=headers)
        assert res_flt.status_code == 200

        # Lọc theo ngày hợp lệ và không hợp lệ
        res_date = await client.get("/api/history?date_from=2020-01-01T00:00:00&date_to=invalid-date", headers=headers)
        assert res_date.status_code == 200

        # Bulk delete
        del_bulk = await client.request(
            "DELETE",
            "/api/history/bulk",
            headers=headers,
            json={"ids": [g1_id, g2_id]},
        )
        assert del_bulk.status_code == 200
        assert del_bulk.json()["deleted"] >= 1

        # Các nhánh 404 của history
        assert (await client.delete("/api/history/999999", headers=headers)).status_code == 404
        assert (await client.get("/api/history/999999/download", headers=headers)).status_code == 404
        assert (await client.get("/api/history/999999/subtitles", headers=headers)).status_code == 404

        # Các nhánh 404 của dictionary
        assert (await client.delete("/api/dictionary/999999", headers=headers)).status_code == 404
        assert (await client.put("/api/dictionary/999999", headers=headers, json={"pattern": "test", "replacement": "test"})).status_code == 404


@pytest.mark.unit
def test_email_notifications():
    """Kiểm tra dịch vụ gửi email giả lập dev và kết nối SMTP."""
    # 1. Dev mode (không có smtp_host cấu hình)
    send_password_reset_email("test_reset@example.com", "dummy_token_123")
    send_verification_email("test_verify@example.com", "dummy_token_456")

    # 2. Mock SMTP mode
    with patch("app.core.email.get_settings") as mock_settings:
        mock_settings.return_value.smtp_host = "smtp.example.com"
        mock_settings.return_value.smtp_port = 587
        mock_settings.return_value.smtp_user = "user@example.com"
        mock_settings.return_value.smtp_password = "password"
        mock_settings.return_value.emails_from = "noreply@voxify.vn"
        mock_settings.return_value.app_name = "Voxify"

        with patch("smtplib.SMTP") as mock_smtp:
            server_mock = MagicMock()
            mock_smtp.return_value.__enter__.return_value = server_mock
            _send_email_or_log("mock_smtp@example.com", "Test Subject", "Test Body", "https://voxify.vn", "TEST TAG")
            server_mock.starttls.assert_called_once()
            server_mock.send_message.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tts_job_failure_and_auto_refund(use_fake_tts):
    """Kiểm tra khi job nền gặp sự cố, credit phải được tự động hoàn lại 100%."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"tts_refund_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Refund User",
        })
        login_res = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Lấy số dư ban đầu
        me_before = await client.get("/api/auth/me", headers=headers)
        bal_before = me_before.json()["credits"]

        # Kích hoạt lỗi giả lập trên FakeTTSProvider instance
        use_fake_tts.simulate_error = True
        try:
            create_res = await client.post("/api/tts/jobs", headers=headers, json={
                "text": "Đoạn văn này sẽ bị lỗi để kiểm tra hoàn tiền tự động.",
                "voice": "vi-VN-HoaiMyNeural",
            })
            assert create_res.status_code == 202
            job_id = create_res.json()["id"]

            # Chờ job xử lý thất bại
            for _ in range(25):
                status_res = await client.get(f"/api/tts/jobs/{job_id}", headers=headers)
                assert status_res.status_code == 200
                st = status_res.json()["status"]
                if st == "failed":
                    break
                await asyncio.sleep(0.3)

            assert status_res.json()["status"] == "failed"

            # Kiểm tra credit đã được hoàn lại đầy đủ
            me_after = await client.get("/api/auth/me", headers=headers)
            bal_after = me_after.json()["credits"]
            assert bal_after == bal_before
        finally:
            use_fake_tts.simulate_error = False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tts_validation_and_insufficient_credits():
    """Kiểm tra xác thực đầu vào và từ chối khi không đủ credit."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"tts_val_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Validation User",
        })
        login_res = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Text rỗng khi gọi /api/tts/jobs -> 422 hoặc 400
        res_empty = await client.post("/api/tts/jobs", headers=headers, json={
            "text": "   ",
            "voice": "vi-VN-HoaiMyNeural",
        })
        assert res_empty.status_code in (400, 422)

        # 2. Text quá 100.000 ký tự -> 400
        res_too_long = await client.post("/api/tts/jobs", headers=headers, json={
            "text": "A" * 100001,
            "voice": "vi-VN-HoaiMyNeural",
        })
        assert res_too_long.status_code == 400

        # 3. Không đủ credit: Trừ hết credit của user trước
        async with AsyncSessionLocal() as db:
            user = await AuthService.get_user_by_email(db, email)
            user.credit_balance = 0
            user.credits = 0
            await db.commit()

        res_no_cred = await client.post("/api/tts/jobs", headers=headers, json={
            "text": "Tôi muốn tạo giọng nói nhưng không còn credit nào.",
            "voice": "vi-VN-HoaiMyNeural",
        })
        assert res_no_cred.status_code == 402


@pytest.mark.unit
@pytest.mark.asyncio
async def test_storage_service_and_backend(tmp_path):
    """Kiểm tra LocalStorage và StorageService lưu/xóa file."""
    storage = LocalStorage()
    saved_path = await storage.save(b"sample audio payload", "unit_test_audio.mp3")
    assert Path(saved_path).exists()

    url = await storage.get_url(saved_path)
    assert "unit_test_audio.mp3" in url

    await storage.delete(saved_path)
    assert not Path(saved_path).exists()

    # StorageService wrapper
    svc = StorageService(backend=storage)
    path2, sz = await svc.save_audio(b"binary content", "vi-VN-HoaiMyNeural", is_preview=True)
    assert Path(path2).exists()
    assert sz == len(b"binary content")
    await storage.delete(path2)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dictionary_toggle_and_complex_rules():
    """Kiểm tra bật/tắt quy tắc từ điển và thay thế ký tự đặc biệt."""
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"dict_toggle_{time.time()}@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Dict Toggle User",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # 1. Thêm từ có ký tự đặc biệt (non-word, ví dụ C#)
        rule = await DictionaryService.create_rule(db, user.id, "C#", "C-Sharp", category="tech")
        assert rule.id is not None

        # 2. Toggle rule thành Inactive
        toggled = await DictionaryService.toggle_rule(db, user.id, rule.id, False)
        assert toggled.is_active is False

        # Khi inactive, không thay thế
        out_inactive = await DictionaryService.apply_dictionary(db, user.id, "Tôi lập trình bằng C#")
        assert out_inactive == "Tôi lập trình bằng C#"

        # 3. Toggle lại thành Active
        await DictionaryService.toggle_rule(db, user.id, rule.id, True)
        out_active = await DictionaryService.apply_dictionary(db, user.id, "Tôi lập trình bằng C#")
        assert "C-Sharp" in out_active

        # 4. Toggle rule không tồn tại -> None
        assert await DictionaryService.toggle_rule(db, user.id, 999999, True) is None

        # 5. apply_dictionary với user_id None hoặc text rỗng
        assert await DictionaryService.apply_dictionary(db, None, "test") == "test"
        assert await DictionaryService.apply_dictionary(db, user.id, "") == ""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_routes_extra():
    """Kiểm tra các endpoint route auth còn thiếu: google, reset-pass, verify-email."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Google login qua route với mock
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_google:
            mock_google.return_value = {
                "sub": f"g_route_{time.time()}",
                "email": f"g_route_{time.time()}@example.com",
                "name": "Google Route User",
            }
            res_g = await client.post("/api/auth/google", json={"credential": "valid_mocked_token"})
            assert res_g.status_code == 200
            assert "access_token" in res_g.json()

        # 2. Reset password qua route
        reset_email = f"reset_route_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": reset_email,
            "password": "InitialPassword123!",
            "full_name": "Reset Route",
        })
        tok = create_timed_token({"sub": reset_email}, token_type="reset_password", expires_minutes=15)
        res_reset = await client.post("/api/auth/reset-password", json={
            "token": tok,
            "new_password": "NewUpdatedPassword789!",
        })
        assert res_reset.status_code == 200

        # 2b. Reset password với token không hợp lệ -> 400
        res_reset_bad = await client.post("/api/auth/reset-password", json={
            "token": "invalid_jwt_token_format",
            "new_password": "NewUpdatedPassword789!",
        })
        assert res_reset_bad.status_code == 400

        # 3. Verify email qua route
        vtok = create_timed_token({"sub": reset_email}, token_type="verify_email", expires_minutes=15)
        res_ver = await client.get(f"/api/auth/verify-email?token={vtok}")
        assert res_ver.status_code == 200

        # 3b. Verify email với token không hợp lệ -> 400
        res_ver_bad = await client.get("/api/auth/verify-email?token=invalid_token")
        assert res_ver_bad.status_code == 400

        # 4. Refresh token không có cookie -> 401
        client.cookies.clear()
        res_ref_no_cookie = await client.post("/api/auth/refresh")
        assert res_ref_no_cookie.status_code == 401

        # 5. Refresh token với cookie sai -> 401
        res_ref_bad_cookie = await client.post("/api/auth/refresh", cookies={"refresh_token": "bad_token"})
        assert res_ref_bad_cookie.status_code == 401

        # 6. Logout xóa cookie -> 200
        res_logout = await client.post("/api/auth/logout", cookies={"refresh_token": "some_token"})
        assert res_logout.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tts_routes_additional_branches():
    """Kiểm tra các nhánh 404, tải download=True và tổng hợp TTS đồng bộ có đăng nhập."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"tts_extra_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "TTS Extra User",
        })
        login_res = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Tra cứu job không tồn tại -> 404
        assert (await client.get("/api/tts/jobs/999999", headers=headers)).status_code == 404
        assert (await client.get("/api/tts/jobs/999999/audio", headers=headers)).status_code == 404
        assert (await client.get("/api/tts/jobs/999999/subtitles", headers=headers)).status_code == 404

        # 2. Tạo job hợp lệ để test download=True
        create_res = await client.post("/api/tts/jobs", headers=headers, json={
            "text": "Bản ghi âm kiểm tra tham số download attachment.",
            "voice": "vi-VN-HoaiMyNeural",
        })
        job_id = create_res.json()["id"]
        for _ in range(25):
            st_res = await client.get(f"/api/tts/jobs/{job_id}", headers=headers)
            if st_res.json()["status"] == "done":
                break
            await asyncio.sleep(0.3)

        dl_res = await client.get(f"/api/tts/jobs/{job_id}/audio?download=true", headers=headers)
        assert dl_res.status_code == 200
        assert "attachment" in dl_res.headers.get("content-disposition", "")

        # 3. Gọi /api/tts đồng bộ (không preview) khi user đã đăng nhập -> trừ credit và trả MP3
        sync_res = await client.post("/api/tts", headers=headers, json={
            "text": "Đọc đồng bộ và trừ credit của tài khoản.",
            "voice": "vi-VN-HoaiMyNeural",
            "preview": False,
        })
        assert sync_res.status_code == 200
        assert sync_res.headers.get("content-type") == "audio/mpeg"
        assert int(sync_res.headers.get("x-credit-used", 0)) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_and_dictionary_error_branches():
    """Kiểm tra các nhánh lỗi HTTP 400, 401, 404 cho routes auth và dictionary."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Google login sai credential -> 400
        res_g_bad = await client.post("/api/auth/google", json={"credential": "invalid_credential"})
        assert res_g_bad.status_code == 400

        # 2. Refresh token sai -> 401
        client.cookies.set("refresh_token", "invalid_jwt_refresh_token_string")
        res_rf_bad = await client.post("/api/auth/refresh")
        assert res_rf_bad.status_code == 401

        # 3. Reset password sai token -> 400
        res_rst_bad = await client.post("/api/auth/reset-password", json={
            "token": "invalid_reset_token",
            "new_password": "ValidNewPassword123!",
        })
        assert res_rst_bad.status_code == 400

        # 4. Verify email sai token -> 400
        res_ver_bad = await client.get("/api/auth/verify-email?token=invalid_token")
        assert res_ver_bad.status_code == 400

        # 5. Logout khi có refresh_token cookie
        client.cookies.set("refresh_token", "any_token_to_clear")
        res_logout = await client.post("/api/auth/logout")
        assert res_logout.status_code == 200

        # 6. Dictionary updates với đầy đủ fields và 404
        email = f"dict_branch_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Dict Branch",
        })
        login_res = await client.post("/api/auth/login", json={
            "email": email,
            "password": "Password123!",
        })
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Tạo rule
        r = await client.post("/api/dictionary", headers=headers, json={"word": "K8s", "replacement": "Kubernetes"})
        rule_id = r.json()["id"]

        # Update đầy đủ fields (replacement, category, is_active)
        up_full = await client.put(f"/api/dictionary/{rule_id}", headers=headers, json={
            "replacement": "Kube",
            "category": "abbreviation",
            "is_active": False,
        })
        assert up_full.status_code == 200
        assert up_full.json()["category"] == "abbreviation"
        assert up_full.json()["is_active"] is False

        # 404 khi update và delete không tồn tại
        assert (await client.put("/api/dictionary/999999", headers=headers, json={"replacement": "X"})).status_code == 404
        assert (await client.delete("/api/dictionary/999999", headers=headers)).status_code == 404


@pytest.mark.unit
def test_audio_service_ffprobe_mock(tmp_path):
    """Kiểm tra nhánh ffprobe thành công khi đo thời lượng."""
    p = tmp_path / "exist.mp3"
    p.write_bytes(b"dummy")
    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(returncode=0, stdout='{"format": {"duration": "45.67"}}')
        dur = AudioService.measure_duration(str(p))
        assert dur == 45.67


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edge_tts_provider_offline_unit():
    """Kiểm tra EdgeTTSProvider ở tầng unit test hoàn toàn offline với mock."""
    provider = EdgeTTSProvider()
    assert provider.provider_name == "edge-tts"

    # 1. format_percent & format_hz
    assert provider._format_percent("") == "+0%"
    assert provider._format_percent("15") == "+15%"
    assert provider._format_percent("-20%") == "-20%"
    assert provider._format_percent("not_a_number") == "+0%"
    assert provider._format_percent("+5%") == "+5%"

    assert provider._format_hz("") == "+0Hz"
    assert provider._format_hz("25") == "+25Hz"
    assert provider._format_hz("-10Hz") == "-10Hz"
    assert provider._format_hz("not_a_number") == "+0Hz"

    # 2. _split_into_micro_chunks
    assert _split_into_micro_chunks("") == []
    assert _split_into_micro_chunks("Ngắn") == ["Ngắn"]
    long_clause = "Mệnh đề một; mệnh đề hai: mệnh đề ba, kết hợp lại thành một câu dài hơn bình thường."
    chunks = _split_into_micro_chunks(long_clause, max_len=30)
    assert len(chunks) >= 2
    assert all(len(c) <= 30 for c in chunks)

    # Từ siêu dài không có khoảng trắng
    long_word = "W" * 80
    assert len(_split_into_micro_chunks(long_word, max_len=25)) >= 3

    # 3. list_voices mock
    with patch("edge_tts.list_voices") as mock_lv:
        mock_lv.return_value = [
            {
                "ShortName": "vi-VN-HoaiMyNeural",
                "FriendlyName": "Microsoft HoaiMy Online (Natural)",
                "Gender": "Female",
                "Locale": "vi-VN",
                "LocaleName": "Vietnamese",
            }
        ]
        voices = await provider.list_voices()
        assert len(voices) == 1
        assert voices[0]["id"] == "vi-VN-HoaiMyNeural"
        assert voices[0]["name"] == "HoaiMy"

    # list_voices lỗi -> RuntimeError
    with patch("edge_tts.list_voices", side_effect=Exception("Network error")):
        with pytest.raises(RuntimeError):
            await provider.list_voices()

    # 4. synthesize text rỗng -> ValueError
    with pytest.raises(ValueError):
        await provider.synthesize("", "vi-VN-HoaiMyNeural")

    # 5. synthesize với mock Communicate stream
    with patch("edge_tts.Communicate") as mock_comm:
        instance = MagicMock()
        async def mock_stream():
            yield {"type": "audio", "data": b"frame_1"}
            yield {"type": "word", "data": "ignore_non_audio"}
            yield {"type": "audio", "data": b"frame_2"}
        instance.stream = mock_stream
        mock_comm.return_value = instance

        audio = await provider.synthesize("Xin chào buổi sáng", "vi-VN-HoaiMyNeural")
        assert audio == b"frame_1frame_2"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dictionary_api_endpoints():
    """Kiểm tra toàn bộ CRUD trên API route /api/dictionary."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"dict_api_{time.time()}@example.com"
        await client.post("/api/auth/register", json={
            "email": email,
            "password": "Password123!",
            "full_name": "Dict User",
        })
        login_res = await client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. List rỗng
        r_list = await client.get("/api/dictionary", headers=headers)
        assert r_list.status_code == 200
        assert r_list.json() == []

        # 2. Tạo mới rule
        r_create = await client.post("/api/dictionary", headers=headers, json={
            "word": "VND",
            "replacement": "đồng",
            "category": "currency",
        })
        assert r_create.status_code == 201
        rule_data = r_create.json()
        assert rule_data["word"] == "VND"
        rule_id = rule_data["id"]

        # 3. Tạo lỗi validation rỗng -> 400
        r_dup = await client.post("/api/dictionary", headers=headers, json={
            "word": "VND",
            "replacement": "   ",
        })
        assert r_dup.status_code == 400

        # 4. Cập nhật rule
        r_up = await client.put(f"/api/dictionary/{rule_id}", headers=headers, json={
            "replacement": "Việt Nam Đồng",
            "category": "custom",
            "is_active": False,
        })
        assert r_up.status_code == 200
        assert r_up.json()["replacement"] == "Việt Nam Đồng"
        assert r_up.json()["is_active"] is False

        # 5. Xóa rule
        r_del = await client.delete(f"/api/dictionary/{rule_id}", headers=headers)
        assert r_del.status_code == 200
        assert "message" in r_del.json()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_history_patch_and_edge_branches():
    """Kiểm tra PATCH /api/history/{id} và các phân quyền liên quan."""
    from app.models.generation import Generation

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        e1 = f"hist_u1_{time.time()}@example.com"
        e2 = f"hist_u2_{time.time()}@example.com"
        reg1 = await client.post("/api/auth/register", json={"email": e1, "password": "Password123!", "full_name": "U1"})
        reg2 = await client.post("/api/auth/register", json={"email": e2, "password": "Password123!", "full_name": "U2"})
        u1_id = reg1.json()["id"]
        log1 = await client.post("/api/auth/login", json={"email": e1, "password": "Password123!"})
        log2 = await client.post("/api/auth/login", json={"email": e2, "password": "Password123!"})
        h1 = {"Authorization": f"Bearer {log1.json()['access_token']}"}
        h2 = {"Authorization": f"Bearer {log2.json()['access_token']}"}

        async with AsyncSessionLocal() as db:
            gen = Generation(
                user_id=u1_id,
                title="Old Title",
                text="Nội dung kiểm thử",
                voice="vi-VN-HoaiMyNeural",
                char_count=17,
                duration=5.0,
                format="mp3",
                file_size=1024,
                file_path="/tmp/test_hist_audio.mp3",
                is_preview=False,
            )
            db.add(gen)
            await db.commit()
            await db.refresh(gen)
            gen_id = gen.id

        # 1. Update title bởi chính chủ -> 200
        patch_ok = await client.patch(f"/api/history/{gen_id}", headers=h1, json={"title": "Updated Brand New Title"})
        assert patch_ok.status_code == 200
        assert patch_ok.json()["title"] == "Updated Brand New Title"

        # 2. Update title bởi người khác -> 403
        patch_forbid = await client.patch(f"/api/history/{gen_id}", headers=h2, json={"title": "Hack Title"})
        assert patch_forbid.status_code == 403

        # 3. Update title không tồn tại -> 404
        patch_nf = await client.patch("/api/history/999999", headers=h1, json={"title": "None"})
        assert patch_nf.status_code == 404

        # 4. Delete bởi người khác -> 403
        del_forbid = await client.delete(f"/api/history/{gen_id}", headers=h2)
        assert del_forbid.status_code == 403

        # 5. List có search và filter
        hist_filter = await client.get("/api/history?search=kiểm+thử&format=mp3", headers=h1)
        assert hist_filter.status_code == 200
        assert hist_filter.json()["total"] >= 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_payment_routes_extra_branches():
    """Kiểm tra coupon validate API, webhook Stripe, VietQR và admin update plan."""
    from app.models.payment import Coupon, PricingPlan

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        e_user = f"extra_pay_{time.time()}@example.com"
        await client.post("/api/auth/register", json={"email": e_user, "password": "Password123!", "full_name": "Pay User"})
        log_u = await client.post("/api/auth/login", json={"email": e_user, "password": "Password123!"})
        h_user = {"Authorization": f"Bearer {log_u.json()['access_token']}"}

        # Tạo admin
        async with AsyncSessionLocal() as db:
            await PaymentService.seed_defaults_if_empty(db)
            admin_user = User(
                email=f"admin_extra_{time.time()}@example.com",
                hashed_password=hash_password("AdminPass123!"),
                full_name="Admin Extra",
                is_admin=True,
                is_active=True,
            )
            coupon = Coupon(
                code=f"ROUTE_CP_{int(time.time()*1000)}",
                discount_type="fixed",
                discount_value=10000,
                min_order_amount=50000,
                is_active=True,
            )
            plan = PricingPlan(
                code=f"plan_extra_{int(time.time()*1000)}",
                name="Gói test update",
                type="credit_pack",
                price=50000,
                currency="VND",
                credits=50000,
                is_active=True,
            )
            db.add_all([admin_user, coupon, plan])
            await db.commit()
            await db.refresh(admin_user)
            await db.refresh(coupon)
            await db.refresh(plan)
            plan_id = plan.id
            coupon_code = coupon.code

        admin_login = await client.post("/api/auth/login", json={"email": admin_user.email, "password": "AdminPass123!"})
        h_admin = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

        # 1. Coupon validate
        # - Invalid coupon
        c_inv = await client.post("/api/payments/coupons/validate", headers=h_user, json={"code": "NONEXISTENT", "order_amount": 100000})
        assert c_inv.status_code == 200
        assert c_inv.json()["valid"] is False

        # - Valid coupon
        c_val = await client.post("/api/payments/coupons/validate", headers=h_user, json={"code": coupon_code, "order_amount": 100000})
        assert c_val.status_code == 200
        assert c_val.json()["valid"] is True
        assert c_val.json()["discount_amount"] == 10000

        # 2. Admin update plan
        p_up = await client.put(f"/api/payments/admin/plans/{plan_id}", headers=h_admin, json={"name": "Gói Đã Đổi Tên", "price": 60000})
        assert p_up.status_code == 200
        assert p_up.json()["name"] == "Gói Đã Đổi Tên"

        # - Admin update plan non-existent -> 404
        p_up_nf = await client.put("/api/payments/admin/plans/999999", headers=h_admin, json={"name": "404"})
        assert p_up_nf.status_code == 404

        # 3. Webhook Stripe edge cases
        # - Invalid signature
        with patch("app.services.payment_service.PaymentService.verify_stripe_signature", return_value=False):
            st_bad_sig = await client.post("/api/payments/webhook/stripe", headers={"Stripe-Signature": "bad_sig"}, content=b"{}")
            assert st_bad_sig.status_code == 400

        # - Invalid JSON
        with patch("app.services.payment_service.PaymentService.verify_stripe_signature", return_value=True):
            st_bad_json = await client.post("/api/payments/webhook/stripe", headers={"Stripe-Signature": "sig"}, content=b"invalid-json")
            assert st_bad_json.status_code == 400

        # - Valid JSON but unknown order
        with patch("app.services.payment_service.PaymentService.verify_stripe_signature", return_value=True):
            st_unknown = await client.post(
                "/api/payments/webhook/stripe",
                headers={"Stripe-Signature": "sig"},
                json={
                    "type": "checkout.session.completed",
                    "data": {"object": {"client_reference_id": "VOX999999", "payment_intent": "pi_test"}},
                },
            )
            assert st_unknown.status_code == 200
            assert st_unknown.json()["received"] is True

        # 4. Webhook VietQR edge cases
        # - Invalid JSON body
        vq_bad_json = await client.post("/api/payments/webhook/vietqr", content=b"not a json")
        assert vq_bad_json.status_code == 200
        assert vq_bad_json.json()["success"] is False

        # - Unknown order content
        vq_unknown = await client.post("/api/payments/webhook/vietqr", json={"content": "UNKNOWN_TRANSACTION_CONTENT"})
        assert vq_unknown.status_code == 200
        assert vq_unknown.json()["success"] is False

        # 5. Webhook PayOS unknown order
        with patch("app.services.payment_service.PaymentService.verify_payos_signature", return_value=True):
            payos_unknown = await client.post(
                "/api/payments/webhook/payos",
                json={
                    "code": "00",
                    "desc": "success",
                    "data": {"orderCode": 99999988, "amount": 50000},
                    "signature": "valid_signature",
                },
            )
            assert payos_unknown.status_code == 200
            assert payos_unknown.json()["success"] is False




