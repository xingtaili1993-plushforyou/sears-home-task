"""Availability and appointment models."""

from datetime import datetime, date, time
from typing import Optional
from enum import Enum
from sqlalchemy import String, Boolean, ForeignKey, Date, Time, Text, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AppointmentStatus(str, Enum):
    """Status options for appointments."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class TimeSlot(Base, TimestampMixin):
    """Model representing an available time slot for a technician."""
    
    __tablename__ = "time_slots"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id"), nullable=False)
    
    # Schedule details
    date: Mapped[date] = mapped_column(Date, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    
    # Status
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Relationships
    technician: Mapped["Technician"] = relationship(
        "Technician",
        back_populates="time_slots"
    )
    appointment: Mapped[Optional["Appointment"]] = relationship(
        "Appointment",
        back_populates="time_slot",
        uselist=False
    )
    
    @property
    def duration_minutes(self) -> int:
        """Calculate the duration of the time slot in minutes."""
        start_dt = datetime.combine(self.date, self.start_time)
        end_dt = datetime.combine(self.date, self.end_time)
        return int((end_dt - start_dt).total_seconds() / 60)
    
    def __repr__(self) -> str:
        return f"<TimeSlot {self.date} {self.start_time}-{self.end_time}>"


class Appointment(Base, TimestampMixin):
    """Model representing a scheduled service appointment."""
    
    __tablename__ = "appointments"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Foreign keys
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id"), nullable=False)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    time_slot_id: Mapped[int] = mapped_column(ForeignKey("time_slots.id"), nullable=False)
    
    # Appointment details
    confirmation_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        SQLEnum(AppointmentStatus),
        default=AppointmentStatus.SCHEDULED,
        nullable=False
    )
    
    # Service details
    appliance_type: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    symptoms: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Notes
    customer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technician_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Call reference
    call_sid: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    technician: Mapped["Technician"] = relationship(
        "Technician",
        back_populates="appointments"
    )
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="appointments"
    )
    time_slot: Mapped["TimeSlot"] = relationship(
        "TimeSlot",
        back_populates="appointment"
    )
    
    def __repr__(self) -> str:
        return f"<Appointment {self.confirmation_number}: {self.status.value}>"


# Import at bottom to avoid circular imports
from app.models.technician import Technician
from app.models.customer import Customer
