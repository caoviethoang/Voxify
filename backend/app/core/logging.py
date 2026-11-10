"""Cấu hình logging tập trung và Structured JSON Logging (Issue #16)."""
import json
import logging
import sys
from datetime import UTC, datetime


class JSONLogFormatter(logging.Formatter):
    """
    Formatter xuất log dạng JSON có cấu trúc (Structured Logging)
    chuẩn hóa cho hệ thống giám sát tập trung (ELK, Loki, Datadog, CloudWatch).
    """

    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        # Hỗ trợ thêm extra attributes nếu có
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_record["user_id"] = record.user_id

        return json.dumps(log_record, ensure_ascii=False)


def setup_logging(level: str = "INFO", log_format: str = "text") -> None:
    """
    Thiết lập logging nhất quán:
    - log_format="json": Structured JSON Logging phục vụ production / containers.
    - log_format="text": Định dạng thân thiện phục vụ local dev / debugging.
    """
    root_logger = logging.getLogger()
    log_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(log_level)

    # Xóa các handler cũ nếu có
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if log_format.lower() == "json":
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )

    root_logger.addHandler(handler)
