"""Các endpoint xác thực tài khoản người dùng."""
import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.rate_limiter import check_login_rate_limit, reset_login_rate_limit
from app.db import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    MessageResponse,
    ResetPasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
)
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Ghi refresh token vào httpOnly cookie (30 ngày)."""
    settings = get_settings()
    max_age = settings.refresh_token_expire_days * 86400
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=max_age,
        expires=max_age,
        httponly=True,
        samesite="lax",
        secure=False if settings.debug else False,  # Có thể bật True khi chạy HTTPS
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Xóa cookie refresh token."""
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
        httponly=True,
        samesite="lax",
    )


@router.post("/register", response_model=UserOut, summary="Đăng ký tài khoản mới")
async def register(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await AuthService.register(
            db=db,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/login", response_model=TokenResponse, summary="Đăng nhập email & mật khẩu")
async def login(
    request: Request,
    response: Response,
    data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # Kiểm tra giới hạn 5 lần/phút/IP chống brute force
    check_login_rate_limit(request, max_attempts=5, window_seconds=60)

    try:
        user = await AuthService.authenticate(
            db=db,
            email=data.email,
            password=data.password,
        )
        access_token, raw_refresh = await AuthService.create_tokens(db, user)
        _set_refresh_cookie(response, raw_refresh)
        reset_login_rate_limit(request)

        settings = get_settings()
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserOut.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/google", response_model=TokenResponse, summary="Đăng nhập / Đăng ký qua Google OAuth")
async def google_login(
    response: Response,
    data: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await AuthService.authenticate_google(db=db, credential=data.credential)
        access_token, raw_refresh = await AuthService.create_tokens(db, user)
        _set_refresh_cookie(response, raw_refresh)
        reset_login_rate_limit(request)

        settings = get_settings()
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserOut.model_validate(user),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/refresh", response_model=TokenResponse, summary="Làm mới access token")
async def refresh_token(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Không tìm thấy phiên làm việc. Vui lòng đăng nhập lại.",
        )

    try:
        new_access_token, user = await AuthService.refresh_access_token(db, refresh_token)
        settings = get_settings()
        return TokenResponse(
            access_token=new_access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
            user=UserOut.model_validate(user),
        )
    except ValueError as e:
        _clear_refresh_cookie(response)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/logout", response_model=MessageResponse, summary="Đăng xuất tài khoản")
async def logout(
    response: Response,
    refresh_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        await AuthService.revoke_refresh_token(db, refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Đăng xuất thành công.")


@router.get("/me", response_model=UserOut, summary="Lấy thông tin người dùng hiện tại")
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.post("/forgot-password", response_model=MessageResponse, summary="Quên mật khẩu")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    await AuthService.request_password_reset(db, data.email)
    return MessageResponse(
        message="Nếu địa chỉ email tồn tại trong hệ thống, hướng dẫn đặt lại mật khẩu đã được gửi."
    )


@router.post("/reset-password", response_model=MessageResponse, summary="Đặt lại mật khẩu mới")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        await AuthService.reset_password(db, data.token, data.new_password)
        return MessageResponse(message="Mật khẩu của bạn đã được thay đổi thành công. Hãy đăng nhập lại.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/verify-email", response_model=MessageResponse, summary="Xác thực email qua token")
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        await AuthService.verify_email_token(db, token)
        return MessageResponse(message="Email của bạn đã được xác thực thành công.")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
