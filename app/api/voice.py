"""Voice API routes for Twilio webhook handling."""

import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.services import CustomerService
from app.voice.session_manager import SessionManager

router = APIRouter()
logger = logging.getLogger(__name__)

# Global session manager
session_manager = SessionManager()


@router.post("/incoming-call")
async def handle_incoming_call(request: Request, db: Session = Depends(get_db)):
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

    # Lookup customer history for returning-customer recognition
    history = customer_service.get_customer_history(customer.id)

    # Initialize conversation session with history context
    session = await session_manager.create_session(
        call_sid=call_sid, customer_phone=caller, customer_id=customer.id
    )

    # Inject returning customer context into session key_facts
    if customer.full_name:
        session.scheduling.customer_name = customer.full_name
        session.add_fact(f"Returning customer: {customer.full_name}")
    if customer.email:
        session.scheduling.customer_email = customer.email
    if customer.zip_code:
        session.scheduling.customer_zip_code = customer.zip_code

    for item in history:
        session.add_fact(item)

    # Build WebSocket URL for media streaming
    host = request.headers.get("host", "localhost")
    ws_url = f"wss://{host}/voice/media-stream/{call_sid}"

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
async def handle_call_status(request: Request, db: Session = Depends(get_db)):
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


@router.post("/transfer/{call_sid}")
async def transfer_call(call_sid: str, request: Request):
    """
    Transfer a call to a live human agent.

    Returns TwiML that bridges the caller to the support line.
    """
    body = (
        await request.json()
        if request.headers.get("content-type") == "application/json"
        else {}
    )
    department = body.get("department", "general_support")
    urgency = body.get("urgency", "normal")

    session = await session_manager.get_session(call_sid)
    summary = ""
    if session:
        summary = "; ".join(session.key_facts[-5:]) if session.key_facts else ""

    logger.info(
        f"Transfer call {call_sid} to {department} "
        f"(urgency={urgency}) summary={summary!r}"
    )

    department_numbers = {
        "general_support": "+15104025551",
        "scheduling": "+15104025551",
        "technical": "+15104025551",
        "emergency": "+15104025551",
    }
    target = department_numbers.get(department, "+15104025551")

    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="Polly.Joanna">
        Please hold while I connect you with a specialist.
    </Say>
    <Dial callerId="{settings.twilio_phone_number}">
        {target}
    </Dial>
</Response>"""

    return Response(content=twiml, media_type="application/xml")


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
        "scheduling": session.scheduling.model_dump(),
    }


@router.post("/session/{call_sid}/context")
async def add_session_context(call_sid: str, request: Request):
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
