"""Hệ thống đo lường và giám sát tích hợp chuẩn Prometheus (Issue #16)."""
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class MetricsRegistry:
    """
    Registry thu thập và xuất chỉ số Prometheus (OpenMetrics / Prometheus text 0.0.4).
    Thread-safe, hiệu năng cao và độc lập không phụ thuộc thư viện ngoài nặng nề.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        # Counters: {name: {(label_key, label_val): count}}
        self._counters: Dict[str, Dict[Tuple[Tuple[str, str], ...], float]] = defaultdict(lambda: defaultdict(float))
        # Gauges: {name: {(label_key, label_val): value}}
        self._gauges: Dict[str, Dict[Tuple[Tuple[str, str], ...], float]] = defaultdict(lambda: defaultdict(float))
        # Request durations summary/histogram
        self._duration_sum: Dict[Tuple[Tuple[str, str], ...], float] = defaultdict(float)
        self._duration_count: Dict[Tuple[Tuple[str, str], ...], int] = defaultdict(int)

    def inc_counter(self, name: str, value: float = 1.0, **labels: str) -> None:
        """Tăng giá trị counter metric."""
        label_tuple = tuple(sorted(labels.items()))
        with self._lock:
            self._counters[name][label_tuple] += value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        """Đặt giá trị gauge metric."""
        label_tuple = tuple(sorted(labels.items()))
        with self._lock:
            self._gauges[name][label_tuple] = value

    def observe_duration(self, duration: float, **labels: str) -> None:
        """Ghi nhận thời gian phản hồi HTTP request."""
        label_tuple = tuple(sorted(labels.items()))
        with self._lock:
            self._duration_sum[label_tuple] += duration
            self._duration_count[label_tuple] += 1

    def reset(self) -> None:
        """Xóa toàn bộ số liệu (phục vụ unit test)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._duration_sum.clear()
            self._duration_count.clear()

    def export_prometheus_text(self) -> str:
        """Xuất định dạng Prometheus exposition format 0.0.4."""
        lines = []

        with self._lock:
            # 1. HTTP Requests Counter
            lines.append("# HELP voxify_http_requests_total Tổng số lượt yêu cầu HTTP")
            lines.append("# TYPE voxify_http_requests_total counter")
            for label_tuple, count in self._counters["voxify_http_requests_total"].items():
                label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                lines.append(f"voxify_http_requests_total{{{label_str}}} {int(count)}")

            # 2. Security Violations Counter
            lines.append("# HELP voxify_security_violations_total Số lượng vi phạm an ninh hệ thống")
            lines.append("# TYPE voxify_security_violations_total counter")
            for label_tuple, count in self._counters["voxify_security_violations_total"].items():
                label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                lines.append(f"voxify_security_violations_total{{{label_str}}} {int(count)}")

            # 3. Content Moderation Counter
            lines.append("# HELP voxify_moderation_blocks_total Số lượt nội dung bị chặn do vi phạm kiểm duyệt")
            lines.append("# TYPE voxify_moderation_blocks_total counter")
            for label_tuple, count in self._counters["voxify_moderation_blocks_total"].items():
                label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                lines.append(f"voxify_moderation_blocks_total{{{label_str}}} {int(count)}")

            # 4. Gauges (Active jobs, etc.)
            lines.append("# HELP voxify_active_jobs_current Số lượng job xử lý đang hoạt động")
            lines.append("# TYPE voxify_active_jobs_current gauge")
            for label_tuple, val in self._gauges["voxify_active_jobs_current"].items():
                if label_tuple:
                    label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                    lines.append(f"voxify_active_jobs_current{{{label_str}}} {val}")
                else:
                    lines.append(f"voxify_active_jobs_current {val}")

            # 5. Request duration summary
            lines.append("# HELP voxify_http_request_duration_seconds Thời gian xử lý yêu cầu HTTP")
            lines.append("# TYPE voxify_http_request_duration_seconds summary")
            for label_tuple, total_time in self._duration_sum.items():
                cnt = self._duration_count[label_tuple]
                label_str = ",".join(f'{k}="{v}"' for k, v in label_tuple)
                lines.append(f"voxify_http_request_duration_seconds_sum{{{label_str}}} {total_time:.4f}")
                lines.append(f"voxify_http_request_duration_seconds_count{{{label_str}}} {cnt}")

        return "\n".join(lines) + "\n"


metrics = MetricsRegistry()


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware đo lường tần suất và độ trễ của mọi HTTP request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        path = request.url.path

        # Bỏ qua đo lường cho chính endpoint metrics để tránh nhiễu
        if path == "/metrics":
            return await call_next(request)

        # Chuẩn hóa path nhóm để tránh cardinality nổ tung (vd: /api/tts/jobs/123 -> /api/tts/jobs/{id})
        normalized_path = path
        if "/api/tts/jobs/" in path:
            normalized_path = "/api/tts/jobs/{id}"
        elif "/api/v1/jobs/" in path:
            normalized_path = "/api/v1/jobs/{id}"

        status_code = 500
        try:
            response: Response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration = time.time() - start_time
            method = request.method
            metrics.inc_counter(
                "voxify_http_requests_total",
                method=method,
                path=normalized_path,
                status=str(status_code),
            )
            metrics.observe_duration(
                duration,
                method=method,
                path=normalized_path,
            )
