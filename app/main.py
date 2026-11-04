from contextlib import asynccontextmanager
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.dependencies import get_tts_service
from app.routes import config_router, tts_router, voices_router

# Thiết lập ghi log
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app.main")

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Vòng đời ứng dụng: khởi tạo bộ đệm giọng nói khi khởi động."""
    logger.info(f"Đang khởi động ứng dụng: {settings.app_name}")
    try:
        # Làm ấm cache danh sách giọng đọc trong nền
        tts_service = get_tts_service()
        await tts_service.get_voices()
        logger.info("Khởi tạo cache giọng đọc hoàn tất thành công.")
    except Exception as e:
        logger.warning(f"Chưa thể nạp trước danh sách giọng đọc: {e}")
    yield
    logger.info(f"Đang dừng ứng dụng {settings.app_name}.")


app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware hỗ trợ gọi API từ các domain khác nếu cần
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các route API
app.include_router(config_router)
app.include_router(voices_router)
app.include_router(tts_router)


# Xử lý trang chủ trả về static/index.html
@app.get("/", include_in_schema=False)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse(
            status_code=404,
            content={"detail": "Không tìm thấy giao diện static/index.html"},
        )
    return FileResponse(index_file)


# Gắn thư mục tĩnh
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Xử lý lỗi toàn cục thân thiện
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Lỗi chưa xử lý tại {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Đã xảy ra lỗi hệ thống: {str(exc)}"},
    )
