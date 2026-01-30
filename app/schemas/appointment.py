"""Schemas for appointment and scheduling data."""

from typing import Optional, List
from datetime import datetime, date, time
from pydantic import BaseModel

from app.models.availability import AppointmentStatus


class TimeSlotResponse(BaseModel):
    """Schema for time slot response."""
    id: int
    technician_id: int
    date: date
    start_time: time
    end_time: time
    is_available: bool
    
    class Config:
        from_attributes = True


class AvailableSlotResponse(BaseModel):
    """Schema for available slot with technician info."""
    slot_id: int
    technician_id: int
    technician_name: str
    date: date
    start_time: time
    end_time: time
    
    class Config:
        from_attributes = True


class AppointmentBase(BaseModel):
    """Base schema for appointment data."""
    appliance_type: str
    issue_description: str
    symptoms: Optional[str] = None
    customer_notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment."""
    technician_id: int
    customer_id: int
    time_slot_id: int
    call_sid: Optional[str] = None


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment."""
    status: Optional[AppointmentStatus] = None
    technician_notes: Optional[str] = None
    customer_notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    """Schema for appointment response."""
    id: int
    confirmation_number: str
    status: AppointmentStatus
    technician_id: int
    customer_id: int
    time_slot_id: int
    call_sid: Optional[str] = None
    created_at: datetime
    
    # Nested info
    technician_name: Optional[str] = None
    appointment_date: Optional[date] = None
    appointment_time: Optional[time] = None
    
    class Config:
        from_attributes = True
