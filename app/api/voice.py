"""Voice API routes for Twilio webhook handling."""

import json
import logging
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.services import CustomerService
from app.voice.session_manager import SessionManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Global session manager
session_manager = SessionManager()


@router.post("/incoming-call")
async def handle_incoming_call(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle incoming Twilio call webhook.
    
    This is the entry point for all inbound calls. It returns TwiML
    to connect the call to our WebSocket handler for real-time voice AI.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    caller = form_data.get("From", "")
    called = form_data.get("To", "")
    
    logger.info(f"Incoming call: {call_sid} from {caller} to {called}")
    
    # Get or create customer record
    customer_service = CustomerService(db)
    customer = customer_service.get_or_create_customer(caller)
    
    # Initialize conversation session
    await session_manager.create_session(
        call_sid=call_sid,
        customer_phone=caller,
        customer_id=customer.id
    )
    
    # Build WebSocket URL for media streaming
    ws_url = f"wss://{request.headers.get('host', 'localhost')}/voice/media-stream/{call_sid}"
    
    # Return TwiML to connect to WebSocket
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{ws_url}">
            <Parameter name="call_sid" value="{call_sid}" />
            <Parameter name="customer_phone" value="{caller}" />
        </Stream>
    </Connect>
</Response>"""
    
    return Response(content=twiml, media_type="application/xml")


@router.post("/call-status")
async def handle_call_status(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle call status updates from Twilio."""
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "")
    call_status = form_data.get("CallStatus", "")
    
    logger.info(f"Call {call_sid} status: {call_status}")
    
    if call_status in ["completed", "busy", "failed", "no-answer", "canceled"]:
        # Clean up the session
        await session_manager.end_session(call_sid)
    
    return PlainTextResponse("OK")


@router.api_route("/media-stream/{call_sid}", methods=["GET", "POST"])
async def media_stream_endpoint(call_sid: str, request: Request):
    """
    Placeholder for WebSocket media stream.
    The actual WebSocket handling is done in the main app.
    """
    return PlainTextResponse("WebSocket endpoint - use ws:// or wss://")


@router.get("/session/{call_sid}")
async def get_session_info(call_sid: str):
    """Get information about an active call session."""
    session = await session_manager.get_session(call_sid)
    if not session:
        return {"error": "Session not found"}
    
    return {
        "call_sid": session.call_sid,
        "customer_phone": session.customer_phone,
        "phase": session.phase.value,
        "turn_count": session.turn_count,
        "diagnostic": session.diagnostic.model_dump(),
        "scheduling": session.scheduling.model_dump()
    }


@router.post("/session/{call_sid}/context")
async def add_session_context(
    call_sid: str,
    request: Request
):
    """Add context to an active session (for testing/debugging)."""
    body = await request.json()
    
    session = await session_manager.get_session(call_sid)
    if not session:
        return {"error": "Session not found"}
    
    # Update session with provided context
    if "appliance_type" in body:
        session.diagnostic.appliance_type = body["appliance_type"]
    if "symptoms" in body:
        session.diagnostic.additional_symptoms.extend(body["symptoms"])
    if "zip_code" in body:
        session.scheduling.customer_zip_code = body["zip_code"]
    
    await session_manager.update_session(session)
    
    return {"message": "Context updated", "session": session.model_dump()}
