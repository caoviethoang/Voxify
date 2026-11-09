"""Dịch vụ quản lý API Key và theo dõi sử dụng Public API v1 (Issue #13)."""
import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.api_key import ApiKey, ApiUsageLog
from app.models.user import User

logger = logging.getLogger(__name__)


class ApiKeyService:
    """Service Object xử lý các logic nghiệp vụ liên quan đến API Key."""

    @staticmethod
    def generate_key_components() -> Tuple[str, str, str]:
        """
        Sinh ra API Key mới:
        - raw_key: vx_live_ + 48 ký tự hex ngẫu nhiên
        - key_prefix: vx_live_xxxx...xxxx để người dùng nhận diện
        - hashed_key: SHA-256 hex string lưu trong cơ sở dữ liệu
        """
        token = secrets.token_hex(24)
        raw_key = f"vx_live_{token}"
        key_prefix = f"{raw_key[:14]}...{raw_key[-4:]}"
        hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return raw_key, key_prefix, hashed_key

    @classmethod
    async def create_api_key(
        cls,
        db: AsyncSession,
        user_id: int,
        name: str,
    ) -> Tuple[ApiKey, str]:
        """Tạo mới API Key và trả về bản ghi kèm raw_key duy nhất một lần."""
        raw_key, key_prefix, hashed_key = cls.generate_key_components()

        api_key = ApiKey(
            user_id=user_id,
            name=name.strip(),
            key_prefix=key_prefix,
            hashed_key=hashed_key,
            is_active=True,
        )
        db.add(api_key)
        await db.commit()
        await db.refresh(api_key)
        logger.info(f"Đã tạo API Key '{name}' (id={api_key.id}, prefix={key_prefix}) cho user={user_id}")
        return api_key, raw_key

    @classmethod
    async def verify_api_key(
        cls,
        db: AsyncSession,
        raw_key: str,
    ) -> Optional[Tuple[ApiKey, User]]:
        """
        Xác thực raw API Key:
        - Tính hash SHA-256
        - Kiểm tra key có tồn tại và đang active hay không
        - Cập nhật last_used_at
        """
        if not raw_key or not raw_key.startswith("vx_live_"):
            return None

        hashed_key = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        stmt = (
            select(ApiKey)
            .options(selectinload(ApiKey.user))
            .where(ApiKey.hashed_key == hashed_key, ApiKey.is_active.is_(True))
        )
        res = await db.execute(stmt)
        api_key = res.scalar_one_or_none()
        if not api_key or not api_key.user:
            return None

        # Cập nhật thời điểm sử dụng gần nhất
        api_key.last_used_at = datetime.now(UTC)
        await db.commit()
        return api_key, api_key.user

    @classmethod
    async def revoke_api_key(
        cls,
        db: AsyncSession,
        user_id: int,
        key_id: int,
    ) -> bool:
        """Thu hồi (revoke) một API Key."""
        stmt = select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user_id)
        res = await db.execute(stmt)
        api_key = res.scalar_one_or_none()
        if not api_key:
            return False

        api_key.is_active = False
        api_key.revoked_at = datetime.now(UTC)
        await db.commit()
        logger.info(f"Đã thu hồi API Key #{key_id} của user={user_id}")
        return True

    @classmethod
    async def list_api_keys(
        cls,
        db: AsyncSession,
        user_id: int,
    ) -> List[ApiKey]:
        """Liệt kê tất cả API Key của người dùng."""
        stmt = select(ApiKey).where(ApiKey.user_id == user_id).order_by(desc(ApiKey.created_at))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @classmethod
    async def log_usage(
        cls,
        db: AsyncSession,
        api_key_id: int,
        user_id: int,
        endpoint: str,
        status_code: int,
        credits_used: int = 0,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> ApiUsageLog:
        """Ghi nhận nhật ký một yêu cầu gọi API."""
        log = ApiUsageLog(
            api_key_id=api_key_id,
            user_id=user_id,
            endpoint=endpoint,
            status_code=status_code,
            credits_used=credits_used,
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else None,
        )
        db.add(log)
        await db.commit()
        return log

    @classmethod
    async def get_usage_stats(
        cls,
        db: AsyncSession,
        user_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Thống kê tổng lượng request, credit và chi tiết từng ngày."""
        start_date = datetime.now(UTC) - timedelta(days=days)

        # Lấy tất cả logs của user trong khoảng thời gian
        stmt = (
            select(ApiUsageLog)
            .where(ApiUsageLog.user_id == user_id, ApiUsageLog.created_at >= start_date)
            .order_by(ApiUsageLog.created_at.asc())
        )
        res = await db.execute(stmt)
        logs = res.scalars().all()

        total_requests = len(logs)
        total_credits = sum(log.credits_used for log in logs)

        # Tổng hợp theo ngày (YYYY-MM-DD)
        daily_dict: Dict[str, Dict[str, int]] = {}
        for d in range(days):
            day_str = (datetime.now(UTC) - timedelta(days=days - 1 - d)).strftime("%Y-%m-%d")
            daily_dict[day_str] = {"requests": 0, "credits": 0}

        for log in logs:
            day_str = log.created_at.strftime("%Y-%m-%d")
            if day_str in daily_dict:
                daily_dict[day_str]["requests"] += 1
                daily_dict[day_str]["credits"] += log.credits_used

        daily_usage = [
            {"date": day_str, "requests": data["requests"], "credits": data["credits"]}
            for day_str, data in daily_dict.items()
        ]

        return {
            "total_requests": total_requests,
            "total_credits": total_credits,
            "daily_usage": daily_usage,
        }
