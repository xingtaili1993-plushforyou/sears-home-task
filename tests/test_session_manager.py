"""Tests for SessionManager."""

import pytest

from app.voice.session_manager import SessionManager
from app.schemas.conversation import ConversationPhase


class TestSessionManagerCreate:
    """Tests for creating sessions."""

    @pytest.mark.asyncio
    async def test_create_session(self, session_manager):
        """Creating a session returns a ConversationState."""
        session = await session_manager.create_session(
            call_sid="CA_test_001",
            customer_phone="+15551112222",
        )
        assert session.call_sid == "CA_test_001"
        assert session.customer_phone == "+15551112222"
        assert session.phase == ConversationPhase.GREETING

    @pytest.mark.asyncio
    async def test_create_session_with_customer_id(self, session_manager):
        """Customer id is stored when provided."""
        session = await session_manager.create_session(
            call_sid="CA_test_002",
            customer_phone="+15553334444",
            customer_id=42,
        )
        assert session.customer_id == 42


class TestSessionManagerGet:
    """Tests for retrieving sessions."""

    @pytest.mark.asyncio
    async def test_get_session_exists(self, session_manager):
        """Retrieving an existing session returns it."""
        await session_manager.create_session("CA_get", "+15550000000")
        session = await session_manager.get_session("CA_get")
        assert session is not None
        assert session.call_sid == "CA_get"

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_manager):
        """Retrieving a nonexistent session returns None."""
        result = await session_manager.get_session("CA_missing")
        assert result is None


class TestSessionManagerUpdate:
    """Tests for updating sessions."""

    @pytest.mark.asyncio
    async def test_update_session(self, session_manager):
        """Updating a session persists changes."""
        session = await session_manager.create_session("CA_upd", "+15550000000")
        session.diagnostic.appliance_type = "dryer"
        await session_manager.update_session(session)

        retrieved = await session_manager.get_session("CA_upd")
        assert retrieved.diagnostic.appliance_type == "dryer"


class TestSessionManagerEnd:
    """Tests for ending sessions."""

    @pytest.mark.asyncio
    async def test_end_session(self, session_manager):
        """Ending a session removes it and returns the state."""
        await session_manager.create_session("CA_end", "+15550000000")
        ended = await session_manager.end_session("CA_end")
        assert ended is not None
        assert ended.call_sid == "CA_end"

        after = await session_manager.get_session("CA_end")
        assert after is None

    @pytest.mark.asyncio
    async def test_end_session_not_found(self, session_manager):
        """Ending a nonexistent session returns None."""
        result = await session_manager.end_session("CA_nope")
        assert result is None


class TestSessionManagerActiveAndPhase:
    """Tests for listing active sessions and phase transitions."""

    @pytest.mark.asyncio
    async def test_get_active_sessions(self, session_manager):
        """Active sessions returns all current sessions."""
        await session_manager.create_session("CA_a", "+15550000001")
        await session_manager.create_session("CA_b", "+15550000002")
        active = await session_manager.get_active_sessions()
        assert len(active) == 2
        assert "CA_a" in active
        assert "CA_b" in active

    @pytest.mark.asyncio
    async def test_transition_phase(self, session_manager):
        """Phase transitions update the conversation phase."""
        await session_manager.create_session("CA_phase", "+15550000000")
        updated = await session_manager.transition_phase(
            "CA_phase", ConversationPhase.GATHER_SYMPTOMS
        )
        assert updated is not None
        assert updated.phase == ConversationPhase.GATHER_SYMPTOMS

    @pytest.mark.asyncio
    async def test_transition_phase_not_found(self, session_manager):
        """Transitioning phase on nonexistent session returns None."""
        result = await session_manager.transition_phase(
            "CA_ghost", ConversationPhase.CLOSING
        )
        assert result is None
