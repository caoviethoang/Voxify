"""Công cụ Cắt âm thanh (Trim Audio) — Audio Tools Framework."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from app.audio_tools.base import AudioTool, AudioToolCategory
from app.services.audio_service import AudioService

logger = logging.getLogger(__name__)


class TrimAudioTool(AudioTool):
    id = "trim"
    name_vi = "Cắt & Ghép âm thanh"
    name_en = "Trim & Cut Audio"
    description_vi = "Cắt lấy đoạn âm thanh mong muốn, tạo hiệu ứng Fade In / Fade Out mượt mà."
    description_en = "Trim selected audio segments with smooth fade-in and fade-out transitions."
    category = AudioToolCategory.TRIM_CUT
    icon = "Scissors"
    heavy = False
    cost = {"type": "free"}

    params_schema = {
        "type": "object",
        "title": "Cấu hình cắt đoạn âm thanh",
        "required": ["start_time", "end_time"],
        "properties": {
            "start_time": {
                "type": "number",
                "title": "Thời gian bắt đầu (giây)",
                "description": "Điểm bắt đầu cắt tính bằng giây",
                "minimum": 0.0,
                "default": 0.0,
                "ui:widget": "number",
                "ui:step": 0.1,
            },
            "end_time": {
                "type": "number",
                "title": "Thời gian kết thúc (giây)",
                "description": "Điểm kết thúc cắt tính bằng giây",
                "minimum": 0.1,
                "default": 10.0,
                "ui:widget": "number",
                "ui:step": 0.1,
            },
            "fade_in": {
                "type": "boolean",
                "title": "Hiệu ứng mở đầu mượt mà (Fade In 0.5s)",
                "description": "Tăng âm lượng từ từ khi bắt đầu đoạn cắt",
                "default": False,
                "ui:widget": "switch",
            },
            "fade_out": {
                "type": "boolean",
                "title": "Hiệu ứng kết thúc mượt mà (Fade Out 0.5s)",
                "description": "Giảm âm lượng dần khi kết thúc đoạn cắt",
                "default": False,
                "ui:widget": "switch",
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

        start = float(params.get("start_time", 0.0))
        end = float(params.get("end_time", 10.0))
        duration = max(0.1, end - start)
        fade_in = bool(params.get("fade_in", False))
        fade_out = bool(params.get("fade_out", False))

        filters = []
        if fade_in:
            filters.append("afade=t=in:ss=0:d=0.5")
        if fade_out and duration > 1.0:
            filters.append(f"afade=t=out:st={duration - 0.5}:d=0.5")

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(duration),
            "-i", input_path,
        ]

        if filters:
            cmd.extend(["-af", ",".join(filters)])

        cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k", output_path])

        if progress_cb:
            await progress_cb(30)

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
                logger.warning(f"ffmpeg trim thất bại: {stderr.decode('utf-8', errors='ignore')}")
        except Exception as e:
            logger.warning(f"Không thể chạy ffmpeg cho trim: {e}")

        if not success:
            # Fallback
            await self._safe_copy_fallback(input_path, output_path)

        if progress_cb:
            await progress_cb(100)

        measured_duration = AudioService.measure_duration(output_path) or duration
        size_bytes = os.path.getsize(output_path) if os.path.exists(output_path) else 0

        return {
            "output_path": output_path,
            "output_filename": Path(output_path).name,
            "duration": round(measured_duration, 2),
            "size_bytes": size_bytes,
            "extra": {"trimmed_duration": round(duration, 2)},
        }
