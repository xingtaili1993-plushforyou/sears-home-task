"""Pydantic schemas for API request/response validation."""

from app.schemas.technician import (
    TechnicianBase,
    TechnicianCreate,
    TechnicianResponse,
    TechnicianWithAvailability,
    SpecialtyResponse,
    ServiceAreaResponse,
)
from app.schemas.appointment import (
    AppointmentBase,
    AppointmentCreate,
    AppointmentResponse,
    AppointmentUpdate,
    TimeSlotResponse,
    AvailableSlotResponse,
)
from app.schemas.customer import (
    CustomerBase,
    CustomerCreate,
    CustomerResponse,
    ImageUploadCreate,
    ImageUploadResponse,
)
from app.schemas.conversation import (
    ConversationState,
    DiagnosticInfo,
    SchedulingInfo,
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
