"""Service for technician-related operations."""

from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_

from app.models import Technician, TechnicianSpecialty, TechnicianServiceArea, TimeSlot


class TechnicianService:
    """Service class for technician operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all_technicians(self, active_only: bool = True) -> List[Technician]:
        """Get all technicians with their specialties and service areas."""
        query = self.db.query(Technician).options(
            joinedload(Technician.specialties),
            joinedload(Technician.service_areas)
        )
        
        if active_only:
            query = query.filter(Technician.is_active == True)
        
        return query.all()
    
    def get_technician_by_id(self, technician_id: int) -> Optional[Technician]:
        """Get a specific technician by ID."""
        return self.db.query(Technician).options(
            joinedload(Technician.specialties),
            joinedload(Technician.service_areas),
            joinedload(Technician.time_slots)
        ).filter(Technician.id == technician_id).first()
    
    def get_technician_by_employee_id(self, employee_id: str) -> Optional[Technician]:
        """Get a technician by their employee ID."""
        return self.db.query(Technician).filter(
            Technician.employee_id == employee_id
        ).first()
    
    def find_technicians_by_criteria(
        self,
        zip_code: str,
        appliance_type: str,
        target_date: Optional[date] = None
    ) -> List[Technician]:
        """
        Find technicians who:
        - Service the given zip code
        - Are certified for the appliance type
        - Have availability on the target date (if specified)
        """
        # Start with base query
        query = self.db.query(Technician).filter(Technician.is_active == True)
        
        # Join and filter by service area
        query = query.join(TechnicianServiceArea).filter(
            TechnicianServiceArea.zip_code == zip_code
        )
        
        # Join and filter by specialty
        query = query.join(Technician.specialties).filter(
            TechnicianSpecialty.appliance_type == appliance_type
        )
        
        # If a date is specified, check for availability
        if target_date:
            query = query.join(Technician.time_slots).filter(
                and_(
                    TimeSlot.date == target_date,
                    TimeSlot.is_available == True,
                    TimeSlot.is_blocked == False
                )
            )
        
        # Eager load relationships
        query = query.options(
            joinedload(Technician.specialties),
            joinedload(Technician.service_areas),
            joinedload(Technician.time_slots)
        )
        
        return query.distinct().all()
    
    def get_all_specialties(self) -> List[TechnicianSpecialty]:
        """Get all available appliance specialties."""
        return self.db.query(TechnicianSpecialty).all()
    
    def get_service_areas_for_technician(
        self, 
        technician_id: int
    ) -> List[TechnicianServiceArea]:
        """Get all service areas for a technician."""
        return self.db.query(TechnicianServiceArea).filter(
            TechnicianServiceArea.technician_id == technician_id
        ).all()
    
    def get_technicians_by_zip_code(self, zip_code: str) -> List[Technician]:
        """Get all technicians who service a specific zip code."""
        return self.db.query(Technician).join(TechnicianServiceArea).filter(
            and_(
                TechnicianServiceArea.zip_code == zip_code,
                Technician.is_active == True
            )
        ).options(
            joinedload(Technician.specialties)
        ).all()
    
    def get_technicians_by_specialty(self, appliance_type: str) -> List[Technician]:
        """Get all technicians certified for an appliance type."""
        return self.db.query(Technician).join(Technician.specialties).filter(
            and_(
                TechnicianSpecialty.appliance_type == appliance_type,
                Technician.is_active == True
            )
        ).options(
            joinedload(Technician.service_areas)
        ).all()
