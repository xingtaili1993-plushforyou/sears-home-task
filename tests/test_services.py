"""Tests for service layer."""

import pytest
from datetime import date, time, timedelta

from app.services import DiagnosticService, CustomerService, SchedulingService
from app.models import Customer, Technician, TechnicianSpecialty, TechnicianServiceArea, TimeSlot


class TestDiagnosticService:
    """Tests for the diagnostic service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = DiagnosticService()
    
    def test_get_supported_appliances(self):
        """Test getting list of supported appliances."""
        appliances = self.service.get_supported_appliances()
        assert len(appliances) > 0
        assert "washer" in appliances
        assert "dryer" in appliances
        assert "refrigerator" in appliances
    
    def test_normalize_appliance_type(self):
        """Test appliance type normalization."""
        assert self.service.normalize_appliance_type("washer") == "washer"
        assert self.service.normalize_appliance_type("Washing Machine") == "washer"
        assert self.service.normalize_appliance_type("fridge") == "refrigerator"
        assert self.service.normalize_appliance_type("AC") == "hvac"
        assert self.service.normalize_appliance_type("unknown") is None
    
    def test_get_common_symptoms(self):
        """Test getting symptoms for appliance."""
        symptoms = self.service.get_common_symptoms("washer")
        assert len(symptoms) > 0
        assert "won't start" in symptoms
    
    def test_get_common_symptoms_unknown(self):
        """Test getting symptoms for unknown appliance."""
        symptoms = self.service.get_common_symptoms("unknown_appliance")
        assert symptoms == []
    
    def test_get_troubleshooting_steps(self):
        """Test getting troubleshooting steps."""
        steps = self.service.get_troubleshooting_steps("washer", "won't start")
        assert len(steps) > 0
    
    def test_get_troubleshooting_steps_default(self):
        """Test fallback to default steps for unknown symptom."""
        steps = self.service.get_troubleshooting_steps("washer", "unknown_symptom")
        assert len(steps) > 0
        # Should return default troubleshooting steps
    
    def test_match_symptom(self):
        """Test symptom matching."""
        matched, score = self.service.match_symptom("washer", "my washer won't start")
        assert matched is not None
        assert score > 0
    
    def test_should_schedule_technician(self):
        """Test technician scheduling recommendation."""
        # Issue resolved - no need for technician
        assert not self.service.should_schedule_technician(
            troubleshooting_attempted=["step1"],
            issue_resolved=True
        )
        
        # High severity - need technician
        assert self.service.should_schedule_technician(
            troubleshooting_attempted=[],
            issue_resolved=False,
            symptom_severity="high"
        )
        
        # Multiple steps tried, not resolved - need technician
        assert self.service.should_schedule_technician(
            troubleshooting_attempted=["step1", "step2"],
            issue_resolved=False
        )


class TestCustomerService:
    """Tests for the customer service."""
    
    def test_get_or_create_customer_new(self, db_session):
        """Test creating new customer."""
        service = CustomerService(db_session)
        phone = "+15551234567"
        
        customer = service.get_or_create_customer(phone)
        
        assert customer is not None
        assert customer.phone == phone
        assert customer.id is not None
    
    def test_get_or_create_customer_existing(self, db_session):
        """Test getting existing customer."""
        service = CustomerService(db_session)
        phone = "+15551234567"
        
        # Create customer
        customer1 = service.get_or_create_customer(phone)
        
        # Should return same customer
        customer2 = service.get_or_create_customer(phone)
        
        assert customer1.id == customer2.id
    
    def test_update_customer(self, db_session):
        """Test updating customer info."""
        service = CustomerService(db_session)
        
        # Create customer
        customer = service.get_or_create_customer("+15551234567")
        
        # Update
        updated = service.update_customer(
            customer.id,
            first_name="John",
            last_name="Doe",
            email="john@example.com"
        )
        
        assert updated.first_name == "John"
        assert updated.last_name == "Doe"
        assert updated.email == "john@example.com"


class TestSchedulingService:
    """Tests for the scheduling service."""
    
    def test_generate_confirmation_number(self, db_session):
        """Test confirmation number generation."""
        service = SchedulingService(db_session)
        
        conf1 = service._generate_confirmation_number()
        conf2 = service._generate_confirmation_number()
        
        assert conf1.startswith("SHS-")
        assert len(conf1) == 12  # SHS- + 8 chars
        assert conf1 != conf2  # Should be unique
    
    def test_get_available_slots_no_technicians(self, db_session):
        """Test availability with no technicians."""
        service = SchedulingService(db_session)
        
        slots = service.get_available_slots(
            zip_code="90210",
            appliance_type="washer"
        )
        
        assert slots == []
