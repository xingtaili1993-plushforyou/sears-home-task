"""Tests for seed_data module."""

from datetime import date, timedelta

from app.models import Technician, TechnicianSpecialty, TimeSlot
from app.seed_data import (
    create_specialties,
    create_time_slots,
    refresh_time_slots,
    seed_database,
)


class TestCreateSpecialties:
    """Tests for create_specialties."""

    def test_creates_all_appliance_types(self, db_session):
        """All standard appliance types are created."""
        specs = create_specialties(db_session)
        db_session.commit()
        assert "washer" in specs
        assert "dryer" in specs
        assert "refrigerator" in specs
        assert "hvac" in specs
        assert len(specs) >= 8


class TestCreateTimeSlots:
    """Tests for create_time_slots."""

    def test_creates_slots_for_technician(self, seeded_db_session):
        """Time slots are created for a valid technician."""
        db = seeded_db_session
        tech = db.query(Technician).first()
        initial_count = (
            db.query(TimeSlot).filter(TimeSlot.technician_id == tech.id).count()
        )

        slots = create_time_slots(db, tech, days_ahead=5)
        db.commit()
        assert len(slots) > 0
        for s in slots:
            assert s.is_available is True
            assert s.date > date.today()

    def test_skips_weekends(self, seeded_db_session):
        """Slots are not created on Saturday or Sunday."""
        db = seeded_db_session
        tech = db.query(Technician).first()
        slots = create_time_slots(db, tech, days_ahead=14)
        db.commit()
        for s in slots:
            assert s.date.weekday() < 5


class TestRefreshTimeSlots:
    """Tests for refresh_time_slots."""

    def test_noop_when_future_slots_exist(self, seeded_db_session):
        """No-op when future slots already exist."""
        db = seeded_db_session
        count_before = db.query(TimeSlot).count()
        refresh_time_slots(db)
        count_after = db.query(TimeSlot).count()
        assert count_after >= count_before

    def test_creates_slots_when_empty(self, db_session):
        """Creates slots when database has technicians but no slots."""
        tech = Technician(
            first_name="Solo",
            last_name="Tech",
            email="solo@test.com",
            phone="555-000-0000",
            employee_id="SOLO001",
            is_active=True,
            years_experience=3,
        )
        db_session.add(tech)
        db_session.commit()

        refresh_time_slots(db_session)
        slots = (
            db_session.query(TimeSlot).filter(TimeSlot.technician_id == tech.id).all()
        )
        assert len(slots) > 0


class TestSeedDatabase:
    """Tests for the full seed_database function."""

    def test_seed_populates_technicians(self, db_session):
        """Seeding creates 10 technicians with specialties and slots."""
        seed_database(db_session)
        count = db_session.query(Technician).count()
        assert count == 10

        specs = db_session.query(TechnicianSpecialty).count()
        assert specs >= 8

        slots = db_session.query(TimeSlot).count()
        assert slots > 0

    def test_seed_is_idempotent(self, db_session):
        """Running seed twice doesn't duplicate data."""
        seed_database(db_session)
        count1 = db_session.query(Technician).count()
        seed_database(db_session)
        count2 = db_session.query(Technician).count()
        assert count1 == count2
