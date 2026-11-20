"""Dịch vụ lồng tiếng phụ đề (Subtitle Dubbing Service - Issue #21).

Xử lý:
- Phân tích và trích xuất kịch bản phụ đề SRT / VTT.
- Tính toán ước lượng chi phí credit theo từng giọng đọc.
- Nghe thử từng câu (Preview cue) với thuật toán co dãn tempo.
- Quản lý vòng đời tác vụ (DubbingJob) với Background Worker.
- Ghép nối thời gian thực (< 100ms sai số) qua silence padding.
- Điều chỉnh âm lượng nhạc nền thông minh (Audio Ducking).
- Đóng gói file ZIP các đoạn thoại riêng rẽ kèm file phụ đề.
"""
import asyncio
import json
import logging
import os
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models.dubbing import DubbingJob
from app.schemas.dubbing import (
    DubbingCreateJobRequest,
    DubbingParseResponse,
    SubtitleCueItem,
)
from app.services.audio_service import AudioService
from app.services.credit_service import CreditService
from app.services.storage_service import StorageService
from app.services.subtitle_parser import SubtitleParser, format_seconds_to_timestamp
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)

# Ngưỡng tăng tốc tối đa an toàn trước khi cảnh báo cho người dùng
MAX_SAFE_TEMPO = 1.35


class DubbingService:
    """Tầng nghiệp vụ lồng tiếng phụ đề khớp thời gian."""

    @staticmethod
    def parse_content(
        content: str,
        default_voice: str = "vi-VN-HoaiMyNeural",
    ) -> DubbingParseResponse:
        """Phân tích nội dung thô phụ đề SRT/VTT, trích xuất danh sách Cue và tính chi phí."""
        raw_cues = SubtitleParser.parse(content, default_voice=default_voice)
        cues: List[SubtitleCueItem] = []
        total_chars = 0
        total_credits = 0

        for c in raw_cues:
            char_count = len(c["text"])
            total_chars += char_count
            cost = CreditService.calculate_cost(char_count=char_count, voice=c["voice"])
            total_credits += cost

            cues.append(
                SubtitleCueItem(
                    index=c["index"],
                    start=c["start"],
                    end=c["end"],
                    duration=c["duration"],
                    text=c["text"],
                    voice=c["voice"],
                    original_voice_tag=c.get("original_voice_tag"),
                    char_count=char_count,
                )
            )

        return DubbingParseResponse(
            cues=cues,
            total_cues=len(cues),
            char_count=total_chars,
            estimated_credits=total_credits,
            warnings_count=0,
        )

    @classmethod
    async def adjust_audio_tempo(
        cls,
        input_file: str,
        output_file: str,
        target_duration: float,
        actual_duration: float,
    ) -> Tuple[str, float, Optional[str]]:
        """
        Tăng tốc âm thanh bằng FFmpeg atempo nếu thời lượng thực tế vượt quá thời lượng cho phép.
        Trả về: (output_file_path, applied_tempo, warning_message_if_exceed_limit)
        """
        if actual_duration <= target_duration or target_duration <= 0.1:
            shutil.copy2(input_file, output_file)
            return output_file, 1.0, None

        needed_tempo = actual_duration / target_duration
        warning: Optional[str] = None

        if needed_tempo > MAX_SAFE_TEMPO:
            applied_tempo = MAX_SAFE_TEMPO
            diff = round(actual_duration - target_duration, 2)
            warning = (
                f"Câu nói dài hơn thời lượng phụ đề {diff}s. "
                f"Đã tăng tốc tối đa {MAX_SAFE_TEMPO}x. Hãy rút bớt từ để tránh bị đè lời."
            )
        else:
            applied_tempo = round(needed_tempo, 2)

        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i", input_file,
                "-filter:a", f"atempo={applied_tempo:.3f}",
                "-vn",
                output_file,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                return output_file, applied_tempo, warning
        except Exception as e:
            logger.warning(f"Lỗi khi chạy ffmpeg atempo: {e}")

        # Fallback giữ nguyên file gốc
        shutil.copy2(input_file, output_file)
        return output_file, 1.0, warning

    @classmethod
    async def preview_cue(
        cls,
        text: str,
        voice: str,
        tts_service: TTSService,
        target_duration: Optional[float] = None,
    ) -> Tuple[bytes, float, Optional[float], Optional[str]]:
        """
        Nghe thử âm thanh của một câu phụ đề riêng lẻ.
        Trả về: (audio_bytes, actual_duration, adjusted_tempo, warning)
        """
        raw_audio = await tts_service.synthesize(text=text, voice=voice, preview=False)

        with tempfile.TemporaryDirectory() as tmp_dir:
            raw_path = os.path.join(tmp_dir, "raw_preview.mp3")
            with open(raw_path, "wb") as f:
                f.write(raw_audio)

            actual_duration = AudioService.measure_duration(raw_path)
            applied_tempo: Optional[float] = None
            warning: Optional[str] = None

            if target_duration and target_duration > 0.1 and actual_duration > target_duration:
                adjusted_path = os.path.join(tmp_dir, "adjusted_preview.mp3")
                _, applied_tempo, warning = await cls.adjust_audio_tempo(
                    raw_path, adjusted_path, target_duration, actual_duration
                )
                if os.path.exists(adjusted_path) and os.path.getsize(adjusted_path) > 0:
                    with open(adjusted_path, "rb") as af:
                        final_bytes = af.read()
                    return final_bytes, actual_duration, applied_tempo, warning

            return raw_audio, actual_duration, applied_tempo, warning

    @classmethod
    async def apply_audio_ducking(
        cls,
        speech_path: str,
        bg_music_path: str,
        output_path: str,
        ducking_volume: float = 0.2,
    ) -> str:
        """
        Trộn giọng đọc với nhạc nền, tự động hạ âm lượng nhạc nền khi có tiếng nói (Ducking).
        """
        if not os.path.exists(bg_music_path) or os.path.getsize(bg_music_path) == 0:
            shutil.copy2(speech_path, output_path)
            return output_path

        safe_duck = max(0.05, min(ducking_volume, 0.9))
        try:
            # Dùng sidechaincompress filter của FFmpeg:
            # Background track bị nén/hạ âm khi track lời thoại (speech) phát ra âm lượng
            cmd = [
                "ffmpeg",
                "-y",
                "-i", speech_path,
                "-stream_loop", "-1",
                "-i", bg_music_path,
                "-filter_complex",
                f"[1:a]volume={safe_duck}[bg];[bg][0:a]sidechaincompress=threshold=0.1:ratio=4:attack=50:release=350[ducked];[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=2",
                "-c:a", "libmp3lame",
                "-b:a", "128k",
                output_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
        except Exception as e:
            logger.warning(f"Lỗi khi thực hiện audio ducking qua ffmpeg: {e}")

        # Fallback copy nguyên file lời thoại
        shutil.copy2(speech_path, output_path)
        return output_path

    @classmethod
    async def create_dubbing_job(
        cls,
        db: AsyncSession,
        user_id: int,
        req: DubbingCreateJobRequest,
    ) -> DubbingJob:
        """
        Khởi tạo tác vụ lồng tiếng:
        - Tính toán và trừ trước credit (Reserve pattern).
        - Lưu cấu hình kịch bản các cue vào DB.
        """
        if not req.cues:
            raise AppError(code="EMPTY_CUES", message="Danh sách phụ đề trống.", status_code=400)

        total_chars = sum(len(c.text) for c in req.cues)
        total_credits = sum(
            CreditService.calculate_cost(char_count=len(c.text), voice=c.voice)
            for c in req.cues
        )

        # Kiểm tra và trừ credit
        await CreditService.reserve(
            db=db,
            user_id=user_id,
            amount=total_credits,
            description=f"Lồng tiếng phụ đề: {req.title} ({len(req.cues)} câu)",
        )

        cues_dicts = [c.model_dump() for c in req.cues]

        job = DubbingJob(
            user_id=user_id,
            title=req.title,
            subtitle_format=req.subtitle_format,
            target_format=req.target_format,
            default_voice=req.default_voice,
            status="queued",
            progress=0,
            total_cues=len(req.cues),
            char_count=total_chars,
            credit_used=total_credits,
            cues_data=json.dumps(cues_dicts, ensure_ascii=False),
            background_audio_path=req.background_audio_path,
            ducking_volume=req.ducking_volume,
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @classmethod
    async def execute_dubbing_job(
        cls,
        job_id: int,
        session_factory: Callable[[], AsyncSession],
        tts_service: TTSService,
        storage_service: StorageService,
    ) -> None:
        """
        Hàm xử lý ngầm (Background Task) chạy quá trình lồng tiếng toàn diện:
        1. Đọc kịch bản cues.
        2. Tổng hợp TTS cho từng câu và co/dãn tempo để khớp khung thời gian.
        3. Ghép nối trục thời gian chèn khoảng lặng để sai số < 100ms.
        4. Áp dụng Audio Ducking nếu có nhạc nền.
        5. Đóng gói ZIP từng file câu kèm phụ đề.
        6. Lưu trữ file kết quả và cập nhật hoàn tất.
        """
        async with session_factory() as db:
            job = await db.get(DubbingJob, job_id)
            if not job or job.status in ("done", "failed"):
                return

            job.status = "processing"
            job.progress = 5
            await db.commit()

        user_id = job.user_id
        credit_used = job.credit_used

        try:
            cues_list: List[Dict[str, Any]] = json.loads(job.cues_data or "[]")
            if not cues_list:
                raise ValueError("Không tìm thấy dữ liệu kịch bản các đoạn phụ đề.")

            with tempfile.TemporaryDirectory() as work_dir:
                cues_dir = os.path.join(work_dir, "cues")
                os.makedirs(cues_dir, exist_ok=True)

                timeline_segments: List[str] = []
                current_timeline_sec = 0.0
                total_cues_count = len(cues_list)

                for idx, cue in enumerate(cues_list):
                    text = cue.get("text", "")
                    voice = cue.get("voice", job.default_voice)
                    start_sec = float(cue.get("start", 0.0))
                    duration_sec = float(cue.get("duration", 1.0))

                    # 1. Tổng hợp TTS cho câu này
                    audio_bytes = await tts_service.synthesize(text=text, voice=voice, preview=False)
                    raw_cue_path = os.path.join(cues_dir, f"raw_{idx+1:03d}.mp3")
                    with open(raw_cue_path, "wb") as f:
                        f.write(audio_bytes)

                    actual_dur = AudioService.measure_duration(raw_cue_path)
                    cue["actual_duration"] = actual_dur

                    # 2. Đồng bộ thời lượng nếu thoại dài hơn mốc phụ đề
                    final_cue_path = os.path.join(cues_dir, f"cue_{idx+1:03d}.mp3")
                    _, applied_tempo, warning = await cls.adjust_audio_tempo(
                        raw_cue_path, final_cue_path, duration_sec, actual_dur
                    )
                    cue["adjusted_tempo"] = applied_tempo
                    cue["warning"] = warning

                    # 3. Chèn khoảng lặng (Silence) vào timeline để khớp mốc thời gian tuyệt đối
                    gap_to_start = start_sec - current_timeline_sec
                    if gap_to_start > 0.05:
                        silence_file = os.path.join(work_dir, f"silence_{idx+1:03d}.mp3")
                        await AudioService.generate_silence(gap_to_start, silence_file)
                        timeline_segments.append(silence_file)
                        current_timeline_sec += gap_to_start

                    # Nạp câu thoại vào timeline
                    timeline_segments.append(final_cue_path)
                    cue_dur = AudioService.measure_duration(final_cue_path)
                    current_timeline_sec += cue_dur

                    # Cập nhật tiến độ định kỳ
                    progress_val = min(80, int(10 + (idx + 1) / total_cues_count * 70))
                    async with session_factory() as db:
                        j = await db.get(DubbingJob, job_id)
                        if j:
                            j.progress = progress_val
                            await db.commit()

                # 4. Ghép toàn bộ timeline thành Master Audio
                master_speech_raw = os.path.join(work_dir, f"master_speech.{job.target_format}")
                await AudioService.concat_audio_files(
                    timeline_segments, master_speech_raw, target_format=job.target_format
                )

                # 5. Xử lý hòa âm & Audio Ducking nếu người dùng chọn nhạc nền
                final_master_path = master_speech_raw
                if job.background_audio_path and os.path.exists(job.background_audio_path):
                    ducked_out = os.path.join(work_dir, f"master_ducked.{job.target_format}")
                    final_master_path = await cls.apply_audio_ducking(
                        speech_path=master_speech_raw,
                        bg_music_path=job.background_audio_path,
                        output_path=ducked_out,
                        ducking_volume=job.ducking_volume,
                    )

                # 6. Đóng gói ZIP bao gồm các file câu thoại và phụ đề
                zip_filename = f"dubbing_cues_job_{job_id}.zip"
                zip_local_path = os.path.join(work_dir, zip_filename)
                with zipfile.ZipFile(zip_local_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    # Thêm từng cue mp3
                    for idx in range(total_cues_count):
                        cue_p = os.path.join(cues_dir, f"cue_{idx+1:03d}.mp3")
                        if os.path.exists(cue_p):
                            zf.write(cue_p, arcname=f"cues/cue_{idx+1:03d}.mp3")

                    # Tạo file phụ đề SRT tương ứng
                    srt_temp = os.path.join(work_dir, "subtitles.srt")
                    with open(srt_temp, "w", encoding="utf-8") as srt_f:
                        for idx, c in enumerate(cues_list, 1):
                            s_ts = format_seconds_to_timestamp(float(c.get("start", 0.0)))
                            e_ts = format_seconds_to_timestamp(float(c.get("end", 0.0)))
                            srt_f.write(f"{idx}\n{s_ts} --> {e_ts}\n{c.get('text', '')}\n\n")
                    zf.write(srt_temp, arcname="subtitles.srt")

                # 7. Lưu master audio và zip vào hệ thống Storage
                with open(final_master_path, "rb") as mf:
                    master_bytes = mf.read()
                audio_path, _ = await storage_service.save_audio(
                    master_bytes, voice="dubbing_master", is_preview=False
                )

                with open(zip_local_path, "rb") as zf_read:
                    zip_bytes = zf_read.read()
                # Lưu file zip thông qua storage backend
                zip_save_path = await storage_service.backend.save(zip_bytes, zip_filename)

                total_duration = AudioService.measure_duration(final_master_path)

                # 8. Cập nhật hoàn tất tác vụ trong DB
                async with session_factory() as db:
                    completed_job = await db.get(DubbingJob, job_id)
                    if completed_job:
                        completed_job.status = "done"
                        completed_job.progress = 100
                        completed_job.output_audio_path = audio_path
                        completed_job.output_zip_path = zip_save_path
                        completed_job.duration = round(total_duration, 2)
                        completed_job.cues_data = json.dumps(cues_list, ensure_ascii=False)
                        completed_job.updated_at = datetime.now(UTC)
                        await db.commit()

        except Exception as err:
            logger.error(f"Lỗi trong quá trình xử lý DubbingJob #{job_id}: {err}", exc_info=True)
            async with session_factory() as db:
                failed_job = await db.get(DubbingJob, job_id)
                if failed_job:
                    failed_job.status = "failed"
                    failed_job.error_message = str(err)
                    await db.commit()

                # Hoàn trả credit nếu job bị lỗi
                if credit_used > 0:
                    try:
                        await CreditService.refund(
                            db=db,
                            user_id=user_id,
                            amount=credit_used,
                            ref_id=f"dubbing_job_{job_id}",
                            reason=f"Hoàn credit do tác vụ lồng tiếng #{job_id} thất bại",
                        )
                    except Exception as refund_err:
                        logger.error(f"Không thể hoàn credit cho job #{job_id}: {refund_err}")

    @classmethod
    async def list_user_jobs(
        cls,
        db: AsyncSession,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> List[DubbingJob]:
        """Lấy danh sách các tác vụ lồng tiếng của người dùng."""
        stmt = (
            select(DubbingJob)
            .where(DubbingJob.user_id == user_id)
            .order_by(desc(DubbingJob.created_at))
            .offset(offset)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def get_job_by_id(
        cls,
        db: AsyncSession,
        job_id: int,
        user_id: int,
    ) -> Optional[DubbingJob]:
        """Lấy chi tiết tác vụ theo ID và kiểm tra quyền sở hữu."""
        job = await db.get(DubbingJob, job_id)
        if not job or job.user_id != user_id:
            return None
        return job

    @classmethod
    async def delete_job(
        cls,
        db: AsyncSession,
        job_id: int,
        user_id: int,
        storage_service: StorageService,
    ) -> bool:
        """Xóa tác vụ và dọn dẹp các tệp âm thanh liên quan."""
        job = await cls.get_job_by_id(db, job_id, user_id)
        if not job:
            return False

        if job.output_audio_path:
            try:
                await storage_service.delete(job.output_audio_path)
            except Exception:
                pass

        if job.output_zip_path:
            try:
                await storage_service.delete(job.output_zip_path)
            except Exception:
                pass

        await db.delete(job)
        await db.commit()
        return True
