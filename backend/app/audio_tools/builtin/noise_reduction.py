"""Công cụ Lọc tạp âm & Tiếng ồn nền (Noise Reduction) — Audio Tools Framework."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from app.audio_tools.base import AudioTool, AudioToolCategory
from app.services.audio_service import AudioService

logger = logging.getLogger(__name__)


class NoiseReductionTool(AudioTool):
    id = "noise_reduction"
    name_vi = "Lọc tạp âm & Tiếng ồn"
    name_en = "Noise Reduction & De-Hum"
    description_vi = "Loại bỏ tiếng quạt, tiếng gió, ù điện và nâng cao độ trong trẻo của giọng nói."
    description_en = "Remove background noise, hum, hiss and enhance vocal clarity."
    category = AudioToolCategory.CLEANUP
    icon = "Sparkles"
    heavy = False
    cost = {"type": "free"}

    params_schema = {
        "type": "object",
        "title": "Cấu hình lọc tạp âm",
        "properties": {
            "reduction_level": {
                "type": "string",
                "title": "Mức độ lọc tiếng ồn",
                "default": "medium",
                "enum": ["light", "medium", "aggressive"],
                "enumNames": ["Nhẹ nhàng (Light)", "Vừa phải (Medium - Khuyên dùng)", "Mạnh mẽ (Aggressive)"],
                "ui:widget": "select",
            },
            "highpass_hz": {
                "type": "integer",
                "title": "Lọc tiếng ù tần số thấp (High-pass Hz)",
                "description": "Cắt tần số dưới ngưỡng để loại bỏ tiếng rung, gió mic (0 = tắt)",
                "minimum": 0,
                "maximum": 200,
                "default": 80,
                "ui:widget": "slider",
                "ui:min": 0,
                "ui:max": 200,
                "ui:step": 10,
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

        level = params.get("reduction_level", "medium")
        highpass_hz = int(params.get("highpass_hz", 80))

        filters = []
        if highpass_hz > 20:
            filters.append(f"highpass=f={highpass_hz}")

        # Lọc nhiễu dùng afftdn (FFT based noise reduction trong ffmpeg)
        # hoặc anlmdn (Non-local means)
        dn_strength = {"light": "nr=12:nf=-30", "medium": "nr=18:nf=-25", "aggressive": "nr=25:nf=-20"}.get(
            level, "nr=18:nf=-25"
        )
        filters.append(f"afftdn={dn_strength}")

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
                logger.warning(f"ffmpeg noise_reduction thất bại: {stderr.decode('utf-8', errors='ignore')}")
        except Exception as e:
            logger.warning(f"Không thể chạy ffmpeg cho noise_reduction: {e}")

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
            "extra": {"reduction_level": level, "highpass_hz": highpass_hz},
        }
