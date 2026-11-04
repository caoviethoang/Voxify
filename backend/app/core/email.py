"""Dịch vụ gửi email (hỗ trợ SMTP hoặc in link ra console khi dev)."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, token: str) -> None:
    """Gửi link đặt lại mật khẩu (hết hạn sau 30 phút)."""
    settings = get_settings()
    reset_url = f"{settings.frontend_url}/reset-password?token={token}"

    subject = f"[{settings.app_name}] Yêu cầu đặt lại mật khẩu"
    body_text = f"""Xin chào,

Chúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản {to_email}.
Vui lòng nhấn vào liên kết bên dưới để tạo mật khẩu mới (liên kết có hiệu lực trong 30 phút):

{reset_url}

Nếu bạn không yêu cầu hành động này, vui lòng bỏ qua email này.

Trân trọng,
Đội ngũ {settings.app_name}
"""
    _send_email_or_log(to_email, subject, body_text, reset_url, "RESET PASSWORD LINK")


def send_verification_email(to_email: str, token: str) -> None:
    """Gửi link xác thực tài khoản email."""
    settings = get_settings()
    verify_url = f"{settings.frontend_url}/verify-email?token={token}"

    subject = f"[{settings.app_name}] Xác thực địa chỉ email"
    body_text = f"""Xin chào,

Cảm ơn bạn đã đăng ký tài khoản tại {settings.app_name}.
Vui lòng nhấn vào liên kết bên dưới để xác thực địa chỉ email của bạn:

{verify_url}

Trân trọng,
Đội ngũ {settings.app_name}
"""
    _send_email_or_log(to_email, subject, body_text, verify_url, "VERIFY EMAIL LINK")


def _send_email_or_log(
    to_email: str, subject: str, body: str, action_url: str, log_tag: str
) -> None:
    """Gửi email qua SMTP nếu có cấu hình, nếu không thì in ra console."""
    settings = get_settings()

    if not settings.smtp_host:
        # Dev mode: in link trực tiếp ra console
        print("\n" + "=" * 65)
        print(f"📧 [DEV EMAIL SIMULATOR] Gửi tới: {to_email}")
        print(f"   Tiêu đề: {subject}")
        print(f"   🔗 {log_tag}: {action_url}")
        print("=" * 65 + "\n", flush=True)
        logger.info(f"Dev Email ({log_tag}) cho {to_email}: {action_url}")
        return

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.emails_from
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            if settings.smtp_user and settings.smtp_password:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info(f"Đã gửi email thành công tới {to_email}")
    except Exception as e:
        logger.error(f"Lỗi khi gửi email qua SMTP: {e}")
        # In fallback link ra console để không block dev/test
        print(f"\n[FALLBACK EMAIL] {log_tag} for {to_email}: {action_url}\n", flush=True)
