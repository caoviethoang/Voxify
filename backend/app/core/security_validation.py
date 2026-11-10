"""Các tiện ích xác thực đầu vào, kiểm tra magic bytes và chống Path Traversal (Issue #16)."""
import os
import re
import unicodedata
from pathlib import Path
from typing import Tuple, Union


class SecurityValidationError(ValueError):
    """Lỗi khi dữ liệu đầu vào hoặc đường dẫn vi phạm an ninh."""
    pass


def validate_audio_magic_bytes(content: bytes) -> Tuple[bool, str, str]:
    """
    Xác thực MIME type thực tế của file âm thanh qua header/magic bytes (chống đổi đuôi file giả mạo).
    Trả về: (is_valid: bool, mime_type: str, suggested_ext: str)
    """
    if not content or len(content) < 4:
        return False, "application/octet-stream", ""

    # 1. MP3 có ID3v2 tag (b"ID3")
    if content.startswith(b"ID3"):
        return True, "audio/mpeg", ".mp3"

    # 2. MP3 thô (MPEG Audio Frame Sync 11 bits: 0xFFE0 / 0xFFF0)
    if len(content) >= 2 and content[0] == 0xFF and (content[1] & 0xE0) == 0xE0:
        return True, "audio/mpeg", ".mp3"

    # 3. WAV (RIFF....WAVE)
    if content.startswith(b"RIFF") and len(content) >= 12 and content[8:12] == b"WAVE":
        return True, "audio/wav", ".wav"

    # 4. OGG (OggS)
    if content.startswith(b"OggS"):
        return True, "audio/ogg", ".ogg"

    # 5. FLAC (fLaC)
    if content.startswith(b"fLaC"):
        return True, "audio/flac", ".flac"

    # 6. M4A / MP4 (....ftyp)
    if len(content) >= 8 and content[4:8] == b"ftyp":
        return True, "audio/mp4", ".m4a"

    # 7. WEBM / EBML (0x1A 0x45 0xDF 0xA3)
    if content.startswith(b"\x1a\x45\xdf\xa3"):
        return True, "audio/webm", ".webm"

    return False, "application/octet-stream", ""


def sanitize_filename(filename: str, default_name: str = "upload.mp3") -> str:
    """
    Chuẩn hóa và lọc sạch tên file tải lên, loại bỏ Path Traversal và ký tự nguy hiểm.
    """
    if not filename:
        return default_name

    # Lấy tên file gốc không chứa đường dẫn thư mục
    base_name = os.path.basename(filename.replace("\\", "/"))

    # Chuẩn hóa Unicode NFC
    normalized = unicodedata.normalize("NFC", base_name)

    # Loại bỏ null byte và các ký tự điều khiển
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", normalized)

    # Chỉ giữ lại các ký tự an toàn: chữ cái, số, gạch dưới, gạch ngang, dấu chấm
    safe_name = re.sub(r"[^\w\s\.\-]", "_", cleaned).strip()

    # Xóa dấu chấm lặp hoặc dấu chấm ở đầu/cuối để tránh ẩn file hoặc đổi đuôi kép lạ
    safe_name = re.sub(r"\.{2,}", ".", safe_name).strip(".")

    if not safe_name:
        return default_name

    return safe_name[:100]


def safe_path_join(base_dir: Union[str, Path], *paths: str) -> Path:
    """
    Ghép đường dẫn an toàn tuyệt đối, chống tấn công Path Traversal (Directory Traversal).
    Ném lỗi SecurityValidationError nếu đường dẫn kết quả nằm ngoài base_dir.
    """
    base_path = Path(base_dir).resolve()

    # Chuẩn hóa các thành phần con, loại bỏ ký tự dẫn đường nguy hiểm
    sanitized_parts = []
    for p in paths:
        if not p:
            continue
        # Bỏ dấu phân cách đầu nếu có để tránh bị coi là absolute path trong Path.joinpath
        p_clean = str(p).replace("\\", "/").lstrip("/")
        sanitized_parts.append(p_clean)

    target_path = (base_path.joinpath(*sanitized_parts)).resolve()

    try:
        # Kiểm tra target_path phải là thư mục con hoặc file nằm bên trong base_path
        if not target_path.is_relative_to(base_path):
            raise SecurityValidationError(f"Phát hiện tấn công Path Traversal: đường dẫn nằm ngoài phạm vi an toàn ({target_path}).")
    except AttributeError:
        # Hỗ trợ Python cũ hơn nếu chưa có is_relative_to
        try:
            target_path.relative_to(base_path)
        except ValueError:
            raise SecurityValidationError(f"Phát hiện tấn công Path Traversal: đường dẫn nằm ngoài phạm vi an toàn ({target_path}).")

    return target_path


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Kiểm tra độ mạnh mật khẩu theo chính sách an ninh OWASP:
    - Độ dài tối thiểu 8 ký tự.
    - Chứa ít nhất một chữ cái (a-z, A-Z).
    - Chứa ít nhất một chữ số (0-9).
    """
    if not password or len(password) < 8:
        return False, "Mật khẩu phải có tối thiểu 8 ký tự."

    has_letter = bool(re.search(r"[a-zA-Z]", password))
    has_digit = bool(re.search(r"\d", password))

    if not has_letter or not has_digit:
        return False, "Mật khẩu phải bao gồm cả chữ cái và chữ số."

    return True, "Mật khẩu đạt tiêu chuẩn an toàn."


def validate_input_text(text: str, max_chars: int = 100000) -> str:
    """
    Kiểm tra và chuẩn hóa văn bản đầu vào:
    - Loại bỏ null bytes (\x00).
    - Giới hạn độ dài ký tự tối đa.
    """
    if "\x00" in text:
        raise SecurityValidationError("Văn bản chứa ký tự không hợp lệ (null byte).")

    cleaned = text.strip()
    if len(cleaned) > max_chars:
        raise SecurityValidationError(f"Văn bản vượt quá giới hạn tối đa {max_chars:,} ký tự.")

    return cleaned
