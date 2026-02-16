"""Tests for the VoiceAgent class."""

from unittest.mock import MagicMock, patch

import pytest

from app.schemas.conversation import ConversationState
from app.voice.agent import SYSTEM_PROMPT


class TestVoiceAgentPrompt:
    """Tests for system prompt generation."""

    def test_get_system_prompt_empty_session(self, voice_agent):
        """Base prompt with a fresh session (no context gathered yet)."""
        session = ConversationState(
            call_sid="CA_empty",
            customer_phone="+15550000000",
        )
        prompt = voice_agent.get_system_prompt(session)
        assert SYSTEM_PROMPT in prompt
        assert "Current Conversation Context" not in prompt

    def test_get_system_prompt_with_diagnostic_info(self, voice_agent, sample_session):
        """Prompt includes appliance, symptom, and scheduling context."""
        prompt = voice_agent.get_system_prompt(sample_session)

        assert SYSTEM_PROMPT in prompt
        assert "Appliance: washer" in prompt
        assert "Main Issue: won't start" in prompt
        assert "makes clicking noise" in prompt
        assert "Customer Zip Code: 90210" in prompt
        assert "Customer Name: Jane Doe" in prompt

    def test_get_system_prompt_with_key_facts(self, voice_agent):
        """Key facts appear under Current Conversation Context."""
        session = ConversationState(
            call_sid="CA_facts",
            customer_phone="+15550000000",
            key_facts=["Appliance is 5 years old", "Under warranty"],
        )
        prompt = voice_agent.get_system_prompt(session)
        assert "Current Conversation Context" in prompt
        assert "Appliance is 5 years old" in prompt
        assert "Under warranty" in prompt


class TestVoiceAgentTools:
    """Tests for tool definitions."""

    def test_get_tools_returns_all_tools(self, voice_agent):
        """All eight tools are present (5 original + 3 new)."""
        tools = voice_agent.get_tools()
        assert len(tools) == 8
        tool_names = {t["name"] for t in tools}
        assert tool_names == {
            "get_troubleshooting_steps",
            "check_technician_availability",
            "book_appointment",
            "request_image_upload",
            "update_customer_info",
            "transfer_to_human",
            "send_call_summary",
            "send_sms_confirmation",
        }

    def test_each_tool_has_required_structure(self, voice_agent):
        """Every tool has type, name, description, and parameters."""
        for tool in voice_agent.get_tools():
            assert tool["type"] == "function"
            assert "name" in tool
            assert "description" in tool
            assert "parameters" in tool
            assert tool["parameters"]["type"] == "object"


class TestVoiceAgentInitialMessage:
    """Tests for the initial greeting."""

    def test_get_initial_message(self, voice_agent):
        """Greeting contains Sears Home Services and agent name."""
        msg = voice_agent.get_initial_message()
        assert "Sears Home Services" in msg
        assert "Samantha" in msg
        assert "help" in msg.lower()


class TestVoiceAgentExecuteTool:
    """Tests for tool execution (each tool is tested with mocks)."""

    @pytest.mark.asyncio
    async def test_execute_tool_get_troubleshooting(self, voice_agent, sample_session):
        """get_troubleshooting_steps returns formatted steps."""
        result = await voice_agent.execute_tool(
            "get_troubleshooting_steps",
            {"appliance_type": "washer", "symptom": "won't start"},
            sample_session,
        )
        assert "Troubleshooting steps" in result or "general steps" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_check_availability(
        self, voice_agent, sample_session, seeded_db_session
    ):
        """check_technician_availability queries the database."""
        with patch("app.voice.agent.get_db_context") as mock_ctx:
            mock_ctx.return_value.__enter__ = MagicMock(return_value=seeded_db_session)
            mock_ctx.return_value.__exit__ = MagicMock(return_value=False)

            result = await voice_agent.execute_tool(
                "check_technician_availability",
                {"zip_code": "90210", "appliance_type": "washer"},
                sample_session,
            )
            assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_execute_tool_unknown(self, voice_agent, sample_session):
        """Unknown tool name returns descriptive message."""
        result = await voice_agent.execute_tool("nonexistent_tool", {}, sample_session)
        assert "Unknown tool" in result

    @pytest.mark.asyncio
    async def test_execute_tool_handles_exception(self, voice_agent, sample_session):
        """Tool execution catches exceptions gracefully."""
        with patch.object(
            voice_agent, "_get_troubleshooting", side_effect=Exception("boom")
        ):
            result = await voice_agent.execute_tool(
                "get_troubleshooting_steps",
                {"appliance_type": "washer", "symptom": "broken"},
                sample_session,
            )
            assert "encountered an issue" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_transfer_to_human(self, voice_agent, sample_session):
        """transfer_to_human returns a transfer message."""
        result = await voice_agent.execute_tool(
            "transfer_to_human",
            {
                "reason": "customer requested",
                "urgency": "normal",
                "department": "general_support",
                "summary": "Customer has a broken washer",
            },
            sample_session,
        )
        assert "Transfer initiated" in result or "EMERGENCY" in result
        assert "General Support" in result

    @pytest.mark.asyncio
    async def test_execute_tool_transfer_emergency(self, voice_agent, sample_session):
        """Emergency transfer returns urgent message."""
        result = await voice_agent.execute_tool(
            "transfer_to_human",
            {
                "reason": "gas leak reported",
                "urgency": "emergency",
                "department": "emergency",
                "summary": "Customer reports gas smell from oven",
            },
            sample_session,
        )
        assert "EMERGENCY" in result

    @pytest.mark.asyncio
    async def test_execute_tool_send_call_summary(self, voice_agent, sample_session):
        """send_call_summary returns success when no API key configured."""
        sample_session.scheduling.customer_email = "test@example.com"
        result = await voice_agent.execute_tool(
            "send_call_summary",
            {"email": "test@example.com", "summary_notes": "Test notes"},
            sample_session,
        )
        assert "sent" in result.lower() or "email" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_send_call_summary_no_email(
        self, voice_agent, sample_session
    ):
        """send_call_summary asks for email when none is available."""
        sample_session.scheduling.customer_email = None
        result = await voice_agent.execute_tool(
            "send_call_summary",
            {},
            sample_session,
        )
        assert "email" in result.lower()

    @pytest.mark.asyncio
    async def test_execute_tool_send_sms_confirmation(
        self, voice_agent, sample_session
    ):
        """send_sms_confirmation returns success in dev mode."""
        result = await voice_agent.execute_tool(
            "send_sms_confirmation",
            {
                "phone": "+15551234567",
                "confirmation_number": "SHS-001",
                "appointment_details": "Monday Jan 5 9:00AM-12:00PM",
            },
            sample_session,
        )
        assert "SMS" in result or "confirmation" in result.lower()


class TestVoiceAgentReturningCustomer:
    """Tests for returning customer greeting."""

    def test_get_returning_customer_greeting(self, voice_agent):
        """Returning customer greeting includes name and history."""
        greeting = voice_agent.get_returning_customer_greeting(
            "Jane Doe",
            "Returning customer with 2 previous appointment(s).",
        )
        assert "Jane Doe" in greeting
        assert "Samantha" in greeting
        assert "Returning customer" in greeting
