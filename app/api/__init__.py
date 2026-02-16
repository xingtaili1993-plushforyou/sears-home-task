"""API routes for the Voice AI Diagnostic Agent."""

from app.api.dashboard import router as dashboard_router
from app.api.routes import router as api_router
from app.api.upload import router as upload_router
from app.api.voice import router as voice_router

__all__ = ["api_router", "voice_router", "upload_router", "dashboard_router"]
