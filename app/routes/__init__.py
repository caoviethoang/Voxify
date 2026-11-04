from app.routes.config import router as config_router
from app.routes.tts import router as tts_router
from app.routes.voices import router as voices_router

__all__ = ["tts_router", "voices_router", "config_router"]
