"""Service ghi nhận Audit Log cho mọi hoạt động của Quản trị viên (Issue #15)."""
import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin import AdminAuditLog

logger = logging.getLogger(__name__)


class AdminAuditService:
    """Service Object chuyên trách ghi nhận và tra cứu Audit Log."""

    @staticmethod
    async def log_action(
        db: AsyncSession,
        admin_id: Optional[int],
        action: str,
        target_type: str,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AdminAuditLog:
        """Ghi nhận một thao tác can thiệp dữ liệu của admin."""
        serialized_details: Optional[str] = None
        if details is not None:
            try:
                serialized_details = json.dumps(details, ensure_ascii=False)
            except Exception as e:
                logger.warning(f"Không thể serialize audit log details: {e}")
                serialized_details = str(details)

        audit_entry = AdminAuditLog(
            admin_id=admin_id,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            details=serialized_details,
            ip_address=ip_address,
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)

        logger.info(
            f"[AUDIT] Admin #{admin_id} thực hiện '{action}' trên {target_type} #{target_id} (IP: {ip_address})"
        )
        return audit_entry

    @staticmethod
    async def list_logs(
        db: AsyncSession,
        action: Optional[str] = None,
        target_type: Optional[str] = None,
        admin_id: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[AdminAuditLog], int]:
        """Tra cứu danh sách Audit Log có phân trang và bộ lọc."""
        from sqlalchemy import func

        stmt = select(AdminAuditLog)
        count_stmt = select(func.count(AdminAuditLog.id))

        if action:
            stmt = stmt.where(AdminAuditLog.action == action)
            count_stmt = count_stmt.where(AdminAuditLog.action == action)
        if target_type:
            stmt = stmt.where(AdminAuditLog.target_type == target_type)
            count_stmt = count_stmt.where(AdminAuditLog.target_type == target_type)
        if admin_id:
            stmt = stmt.where(AdminAuditLog.admin_id == admin_id)
            count_stmt = count_stmt.where(AdminAuditLog.admin_id == admin_id)

        # Đếm tổng
        total_res = await db.execute(count_stmt)
        total = total_res.scalar() or 0

        # Lấy bản ghi phân trang
        offset = (page - 1) * limit
        stmt = stmt.order_by(desc(AdminAuditLog.created_at)).offset(offset).limit(limit)
        res = await db.execute(stmt)
        items = list(res.scalars().all())

        return items, total
