"""Routes /api/voices/library — Voice Library tập trung (Issue #18)."""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.dependencies import get_current_active_user, get_tts_service
from app.models.user import User
from app.schemas.voice_library import (
    SyncVoicesResponse,
    ToggleFavoriteResponse,
    VoiceLibraryItem,
    VoiceLibraryListResponse,
    VoiceUpdateRequest,
)
from app.services.tts_service import TTSService
from app.services.voice_library_service import VoiceLibraryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/voices", tags=["Voice Library"])


@router.get("/library", response_model=VoiceLibraryListResponse, summary="Thư viện giọng tập trung")
async def get_voice_library(
    tab: str = Query("all", description="all | mine | favorites"),
    voice_type: Optional[str] = Query(None, description="system | cloned | imported"),
    language: Optional[str] = Query(None, description="Lọc theo ngôn ngữ: vi-VN, en-US..."),
    gender: Optional[str] = Query(None, description="Female | Male | Unknown"),
    search: Optional[str] = Query(None, description="Tìm kiếm theo tên giọng"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> VoiceLibraryListResponse:
    """
    Lấy danh sách giọng đọc từ thư viện tập trung:
    - tab=all: tất cả giọng public + giọng cá nhân của user
    - tab=mine: chỉ giọng clone của user
    - tab=favorites: chỉ giọng user đã yêu thích
    Admin-disabled voices (is_active=False) không xuất hiện với user thường.
    """
    favorites_only = tab == "favorites"
    owner_only = tab == "mine"
    effective_voice_type = voice_type or ("cloned" if owner_only else None)

    result = await VoiceLibraryService.list_voices(
        db=db,
        user_id=current_user.id,
        voice_type=effective_voice_type,
        language=language,
        gender=gender,
        search=search,
        favorites_only=favorites_only,
        owner_only=owner_only,
        limit=limit,
        offset=offset,
        only_active=not getattr(current_user, "is_admin", False),
    )

    fav_set = set(result["favorite_ids"])
    voice_items = [
        VoiceLibraryItem(
            **{
                col: getattr(v, col)
                for col in [
                    "id", "owner_id", "name", "display_name", "description",
                    "provider", "provider_voice_id", "voice_type", "language",
                    "gender", "tags", "preview_url", "sample_duration",
                    "visibility", "status", "is_active", "tier",
                    "credit_multiplier", "cloned_voice_ref", "total_uses", "created_at",
                ]
            },
            is_favorite=v.id in fav_set,
        )
        for v in result["voices"]
    ]

    return VoiceLibraryListResponse(
        total=result["total"],
        voices=voice_items,
        favorite_ids=result["favorite_ids"],
    )


@router.post(
    "/library/{voice_id}/favorite",
    response_model=ToggleFavoriteResponse,
    summary="Thêm/xoá yêu thích giọng đọc",
)
async def toggle_voice_favorite(
    voice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ToggleFavoriteResponse:
    """Toggle yêu thích một giọng trong thư viện."""
    # Verify voice exists
    voice = await VoiceLibraryService.get_voice_by_id(db, voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Giọng không tồn tại trong thư viện.")

    is_favorite = await VoiceLibraryService.toggle_favorite(
        db=db, user_id=current_user.id, voice_id=voice_id
    )
    msg = "Đã thêm vào yêu thích." if is_favorite else "Đã bỏ yêu thích."
    return ToggleFavoriteResponse(voice_id=voice_id, is_favorite=is_favorite, message=msg)


@router.get("/favorites", response_model=list[int], summary="Danh sách ID giọng đã yêu thích")
async def get_favorite_voice_ids(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[int]:
    """Trả về danh sách voice_id mà user đã yêu thích."""
    return await VoiceLibraryService.get_favorites(db=db, user_id=current_user.id)


@router.post(
    "/library/sync",
    response_model=SyncVoicesResponse,
    status_code=status.HTTP_200_OK,
    summary="[Admin] Đồng bộ giọng hệ thống từ provider vào DB",
)
async def sync_system_voices(
    db: AsyncSession = Depends(get_db),
    tts_service: TTSService = Depends(get_tts_service),
    current_user: User = Depends(get_current_active_user),
) -> SyncVoicesResponse:
    """Admin: Đồng bộ danh sách giọng từ edge-tts vào bảng voices."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền đồng bộ giọng.")

    provider_voices = await tts_service.get_voices(force_refresh=True)
    synced = await VoiceLibraryService.sync_system_voices(
        db=db, provider_voices=provider_voices, provider="edge"
    )
    return SyncVoicesResponse(synced=synced, message=f"Đã đồng bộ {synced} giọng từ edge-tts.")


@router.patch(
    "/library/{voice_id}",
    response_model=VoiceLibraryItem,
    summary="[Admin] Cập nhật cấu hình giọng đọc",
)
async def update_voice(
    voice_id: int,
    payload: VoiceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> VoiceLibraryItem:
    """Admin: Cập nhật is_active, tier, credit_multiplier, tags, display_name."""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Chỉ admin mới có quyền chỉnh sửa giọng.")

    voice = await VoiceLibraryService.get_voice_by_id(db, voice_id)
    if not voice:
        raise HTTPException(status_code=404, detail="Giọng không tồn tại.")

    if payload.is_active is not None:
        voice.is_active = payload.is_active
    if payload.tier is not None:
        voice.tier = payload.tier
    if payload.credit_multiplier is not None:
        voice.credit_multiplier = payload.credit_multiplier
    if payload.tags is not None:
        voice.tags = payload.tags
    if payload.display_name is not None:
        voice.display_name = payload.display_name

    await db.commit()
    await db.refresh(voice)

    fav_ids = await VoiceLibraryService.get_favorites(db, current_user.id)
    return VoiceLibraryItem(
        **{
            col: getattr(voice, col)
            for col in [
                "id", "owner_id", "name", "display_name", "description",
                "provider", "provider_voice_id", "voice_type", "language",
                "gender", "tags", "preview_url", "sample_duration",
                "visibility", "status", "is_active", "tier",
                "credit_multiplier", "cloned_voice_ref", "total_uses", "created_at",
            ]
        },
        is_favorite=voice.id in fav_ids,
    )
