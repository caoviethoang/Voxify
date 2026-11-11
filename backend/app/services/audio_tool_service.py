"""Service quản lý vòng đời và thực thi các tác vụ Audio Tools (AudioToolService)."""
from __future__ import annotations

import json
import logging
import math
import os
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio_tools.base import registry
from app.core.errors import AppError
from app.models.audio_tool import AudioToolJob
from app.models.user import User
from app.services.audio_service import AudioService
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)

STORAGE_TOOLS_DIR = Path("storage/tools")
INPUTS_DIR = STORAGE_TOOLS_DIR / "inputs"
OUTPUTS_DIR = STORAGE_TOOLS_DIR / "outputs"


class AudioToolService:
    """Service điều phối toàn bộ các công cụ âm thanh (Audio Tools Framework)."""

    def __init__(self) -> None:
        INPUTS_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def calculate_cost(cost_def: Dict[str, Any], duration_seconds: float) -> int:
        """Tính toán lượng credit cần trừ dựa trên cấu hình công cụ và độ dài file."""
        cost_type = cost_def.get("type", "free")
        if cost_type == "free":
            return 0
        if cost_type == "fixed":
            return int(cost_def.get("rate", 1))
        if cost_type == "per_minute":
            rate = int(cost_def.get("rate", 1))
            minutes = max(1, math.ceil(duration_seconds / 60.0))
            return minutes * rate
        return 0

    async def create_and_execute_job(
        self,
        db: AsyncSession,
        user: User,
        tool_id: str,
        params: Dict[str, Any],
        file_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
        source_path: Optional[str] = None,
    ) -> AudioToolJob:
        """
        Khởi tạo và thực thi một công việc xử lý âm thanh:
        1. Kiểm tra tính hợp lệ của công cụ
        2. Lưu tệp đầu vào
        3. Đo thời lượng và trừ credit tương ứng
        4. Chạy Runner của công cụ qua ffmpeg
        5. Cập nhật kết quả vào DB và dọn dẹp tệp tạm
        """
        tool = registry.get(tool_id)
        if not tool:
            raise AppError(
                code="TOOL_NOT_FOUND",
                message=f"Công cụ âm thanh '{tool_id}' không tồn tại trong hệ thống.",
                status_code=404,
            )

        job_uuid = uuid.uuid4().hex[:12]

        # 1. Lưu tệp đầu vào
        if file_bytes and filename:
            ext = Path(filename).suffix or ".mp3"
            input_file_path = str(INPUTS_DIR / f"{job_uuid}_in{ext}")
            with open(input_file_path, "wb") as f:
                f.write(file_bytes)
            input_filename = filename
        elif source_path and os.path.exists(source_path):
            ext = Path(source_path).suffix or ".mp3"
            input_file_path = str(INPUTS_DIR / f"{job_uuid}_in{ext}")
            shutil.copy2(source_path, input_file_path)
            input_filename = Path(source_path).name
        else:
            raise AppError(
                code="MISSING_INPUT_AUDIO",
                message="Vui lòng tải lên tệp âm thanh hoặc chọn tệp nguồn từ hệ thống.",
                status_code=400,
            )

        # 2. Đo thời lượng tệp đầu vào
        input_duration = AudioService.measure_duration(input_file_path)

        # 3. Tính toán và trừ credit (nếu có phí)
        cost_credits = self.calculate_cost(tool.cost, input_duration)
        if cost_credits > 0:
            if (user.credit_balance or 0) < cost_credits:
                # Xóa file vừa lưu để dọn dẹp
                if os.path.exists(input_file_path):
                    os.remove(input_file_path)
                raise AppError(
                    code="INSUFFICIENT_CREDITS",
                    message=f"Bạn cần {cost_credits} credits để sử dụng công cụ này, số dư hiện tại là {user.credit_balance or 0} credits.",
                    status_code=402,
                )

            await CreditService.reserve(
                db=db,
                user_id=user.id,
                amount=cost_credits,
                ref_id=f"tool_job_{job_uuid}",
                description=f"Sử dụng công cụ âm thanh: {tool.name_vi}",
            )

        # 4. Tạo record Job trong database
        job = AudioToolJob(
            user_id=user.id,
            tool_id=tool_id,
            status="processing",
            progress=15,
            input_path=input_file_path,
            input_filename=input_filename,
            input_duration=round(input_duration, 2),
            params=json.dumps(params, ensure_ascii=False),
            credit_used=cost_credits,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        # 5. Đường dẫn tệp đầu ra
        out_ext = ".mp3"
        if "format" in params:
            out_ext = f".{params['format'].lower()}"
        output_file_path = str(OUTPUTS_DIR / f"{job_uuid}_out_{tool_id}{out_ext}")

        # Callback cập nhật tiến độ
        async def progress_callback(pct: int) -> None:
            job.progress = pct
            job.updated_at = datetime.now(UTC)
            await db.commit()

        # 6. Chạy công cụ
        try:
            result = await tool.run(
                input_path=input_file_path,
                params=params,
                output_path=output_file_path,
                progress_cb=progress_callback,
            )

            actual_output_path = result.get("output_path", output_file_path)
            measured_out_duration = result.get("duration") or AudioService.measure_duration(actual_output_path)
            size_bytes = result.get("size_bytes") or (os.path.getsize(actual_output_path) if os.path.exists(actual_output_path) else 0)

            job.status = "done"
            job.progress = 100
            job.output_path = actual_output_path
            job.output_filename = Path(actual_output_path).name
            job.output_duration = round(measured_out_duration, 2)
            job.output_size_bytes = size_bytes
            job.error_message = None
            job.updated_at = datetime.now(UTC)
            await db.commit()
            await db.refresh(job)
            return job

        except Exception as e:
            logger.error(f"Lỗi khi thực thi AudioTool '{tool_id}': {e}", exc_info=True)
            job.status = "failed"
            job.progress = 0
            job.error_message = str(e)
            job.updated_at = datetime.now(UTC)

            # Hoàn trả credit nếu job bị lỗi hệ thống
            if cost_credits > 0:
                try:
                    await CreditService.refund(
                        db=db,
                        user_id=user.id,
                        amount=cost_credits,
                        ref_id=f"tool_job_{job_uuid}",
                        reason=f"Hoàn trả do lỗi xử lý công cụ {tool.name_vi}: {str(e)[:100]}",
                    )
                    job.credit_used = 0
                except Exception as ref_err:
                    logger.error(f"Không thể hoàn credit cho job {job.id}: {ref_err}")

            await db.commit()
            await db.refresh(job)
            raise AppError(
                code="TOOL_EXECUTION_FAILED",
                message=f"Xử lý âm thanh thất bại: {str(e)}",
                status_code=500,
            )

    @staticmethod
    async def get_job(db: AsyncSession, job_id: int, user_id: int) -> Optional[AudioToolJob]:
        """Lấy thông tin chi tiết một job theo ID của người dùng."""
        result = await db.execute(
            select(AudioToolJob).where(
                AudioToolJob.id == job_id,
                AudioToolJob.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_jobs(
        db: AsyncSession,
        user_id: int,
        tool_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Lấy danh sách các tác vụ công cụ âm thanh của người dùng."""
        query = select(AudioToolJob).where(AudioToolJob.user_id == user_id)
        if tool_id:
            query = query.where(AudioToolJob.tool_id == tool_id)

        query = query.order_by(desc(AudioToolJob.created_at)).limit(limit).offset(offset)
        result = await db.execute(query)
        jobs = list(result.scalars().all())

        from sqlalchemy import func
        count_q = select(func.count()).select_from(AudioToolJob).where(AudioToolJob.user_id == user_id)
        if tool_id:
            count_q = count_q.where(AudioToolJob.tool_id == tool_id)
        total_res = await db.execute(count_q)
        total = total_res.scalar_one()

        return {"total": total, "jobs": jobs}
