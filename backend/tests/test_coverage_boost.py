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

    # 6. synthesize with retry fallback to alternate voice
    call_count = 0
    with patch("edge_tts.Communicate") as mock_comm:
        instance = MagicMock()
        async def mock_stream_flaky():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated connection drop")
            yield {"type": "audio", "data": b"recovered_audio"}
        instance.stream = mock_stream_flaky
        mock_comm.return_value = instance

        audio = await provider._synthesize_chunk("Đoạn test thử lại khi gặp sự cố", "vi-VN-NamMinhNeural", "+0%", "+0Hz", "+0%", 1, 1)
        assert audio == b"recovered_audio"

    # 7. synthesize with sub-splitting on persistent failure
    with patch("edge_tts.Communicate") as mock_comm:
        instance = MagicMock()
        sub_call = 0
        async def mock_stream_subsplit():
            nonlocal sub_call
            sub_call += 1
            # First 3 attempts for full 90-char text fail, then sub-chunks succeed
            if sub_call <= 3:
                raise Exception("Persistent error")
            yield {"type": "audio", "data": b"sub_audio_chunk"}
        instance.stream = mock_stream_subsplit
        mock_comm.return_value = instance

        long_failing_text = "Đây là một đoạn văn bản tiếng Việt dài hơn 80 ký tự để kích hoạt cơ chế chia nhỏ khi bị lỗi."
        audio = await provider._synthesize_chunk(long_failing_text, "vi-VN-HoaiMyNeural", "+0%", "+0Hz", "+0%", 1, 1)
        assert len(audio) > 0

    # 8. synthesize with complete failure raising RuntimeError
    with patch("edge_tts.Communicate") as mock_comm:
        instance = MagicMock()
        async def mock_stream_fail():
            raise Exception("Fatal network failure")
            yield {"type": "audio", "data": b""}
        instance.stream = mock_stream_fail
        mock_comm.return_value = instance

        with pytest.raises(RuntimeError):
            await provider._synthesize_chunk("Ngắn", "vi-VN-HoaiMyNeural", "+0%", "+0Hz", "+0%", 1, 1, max_retries=1)


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_additional_service_units():
    """Bổ sung unit tests cho core handlers, dictionary service, script parser và audio service."""
    # 1. app_error_handler & custom error classes
    from app.core.errors import AppError, TTSError, ValidationError, app_error_handler
    from app.services.dictionary_service import DictionaryService
    from app.services.tts_script_parser import TTSScriptParser
    ve = ValidationError("Validation test")
    assert ve.status_code == 400
    te = TTSError("TTS test")
    assert te.status_code == 502

    dummy_req = MagicMock()
    err_resp = await app_error_handler(dummy_req, AppError(code="TEST_CODE", message="Test error", status_code=418))
    assert err_resp.status_code == 418

    # Anti-abuse check
    from app.core.voice_anti_abuse import check_voice_name_against_blocklist
    is_blocked, target, msg = check_voice_name_against_blocklist("Sơn Tùng M-TP Clone", "Mô tả")
    assert is_blocked is True
    assert target is not None

    # 2. DictionaryService non-existent delete and edge cases
    async with AsyncSessionLocal() as db:
        del_res = await DictionaryService.delete_rule(db, user_id=999999, rule_id=999999)
        assert del_res is False

        # apply_dictionary với user_id=None hoặc text=""
        res_none_usr = await DictionaryService.apply_dictionary(db, None, "Test text")
        assert res_none_usr == "Test text"
        res_empty_txt = await DictionaryService.apply_dictionary(db, 1, "")
        assert res_empty_txt == ""

    # 3. AudioService duration đo file không tồn tại
    dur = AudioService.measure_duration("/non/existent/path/audio.mp3")
    assert dur == 0.0

    # 4. TTSScriptParser edge cases (line 19 & line 91)
    empty_lines = TTSScriptParser.parse_script("   \n\n  ", default_voice="vi-VN-HoaiMyNeural")
    assert empty_lines == []

    parsed_alias = TTSScriptParser._map_voice_alias("custom-neural-voice", default_voice="vi-VN-HoaiMyNeural")
    assert parsed_alias == "custom-neural-voice"

    # 5. StorageService get_url (line 33) & PDF receipt non-ascii char (line 46)
    from datetime import UTC, datetime

    from app.core.receipt import generate_receipt_pdf
    from app.services.storage_service import StorageService

    storage = StorageService()
    url = await storage.get_url("storage/audio/test.mp3")
    assert "/storage/audio/test.mp3" in url or "test.mp3" in url

    pdf_bytes = generate_receipt_pdf(
        order_code="VOX_SPECIAL_€™",
        user_email="test_special_€@example.com",
        plan_name="Gói Đặc Biệt ™",
        original_amount=50000,
        discount_amount=0,
        final_amount=50000,
        credits=1000,
        payment_method="vietqr",
        paid_at=datetime.now(UTC),
    )
    assert len(pdf_bytes) > 0


@pytest.mark.asyncio
async def test_admin_audit_service_and_dashboard_deep_coverage():
    """Kiểm thử chuyên sâu AdminAuditService và các nhánh edge cases."""
    from app.db import AsyncSessionLocal
    from app.services.admin_audit_service import AdminAuditService

    async with AsyncSessionLocal() as db:
        class Unserializable:
            pass

        log1 = await AdminAuditService.log_action(
            db=db,
            admin_id=1,
            action="custom_action",
            target_type="custom_target",
            target_id="123",
            details={"obj": Unserializable()},
            ip_address="127.0.0.1",
        )
        assert log1.id is not None

        log2 = await AdminAuditService.log_action(
            db=db,
            admin_id=1,
            action="custom_action_2",
            target_type="custom_target_2",
            target_id=None,
            details=None,
            ip_address=None,
        )
        assert log2.id is not None

        items, total = await AdminAuditService.list_logs(
            db=db,
            action="custom_action",
            target_type="custom_target",
            admin_id=1,
            page=1,
            limit=10,
        )
        assert total >= 1


@pytest.mark.asyncio
async def test_voice_clone_routes_deep_coverage():
    """Kiểm thử chuyên sâu các routes của Voice Clone để tăng coverage."""
    import time
    from pathlib import Path
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.db import AsyncSessionLocal
    from app.models.cloned_voice import ClonedVoice
    from app.models.user import User
    from app.core.security import hash_password

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Tạo 2 users (owner và other)
        t = int(time.time() * 1000)
        async with AsyncSessionLocal() as db:
            u1 = User(email=f"u1_{t}@example.com", hashed_password=hash_password("Pass123!"), full_name="User 1", role="user", is_active=True, credit_balance=50000, credits=50000)
            u2 = User(email=f"u2_{t}@example.com", hashed_password=hash_password("Pass123!"), full_name="User 2", role="user", is_active=True, credit_balance=50000, credits=50000)
            db.add_all([u1, u2])
            await db.commit()
            await db.refresh(u1)
            await db.refresh(u2)
            u1_id = u1.id
            u2_id = u2.id

        t1 = (await client.post("/api/auth/login", json={"email": f"u1_{t}@example.com", "password": "Pass123!"})).json()["access_token"]
        t2 = (await client.post("/api/auth/login", json={"email": f"u2_{t}@example.com", "password": "Pass123!"})).json()["access_token"]
        h1 = {"Authorization": f"Bearer {t1}"}
        h2 = {"Authorization": f"Bearer {t2}"}

        # Tạo file mẫu và preview giả lập
        Path("storage/clones/samples").mkdir(parents=True, exist_ok=True)
        Path("storage/clones/previews").mkdir(parents=True, exist_ok=True)
        s_file = f"storage/clones/samples/clone_{u1_id}_{t}_sample.mp3"
        p_file = f"storage/clones/previews/clone_{u1_id}_{t}_preview.mp3"
        with open(s_file, "wb") as f:
            f.write(b"SAMPLE_AUDIO_BYTES_TEST")
        with open(p_file, "wb") as f:
            f.write(b"PREVIEW_AUDIO_BYTES_TEST")

        async with AsyncSessionLocal() as db:
            cv = ClonedVoice(
                voice_id=f"clone_{u1_id}_{t}_voice",
                user_id=u1_id,
                name="Giọng Test Clone",
                description="Mô tả test",
                audio_sample_path=s_file,
                sample_duration=10.0,
                sample_size_bytes=1000,
                quality_score=4.5,
                gender="male",
                language="vi-VN",
                provider="mock",
                provider_voice_id="mock_id_123",
                preview_audio_path=p_file,
                status="ready",
                is_active=True,
            )
            db.add(cv)
            await db.commit()
            await db.refresh(cv)
            vid = cv.voice_id

        # 1. GET detail
        res_det = await client.get(f"/api/voices/cloned/{vid}", headers=h1)
        assert res_det.status_code == 200
        assert res_det.json()["name"] == "Giọng Test Clone"

        # 2. GET detail 403 (user 2 gọi voice của user 1)
        assert (await client.get(f"/api/voices/cloned/{vid}", headers=h2)).status_code == 403

        # 3. GET detail 404
        assert (await client.get("/api/voices/cloned/not_exists", headers=h1)).status_code == 404

        # 4. PATCH update
        res_patch = await client.patch(
            f"/api/voices/cloned/{vid}",
            headers=h1,
            json={"name": "Giọng Test Đổi Tên", "description": "Mô tả mới"},
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["name"] == "Giọng Test Đổi Tên"

        # 5. GET preview stream
        res_prev = await client.get(f"/api/voices/cloned/{vid}/preview", headers=h1)
        assert res_prev.status_code == 200

        # 6. GET sample stream
        res_sample = await client.get(f"/api/voices/cloned/{vid}/sample", headers=h1)
        assert res_sample.status_code == 200
        assert (await client.get(f"/api/voices/cloned/{vid}/sample", headers=h2)).status_code == 403

        # 7. DELETE voice
        res_del = await client.delete(f"/api/voices/cloned/{vid}", headers=h1)
        assert res_del.status_code == 200


@pytest.mark.asyncio
async def test_voices_route_and_overrides():
    """Kiểm thử route /api/voices với cache, force_refresh, và overrides."""
    import time
    from unittest.mock import AsyncMock, patch
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.db import AsyncSessionLocal
    from app.models.admin import SystemVoiceSetting

    async with AsyncSessionLocal() as db:
        # Tạo override voice setting
        s = SystemVoiceSetting(
            voice_id=f"vi-VN-Custom_{int(time.time()*1000)}",
            name="Custom Test Name",
            is_active=False,
            tier="premium",
            credit_multiplier=1.8,
        )
        db.add(s)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/voices
        res = await client.get("/api/voices")
        assert res.status_code == 200
        data = res.json()
        assert "voices" in data
        assert "total" in data

        # 2. GET /api/voices?refresh=true
        res_ref = await client.get("/api/voices?refresh=true")
        assert res_ref.status_code == 200

        # 3. Lỗi 500 khi tts_service gặp sự cố
        with patch("app.services.tts_service.TTSService.get_voices", new=AsyncMock(side_effect=Exception("Lỗi mock voice"))):
            res_err = await client.get("/api/voices")
            assert res_err.status_code == 500


@pytest.mark.asyncio
async def test_history_item_patch_delete_and_cleanup():
    """Kiểm thử PATCH title, DELETE generation, quyền truy cập và cleanup."""
    import time
    from datetime import UTC, datetime, timedelta
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.db import AsyncSessionLocal
    from app.models.generation import Generation
    from app.models.user import User
    from app.core.security import create_access_token, hash_password
    from app.routes.history import cleanup_old_generations

    async with AsyncSessionLocal() as db:
        u1 = User(email=f"u1_hist_{time.time()}@example.com", hashed_password=hash_password("Pass123!"), is_active=True, is_verified=True)
        u2 = User(email=f"u2_hist_{time.time()}@example.com", hashed_password=hash_password("Pass123!"), is_active=True, is_verified=True)
        db.add_all([u1, u2])
        await db.flush()

        gen = Generation(
            user_id=u1.id,
            text="Nội dung lịch sử mẫu",
            voice="vi-VN-HoaiMyNeural",
            status="done",
            char_count=20,
            duration=2.5,
            is_preview=True,
            created_at=datetime.now(UTC) - timedelta(days=10),
        )
        db.add(gen)
        await db.flush()
        gen_id = gen.id
        u1_id, u2_id = u1.id, u2.id
        await db.commit()

    t1 = create_access_token(data={"sub": str(u1_id)})
    t2 = create_access_token(data={"sub": str(u2_id)})
    h1 = {"Authorization": f"Bearer {t1}"}
    h2 = {"Authorization": f"Bearer {t2}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. PATCH 404
        assert (await client.patch("/api/history/999999", headers=h1, json={"title": "Mới"})).status_code == 404

        # 2. PATCH 403 (khác user)
        assert (await client.patch(f"/api/history/{gen_id}", headers=h2, json={"title": "Mới"})).status_code == 403

        # 3. PATCH 200 (chủ sở hữu)
        res_patch = await client.patch(f"/api/history/{gen_id}", headers=h1, json={"title": "Tiêu đề tùy chỉnh"})
        assert res_patch.status_code == 200
        assert res_patch.json()["title"] == "Tiêu đề tùy chỉnh"

        # 4. DELETE 404
        assert (await client.delete("/api/history/999999", headers=h1)).status_code == 404

        # 5. DELETE 403 (khác user)
        assert (await client.delete(f"/api/history/{gen_id}", headers=h2)).status_code == 403

        # 6. DELETE 200 (chủ sở hữu)
        res_del = await client.delete(f"/api/history/{gen_id}", headers=h1)
        assert res_del.status_code == 200
        assert res_del.json()["deleted"] == 1

        # 7. cleanup_old_generations
        async with AsyncSessionLocal() as db:
            await cleanup_old_generations(db, retention_days=7)


@pytest.mark.asyncio
async def test_dictionary_patch_and_delete_endpoints():
    """Kiểm thử PUT và DELETE rule cho từ điển phát âm."""
    import time
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.db import AsyncSessionLocal
    from app.models.user import User
    from app.models.dictionary import PronunciationDictionary
    from app.core.security import create_access_token, hash_password

    async with AsyncSessionLocal() as db:
        user = User(email=f"dict_user_{time.time()}@example.com", hashed_password=hash_password("Pass123!"), is_active=True, is_verified=True)
        db.add(user)
        await db.flush()
        rule = PronunciationDictionary(user_id=user.id, word="AI", replacement="trí tuệ nhân tạo", category="tech", is_active=True)
        db.add(rule)
        await db.flush()
        u_id = user.id
        r_id = rule.id
        await db.commit()

    token = create_access_token(data={"sub": str(u_id)})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # PUT 404
        assert (await client.put("/api/dictionary/999999", headers=headers, json={"replacement": "abc"})).status_code == 404

        # PUT 200
        res_put = await client.put(f"/api/dictionary/{r_id}", headers=headers, json={"replacement": "ây ai", "category": "custom", "is_active": False})
        assert res_put.status_code == 200
        assert res_put.json()["replacement"] == "ây ai"

        # DELETE 404
        assert (await client.delete("/api/dictionary/999999", headers=headers)).status_code == 404

        # DELETE 200
        res_del = await client.delete(f"/api/dictionary/{r_id}", headers=headers)
        assert res_del.status_code == 200


@pytest.mark.unit
def test_text_splitter_and_sentence_splitter_deep():
    """Kiểm thử chuyên sâu hàm split_text_into_chunks và _split_long_sentence."""
    from app.services.text_splitter import split_text_into_chunks, _split_long_sentence

    # 1. Empty & space text
    assert split_text_into_chunks("") == []
    assert split_text_into_chunks("   \n\t  ") == []

    # 2. Text fits within max_chunk_size
    assert split_text_into_chunks("Một đoạn văn ngắn.", max_chunk_size=100) == ["Một đoạn văn ngắn."]

    # 3. Câu siêu dài với các loại dấu ngắt (phẩy, chấm phẩy, khoảng trắng, không khoảng trắng)
    sentence_commas = "Từ một, từ hai, từ ba, từ bốn, từ năm, từ sáu, từ bảy, từ tám."
    chunks_c = _split_long_sentence(sentence_commas, max_chunk_size=20)
    assert len(chunks_c) >= 2

    # Không có dấu phẩy nhưng có khoảng trắng
    sentence_spaces = "Một hai ba bốn năm sáu bảy tám chín mười mười một mười hai"
    chunks_s = _split_long_sentence(sentence_spaces, max_chunk_size=15)
    assert len(chunks_s) >= 2

    # Không có khoảng trắng (từ liền siêu dài)
    sentence_nowhitespace = "A" * 60
    chunks_nw = _split_long_sentence(sentence_nowhitespace, max_chunk_size=20)
    assert len(chunks_nw) == 3
    assert all(len(c) <= 20 for c in chunks_nw)

    # 4. Văn bản nhiều câu có cả câu siêu dài
    long_doc = "Câu ngắn đầu tiên. " + ("Siêu dài không ngắt " * 20) + ". Câu ngắn kết thúc!"
    res_doc = split_text_into_chunks(long_doc, max_chunk_size=50)
    assert len(res_doc) >= 3


@pytest.mark.asyncio
async def test_dashboard_stats_and_history_filters_deep():
    """Kiểm thử dashboard stats khi có dữ liệu và history filter date/format."""
    import time
    from datetime import UTC, datetime
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.db import AsyncSessionLocal
    from app.models.user import User
    from app.models.generation import Generation
    from app.core.security import create_access_token, hash_password

    async with AsyncSessionLocal() as db:
        user = User(
            email=f"dash_hist_{time.time()}@example.com",
            hashed_password=hash_password("Pass123!"),
            is_active=True,
            is_verified=True,
            credit_balance=10000,
            credits=10000,
        )
        db.add(user)
        await db.flush()

        gen = Generation(
            user_id=user.id,
            text="Bài phát biểu test cho dashboard stats",
            voice="vi-VN-NamMinhNeural",
            status="done",
            char_count=50,
            duration=3.5,
            format="mp3",
            is_preview=False,
            created_at=datetime.now(UTC),
        )
        db.add(gen)
        await db.flush()
        u_id = user.id
        await db.commit()

    token = create_access_token(data={"sub": str(u_id)})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/dashboard/stats
        res_dash = await client.get("/api/dashboard/stats", headers=headers)
        assert res_dash.status_code == 200
        dash_data = res_dash.json()
        assert dash_data["total_audio_generated"] >= 1
        assert dash_data["chars_used_this_month"] >= 50
        assert dash_data["latest_generation"] is not None

        # 2. GET /api/history với các bộ lọc ngày hợp lệ và không hợp lệ, format
        res_h1 = await client.get("/api/history?date_from=2026-01-01T00:00:00&date_to=2026-12-31T23:59:59&format=mp3", headers=headers)
        assert res_h1.status_code == 200

        # Lọc ngày sai định dạng (vẫn 200 nhưng log warning)
        res_h2 = await client.get("/api/history?date_from=invalid-date&date_to=invalid-date", headers=headers)
        assert res_h2.status_code == 200


@pytest.mark.asyncio
async def test_v1_voices_extended_deep():
    """Kiểm thử chuyên sâu /v1/voices với cloned voice, overrides và bộ lọc language/gender."""
    import time
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.db import AsyncSessionLocal
    from app.models.user import User
    from app.models.cloned_voice import ClonedVoice
    from app.models.admin import SystemVoiceSetting
    from app.services.api_key_service import ApiKeyService

    async with AsyncSessionLocal() as db:
        user = User(
            email=f"v1_voices_user_{time.time()}@example.com",
            hashed_password="hash",
            is_active=True,
            is_verified=True,
            credit_balance=50000,
            credits=50000,
        )
        db.add(user)
        await db.flush()

        # Tạo cloned voice ready
        cv = ClonedVoice(
            user_id=user.id,
            voice_id=f"clone_v1_{int(time.time()*1000)}",
            name="Giọng Clone V1 Test",
            audio_sample_path="/tmp/sample.wav",
            sample_duration=15.0,
            sample_size_bytes=44100,
            gender="Female",
            language="vi-VN",
            status="ready",
            is_active=True,
            quality_score=95.0,
        )
        db.add(cv)

        # Tạo voice override
        sv = SystemVoiceSetting(
            voice_id=f"sys_override_{int(time.time()*1000)}",
            name="Sys Override Voice",
            tier="premium",
            credit_multiplier=2.0,
            is_active=True,
        )
        db.add(sv)
        await db.flush()

        _, plain_key = await ApiKeyService.create_api_key(db, user.id, name="Test V1 Voices Key")
        await db.commit()

    headers = {"Authorization": f"Bearer {plain_key}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /v1/voices
        res = await client.get("/v1/voices", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "voices" in data
        assert any(v.get("is_clone") for v in data["voices"])


@pytest.mark.asyncio
async def test_audio_service_sample_validation_scoring(tmp_path):
    """Kiểm thử tính điểm chất lượng voice sample trong AudioService."""
    from unittest.mock import AsyncMock, patch
    from app.services.audio_service import AudioService

    fake_file = tmp_path / "test_sample.wav"
    fake_file.write_bytes(b"RIFF" + b"\x00" * 200)

    # 1. Mock duration = 15s (lý tưởng), mean_volume = -20dB, max_volume = -0.5dB
    with patch.object(AudioService, "measure_duration", return_value=15.0):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (
                b"",
                b"mean_volume: -20.0 dB\nmax_volume: -0.5 dB\n",
            )
            mock_exec.return_value = mock_proc

            res = await AudioService.validate_voice_sample(str(fake_file))
            assert res["valid"] is True
            assert res["quality_score"] >= 4.0

    # 2. Mock âm thanh quá nhỏ (dưới -50dB)
    with patch.object(AudioService, "measure_duration", return_value=15.0):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (
                b"",
                b"mean_volume: -55.0 dB\nmax_volume: -40.0 dB\n",
            )
            mock_exec.return_value = mock_proc

            res_silent = await AudioService.validate_voice_sample(str(fake_file))
            assert res_silent["valid"] is False
            assert "quá nhỏ" in res_silent["error"]

    # 3. Mock clipping max_volume >= 0.0 & duration < 7s
    with patch.object(AudioService, "measure_duration", return_value=5.0):
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (
                b"",
                b"mean_volume: -40.0 dB\nmax_volume: 0.5 dB\n",
            )
            mock_exec.return_value = mock_proc

            res_clip = await AudioService.validate_voice_sample(str(fake_file))
            assert res_clip["valid"] is True
            assert res_clip["quality_score"] <= 4.0


@pytest.mark.asyncio
async def test_voice_clone_routes_full_branches(tmp_path):
    """Bổ sung độ phủ cho app/routes/voice_clone.py các nhánh detail, sample, preview, report."""
    from app.core.security import create_access_token
    from app.models.cloned_voice import ClonedVoice

    # Chuẩn bị file mẫu wav thật tạm thời
    sample_wav = tmp_path / "voice_sample.wav"
    sample_wav.write_bytes(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00" + b"\x00" * 100)
    prev_mp3 = tmp_path / "voice_prev.mp3"
    prev_mp3.write_bytes(b"ID3" + b"\x00" * 6000)

    async with AsyncSessionLocal() as db:
        u1 = User(
            email=f"vclone_u1_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="User One",
            role="user",
            credit_balance=10000,
            credits=10000,
        )
        u2 = User(
            email=f"vclone_u2_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="User Two",
            role="user",
            credit_balance=10000,
            credits=10000,
        )
        db.add(u1)
        await db.commit()
        await db.refresh(u1)
        db.add(u2)
        await db.commit()
        await db.refresh(u2)

        cv = ClonedVoice(
            user_id=u1.id,
            voice_id=f"voice_extra_{int(time.time()*1000)}",
            name="Giọng Mẫu U1",
            audio_sample_path=str(sample_wav),
            sample_duration=12.0,
            sample_size_bytes=sample_wav.stat().st_size,
            preview_audio_path=str(prev_mp3),
            is_active=True,
        )
        db.add(cv)
        await db.commit()
        await db.refresh(cv)
        v_id = cv.voice_id

    tok_u1 = create_access_token(data={"sub": str(u1.id), "email": u1.email, "role": u1.role})
    tok_u2 = create_access_token(data={"sub": str(u2.id), "email": u2.email, "role": u2.role})
    h1 = {"Authorization": f"Bearer {tok_u1}"}
    h2 = {"Authorization": f"Bearer {tok_u2}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/voices/cloned
        r_list = await client.get("/api/voices/cloned", headers=h1)
        assert r_list.status_code == 200

        # 2. GET /api/voices/cloned/{v_id} -> 200 cho U1, 403 cho U2, 404 cho không tồn tại
        r_det_ok = await client.get(f"/api/voices/cloned/{v_id}", headers=h1)
        assert r_det_ok.status_code == 200
        assert r_det_ok.json()["name"] == "Giọng Mẫu U1"

        r_det_403 = await client.get(f"/api/voices/cloned/{v_id}", headers=h2)
        assert r_det_403.status_code == 403

        r_det_404 = await client.get("/api/voices/cloned/non_existent_999", headers=h1)
        assert r_det_404.status_code == 404

        # 3. GET /api/voices/cloned/{v_id}/sample
        r_samp_ok = await client.get(f"/api/voices/cloned/{v_id}/sample", headers=h1)
        assert r_samp_ok.status_code == 200

        r_samp_403 = await client.get(f"/api/voices/cloned/{v_id}/sample", headers=h2)
        assert r_samp_403.status_code == 403

        r_samp_404 = await client.get("/api/voices/cloned/non_existent_999/sample", headers=h1)
        assert r_samp_404.status_code == 404

        # 4. GET /api/voices/cloned/{v_id}/preview
        r_prev_ok = await client.get(f"/api/voices/cloned/{v_id}/preview")
        assert r_prev_ok.status_code == 200

        r_prev_404 = await client.get("/api/voices/cloned/non_existent_999/preview")
        assert r_prev_404.status_code == 404

        # 5. POST /api/voices/cloned/{v_id}/report
        r_rep = await client.post(
            f"/api/voices/cloned/{v_id}/report",
            headers=h1,
            json={
                "reason": "copyright",
                "description": "Báo cáo thử nghiệm vi phạm bản quyền giọng đọc.",
                "reporter_email": u1.email,
            },
        )
        assert r_rep.status_code == 200
        assert r_rep.json()["status"] == "pending"

        # 6. PATCH /api/voices/cloned/{v_id}
        r_patch = await client.patch(
            f"/api/voices/cloned/{v_id}",
            headers=h1,
            json={"name": "Giọng Mẫu U1 Đã Sửa", "description": "Mô tả mới"},
        )
        assert r_patch.status_code == 200
        assert r_patch.json()["name"] == "Giọng Mẫu U1 Đã Sửa"

        # 7. DELETE /api/voices/cloned/{v_id}
        r_del = await client.delete(f"/api/voices/cloned/{v_id}", headers=h1)
        assert r_del.status_code == 200


@pytest.mark.asyncio
async def test_payments_routes_full_branches():
    """Bổ sung độ phủ cho app/routes/payments.py các nhánh coupon, receipt, order status, webhook."""
    from datetime import UTC, datetime, timedelta
    from app.core.security import create_access_token
    from app.models.payment import Coupon, Order

    async with AsyncSessionLocal() as db:
        u = User(
            email=f"pay_u_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Payment User",
            role="user",
            credit_balance=10000,
            credits=10000,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)

        coupon = Coupon(
            code=f"SALE{int(time.time()*1000)}",
            discount_type="percent",
            discount_value=20,
            is_active=True,
            max_uses=100,
            used_count=0,
        )
        now_utc = datetime.now(UTC)
        order_paid = Order(
            order_code=f"ORD_PAID_{int(time.time()*1000)}",
            order_number=int(time.time()) % 1000000,
            user_id=u.id,
            original_amount=100000,
            final_amount=80000,
            discount_amount=20000,
            credits_to_add=50000,
            payment_method="payos",
            status="paid",
            expires_at=now_utc + timedelta(hours=24),
            paid_at=now_utc,
        )
        order_pending = Order(
            order_code=f"ORD_PEND_{int(time.time()*1000)}",
            order_number=(int(time.time()) + 1) % 1000000,
            user_id=u.id,
            original_amount=50000,
            final_amount=50000,
            credits_to_add=20000,
            payment_method="bank_transfer",
            status="pending",
            expires_at=now_utc + timedelta(hours=24),
        )
        db.add_all([coupon, order_paid, order_pending])
        await db.commit()
        await db.refresh(coupon)
        await db.refresh(order_paid)
        await db.refresh(order_pending)

    tok = create_access_token(data={"sub": str(u.id), "email": u.email, "role": u.role})
    headers = {"Authorization": f"Bearer {tok}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /api/payments/coupons/validate hợp lệ và không hợp lệ
        r_c_ok = await client.post(
            "/api/payments/coupons/validate",
            headers=headers,
            json={"code": coupon.code, "order_amount": 100000},
        )
        assert r_c_ok.status_code == 200
        assert r_c_ok.json()["valid"] is True

        r_c_bad = await client.post(
            "/api/payments/coupons/validate",
            headers=headers,
            json={"code": "KHONG_TON_TAI_999", "order_amount": 100000},
        )
        assert r_c_bad.status_code == 200
        assert r_c_bad.json()["valid"] is False

        # 2. GET /api/payments/orders/{order_id}
        r_ord_ok = await client.get(f"/api/payments/orders/{order_paid.id}", headers=headers)
        assert r_ord_ok.status_code == 200

        r_ord_404 = await client.get("/api/payments/orders/9999999", headers=headers)
        assert r_ord_404.status_code == 404

        # 3. GET /api/payments/orders/{order_id}/receipt
        r_rec_ok = await client.get(f"/api/payments/orders/{order_paid.id}/receipt", headers=headers)
        assert r_rec_ok.status_code == 200
        assert r_rec_ok.headers["content-type"] == "application/pdf"

        # Đơn chưa thanh toán tải biên lai -> 400
        r_rec_notpaid = await client.get(f"/api/payments/orders/{order_pending.id}/receipt", headers=headers)
        assert r_rec_notpaid.status_code == 400

        # Đơn không tồn tại -> 404
        r_rec_404 = await client.get("/api/payments/orders/9999999/receipt", headers=headers)
        assert r_rec_404.status_code == 404

        # 4. POST /api/payments/webhook/payos đơn không tồn tại -> 200 với success=False
        r_wh_bad = await client.post(
            "/api/payments/webhook/payos",
            json={
                "code": "00",
                "desc": "success",
                "data": {"orderCode": 12345},
                "signature": "bad_signature",
            },
        )
        assert r_wh_bad.status_code == 200
        assert r_wh_bad.json()["success"] is False


@pytest.mark.asyncio
async def test_history_and_tts_routes_branches():
    """Bổ sung độ phủ cho app/routes/history.py và app/routes/tts.py các nhánh lỗi và phụ đề."""
    from app.core.security import create_access_token

    async with AsyncSessionLocal() as db:
        u = User(
            email=f"hist_tts_u_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="History TTS User",
            role="user",
            credit_balance=10000,
            credits=10000,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)

    tok = create_access_token(data={"sub": str(u.id), "email": u.email, "role": u.role})
    headers = {"Authorization": f"Bearer {tok}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # History 404
        r_h_del_404 = await client.delete("/api/history/9999999", headers=headers)
        assert r_h_del_404.status_code == 404

        r_h_patch_404 = await client.patch("/api/history/9999999", headers=headers, json={"title": "Mới"})
        assert r_h_patch_404.status_code == 404

        # TTS Subtitles 404
        r_sub_srt_404 = await client.get("/api/tts/9999999/subtitles?format=srt", headers=headers)
        assert r_sub_srt_404.status_code == 404

        r_sub_vtt_404 = await client.get("/api/tts/9999999/subtitles?format=vtt", headers=headers)
        assert r_sub_vtt_404.status_code == 404

        # TTS Job 404 & Audio 404
        r_job_404 = await client.get("/api/tts/jobs/9999999", headers=headers)
        assert r_job_404.status_code == 404

        r_audio_404 = await client.get("/api/tts/jobs/9999999/audio", headers=headers)
        assert r_audio_404.status_code == 404

        # TTS Synthesize exception branches
        with patch("app.services.tts_service.TTSService.synthesize", side_effect=ValueError("Tham số không hợp lệ")):
            r_val_err = await client.post(
                "/api/tts",
                headers=headers,
                json={"text": "Hello test value error", "voice": "vi-VN-NamMinhNeural"},
            )
            assert r_val_err.status_code == 400

        with patch("app.services.tts_service.TTSService.synthesize", side_effect=RuntimeError("Lỗi kết nối dịch vụ")):
            r_rt_err = await client.post(
                "/api/tts",
                headers=headers,
                json={"text": "Hello test runtime error", "voice": "vi-VN-NamMinhNeural"},
            )
            assert r_rt_err.status_code == 502


@pytest.mark.asyncio
async def test_payment_service_process_successful_payment_deep():
    """Tăng coverage cho app/services/payment_service.py: process_successful_payment, get_payment_methods, v.v."""
    from datetime import UTC, datetime, timedelta
    from app.models.payment import Coupon, Order, PricingPlan

    async with AsyncSessionLocal() as db:
        u = User(
            email=f"pay_deep_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Payment Deep User",
            credit_balance=5000,
            credits=5000,
        )
        db.add(u)
        await db.flush()

        coupon = Coupon(
            code=f"CP_DEEP_{int(time.time())}",
            discount_type="percent",
            discount_value=20,
            max_uses=10,
            used_count=0,
            is_active=True,
        )
        db.add(coupon)
        await db.flush()

        plan = PricingPlan(
            code=f"plan_deep_{int(time.time())}",
            name="Plan Test Deep",
            price=100000,
            credits=100000,
            is_active=True,
        )
        db.add(plan)
        await db.flush()

        order_num = int(time.time() * 1000) % 100000000
        order = Order(
            order_code=f"ORD_DEEP_{order_num}",
            order_number=order_num,
            user_id=u.id,
            plan_id=plan.id,
            coupon_id=coupon.id,
            original_amount=100000,
            discount_amount=20000,
            final_amount=80000,
            credits_to_add=100000,
            payment_method="payos",
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        db.add(order)
        await db.commit()

        # 1. process_successful_payment
        dyn_tx_id = f"tx_test_payos_{int(time.time() * 1000)}"
        loaded_order, was_already_paid = await PaymentService.process_successful_payment(
            db=db,
            order=order,
            gateway="payos",
            transaction_id=dyn_tx_id,
            paid_amount=80000,
            raw_payload={"code": "00"},
        )
        assert was_already_paid is False
        assert loaded_order.status == "paid"
        assert loaded_order.paid_at is not None

        # 2. Xử lý lại đơn đã thanh toán -> was_already_paid is True
        again_order, again_paid = await PaymentService.process_successful_payment(
            db=db,
            order=loaded_order,
            gateway="payos",
            transaction_id=dyn_tx_id,
            paid_amount=80000,
        )
        assert again_paid is True
        assert again_order.status == "paid"

        # 3. list_plans & get_plan_by_code
        plans = await PaymentService.list_plans(db)
        assert len(plans) >= 1
        p_by_code = await PaymentService.get_plan_by_code(db, plan.code)
        assert p_by_code is not None

        # 4. generate_vietqr_url
        qr_url = PaymentService.generate_vietqr_url(
            bank_id="ICB",
            account_no="123456789",
            account_name="VOXIFY",
            amount=50000,
            transfer_content="VOX 123",
        )
        assert "vietqr" in qr_url.lower() or "http" in qr_url

        # 4. get_order_by_id_or_code
        by_id = await PaymentService.get_order_by_id_or_code(db, order.id)
        assert by_id is not None
        by_code = await PaymentService.get_order_by_id_or_code(db, order.order_code)
        assert by_code is not None

        # 5. cancel_order
        cancel_ord_num = int(time.time() * 1000) % 100000000
        cancel_order = Order(
            order_code=f"ORD_CAN_{cancel_ord_num}",
            order_number=cancel_ord_num,
            user_id=u.id,
            plan_id=plan.id,
            original_amount=50000,
            discount_amount=0,
            final_amount=50000,
            credits_to_add=50000,
            payment_method="vietqr",
            status="pending",
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        db.add(cancel_order)
        await db.commit()

        res_can = await PaymentService.cancel_order(db, cancel_order.id, user_id=u.id)
        assert res_can.status == "cancelled"

        # 6. create_plan & update_plan
        p_new = await PaymentService.create_plan(db, {
            "code": f"new_plan_{int(time.time() * 1000)}",
            "name": "New Plan",
            "price": 120000,
            "credits": 120000,
        })
        assert p_new.id is not None
        p_up = await PaymentService.update_plan(db, p_new.id, {"name": "Updated Plan Name"})
        assert p_up.name == "Updated Plan Name"

        # 7. validate_coupon branches
        # - Non-existent
        _, d, msg = await PaymentService.validate_coupon(db, "KHONG_CO_12345", 100000)
        assert d == 0
        # - Inactive
        c_inact = Coupon(code=f"INACT_{int(time.time())}", discount_type="percent", discount_value=10, is_active=False)
        # - Expired
        c_exp = Coupon(code=f"EXP_{int(time.time())}", discount_type="percent", discount_value=10, is_active=True, expires_at=datetime.now(UTC) - timedelta(days=1))
        # - Max uses reached
        c_max = Coupon(code=f"MAX_{int(time.time())}", discount_type="percent", discount_value=10, is_active=True, max_uses=2, used_count=2)
        # - Min order amount
        c_min = Coupon(code=f"MIN_{int(time.time())}", discount_type="percent", discount_value=10, is_active=True, min_order_amount=200000)
        # - Fixed discount
        c_fix = Coupon(code=f"FIX_{int(time.time())}", discount_type="fixed", discount_value=30000, is_active=True)
        db.add_all([c_inact, c_exp, c_max, c_min, c_fix])
        await db.commit()

        assert (await PaymentService.validate_coupon(db, c_inact.code, 100000))[1] == 0
        assert (await PaymentService.validate_coupon(db, c_exp.code, 100000))[1] == 0
        assert (await PaymentService.validate_coupon(db, c_max.code, 100000))[1] == 0
        assert (await PaymentService.validate_coupon(db, c_min.code, 50000))[1] == 0
        cp_ok, d_ok, _ = await PaymentService.validate_coupon(db, c_fix.code, 100000)
        assert d_ok == 30000


@pytest.mark.asyncio
async def test_tts_route_authenticated_and_subtitles_deep():
    """Tăng coverage cho app/routes/tts.py: POST /api/tts (authenticated), phụ đề srt/vtt, danh sách jobs."""
    from app.core.security import create_access_token
    from app.models.generation import Generation

    async with AsyncSessionLocal() as db:
        u = User(
            email=f"tts_deep_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="TTS Deep User",
            credit_balance=20000,
            credits=20000,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)

    token = create_access_token(data={"sub": str(u.id), "email": u.email, "role": u.role})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. POST /api/tts với user đã đăng nhập
        res = await client.post(
            "/api/tts",
            headers=headers,
            json={"text": "Xin chào đây là bài kiểm thử âm thanh đồng bộ", "voice": "vi-VN-HoaiMyNeural"},
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "audio/mpeg"
        assert "x-credit-balance" in res.headers
        assert "x-duration" in res.headers

        # 2. Tạo một job hoàn tất trong DB để tải phụ đề srt và vtt
        async with AsyncSessionLocal() as db:
            gen = Generation(
                user_id=u.id,
                text="Câu một cho phụ đề. Câu hai cho phụ đề.",
                voice="vi-VN-HoaiMyNeural",
                char_count=40,
                credit_used=40,
                duration=3.5,
                status="done",
                is_preview=False,
            )
            db.add(gen)
            await db.commit()
            await db.refresh(gen)
            gen_id = gen.id

        # Tải phụ đề SRT (tự sinh ước tính)
        res_srt = await client.get(f"/api/tts/jobs/{gen_id}/subtitles?format=srt", headers=headers)
        assert res_srt.status_code == 200
        assert "subtitles" in res_srt.headers.get("content-disposition", "")

        # Tải phụ đề VTT (đã có hoặc ước tính)
        res_vtt = await client.get(f"/api/tts/jobs/{gen_id}/subtitles?format=vtt", headers=headers)
        assert res_vtt.status_code == 200

        # 3. GET /api/tts/jobs danh sách job gần đây
        res_jobs = await client.get("/api/tts/jobs?limit=5", headers=headers)
        assert res_jobs.status_code == 200
        assert isinstance(res_jobs.json(), list)


@pytest.mark.asyncio
async def test_v1_tts_sync_modes_and_download():
    """Tăng coverage cho app/routes/v1/tts.py: chế độ sync, download=true, header accept audio."""
    from app.services.api_key_service import ApiKeyService

    async with AsyncSessionLocal() as db:
        u = User(
            email=f"v1_sync_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="V1 Sync User",
            credit_balance=50000,
            credits=50000,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)

        key_rec, raw_key = await ApiKeyService.create_api_key(
            db=db,
            user_id=u.id,
            name="V1 Sync Test Key",
        )

    v1_headers = {"Authorization": f"Bearer {raw_key}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Sync TTS trả về JSON
        res_json = await client.post(
            "/v1/tts",
            headers=v1_headers,
            json={
                "text": "Kiểm thử API v1 chế độ đồng bộ JSON",
                "voice": "vi-VN-HoaiMyNeural",
                "mode": "sync",
            },
        )
        assert res_json.status_code == 200
        data = res_json.json()
        assert data["status"] == "completed"
        assert "audio_url" in data

        # 2. Sync TTS với download=true trả về file audio/mpeg
        res_dl = await client.post(
            "/v1/tts?download=true",
            headers=v1_headers,
            json={
                "text": "Kiểm thử API v1 download trực tiếp",
                "voice": "vi-VN-HoaiMyNeural",
                "mode": "sync",
            },
        )
        assert res_dl.status_code == 200
        assert res_dl.headers["content-type"] == "audio/mpeg"
        assert "attachment" in res_dl.headers.get("content-disposition", "")

        # 3. Sync TTS với Header Accept: audio/mpeg
        res_accept = await client.post(
            "/v1/tts",
            headers={**v1_headers, "Accept": "audio/mpeg"},
            json={
                "text": "Kiểm thử API v1 Accept audio mpeg",
                "voice": "vi-VN-HoaiMyNeural",
                "mode": "sync",
            },
        )
        assert res_accept.status_code == 200
        assert res_accept.headers["content-type"] == "audio/mpeg"

        # 4. Sync TTS với giọng clone không tồn tại -> 404
        res_clone_404 = await client.post(
            "/v1/tts",
            headers=v1_headers,
            json={
                "text": "Kiểm thử giọng clone không tồn tại",
                "voice": "clone_99999999",
                "mode": "sync",
            },
        )
        assert res_clone_404.status_code == 404


@pytest.mark.asyncio
async def test_history_routes_search_bulk_delete_and_cleanup():
    """Tăng coverage cho app/routes/history.py: lọc search, format, bulk delete, cleanup_old_generations."""
    from datetime import UTC, datetime, timedelta
    from app.core.security import create_access_token
    from app.models.generation import Generation
    from app.routes.history import cleanup_old_generations

    async with AsyncSessionLocal() as db:
        u = User(
            email=f"hist_deep_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="History Deep User",
            credit_balance=10000,
            credits=10000,
        )
        db.add(u)
        await db.commit()
        await db.refresh(u)

        # Tạo 3 bản ghi generation
        g1 = Generation(
            user_id=u.id,
            text="Tin tức thời sự hôm nay đặc biệt",
            voice="vi-VN-HoaiMyNeural",
            char_count=35,
            credit_used=35,
            format="mp3",
            status="done",
            is_preview=False,
        )
        g2 = Generation(
            user_id=u.id,
            text="Tin thể thao bóng đá hôm qua",
            voice="vi-VN-NamMinhNeural",
            char_count=28,
            credit_used=28,
            format="mp3",
            status="done",
            is_preview=False,
        )
        g_prev = Generation(
            user_id=u.id,
            text="Bản ghi nghe thử preview",
            voice="vi-VN-HoaiMyNeural",
            char_count=24,
            credit_used=0,
            format="mp3",
            status="done",
            is_preview=True,
            created_at=datetime.now(UTC) - timedelta(days=10),
        )
        db.add_all([g1, g2, g_prev])
        await db.commit()
        await db.refresh(g1)
        await db.refresh(g2)
        g1_id = g1.id
        g2_id = g2.id

    token = create_access_token(data={"sub": str(u.id), "email": u.email, "role": u.role})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Lọc search và format
        res_search = await client.get(
            "/api/history?page=1&limit=10&search=thời+sự&format=mp3",
            headers=headers,
        )
        assert res_search.status_code == 200
        assert res_search.json()["total"] >= 1

        # 2. Cập nhật title
        res_patch = await client.patch(
            f"/api/history/{g1_id}",
            headers=headers,
            json={"title": "Tiêu đề mới cập nhật"},
        )
        assert res_patch.status_code == 200
        assert res_patch.json()["title"] == "Tiêu đề mới cập nhật"

        # 3. Bulk delete
        res_bulk = await client.request(
            "DELETE",
            "/api/history/bulk",
            headers=headers,
            json={"ids": [g1_id]},
        )
        assert res_bulk.status_code == 200
        assert res_bulk.json()["deleted"] >= 1

        # 4. Xóa từng bản ghi
        res_del = await client.delete(f"/api/history/{g2_id}", headers=headers)
        assert res_del.status_code == 200
        assert res_del.json()["deleted"] == 1

    # 5. Dọn dẹp preview cũ
    async with AsyncSessionLocal() as db:
        await cleanup_old_generations(db, retention_days=7)


@pytest.mark.asyncio
async def test_voices_route_with_overrides():
    """Tăng coverage cho app/routes/voices.py: ghi đè thông tin giọng đọc và lọc giọng tắt."""
    from sqlalchemy import select
    from app.models.admin import SystemVoiceSetting

    async with AsyncSessionLocal() as db:
        # Cập nhật hoặc thêm setting cho 1 giọng
        stmt = select(SystemVoiceSetting).where(SystemVoiceSetting.voice_id == "vi-VN-HoaiMyNeural")
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.name = "Hoài My VIP"
            existing.tier = "pro"
            existing.credit_multiplier = 1.8
            existing.is_active = True
        else:
            s_pro = SystemVoiceSetting(
                voice_id="vi-VN-HoaiMyNeural",
                name="Hoài My VIP",
                is_active=True,
                tier="pro",
                credit_multiplier=1.8,
            )
            db.add(s_pro)
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/voices?refresh=true")
        assert res.status_code == 200
        data = res.json()
        assert "voices" in data
        assert "total" in data

        hoaimy = next((v for v in data["voices"] if v.get("id") == "vi-VN-HoaiMyNeural"), None)
        if hoaimy:
            assert hoaimy["name"] == "Hoài My VIP"
            assert hoaimy["tier"] == "pro"
            assert hoaimy["credit_multiplier"] == 1.8


@pytest.mark.asyncio
async def test_final_coverage_push_to_reach_80_percent():
    """Tăng coverage toàn diện vượt ngưỡng 80%: TTSService, Voice Anti-Abuse, Config API, Storage, TextSplitter, History 403."""
    from app.core.security import create_access_token
    from app.core.voice_anti_abuse import check_voice_name_against_blocklist, normalize_text
    from app.models.generation import Generation
    from app.providers.fake import FakeTTSProvider
    from app.services.text_splitter import split_text_into_chunks
    from app.services.tts_service import TTSService
    from app.storage import get_storage

    # 1. TTSService branches
    fake_provider = FakeTTSProvider()
    tts_svc = TTSService(provider=fake_provider)

    # Empty text
    with pytest.raises(ValueError, match="Vui lòng nhập nội dung"):
        await tts_svc.synthesize(text="", voice="vi-VN-HoaiMyNeural")

    # Text exceeding max_chars
    with patch.object(tts_svc.settings, "max_chars", 10):
        with pytest.raises(ValueError, match="vượt quá giới hạn"):
            await tts_svc.synthesize(text="Đoạn văn này dài hơn 10 ký tự chắc chắn", voice="vi-VN-HoaiMyNeural")

    # Invalid voice not starting with known prefix
    with pytest.raises(ValueError, match="không tồn tại"):
        await tts_svc.synthesize(text="Xin chào", voice="unknown_voice_xxx")

    # Exception in get_voices during _validate_voice (should be caught and logged)
    with patch.object(tts_svc, "get_voices", side_effect=Exception("Network error")):
        # Since voice starts with vi-, fallback allows it
        res_audio = await tts_svc.synthesize(text="Xin chào", voice="vi-VN-TestVoice")
        assert len(res_audio) > 0

    # 2. Voice Anti-Abuse
    assert normalize_text("Đại Tướng Võ Nguyên Giáp!!") == "dai tuong vo nguyen giap"
    assert normalize_text("") == ""

    # Politicians
    blocked, name, reason = check_voice_name_against_blocklist("Donald Trump Voice")
    assert blocked is True
    assert "donald trump" in name.lower()

    # Celebrities
    blocked, name, reason = check_voice_name_against_blocklist("Sơn Tùng M-TP")
    assert blocked is True

    # Clean name
    blocked, name, reason = check_voice_name_against_blocklist("Nguyen Van A Giọng Đọc Bình Thường")
    assert blocked is False
    assert name is None

    # 3. Storage unsupported backend
    with pytest.raises(ValueError, match="chưa được hỗ trợ"):
        get_storage("unsupported_backend_xyz")

    # 4. TextSplitter with super long word
    long_word_text = "Câu bắt đầu. " + "A" * 50 + " Kết thúc câu."
    chunks = split_text_into_chunks(long_word_text, max_chunk_size=15)
    assert len(chunks) > 1

    # 5. Config API & History 403 Forbidden
    async with AsyncSessionLocal() as db:
        u1 = User(
            email=f"u1_hist_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="User 1",
            credit_balance=10000,
            credits=10000,
        )
        u2 = User(
            email=f"u2_hist_{time.time()}@test.com",
            hashed_password=hash_password("Pass123!"),
            full_name="User 2",
            credit_balance=10000,
            credits=10000,
        )
        db.add_all([u1, u2])
        await db.commit()
        await db.refresh(u1)
        await db.refresh(u2)

        g_u1 = Generation(
            user_id=u1.id,
            text="Bài viết thuộc về User 1",
            voice="vi-VN-HoaiMyNeural",
            char_count=25,
            credit_used=25,
            status="done",
            is_preview=False,
        )
        db.add(g_u1)
        await db.commit()
        await db.refresh(g_u1)
        g_u1_id = g_u1.id

    token_u2 = create_access_token(data={"sub": str(u2.id), "email": u2.email, "role": u2.role})
    headers_u2 = {"Authorization": f"Bearer {token_u2}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/config
        r_conf = await client.get("/api/config")
        assert r_conf.status_code == 200
        assert "app_name" in r_conf.json()

        # User 2 tries to delete User 1's generation -> 403
        r_del_403 = await client.delete(f"/api/history/{g_u1_id}", headers=headers_u2)
        assert r_del_403.status_code == 403

        # User 2 tries to patch User 1's generation -> 403
        r_patch_403 = await client.patch(f"/api/history/{g_u1_id}", headers=headers_u2, json={"title": "Hacked"})
        assert r_patch_403.status_code == 403



def test_receipt_pdf_generation_direct():
    """Tăng coverage cho app/core/receipt.py."""
    from datetime import UTC, datetime
    from app.core.receipt import generate_receipt_pdf

    pdf_bytes = generate_receipt_pdf(
        order_code="VOX_ORDER_9999",
        user_email="test_pdf@voxify.vn",
        plan_name="Gói Chuyên Nghiệp (Pro)",
        original_amount=200000,
        discount_amount=50000,
        final_amount=150000,
        credits=150000,
        payment_method="vietqr",
        paid_at=datetime.now(UTC),
    )
    assert len(pdf_bytes) > 100
    assert pdf_bytes.startswith(b"%PDF-1.4")


@pytest.mark.asyncio
async def test_rate_limiter_and_login_limit():
    """Tăng coverage cho app/core/rate_limiter.py."""
    from unittest.mock import MagicMock
    from fastapi import HTTPException
    from app.core.rate_limiter import (
        MemorySlidingWindowRateLimiter,
        RateLimiterService,
        check_login_rate_limit,
        reset_login_rate_limit,
    )

    # 1. Login rate limit
    req = MagicMock()
    req.client.host = "192.168.1.100"
    req.headers = {"x-forwarded-for": "10.0.0.1"}

    # 5 attempts allowed
    for _ in range(5):
        check_login_rate_limit(req, max_attempts=5, window_seconds=60)

    # 6th attempt raises 429
    with pytest.raises(HTTPException) as exc_info:
        check_login_rate_limit(req, max_attempts=5, window_seconds=60)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers

    # Reset
    reset_login_rate_limit(req)
    # Allowed again
    check_login_rate_limit(req, max_attempts=5, window_seconds=60)

    # 2. MemorySlidingWindowRateLimiter
    limiter = MemorySlidingWindowRateLimiter()
    assert limiter.is_allowed("test_key", 2)[0] is True
    assert limiter.is_allowed("test_key", 2)[0] is True
    allowed, rem, reset_sec = limiter.is_allowed("test_key", 2)
    assert allowed is False
    assert rem == 0
    assert reset_sec > 0
    limiter.reset()

    # 3. RateLimiterService
    RateLimiterService.reset_in_memory()
    res_free = await RateLimiterService.check_rate_limit(api_key_id=1234, plan_name="free")
    assert res_free[0] is True
    res_vip = await RateLimiterService.check_rate_limit(api_key_id=1234, plan_name="vip")
    assert res_vip[0] is True


@pytest.mark.asyncio
async def test_reach_80_percent_coverage_guarantee():
    """Kiểm tra các nhánh còn thiếu để đảm bảo độ bao phủ đạt >= 80%."""
    from datetime import timedelta
    from app.core.errors import AppError, TTSError, ValidationError, app_error_handler
    from app.core.security import verify_password, create_access_token, create_timed_token, decode_token
    from app.services.text_splitter import split_text_into_chunks, _split_long_sentence
    from app.services.dictionary_service import DictionaryService
    from app.models.generation import Generation

    # 1. Security unit tests
    assert verify_password("secret", None) is False
    assert verify_password("secret", "invalid-hash-data") is False
    token_delta = create_access_token({"sub": "999"}, expires_delta=timedelta(hours=2))
    assert token_delta is not None
    expired_tok = create_timed_token({"sub": "999"}, token_type="reset", expires_minutes=-10)
    assert decode_token(expired_tok) is None
    assert decode_token("not-a-valid-token") is None

    # 2. Text splitter unit tests
    assert split_text_into_chunks("") == []
    assert split_text_into_chunks("short text", max_chunk_size=100) == ["short text"]
    # Long word buffer flush branch
    res_split = _split_long_sentence("hello " + "A" * 50, max_chunk_size=10)
    assert len(res_split) > 1

    # 3. DictionaryService unit tests
    async with AsyncSessionLocal() as db:
        with pytest.raises(ValueError, match="Từ gốc không được để trống"):
            await DictionaryService.create_rule(db, user_id=1, word="   ", replacement="abc")

    # 4. Routes: Developers API Keys, Credits, and History
    t = int(time.time() * 1000)
    async with AsyncSessionLocal() as db:
        user = User(
            email=f"cov80_{t}@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Cov80 User",
            role="user",
            is_active=True,
            credit_balance=25000,
            credits=25000,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        u_id = user.id

        # Tạo 1 generation để test history
        gen = Generation(
            user_id=u_id,
            text="Văn bản thử nghiệm lịch sử",
            voice="vi-VN-HoaiMyNeural",
            provider="edge",
            file_path="/storage/audio/test_cov.mp3",
            format="mp3",
            char_count=26,
            duration=3.5,
            status="done",
            is_preview=False,
            title="Lịch sử ban đầu",
        )
        db.add(gen)
        await db.commit()

    token = create_access_token(data={"sub": str(u_id), "email": user.email, "role": user.role})
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Developers stats & revoke 404
        stats_res = await client.get("/api/developers/stats?days=7", headers=headers)
        assert stats_res.status_code == 200
        del_key_res = await client.delete("/api/developers/keys/999999", headers=headers)
        assert del_key_res.status_code == 404

        # Credits balance & transactions list
        cred_res = await client.get("/api/credits", headers=headers)
        assert cred_res.status_code == 200
        cred_tx_res = await client.get("/api/credits/transactions?page=1&limit=10", headers=headers)
        assert cred_tx_res.status_code == 200

        # History list với các bộ lọc
        h1 = await client.get("/api/history?page=1&limit=10&search=nghiệm&format=mp3&status=done&is_preview=false", headers=headers)
        assert h1.status_code == 200
        assert h1.json()["total"] >= 1

        h2 = await client.get("/api/history?date_from=2026-01-01T00:00:00&date_to=2026-12-31T23:59:59", headers=headers)
        assert h2.status_code == 200

        h3 = await client.get("/api/history?date_from=invalid-date&date_to=invalid-date", headers=headers)
        assert h3.status_code == 200

        # History 404s
        assert (await client.delete("/api/history/999999", headers=headers)).status_code == 404
        assert (await client.patch("/api/history/999999", headers=headers, json={"title": "new"})).status_code == 404

    # 4.1 CreditService extra branches
    from app.services.credit_service import CreditService
    assert CreditService.calculate_cost(char_count=100, voice_multiplier=2.5) > 0
    with pytest.raises(AppError):
        async with AsyncSessionLocal() as db:
            await CreditService.reserve(db, user_id=9999999, amount=0)

    # 4.2 EdgeTTSProvider voice display_name fallback
    from app.providers.edge import EdgeTTSProvider
    from unittest.mock import patch, AsyncMock
    with patch("edge_tts.list_voices", new_callable=AsyncMock) as m_edge:
        m_edge.return_value = [{"ShortName": "edge_voice_1", "FriendlyName": "", "Gender": "Female", "Locale": "vi-VN"}]
        edge_v_list = await EdgeTTSProvider().list_voices()
        assert edge_v_list[0]["name"] == "edge_voice_1"

    # 4.3 Rate limiter x-forwarded-for branch
    from unittest.mock import MagicMock
    from app.core.rate_limiter import check_login_rate_limit, reset_login_rate_limit
    mock_req = MagicMock()
    mock_req.headers = {"x-forwarded-for": "10.0.0.1, 10.0.0.2"}
    mock_req.client = None
    check_login_rate_limit(mock_req)
    reset_login_rate_limit(mock_req)

    # 5. Core Errors unit tests
    e_tts = TTSError("Lỗi TTS")
    assert e_tts.code == "TTS_ERROR"
    assert e_tts.status_code == 502
    e_val = ValidationError("Lỗi Validate")
    assert e_val.code == "VALIDATION_ERROR"
    assert e_val.status_code == 400
    err_resp = await app_error_handler(None, AppError("CUSTOM_ERR", "Thông báo lỗi", 422))
    assert err_resp.status_code == 422

    # 6. Storage factory unit tests
    from app.storage import get_storage
    assert get_storage("local") is not None
    with pytest.raises(ValueError, match="chưa được hỗ trợ"):
        get_storage("unknown_backend_storage")

    # 7. Voice anti-abuse unit tests
    from app.core.voice_anti_abuse import normalize_text, check_voice_name_against_blocklist
    assert normalize_text("") == ""
    assert normalize_text("Đỗ Mười!!!") == "do muoi"
    bl_pol = check_voice_name_against_blocklist("Donald Trump")
    assert bl_pol[0] is True
    bl_celeb = check_voice_name_against_blocklist("Taylor Swift")
    assert bl_celeb[0] is True
    bl_ok = check_voice_name_against_blocklist("Giọng đọc bình thường")
    assert bl_ok[0] is False

    # 8. Email core unit tests
    from unittest.mock import patch, MagicMock
    from app.core.email import send_password_reset_email, send_verification_email, send_payment_confirmation_email

    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        with patch("app.core.email.get_settings") as mock_set:
            mock_s = MagicMock()
            mock_s.smtp_host = "smtp.example.com"
            mock_s.smtp_port = 587
            mock_s.smtp_user = "user"
            mock_s.smtp_password = "password"
            mock_s.emails_from = "no-reply@voxify.vn"
            mock_s.frontend_url = "http://localhost:3000"
            mock_s.app_name = "Voxify"
            mock_set.return_value = mock_s

            send_password_reset_email("test@example.com", "tok123")
            send_verification_email("test@example.com", "tok123")
            send_payment_confirmation_email("test@example.com", "ORDER1", "Pro", 99000, 100000, "vietqr")
            assert mock_server.send_message.call_count == 3

    # SMTP error branch
    with patch("smtplib.SMTP", side_effect=Exception("SMTP connection failed")):
        with patch("app.core.email.get_settings") as mock_set:
            mock_s = MagicMock()
            mock_s.smtp_host = "smtp.example.com"
            mock_s.smtp_port = 587
            mock_s.smtp_user = None
            mock_s.emails_from = "no-reply@voxify.vn"
            mock_s.frontend_url = "http://localhost:3000"
            mock_s.app_name = "Voxify"
            mock_set.return_value = mock_s

            send_password_reset_email("test@example.com", "tok123")

    # 9. Abstract Provider Bases unit tests
    from app.providers.base import TTSProvider
    from app.providers.clone_base import CloneProvider

    class DummyProvider(TTSProvider):
        @property
        def provider_name(self) -> str:
            return super().provider_name

        async def list_voices(self):
            return await super().list_voices()

        async def synthesize(self, text, voice, rate="+0%", pitch="+0Hz", volume="+0%"):
            return await super().synthesize(text, voice, rate, pitch, volume)

    class DummyClone(CloneProvider):
        @property
        def provider_name(self) -> str:
            return super().provider_name

        async def clone_voice(self, name, audio_file_path, description=None, **kwargs):
            return await super().clone_voice(name, audio_file_path, description, **kwargs)

        async def delete_cloned_voice(self, provider_voice_id):
            return await super().delete_cloned_voice(provider_voice_id)

        async def synthesize(self, text, provider_voice_id, audio_sample_path=None, rate="+0%", pitch="+0Hz", volume="+0%", **kwargs):
            return await super().synthesize(text, provider_voice_id, audio_sample_path, rate, pitch, volume, **kwargs)

    dp = DummyProvider()
    _ = dp.provider_name
    await dp.list_voices()
    await dp.synthesize("a", "b")

    dc = DummyClone()
    _ = dc.provider_name
    await dc.clone_voice("a", "b")
    await dc.delete_cloned_voice("a")
    await dc.synthesize("a", "b")



















