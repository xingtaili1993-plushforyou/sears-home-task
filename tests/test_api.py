"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.models import Technician, TechnicianSpecialty, TechnicianServiceArea, TimeSlot
from datetime import date, time, timedelta


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
            "/api/diagnostics/washer/troubleshoot",
            params={"symptom": "won't start"}
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
            params={
                "zip_code": "90210",
                "appliance_type": "washer"
            }
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
