"""Unit and integration tests for Prompt 5 - TTS Background Jobs, Dictionary, and Subtitles."""
import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.audio_service import AudioService
from app.services.tts_script_parser import TTSScriptParser
from app.services.tts_job_service import TTSJobService
from app.services.dictionary_service import DictionaryService
from app.models.generation import Generation
from app.db import AsyncSessionLocal


@pytest.mark.asyncio
async def test_tts_script_parser():
    """Kiểm tra parser tách kịch bản đa giọng và ngắt nghỉ."""
    raw_script = "[Voice: NamMinh] Xin chào các bạn! [pause 1.5s] [Voice: HoaiMy] Rất vui được gặp lại [pause 500ms] mọi người."
    blocks = TTSScriptParser.parse_script(raw_script, default_voice="vi-VN-HoaiMyNeural")
    
    assert len(blocks) >= 4
    # Block 1: speech with NamMinh
    assert blocks[0]["type"] == "speech"
    assert blocks[0]["voice"] == "vi-VN-NamMinhNeural"
    assert "Xin chào các bạn!" in blocks[0]["text"]
    
    # Block 2: pause 1.5s
    assert blocks[1]["type"] == "pause"
    assert blocks[1]["duration"] == 1.5
    
    # Block 3: speech with HoaiMy
    assert blocks[2]["type"] == "speech"
    assert blocks[2]["voice"] == "vi-VN-HoaiMyNeural"
    assert "Rất vui được gặp lại" in blocks[2]["text"]
    
    # Block 4: pause 0.5s
    assert blocks[3]["type"] == "pause"
    assert blocks[3]["duration"] == 0.5


@pytest.mark.asyncio
async def test_macro_chunking_15000_chars():
    """Kiểm tra tách đoạn văn bản lớn (~15.000 ký tự) theo ngưỡng 2.500 ký tự."""
    sentence = "Đây là một câu kiểm thử hệ thống tổng hợp giọng nói của dự án Voxify. "
    # Tạo văn bản ~15.000 ký tự
    long_text = sentence * 215
    assert len(long_text) >= 15000

    chunks = TTSJobService._split_macro_chunks(long_text, max_chars=2500)
    assert len(chunks) >= 6
    for c in chunks:
        assert len(c) <= 2500
        assert len(c) > 0


@pytest.mark.asyncio
async def test_subtitle_formatting():
    """Kiểm tra sinh phụ đề chuẩn SRT và WebVTT."""
    segments = [
        {"text": "Xin chào các bạn.", "start": 0.0, "end": 2.5},
        {"text": "Chào mừng đến với Voxify.", "start": 2.5, "end": 5.0},
    ]
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".srt", delete=False) as srt_tmp:
        srt_file = srt_tmp.name
    with tempfile.NamedTemporaryFile(suffix=".vtt", delete=False) as vtt_tmp:
        vtt_file = vtt_tmp.name

    try:
        AudioService.generate_subtitles(segments, srt_file, vtt_file)

        with open(srt_file, "r", encoding="utf-8") as f:
            srt_content = f.read()
            assert "00:00:00,000 --> 00:00:02,500" in srt_content
            assert "Xin chào các bạn." in srt_content
            assert "00:00:02,500 --> 00:00:05,000" in srt_content

        with open(vtt_file, "r", encoding="utf-8") as f:
            vtt_content = f.read()
            assert "WEBVTT" in vtt_content
            assert "00:00:00.000 --> 00:00:02.500" in vtt_content
    finally:
        import os
        if os.path.exists(srt_file): os.remove(srt_file)
        if os.path.exists(vtt_file): os.remove(vtt_file)


@pytest.mark.asyncio
async def test_dictionary_api_and_apply():
    """Kiểm tra API Từ điển phát âm cá nhân và hàm apply_dictionary."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Đăng ký tài khoản
        email = f"dict_test_{asyncio.get_event_loop().time()}@example.com"
        reg = await client.post("/api/auth/register", json={
            "email": email,
            "password": "password123",
            "full_name": "Dict Tester",
        })
        assert reg.status_code == 200
        user_id = reg.json()["id"]

        login = await client.post("/api/auth/login", json={
            "email": email,
            "password": "password123",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Thêm từ vào từ điển
        create_res = await client.post(
            "/api/dictionary",
            headers=headers,
            json={
                "word": "TP.HCM",
                "replacement": "Thành phố Hồ Chí Minh",
                "category": "abbreviation",
            },
        )
        assert create_res.status_code == 201
        rule_id = create_res.json()["id"]

        # 2. Lấy danh sách từ điển
        list_res = await client.get("/api/dictionary", headers=headers)
        assert list_res.status_code == 200
        assert any(r["word"] == "TP.HCM" for r in list_res.json())

        # 3. Kiểm tra áp dụng từ điển
        async with AsyncSessionLocal() as db:
            original_text = "Tôi đang sống tại TP.HCM rất vui vẻ."
            replaced = await DictionaryService.apply_dictionary(db, user_id, original_text)
            assert "Thành phố Hồ Chí Minh" in replaced
            assert "TP.HCM" not in replaced

        # 4. Tắt quy tắc
        toggle_res = await client.put(f"/api/dictionary/{rule_id}", headers=headers, json={"is_active": False})
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_active"] is False

        # Áp dụng lại khi quy tắc tắt
        async with AsyncSessionLocal() as db:
            replaced_off = await DictionaryService.apply_dictionary(db, user_id, original_text)
            assert "TP.HCM" in replaced_off

        # 5. Xóa quy tắc
        del_res = await client.delete(f"/api/dictionary/{rule_id}", headers=headers)
        assert del_res.status_code == 200


@pytest.mark.asyncio
async def test_tts_job_lifecycle():
    """Kiểm tra vòng đời đầy đủ của Background Job TTS."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Đăng ký tài khoản
        email = f"job_user_{asyncio.get_event_loop().time()}@example.com"
        reg = await client.post("/api/auth/register", json={
            "email": email,
            "password": "password123",
            "full_name": "Job User",
        })
        assert reg.status_code == 200

        login = await client.post("/api/auth/login", json={
            "email": email,
            "password": "password123",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Tạo Job bất đồng bộ
        text = "Xin chào các bạn, đây là kiểm thử job tạo giọng nói nền bất đồng bộ của Voxify."
        create_res = await client.post(
            "/api/tts/jobs",
            headers=headers,
            json={
                "text": text,
                "voice": "vi-VN-NamMinhNeural",
                "format": "mp3",
                "apply_dictionary": True,
            },
        )
        assert create_res.status_code == 202
        job_data = create_res.json()
        job_id = job_data["id"]
        assert job_data["status"] in ["queued", "processing"]
        assert job_data["char_count"] == len(text)

        # Polling job cho đến khi hoàn tất hoặc timeout (tối đa 20s)
        for _ in range(25):
            await asyncio.sleep(1.0)
            poll_res = await client.get(f"/api/tts/jobs/{job_id}", headers=headers)
            assert poll_res.status_code == 200
            current_job = poll_res.json()
            if current_job["status"] == "done":
                assert current_job["progress"] == 100
                assert current_job["duration"] > 0
                assert current_job["audio_url"] is not None
                assert current_job["srt_url"] is not None
                break
            if current_job["status"] == "failed":
                pytest.fail(f"Job #{job_id} thất bại: {current_job.get('error_message')}")
        else:
            pytest.fail("Polling Job timeout sau 25 giây")

        # Kiểm tra tải file audio
        audio_res = await client.get(f"/api/tts/jobs/{job_id}/audio", headers=headers)
        assert audio_res.status_code == 200
        assert len(audio_res.content) > 1000

        # Kiểm tra tải file phụ đề SRT
        srt_res = await client.get(f"/api/tts/jobs/{job_id}/subtitles?format=srt", headers=headers)
        assert srt_res.status_code == 200
        assert "-->" in srt_res.text
