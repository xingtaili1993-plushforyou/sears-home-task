"""Extended tests for main.py endpoints."""


class TestVoiceTestEndpoint:
    """Tests for the voice configuration test endpoint."""

    def test_voice_test_returns_config(self, client):
        """Voice test endpoint reports configuration status."""
        response = client.get("/voice/test")
        assert response.status_code == 200
        data = response.json()
        assert "twilio_configured" in data
        assert "openai_configured" in data
        assert "realtime_model" in data
        assert "voice" in data


class TestRootEndpointExtended:
    """Additional tests for root endpoint."""

    def test_root_has_dashboard_endpoint(self, client):
        """Root lists dashboard in endpoints."""
        response = client.get("/")
        data = response.json()
        assert data["endpoints"]["dashboard"] == "/dashboard"

    def test_root_version(self, client):
        """Root reports correct version."""
        response = client.get("/")
        data = response.json()
        assert data["version"] == "2.0.0"
