"""Schemas for conversation state management."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class ConversationPhase(str, Enum):
    """Phases of the diagnostic conversation."""
    GREETING = "greeting"
    IDENTIFY_APPLIANCE = "identify_appliance"
    GATHER_SYMPTOMS = "gather_symptoms"
    DIAGNOSTIC = "diagnostic"
    TROUBLESHOOTING = "troubleshooting"
    SCHEDULING = "scheduling"
    CONFIRMATION = "confirmation"
    IMAGE_CAPTURE = "image_capture"
    CLOSING = "closing"


class DiagnosticInfo(BaseModel):
    """Information gathered during diagnosis."""
    appliance_type: Optional[str] = None
    appliance_brand: Optional[str] = None
    appliance_model: Optional[str] = None
    appliance_age_years: Optional[int] = None
    
    # Symptoms and issues
    primary_symptom: Optional[str] = None
    additional_symptoms: List[str] = Field(default_factory=list)
    error_codes: List[str] = Field(default_factory=list)
    unusual_sounds: Optional[str] = None
    when_started: Optional[str] = None
    
    # Troubleshooting attempted
    troubleshooting_steps_tried: List[str] = Field(default_factory=list)
    troubleshooting_results: Dict[str, str] = Field(default_factory=dict)
    
    # Resolution
    issue_resolved: bool = False
    resolution_notes: Optional[str] = None


class SchedulingInfo(BaseModel):
    """Information for scheduling a technician visit."""
    customer_zip_code: Optional[str] = None
    preferred_dates: List[str] = Field(default_factory=list)
    preferred_time_of_day: Optional[str] = None  # morning, afternoon, any
    
    # Selected appointment
    selected_technician_id: Optional[int] = None
    selected_time_slot_id: Optional[int] = None
    
    # Customer contact
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None


class ConversationState(BaseModel):
    """Complete state of a voice conversation."""
    
    # Identifiers
    call_sid: str
    customer_phone: str
    
    # Timing
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: datetime = Field(default_factory=datetime.utcnow)
    
    # Conversation tracking
    phase: ConversationPhase = ConversationPhase.GREETING
    turn_count: int = 0
    
    # Gathered information
    diagnostic: DiagnosticInfo = Field(default_factory=DiagnosticInfo)
    scheduling: SchedulingInfo = Field(default_factory=SchedulingInfo)
    
    # Customer info
    customer_id: Optional[int] = None
    
    # Conversation history (for context)
    conversation_summary: str = ""
    key_facts: List[str] = Field(default_factory=list)
    
    # Image upload
    image_upload_requested: bool = False
    image_upload_token: Optional[str] = None
    image_analysis_result: Optional[str] = None
    
    # Outcome
    appointment_id: Optional[int] = None
    appointment_confirmation: Optional[str] = None
    
    def update_interaction(self) -> None:
        """Update the last interaction timestamp."""
        self.last_interaction = datetime.utcnow()
        self.turn_count += 1
    
    def add_fact(self, fact: str) -> None:
        """Add a key fact to the conversation."""
        if fact not in self.key_facts:
            self.key_facts.append(fact)
    
    class Config:
        from_attributes = True
