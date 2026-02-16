"""Pydantic schemas for API request/response validation."""

from app.schemas.appointment import (
    AppointmentBase,
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    AvailableSlotResponse,
    TimeSlotResponse,
)
from app.schemas.conversation import (
    ConversationState,
    DiagnosticInfo,
    SchedulingInfo,
)
from app.schemas.customer import (
    CustomerBase,
    CustomerCreate,
    CustomerResponse,
    ImageUploadCreate,
    ImageUploadResponse,
)
from app.schemas.technician import (
    ServiceAreaResponse,
    SpecialtyResponse,
    TechnicianBase,
    TechnicianCreate,
    TechnicianResponse,
    TechnicianWithAvailability,
)

__all__ = [
    "TechnicianBase",
    "TechnicianCreate",
    "TechnicianResponse",
    "TechnicianWithAvailability",
    "SpecialtyResponse",
    "ServiceAreaResponse",
    "AppointmentBase",
    "AppointmentCreate",
    "AppointmentResponse",
    "AppointmentUpdate",
    "TimeSlotResponse",
    "AvailableSlotResponse",
    "CustomerBase",
    "CustomerCreate",
    "CustomerResponse",
    "ImageUploadCreate",
    "ImageUploadResponse",
    "ConversationState",
    "DiagnosticInfo",
    "SchedulingInfo",
]
