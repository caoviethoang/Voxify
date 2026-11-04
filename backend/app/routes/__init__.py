from app.routes.auth import router as auth_router
from app.routes.config import router as config_router
from app.routes.credits import router as credit_router
from app.routes.tts import router as tts_router
from app.routes.voices import router as voices_router

__all__ = ["auth_router", "config_router", "credit_router", "tts_router", "voices_router"]
