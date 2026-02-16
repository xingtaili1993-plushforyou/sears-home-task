"""Database models for the Voice AI Diagnostic Agent."""

from app.models.availability import Appointment, TimeSlot
from app.models.base import Base
from app.models.customer import Customer, ImageUploadRequest
from app.models.technician import (
    ApplianceType,
    Technician,
    TechnicianServiceArea,
    TechnicianSpecialty,
)

__all__ = [
    "Base",
    "Technician",
    "TechnicianSpecialty",
    "TechnicianServiceArea",
    "ApplianceType",
    "TimeSlot",
    "Appointment",
    "Customer",
    "ImageUploadRequest",
]
