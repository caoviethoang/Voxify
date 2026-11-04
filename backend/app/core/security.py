"""Module bảo mật: băm mật khẩu, mã hóa và giải mã JWT token."""
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import secrets
from typing import Any, Dict, Optional

import bcrypt
import jwt

from app.config import get_settings

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """Băm mật khẩu bằng bcrypt."""
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """Xác thực mật khẩu plain với hash bcrypt."""
    if not hashed_password:
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except Exception as e:
        logger.warning(f"Lỗi kiểm tra mật khẩu: {e}")
        return False


def hash_token(raw_token: str) -> str:
    """Tạo hash SHA-256 từ chuỗi token để lưu an toàn vào DB."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Tạo JWT access token (mặc định 15 phút)."""
    settings = get_settings()
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": "access",
    })
    encoded_jwt = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def create_refresh_token(
    user_id: int,
) -> tuple[str, str, datetime]:
    """
    Tạo refresh token ngẫu nhiên (30 ngày).
    Trả về: (raw_token, token_hash, expires_at).
    """
    settings = get_settings()
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return raw_token, token_hash, expires_at


def create_timed_token(
    payload: Dict[str, Any],
    token_type: str,
    expires_minutes: int,
) -> str:
    """Tạo JWT token có thời hạn cho reset mật khẩu hoặc xác thực email."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    to_encode = payload.copy()
    to_encode.update({
        "exp": now + timedelta(minutes=expires_minutes),
        "iat": now,
        "type": token_type,
    })
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Giải mã và kiểm tra tính hợp lệ của token."""
    settings = get_settings()
    try:
        decoded = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return decoded
    except jwt.ExpiredSignatureError:
        logger.debug("Token đã hết hạn")
        return None
    except jwt.PyJWTError as e:
        logger.debug(f"Token không hợp lệ: {e}")
        return None

