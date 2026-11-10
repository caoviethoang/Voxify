"""Dịch vụ xử lý logic xác thực người dùng."""
import logging
from datetime import UTC, datetime
from typing import Optional

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.email import send_password_reset_email, send_verification_email
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_timed_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.security_validation import validate_password_strength
from app.models.refresh_token import RefreshToken
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthService:
    """Nghiệp vụ xác thực, phiên làm việc và bảo mật tài khoản."""

    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower().strip())
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def register(
        db: AsyncSession,
        email: str,
        password: str,
        full_name: Optional[str] = None,
    ) -> User:
        """Đăng ký tài khoản người dùng mới."""
        settings = get_settings()
        clean_email = email.lower().strip()

        existing = await AuthService.get_user_by_email(db, clean_email)
        if existing:
            raise ValueError("Email này đã được sử dụng. Vui lòng đăng nhập hoặc dùng email khác.")

        # Chính sách mật khẩu mạnh (Issue #16)
        is_strong, pw_msg = validate_password_strength(password)
        if not is_strong:
            raise ValueError(pw_msg)

        user = User(
            email=clean_email,
            hashed_password=hash_password(password),
            full_name=full_name.strip() if full_name else None,
            role="user",
            is_active=True,
            is_admin=False,
            # Nếu hệ thống không bắt buộc xác thực email, đánh dấu verified luôn
            is_verified=not settings.require_email_verification,
            credit_balance=0,
            credits=0,
        )
        db.add(user)
        await db.flush()

        # Tặng credit khi đăng ký qua CreditService (ghi nhận sổ cái ledger)
        from app.services.credit_service import CreditService
        await CreditService.add_signup_bonus(db, user.id)

        await db.commit()
        await db.refresh(user)

        # Gửi email kích hoạt nếu bật tính năng
        if settings.require_email_verification:
            token = create_timed_token({"sub": clean_email}, token_type="verify_email", expires_minutes=1440)
            send_verification_email(clean_email, token)

        return user

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        email: str,
        password: str,
    ) -> User:
        """Xác thực thông tin đăng nhập email + password."""
        clean_email = email.lower().strip()
        user = await AuthService.get_user_by_email(db, clean_email)

        if not user or not user.hashed_password:
            raise ValueError("Email hoặc mật khẩu không chính xác.")

        if not verify_password(password, user.hashed_password):
            raise ValueError("Email hoặc mật khẩu không chính xác.")

        if not user.is_active:
            raise ValueError("Tài khoản của bạn đã bị khóa hoặc ngừng hoạt động.")

        return user

    @staticmethod
    async def create_tokens(
        db: AsyncSession,
        user: User,
    ) -> tuple[str, str]:
        """
        Tạo cặp JWT access token (15 phút) và refresh token (30 ngày).
        Lưu token_hash vào bảng refresh_tokens.
        Trả về: (access_token, raw_refresh_token).
        """
        get_settings()
        access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        })

        raw_refresh, token_hash, expires_at = create_refresh_token(user.id)
        db_token = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(db_token)
        await db.commit()

        return access_token, raw_refresh

    @staticmethod
    async def refresh_access_token(
        db: AsyncSession,
        raw_refresh_token: str,
    ) -> tuple[str, User]:
        """Tạo access token mới từ refresh token hợp lệ."""
        token_hash = hash_token(raw_refresh_token)
        now = datetime.now(UTC)

        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > now,
        )
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise ValueError("Phiên đăng nhập đã hết hạn hoặc không hợp lệ. Vui lòng đăng nhập lại.")

        user = await AuthService.get_user_by_id(db, token_record.user_id)
        if not user or not user.is_active:
            raise ValueError("Tài khoản không tồn tại hoặc đã bị khóa.")

        new_access_token = create_access_token({
            "sub": str(user.id),
            "email": user.email,
            "role": user.role,
        })
        return new_access_token, user

    @staticmethod
    async def revoke_refresh_token(
        db: AsyncSession,
        raw_refresh_token: str,
    ) -> None:
        """Thu hồi refresh token khi người dùng đăng xuất."""
        token_hash = hash_token(raw_refresh_token)
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        result = await db.execute(stmt)
        token_record = result.scalar_one_or_none()
        if token_record:
            token_record.is_revoked = True
            await db.commit()

    @staticmethod
    async def request_password_reset(db: AsyncSession, email: str) -> None:
        """Tạo và gửi link đặt lại mật khẩu qua email."""
        clean_email = email.lower().strip()
        user = await AuthService.get_user_by_email(db, clean_email)
        if not user:
            # Bảo mật: không báo cho attacker biết email có tồn tại hay không
            return

        token = create_timed_token({"sub": clean_email}, token_type="reset_password", expires_minutes=30)
        send_password_reset_email(clean_email, token)

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        token: str,
        new_password: str,
    ) -> None:
        """Xác minh token và cập nhật mật khẩu mới."""
        payload = decode_token(token)
        if not payload or payload.get("type") != "reset_password":
            raise ValueError("Đường dẫn đặt lại mật khẩu đã hết hạn hoặc không hợp lệ.")

        email = payload.get("sub")
        if not email:
            raise ValueError("Mã xác thực không hợp lệ.")

        user = await AuthService.get_user_by_email(db, email)
        if not user:
            raise ValueError("Người dùng không tồn tại.")

        # Chính sách mật khẩu mạnh (Issue #16)
        is_strong, pw_msg = validate_password_strength(new_password)
        if not is_strong:
            raise ValueError(pw_msg)

        user.hashed_password = hash_password(new_password)
        await db.commit()

    @staticmethod
    async def verify_email_token(db: AsyncSession, token: str) -> None:
        """Xác minh email người dùng qua token."""
        payload = decode_token(token)
        if not payload or payload.get("type") != "verify_email":
            raise ValueError("Đường dẫn xác thực đã hết hạn hoặc không hợp lệ.")

        email = payload.get("sub")
        if not email or not isinstance(email, str):
            raise ValueError("Mã xác thực không hợp lệ.")
        user = await AuthService.get_user_by_email(db, email)
        if not user:
            raise ValueError("Người dùng không tồn tại.")

        user.is_verified = True
        await db.commit()

    @staticmethod
    async def authenticate_google(
        db: AsyncSession,
        credential: str,
    ) -> User:
        """Xác thực Google ID Token và đăng nhập / đăng ký người dùng."""
        settings = get_settings()
        try:
            # Xác minh Google ID Token
            client_id = settings.google_client_id or None
            id_info = google_id_token.verify_oauth2_token(
                credential, google_requests.Request(), client_id
            )
        except Exception as e:
            logger.warning(f"Lỗi xác thực Google token: {e}")
            raise ValueError(f"Không thể xác thực danh tính Google: {str(e)}")

        google_sub = id_info.get("sub")
        email = id_info.get("email", "").lower().strip()
        full_name = id_info.get("name")

        if not email:
            raise ValueError("Không lấy được địa chỉ email từ tài khoản Google.")

        # Tìm người dùng theo google_id hoặc email
        stmt = select(User).where((User.google_id == google_sub) | (User.email == email))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if user:
            # Cập nhật google_id nếu trước đó đăng ký bằng email
            if not user.google_id:
                user.google_id = google_sub
            if not user.is_verified:
                user.is_verified = True
            await db.commit()
            return user

        # Tạo mới tài khoản qua Google
        new_user = User(
            email=email,
            full_name=full_name,
            google_id=google_sub,
            hashed_password=None,
            role="user",
            is_active=True,
            is_admin=False,
            is_verified=True,
            credit_balance=0,
            credits=0,
        )
        db.add(new_user)
        await db.flush()

        from app.services.credit_service import CreditService
        await CreditService.add_signup_bonus(db, new_user.id)

        await db.commit()
        await db.refresh(new_user)
        return new_user

