"""Service quản lý vòng đời và xử lý Job Text to Speech bất đồng bộ."""
import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.errors import AppError
from app.db import AsyncSessionLocal
from app.models.generation import Generation
from app.models.user import User
from app.services.audio_service import AudioService
from app.services.credit_service import CreditService, InsufficientCreditsError
from app.services.dictionary_service import DictionaryService
from app.services.storage_service import StorageService
from app.services.tts_script_parser import TTSScriptParser
from app.services.tts_service import TTSService

logger = logging.getLogger(__name__)


# Ngưỡng tách đoạn lớn (~2.500 ký tự) theo yêu cầu Prompt 5
_MACRO_CHUNK_SIZE = 2500
_SENTENCE_SPLIT_REGEX = re.compile(r"(?<=[.!?…\n])\s+")


class TTSJobService:
    def __init__(
        self,
        tts_service: Optional[TTSService] = None,
        storage_service: Optional[StorageService] = None,
    ):
        if tts_service is None:
            from app.dependencies import get_tts_service
            self.tts = get_tts_service()
        else:
            self.tts = tts_service
        self.storage = storage_service or StorageService()

    async def create_job(
        self,
        db: AsyncSession,
        user: Optional[User],
        text: str,
        voice: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
        output_format: str = "mp3",
        apply_dict: bool = True,
    ) -> Generation:
        """
        Tạo job TTS mới trong hàng đợi, trừ trước credit (reserve) và kích hoạt worker ngầm.
        """
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Văn bản không được để trống.")

        get_settings()
        # Tính toán chi phí credit
        char_count = len(clean_text)
        cost = CreditService.calculate_cost(char_count, provider="edge", voice=voice) if user else 0

        # Trừ trước credit (reserve)
        tx = None
        if user and cost > 0:
            try:
                tx = await CreditService.reserve(
                    db=db,
                    user_id=user.id,
                    amount=cost,
                    description=f"Job TTS ({char_count} ký tự - {voice})",
                )
            except InsufficientCreditsError as e:
                raise AppError(
                    code="INSUFFICIENT_CREDITS",
                    message=f"Số dư credit không đủ ({e.current}/{e.required}). Vui lòng nạp thêm credit.",
                    status_code=402,
                )

        # Tạo bản ghi Generation
        target_format = "wav" if output_format.lower() == "wav" else "mp3"
        generation = Generation(
            user_id=user.id if user else None,
            text=clean_text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            volume=volume,
            char_count=char_count,
            format=target_format,
            duration=0.0,
            status="queued",
            progress=0,
            credit_used=cost,
            is_preview=False,
            provider="edge",
        )
        db.add(generation)
        await db.commit()
        await db.refresh(generation)

        if tx:
            tx.ref_id = f"gen_{generation.id}"
            await db.commit()

        logger.info(f"Đã tạo Job TTS #{generation.id} (user={user.id if user else 'guest'}, chars={char_count}, cost={cost})")

        # Kích hoạt worker bất đồng bộ
        asyncio.create_task(self._execute_job_in_background(generation.id, apply_dict))

        return generation

    async def get_job(self, db: AsyncSession, job_id: int, user_id: Optional[int] = None) -> Optional[Generation]:
        """Lấy thông tin và trạng thái tiến độ của Job."""
        stmt = select(Generation).where(Generation.id == job_id)
        if user_id:
            stmt = stmt.where(Generation.user_id == user_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_recent_jobs(self, db: AsyncSession, user_id: int, limit: int = 15) -> List[Generation]:
        """Liệt kê danh sách job gần đây của người dùng."""
        stmt = (
            select(Generation)
            .where(Generation.user_id == user_id)
            .order_by(Generation.created_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    # -------------------------------------------------------------------------
    # Worker xử lý Job nền
    # -------------------------------------------------------------------------

    async def _execute_job_in_background(self, job_id: int, apply_dict: bool) -> None:
        """Hàm thực thi ngầm cho từng job trong worker."""
        async with AsyncSessionLocal() as db:
            job = await db.get(Generation, job_id)
            if not job:
                logger.error(f"Worker: Không tìm thấy Job #{job_id}")
                return

            try:
                # 1. Cập nhật tiến độ bắt đầu: 5%
                job.status = "processing"
                job.progress = 5
                await db.commit()

                # 2. Áp dụng từ điển phát âm cá nhân nếu được bật
                processed_text = job.text
                if apply_dict and job.user_id:
                    processed_text = await DictionaryService.apply_dictionary(db, job.user_id, processed_text)

                # 3. Phân tích kịch bản đa giọng và ngắt nghỉ
                blocks = TTSScriptParser.parse_script(processed_text, default_voice=job.voice)
                if not blocks:
                    raise ValueError("Không có nội dung giọng nói hợp lệ để tổng hợp.")

                job.progress = 10
                await db.commit()

                # 4. Tách các block thành micro/macro tasks và tổng hợp audio
                temp_dir = Path("storage/temp") / f"job_{job_id}_{int(datetime.now().timestamp())}"
                temp_dir.mkdir(parents=True, exist_ok=True)

                segment_audio_files: List[str] = []
                subtitles_data: List[Dict[str, Any]] = []
                current_timeline_seconds = 0.0

                total_blocks = len(blocks)
                for block_idx, block in enumerate(blocks):
                    if block["type"] == "pause":
                        pause_sec = block["duration"]
                        silence_file = str(temp_dir / f"silence_{block_idx}.mp3")
                        await AudioService.generate_silence(pause_sec, silence_file)
                        segment_audio_files.append(silence_file)
                        current_timeline_seconds += pause_sec

                    elif block["type"] == "speech":
                        speech_text = block["text"]
                        speech_voice = block["voice"]

                        # Tách theo câu nếu văn bản dài hơn ~2500 ký tự
                        macro_chunks = self._split_macro_chunks(speech_text, max_chars=_MACRO_CHUNK_SIZE)

                        for chunk_sub_idx, chunk_text in enumerate(macro_chunks):
                            # Gọi TTS Service tổng hợp
                            audio_bytes = await self.tts.synthesize(
                                text=chunk_text,
                                voice=speech_voice,
                                rate=job.rate,
                                pitch=job.pitch,
                                volume=job.volume,
                                preview=False,
                            )

                            chunk_file = str(temp_dir / f"chunk_{block_idx}_{chunk_sub_idx}.mp3")
                            with open(chunk_file, "wb") as f_chunk:
                                f_chunk.write(audio_bytes)

                            # Đo thời lượng đoạn vừa tạo để làm mốc phụ đề
                            chunk_duration = AudioService.measure_duration(chunk_file)
                            if chunk_duration <= 0:
                                # Ước lượng ~12 ký tự/giây cho tiếng Việt
                                chunk_duration = max(0.5, len(chunk_text) / 12.0)

                            subtitles_data.append({
                                "text": chunk_text,
                                "start": current_timeline_seconds,
                                "end": current_timeline_seconds + chunk_duration,
                            })
                            current_timeline_seconds += chunk_duration
                            segment_audio_files.append(chunk_file)

                    # Cập nhật tiến độ mượt mà từ 15% đến 85%
                    progress_val = int(15 + (block_idx + 1) / total_blocks * 70)
                    job.progress = min(progress_val, 85)
                    await db.commit()

                # 5. Ghép nối các đoạn âm thanh bằng ffmpeg
                job.progress = 90
                await db.commit()

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_ext = job.format.lower()
                final_local_path = str(Path("storage/audio") / f"speech_job_{job_id}_{timestamp}.{target_ext}")
                Path("storage/audio").mkdir(parents=True, exist_ok=True)

                output_path, final_duration, final_size = await AudioService.concat_audio_files(
                    file_paths=segment_audio_files,
                    output_path=final_local_path,
                    target_format=target_ext,
                )

                # 6. Tạo file phụ đề SRT & WebVTT
                srt_local_path = str(Path("storage/audio") / f"subtitles_job_{job_id}_{timestamp}.srt")
                vtt_local_path = str(Path("storage/audio") / f"subtitles_job_{job_id}_{timestamp}.vtt")
                AudioService.generate_subtitles(subtitles_data, srt_local_path, vtt_local_path)

                # 7. Dọn dẹp thư mục tạm
                import shutil
                shutil.rmtree(temp_dir, ignore_errors=True)

                # 8. Hoàn tất job thành công
                job.status = "done"
                job.progress = 100
                job.file_path = output_path
                job.file_size = final_size
                job.duration = final_duration
                job.srt_path = srt_local_path
                job.vtt_path = vtt_local_path
                job.error_message = None
                await db.commit()

                logger.info(
                    f"Job TTS #{job_id} hoàn tất thành công! ({final_duration:.1f}s, {final_size} bytes, định dạng {target_ext})"
                )

            except Exception as exc:
                logger.error(f"Job TTS #{job_id} thất bại: {exc}", exc_info=True)
                # TỰ ĐỘNG HOÀN TRẢ CREDIT KHI JOB LỖI
                if job.user_id and job.credit_used > 0:
                    try:
                        await CreditService.refund(
                            db=db,
                            user_id=job.user_id,
                            amount=job.credit_used,
                            ref_id=f"gen_{job_id}",
                            reason=f"Hoàn trả credit cho job #{job_id} bị lỗi: {str(exc)[:100]}",
                        )
                        logger.warning(f"Đã hoàn trả {job.credit_used} credit cho User #{job.user_id} sau sự cố job #{job_id}")
                    except Exception as refund_err:
                        logger.error(f"Lỗi khi hoàn credit cho job #{job_id}: {refund_err}")

                job.status = "failed"
                job.progress = 0
                job.error_message = f"Lỗi xử lý: {str(exc)}"
                await db.commit()

    @staticmethod
    def _split_macro_chunks(text: str, max_chars: int = _MACRO_CHUNK_SIZE) -> List[str]:
        """Tách các đoạn lớn theo câu nếu text vượt quá max_chars."""
        if len(text) <= max_chars:
            return [text]

        sentences = _SENTENCE_SPLIT_REGEX.split(text)
        chunks: List[str] = []
        buf = ""

        for s in sentences:
            s_clean = s.strip()
            if not s_clean:
                continue

            cand = f"{buf} {s_clean}".strip() if buf else s_clean
            if len(cand) <= max_chars:
                buf = cand
            else:
                if buf:
                    chunks.append(buf)
                if len(s_clean) > max_chars:
                    # Nếu 1 câu đơn lẻ vẫn dài hơn max_chars, cắt theo khoảng trắng
                    words = s_clean.split(" ")
                    wbuf = ""
                    for w in words:
                        wcand = f"{wbuf} {w}".strip() if wbuf else w
                        if len(wcand) <= max_chars:
                            wbuf = wcand
                        else:
                            if wbuf:
                                chunks.append(wbuf)
                            wbuf = w
                    if wbuf:
                        chunks.append(wbuf)
                    buf = ""
                else:
                    buf = s_clean

        if buf:
            chunks.append(buf)

        return chunks
