"""Router tổng hợp cho Public API v1 (/v1/...)."""
from fastapi import APIRouter

from app.routes.v1.credits import router as credits_router
from app.routes.v1.jobs import router as jobs_router
from app.routes.v1.tts import router as tts_router
from app.routes.v1.voices import router as voices_router

v1_router = APIRouter(prefix="/v1", tags=["Public API v1"])

v1_router.include_router(voices_router)
v1_router.include_router(tts_router)
v1_router.include_router(jobs_router)
v1_router.include_router(credits_router)

__all__ = ["v1_router"]
