"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.core.logging import setup_logging
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
    voices_router,
)
from app.routes.history import cleanup_old_generations
from app.schemas.auth import UserOut

settings = get_settings()
setup_logging("DEBUG" if settings.debug else "INFO")
logger = logging.getLogger("app.main")

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

    # Warmup cache danh sách giọng đọc
    try:
        tts_service = get_tts_service()
        await tts_service.get_voices()
        logger.info("Cache giọng đọc sẵn sàng.")
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

# CORS — cho phép frontend Vite dev server (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok", "app": settings.app_name, "version": "2.0.0"}


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
