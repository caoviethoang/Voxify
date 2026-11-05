"""Service tiện ích xử lý âm thanh: đo thời lượng, ghép nối ffmpeg, chuyển định dạng và tạo phụ đề SRT/VTT."""
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

logger = logging.getLogger(__name__)


class AudioService:
    @staticmethod
    def measure_duration(file_path: str) -> float:
        """
        Đo độ dài file âm thanh tính bằng giây sử dụng ffprobe (hoặc fallback đọc kích thước).
        """
        if not os.path.exists(file_path):
            return 0.0

        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                file_path,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                duration = data.get("format", {}).get("duration")
                if duration:
                    return float(duration)
        except Exception as e:
            logger.warning(f"ffprobe không thể đo thời lượng file {file_path}: {e}")

        # Fallback ước lượng cơ bản cho MP3 (giả sử 48kbps mono ~ 6000 bytes/giây)
        try:
            size = os.path.getsize(file_path)
            return round(size / 6000.0, 2)
        except Exception:
            return 0.0

    @classmethod
    async def concat_audio_files(
        cls,
        file_paths: List[str],
        output_path: str,
        target_format: str = "mp3",
    ) -> Tuple[str, float, int]:
        """
        Ghép nhiều file âm thanh lại thành một file duy nhất qua ffmpeg.
        Hỗ trợ đầu ra định dạng mp3 hoặc wav.
        Trả về: (output_path, duration_seconds, file_size_bytes)
        """
        valid_files = [f for f in file_paths if os.path.exists(f) and os.path.getsize(f) > 0]
        if not valid_files:
            raise ValueError("Không có file âm thanh hợp lệ nào để ghép nối.")

        if len(valid_files) == 1 and valid_files[0].endswith(f".{target_format}"):
            # Chỉ có 1 file và đúng định dạng, copy trực tiếp
            import shutil
            shutil.copy2(valid_files[0], output_path)
            duration = cls.measure_duration(output_path)
            size = os.path.getsize(output_path)
            return output_path, duration, size

        # Tạo file danh sách cho ffmpeg concat demuxer
        temp_dir = Path(output_path).parent
        list_file_path = temp_dir / f"concat_list_{os.getpid()}_{id(file_paths)}.txt"
        with open(list_file_path, "w", encoding="utf-8") as f:
            for p in valid_files:
                # ffmpeg concat yêu cầu đường dẫn tuyệt đối hoặc escape
                abs_p = os.path.abspath(p).replace("'", "'\\''")
                f.write(f"file '{abs_p}'\n")

        try:
            # ffmpeg concat command
            cmd = [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file_path),
            ]

            if target_format == "wav":
                cmd.extend(["-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1", output_path])
            else:
                cmd.extend(["-c:a", "libmp3lame", "-b:a", "64k", "-ar", "24000", "-ac", "1", output_path])

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error(f"Lỗi khi ghép audio bằng ffmpeg: {stderr.decode('utf-8', errors='ignore')}")
                raise RuntimeError("Không thể ghép nối các đoạn âm thanh.")

            duration = cls.measure_duration(output_path)
            size = os.path.getsize(output_path)
            return output_path, duration, size

        finally:
            if os.path.exists(list_file_path):
                os.remove(list_file_path)

    @classmethod
    async def generate_silence(cls, duration_seconds: float, output_path: str) -> str:
        """Tạo đoạn âm thanh khoảng lặng (silence) qua ffmpeg anullsrc."""
        duration = max(0.1, min(duration_seconds, 30.0))
        cmd = [
            "ffmpeg",
            "-y",
            "-f", "lavfi",
            "-i", "anullsrc=r=24000:cl=mono",
            "-t", str(duration),
            "-q:a", "9",
            "-acodec", "libmp3lame",
            output_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return output_path

    @staticmethod
    def generate_subtitles(
        segments: List[Dict[str, Any]],
        srt_path: str,
        vtt_path: str,
    ) -> Tuple[str, str]:
        """
        Tạo file phụ đề chuẩn SRT và WebVTT từ danh sách các đoạn câu:
        segments: [{"text": str, "start": float, "end": float}]
        """
        def format_time_srt(seconds: float) -> str:
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int(round((seconds - int(seconds)) * 1000))
            return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

        def format_time_vtt(seconds: float) -> str:
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            millis = int(round((seconds - int(seconds)) * 1000))
            return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"

        # Ghi file SRT
        with open(srt_path, "w", encoding="utf-8") as f_srt:
            for i, seg in enumerate(segments, 1):
                start_str = format_time_srt(seg["start"])
                end_str = format_time_srt(seg["end"])
                clean_txt = seg["text"].strip()
                f_srt.write(f"{i}\n{start_str} --> {end_str}\n{clean_txt}\n\n")

        # Ghi file VTT
        with open(vtt_path, "w", encoding="utf-8") as f_vtt:
            f_vtt.write("WEBVTT\n\n")
            for i, seg in enumerate(segments, 1):
                start_str = format_time_vtt(seg["start"])
                end_str = format_time_vtt(seg["end"])
                clean_txt = seg["text"].strip()
                f_vtt.write(f"{i}\n{start_str} --> {end_str}\n{clean_txt}\n\n")

        return srt_path, vtt_path
