"""Pytest fixtures for testing."""

from datetime import date, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import (
    Base,
    Customer,
    Technician,
    TechnicianServiceArea,
    TechnicianSpecialty,
    TimeSlot,
)
from app.schemas.conversation import (
    ConversationPhase,
    ConversationState,
    DiagnosticInfo,
    SchedulingInfo,
)
from app.voice.agent import VoiceAgent
from app.voice.session_manager import SessionManager

# ---------------------------------------------------------------------------
# Database engine (in-memory SQLite shared across all tests)
# ---------------------------------------------------------------------------
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Core fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_technician_data():
    """Sample technician data for testing."""
    return {
        "first_name": "John",
        "last_name": "Smith",
        "email": "jsmith@test.com",
        "phone": "555-123-4567",
        "employee_id": "TEST001",
        "years_experience": 5,
    }


@pytest.fixture
def sample_customer_data():
    """Sample customer data for testing."""
    return {
        "phone": "+15551234567",
        "email": "customer@test.com",
        "first_name": "Jane",
        "last_name": "Doe",
        "zip_code": "90210",
    }


# ---------------------------------------------------------------------------
# Seeded database fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def seeded_db_session(db_session):
    """Database session pre-populated with technicians, slots, and a customer."""
    # Create specialties
    washer_spec = TechnicianSpecialty(
        appliance_type="washer", description="Washer repair"
    )
    dryer_spec = TechnicianSpecialty(appliance_type="dryer", description="Dryer repair")
    fridge_spec = TechnicianSpecialty(
        appliance_type="refrigerator", description="Refrigerator repair"
    )
    db_session.add_all([washer_spec, dryer_spec, fridge_spec])
    db_session.flush()

    # Create technicians
    tech1 = Technician(
        first_name="Alice",
        last_name="Johnson",
        email="alice@test.com",
        phone="555-111-1111",
        employee_id="TECH001",
        is_active=True,
        years_experience=8,
    )
    tech2 = Technician(
        first_name="Bob",
        last_name="Williams",
        email="bob@test.com",
        phone="555-222-2222",
        employee_id="TECH002",
        is_active=True,
        years_experience=5,
    )
    db_session.add_all([tech1, tech2])
    db_session.flush()

    # Link specialties
    tech1.specialties.append(washer_spec)
    tech1.specialties.append(fridge_spec)
    tech2.specialties.append(dryer_spec)
    tech2.specialties.append(washer_spec)
    db_session.flush()

    # Service areas
    db_session.add_all(
        [
            TechnicianServiceArea(
                technician_id=tech1.id, zip_code="90210", is_primary=True
            ),
            TechnicianServiceArea(
                technician_id=tech1.id, zip_code="90211", is_primary=False
            ),
            TechnicianServiceArea(
                technician_id=tech2.id, zip_code="90210", is_primary=True
            ),
        ]
    )
    db_session.flush()

    # Time slots (next 3 days)
    today = date.today()
    for day_offset in range(1, 4):
        slot_date = today + timedelta(days=day_offset)
        # Morning slot for tech1
        db_session.add(
            TimeSlot(
                technician_id=tech1.id,
                date=slot_date,
                start_time=time(9, 0),
                end_time=time(12, 0),
                is_available=True,
            )
        )
        # Afternoon slot for tech2
        db_session.add(
            TimeSlot(
                technician_id=tech2.id,
                date=slot_date,
                start_time=time(13, 0),
                end_time=time(17, 0),
                is_available=True,
            )
        )
    db_session.flush()

    # Create a test customer
    customer = Customer(
        phone="+15559990000",
        email="testcustomer@test.com",
        first_name="Test",
        last_name="Customer",
        zip_code="90210",
    )
    db_session.add(customer)
    db_session.commit()

    return db_session


# ---------------------------------------------------------------------------
# Voice / Agent fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def voice_agent():
    """VoiceAgent instance."""
    return VoiceAgent()


@pytest.fixture
def session_manager():
    """Fresh SessionManager instance."""
    return SessionManager()


@pytest.fixture
def sample_session():
    """Pre-built ConversationState for testing."""
    return ConversationState(
        call_sid="CA_test_123",
        customer_phone="+15559990000",
        phase=ConversationPhase.GATHER_SYMPTOMS,
        customer_id=1,
        diagnostic=DiagnosticInfo(
            appliance_type="washer",
            primary_symptom="won't start",
            additional_symptoms=["makes clicking noise"],
        ),
        scheduling=SchedulingInfo(
            customer_zip_code="90210",
            customer_name="Jane Doe",
            customer_email="jane@test.com",
        ),
        key_facts=["Customer has a washer that won't start"],
    )


# ---------------------------------------------------------------------------
# Mock fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_openai():
    """Mocked OpenAI async client for vision tests."""
    with patch("app.services.image_service.openai") as mock:
        mock_client = AsyncMock()
        mock.AsyncOpenAI.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "This appears to be a washer with visible wear on the drum seal."
        )
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

        yield mock_client


@pytest.fixture
def mock_sendgrid():
    """Mocked SendGrid client for email tests."""
    with patch("app.services.email_service.sendgrid") as mock_sg_module:
        mock_client = MagicMock()
        mock_sg_module.SendGridAPIClient.return_value = mock_client

        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = b""
        mock_client.send.return_value = mock_response

        yield mock_client
