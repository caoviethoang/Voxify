"""Router quản lý API Key và Thống kê cho Developer Portal trên Web."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.api_key import (
    ApiKeyCreatedResponse,
    ApiKeyCreateRequest,
    ApiKeyItemResponse,
    ApiStatsResponse,
)
from app.services.api_key_service import ApiKeyService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/developers", tags=["Developers"])


@router.get("/keys", response_model=List[ApiKeyItemResponse], summary="Lấy danh sách API Key của người dùng")
async def list_keys(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ApiKeyItemResponse]:
    """
    Trả về danh sách tất cả API Key của tài khoản hiện tại.
    Khóa bí mật không bao giờ được trả về (chỉ trả prefix như: vx_live_abc123...****).
    """
    keys = await ApiKeyService.list_api_keys(db=db, user_id=current_user.id)
    return [
        ApiKeyItemResponse(
            id=k.id,
            name=k.name,
            key_prefix=k.key_prefix,
            is_active=k.is_active,
            created_at=k.created_at,
            last_used_at=k.last_used_at,
            revoked_at=k.revoked_at,
        )
        for k in keys
    ]


@router.post(
    "/keys",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo API Key mới",
)
async def create_key(
    payload: ApiKeyCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    """
    Tạo một API Key mới.
    QUAN TRỌNG: raw_key chỉ được trả về DUY NHẤT một lần trong phản hồi này.
    """
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Tên API Key không được để trống.")

    api_key, raw_key = await ApiKeyService.create_api_key(
        db=db,
        user_id=current_user.id,
        name=name,
    )

    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        key_prefix=api_key.key_prefix,
        raw_key=raw_key,
        created_at=api_key.created_at,
    )


@router.delete("/keys/{key_id}", summary="Thu hồi (Revoke) API Key")
async def revoke_key(
    key_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Vô hiệu hóa vĩnh viễn một API Key. Các request sau đó bằng key này sẽ bị từ chối 401."""
    success = await ApiKeyService.revoke_api_key(
        db=db,
        user_id=current_user.id,
        key_id=key_id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy API Key #{key_id} hoặc bạn không có quyền thu hồi.",
        )

    return {"message": "API Key đã được thu hồi thành công."}


@router.get("/stats", response_model=ApiStatsResponse, summary="Thống kê lượng gọi API và Credit tiêu thụ")
async def get_stats(
    days: int = Query(7, ge=1, le=30, description="Số ngày cần thống kê"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ApiStatsResponse:
    """Thống kê tổng request, credit tiêu thụ và biểu đồ theo từng ngày."""
    stats = await ApiKeyService.get_usage_stats(
        db=db,
        user_id=current_user.id,
        days=days,
    )
    return ApiStatsResponse(**stats)
