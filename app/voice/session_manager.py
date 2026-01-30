"""Session management for voice conversations."""

import logging
from typing import Dict, Optional
from datetime import datetime

from app.schemas.conversation import ConversationState, ConversationPhase

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages conversation sessions for active calls.
    
    In production, this would use Redis or another distributed cache.
    For this implementation, we use an in-memory store.
    """
    
    def __init__(self):
        self._sessions: Dict[str, ConversationState] = {}
    
    async def create_session(
        self,
        call_sid: str,
        customer_phone: str,
        customer_id: Optional[int] = None
    ) -> ConversationState:
        """Create a new conversation session."""
        session = ConversationState(
            call_sid=call_sid,
            customer_phone=customer_phone,
            customer_id=customer_id,
            started_at=datetime.utcnow(),
            phase=ConversationPhase.GREETING
        )
        
        self._sessions[call_sid] = session
        logger.info(f"Created session for call {call_sid}")
        
        return session
    
    async def get_session(self, call_sid: str) -> Optional[ConversationState]:
        """Get an existing session by call SID."""
        return self._sessions.get(call_sid)
    
    async def update_session(self, session: ConversationState) -> None:
        """Update a session."""
        session.update_interaction()
        self._sessions[session.call_sid] = session
    
    async def end_session(self, call_sid: str) -> Optional[ConversationState]:
        """End and remove a session."""
        session = self._sessions.pop(call_sid, None)
        if session:
            logger.info(f"Ended session for call {call_sid}")
        return session
    
    async def get_active_sessions(self) -> Dict[str, ConversationState]:
        """Get all active sessions."""
        return self._sessions.copy()
    
    async def transition_phase(
        self,
        call_sid: str,
        new_phase: ConversationPhase
    ) -> Optional[ConversationState]:
        """Transition a session to a new phase."""
        session = await self.get_session(call_sid)
        if session:
            old_phase = session.phase
            session.phase = new_phase
            await self.update_session(session)
            logger.info(
                f"Session {call_sid}: {old_phase.value} -> {new_phase.value}"
            )
        return session
