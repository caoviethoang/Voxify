"""Công cụ Điều chỉnh & Chuẩn hóa âm lượng (Volume & Normalize) — Audio Tools Framework."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from app.audio_tools.base import AudioTool, AudioToolCategory

logger = logging.getLogger(__name__)


class VolumeNormalizeTool(AudioTool):
    id = "volume_normalize"
    name_vi = "Âm lượng & Chuẩn hóa"
    name_en = "Volume & Loudness Normalization"
    description_vi = "Tăng giảm độ lớn âm thanh hoặc chuẩn hóa mức âm theo tiêu chuẩn phát thanh EBU R128."
    description_en = "Adjust audio gain or normalize loudness to broadcast standards (EBU R128)."
    category = AudioToolCategory.VOLUME_DYNAMICS
    icon = "Volume2"
    heavy = False
    cost = {"type": "free"}

    params_schema = {
        "type": "object",
        "title": "Cấu hình âm lượng & chuẩn hóa",
        "properties": {
            "gain_db": {
                "type": "number",
                "title": "Tăng giảm âm lượng (dB)",
                "description": "Giá trị âm làm giảm, dương làm tăng (-24 dB đến +24 dB)",
                "minimum": -24.0,
                "maximum": 24.0,
                "default": 0.0,
                "ui:widget": "slider",
                "ui:min": -24,
                "ui:max": 24,
                "ui:step": 1,
            },
            "normalize": {
                "type": "boolean",
                "title": "Chuẩn hóa âm lượng EBU R128 (-16 LUFS)",
                "description": "Cân bằng âm thanh tự động, tránh rè tiếng và đều đặn xuyên suốt",
                "default": True,
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

        gain_db = float(params.get("gain_db", 0.0))
        normalize = bool(params.get("normalize", True))

        filters = []
        if normalize:
            # loudnorm chuẩn EBU R128
            filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
        if gain_db != 0.0:
            filters.append(f"volume={gain_db}dB")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
        ]

        if filters:
            cmd.extend(["-af", ",".join(filters)])

        cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k", output_path])

        if progress_cb:
            await progress_cb(40)

        await self.run_ffmpeg_command(cmd, input_path, output_path, "volume")

        if progress_cb:
            await progress_cb(100)

        return self.build_tool_result(
            output_path,
            extra={"gain_applied": gain_db, "normalized": normalize},
        )
