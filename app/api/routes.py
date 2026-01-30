"""General API routes for technicians, scheduling, and customers."""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import (
    TechnicianService,
    SchedulingService,
    CustomerService,
    DiagnosticService
)
from app.schemas import (
    TechnicianResponse,
    SpecialtyResponse,
    AvailableSlotResponse,
    AppointmentCreate,
    AppointmentResponse,
    CustomerCreate,
    CustomerResponse,
)

router = APIRouter()


# ============== Health Check ==============

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "SEARS Voice AI Diagnostic Agent"}


# ============== Technician Routes ==============

@router.get("/technicians", response_model=List[TechnicianResponse])
async def list_technicians(
    db: Session = Depends(get_db)
):
    """List all active technicians."""
    service = TechnicianService(db)
    return service.get_all_technicians()


@router.get("/technicians/{technician_id}", response_model=TechnicianResponse)
async def get_technician(
    technician_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific technician by ID."""
    service = TechnicianService(db)
    technician = service.get_technician_by_id(technician_id)
    if not technician:
        raise HTTPException(status_code=404, detail="Technician not found")
    return technician


@router.get("/technicians/search/by-criteria")
async def search_technicians(
    zip_code: str,
    appliance_type: str,
    target_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    """Find technicians matching zip code and appliance type."""
    service = TechnicianService(db)
    technicians = service.find_technicians_by_criteria(
        zip_code=zip_code,
        appliance_type=appliance_type,
        target_date=target_date
    )
    return [TechnicianResponse.model_validate(t) for t in technicians]


@router.get("/specialties", response_model=List[SpecialtyResponse])
async def list_specialties(
    db: Session = Depends(get_db)
):
    """List all appliance specialties."""
    service = TechnicianService(db)
    return service.get_all_specialties()


# ============== Scheduling Routes ==============

@router.get("/availability", response_model=List[AvailableSlotResponse])
async def get_available_slots(
    zip_code: str,
    appliance_type: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    time_preference: Optional[str] = Query(None, pattern="^(morning|afternoon|any)$"),
    db: Session = Depends(get_db)
):
    """
    Get available appointment slots for a zip code and appliance type.
    
    - **zip_code**: Customer's zip code
    - **appliance_type**: Type of appliance (washer, dryer, etc.)
    - **start_date**: Start of date range (default: tomorrow)
    - **end_date**: End of date range (default: 14 days from start)
    - **time_preference**: Preferred time of day (morning, afternoon, any)
    """
    service = SchedulingService(db)
    return service.get_available_slots(
        zip_code=zip_code,
        appliance_type=appliance_type,
        start_date=start_date,
        end_date=end_date,
        time_preference=time_preference
    )


@router.post("/appointments", response_model=AppointmentResponse)
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db)
):
    """Book a new appointment."""
    service = SchedulingService(db)
    
    appointment, error = service.book_appointment(
        customer_id=appointment_data.customer_id,
        time_slot_id=appointment_data.time_slot_id,
        appliance_type=appointment_data.appliance_type,
        issue_description=appointment_data.issue_description,
        symptoms=appointment_data.symptoms,
        customer_notes=appointment_data.customer_notes,
        call_sid=appointment_data.call_sid
    )
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    # Add extra fields for response
    response_data = AppointmentResponse.model_validate(appointment)
    response_data.technician_name = appointment.technician.full_name
    response_data.appointment_date = appointment.time_slot.date
    response_data.appointment_time = appointment.time_slot.start_time
    
    return response_data


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db)
):
    """Get appointment details by ID."""
    service = SchedulingService(db)
    appointment = service.get_appointment_by_id(appointment_id)
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    response_data = AppointmentResponse.model_validate(appointment)
    response_data.technician_name = appointment.technician.full_name
    response_data.appointment_date = appointment.time_slot.date
    response_data.appointment_time = appointment.time_slot.start_time
    
    return response_data


@router.get("/appointments/confirmation/{confirmation_number}")
async def get_appointment_by_confirmation(
    confirmation_number: str,
    db: Session = Depends(get_db)
):
    """Get appointment by confirmation number."""
    service = SchedulingService(db)
    appointment = service.get_appointment_by_confirmation(confirmation_number)
    
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    return service.format_appointment_details(appointment)


@router.delete("/appointments/{appointment_id}")
async def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db)
):
    """Cancel an appointment."""
    service = SchedulingService(db)
    success, error = service.cancel_appointment(appointment_id)
    
    if not success:
        raise HTTPException(status_code=400, detail=error)
    
    return {"message": "Appointment cancelled successfully"}


# ============== Customer Routes ==============

@router.post("/customers", response_model=CustomerResponse)
async def create_customer(
    customer_data: CustomerCreate,
    db: Session = Depends(get_db)
):
    """Create a new customer."""
    service = CustomerService(db)
    return service.create_customer(customer_data)


@router.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    db: Session = Depends(get_db)
):
    """Get customer by ID."""
    service = CustomerService(db)
    customer = service.get_customer_by_id(customer_id)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return customer


@router.get("/customers/phone/{phone}")
async def get_customer_by_phone(
    phone: str,
    db: Session = Depends(get_db)
):
    """Get customer by phone number."""
    service = CustomerService(db)
    customer = service.get_customer_by_phone(phone)
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    return CustomerResponse.model_validate(customer)


# ============== Diagnostic Routes ==============

@router.get("/diagnostics/appliances")
async def list_supported_appliances():
    """List all supported appliance types."""
    service = DiagnosticService()
    return {"appliances": service.get_supported_appliances()}


@router.get("/diagnostics/{appliance_type}/symptoms")
async def get_common_symptoms(appliance_type: str):
    """Get common symptoms for an appliance type."""
    service = DiagnosticService()
    symptoms = service.get_common_symptoms(appliance_type)
    return {"appliance_type": appliance_type, "symptoms": symptoms}


@router.get("/diagnostics/{appliance_type}/questions")
async def get_diagnostic_questions(appliance_type: str):
    """Get diagnostic questions for an appliance type."""
    service = DiagnosticService()
    questions = service.get_diagnostic_questions(appliance_type)
    return {"appliance_type": appliance_type, "questions": questions}


@router.post("/diagnostics/{appliance_type}/troubleshoot")
async def get_troubleshooting_steps(
    appliance_type: str,
    symptom: str = Query(..., description="The symptom to troubleshoot")
):
    """Get troubleshooting steps for a specific symptom."""
    service = DiagnosticService()
    steps = service.get_troubleshooting_steps(appliance_type, symptom)
    return {
        "appliance_type": appliance_type,
        "symptom": symptom,
        "troubleshooting_steps": steps
    }
