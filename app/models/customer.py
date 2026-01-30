"""Customer-related database models."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Customer(Base, TimestampMixin):
    """Model representing a customer who calls for service."""
    
    __tablename__ = "customers"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    
    # Contact info
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Address
    address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    # Preferences
    preferred_contact_method: Mapped[str] = mapped_column(String(20), default="phone")
    
    # Relationships
    appointments: Mapped[List["Appointment"]] = relationship(
        "Appointment",
        back_populates="customer"
    )
    image_uploads: Mapped[List["ImageUploadRequest"]] = relationship(
        "ImageUploadRequest",
        back_populates="customer",
        cascade="all, delete-orphan"
    )
    
    @property
    def full_name(self) -> Optional[str]:
        """Return the customer's full name if available."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.last_name
    
    def __repr__(self) -> str:
        return f"<Customer {self.id}: {self.phone}>"


class ImageUploadRequest(Base, TimestampMixin):
    """Model for tracking image upload requests sent to customers."""
    
    __tablename__ = "image_upload_requests"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False)
    
    # Unique token for the upload link
    upload_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    
    # Email tracking
    email_sent_to: Mapped[str] = mapped_column(String(255), nullable=False)
    email_sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Expiry
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Upload status
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uploaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Image details
    image_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    image_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Context from the call
    appliance_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    issue_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    call_sid: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="image_uploads"
    )
    
    @property
    def is_expired(self) -> bool:
        """Check if the upload link has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_valid(self) -> bool:
        """Check if the upload link is still valid."""
        return not self.is_used and not self.is_expired
    
    def __repr__(self) -> str:
        return f"<ImageUploadRequest {self.upload_token[:8]}... for Customer {self.customer_id}>"


# Import at bottom to avoid circular imports
from app.models.availability import Appointment
