"""Tích hợp giám sát lỗi runtime với Sentry (Issue #16)."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def init_sentry(sentry_dsn: Optional[str] = None, environment: str = "production") -> bool:
    """
    Khởi tạo Sentry SDK để giám sát và cảnh báo runtime exception.
    Nếu sentry_dsn để trống hoặc thư viện sentry_sdk chưa cài đặt, hệ thống sẽ bỏ qua an toàn.
    """
    if not sentry_dsn or not sentry_dsn.strip():
        logger.debug("Sentry DSN không được cấu hình, bỏ qua khởi tạo Sentry.")
        return False

    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=sentry_dsn.strip(),
            environment=environment,
            traces_sample_rate=0.1,
            send_default_pii=False,
        )
        logger.info("Đã khởi tạo thành công Sentry SDK monitoring.")
        return True
    except ImportError:
        logger.warning("Thư viện 'sentry-sdk' chưa được cài đặt. Bỏ qua giám sát Sentry.")
        return False
    except Exception as e:
        logger.warning(f"Không thể khởi tạo Sentry: {e}")
        return False
