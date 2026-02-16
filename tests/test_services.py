"""Tests for service layer."""

from app.models import Customer
from app.models.availability import AppointmentStatus
from app.services import (
    CustomerService,
    DiagnosticService,
    SchedulingService,
    TechnicianService,
)


class TestDiagnosticService:
    """Tests for the diagnostic service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = DiagnosticService()

    def test_get_supported_appliances(self):
        """Test getting list of supported appliances."""
        appliances = self.service.get_supported_appliances()
        assert len(appliances) > 0
        assert "washer" in appliances
        assert "dryer" in appliances
        assert "refrigerator" in appliances

    def test_normalize_appliance_type(self):
        """Test appliance type normalization."""
        assert self.service.normalize_appliance_type("washer") == "washer"
        assert self.service.normalize_appliance_type("Washing Machine") == "washer"
        assert self.service.normalize_appliance_type("fridge") == "refrigerator"
        assert self.service.normalize_appliance_type("AC") == "hvac"
        assert self.service.normalize_appliance_type("unknown") is None

    def test_get_common_symptoms(self):
        """Test getting symptoms for appliance."""
        symptoms = self.service.get_common_symptoms("washer")
        assert len(symptoms) > 0
        assert "won't start" in symptoms

    def test_get_common_symptoms_unknown(self):
        """Test getting symptoms for unknown appliance."""
        symptoms = self.service.get_common_symptoms("unknown_appliance")
        assert symptoms == []

    def test_get_troubleshooting_steps(self):
        """Test getting troubleshooting steps."""
        steps = self.service.get_troubleshooting_steps("washer", "won't start")
        assert len(steps) > 0

    def test_get_troubleshooting_steps_default(self):
        """Test fallback to default steps for unknown symptom."""
        steps = self.service.get_troubleshooting_steps("washer", "unknown_symptom")
        assert len(steps) > 0
        # Should return default troubleshooting steps

    def test_match_symptom(self):
        """Test symptom matching."""
        matched, score = self.service.match_symptom("washer", "my washer won't start")
        assert matched is not None
        assert score > 0

    def test_should_schedule_technician(self):
        """Test technician scheduling recommendation."""
        # Issue resolved - no need for technician
        assert not self.service.should_schedule_technician(
            troubleshooting_attempted=["step1"], issue_resolved=True
        )

        # High severity - need technician
        assert self.service.should_schedule_technician(
            troubleshooting_attempted=[], issue_resolved=False, symptom_severity="high"
        )

        # Multiple steps tried, not resolved - need technician
        assert self.service.should_schedule_technician(
            troubleshooting_attempted=["step1", "step2"], issue_resolved=False
        )


class TestCustomerService:
    """Tests for the customer service."""

    def test_get_or_create_customer_new(self, db_session):
        """Test creating new customer."""
        service = CustomerService(db_session)
        phone = "+15551234567"

        customer = service.get_or_create_customer(phone)

        assert customer is not None
        assert customer.phone == phone
        assert customer.id is not None

    def test_get_or_create_customer_existing(self, db_session):
        """Test getting existing customer."""
        service = CustomerService(db_session)
        phone = "+15551234567"

        # Create customer
        customer1 = service.get_or_create_customer(phone)

        # Should return same customer
        customer2 = service.get_or_create_customer(phone)

        assert customer1.id == customer2.id

    def test_update_customer(self, db_session):
        """Test updating customer info."""
        service = CustomerService(db_session)

        # Create customer
        customer = service.get_or_create_customer("+15551234567")

        # Update
        updated = service.update_customer(
            customer.id, first_name="John", last_name="Doe", email="john@example.com"
        )

        assert updated.first_name == "John"
        assert updated.last_name == "Doe"
        assert updated.email == "john@example.com"


class TestSchedulingService:
    """Tests for the scheduling service."""

    def test_generate_confirmation_number(self, db_session):
        """Test confirmation number generation."""
        service = SchedulingService(db_session)

        conf1 = service._generate_confirmation_number()
        conf2 = service._generate_confirmation_number()

        assert conf1.startswith("SHS-")
        assert len(conf1) == 12  # SHS- + 8 chars
        assert conf1 != conf2  # Should be unique

    def test_get_available_slots_no_technicians(self, db_session):
        """Test availability with no technicians."""
        service = SchedulingService(db_session)

        slots = service.get_available_slots(zip_code="90210", appliance_type="washer")

        assert slots == []

    def test_get_available_slots_with_seeded_data(self, seeded_db_session):
        """Available slots are returned when technicians exist."""
        service = SchedulingService(seeded_db_session)
        slots = service.get_available_slots(
            zip_code="90210",
            appliance_type="washer",
        )
        assert len(slots) > 0
        assert slots[0].technician_name is not None

    def test_book_appointment_success(self, seeded_db_session):
        """Full booking flow creates appointment and marks slot unavailable."""
        service = SchedulingService(seeded_db_session)

        # Get a customer
        customer = seeded_db_session.query(Customer).first()

        # Get an available slot
        slots = service.get_available_slots(zip_code="90210", appliance_type="washer")
        assert len(slots) > 0
        slot_id = slots[0].slot_id

        appointment, error = service.book_appointment(
            customer_id=customer.id,
            time_slot_id=slot_id,
            appliance_type="washer",
            issue_description="won't drain",
            symptoms="standing water",
        )

        assert error is None
        assert appointment is not None
        assert appointment.confirmation_number.startswith("SHS-")
        assert appointment.status == AppointmentStatus.SCHEDULED

        # Slot should be unavailable now
        slot = service.get_slot_by_id(slot_id)
        assert slot.is_available is False

    def test_book_appointment_slot_not_found(self, seeded_db_session):
        """Booking a nonexistent slot returns error."""
        service = SchedulingService(seeded_db_session)
        customer = seeded_db_session.query(Customer).first()

        appointment, error = service.book_appointment(
            customer_id=customer.id,
            time_slot_id=99999,
            appliance_type="washer",
            issue_description="test",
        )

        assert appointment is None
        assert "not found" in error.lower()

    def test_cancel_appointment(self, seeded_db_session):
        """Cancelling an appointment frees the slot."""
        service = SchedulingService(seeded_db_session)
        customer = seeded_db_session.query(Customer).first()

        slots = service.get_available_slots(zip_code="90210", appliance_type="washer")
        slot_id = slots[0].slot_id

        appointment, _ = service.book_appointment(
            customer_id=customer.id,
            time_slot_id=slot_id,
            appliance_type="washer",
            issue_description="test cancel",
        )

        success, error = service.cancel_appointment(appointment.id)
        assert success is True
        assert error is None

        slot = service.get_slot_by_id(slot_id)
        assert slot.is_available is True

    def test_cancel_appointment_not_found(self, seeded_db_session):
        """Cancelling a nonexistent appointment returns error."""
        service = SchedulingService(seeded_db_session)
        success, error = service.cancel_appointment(99999)
        assert success is False
        assert "not found" in error.lower()

    def test_format_appointment_details(self, seeded_db_session):
        """Formatted details dict has all required keys."""
        service = SchedulingService(seeded_db_session)
        customer = seeded_db_session.query(Customer).first()

        slots = service.get_available_slots(zip_code="90210", appliance_type="washer")
        appointment, _ = service.book_appointment(
            customer_id=customer.id,
            time_slot_id=slots[0].slot_id,
            appliance_type="washer",
            issue_description="noisy spin",
        )

        details = service.format_appointment_details(appointment)
        assert "confirmation_number" in details
        assert "date" in details
        assert "time_window" in details
        assert "technician_name" in details
        assert "appliance_type" in details
        assert "issue_description" in details


class TestTechnicianService:
    """Tests for the technician service."""

    def test_get_all_technicians_empty(self, db_session):
        """Empty database returns empty list."""
        service = TechnicianService(db_session)
        assert service.get_all_technicians() == []

    def test_get_all_technicians_seeded(self, seeded_db_session):
        """Returns technicians from seeded database."""
        service = TechnicianService(seeded_db_session)
        techs = service.get_all_technicians()
        assert len(techs) == 2

    def test_find_technicians_by_criteria(self, seeded_db_session):
        """Finds technicians matching zip code and appliance type."""
        service = TechnicianService(seeded_db_session)
        techs = service.find_technicians_by_criteria(
            zip_code="90210",
            appliance_type="washer",
        )
        assert len(techs) >= 1

    def test_find_technicians_no_match(self, seeded_db_session):
        """Returns empty when no technician matches."""
        service = TechnicianService(seeded_db_session)
        techs = service.find_technicians_by_criteria(
            zip_code="00000",
            appliance_type="washer",
        )
        assert techs == []
