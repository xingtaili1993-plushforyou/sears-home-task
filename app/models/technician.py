"""Technician-related database models."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, ForeignKey, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


# Association table for technician specialties
technician_specialty_association = Table(
    "technician_specialty_association",
    Base.metadata,
    Column("technician_id", Integer, ForeignKey("technicians.id"), primary_key=True),
    Column("specialty_id", Integer, ForeignKey("specialties.id"), primary_key=True),
)


class ApplianceType:
    """Constants for supported appliance types."""
    WASHER = "washer"
    DRYER = "dryer"
    REFRIGERATOR = "refrigerator"
    DISHWASHER = "dishwasher"
    OVEN = "oven"
    MICROWAVE = "microwave"
    HVAC = "hvac"
    GARBAGE_DISPOSAL = "garbage_disposal"
    WATER_HEATER = "water_heater"
    FREEZER = "freezer"
    
    ALL_TYPES = [
        WASHER, DRYER, REFRIGERATOR, DISHWASHER, OVEN,
        MICROWAVE, HVAC, GARBAGE_DISPOSAL, WATER_HEATER, FREEZER
    ]


class Technician(Base, TimestampMixin):
    """Model representing a service technician."""
    
    __tablename__ = "technicians"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Personal info
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Employment
    employee_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, default=0)
    
    # Relationships
    specialties: Mapped[List["TechnicianSpecialty"]] = relationship(
        "TechnicianSpecialty",
        secondary=technician_specialty_association,
        back_populates="technicians"
    )
    service_areas: Mapped[List["TechnicianServiceArea"]] = relationship(
        "TechnicianServiceArea",
        back_populates="technician",
        cascade="all, delete-orphan"
    )
    time_slots: Mapped[List["TimeSlot"]] = relationship(
        "TimeSlot",
        back_populates="technician",
        cascade="all, delete-orphan"
    )
    appointments: Mapped[List["Appointment"]] = relationship(
        "Appointment",
        back_populates="technician"
    )
    
    @property
    def full_name(self) -> str:
        """Return the technician's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self) -> str:
        return f"<Technician {self.employee_id}: {self.full_name}>"


class TechnicianSpecialty(Base):
    """Model representing an appliance specialty/certification."""
    
    __tablename__ = "specialties"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    appliance_type: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Relationships
    technicians: Mapped[List["Technician"]] = relationship(
        "Technician",
        secondary=technician_specialty_association,
        back_populates="specialties"
    )
    
    def __repr__(self) -> str:
        return f"<Specialty: {self.appliance_type}>"


class TechnicianServiceArea(Base):
    """Model representing a zip code a technician services."""
    
    __tablename__ = "service_areas"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    technician_id: Mapped[int] = mapped_column(ForeignKey("technicians.id"), nullable=False)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relationships
    technician: Mapped["Technician"] = relationship(
        "Technician",
        back_populates="service_areas"
    )
    
    def __repr__(self) -> str:
        return f"<ServiceArea: {self.zip_code} (Tech: {self.technician_id})>"


# Import at bottom to avoid circular imports
from app.models.availability import TimeSlot, Appointment
