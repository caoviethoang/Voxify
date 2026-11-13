"""Công cụ Chuyển đổi định dạng âm thanh (Format Converter) — Audio Tools Framework."""
from __future__ import annotations

import logging
import os
from typing import Any, Awaitable, Callable, Dict, Optional

from app.audio_tools.base import AudioTool, AudioToolCategory

logger = logging.getLogger(__name__)


class FormatConverterTool(AudioTool):
    id = "format_converter"
    name_vi = "Chuyển đổi định dạng"
    name_en = "Audio Format Converter"
    description_vi = "Chuyển đổi tệp âm thanh sang các định dạng phổ biến: MP3, WAV, AAC, FLAC với tùy chọn bitrate."
    description_en = "Convert audio files to MP3, WAV, AAC, FLAC with customizable bitrate options."
    category = AudioToolCategory.FORMAT_CONVERSION
    icon = "FileAudio"
    heavy = False
    cost = {"type": "free"}

    params_schema = {
        "type": "object",
        "title": "Cấu hình chuyển đổi định dạng",
        "required": ["format"],
        "properties": {
            "format": {
                "type": "string",
                "title": "Định dạng âm thanh đầu ra",
                "default": "mp3",
                "enum": ["mp3", "wav", "aac", "flac"],
                "enumNames": ["MP3 (.mp3)", "WAV (.wav - Không nén)", "AAC (.m4a)", "FLAC (.flac - Lossless)"],
                "ui:widget": "select",
            },
            "bitrate": {
                "type": "string",
                "title": "Chất lượng Bitrate",
                "default": "192k",
                "enum": ["128k", "192k", "256k", "320k"],
                "enumNames": ["128 kbps (Nhẹ)", "192 kbps (Tiêu chuẩn)", "256 kbps (Chất lượng cao)", "320 kbps (Phòng thu)"],
                "ui:widget": "select",
            },
            "sample_rate": {
                "type": "string",
                "title": "Tần số lấy mẫu (Sample Rate)",
                "default": "44100",
                "enum": ["22050", "44100", "48000"],
                "enumNames": ["22.05 kHz", "44.1 kHz (CD Standard)", "48.0 kHz (Studio Video)"],
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
            await progress_cb(10)

        target_fmt = str(params.get("format", "mp3")).lower()
        bitrate = str(params.get("bitrate", "192k"))
        sample_rate = str(params.get("sample_rate", "44100"))

        # Điều chỉnh phần mở rộng file nếu cần
        base, _ = os.path.splitext(output_path)
        actual_output = f"{base}.{target_fmt}"

        cmd = [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", sample_rate,
        ]

        if target_fmt == "wav":
            cmd.extend(["-c:a", "pcm_s16le", actual_output])
        elif target_fmt == "flac":
            cmd.extend(["-c:a", "flac", actual_output])
        elif target_fmt == "aac":
            cmd.extend(["-c:a", "aac", "-b:a", bitrate, actual_output])
        else:
            cmd.extend(["-c:a", "libmp3lame", "-b:a", bitrate, actual_output])

        if progress_cb:
            await progress_cb(35)

        await self.run_ffmpeg_command(cmd, input_path, actual_output, "format_converter")

        if progress_cb:
            await progress_cb(100)

        return self.build_tool_result(
            actual_output,
            extra={"format": target_fmt, "bitrate": bitrate},
        )
