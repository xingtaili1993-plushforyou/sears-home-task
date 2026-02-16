"""Tests for API endpoints."""

from datetime import datetime, timedelta

from app.models import (
    Customer,
    ImageUploadRequest,
)


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client):
        """Test that health check returns healthy status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestDiagnosticsEndpoint:
    """Tests for diagnostic endpoints."""

    def test_list_appliances(self, client):
        """Test listing supported appliances."""
        response = client.get("/api/diagnostics/appliances")
        assert response.status_code == 200
        data = response.json()
        assert "appliances" in data
        assert "washer" in data["appliances"]
        assert "refrigerator" in data["appliances"]

    def test_get_symptoms(self, client):
        """Test getting symptoms for an appliance."""
        response = client.get("/api/diagnostics/washer/symptoms")
        assert response.status_code == 200
        data = response.json()
        assert data["appliance_type"] == "washer"
        assert "symptoms" in data
        assert len(data["symptoms"]) > 0

    def test_get_troubleshooting(self, client):
        """Test getting troubleshooting steps."""
        response = client.post(
            "/api/diagnostics/washer/troubleshoot", params={"symptom": "won't start"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "troubleshooting_steps" in data
        assert len(data["troubleshooting_steps"]) > 0


class TestTechnicianEndpoints:
    """Tests for technician-related endpoints."""

    def test_list_technicians_empty(self, client, db_session):
        """Test listing technicians when none exist."""
        response = client.get("/api/technicians")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_specialties_empty(self, client, db_session):
        """Test listing specialties when none exist."""
        response = client.get("/api/specialties")
        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestSchedulingEndpoints:
    """Tests for scheduling-related endpoints."""

    def test_availability_no_technicians(self, client, db_session):
        """Test availability when no technicians exist."""
        response = client.get(
            "/api/availability",
            params={"zip_code": "90210", "appliance_type": "washer"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data == []


class TestCustomerEndpoints:
    """Tests for customer-related endpoints."""

    def test_create_customer(self, client, db_session, sample_customer_data):
        """Test creating a new customer."""
        response = client.post("/api/customers", json=sample_customer_data)
        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == sample_customer_data["phone"]
        assert data["email"] == sample_customer_data["email"]
        assert "id" in data

    def test_get_customer_not_found(self, client, db_session):
        """Test getting non-existent customer."""
        response = client.get("/api/customers/99999")
        assert response.status_code == 404


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "endpoints" in data


class TestUploadEndpoints:
    """Tests for image upload endpoints."""

    def _seed_customer(self, db_session):
        """Create a customer for upload tests."""
        customer = Customer(phone="+15550001234", email="up@test.com")
        db_session.add(customer)
        db_session.commit()
        return customer

    def test_image_upload_request_endpoint(self, client, db_session):
        """Create upload request via the API."""
        customer = self._seed_customer(db_session)

        response = client.post(
            "/image-upload-request",
            json={
                "customer_id": customer.id,
                "email": "up@test.com",
                "appliance_type": "oven",
                "issue_description": "not heating",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "upload_token" in data
        assert data["email_sent_to"] == "up@test.com"
        assert data["is_used"] is False

    def test_upload_page_valid_token(self, client, db_session):
        """Valid token serves the upload HTML page."""
        customer = self._seed_customer(db_session)
        req = ImageUploadRequest(
            customer_id=customer.id,
            upload_token="page_test_token",
            email_sent_to="p@test.com",
            email_sent_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_used=False,
        )
        db_session.add(req)
        db_session.commit()

        response = client.get("/upload/page_test_token")
        assert response.status_code == 200
        assert "Upload Appliance Photo" in response.text
        assert "page_test_token" in response.text

    def test_upload_page_invalid_token(self, client, db_session):
        """Invalid token returns error page."""
        response = client.get("/upload/does_not_exist")
        assert response.status_code == 400
        assert "Invalid" in response.text

    def test_upload_page_expired_token(self, client, db_session):
        """Expired token returns error page."""
        customer = self._seed_customer(db_session)
        req = ImageUploadRequest(
            customer_id=customer.id,
            upload_token="expired_page_tok",
            email_sent_to="e@test.com",
            email_sent_at=datetime.utcnow(),
            expires_at=datetime.utcnow() - timedelta(hours=1),
            is_used=False,
        )
        db_session.add(req)
        db_session.commit()

        response = client.get("/upload/expired_page_tok")
        assert response.status_code == 400
        assert "expired" in response.text.lower()
