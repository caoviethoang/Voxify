"""Tests cho ARQ Background Worker và Queue Dispatching."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.worker import (
    WorkerSettings,
    enqueue_tts_job,
    get_arq_pool,
    get_redis_settings,
    process_tts_job,
    shutdown,
    startup,
)


@pytest.mark.asyncio
async def test_process_tts_job():
    with patch("app.services.tts_job_service.TTSJobService._execute_job_in_background", new_callable=AsyncMock) as mock_exec:
        await process_tts_job({"job_id": 10}, job_id=10, apply_dict=True)
        mock_exec.assert_awaited_once_with(job_id=10, apply_dict=True)


@pytest.mark.asyncio
async def test_enqueue_tts_job_success():
    mock_pool = MagicMock()
    mock_pool.enqueue_job = AsyncMock(return_value=None)

    with patch("app.workers.worker.get_arq_pool", new_callable=AsyncMock) as mock_get_pool:
        mock_get_pool.return_value = mock_pool

        result = await enqueue_tts_job(job_id=42, apply_dict=False)
        assert result is True
        mock_pool.enqueue_job.assert_awaited_once_with("process_tts_job", 42, False)


@pytest.mark.asyncio
async def test_enqueue_tts_job_failures():
    # 1. Khi không có pool
    with patch("app.workers.worker.get_arq_pool", new_callable=AsyncMock) as mock_get_pool:
        mock_get_pool.return_value = None
        result = await enqueue_tts_job(job_id=99)
        assert result is False

    # 2. Khi enqueue ném Exception
    mock_pool = MagicMock()
    mock_pool.enqueue_job = AsyncMock(side_effect=RuntimeError("Redis connection lost"))
    with patch("app.workers.worker.get_arq_pool", new_callable=AsyncMock) as mock_get_pool:
        mock_get_pool.return_value = mock_pool
        result = await enqueue_tts_job(job_id=99)
        assert result is False


@pytest.mark.asyncio
async def test_worker_lifecycle():
    ctx = {}
    await startup(ctx)
    await shutdown(ctx)


def test_worker_settings():
    assert process_tts_job in WorkerSettings.functions
    assert WorkerSettings.max_jobs == 10
    assert WorkerSettings.job_timeout == 600

    # get_redis_settings
    with patch("app.workers.worker.RedisSettings") as mock_rs, patch("app.workers.worker.get_settings") as mock_settings:
        mock_settings.return_value.redis_url = "redis://localhost:6379/1"
        get_redis_settings()
        mock_rs.from_dsn.assert_called_with("redis://localhost:6379/1")


@pytest.mark.asyncio
async def test_get_arq_pool_logic():
    # Khi create_pool là None
    with patch("app.workers.worker.create_pool", None), patch("app.workers.worker._arq_pool", None):
        pool = await get_arq_pool()
        assert pool is None
