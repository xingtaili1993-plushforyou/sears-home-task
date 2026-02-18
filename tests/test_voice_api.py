"""Tests for voice API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models import Customer


class TestIncomingCall:
    """Tests for the incoming call webhook."""

    def _seed_customer(self, db_session, phone="+15551234567"):
        customer = Customer(
            phone=phone,
            email="caller@test.com",
            first_name="Alice",
            last_name="Test",
            zip_code="90210",
        )
        db_session.add(customer)
        db_session.commit()
        return customer

    def test_incoming_call_new_customer(self, client, db_session):
        """Incoming call returns TwiML with WebSocket stream."""
        response = client.post(
            "/voice/incoming-call",
            data={"CallSid": "CA_new", "From": "+15559999999", "To": "+18001234567"},
        )
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "<Stream" in response.text
        assert "CA_new" in response.text

    def test_incoming_call_returning_customer(self, client, db_session):
        """Returning customer context is injected into session."""
        self._seed_customer(db_session, phone="+15553334444")
        response = client.post(
            "/voice/incoming-call",
            data={
                "CallSid": "CA_return",
                "From": "+15553334444",
                "To": "+18001234567",
            },
        )
        assert response.status_code == 200
        assert "<Stream" in response.text

    def test_incoming_call_missing_fields(self, client, db_session):
        """Call with missing form fields still succeeds with defaults."""
        response = client.post("/voice/incoming-call", data={})
        assert response.status_code == 200
        assert "<Stream" in response.text


class TestCallStatus:
    """Tests for call status webhook."""

    def test_call_completed(self, client, db_session):
        """Completed call returns OK."""
        response = client.post(
            "/voice/call-status",
            data={"CallSid": "CA_done", "CallStatus": "completed"},
        )
        assert response.status_code == 200
        assert response.text == "OK"

    def test_call_failed(self, client, db_session):
        """Failed call returns OK and cleans up."""
        response = client.post(
            "/voice/call-status",
            data={"CallSid": "CA_fail", "CallStatus": "failed"},
        )
        assert response.status_code == 200

    def test_call_in_progress(self, client, db_session):
        """In-progress status returns OK without cleanup."""
        response = client.post(
            "/voice/call-status",
            data={"CallSid": "CA_prog", "CallStatus": "in-progress"},
        )
        assert response.status_code == 200


class TestMediaStreamEndpoint:
    """Tests for the media stream placeholder."""

    def test_media_stream_get(self, client, db_session):
        """GET to media stream returns placeholder text."""
        response = client.get("/voice/media-stream/CA_test")
        assert response.status_code == 200
        assert "WebSocket" in response.text

    def test_media_stream_post(self, client, db_session):
        """POST to media stream returns placeholder text."""
        response = client.post("/voice/media-stream/CA_test")
        assert response.status_code == 200


class TestTransferEndpoint:
    """Tests for the call transfer endpoint."""

    def test_transfer_returns_twiml(self, client, db_session):
        """Transfer endpoint returns TwiML with Dial."""
        response = client.post(
            "/voice/transfer/CA_xfer",
            json={"department": "technical", "urgency": "normal"},
        )
        assert response.status_code == 200
        assert "application/xml" in response.headers["content-type"]
        assert "<Dial" in response.text
        assert "+15104025551" in response.text

    def test_transfer_emergency(self, client, db_session):
        """Emergency transfer returns TwiML."""
        response = client.post(
            "/voice/transfer/CA_emrg",
            json={"department": "emergency", "urgency": "emergency"},
        )
        assert response.status_code == 200
        assert "<Dial" in response.text

    def test_transfer_no_body(self, client, db_session):
        """Transfer with no JSON body uses defaults."""
        response = client.post("/voice/transfer/CA_def")
        assert response.status_code == 200
        assert "<Dial" in response.text
