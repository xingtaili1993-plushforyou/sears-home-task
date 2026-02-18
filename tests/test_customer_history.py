"""Tests for customer history lookup and seed data refresh."""

from app.models import Customer, TimeSlot
from app.services.customer_service import CustomerService
from app.services.scheduling_service import SchedulingService


class TestCustomerHistory:
    """Tests for CustomerService.get_customer_history."""

    def test_no_history(self, db_session):
        """Customer with no appointments returns empty list."""
        customer = Customer(phone="+15550000001")
        db_session.add(customer)
        db_session.commit()

        service = CustomerService(db_session)
        history = service.get_customer_history(customer.id)
        assert history == []

    def test_with_appointments(self, seeded_db_session):
        """Customer with appointments returns history strings."""
        db = seeded_db_session
        customer = db.query(Customer).first()
        slot = db.query(TimeSlot).filter(TimeSlot.is_available).first()

        sched = SchedulingService(db)
        appt, _ = sched.book_appointment(
            customer_id=customer.id,
            time_slot_id=slot.id,
            appliance_type="washer",
            issue_description="leaking water",
        )
        assert appt is not None

        service = CustomerService(db)
        history = service.get_customer_history(customer.id)
        assert len(history) >= 1
        assert "Returning customer" in history[0]
        assert "Most recent appointment" in history[1]

    def test_history_nonexistent_customer(self, db_session):
        """Non-existent customer ID returns empty list."""
        service = CustomerService(db_session)
        history = service.get_customer_history(99999)
        assert history == []


class TestSchedulingServiceExtended:
    """Additional scheduling service tests."""

    def test_get_appointment_by_confirmation(self, seeded_db_session):
        """Look up appointment by confirmation number."""
        db = seeded_db_session
        customer = db.query(Customer).first()
        slot = db.query(TimeSlot).filter(TimeSlot.is_available).first()

        sched = SchedulingService(db)
        appt, _ = sched.book_appointment(
            customer_id=customer.id,
            time_slot_id=slot.id,
            appliance_type="dryer",
            issue_description="not heating",
        )
        found = sched.get_appointment_by_confirmation(appt.confirmation_number)
        assert found is not None
        assert found.id == appt.id

    def test_get_appointment_by_confirmation_not_found(self, seeded_db_session):
        """Non-existent confirmation returns None."""
        sched = SchedulingService(seeded_db_session)
        assert sched.get_appointment_by_confirmation("FAKE-000") is None

    def test_cancel_already_cancelled(self, seeded_db_session):
        """Cancelling an already cancelled appointment returns error."""
        db = seeded_db_session
        customer = db.query(Customer).first()
        slot = db.query(TimeSlot).filter(TimeSlot.is_available).first()

        sched = SchedulingService(db)
        appt, _ = sched.book_appointment(
            customer_id=customer.id,
            time_slot_id=slot.id,
            appliance_type="washer",
            issue_description="broken",
        )
        sched.cancel_appointment(appt.id)
        success, error = sched.cancel_appointment(appt.id)
        assert success is False
        assert "Cannot cancel" in error

    def test_get_appointments_for_customer(self, seeded_db_session):
        """Retrieve appointments for a customer."""
        db = seeded_db_session
        customer = db.query(Customer).first()
        slot = db.query(TimeSlot).filter(TimeSlot.is_available).first()

        sched = SchedulingService(db)
        sched.book_appointment(
            customer_id=customer.id,
            time_slot_id=slot.id,
            appliance_type="oven",
            issue_description="not heating",
        )
        appointments = sched.get_appointments_for_customer(customer.id)
        assert len(appointments) >= 1

    def test_book_unavailable_slot(self, seeded_db_session):
        """Booking an already-booked slot returns error."""
        db = seeded_db_session
        customer = db.query(Customer).first()
        slot = db.query(TimeSlot).filter(TimeSlot.is_available).first()

        sched = SchedulingService(db)
        sched.book_appointment(
            customer_id=customer.id,
            time_slot_id=slot.id,
            appliance_type="washer",
            issue_description="broken",
        )
        _, error = sched.book_appointment(
            customer_id=customer.id,
            time_slot_id=slot.id,
            appliance_type="washer",
            issue_description="broken again",
        )
        assert error is not None
        assert "no longer available" in error
