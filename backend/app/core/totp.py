"""Bộ sinh và xác thực mã 2FA / TOTP chuẩn RFC 6238 (Issue #16)."""
import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Tuple
from urllib.parse import quote


def generate_totp_secret(length: int = 32) -> str:
    """Sinh khóa bí mật ngẫu nhiên mã hóa Base32 cho TOTP (mặc định 32 ký tự)."""
    # 20 bytes ngẫu nhiên -> sinh chuỗi Base32 chuẩn
    random_bytes = secrets.token_bytes(20)
    secret_b32 = base64.b32encode(random_bytes).decode("ascii").replace("=", "")
    return secret_b32[:length]


def _get_hotp_code(secret_b32: str, counter: int, digits: int = 6) -> str:
    """Sinh mã HOTP từ khóa Base32 và counter theo chuẩn RFC 4226."""
    # Chuẩn hóa Base32 padding
    clean_secret = secret_b32.strip().upper()
    padding = (8 - len(clean_secret) % 8) % 8
    clean_secret += "=" * padding

    key = base64.b32decode(clean_secret, casefold=True)
    counter_bytes = struct.pack(">Q", counter)

    hmac_digest = hmac.new(key, counter_bytes, hashlib.sha1).digest()
    offset = hmac_digest[-1] & 0x0F
    truncated_hash = struct.unpack(">I", hmac_digest[offset : offset + 4])[0] & 0x7FFFFFFF

    code = truncated_hash % (10**digits)
    return str(code).zfill(digits)


def generate_totp_code(secret_b32: str, timestamp: float | None = None, step: int = 30) -> str:
    """Sinh mã TOTP 6 số tại thời điểm timestamp (mặc định hiện tại)."""
    now = time.time() if timestamp is None else timestamp
    counter = int(now // step)
    return _get_hotp_code(secret_b32, counter)


def verify_totp_code(
    secret_b32: str,
    code: str,
    timestamp: float | None = None,
    step: int = 30,
    window: int = 1,
) -> bool:
    """
    Xác thực mã 6 số TOTP.
    Cho phép window lệch ±1 chu kỳ (tối đa ±30 giây) để bù trừ trễ thời gian hệ thống người dùng.
    """
    if not secret_b32 or not code:
        return False

    clean_code = str(code).strip()
    if len(clean_code) != 6 or not clean_code.isdigit():
        return False

    now = time.time() if timestamp is None else timestamp
    current_counter = int(now // step)

    for i in range(-window, window + 1):
        expected_code = _get_hotp_code(secret_b32, current_counter + i)
        if hmac.compare_digest(expected_code, clean_code):
            return True

    return False


def get_totp_uri(secret_b32: str, email: str, issuer: str = "Voxify") -> str:
    """
    Tạo URI provisioning cho ứng dụng xác thực (Google Authenticator, Authy, 1Password).
    Định dạng: otpauth://totp/Issuer:user@example.com?secret=...&issuer=Issuer
    """
    quoted_issuer = quote(issuer)
    quoted_email = quote(email)
    return f"otpauth://totp/{quoted_issuer}:{quoted_email}?secret={secret_b32}&issuer={quoted_issuer}&algorithm=SHA1&digits=6&period=30"


def setup_admin_2fa(email: str, issuer: str = "Voxify") -> Tuple[str, str]:
    """Tạo bộ khóa 2FA mới và trả về tuple: (secret_b32, totp_uri)."""
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, email, issuer)
    return secret, uri
