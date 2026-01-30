"""Schemas for customer-related data."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr


class CustomerBase(BaseModel):
    """Base schema for customer data."""
    phone: str
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer."""
    pass


class CustomerResponse(CustomerBase):
    """Schema for customer response."""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ImageUploadCreate(BaseModel):
    """Schema for creating an image upload request."""
    customer_id: int
    email: EmailStr
    appliance_type: Optional[str] = None
    issue_description: Optional[str] = None
    call_sid: Optional[str] = None


class ImageUploadResponse(BaseModel):
    """Schema for image upload request response."""
    id: int
    upload_token: str
    upload_url: str
    email_sent_to: str
    expires_at: datetime
    is_used: bool
    image_analysis: Optional[str] = None
    
    class Config:
        from_attributes = True
