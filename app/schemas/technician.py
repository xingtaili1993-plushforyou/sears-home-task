"""Schemas for technician-related data."""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class SpecialtyResponse(BaseModel):
    """Schema for appliance specialty response."""
    id: int
    appliance_type: str
    description: Optional[str] = None
    
    class Config:
        from_attributes = True


class ServiceAreaResponse(BaseModel):
    """Schema for service area response."""
    id: int
    zip_code: str
    is_primary: bool
    
    class Config:
        from_attributes = True


class TechnicianBase(BaseModel):
    """Base schema for technician data."""
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    employee_id: str
    years_experience: int = 0


class TechnicianCreate(TechnicianBase):
    """Schema for creating a new technician."""
    specialty_ids: List[int] = []
    zip_codes: List[str] = []


class TechnicianResponse(TechnicianBase):
    """Schema for technician response."""
    id: int
    is_active: bool
    created_at: datetime
    specialties: List[SpecialtyResponse] = []
    service_areas: List[ServiceAreaResponse] = []
    
    class Config:
        from_attributes = True


class TechnicianWithAvailability(TechnicianResponse):
    """Schema for technician with available slots."""
    available_slots: List["TimeSlotResponse"] = []
    
    class Config:
        from_attributes = True


# Import at end to avoid circular import
from app.schemas.appointment import TimeSlotResponse
TechnicianWithAvailability.model_rebuild()
