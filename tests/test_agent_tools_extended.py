"""Extended tests for VoiceAgent tool branches not covered by test_voice_agent.py."""

from unittest.mock import MagicMock, patch

import pytest


class TestBookAppointment:
    """Tests for the _book_appointment tool."""

    @pytest.mark.asyncio
    async def test_book_appointment_success(
        self, voice_agent, sample_session, seeded_db_session
    ):
        """Booking with valid slot returns confirmation details."""
        from app.models import TimeSlot

        slot = seeded_db_session.query(TimeSlot).filter(TimeSlot.is_available).first()
        assert slot is not None

        with patch("app.voice.agent.get_db_context") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=seeded_db_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = await voice_agent.execute_tool(
                "book_appointment",
                {
                    "slot_id": slot.id,
                    "customer_name": "Jane Doe",
                    "customer_zip_code": "90210",
                    "appliance_type": "washer",
                    "issue_description": "won't start",
                },
                sample_session,
            )
        assert "Confirmation Number" in result
        assert "SHS-" in result
        assert sample_session.appointment_confirmation is not None

    @pytest.mark.asyncio
    async def test_book_appointment_invalid_slot(
        self, voice_agent, sample_session, seeded_db_session
    ):
        """Booking with non-existent slot returns error."""
        with patch("app.voice.agent.get_db_context") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=seeded_db_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = await voice_agent.execute_tool(
                "book_appointment",
                {
                    "slot_id": 99999,
                    "customer_name": "Jane Doe",
                    "appliance_type": "washer",
                    "issue_description": "won't start",
                },
                sample_session,
            )
        assert "wasn't able to book" in result


class TestRequestImageUpload:
    """Tests for the _request_image tool."""

    @pytest.mark.asyncio
    async def test_request_image_success(
        self, voice_agent, sample_session, seeded_db_session
    ):
        """Image upload request sends email and returns message."""
        with patch("app.voice.agent.get_db_context") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=seeded_db_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = await voice_agent.execute_tool(
                "request_image_upload",
                {
                    "email": "test@example.com",
                    "appliance_type": "washer",
                    "specific_area": "drum",
                },
                sample_session,
            )
        assert "email" in result.lower() or "link" in result.lower()
        assert sample_session.image_upload_requested is True

    @pytest.mark.asyncio
    async def test_request_image_no_specific_area(
        self, voice_agent, sample_session, seeded_db_session
    ):
        """Image upload without specific area still works."""
        with patch("app.voice.agent.get_db_context") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=seeded_db_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = await voice_agent.execute_tool(
                "request_image_upload",
                {"email": "test@example.com", "appliance_type": "washer"},
                sample_session,
            )
        assert "washer" in result.lower()


class TestUpdateCustomer:
    """Tests for the _update_customer tool."""

    @pytest.mark.asyncio
    async def test_update_customer_name(
        self, voice_agent, sample_session, seeded_db_session
    ):
        """Updating customer name updates session."""
        with patch("app.voice.agent.get_db_context") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=seeded_db_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = await voice_agent.execute_tool(
                "update_customer_info",
                {"name": "Alice Smith", "email": "alice@test.com", "zip_code": "90211"},
                sample_session,
            )
        assert "updated" in result.lower()
        assert sample_session.scheduling.customer_name == "Alice Smith"
        assert sample_session.scheduling.customer_email == "alice@test.com"
        assert sample_session.scheduling.customer_zip_code == "90211"

    @pytest.mark.asyncio
    async def test_update_customer_address(
        self, voice_agent, sample_session, seeded_db_session
    ):
        """Updating customer address updates session."""
        with patch("app.voice.agent.get_db_context") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=seeded_db_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = await voice_agent.execute_tool(
                "update_customer_info",
                {"address": "123 Main St"},
                sample_session,
            )
        assert "updated" in result.lower()
        assert sample_session.scheduling.customer_address == "123 Main St"

    @pytest.mark.asyncio
    async def test_update_customer_single_name(
        self, voice_agent, sample_session, seeded_db_session
    ):
        """Single-word name is handled correctly."""
        with patch("app.voice.agent.get_db_context") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=seeded_db_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = await voice_agent.execute_tool(
                "update_customer_info",
                {"name": "Madonna"},
                sample_session,
            )
        assert "updated" in result.lower()
        assert sample_session.scheduling.customer_name == "Madonna"
