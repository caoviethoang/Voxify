"""Service tiện ích xử lý âm thanh: đo thời lượng, ghép nối ffmpeg, chuyển định dạng và tạo phụ đề SRT/VTT."""
import asyncio
import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

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
    async def validate_voice_sample(
        cls,
        file_path: str,
        min_duration: float = 5.0,
        max_duration: float = 180.0,
    ) -> Dict[str, Any]:
        """
        Kiểm tra chất lượng mẫu âm thanh cho Clone giọng nói (Prompt 10 / Issue #12):
        - Độ dài mẫu: 5.0s – 180.0s (tối đa 3 phút)
        - Mức độ âm lượng và độ ồn (volumedetect qua ffmpeg)
        - Điểm chất lượng mẫu (1.0 – 5.0 sao)
        """
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return {
                "valid": False,
                "duration": 0.0,
                "quality_score": 0.0,
                "error": "Tệp âm thanh trống hoặc không tồn tại.",
            }

        # 1. Đo thời lượng bằng ffprobe
        duration = cls.measure_duration(file_path)
        if duration < min_duration:
            return {
                "valid": False,
                "duration": round(duration, 2),
                "quality_score": 1.0,
                "error": f"Mẫu âm thanh quá ngắn ({duration:.1f}s). Yêu cầu tối thiểu {min_duration:.0f} giây để mô hình học âm sắc.",
            }
        if duration > max_duration:
            max_mins = int(max_duration // 60)
            return {
                "valid": False,
                "duration": round(duration, 2),
                "quality_score": 1.0,
                "error": f"Mẫu âm thanh quá dài ({duration:.1f}s). Yêu cầu tối đa {max_mins} phút ({max_duration:.0f} giây).",
            }

        # 2. Phân tích mức âm lượng / độ nhiễu bằng ffmpeg volumedetect
        mean_volume = -25.0
        max_volume = -3.0
        try:
            cmd = [
                "ffmpeg",
                "-i", file_path,
                "-af", "volumedetect",
                "-vn", "-sn", "-dn",
                "-f", "null",
                "/dev/null",
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
            err_text = stderr.decode("utf-8", errors="ignore")

            for line in err_text.splitlines():
                if "mean_volume:" in line:
                    parts = line.split("mean_volume:")[1].split("dB")[0].strip()
                    mean_volume = float(parts)
                elif "max_volume:" in line:
                    parts = line.split("max_volume:")[1].split("dB")[0].strip()
                    max_volume = float(parts)
        except Exception as e:
            logger.warning(f"Không thể chạy ffmpeg volumedetect cho file {file_path}: {e}")

        # Kiểm tra âm thanh câm / quá nhỏ
        if mean_volume < -50.0:
            return {
                "valid": False,
                "duration": round(duration, 2),
                "mean_volume_db": mean_volume,
                "max_volume_db": max_volume,
                "quality_score": 1.0,
                "error": "Mẫu âm thanh quá nhỏ hoặc gần như im lặng (dưới -50 dB). Vui lòng nói to và rõ hơn.",
            }

        # 3. Tính điểm chất lượng (1.0 - 5.0)
        score = 4.0
        # Thời lượng lý tưởng: 10s - 25s
        if 10.0 <= duration <= 25.0:
            score += 0.5
        elif duration < 7.0:
            score -= 0.5

        # Âm lượng lý tưởng: mean_volume giữa -28 dB và -16 dB
        if -28.0 <= mean_volume <= -16.0:
            score += 0.5
        elif mean_volume < -38.0:
            score -= 0.5

        # Tránh clipping quá lớn
        if max_volume >= 0.0:
            score -= 0.3

        quality_score = max(1.0, min(5.0, round(score, 1)))

        return {
            "valid": True,
            "duration": round(duration, 2),
            "mean_volume_db": round(mean_volume, 1),
            "max_volume_db": round(max_volume, 1),
            "quality_score": quality_score,
            "error": None,
        }

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

        except (FileNotFoundError, RuntimeError) as e:
            logger.warning(f"ffmpeg không khả dụng hoặc lỗi ({e}), chuyển sang ghép nối file trực tiếp.")
            with open(output_path, "wb") as out_f:
                for p in valid_files:
                    with open(p, "rb") as in_f:
                        out_f.write(in_f.read())
            duration = cls.measure_duration(output_path)
            size = os.path.getsize(output_path)
            return output_path, duration, size

        finally:
            if os.path.exists(list_file_path):
                os.remove(list_file_path)

    @classmethod
    async def generate_silence(cls, duration_seconds: float, output_path: str) -> str:
        """Tạo đoạn âm thanh khoảng lặng (silence) qua ffmpeg anullsrc (hoặc fallback nhị phân)."""
        duration = max(0.1, min(duration_seconds, 30.0))
        try:
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
            if proc.returncode == 0:
                return output_path
        except Exception:
            pass

        # Fallback tạo khung mp3 im lặng trực tiếp
        num_frames = max(1, int(duration * 25))
        silent_frame = b"\xff\xfb\x90\x64" + (b"\x00" * 414)
        with open(output_path, "wb") as f:
            f.write(silent_frame * num_frames)
        return output_path

    @staticmethod
    def generate_estimated_subtitles(
        text: str,
        total_duration: float,
        srt_path: str,
        vtt_path: str,
    ) -> Tuple[str, str]:
        """
        Ước lượng mốc thời gian phụ đề từ văn bản và tổng thời lượng âm thanh,
        chia theo câu/mệnh đề để tạo file SRT và WebVTT.
        """
        import re
        clean_text = text.strip()
        if not clean_text:
            clean_text = "..."

        # Tách theo câu (. ! ? … \n)
        raw_sentences = re.split(r'(?<=[.!?…\n])\s+', clean_text)
        sentences = [s.strip() for s in raw_sentences if s.strip()]
        if not sentences:
            sentences = [clean_text]

        total_chars = sum(len(s) for s in sentences) or 1
        safe_duration = max(0.5, total_duration)

        segments: List[Dict[str, Any]] = []
        current_time = 0.0

        for idx, s in enumerate(sentences):
            # Tỷ lệ thời gian theo số ký tự
            proportion = len(s) / total_chars
            seg_dur = max(0.3, proportion * safe_duration)
            end_time = current_time + seg_dur
            if idx == len(sentences) - 1:
                end_time = max(end_time, safe_duration)

            segments.append({
                "text": s,
                "start": current_time,
                "end": end_time,
            })
            current_time = end_time

        return AudioService.generate_subtitles(segments, srt_path, vtt_path)

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
