"""Service for sending SMS messages via Twilio."""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    """Send SMS messages using the Twilio REST API."""

    def __init__(self):
        self.account_sid = settings.twilio_account_sid
        self.auth_token = settings.twilio_auth_token
        self.from_number = settings.twilio_phone_number

    async def send_appointment_confirmation(
        self,
        to_phone: str,
        confirmation_number: str,
        appointment_details: str,
    ) -> bool:
        """
        Send an SMS with appointment confirmation details.

        Returns True on success, False on failure.
        """
        body = (
            f"Sears Home Services\n"
            f"Appointment Confirmed!\n\n"
            f"Confirmation: {confirmation_number}\n"
            f"{appointment_details}\n\n"
            f"Your technician will call when on the way.\n"
            f"Need to reschedule? Call 1-800-4-MY-HOME\n"
            f"Reply STOP to opt out of texts."
        )

        return await self._send(to_phone, body)

    async def send_reminder(
        self,
        to_phone: str,
        confirmation_number: str,
        appointment_date: str,
        appointment_time: str,
    ) -> bool:
        """Send a day-before reminder SMS."""
        body = (
            f"Sears Home Services Reminder\n\n"
            f"Your appointment ({confirmation_number}) is tomorrow "
            f"{appointment_date} at {appointment_time}.\n\n"
            f"Please ensure access to the appliance.\n"
            f"Need to reschedule? Call 1-800-4-MY-HOME"
        )

        return await self._send(to_phone, body)

    async def _send(self, to_phone: str, body: str) -> bool:
        """Low-level send via Twilio REST API."""
        if not self.account_sid or not self.auth_token or not self.from_number:
            logger.warning(
                f"Twilio not fully configured. Would send SMS to {to_phone}: "
                f"{body[:80]}..."
            )
            return True  # treat as success in development

        try:
            from twilio.rest import Client

            client = Client(self.account_sid, self.auth_token)
            message = client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_phone,
            )
            logger.info(
                f"SMS sent to {to_phone} — SID: {message.sid}"
            )
            return True

        except ImportError:
            logger.warning("Twilio package not installed. SMS not sent.")
            return True
        except Exception as e:
            logger.error(f"Error sending SMS to {to_phone}: {str(e)}")
            return False
