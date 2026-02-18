"""Extended tests for API routes with seeded data."""

from app.models import Customer, TimeSlot


class TestTechnicianRoutes:
    """Tests for technician API routes with seeded data."""

    def test_list_technicians_seeded(self, client, seeded_db_session):
        """List technicians returns seeded data."""
        response = client.get("/api/technicians")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_technician_by_id(self, client, seeded_db_session):
        """Get specific technician by ID."""
        techs = client.get("/api/technicians").json()
        tech_id = techs[0]["id"]
        response = client.get(f"/api/technicians/{tech_id}")
        assert response.status_code == 200
        assert response.json()["id"] == tech_id

    def test_get_technician_not_found(self, client, seeded_db_session):
        """Non-existent technician returns 404."""
        response = client.get("/api/technicians/99999")
        assert response.status_code == 404

    def test_search_technicians_by_criteria(self, client, seeded_db_session):
        """Search by zip and appliance type returns matches."""
        response = client.get(
            "/api/technicians/search/by-criteria",
            params={"zip_code": "90210", "appliance_type": "washer"},
        )
        assert response.status_code == 200

    def test_list_specialties_seeded(self, client, seeded_db_session):
        """List specialties returns seeded data."""
        response = client.get("/api/specialties")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2


class TestAvailabilityRoutes:
    """Tests for availability endpoints."""

    def test_availability_with_seeded_data(self, client, seeded_db_session):
        """Available slots returned for valid zip and appliance."""
        response = client.get(
            "/api/availability",
            params={"zip_code": "90210", "appliance_type": "washer"},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_availability_no_match(self, client, seeded_db_session):
        """No slots for non-existent zip code."""
        response = client.get(
            "/api/availability",
            params={"zip_code": "00000", "appliance_type": "washer"},
        )
        assert response.status_code == 200
        assert response.json() == []


class TestAppointmentRoutes:
    """Tests for appointment CRUD endpoints."""

    def test_create_and_get_appointment(self, client, seeded_db_session):
        """Create appointment and retrieve it."""
        db = seeded_db_session
        customer = db.query(Customer).first()
        slot = db.query(TimeSlot).filter(TimeSlot.is_available).first()

        response = client.post(
            "/api/appointments",
            json={
                "customer_id": customer.id,
                "technician_id": slot.technician_id,
                "time_slot_id": slot.id,
                "appliance_type": "washer",
                "issue_description": "leaking water",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "confirmation_number" in data
        appt_id = data["id"]

        get_resp = client.get(f"/api/appointments/{appt_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == appt_id

    def test_get_appointment_not_found(self, client, seeded_db_session):
        """Non-existent appointment returns 404."""
        response = client.get("/api/appointments/99999")
        assert response.status_code == 404

    def test_get_appointment_by_confirmation(self, client, seeded_db_session):
        """Look up appointment by confirmation number."""
        db = seeded_db_session
        customer = db.query(Customer).first()
        slot = db.query(TimeSlot).filter(TimeSlot.is_available).first()

        create_resp = client.post(
            "/api/appointments",
            json={
                "customer_id": customer.id,
                "technician_id": slot.technician_id,
                "time_slot_id": slot.id,
                "appliance_type": "dryer",
                "issue_description": "not heating",
            },
        )
        conf = create_resp.json()["confirmation_number"]

        lookup_resp = client.get(f"/api/appointments/confirmation/{conf}")
        assert lookup_resp.status_code == 200

    def test_get_appointment_by_confirmation_not_found(self, client, seeded_db_session):
        """Non-existent confirmation number returns 404."""
        response = client.get("/api/appointments/confirmation/FAKE-000")
        assert response.status_code == 404

    def test_cancel_appointment(self, client, seeded_db_session):
        """Cancel an appointment."""
        db = seeded_db_session
        customer = db.query(Customer).first()
        slot = db.query(TimeSlot).filter(TimeSlot.is_available).first()

        create_resp = client.post(
            "/api/appointments",
            json={
                "customer_id": customer.id,
                "technician_id": slot.technician_id,
                "time_slot_id": slot.id,
                "appliance_type": "oven",
                "issue_description": "won't heat",
            },
        )
        appt_id = create_resp.json()["id"]

        del_resp = client.delete(f"/api/appointments/{appt_id}")
        assert del_resp.status_code == 200
        assert "cancelled" in del_resp.json()["message"].lower()


class TestCustomerRoutesByPhone:
    """Tests for customer phone lookup."""

    def test_get_customer_by_phone(self, client, seeded_db_session):
        """Retrieve customer by phone number."""
        db = seeded_db_session
        customer = db.query(Customer).first()
        response = client.get(f"/api/customers/phone/{customer.phone}")
        assert response.status_code == 200
        assert response.json()["phone"] == customer.phone

    def test_get_customer_by_phone_not_found(self, client, seeded_db_session):
        """Non-existent phone returns 404."""
        response = client.get("/api/customers/phone/+10000000000")
        assert response.status_code == 404


class TestDiagnosticQuestions:
    """Tests for diagnostic questions endpoint."""

    def test_get_diagnostic_questions(self, client):
        """Diagnostic questions returned for valid appliance."""
        response = client.get("/api/diagnostics/washer/questions")
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
