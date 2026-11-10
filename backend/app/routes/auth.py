"""Các endpoint xác thực tài khoản người dùng."""
import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.rate_limiter import check_login_rate_limit, reset_login_rate_limit
from app.core.security import create_timed_token, decode_token
from app.core.security_validation import validate_password_strength
from app.core.totp import generate_totp_secret, get_totp_uri, verify_totp_code
from app.db import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    MessageResponse,
    PasswordStrengthRequest,
    PasswordStrengthResponse,
    ResetPasswordRequest,
    TokenResponse,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
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

        # Nếu user đã bật xác thực 2 bước (2FA) (Issue #16)
        if getattr(user, "two_factor_enabled", False):
            temp_token = create_timed_token(
                {"sub": str(user.id), "email": user.email, "role": user.role},
                token_type="2fa_pending",
                expires_minutes=5,
            )
            reset_login_rate_limit(request)
            return TokenResponse(
                access_token="",
                token_type="bearer",
                expires_in=300,
                user=None,
                requires_2fa=True,
                temp_token=temp_token,
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
            requires_2fa=False,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/google", response_model=TokenResponse, summary="Đăng nhập / Đăng ký qua Google OAuth")
async def google_login(
    request: Request,
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


@router.post("/password-strength", response_model=PasswordStrengthResponse, summary="Kiểm tra độ mạnh mật khẩu")
async def check_password_strength(data: PasswordStrengthRequest):
    """Kiểm tra độ an toàn của mật khẩu theo chuẩn an ninh OWASP."""
    is_valid, msg = validate_password_strength(data.password)
    return PasswordStrengthResponse(is_valid=is_valid, message=msg)


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse, summary="Khởi tạo mã 2FA / TOTP (Admin/User)")
async def setup_two_factor(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Sinh khóa bí mật Base32 và URI quét mã QR qua Google Authenticator / Authy."""
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, current_user.email, issuer="Voxify")
    current_user.two_factor_secret = secret
    await db.commit()
    return TwoFactorSetupResponse(secret=secret, qr_uri=uri, manual_entry_key=secret)


@router.post("/2fa/enable", response_model=MessageResponse, summary="Kích hoạt 2FA sau khi xác nhận mã TOTP")
async def enable_two_factor(
    data: TwoFactorVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Xác nhận mã 6 số từ ứng dụng và chính thức kích hoạt bảo mật 2FA."""
    if not current_user.two_factor_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vui lòng gọi API /2fa/setup trước khi kích hoạt.",
        )

    if not verify_totp_code(current_user.two_factor_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác thực 2FA không chính xác hoặc đã hết hạn.",
        )

    current_user.two_factor_enabled = True
    await db.commit()
    return MessageResponse(message="Đã kích hoạt xác thực 2 bước (2FA) thành công.")


@router.post("/2fa/disable", response_model=MessageResponse, summary="Tắt xác thực 2 bước (2FA)")
async def disable_two_factor(
    data: TwoFactorVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Tắt 2FA (yêu cầu cung cấp mã 6 số TOTP hiện tại để xác minh danh tính)."""
    if not current_user.two_factor_enabled:
        return MessageResponse(message="Tài khoản chưa kích hoạt 2FA.")

    if not current_user.two_factor_secret or not verify_totp_code(current_user.two_factor_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác thực 2FA không chính xác.",
        )

    current_user.two_factor_enabled = False
    current_user.two_factor_secret = None
    await db.commit()
    return MessageResponse(message="Đã tắt xác thực 2 bước (2FA) thành công.")


@router.post("/2fa/verify", response_model=TokenResponse, summary="Hoàn tất đăng nhập bằng mã 2FA")
async def verify_two_factor_login(
    data: TwoFactorVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Xác thực mã 6 số TOTP khi đăng nhập có 2FA và cấp Access Token đầy đủ."""
    if not data.temp_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Thiếu mã token tạm thời (temp_token).",
        )

    payload = decode_token(data.temp_token)
    if not payload or payload.get("type") != "2fa_pending":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên xác thực 2FA đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.",
        )

    user_id = int(payload["sub"])
    user = await AuthService.get_user_by_id(db, user_id)
    if not user or not user.is_active or getattr(user, "is_banned", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản không hợp lệ hoặc đã bị khóa.",
        )

    if not user.two_factor_secret or not verify_totp_code(user.two_factor_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã xác thực 2FA không chính xác.",
        )

    access_token, raw_refresh = await AuthService.create_tokens(db, user)
    _set_refresh_cookie(response, raw_refresh)
    settings = get_settings()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
        requires_2fa=False,
    )
