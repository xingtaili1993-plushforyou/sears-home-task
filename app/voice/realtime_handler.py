"""Handler for OpenAI Realtime API WebSocket connections."""

import asyncio
import json
import logging
from typing import Any, Optional

import websockets

from app.config import settings
from app.schemas.conversation import ConversationPhase, ConversationState
from app.voice.agent import VoiceAgent
from app.voice.session_manager import SessionManager

logger = logging.getLogger(__name__)

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"

# Global set of dashboard WebSocket connections (populated by the dashboard endpoint)
dashboard_connections: set = set()


class RealtimeHandler:
    """
    Handles the real-time voice conversation using OpenAI's Realtime API.

    Bridges Twilio's media streams with OpenAI's Realtime API for
    low-latency voice-to-voice conversation.
    """

    def __init__(self, session_manager: SessionManager, agent: VoiceAgent):
        self.session_manager = session_manager
        self.agent = agent
        self.openai_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session: Optional[ConversationState] = None
        self.stream_sid: Optional[str] = None

    # ------------------------------------------------------------------
    # Broadcast helpers (for live dashboard)
    # ------------------------------------------------------------------

    async def _broadcast(self, event: dict) -> None:
        """Send an event to all connected dashboard clients."""
        if not dashboard_connections:
            return
        payload = json.dumps(event)
        stale = set()
        for ws in dashboard_connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.add(ws)
        dashboard_connections.difference_update(stale)

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    async def handle_twilio_connection(self, twilio_ws, call_sid: str):
        """Handle a Twilio WebSocket connection for media streaming."""
        self.session = await self.session_manager.get_session(call_sid)

        if not self.session:
            logger.error(f"No session found for call {call_sid}")
            await twilio_ws.close()
            return

        await self._broadcast({"type": "call_started", "call_sid": call_sid})

        try:
            await self._connect_to_openai()
            await self._configure_openai_session()
            await self._send_initial_greeting()

            tasks = [
                asyncio.create_task(self._receive_from_twilio(twilio_ws)),
                asyncio.create_task(self._receive_from_openai(twilio_ws)),
            ]
            done, pending = await asyncio.wait(
                tasks, return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except Exception as e:
            logger.error(f"Error in realtime handler: {str(e)}")
        finally:
            await self._broadcast({"type": "call_ended", "call_sid": call_sid})
            await self._cleanup()

    # ------------------------------------------------------------------
    # OpenAI connection management
    # ------------------------------------------------------------------

    async def _connect_to_openai(self):
        """Establish WebSocket connection to OpenAI Realtime API."""
        headers = [
            ("Authorization", f"Bearer {settings.openai_api_key}"),
            ("OpenAI-Beta", "realtime=v1"),
        ]
        url = f"{OPENAI_REALTIME_URL}?model={settings.openai_realtime_model}"
        self.openai_ws = await websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10,
        )
        logger.info("Connected to OpenAI Realtime API")

    async def _configure_openai_session(self):
        """Configure the OpenAI Realtime session."""
        session_config = {
            "type": "session.update",
            "session": {
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.6,
                    "prefix_padding_ms": 400,
                    "silence_duration_ms": 700,
                },
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "input_audio_transcription": {"model": "whisper-1"},
                "voice": settings.openai_voice,
                "instructions": self.agent.get_system_prompt(self.session),
                "modalities": ["text", "audio"],
                "temperature": 0.6,
                "tools": self.agent.get_tools(),
                "tool_choice": "auto",
            },
        }
        await self.openai_ws.send(json.dumps(session_config))
        logger.info("OpenAI session configured")

    async def _send_initial_greeting(self):
        """
        Trigger the initial greeting.

        We inject a hidden user message so the model knows the call just
        started, then request a response.  The system prompt already
        contains the customer's history and name (if returning), so the
        model will produce the right personalised greeting on its own.
        """
        # Build a hidden context nudge the caller never hears
        if self.session and self.session.scheduling.customer_name:
            nudge = (
                f"[System: A new inbound call has just connected. "
                f"The caller is a returning customer named "
                f"{self.session.scheduling.customer_name}. "
                f"Greet them warmly by name and reference their "
                f"history if relevant. Then ask how you can help.]"
            )
        else:
            nudge = (
                "[System: A new inbound call has just connected. "
                "Greet the caller warmly and ask how you can help.]"
            )

        # Inject as a user message so the model responds to it
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [{"type": "input_text", "text": nudge}],
            },
        }
        await self.openai_ws.send(json.dumps(event))

        # Request the model to generate the greeting as audio + text
        await self.openai_ws.send(
            json.dumps(
                {
                    "type": "response.create",
                    "response": {"modalities": ["audio", "text"]},
                }
            )
        )

    # ------------------------------------------------------------------
    # Bidirectional audio streaming
    # ------------------------------------------------------------------

    async def _receive_from_twilio(self, twilio_ws):
        """Receive audio from Twilio and forward to OpenAI."""
        try:
            while True:
                message = await twilio_ws.receive_text()
                data = json.loads(message)

                if data["event"] == "start":
                    self.stream_sid = data["start"]["streamSid"]
                    logger.info(f"Twilio stream started: {self.stream_sid}")

                elif data["event"] == "media":
                    audio_data = data["media"]["payload"]
                    audio_event = {
                        "type": "input_audio_buffer.append",
                        "audio": audio_data,
                    }
                    if self.openai_ws:
                        await self.openai_ws.send(json.dumps(audio_event))

                elif data["event"] == "stop":
                    logger.info("Twilio stream stopped")
                    break

        except Exception as e:
            if "disconnect" not in str(e).lower():
                logger.error(f"Error receiving from Twilio: {str(e)}")

    async def _receive_from_openai(self, twilio_ws):
        """Receive responses from OpenAI and forward audio to Twilio."""
        try:
            async for message in self.openai_ws:
                event = json.loads(message)
                event_type = event.get("type", "")

                if event_type == "response.audio.delta":
                    audio_data = event.get("delta", "")
                    if audio_data and self.stream_sid:
                        media_message = {
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {"payload": audio_data},
                        }
                        await twilio_ws.send_text(json.dumps(media_message))

                elif event_type == "response.audio_transcript.done":
                    transcript = event.get("transcript", "")
                    logger.info(f"Assistant: {transcript[:100]}...")
                    await self._broadcast(
                        {
                            "type": "transcript",
                            "role": "assistant",
                            "text": transcript,
                            "call_sid": (self.session.call_sid if self.session else ""),
                        }
                    )

                elif (
                    event_type
                    == "conversation.item.input_audio_transcription.completed"
                ):
                    transcript = event.get("transcript", "")
                    logger.info(f"User: {transcript[:100]}...")

                    if self.session:
                        self.session.add_fact(f"User said: {transcript[:200]}")
                        self.session.update_interaction()

                    await self._broadcast(
                        {
                            "type": "transcript",
                            "role": "user",
                            "text": transcript,
                            "call_sid": (self.session.call_sid if self.session else ""),
                        }
                    )

                elif event_type == "response.function_call_arguments.done":
                    await self._handle_tool_call(event, twilio_ws)

                elif event_type == "error":
                    logger.error(f"OpenAI error: {event.get('error', {})}")

                elif event_type == "session.created":
                    logger.info("OpenAI session created")

                elif event_type == "session.updated":
                    logger.info("OpenAI session updated")

        except websockets.exceptions.ConnectionClosed:
            logger.info("OpenAI connection closed")
        except Exception as e:
            logger.error(f"Error receiving from OpenAI: {str(e)}")

    # ------------------------------------------------------------------
    # Tool call handling
    # ------------------------------------------------------------------

    async def _handle_tool_call(self, event: dict, twilio_ws):
        """Handle a function/tool call from OpenAI."""
        try:
            call_id = event.get("call_id")
            name = event.get("name")
            arguments = json.loads(event.get("arguments", "{}"))

            logger.info(f"Tool call: {name}({arguments})")

            await self._broadcast(
                {
                    "type": "tool_call",
                    "tool": name,
                    "arguments": arguments,
                    "call_sid": (self.session.call_sid if self.session else ""),
                }
            )

            result = await self.agent.execute_tool(name, arguments, self.session)

            await self._broadcast(
                {
                    "type": "tool_result",
                    "tool": name,
                    "result": result,
                    "call_sid": (self.session.call_sid if self.session else ""),
                }
            )

            tool_result = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result,
                },
            }
            await self.openai_ws.send(json.dumps(tool_result))
            await self.openai_ws.send(json.dumps({"type": "response.create"}))

            if name == "transfer_to_human" and self.session:
                asyncio.create_task(
                    self._execute_live_transfer(
                        self.session.call_sid,
                        arguments.get("department", "general_support"),
                        arguments.get("urgency", "normal"),
                    )
                )

        except Exception as e:
            logger.error(f"Error handling tool call: {str(e)}")

    # ------------------------------------------------------------------
    # Live call transfer via Twilio REST API
    # ------------------------------------------------------------------

    async def _execute_live_transfer(
        self, call_sid: str, department: str, urgency: str
    ):
        """
        Redirect the live Twilio call to a real phone number.

        Waits a few seconds so the AI can finish its goodbye message,
        then uses the Twilio REST API to update the call with TwiML
        that dials the specialist.
        """
        await asyncio.sleep(6)

        department_numbers = {
            "general_support": "+15104025551",
            "scheduling": "+15104025551",
            "technical": "+15104025551",
            "emergency": "+15104025551",
        }
        target = department_numbers.get(department, "+15104025551")

        twiml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            "<Response>"
            '<Say voice="Polly.Joanna">'
            "Please hold while I connect you with a specialist."
            "</Say>"
            f'<Dial callerId="{settings.twilio_phone_number}">'
            f"{target}"
            "</Dial>"
            "</Response>"
        )

        try:
            from twilio.rest import Client

            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            client.calls(call_sid).update(twiml=twiml)
            logger.info(
                f"Live transfer executed for {call_sid} -> {target} "
                f"(dept={department})"
            )
        except ImportError:
            logger.warning("Twilio package not installed. Live transfer skipped.")
        except Exception as e:
            logger.error(f"Failed to execute live transfer for {call_sid}: {e}")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def _cleanup(self):
        """Clean up connections."""
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except Exception:
                pass

        if self.session:
            await self.session_manager.update_session(self.session)
