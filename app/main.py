"""
SEARS Home Services - Voice AI Diagnostic Agent

Main FastAPI application entry point.
"""

import logging
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.database import init_db, get_db_context
from app.seed_data import seed_database
from app.api import api_router, voice_router, upload_router
from app.voice import VoiceAgent, RealtimeHandler
# Import the shared session_manager from voice.py
from app.api.voice import session_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global instances
voice_agent = VoiceAgent()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting SEARS Voice AI Diagnostic Agent...")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    # Seed data if needed
    with get_db_context() as db:
        seed_database(db)
    
    # Create uploads directory
    Path("uploads/images").mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Application ready at {settings.base_url}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description="""
    Voice AI system for diagnosing home appliance issues and scheduling technician visits.
    
    ## Features
    - Natural voice conversation for appliance diagnosis
    - Intelligent troubleshooting guidance
    - Automated technician scheduling
    - Image upload for visual diagnosis
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(voice_router, prefix="/voice", tags=["Voice"])
app.include_router(upload_router, tags=["Upload"])

# Static files for uploads
uploads_path = Path("uploads")
uploads_path.mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/api/health",
            "docs": "/docs",
            "voice_webhook": "/voice/incoming-call",
            "api": "/api"
        }
    }


@app.websocket("/voice/media-stream/{call_sid}")
async def websocket_media_stream(websocket: WebSocket, call_sid: str):
    """
    WebSocket endpoint for Twilio media streams.
    
    This handles real-time audio streaming between Twilio and the AI agent.
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for call: {call_sid}")
    
    try:
        # Create realtime handler for this connection
        handler = RealtimeHandler(session_manager, voice_agent)
        
        # Handle the connection
        await handler.handle_twilio_connection(websocket, call_sid)
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for call: {call_sid}")
    except Exception as e:
        logger.error(f"WebSocket error for call {call_sid}: {str(e)}")
    finally:
        # Ensure session is cleaned up
        await session_manager.end_session(call_sid)


@app.get("/voice/test")
async def test_voice_endpoint():
    """Test endpoint to verify voice configuration."""
    return {
        "twilio_configured": bool(settings.twilio_account_sid),
        "openai_configured": bool(settings.openai_api_key),
        "realtime_model": settings.openai_realtime_model,
        "voice": settings.openai_voice
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
