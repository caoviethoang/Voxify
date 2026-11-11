"""Unit & Integration tests cho Khung Công cụ Âm thanh (Audio Tools Framework) — Issue #20."""
from __future__ import annotations

import io
import json
import os
import time
from typing import Dict, Tuple

import pytest
from httpx import ASGITransport, AsyncClient

from app.audio_tools.base import AudioTool, AudioToolCategory, registry
from app.core.security import create_access_token, hash_password
from app.db import AsyncSessionLocal
from app.main import app
from app.models.generation import Generation
from app.models.user import User
from app.services.audio_tool_service import AudioToolService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_auth_headers(credits: int = 50000) -> Tuple[Dict[str, str], int]:
    email = f"tool_user_{time.time_ns()}@test.com"
    password = "ToolPassword123!"
    async with AsyncSessionLocal() as db:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name="Tool User",
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


def _dummy_audio_bytes(duration_sec: float = 5.0) -> bytes:
    # Giả lập audio mp3 với header ID3
    size = int(duration_sec * 6000)
    return b"ID3\x03\x00\x00\x00\x00\x00#" + b"\x00" * max(100, size)


# ---------------------------------------------------------------------------
# 1. Registry & Tool Extensibility Tests
# ---------------------------------------------------------------------------

def test_registry_contains_builtin_tools() -> None:
    tools = registry.list_tools()
    assert len(tools) >= 5
    ids = [t.id for t in tools]
    assert "trim" in ids
    assert "volume_normalize" in ids
    assert "format_converter" in ids
    assert "tempo_pitch" in ids
    assert "noise_reduction" in ids
    assert "ai_vocal_remover" in ids


def test_registry_get_by_category() -> None:
    categories = registry.get_by_category()
    assert AudioToolCategory.TRIM_CUT in categories
    assert AudioToolCategory.VOLUME_DYNAMICS in categories
    assert AudioToolCategory.FORMAT_CONVERSION in categories
    assert len(categories[AudioToolCategory.TRIM_CUT]["tools"]) >= 1


def test_extensibility_custom_tool_registration() -> None:
    class CustomEchoTool(AudioTool):
        id = f"custom_echo_{time.time_ns()}"
        name_vi = "Hiệu ứng Vang vọng"
        name_en = "Echo Effect"
        description_vi = "Tạo hiệu ứng tiếng vang đa chiều"
        description_en = "Multi-dimensional echo effect"
        category = AudioToolCategory.EFFECTS
        icon = "Wand2"
        params_schema = {
            "type": "object",
            "properties": {"delay_ms": {"type": "integer", "default": 200}},
        }
        cost = {"type": "free"}

        async def run(self, input_path: str, params: dict, output_path: str, progress_cb=None):
            await self._safe_copy_fallback(input_path, output_path)
            return {"output_path": output_path, "duration": 5.0, "size_bytes": 1000}

    custom_tool = CustomEchoTool()
    registry.register(custom_tool)
    assert registry.get(custom_tool.id) is custom_tool

    # Kiểm tra tự động xuất hiện trong list_tools và to_dict
    d = custom_tool.to_dict()
    assert d["id"] == custom_tool.id
    assert d["category_name_vi"] == "Hiệu ứng"


# ---------------------------------------------------------------------------
# 2. Builtin Tools Direct Runner Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_builtin_trim_tool_run(tmp_path) -> None:
    tool = registry.get("trim")
    assert tool is not None

    in_file = tmp_path / "in.mp3"
    out_file = tmp_path / "out.mp3"
    in_file.write_bytes(_dummy_audio_bytes(10.0))

    progress_log = []
    async def cb(pct: int):
        progress_log.append(pct)

    res = await tool.run(
        input_path=str(in_file),
        params={"start_time": 1.0, "end_time": 4.0, "fade_in": True, "fade_out": True},
        output_path=str(out_file),
        progress_cb=cb,
    )
    assert "output_path" in res
    assert os.path.exists(res["output_path"])
    assert len(progress_log) > 0


@pytest.mark.asyncio
async def test_builtin_volume_normalize_tool_run(tmp_path) -> None:
    tool = registry.get("volume_normalize")
    assert tool is not None

    in_file = tmp_path / "in.mp3"
    out_file = tmp_path / "out.mp3"
    in_file.write_bytes(_dummy_audio_bytes(5.0))

    res = await tool.run(
        input_path=str(in_file),
        params={"gain_db": 3.0, "normalize": True},
        output_path=str(out_file),
    )
    assert os.path.exists(res["output_path"])


@pytest.mark.asyncio
async def test_builtin_format_converter_tool_run(tmp_path) -> None:
    tool = registry.get("format_converter")
    assert tool is not None

    in_file = tmp_path / "in.mp3"
    out_file = tmp_path / "out.wav"
    in_file.write_bytes(_dummy_audio_bytes(5.0))

    res = await tool.run(
        input_path=str(in_file),
        params={"format": "wav", "bitrate": "192k", "sample_rate": "44100"},
        output_path=str(out_file),
    )
    assert os.path.exists(res["output_path"])


@pytest.mark.asyncio
async def test_builtin_tempo_pitch_tool_run(tmp_path) -> None:
    tool = registry.get("tempo_pitch")
    assert tool is not None

    in_file = tmp_path / "in.mp3"
    out_file = tmp_path / "out.mp3"
    in_file.write_bytes(_dummy_audio_bytes(5.0))

    res = await tool.run(
        input_path=str(in_file),
        params={"tempo": 1.25, "pitch_semitones": 2},
        output_path=str(out_file),
    )
    assert os.path.exists(res["output_path"])


@pytest.mark.asyncio
async def test_builtin_noise_reduction_tool_run(tmp_path) -> None:
    tool = registry.get("noise_reduction")
    assert tool is not None

    in_file = tmp_path / "in.mp3"
    out_file = tmp_path / "out.mp3"
    in_file.write_bytes(_dummy_audio_bytes(5.0))

    res = await tool.run(
        input_path=str(in_file),
        params={"reduction_level": "medium", "highpass_hz": 80},
        output_path=str(out_file),
    )
    assert os.path.exists(res["output_path"])


@pytest.mark.asyncio
async def test_builtin_ai_vocal_remover_tool_run(tmp_path) -> None:
    tool = registry.get("ai_vocal_remover")
    assert tool is not None

    in_file = tmp_path / "in.mp3"
    out_file = tmp_path / "out.mp3"
    in_file.write_bytes(_dummy_audio_bytes(5.0))

    res = await tool.run(
        input_path=str(in_file),
        params={"mode": "instrumental"},
        output_path=str(out_file),
    )
    assert os.path.exists(res["output_path"])


# ---------------------------------------------------------------------------
# 3. AudioToolService Unit Tests
# ---------------------------------------------------------------------------

def test_audio_tool_service_cost_calculation() -> None:
    service = AudioToolService()
    # Free tool
    assert service.calculate_cost({"type": "free"}, 120.0) == 0
    # Fixed tool
    assert service.calculate_cost({"type": "fixed", "rate": 10}, 45.0) == 10
    # Per minute: 30s -> 1 min -> 2 credits
    assert service.calculate_cost({"type": "per_minute", "rate": 2}, 30.0) == 2
    # Per minute: 65s -> 2 min -> 4 credits
    assert service.calculate_cost({"type": "per_minute", "rate": 2}, 65.0) == 4
    # Unknown cost type
    assert service.calculate_cost({"type": "custom"}, 100.0) == 0


@pytest.mark.asyncio
async def test_audio_tool_service_missing_input_error() -> None:
    from app.core.errors import AppError

    service = AudioToolService()
    async with AsyncSessionLocal() as db:
        user = User(email=f"u_{time.time_ns()}@test.com", full_name="User", credit_balance=100)
        with pytest.raises(AppError) as exc_info:
            await service.create_and_execute_job(
                db=db,
                user=user,
                tool_id="trim",
                params={},
                file_bytes=None,
                filename=None,
                source_path=None,
            )
        assert exc_info.value.code == "MISSING_INPUT_AUDIO"


@pytest.mark.asyncio
async def test_audio_tool_service_invalid_tool_error() -> None:
    from app.core.errors import AppError

    service = AudioToolService()
    async with AsyncSessionLocal() as db:
        user = User(email=f"u_{time.time_ns()}@test.com", full_name="User", credit_balance=100)
        with pytest.raises(AppError) as exc_info:
            await service.create_and_execute_job(
                db=db,
                user=user,
                tool_id="nonexistent_super_tool",
                params={},
                file_bytes=_dummy_audio_bytes(),
                filename="sample.mp3",
            )
        assert exc_info.value.code == "TOOL_NOT_FOUND"


# ---------------------------------------------------------------------------
# 4. API Endpoints Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_list_tools() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "tools" in data
        assert "categories" in data
        assert data["total"] >= 5


@pytest.mark.asyncio
async def test_api_get_tool_detail() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/tools/trim")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "trim"
        assert "params_schema" in data

        # Non-existent tool
        resp_404 = await client.get("/api/tools/nonexistent_tool_id")
        assert resp_404.status_code == 404


@pytest.mark.asyncio
async def test_api_create_job_with_upload() -> None:
    headers, _ = await _get_auth_headers(credits=1000)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        audio_content = _dummy_audio_bytes(5.0)
        files = {
            "audio_file": ("test_sample.mp3", io.BytesIO(audio_content), "audio/mpeg"),
        }
        data = {
            "params": json.dumps({"start_time": 0.0, "end_time": 3.0}),
        }

        resp = await client.post(
            "/api/tools/trim/jobs",
            headers=headers,
            data=data,
            files=files,
        )
        assert resp.status_code == 201
        job_data = resp.json()
        assert job_data["status"] == "done"
        assert job_data["progress"] == 100
        assert job_data["tool_id"] == "trim"
        assert "output_url" in job_data

        job_id = job_data["id"]

        # Tra cứu chi tiết job
        resp_detail = await client.get(f"/api/tools/jobs/{job_id}", headers=headers)
        assert resp_detail.status_code == 200
        assert resp_detail.json()["id"] == job_id

        # Stream audio
        resp_stream = await client.get(f"/api/tools/jobs/{job_id}/stream", headers=headers)
        assert resp_stream.status_code == 200

        # Download audio
        resp_download = await client.get(f"/api/tools/jobs/{job_id}/download", headers=headers)
        assert resp_download.status_code == 200
        assert "attachment" in resp_download.headers.get("Content-Disposition", "")


@pytest.mark.asyncio
async def test_api_create_job_from_source_generation(tmp_path) -> None:
    headers, user_id = await _get_auth_headers(credits=1000)
    gen_file = tmp_path / "tts_output.mp3"
    gen_file.write_bytes(_dummy_audio_bytes(5.0))

    # Tạo generation mẫu
    async with AsyncSessionLocal() as db:
        gen = Generation(
            user_id=user_id,
            text="Xin chào Việt Nam",
            voice="vi-VN-NamMinhNeural",
            file_path=str(gen_file),
            format="mp3",
            duration=5.0,
            char_count=16,
            credit_used=2,
            status="done",
        )
        db.add(gen)
        await db.commit()
        await db.refresh(gen)
        gen_id = gen.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/tools/volume_normalize/jobs",
            headers=headers,
            data={
                "source_generation_id": str(gen_id),
                "params": json.dumps({"gain_db": 2.0}),
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "done"


@pytest.mark.asyncio
async def test_api_create_job_chaining_tools() -> None:
    headers, _ = await _get_auth_headers(credits=1000)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Trim
        files = {
            "audio_file": ("chain_in.mp3", io.BytesIO(_dummy_audio_bytes(6.0)), "audio/mpeg"),
        }
        res1 = await client.post(
            "/api/tools/trim/jobs",
            headers=headers,
            data={"params": json.dumps({"start_time": 0.0, "end_time": 4.0})},
            files=files,
        )
        assert res1.status_code == 201
        job1_id = res1.json()["id"]

        # Step 2: Format Convert reusing job1 output
        res2 = await client.post(
            "/api/tools/format_converter/jobs",
            headers=headers,
            data={
                "source_tool_job_id": str(job1_id),
                "params": json.dumps({"format": "wav"}),
            },
        )
        assert res2.status_code == 201
        job2 = res2.json()
        assert job2["status"] == "done"
        assert job2["output_filename"].endswith(".wav")


@pytest.mark.asyncio
async def test_api_list_user_jobs() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/tools/jobs", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "jobs" in data


@pytest.mark.asyncio
async def test_api_job_not_found_and_errors() -> None:
    headers, _ = await _get_auth_headers()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid job id
        res = await client.get("/api/tools/jobs/999999", headers=headers)
        assert res.status_code == 404

        # Stream non-existent
        res_stream = await client.get("/api/tools/jobs/999999/stream", headers=headers)
        assert res_stream.status_code == 404

        # Bad params json
        res_bad_json = await client.post(
            "/api/tools/trim/jobs",
            headers=headers,
            data={"params": "{bad_json}"},
        )
        assert res_bad_json.status_code == 400

        # No audio source provided
        res_no_audio = await client.post(
            "/api/tools/trim/jobs",
            headers=headers,
            data={"params": "{}"},
        )
        assert res_no_audio.status_code == 400
