"""ARQ Worker — Xử lý các job TTS nền và tác vụ hàng đợi bất đồng bộ."""
import logging
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

create_pool: Any = None
RedisSettings: Any = None

try:
    from arq import create_pool as _create_pool
    from arq.connections import RedisSettings as _RedisSettings
    create_pool = _create_pool
    RedisSettings = _RedisSettings
except ImportError:
    pass

# Cache arq redis pool connection
_arq_pool: Optional[Any] = None


async def get_arq_pool() -> Optional[Any]:
    """Lấy hoặc khởi tạo kết nối ARQ Redis pool."""
    global _arq_pool
    if _arq_pool is not None:
        return _arq_pool

    if create_pool is None or RedisSettings is None:
        return None

    settings = get_settings()
    if not settings.redis_url:
        return None

    try:
        redis_settings = RedisSettings.from_dsn(settings.redis_url)
        _arq_pool = await create_pool(redis_settings)
        return _arq_pool
    except Exception as e:
        logger.warning(f"Không thể kết nối ARQ Redis pool ({settings.redis_url}): {e}")
        return None


async def process_tts_job(ctx: dict[str, Any], job_id: int, apply_dict: bool = True) -> None:
    """
    ARQ Task: Thực thi job chuyển đổi văn bản sang giọng nói trong worker riêng biệt.
    """
    logger.info(f"[ARQ Worker] Bắt đầu xử lý Job TTS #{job_id}")
    from app.services.tts_job_service import TTSJobService
    service = TTSJobService()
    await service._execute_job_in_background(job_id=job_id, apply_dict=apply_dict)
    logger.info(f"[ARQ Worker] Hoàn tất xử lý Job TTS #{job_id}")


async def enqueue_tts_job(job_id: int, apply_dict: bool = True) -> bool:
    """
    Đẩy job vào hàng đợi ARQ nếu Redis khả dụng.
    Trả về True nếu đã đưa vào hàng đợi ARQ thành công, False nếu cần fallback sang asyncio.create_task.
    """
    pool = await get_arq_pool()
    if pool is None:
        return False

    try:
        await pool.enqueue_job("process_tts_job", job_id, apply_dict)
        logger.info(f"Đã đưa Job TTS #{job_id} vào hàng đợi ARQ Redis")
        return True
    except Exception as e:
        logger.warning(f"Lỗi khi enqueue job #{job_id} vào ARQ: {e}, chuyển sang fallback local")
        return False


async def startup(ctx: dict[str, Any]) -> None:
    """Khởi tạo tài nguyên khi ARQ worker khởi động."""
    logger.info("[ARQ Worker] Đang khởi động worker process...")
    # Pre-warm settings & kiểm tra storage
    settings = get_settings()
    logger.info(f"[ARQ Worker] TTS Provider: {settings.tts_provider}, Storage: {settings.storage_backend}")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Dọn dẹp tài nguyên khi ARQ worker dừng."""
    logger.info("[ARQ Worker] Đang dừng worker process...")


def get_redis_settings() -> Any:
    """Khởi tạo RedisSettings từ cấu hình."""
    if RedisSettings is not None:
        settings = get_settings()
        if settings.redis_url:
            return RedisSettings.from_dsn(settings.redis_url)
    return None


class WorkerSettings:
    """
    Cấu hình cho ARQ CLI worker:
    Chạy bằng lệnh: python -m arq app.workers.worker.WorkerSettings
    """
    functions = [process_tts_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 600  # 10 phút cho các file TTS lớn
    keep_result = 3600
