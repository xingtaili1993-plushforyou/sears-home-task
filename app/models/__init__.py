"""Database models for the Voice AI Diagnostic Agent."""

from app.models.base import Base
from app.models.technician import Technician, TechnicianSpecialty, TechnicianServiceArea, ApplianceType
from app.models.availability import TimeSlot, Appointment
from app.models.customer import Customer, ImageUploadRequest

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
