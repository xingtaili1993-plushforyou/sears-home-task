"""Service for scheduling and appointment operations."""

import secrets
import string
from typing import List, Optional, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from app.models import (
    Technician, 
    TimeSlot, 
    Appointment, 
    Customer,
    TechnicianServiceArea,
    TechnicianSpecialty
)
from app.models.availability import AppointmentStatus
from app.schemas.appointment import AvailableSlotResponse


class SchedulingService:
    """Service class for scheduling operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _generate_confirmation_number(self) -> str:
        """Generate a unique confirmation number."""
        prefix = "SHS"
        random_part = ''.join(
            secrets.choice(string.ascii_uppercase + string.digits) 
            for _ in range(8)
        )
        return f"{prefix}-{random_part}"
    
    def get_available_slots(
        self,
        zip_code: str,
        appliance_type: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        time_preference: Optional[str] = None  # "morning", "afternoon", "any"
    ) -> List[AvailableSlotResponse]:
        """
        Find available time slots matching the criteria.
        
        Returns slots with technician info for presentation to the caller.
        """
        # Default date range: next 14 days
        if not start_date:
            start_date = date.today() + timedelta(days=1)
        if not end_date:
            end_date = start_date + timedelta(days=14)
        
        # Query for available slots
        query = self.db.query(
            TimeSlot,
            Technician
        ).join(
            Technician
        ).join(
            TechnicianServiceArea
        ).join(
            Technician.specialties
        ).filter(
            and_(
                TimeSlot.is_available == True,
                TimeSlot.is_blocked == False,
                TimeSlot.date >= start_date,
                TimeSlot.date <= end_date,
                TechnicianServiceArea.zip_code == zip_code,
                TechnicianSpecialty.appliance_type == appliance_type,
                Technician.is_active == True
            )
        )
        
        # Apply time preference filter
        if time_preference == "morning":
            from datetime import time as dt_time
            query = query.filter(TimeSlot.start_time < dt_time(12, 0))
        elif time_preference == "afternoon":
            from datetime import time as dt_time
            query = query.filter(TimeSlot.start_time >= dt_time(12, 0))
        
        # Order by date and time
        query = query.order_by(TimeSlot.date, TimeSlot.start_time)
        
        results = query.distinct().all()
        
        # Convert to response format
        available_slots = []
        for slot, technician in results:
            available_slots.append(AvailableSlotResponse(
                slot_id=slot.id,
                technician_id=technician.id,
                technician_name=technician.full_name,
                date=slot.date,
                start_time=slot.start_time,
                end_time=slot.end_time
            ))
        
        return available_slots
    
    def get_slot_by_id(self, slot_id: int) -> Optional[TimeSlot]:
        """Get a specific time slot by ID."""
        return self.db.query(TimeSlot).filter(TimeSlot.id == slot_id).first()
    
    def book_appointment(
        self,
        customer_id: int,
        time_slot_id: int,
        appliance_type: str,
        issue_description: str,
        symptoms: Optional[str] = None,
        customer_notes: Optional[str] = None,
        call_sid: Optional[str] = None
    ) -> Tuple[Optional[Appointment], Optional[str]]:
        """
        Book an appointment for a customer.
        
        Returns:
            Tuple of (Appointment, None) on success
            Tuple of (None, error_message) on failure
        """
        # Get the time slot
        slot = self.db.query(TimeSlot).filter(TimeSlot.id == time_slot_id).first()
        
        if not slot:
            return None, "Time slot not found"
        
        if not slot.is_available:
            return None, "This time slot is no longer available"
        
        if slot.is_blocked:
            return None, "This time slot is blocked"
        
        # Mark slot as unavailable
        slot.is_available = False
        
        # Create the appointment
        appointment = Appointment(
            technician_id=slot.technician_id,
            customer_id=customer_id,
            time_slot_id=time_slot_id,
            confirmation_number=self._generate_confirmation_number(),
            status=AppointmentStatus.SCHEDULED,
            appliance_type=appliance_type,
            issue_description=issue_description,
            symptoms=symptoms,
            customer_notes=customer_notes,
            call_sid=call_sid
        )
        
        self.db.add(appointment)
        self.db.commit()
        self.db.refresh(appointment)
        
        return appointment, None
    
    def get_appointment_by_id(self, appointment_id: int) -> Optional[Appointment]:
        """Get an appointment by ID with related data."""
        return self.db.query(Appointment).options(
            joinedload(Appointment.technician),
            joinedload(Appointment.customer),
            joinedload(Appointment.time_slot)
        ).filter(Appointment.id == appointment_id).first()
    
    def get_appointment_by_confirmation(
        self, 
        confirmation_number: str
    ) -> Optional[Appointment]:
        """Get an appointment by confirmation number."""
        return self.db.query(Appointment).options(
            joinedload(Appointment.technician),
            joinedload(Appointment.customer),
            joinedload(Appointment.time_slot)
        ).filter(
            Appointment.confirmation_number == confirmation_number
        ).first()
    
    def cancel_appointment(
        self, 
        appointment_id: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Cancel an appointment and free up the time slot.
        
        Returns:
            Tuple of (success, error_message)
        """
        appointment = self.db.query(Appointment).filter(
            Appointment.id == appointment_id
        ).first()
        
        if not appointment:
            return False, "Appointment not found"
        
        if appointment.status in [
            AppointmentStatus.COMPLETED, 
            AppointmentStatus.CANCELLED
        ]:
            return False, f"Cannot cancel appointment with status: {appointment.status.value}"
        
        # Update appointment status
        appointment.status = AppointmentStatus.CANCELLED
        
        # Free up the time slot
        slot = self.db.query(TimeSlot).filter(
            TimeSlot.id == appointment.time_slot_id
        ).first()
        if slot:
            slot.is_available = True
        
        self.db.commit()
        return True, None
    
    def get_appointments_for_customer(
        self, 
        customer_id: int,
        include_past: bool = False
    ) -> List[Appointment]:
        """Get all appointments for a customer."""
        query = self.db.query(Appointment).options(
            joinedload(Appointment.technician),
            joinedload(Appointment.time_slot)
        ).filter(Appointment.customer_id == customer_id)
        
        if not include_past:
            query = query.join(TimeSlot).filter(
                TimeSlot.date >= date.today()
            )
        
        return query.order_by(Appointment.created_at.desc()).all()
    
    def format_appointment_details(self, appointment: Appointment) -> dict:
        """Format appointment details for voice response."""
        slot = appointment.time_slot
        technician = appointment.technician
        
        # Format time nicely
        start_time = slot.start_time.strftime("%I:%M %p").lstrip("0")
        end_time = slot.end_time.strftime("%I:%M %p").lstrip("0")
        
        # Format date nicely
        date_str = slot.date.strftime("%A, %B %d")
        
        return {
            "confirmation_number": appointment.confirmation_number,
            "date": date_str,
            "time_window": f"{start_time} to {end_time}",
            "technician_name": technician.full_name,
            "appliance_type": appointment.appliance_type,
            "issue_description": appointment.issue_description
        }
