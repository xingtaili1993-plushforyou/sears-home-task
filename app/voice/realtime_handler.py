"""Handler for OpenAI Realtime API WebSocket connections."""

import json
import base64
import logging
import asyncio
from typing import Optional, Callable, Any
import websockets

from app.config import settings
from app.voice.agent import VoiceAgent
from app.voice.session_manager import SessionManager
from app.schemas.conversation import ConversationState, ConversationPhase

logger = logging.getLogger(__name__)

OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime"


class RealtimeHandler:
    """
    Handles the real-time voice conversation using OpenAI's Realtime API.
    
    This bridges Twilio's media streams with OpenAI's Realtime API for
    low-latency voice-to-voice conversation.
    """
    
    def __init__(
        self,
        session_manager: SessionManager,
        agent: VoiceAgent
    ):
        self.session_manager = session_manager
        self.agent = agent
        self.openai_ws: Optional[websockets.WebSocketClientProtocol] = None
        self.session: Optional[ConversationState] = None
        self.stream_sid: Optional[str] = None
    
    async def handle_twilio_connection(
        self,
        twilio_ws,
        call_sid: str
    ):
        """
        Handle a Twilio WebSocket connection for media streaming.
        
        This method:
        1. Connects to OpenAI's Realtime API
        2. Sets up the conversation session
        3. Bridges audio between Twilio and OpenAI
        """
        self.session = await self.session_manager.get_session(call_sid)
        
        if not self.session:
            logger.error(f"No session found for call {call_sid}")
            await twilio_ws.close()
            return
        
        try:
            # Connect to OpenAI Realtime API
            await self._connect_to_openai()
            
            # Configure the session
            await self._configure_openai_session()
            
            # Send initial greeting
            await self._send_initial_greeting()
            
            # Create tasks for bidirectional streaming
            tasks = [
                asyncio.create_task(self._receive_from_twilio(twilio_ws)),
                asyncio.create_task(self._receive_from_openai(twilio_ws)),
            ]
            
            # Wait for either task to complete (connection closed)
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            logger.error(f"Error in realtime handler: {str(e)}")
        finally:
            await self._cleanup()
    
    async def _connect_to_openai(self):
        """Establish WebSocket connection to OpenAI Realtime API."""
        headers = [
            ("Authorization", f"Bearer {settings.openai_api_key}"),
            ("OpenAI-Beta", "realtime=v1")
        ]
        
        url = f"{OPENAI_REALTIME_URL}?model={settings.openai_realtime_model}"
        
        self.openai_ws = await websockets.connect(
            url,
            additional_headers=headers,
            ping_interval=20,
            ping_timeout=10
        )
        
        logger.info("Connected to OpenAI Realtime API")
    
    async def _configure_openai_session(self):
        """Configure the OpenAI Realtime session."""
        session_config = {
            "type": "session.update",
            "session": {
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "voice": settings.openai_voice,
                "instructions": self.agent.get_system_prompt(self.session),
                "modalities": ["text", "audio"],
                "temperature": 0.7,
                "tools": self.agent.get_tools(),
                "tool_choice": "auto"
            }
        }
        
        await self.openai_ws.send(json.dumps(session_config))
        logger.info("OpenAI session configured")
    
    async def _send_initial_greeting(self):
        """Send the initial greeting to start the conversation."""
        greeting = self.agent.get_initial_message()
        
        # Create a conversation item with the greeting
        event = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "assistant",
                "content": [
                    {
                        "type": "input_text",
                        "text": greeting
                    }
                ]
            }
        }
        
        await self.openai_ws.send(json.dumps(event))
        
        # Request a response to generate audio for the greeting
        await self.openai_ws.send(json.dumps({
            "type": "response.create",
            "response": {
                "modalities": ["audio", "text"]
            }
        }))
    
    async def _receive_from_twilio(self, twilio_ws):
        """Receive audio from Twilio and forward to OpenAI."""
        try:
            while True:
                # FastAPI WebSocket uses receive_text() instead of async for
                message = await twilio_ws.receive_text()
                data = json.loads(message)
                
                if data["event"] == "start":
                    self.stream_sid = data["start"]["streamSid"]
                    logger.info(f"Twilio stream started: {self.stream_sid}")
                
                elif data["event"] == "media":
                    # Forward audio to OpenAI
                    audio_data = data["media"]["payload"]
                    
                    audio_event = {
                        "type": "input_audio_buffer.append",
                        "audio": audio_data
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
                    # Forward audio to Twilio
                    audio_data = event.get("delta", "")
                    
                    if audio_data and self.stream_sid:
                        media_message = {
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {
                                "payload": audio_data
                            }
                        }
                        # FastAPI WebSocket uses send_text() instead of send()
                        await twilio_ws.send_text(json.dumps(media_message))
                
                elif event_type == "response.audio_transcript.done":
                    # Log the assistant's response
                    transcript = event.get("transcript", "")
                    logger.info(f"Assistant: {transcript[:100]}...")
                
                elif event_type == "conversation.item.input_audio_transcription.completed":
                    # Log user's speech
                    transcript = event.get("transcript", "")
                    logger.info(f"User: {transcript[:100]}...")
                    
                    # Update session
                    if self.session:
                        self.session.add_fact(f"User said: {transcript[:200]}")
                        self.session.update_interaction()
                
                elif event_type == "response.function_call_arguments.done":
                    # Handle tool calls
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
    
    async def _handle_tool_call(self, event: dict, twilio_ws):
        """Handle a function/tool call from OpenAI."""
        try:
            call_id = event.get("call_id")
            name = event.get("name")
            arguments = json.loads(event.get("arguments", "{}"))
            
            logger.info(f"Tool call: {name}({arguments})")
            
            # Execute the tool
            result = await self.agent.execute_tool(name, arguments, self.session)
            
            # Send the result back to OpenAI
            tool_result = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result
                }
            }
            
            await self.openai_ws.send(json.dumps(tool_result))
            
            # Request a response based on the tool result
            await self.openai_ws.send(json.dumps({
                "type": "response.create"
            }))
            
        except Exception as e:
            logger.error(f"Error handling tool call: {str(e)}")
    
    async def _cleanup(self):
        """Clean up connections."""
        if self.openai_ws:
            try:
                await self.openai_ws.close()
            except:
                pass
        
        if self.session:
            await self.session_manager.update_session(self.session)
