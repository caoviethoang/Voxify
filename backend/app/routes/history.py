"""Route /api/history — lịch sử xử lý TTS của người dùng."""
import logging
import math
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies import get_current_active_user
from app.models.generation import Generation
from app.models.user import User
from app.schemas.history import (
    BulkDeleteRequest,
    HistoryItemResponse,
    HistoryListResponse,
    UpdateHistoryTitleRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["History"])


def _build_history_item(gen: Generation) -> HistoryItemResponse:
    """Chuyển đổi Generation model sang HistoryItemResponse kèm URL tải file."""
    has_audio = gen.status == "done" and bool(gen.file_path and os.path.exists(gen.file_path))
    has_srt = gen.status == "done" and bool(gen.srt_path and os.path.exists(gen.srt_path))
    has_vtt = gen.status == "done" and bool(gen.vtt_path and os.path.exists(gen.vtt_path))

    # Ưu tiên tiêu đề tùy chỉnh, nếu không có thì lấy 60 ký tự đầu của text
    title = gen.title if gen.title else (gen.text or "")[:60].strip()

    return HistoryItemResponse(
        id=gen.id,
        title=title,
        text=gen.text or "",
        voice=gen.voice or "",
        rate=gen.rate or "+0%",
        pitch=gen.pitch or "+0Hz",
        volume=gen.volume or "+0%",
        format=gen.format or "mp3",
        duration=round(gen.duration or 0.0, 2),
        char_count=gen.char_count or 0,
        credit_used=gen.credit_used or 0,
        status=gen.status or "done",
        progress=gen.progress or 100,
        error_message=gen.error_message,
        audio_url=f"/api/tts/jobs/{gen.id}/audio" if has_audio else None,
        srt_url=f"/api/tts/jobs/{gen.id}/subtitles?format=srt" if has_srt else None,
        vtt_url=f"/api/tts/jobs/{gen.id}/subtitles?format=vtt" if has_vtt else None,
        is_preview=gen.is_preview,
        created_at=gen.created_at,
        updated_at=gen.updated_at,
    )


def _delete_generation_files(gen: Generation) -> None:
    """Xóa các file vật lý liên kết với Generation (audio, SRT, VTT)."""
    for file_attr in [gen.file_path, gen.srt_path, gen.vtt_path]:
        if file_attr:
            Path(file_attr).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# GET /api/history
# ---------------------------------------------------------------------------

@router.get("", response_model=HistoryListResponse, summary="Lấy danh sách lịch sử xử lý")
async def list_history(
    page: int = Query(default=1, ge=1, description="Số trang"),
    limit: int = Query(default=20, ge=1, le=100, description="Số bản ghi mỗi trang"),
    status: Optional[str] = Query(default=None, description="Lọc theo trạng thái"),
    search: Optional[str] = Query(default=None, description="Tìm kiếm trong nội dung văn bản"),
    date_from: Optional[str] = Query(default=None, description="Lọc từ ngày (ISO format)"),
    date_to: Optional[str] = Query(default=None, description="Lọc đến ngày (ISO format)"),
    format: Optional[str] = Query(default=None, description="Lọc theo định dạng audio"),
    is_preview: Optional[bool] = Query(default=None, description="Lọc theo is_preview"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Lấy danh sách lịch sử xử lý TTS với phân trang và bộ lọc."""
    # Điều kiện cơ bản: chỉ lấy bản ghi của user hiện tại
    base_conditions = [Generation.user_id == current_user.id]

    # Mặc định chỉ lấy bản ghi không phải preview (trừ khi lọc is_preview=True)
    if is_preview is not None:
        base_conditions.append(Generation.is_preview == is_preview)
    else:
        base_conditions.append(Generation.is_preview == False)  # noqa: E712

    # Lọc theo trạng thái
    if status:
        base_conditions.append(Generation.status == status)

    # Tìm kiếm theo nội dung văn bản (case-insensitive)
    if search:
        base_conditions.append(Generation.text.ilike(f"%{search}%"))

    # Lọc theo khoảng ngày
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from).replace(tzinfo=UTC)
            base_conditions.append(Generation.created_at >= dt_from)
        except ValueError:
            logger.warning(f"date_from không hợp lệ: {date_from}")

    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to).replace(tzinfo=UTC)
            base_conditions.append(Generation.created_at <= dt_to)
        except ValueError:
            logger.warning(f"date_to không hợp lệ: {date_to}")

    # Lọc theo định dạng
    if format:
        base_conditions.append(Generation.format == format)

    # Đếm tổng số bản ghi thỏa mãn điều kiện
    count_stmt = select(func.count()).select_from(Generation).where(*base_conditions)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    # Truy vấn dữ liệu với phân trang, sắp xếp mới nhất trước
    offset = (page - 1) * limit
    data_stmt = (
        select(Generation)
        .where(*base_conditions)
        .order_by(Generation.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(data_stmt)
    generations = result.scalars().all()

    # Tính số trang
    pages = math.ceil(total / limit) if total > 0 else 1

    items = [_build_history_item(gen) for gen in generations]

    return HistoryListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# DELETE /api/history/bulk
# ---------------------------------------------------------------------------

@router.delete("/bulk", summary="Xóa hàng loạt bản ghi lịch sử")
async def bulk_delete_history(
    body: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Xóa nhiều bản ghi lịch sử cùng lúc, bao gồm cả file vật lý."""
    deleted_count = 0

    for gen_id in body.ids:
        stmt = select(Generation).where(
            Generation.id == gen_id,
            Generation.user_id == current_user.id,
        )
        result = await db.execute(stmt)
        gen = result.scalar_one_or_none()

        if gen:
            # Xóa file vật lý trước khi xóa bản ghi
            _delete_generation_files(gen)
            await db.delete(gen)
            deleted_count += 1

    await db.commit()
    logger.info(f"User {current_user.id} đã xóa {deleted_count} bản ghi lịch sử.")
    return {"deleted": deleted_count}


# ---------------------------------------------------------------------------
# DELETE /api/history/{id}
# ---------------------------------------------------------------------------

@router.delete("/{gen_id}", summary="Xóa một bản ghi lịch sử")
async def delete_history_item(
    gen_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Xóa một bản ghi lịch sử theo ID, bao gồm cả file vật lý."""
    stmt = select(Generation).where(Generation.id == gen_id)
    result = await db.execute(stmt)
    gen = result.scalar_one_or_none()

    if not gen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi.")

    # Kiểm tra quyền sở hữu
    if gen.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xóa bản ghi này.",
        )

    # Xóa file vật lý
    _delete_generation_files(gen)

    # Xóa bản ghi khỏi DB
    await db.delete(gen)
    await db.commit()

    logger.info(f"User {current_user.id} đã xóa bản ghi lịch sử {gen_id}.")
    return {"deleted": 1}


# ---------------------------------------------------------------------------
# PATCH /api/history/{id}
# ---------------------------------------------------------------------------

@router.patch("/{gen_id}", response_model=HistoryItemResponse, summary="Cập nhật tiêu đề bản ghi")
async def update_history_title(
    gen_id: int,
    body: UpdateHistoryTitleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Cập nhật tiêu đề tùy chỉnh cho bản ghi lịch sử."""
    stmt = select(Generation).where(Generation.id == gen_id)
    result = await db.execute(stmt)
    gen = result.scalar_one_or_none()

    if not gen:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy bản ghi.")

    # Kiểm tra quyền sở hữu
    if gen.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền chỉnh sửa bản ghi này.",
        )

    # Lưu tiêu đề mới (tối đa 200 ký tự)
    gen.title = body.title[:200].strip()
    await db.commit()
    await db.refresh(gen)

    logger.info(f"User {current_user.id} đã cập nhật tiêu đề bản ghi {gen_id}.")
    return _build_history_item(gen)


# ---------------------------------------------------------------------------
# Hàm dọn dẹp dữ liệu cũ (gọi từ main.py khi khởi động)
# ---------------------------------------------------------------------------

async def cleanup_old_generations(db: AsyncSession, retention_days: int = 7) -> None:
    """
    Xóa các Generation cũ hơn retention_days ngày:
    - Chỉ xóa bản ghi is_preview=True
    - Áp dụng cho tất cả người dùng (có thể lọc theo plan sau)
    """
    cutoff_dt = datetime.now(UTC) - timedelta(days=retention_days)

    stmt = select(Generation).where(
        Generation.is_preview == True,  # noqa: E712
        Generation.created_at < cutoff_dt,
    )
    result = await db.execute(stmt)
    old_generations = result.scalars().all()

    deleted_count = 0
    for gen in old_generations:
        _delete_generation_files(gen)
        await db.delete(gen)
        deleted_count += 1

    if deleted_count > 0:
        await db.commit()
        logger.info(f"Dọn dẹp tự động: đã xóa {deleted_count} bản ghi preview cũ hơn {retention_days} ngày.")
    else:
        logger.debug(f"Dọn dẹp tự động: không có bản ghi preview nào cũ hơn {retention_days} ngày.")
