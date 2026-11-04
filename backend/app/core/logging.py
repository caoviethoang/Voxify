"""Cấu hình logging tập trung."""
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Thiết lập logging format nhất quán cho toàn ứng dụng."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
