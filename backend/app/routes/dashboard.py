"""Route /api/dashboard — Thống kê và dữ liệu tổng quan cho trang Dashboard."""
import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies import get_current_active_user
from app.models.generation import Generation
from app.models.user import User
from app.routes.history import _build_history_item
from app.schemas.dashboard import DashboardStatsResponse
from app.services.credit_service import CreditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStatsResponse, summary="Lấy thống kê tổng quan của người dùng")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Trả về dữ liệu tổng quan cho Dashboard:
    1. Ký tự đã dùng trong tháng này (tính từ ngày 1 của tháng hiện tại)
    2. Tổng số audio đã tạo thành công
    3. Tổng thời lượng audio (giây)
    4. Số dư credit hiện tại
    5. Generation gần nhất để 'Tiếp tục công việc'
    6. 5 hoạt động gần đây nhất
    """
    now = datetime.now(timezone.utc)
    start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    # 1. Ký tự đã dùng trong tháng này
    stmt_chars = select(func.coalesce(func.sum(Generation.char_count), 0)).where(
        Generation.user_id == current_user.id,
        Generation.created_at >= start_of_month,
        Generation.is_preview == False,  # noqa: E712
    )
    chars_used = (await db.execute(stmt_chars)).scalar() or 0

    # 2. Tổng số audio đã tạo thành công
    stmt_count = select(func.count(Generation.id)).where(
        Generation.user_id == current_user.id,
        Generation.is_preview == False,  # noqa: E712
        Generation.status == "done",
    )
    total_audio = (await db.execute(stmt_count)).scalar() or 0

    # 3. Tổng thời lượng audio (giây)
    stmt_duration = select(func.coalesce(func.sum(Generation.duration), 0.0)).where(
        Generation.user_id == current_user.id,
        Generation.is_preview == False,  # noqa: E712
        Generation.status == "done",
    )
    total_duration = float((await db.execute(stmt_duration)).scalar() or 0.0)

    # 4. Số dư credit
    credit_balance = await CreditService.get_balance(db, current_user.id)

    # 5. 5 hoạt động gần đây
    stmt_recent = (
        select(Generation)
        .where(
            Generation.user_id == current_user.id,
            Generation.is_preview == False,  # noqa: E712
        )
        .order_by(Generation.created_at.desc())
        .limit(5)
    )
    recent_gens = (await db.execute(stmt_recent)).scalars().all()
    recent_items = [_build_history_item(g) for g in recent_gens]

    # 6. Generation gần nhất cho card "Tiếp tục công việc"
    latest_item = recent_items[0] if recent_items else None

    return DashboardStatsResponse(
        chars_used_this_month=int(chars_used),
        total_audio_generated=int(total_audio),
        total_duration_seconds=round(total_duration, 2),
        credit_balance=credit_balance,
        latest_generation=latest_item,
        recent_activities=recent_items,
    )

