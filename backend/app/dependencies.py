"""FastAPI dependencies — singleton instances & auth guards."""
from functools import lru_cache
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.security import decode_token
from app.db import get_db
from app.models.user import User
from app.providers import ProviderRegistry
from app.services.auth_service import AuthService
from app.services.tts_service import TTSService

# HTTP Bearer scheme không bắt buộc để hỗ trợ cả cookie lẫn header
security = HTTPBearer(auto_error=False)


@lru_cache
def get_tts_service() -> TTSService:
    """Singleton TTSService với provider được cấu hình từ .env."""
    settings = get_settings()
    provider = ProviderRegistry.get(settings.tts_provider)
    return TTSService(provider=provider, settings=settings)


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Xác thực người dùng hiện tại từ header Authorization: Bearer <token>
    hoặc cookie access_token.
    """
    token: Optional[str] = None
    if credentials:
        token = credentials.credentials
    elif "access_token" in request.cookies:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chưa đăng nhập. Vui lòng đăng nhập để tiếp tục.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập đã hết hạn hoặc không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mã định danh người dùng không hợp lệ.",
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ.")

    user = await AuthService.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Người dùng không tồn tại.")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị tạm khóa.")

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Kiểm tra tài khoản đã kích hoạt và xác thực email (nếu bật cấu hình)."""
    settings = get_settings()
    if settings.require_email_verification and not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vui lòng xác thực email trước khi sử dụng tính năng này.",
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Chỉ cho phép quản trị viên (Admin) truy cập."""
    if current_user.role != "admin" and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền quản trị viên để thực hiện thao tác này.",
        )
    return current_user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Lấy user nếu có token hợp lệ, nếu không trả None mà không raise exception."""
    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None
