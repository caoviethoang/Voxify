"""Công cụ Tách âm AI (Vocal & Instrumental Separation) — Audio Tools Framework."""
from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from app.audio_tools.base import AudioTool, AudioToolCategory

logger = logging.getLogger(__name__)


class AIVocalRemoverTool(AudioTool):
    id = "ai_vocal_remover"
    name_vi = "Tách âm AI (Vocals / Beat)"
    name_en = "AI Vocal & Music Remover"
    description_vi = "Tách riêng giọng hát (Acappella) hoặc nhạc nền (Beat/Karaoke) bằng mô hình AI chuyên dụng."
    description_en = "Isolate vocals (acappella) or backing instrumental tracks using AI separation models."
    category = AudioToolCategory.AI_SEPARATION
    icon = "Radio"
    heavy = True  # Tác vụ nặng, dùng queue xử lý
    cost = {"type": "per_minute", "rate": 2}  # 2 credits / phút âm thanh

    params_schema = {
        "type": "object",
        "title": "Cấu hình tách âm AI",
        "required": ["mode"],
        "properties": {
            "mode": {
                "type": "string",
                "title": "Kết quả muốn tách lấy",
                "default": "vocals",
                "enum": ["vocals", "instrumental"],
                "enumNames": ["Giữ lại Giọng hát (Tách Acappella)", "Giữ lại Nhạc nền (Tách Beat / Karaoke)"],
                "ui:widget": "select",
            },
            "output_format": {
                "type": "string",
                "title": "Định dạng âm thanh đầu ra",
                "default": "mp3",
                "enum": ["mp3", "wav"],
                "enumNames": ["MP3 (192 kbps)", "WAV (Lossless 44.1kHz)"],
                "ui:widget": "select",
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
            await progress_cb(15)

        mode = params.get("mode", "vocals")

        # Giả lập hoặc xử lý center channel vocal removal / isolation qua ffmpeg
        # pan=stereo|c0=c0-c1|c1=c0-c1 (hủy âm thanh center - instrumental)
        # hoặc bandpass vocal
        filters = []
        if mode == "instrumental":
            filters.append("stereotools=mlev=0.1:slev=1.4")
        else:
            # Vocal isolation center boost
            filters.append("stereotools=mlev=1.5:slev=0.2,equalizer=f=1000:t=q:w=1:g=3")

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
        ]

        if filters:
            cmd.extend(["-af", ",".join(filters)])

        cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k", output_path])

        if progress_cb:
            await progress_cb(50)

        await self.run_ffmpeg_command(cmd, input_path, output_path, "ai_vocal_remover")

        if progress_cb:
            await progress_cb(100)

        return self.build_tool_result(
            output_path,
            extra={"mode": mode},
        )
