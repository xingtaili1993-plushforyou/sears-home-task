"""Tests for dashboard routes."""


class TestDashboardPage:
    """Tests for the dashboard HTML page."""

    def test_dashboard_page_returns_html(self, client, db_session):
        """Dashboard page returns HTML with expected elements."""
        response = client.get("/dashboard/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Live Agent Dashboard" in response.text
        assert "Live Transcript" in response.text
        assert "Tool Calls" in response.text
        assert "Sentiment" in response.text

    def test_dashboard_page_has_websocket_script(self, client, db_session):
        """Dashboard HTML includes WebSocket connection script."""
        response = client.get("/dashboard/")
        assert response.status_code == 200
        assert "WebSocket" in response.text
