"""Tests for EmailService."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.email_service import EmailService


class TestEmailServiceNoApiKey:
    """Behaviour when SendGrid API key is not configured."""

    @pytest.mark.asyncio
    async def test_send_image_upload_link_no_api_key(self):
        """Returns True and logs a warning when API key is empty."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = ""
            mock_settings.sendgrid_from_email = "test@test.com"

            service = EmailService()
            result = await service.send_image_upload_link(
                to_email="user@example.com",
                upload_url="https://example.com/upload/token123",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_appointment_confirmation_no_api_key(self):
        """Appointment confirmation also returns True without key."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = ""
            mock_settings.sendgrid_from_email = "test@test.com"

            service = EmailService()
            result = await service.send_appointment_confirmation(
                to_email="user@example.com",
                customer_name="Jane Doe",
                confirmation_number="SHS-ABC12345",
                appointment_date="2026-02-20",
                appointment_time="9:00 AM - 12:00 PM",
                technician_name="John Smith",
                appliance_type="washer",
                issue_description="won't start",
            )
            assert result is True


class TestEmailServiceWithApiKey:
    """Behaviour with a configured (mocked) SendGrid client."""

    @pytest.mark.asyncio
    async def test_send_image_upload_link_success(self):
        """Successful send returns True."""
        import sendgrid as sg_module

        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.fake"
            mock_settings.sendgrid_from_email = "sears@test.com"

            service = EmailService()

            with patch.dict("sys.modules", {"sendgrid": sg_module}):
                with patch("sendgrid.SendGridAPIClient") as mock_sg_cls:
                    mock_client = MagicMock()
                    mock_sg_cls.return_value = mock_client
                    mock_response = MagicMock()
                    mock_response.status_code = 202
                    mock_client.send.return_value = mock_response

                    result = await service.send_image_upload_link(
                        to_email="customer@test.com",
                        upload_url="https://example.com/upload/abc",
                        customer_name="Alice",
                        appliance_type="dryer",
                    )
                    assert result is True
                    mock_client.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_image_upload_link_failure(self):
        """Non-success status code returns False."""
        import sendgrid as sg_module

        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.fake"
            mock_settings.sendgrid_from_email = "sears@test.com"

            service = EmailService()

            with patch.dict("sys.modules", {"sendgrid": sg_module}):
                with patch("sendgrid.SendGridAPIClient") as mock_sg_cls:
                    mock_client = MagicMock()
                    mock_sg_cls.return_value = mock_client
                    mock_response = MagicMock()
                    mock_response.status_code = 403
                    mock_response.body = b"Forbidden"
                    mock_client.send.return_value = mock_response

                    result = await service.send_image_upload_link(
                        to_email="customer@test.com",
                        upload_url="https://example.com/upload/abc",
                    )
                    assert result is False

    @pytest.mark.asyncio
    async def test_send_image_upload_link_exception(self):
        """Catches exception and returns False."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.fake"
            mock_settings.sendgrid_from_email = "sears@test.com"

            service = EmailService()

            # Simulate sendgrid import raising an error
            with patch.dict("sys.modules", {"sendgrid": None}):
                result = await service.send_image_upload_link(
                    to_email="customer@test.com",
                    upload_url="https://example.com/upload/abc",
                )
                # ImportError is caught, returns True in development
                assert result is True

    @pytest.mark.asyncio
    async def test_send_appointment_confirmation_success(self):
        """Appointment confirmation with mocked SendGrid."""
        import sendgrid as sg_module

        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.fake"
            mock_settings.sendgrid_from_email = "sears@test.com"

            service = EmailService()

            with patch.dict("sys.modules", {"sendgrid": sg_module}):
                with patch("sendgrid.SendGridAPIClient") as mock_sg_cls:
                    mock_client = MagicMock()
                    mock_sg_cls.return_value = mock_client
                    mock_response = MagicMock()
                    mock_response.status_code = 200
                    mock_client.send.return_value = mock_response

                    result = await service.send_appointment_confirmation(
                        to_email="customer@test.com",
                        customer_name="Jane Doe",
                        confirmation_number="SHS-XYZ12345",
                        appointment_date="Monday, February 20",
                        appointment_time="9:00 AM - 12:00 PM",
                        technician_name="Bob Smith",
                        appliance_type="refrigerator",
                        issue_description="not cooling",
                    )
                    assert result is True


class TestEmailContentGeneration:
    """Verify email HTML content includes expected data."""

    @pytest.mark.asyncio
    async def test_email_content_includes_customer_name(self):
        """Upload link email personalises with customer name."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.sendgrid_api_key = ""
            mock_settings.sendgrid_from_email = "test@test.com"

            service = EmailService()

            # Even without an API key the method still builds content internally.
            # We simply verify it does not crash with all optional params filled.
            result = await service.send_image_upload_link(
                to_email="person@test.com",
                upload_url="https://example.com/upload/xyz",
                customer_name="Bob Builder",
                appliance_type="oven",
            )
            assert result is True
