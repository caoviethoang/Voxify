"""Công cụ Thay đổi Tốc độ & Cao độ (Tempo & Pitch) — Audio Tools Framework."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from app.audio_tools.base import AudioTool, AudioToolCategory
from app.services.audio_service import AudioService

logger = logging.getLogger(__name__)


class TempoPitchTool(AudioTool):
    id = "tempo_pitch"
    name_vi = "Tốc độ & Cao độ"
    name_en = "Speed & Pitch Shifter"
    description_vi = "Điều chỉnh tốc độ nhanh/chậm giữ nguyên giọng, hoặc nâng hạ tone giọng (pitch shift)."
    description_en = "Adjust tempo with pitch preservation or shift musical pitch."
    category = AudioToolCategory.EFFECTS
    icon = "Sliders"
    heavy = False
    cost = {"type": "free"}

    params_schema = {
        "type": "object",
        "title": "Cấu hình tốc độ & cao độ",
        "properties": {
            "tempo": {
                "type": "number",
                "title": "Tốc độ phát (0.5x – 2.0x)",
                "description": "Giá trị < 1 làm chậm, > 1 làm nhanh",
                "minimum": 0.5,
                "maximum": 2.0,
                "default": 1.0,
                "ui:widget": "slider",
                "ui:min": 0.5,
                "ui:max": 2.0,
                "ui:step": 0.05,
            },
            "pitch_semitones": {
                "type": "integer",
                "title": "Đổi cao độ (Semitones: -6 đến +6)",
                "description": "Nâng hoặc hạ tone giọng",
                "minimum": -6,
                "maximum": 6,
                "default": 0,
                "ui:widget": "slider",
                "ui:min": -6,
                "ui:max": 6,
                "ui:step": 1,
            },
        },
    }

    async def run(
        self,
        input_path: str,
        params: Dict[str, Any],
        output_path: str,
        progress_cb: Optional[Callable[[int], Awaitable[None]]] = None,
    ) -> Dict[str, Any]:
        if progress_cb:
            await progress_cb(10)

        tempo = float(params.get("tempo", 1.0))
        pitch = int(params.get("pitch_semitones", 0))

        filters = []
        # Tốc độ atempo (hỗ trợ 0.5 đến 2.0 trong 1 filter)
        if abs(tempo - 1.0) > 0.01:
            filters.append(f"atempo={tempo}")

        # Cao độ pitch: dùng asetrate + atempo để đổi pitch
        if pitch != 0:
            pitch_ratio = 2.0 ** (pitch / 12.0)
            filters.append(f"asetrate=44100*{pitch_ratio},aresample=44100,atempo={1.0 / pitch_ratio}")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
        ]

        if filters:
            cmd.extend(["-af", ",".join(filters)])

        cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k", output_path])

        if progress_cb:
            await progress_cb(40)

        success = False
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            if proc.returncode == 0:
                success = True
            else:
                logger.warning(f"ffmpeg tempo_pitch thất bại: {stderr.decode('utf-8', errors='ignore')}")
        except Exception as e:
            logger.warning(f"Không thể chạy ffmpeg cho tempo_pitch: {e}")

        if not success:
            await self._safe_copy_fallback(input_path, output_path)

        if progress_cb:
            await progress_cb(100)

        measured_duration = AudioService.measure_duration(output_path)
        size_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        return {
            "output_path": output_path,
            "output_filename": Path(output_path).name,
            "duration": round(measured_duration, 2),
            "size_bytes": size_bytes,
            "extra": {"tempo": tempo, "pitch_semitones": pitch},
        }
