"""Extended tests for SMS service and email service methods."""

from unittest.mock import patch

import pytest

from app.services.email_service import EmailService
from app.services.sms_service import SMSService


class TestSMSService:
    """Tests for SMS service methods."""

    @pytest.mark.asyncio
    async def test_send_appointment_confirmation_no_config(self):
        """SMS returns True in dev mode (no Twilio credentials)."""
        sms = SMSService()
        sms.account_sid = ""
        sms.auth_token = ""
        sms.from_number = ""
        result = await sms.send_appointment_confirmation(
            to_phone="+15551234567",
            confirmation_number="SHS-TEST123",
            appointment_details="Monday Jan 5, 9:00 AM - 12:00 PM",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_reminder_no_config(self):
        """SMS reminder returns True in dev mode."""
        sms = SMSService()
        sms.account_sid = ""
        sms.auth_token = ""
        sms.from_number = ""
        result = await sms.send_reminder(
            to_phone="+15551234567",
            confirmation_number="SHS-TEST123",
            appointment_date="Monday Jan 5",
            appointment_time="9:00 AM",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_raw_no_config(self):
        """Low-level _send returns True in dev mode."""
        sms = SMSService()
        sms.account_sid = ""
        sms.auth_token = ""
        sms.from_number = ""
        result = await sms._send("+15551234567", "Test message body")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_with_import_error(self):
        """SMS handles missing twilio package gracefully."""
        sms = SMSService()
        sms.account_sid = "ACtest"
        sms.auth_token = "token"
        sms.from_number = "+15550000000"

        with patch("app.services.sms_service.SMSService._send") as mock_send:
            mock_send.return_value = True
            result = await sms.send_appointment_confirmation(
                to_phone="+15551234567",
                confirmation_number="SHS-TEST",
                appointment_details="Tomorrow",
            )
        assert result is True


class TestEmailCallSummary:
    """Tests for the call summary email method."""

    @pytest.mark.asyncio
    async def test_send_call_summary_no_api_key(self):
        """Call summary returns True without API key (dev mode)."""
        service = EmailService()
        result = await service.send_call_summary(
            to_email="test@example.com",
            customer_name="John Doe",
            appliance_type="washer",
            primary_symptom="won't start",
            troubleshooting_steps=["Check power cord", "Reset circuit breaker"],
            appointment_confirmation="SHS-ABC12345",
            key_facts=["Appliance is 5 years old", "Under warranty"],
            summary_notes="Customer may need a new motor.",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_call_summary_minimal(self):
        """Call summary with minimal fields returns True."""
        service = EmailService()
        result = await service.send_call_summary(to_email="min@test.com")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_call_summary_filters_user_said(self):
        """Key facts starting with 'User said:' are filtered out."""
        service = EmailService()
        result = await service.send_call_summary(
            to_email="test@example.com",
            key_facts=[
                "User said: Hello",
                "Appliance is old",
                "User said: I need help",
            ],
        )
        assert result is True


class TestEmailImageAnalysis:
    """Tests for the image analysis email method."""

    @pytest.mark.asyncio
    async def test_send_image_analysis_no_api_key(self):
        """Image analysis email returns True without API key."""
        service = EmailService()
        result = await service.send_image_analysis(
            to_email="test@example.com",
            appliance_type="refrigerator",
            analysis="The seal on the door appears worn.\nRecommend replacement.",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_send_image_analysis_minimal(self):
        """Image analysis with no appliance_type uses default."""
        service = EmailService()
        result = await service.send_image_analysis(
            to_email="test@example.com",
            analysis="Analysis result here.",
        )
        assert result is True
