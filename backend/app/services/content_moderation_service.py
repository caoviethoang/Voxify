"""Dịch vụ kiểm duyệt nội dung (Content Moderation) và tự động xử lý vi phạm (Issue #16)."""
import logging
import re
import unicodedata
from dataclasses import dataclass
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.metrics import metrics
from app.models.admin import SecurityViolationLog
from app.models.user import User

logger = logging.getLogger(__name__)


@dataclass
class ModerationResult:
    is_flagged: bool
    category: Optional[str] = None
    detected_pattern: Optional[str] = None
    reason: Optional[str] = None


# Danh mục từ khóa & mẫu vi phạm an toàn nội dung (chuẩn hóa không dấu)
PROHIBITED_CATEGORIES = {
    "VIOLENCE": {
        "reason": "Bạo lực, khủng bố, vũ khí hoặc kích động tự hại",
        "keywords": [
            "che tao bom",
            "che tao thuoc no",
            "khung bo",
            "giet nguoi",
            "cach tu tu",
            "tu sat",
            "xa sung",
            "dam chem",
            "chat dau",
            "buon ban vu khi",
            "ban vu khi quan dung",
        ],
    },
    "FRAUD_SCAM": {
        "reason": "Lừa đảo chiếm đoạt tài sản, mạo danh cơ quan công quyền hoặc OTP",
        "keywords": [
            "cung cap ma otp",
            "gui ma otp",
            "chuyen tien vao tai khoan an toan",
            "bo cong an yeu cau chuyen tien",
            "vien kiem sat yeu cau chuyen tien",
            "toa an phat nguoi nop phat gap",
            "khoa tai khoan ngan hang bam vao link",
            "rua tien",
            "chiem doat tai san",
            "lua dao qua mang",
        ],
    },
    "IMPERSONATION": {
        "reason": "Mạo danh lãnh đạo cấp cao, nguyên thủ quốc gia hoặc cơ quan tư pháp",
        "keywords": [
            "tong bi thu",
            "chu tich nuoc",
            "thu tuong chinh phu",
            "chu tich quoc hoi",
            "bo truong bo cong an",
            "ban chap hanh trung uong",
        ],
    },
    "SEXUAL_EXPLOITATION": {
        "reason": "Nội dung khiêu dâm, lạm dụng tình dục hoặc đồi trụy",
        "keywords": [
            "au dam",
            "khieu dam tre em",
            "quay len phong tam",
            "mua ban trinh",
        ],
    },
}


class ContentModerationService:
    """Hệ thống kiểm duyệt văn bản tự động, bảo vệ chống lừa đảo, deepfake và bạo lực."""

    @staticmethod
    def normalize_text_for_moderation(text: str) -> str:
        """
        Chuẩn hóa văn bản:
        - Chuyển thành chữ thường.
        - Loại bỏ dấu tiếng Việt (NFD -> ASCII).
        - Xóa các ký tự đặc biệt lách luật (l.ừ.a đ.ả.o -> lua dao, b@m -> bom).
        """
        if not text:
            return ""

        lower_text = text.lower()

        # Thay thế ký tự leetspeak phổ biến
        leet_map = {"@": "a", "0": "o", "1": "i", "3": "e", "$": "s"}
        for k, v in leet_map.items():
            lower_text = lower_text.replace(k, v)

        # Khử dấu tiếng Việt
        normalized_nfd = unicodedata.normalize("NFD", lower_text)
        de_accented = "".join(c for c in normalized_nfd if unicodedata.category(c) != "Mn")
        de_accented = de_accented.replace("đ", "d").replace("Đ", "d")

        # Khử các dấu chấm/gạch nối lách luật giữa các chữ cái đơn (vd: c.h.e -> che, b.o.m -> bom)
        de_accented = re.sub(r"(?<=\b[a-z])[.\-_]+(?=[a-z]\b)", "", de_accented)

        # Thay các dấu phân cách còn lại thành khoảng trắng
        cleaned = re.sub(r"[^\w\s]", " ", de_accented)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    @classmethod
    def check_text(cls, text: str) -> ModerationResult:
        """Kiểm tra nội dung văn bản có vi phạm chính sách kiểm duyệt hay không."""
        if not text:
            return ModerationResult(is_flagged=False)

        normalized = cls.normalize_text_for_moderation(text)
        padded_norm = f" {normalized} "

        for category, data in PROHIBITED_CATEGORIES.items():
            keywords: List[str] = data["keywords"]  # type: ignore[assignment]
            reason: str = str(data["reason"])
            for kw in keywords:
                # Tìm kiếm theo ranh giới từ hoặc cụm từ
                pattern = rf"\b{re.escape(kw)}\b"
                if re.search(pattern, normalized) or f" {kw} " in padded_norm:
                    return ModerationResult(
                        is_flagged=True,
                        category=category,
                        detected_pattern=kw,
                        reason=reason,
                    )

        return ModerationResult(is_flagged=False)

    @classmethod
    async def check_and_enforce(
        cls,
        db: AsyncSession,
        text: str,
        user: Optional[User] = None,
        ip_address: Optional[str] = None,
    ) -> ModerationResult:
        """
        Kiểm tra và thực thi hình phạt:
        - Nếu vi phạm: Ghi log SecurityViolationLog.
        - Tăng số lần vi phạm của user (violation_count).
        - Khóa tài khoản vĩnh viễn nếu vi phạm đến lần thứ 3.
        - Ném HTTP 400 hoặc 403.
        """
        result = cls.check_text(text)
        if not result.is_flagged:
            return result

        category = result.category or "OTHER"
        action_taken = "blocked"

        metrics.inc_counter("voxify_moderation_blocks_total", category=category)

        # Tạo snippet an toàn lưu log (tối đa 150 ký tự)
        snippet = (text[:150] + "...") if len(text) > 150 else text

        if user:
            user.violation_count = (user.violation_count or 0) + 1
            if user.violation_count >= 3:
                user.is_banned = True
                user.is_active = False
                user.ban_reason = (
                    f"Tài khoản bị khóa tự động do vi phạm kiểm duyệt nội dung 3 lần: {result.reason}"
                )
                action_taken = "account_banned"
            else:
                action_taken = "warned"

        metrics.inc_counter(
            "voxify_security_violations_total",
            violation_type="content_moderation",
            action=action_taken,
        )

        violation_log = SecurityViolationLog(
            user_id=user.id if user else None,
            ip_address=ip_address,
            violation_type="content_moderation",
            category=category,
            snippet=snippet,
            action_taken=action_taken,
            details=f"Phát hiện mẫu vi phạm: '{result.detected_pattern}' - {result.reason}",
        )
        db.add(violation_log)
        await db.commit()

        if user and user.is_banned:
            logger.warning(
                f"Đã tự động khóa tài khoản user {user.id} ({user.email}) sau 3 lần vi phạm kiểm duyệt."
            )
            raise HTTPException(
                status_code=403,
                detail="Tài khoản của bạn đã bị khóa do vi phạm chính sách kiểm duyệt an toàn nội dung nhiều lần.",
            )

        warning_info = f" Cảnh báo vi phạm: {user.violation_count}/3." if user else ""
        raise HTTPException(
            status_code=400,
            detail=f"Nội dung bị từ chối do vi phạm quy tắc an toàn ({result.reason}).{warning_info}",
        )
