"""FastAPI application entry point."""
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import setup_logging
from app.core.metrics import PrometheusMetricsMiddleware, metrics
from app.core.security_headers import SecurityHeadersMiddleware
from app.core.sentry import init_sentry
from app.db import create_tables
from app.dependencies import get_current_active_user, get_tts_service
from app.models.user import User
from app.routes import (
    admin_router,
    auth_router,
    config_router,
    credit_router,
    dashboard_router,
    developers_router,
    dictionary_router,
    history_router,
    payment_router,
    tts_router,
    v1_router,
    voice_clone_router,
    voice_library_router,
    voices_router,
)
from app.routes.history import cleanup_old_generations
from app.schemas.auth import UserOut

settings = get_settings()
setup_logging("DEBUG" if settings.debug else "INFO", log_format=getattr(settings, "log_format", "text"))
init_sentry(settings.sentry_dsn)
logger = logging.getLogger("app.main")
_server_start_time = time.time()

STORAGE_DIR = Path(settings.storage_path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Vòng đời ứng dụng: tạo bảng DB, warmup cache giọng đọc."""
    logger.info(f"Đang khởi động: {settings.app_name}")

    # Tạo bảng DB nếu chưa có (dev mode); production dùng alembic upgrade head
    try:
        await create_tables()
        logger.info("Đã tạo/kiểm tra bảng database.")
    except Exception as e:
        logger.warning(f"Không thể tạo bảng DB: {e}")

    # Dọn dẹp các bản ghi preview cũ khi khởi động
    try:
        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as cleanup_session:
            await cleanup_old_generations(cleanup_session)
        logger.info("Đã hoàn tất dọn dẹp bản ghi preview cũ.")
    except Exception as e:
        logger.warning(f"Không thể dọn dẹp bản ghi cũ: {e}")

    # Warmup cache danh sách giọng đọc và đồng bộ vào Thư viện Giọng (Issue #18)
    try:
        tts_service = get_tts_service()
        raw_voices = await tts_service.get_voices()
        logger.info("Cache giọng đọc sẵn sàng.")
        try:
            from app.db import AsyncSessionLocal
            from app.services.voice_library_service import VoiceLibraryService
            async with AsyncSessionLocal() as vl_session:
                await VoiceLibraryService.sync_system_voices(vl_session, raw_voices, provider="edge")
            logger.info("Đã đồng bộ giọng hệ thống vào Voice Library.")
        except Exception as vl_err:
            logger.warning(f"Không thể đồng bộ Voice Library: {vl_err}")
    except Exception as e:
        logger.warning(f"Chưa thể warmup danh sách giọng đọc: {e}")

    # Khởi tạo gói dịch vụ và mã giảm giá mặc định
    try:
        from app.db import AsyncSessionLocal
        from app.services.payment_service import PaymentService
        async with AsyncSessionLocal() as payment_session:
            await PaymentService.seed_defaults_if_empty(payment_session)
    except Exception as e:
        logger.warning(f"Không thể khởi tạo gói cước mặc định: {e}")

    port = settings.port
    print("\n" + "=" * 60)
    print(f"  🚀 {settings.app_name} đang hoạt động!")
    print(f"  ➜  API:   http://localhost:{port}/")
    print(f"  ➜  Docs:  http://localhost:{port}/docs")
    print("=" * 60 + "\n", flush=True)

    yield
    logger.info(f"Đang dừng {settings.app_name}.")


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version="2.0.0",
    lifespan=lifespan,
)

# 1. Prometheus Metrics Middleware (đo lường latency & request count)
app.add_middleware(PrometheusMetricsMiddleware)

# 2. Security Headers Middleware (CSP, HSTS, X-Frame-Options...)
app.add_middleware(SecurityHeadersMiddleware)

# 3. CORS — Cấu hình domain chuẩn bảo mật (Issue #16)
cors_allowed = list(getattr(settings, "cors_origins", []))
if settings.frontend_url and settings.frontend_url not in cors_allowed:
    cors_allowed.append(settings.frontend_url)
if "http://localhost:5173" not in cors_allowed:
    cors_allowed.append("http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handler tùy chỉnh
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]

# Đăng ký routes API
app.include_router(auth_router)
app.include_router(config_router)
app.include_router(credit_router)
app.include_router(dictionary_router)
app.include_router(voices_router)
app.include_router(voice_clone_router)
app.include_router(voice_library_router)
app.include_router(tts_router)
app.include_router(history_router)
app.include_router(payment_router)
app.include_router(dashboard_router)
app.include_router(developers_router)
app.include_router(admin_router)
app.include_router(v1_router)


@app.get("/api/me", response_model=UserOut, summary="Lấy thông tin người dùng hiện tại (alias)")
async def get_me_alias(current_user: User = Depends(get_current_active_user)):
    """API lấy thông tin người dùng và số dư credit."""
    return UserOut.model_validate(current_user)


@app.get("/health", summary="Kiểm tra trạng thái hoạt động hệ thống (Health Check)")
async def health_check():
    """Kiểm tra chi tiết tình trạng database, lưu trữ và thời gian uptime (Issue #16)."""
    db_status = "ok"
    db_latency_ms = 0.0
    t0 = time.time()
    try:
        from sqlalchemy import text

        from app.db import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_latency_ms = round((time.time() - t0) * 1000, 2)
    except Exception as e:
        db_status = f"error: {str(e)}"

    storage_writable = STORAGE_DIR.exists() and os.access(str(STORAGE_DIR), os.W_OK)
    storage_status = "writable" if storage_writable else "degraded"
    uptime = round(time.time() - _server_start_time, 2)
    is_healthy = (db_status == "ok")

    return JSONResponse(
        status_code=200 if is_healthy else 503,
        content={
            "status": "ok" if is_healthy else "unhealthy",
            "app": settings.app_name,
            "version": "2.0.0",
            "uptime_seconds": uptime,
            "database": {
                "status": db_status,
                "latency_ms": db_latency_ms,
            },
            "storage": {
                "status": storage_status,
                "path": str(STORAGE_DIR),
            },
        },
    )


@app.get("/metrics", summary="Chỉ số giám sát hệ thống chuẩn Prometheus", include_in_schema=False)
async def prometheus_metrics():
    """Xuất các chỉ số hoạt động cho Prometheus scraper thu thập (Issue #16)."""
    metrics_text = metrics.export_prometheus_text()
    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# Phục vụ file audio đã lưu
if not STORAGE_DIR.exists():
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Lỗi chưa xử lý tại {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": f"Đã xảy ra lỗi hệ thống: {str(exc)}"}},
    )
