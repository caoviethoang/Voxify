"""Unit & Integration tests cho tính năng Lồng tiếng phụ đề (Subtitle Dubbing - Issue #21)."""
from __future__ import annotations

import io
import time
from typing import Dict, Tuple
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.db import AsyncSessionLocal
from app.main import app
from app.models.dubbing import DubbingJob
from app.models.user import User
from app.schemas.dubbing import DubbingCreateJobRequest, SubtitleCueItem
from app.services.dubbing_service import DubbingService
from app.services.storage_service import StorageService
from app.services.subtitle_parser import (
    SubtitleParser,
    format_seconds_to_timestamp,
    parse_timestamp_to_seconds,
)
from app.services.tts_service import TTSService

# ---------------------------------------------------------------------------
# Test Data Fixtures
# ---------------------------------------------------------------------------

SAMPLE_SRT = """\
1
00:00:01,000 --> 00:00:03,500
[Voice: vi-VN-NamMinhNeural] Xin chào mọi người, đây là Voxify.

2
00:00:04,000 --> 00:00:06,800
Hệ thống lồng tiếng video tự động và chuẩn xác.

3
00:00:07,200 --> 00:00:10,000
<i>Đồng bộ thời gian theo từng giây!</i>
"""

SAMPLE_VTT = """\
WEBVTT - Demo Subtitles

00:00:01.200 --> 00:00:03.800
<v vi-VN-HoaiMyNeural>Chào mừng bạn đến với Studio lồng tiếng.

00:00:04.500 --> 00:00:07.000
<b>Khớp thời gian hoàn hảo và chất lượng cao.</b>
"""


async def _get_auth_headers(credits: int = 50000) -> Tuple[Dict[str, str], int]:
    email = f"dubbing_user_{time.time_ns()}@test.com"
    password = "DubbingPassword123!"
    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Dubbing User",
            role="user",
            is_active=True,
            is_verified=True,
            credit_balance=credits,
            credits=credits,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        user_id = user.id

    token = create_access_token(data={"sub": str(user_id), "email": email, "role": "user"})
    return {"Authorization": f"Bearer {token}"}, user_id


def _dummy_audio_bytes(size: int = 6000) -> bytes:
    return b"ID3\x03\x00\x00\x00\x00\x00#" + b"\x00" * max(100, size)


# ---------------------------------------------------------------------------
# 1. Subtitle Parser Unit Tests
# ---------------------------------------------------------------------------

def test_parse_timestamp_to_seconds() -> None:
    assert parse_timestamp_to_seconds("00:00:01,500") == 1.5
    assert parse_timestamp_to_seconds("00:01:23.456") == 83.456
    assert parse_timestamp_to_seconds("01:30.000") == 90.0
    assert parse_timestamp_to_seconds("15.5") == 15.5


def test_format_seconds_to_timestamp() -> None:
    assert format_seconds_to_timestamp(1.5, is_vtt=False) == "00:00:01,500"
    assert format_seconds_to_timestamp(83.456, is_vtt=True) == "00:01:23.456"
    assert format_seconds_to_timestamp(-5.0) == "00:00:00,000"


def test_clean_subtitle_text() -> None:
    # Tag [Voice: ...]
    text, voice = SubtitleParser.clean_subtitle_text("[Voice: vi-VN-NamMinhNeural] Xin chào bạn")
    assert voice == "vi-VN-NamMinhNeural"
    assert text == "Xin chào bạn"

    # Tag VTT <v Speaker>
    text_vtt, voice_vtt = SubtitleParser.clean_subtitle_text("<v HoaiMy> Đây là phụ đề WebVTT")
    assert voice_vtt == "HoaiMy"
    assert text_vtt == "Đây là phụ đề WebVTT"

    # Thẻ HTML định dạng (<b>, <i>...)
    text_html, _ = SubtitleParser.clean_subtitle_text("<b>Văn bản đậm</b> và <i>nghiêng</i>")
    assert text_html == "Văn bản đậm và nghiêng"


def test_parse_srt_content() -> None:
    cues = SubtitleParser.parse(SAMPLE_SRT, default_voice="vi-VN-HoaiMyNeural")
    assert len(cues) == 3

    assert cues[0]["index"] == 1
    assert cues[0]["start"] == 1.0
    assert cues[0]["end"] == 3.5
    assert cues[0]["duration"] == 2.5
    assert cues[0]["voice"] == "vi-VN-NamMinhNeural"
    assert "Xin chào mọi người" in cues[0]["text"]

    assert cues[1]["index"] == 2
    assert cues[1]["voice"] == "vi-VN-HoaiMyNeural"

    assert cues[2]["index"] == 3
    assert cues[2]["text"] == "Đồng bộ thời gian theo từng giây!"


def test_parse_vtt_content() -> None:
    cues = SubtitleParser.parse(SAMPLE_VTT, default_voice="vi-VN-HoaiMyNeural")
    assert len(cues) == 2

    assert cues[0]["index"] == 1
    assert cues[0]["start"] == 1.2
    assert cues[0]["end"] == 3.8
    assert cues[0]["voice"] == "vi-VN-HoaiMyNeural"
    assert "Chào mừng bạn" in cues[0]["text"]


def test_parse_empty_and_bom_content() -> None:
    assert SubtitleParser.parse("") == []
    bom_content = "\ufeff1\n00:00:01,000 --> 00:00:02,000\nNội dung có BOM\n"
    cues = SubtitleParser.parse(bom_content)
    assert len(cues) == 1
    assert cues[0]["text"] == "Nội dung có BOM"


# ---------------------------------------------------------------------------
# 2. Dubbing Service Unit Tests
# ---------------------------------------------------------------------------

def test_dubbing_service_parse_content() -> None:
    resp = DubbingService.parse_content(SAMPLE_SRT)
    assert resp.total_cues == 3
    assert resp.char_count > 0
    assert resp.estimated_credits > 0
    assert len(resp.cues) == 3


@pytest.mark.asyncio
async def test_adjust_audio_tempo_no_speedup() -> None:
    # Trường hợp thời lượng thực tế nhỏ hơn hoặc bằng khung cho phép
    with patch("shutil.copy2") as mock_copy:
        out_file, tempo, warning = await DubbingService.adjust_audio_tempo(
            input_file="in.mp3", output_file="out.mp3", target_duration=5.0, actual_duration=4.0
        )
        assert tempo == 1.0
        assert warning is None
        mock_copy.assert_called_once()


@pytest.mark.asyncio
async def test_adjust_audio_tempo_within_safe_limit() -> None:
    # Trường hợp thoại dài hơn nhưng nằm trong ngưỡng an toàn <= 1.35x
    with patch("asyncio.create_subprocess_exec") as mock_proc, \
         patch("os.path.exists", return_value=True), \
         patch("os.path.getsize", return_value=1000):
        mock_p = AsyncMock()
        mock_p.returncode = 0
        mock_p.communicate.return_value = (b"", b"")
        mock_proc.return_value = mock_p

        out_file, tempo, warning = await DubbingService.adjust_audio_tempo(
            input_file="in.mp3", output_file="out.mp3", target_duration=2.0, actual_duration=2.4
        )
        assert tempo == 1.2
        assert warning is None


@pytest.mark.asyncio
async def test_adjust_audio_tempo_exceeding_limit_warning() -> None:
    # Trường hợp thoại quá dài, cần speedup > 1.35x -> áp dụng 1.35x và trả cảnh báo
    with patch("asyncio.create_subprocess_exec") as mock_proc, \
         patch("os.path.exists", return_value=True), \
         patch("os.path.getsize", return_value=1000):
        mock_p = AsyncMock()
        mock_p.returncode = 0
        mock_p.communicate.return_value = (b"", b"")
        mock_proc.return_value = mock_p

        out_file, tempo, warning = await DubbingService.adjust_audio_tempo(
            input_file="in.mp3", output_file="out.mp3", target_duration=1.0, actual_duration=2.0
        )
        assert tempo == 1.35
        assert warning is not None
        assert "tối đa 1.35x" in warning


@pytest.mark.asyncio
async def test_preview_cue_service() -> None:
    mock_tts = AsyncMock(spec=TTSService)
    mock_tts.synthesize.return_value = _dummy_audio_bytes(1000)

    with patch("app.services.audio_service.AudioService.measure_duration", return_value=2.0):
        audio_bytes, dur, tempo, warning = await DubbingService.preview_cue(
            text="Câu nghe thử nghiệm",
            voice="vi-VN-HoaiMyNeural",
            tts_service=mock_tts,
            target_duration=3.0,
        )
        assert len(audio_bytes) > 0
        assert dur == 2.0


@pytest.mark.asyncio
async def test_create_dubbing_job_and_execution() -> None:
    _, user_id = await _get_auth_headers(credits=10000)

    cue_items = [
        SubtitleCueItem(
            index=1,
            start=0.0,
            end=2.0,
            duration=2.0,
            text="Câu số một",
            voice="vi-VN-HoaiMyNeural",
            char_count=10,
        ),
        SubtitleCueItem(
            index=2,
            start=2.5,
            end=5.0,
            duration=2.5,
            text="Câu số hai dài hơn một chút",
            voice="vi-VN-HoaiMyNeural",
            char_count=26,
        ),
    ]
    req = DubbingCreateJobRequest(
        title="Job Lồng tiếng Test",
        subtitle_format="srt",
        target_format="mp3",
        default_voice="vi-VN-HoaiMyNeural",
        cues=cue_items,
        ducking_volume=0.2,
    )

    async with AsyncSessionLocal() as db:
        job = await DubbingService.create_dubbing_job(db=db, user_id=user_id, req=req)
        assert job.id is not None
        assert job.status == "queued"
        assert job.total_cues == 2
        assert job.credit_used > 0
        job_id = job.id

    # Giả lập worker thực thi job
    mock_tts = AsyncMock(spec=TTSService)
    mock_tts.synthesize.return_value = _dummy_audio_bytes(3000)

    storage = StorageService()

    async def mock_concat(segments, output_path, target_format="mp3"):
        with open(output_path, "wb") as f:
            f.write(b"ID3\x03fake_master_audio")
        return output_path, 5.0, 10000

    with patch("app.services.audio_service.AudioService.measure_duration", return_value=2.0), \
         patch("app.services.audio_service.AudioService.concat_audio_files", side_effect=mock_concat), \
         patch("app.services.audio_service.AudioService.generate_silence", return_value="silence.mp3"):
        await DubbingService.execute_dubbing_job(
            job_id=job_id,
            session_factory=AsyncSessionLocal,
            tts_service=mock_tts,
            storage_service=storage,
        )

    async with AsyncSessionLocal() as db:
        finished_job = await db.get(DubbingJob, job_id)
        assert finished_job is not None
        assert finished_job.status == "done"
        assert finished_job.progress == 100
        assert finished_job.output_audio_path is not None
        assert finished_job.output_zip_path is not None


# ---------------------------------------------------------------------------
# 3. API Integration Endpoints Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_parse_subtitles_endpoint() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/dubbing/parse",
            headers=headers,
            json={"content": SAMPLE_SRT, "default_voice": "vi-VN-HoaiMyNeural"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_cues"] == 3
        assert len(data["cues"]) == 3
        assert data["char_count"] > 0
        assert data["estimated_credits"] > 0


@pytest.mark.asyncio
async def test_api_upload_subtitle_file_endpoint() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # File hợp lệ (.srt)
        files = {"file": ("sub.srt", io.BytesIO(SAMPLE_SRT.encode("utf-8")), "text/plain")}
        resp = await client.post(
            "/api/dubbing/upload-file",
            headers=headers,
            files=files,
            data={"default_voice": "vi-VN-HoaiMyNeural"},
        )
        assert resp.status_code == 200
        assert resp.json()["total_cues"] == 3

        # File không đúng định dạng (.txt)
        bad_files = {"file": ("sub.txt", io.BytesIO(b"Hello"), "text/plain")}
        bad_resp = await client.post(
            "/api/dubbing/upload-file",
            headers=headers,
            files=bad_files,
        )
        assert bad_resp.status_code == 400


@pytest.mark.asyncio
async def test_api_preview_cue_endpoint() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)

    with patch.object(DubbingService, "preview_cue") as mock_prev:
        mock_prev.return_value = (_dummy_audio_bytes(2000), 2.5, 1.15, None)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/dubbing/preview-cue",
                headers=headers,
                json={
                    "text": "Câu nghe thử nhanh",
                    "voice": "vi-VN-HoaiMyNeural",
                    "target_duration": 2.2,
                },
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "audio/mpeg"
            assert resp.headers["x-actual-duration"] == "2.5"
            assert resp.headers["x-adjusted-tempo"] == "1.15"


@pytest.mark.asyncio
async def test_api_upload_bg_music_endpoint() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("background.mp3", io.BytesIO(_dummy_audio_bytes(1000)), "audio/mpeg")}
        resp = await client.post(
            "/api/dubbing/upload-bg-music",
            headers=headers,
            files=files,
        )
        assert resp.status_code == 200
        assert "background_audio_path" in resp.json()


@pytest.mark.asyncio
async def test_api_create_and_manage_dubbing_jobs() -> None:
    headers, user_id = await _get_auth_headers(credits=20000)
    transport = ASGITransport(app=app)

    cue_data = [
        {
            "index": 1,
            "start": 1.0,
            "end": 3.0,
            "duration": 2.0,
            "text": "Xin chào thế giới",
            "voice": "vi-VN-HoaiMyNeural",
            "char_count": 17,
        }
    ]

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Tạo Job
        create_resp = await client.post(
            "/api/dubbing/jobs",
            headers=headers,
            json={
                "title": "Kịch bản lồng tiếng 01",
                "subtitle_format": "srt",
                "target_format": "mp3",
                "default_voice": "vi-VN-HoaiMyNeural",
                "cues": cue_data,
                "ducking_volume": 0.2,
            },
        )
        assert create_resp.status_code == 201
        job_data = create_resp.json()
        job_id = job_data["id"]
        assert job_data["status"] == "queued"
        assert job_data["total_cues"] == 1

        # 2. Lấy chi tiết Job
        get_resp = await client.get(f"/api/dubbing/jobs/{job_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == job_id

        # 3. Lấy danh sách Jobs
        list_resp = await client.get("/api/dubbing/jobs", headers=headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # 4. Xóa Job
        del_resp = await client.delete(f"/api/dubbing/jobs/{job_id}", headers=headers)
        assert del_resp.status_code == 204

        # 5. Kiểm tra sau khi xóa -> 404
        get_after_del = await client.get(f"/api/dubbing/jobs/{job_id}", headers=headers)
        assert get_after_del.status_code == 404
