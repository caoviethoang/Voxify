"""Cơ chế bảo vệ bản quyền, chống lạm dụng & kiểm tra danh sách người nổi tiếng / chính trị gia."""
import re
import unicodedata
from typing import Optional, Tuple

# Danh sách chuẩn hóa tên chính trị gia, lãnh đạo quốc gia & thế giới
BLOCKED_POLITICIANS = {
    # Việt Nam
    "ho chi minh",
    "bac ho",
    "chu tich ho chi minh",
    "nguyen phu trong",
    "pham minh chinh",
    "to lam",
    "nguyen xuan phuc",
    "vo van thuong",
    "luong cuong",
    "tran dai quang",
    "nong duc manh",
    "nguyen tan dung",
    "truong tan sang",
    "phan van khai",
    "le kha phieu",
    "do muoi",
    "nguyen van linh",
    "le duan",
    "truong chinh",
    "vo nguyen giap",
    "dai tuong vo nguyen giap",
    "pham van dong",
    # Quốc tế
    "donald trump",
    "barack obama",
    "joe biden",
    "vladimir putin",
    "xi jinping",
    "tap can binh",
    "kim jong un",
    "emmanuel macron",
    "justin trudeau",
    "boris johnson",
    "rishi sunak",
    "keir starmer",
    "volodymyr zelenskyy",
    "zelensky",
    "george w bush",
    "bill clinton",
    "angela merkel",
    "narendra modi",
    "benjamin netanyahu",
    "hillary clinton",
    "kamala harris",
}

# Danh sách nghệ sĩ, người nổi tiếng, KOL có tầm ảnh hưởng lớn
BLOCKED_CELEBRITIES = {
    # Nghệ sĩ Việt Nam
    "son tung",
    "son tung mtp",
    "m-tp",
    "tran thanh",
    "hoai linh",
    "dam vinh hung",
    "viet huong",
    "ho ngoc ha",
    "my tam",
    "den vau",
    "quang le",
    "phi nhung",
    "xuan bac",
    "tu long",
    "cong ly",
    "van dung",
    "lai van sam",
    "quang minh",
    "truong giang",
    "nha phuong",
    "jack 97",
    "j97",
    "trinh tran phuong tuan",
    "karik",
    "suboi",
    "wowy",
    "justatee",
    "soobin hoang son",
    "mono",
    "chi pu",
    "ha anh tuan",
    # Quốc tế
    "taylor swift",
    "elon musk",
    "bill gates",
    "mark zuckerberg",
    "steve jobs",
    "cristiano ronaldo",
    "ronaldo",
    "messi",
    "lionel messi",
    "mrbeast",
    "pewdiepie",
    "ariana grande",
    "justin bieber",
    "selena gomez",
    "drake",
    "eminem",
    "kanye west",
    "morgan freeman",
    "david beckham",
}

VALID_ABUSE_REASONS = {
    "celebrity_impersonation": "Giả mạo người nổi tiếng hoặc chính trị gia",
    "no_consent": "Sử dụng giọng nói khi chưa có sự đồng ý của chủ giọng",
    "copyright": "Vi phạm bản quyền sở hữu trí tuệ",
    "defamation": "Phỉ báng, bôi nhọ hoặc phát tán tin giả (Deepfake)",
    "other": "Lý do khác",
}


def normalize_text(text: str) -> str:
    """Loại bỏ dấu tiếng Việt, ký tự đặc biệt, chuyển về chữ thường chuẩn ASCII."""
    if not text:
        return ""
    # Chuyển unicode decomposed để tách dấu
    nfkd_form = unicodedata.normalize("NFKD", text)
    # Loại bỏ combining characters (dấu tiếng Việt)
    no_accents = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Thay 'đ'/'Đ' thủ công
    no_accents = no_accents.replace("đ", "d").replace("Đ", "d")
    # Thay ký tự đặc biệt bằng khoảng trắng
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", no_accents)
    return " ".join(clean.lower().split())


def check_voice_name_against_blocklist(
    name: str, description: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Kiểm tra tên giọng hoặc mô tả có chứa tên người nổi tiếng / chính trị gia bị cấm clone không.

    Trả về:
    - (is_blocked: bool, detected_name: Optional[str], reason: Optional[str])
    """
    combined = f"{name} {description or ''}"
    norm = normalize_text(combined)

    # 1. Kiểm tra chính trị gia
    for politician in BLOCKED_POLITICIANS:
        pattern = r"\b" + re.escape(politician) + r"\b"
        if re.search(pattern, norm):
            return (
                True,
                politician,
                f"Tên '{name}' trùng hoặc chứa tên chính trị gia/lãnh đạo quốc gia ({politician.title()}). "
                "Voxify nghiêm cấm hành vi clone giọng lãnh đạo, chính trị gia nhằm chống giả mạo Deepfake.",
            )

    # 2. Kiểm tra người nổi tiếng / nghệ sĩ
    for celebrity in BLOCKED_CELEBRITIES:
        pattern = r"\b" + re.escape(celebrity) + r"\b"
        if re.search(pattern, norm):
            return (
                True,
                celebrity,
                f"Tên '{name}' trùng hoặc chứa tên người nổi tiếng/nghệ sĩ ({celebrity.title()}). "
                "Để bảo vệ bản quyền giọng nói, bạn chỉ được clone giọng của chính mình hoặc người đã ủy quyền văn bản hợp pháp.",
            )

    return False, None, None
