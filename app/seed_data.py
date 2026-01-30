"""Seed data for the database with sample technicians and availability."""

import random
from datetime import datetime, date, time, timedelta
from typing import List

from sqlalchemy.orm import Session

from app.models import (
    Technician, 
    TechnicianSpecialty, 
    TechnicianServiceArea,
    TimeSlot,
    ApplianceType
)


# Sample technician data
TECHNICIANS = [
    {
        "first_name": "Michael",
        "last_name": "Johnson",
        "email": "mjohnson@searshomeservices.com",
        "phone": "555-101-0001",
        "employee_id": "TECH001",
        "years_experience": 12,
        "specialties": ["washer", "dryer", "dishwasher"],
        "zip_codes": ["90210", "90211", "90212", "90213"],
    },
    {
        "first_name": "Sarah",
        "last_name": "Williams",
        "email": "swilliams@searshomeservices.com",
        "phone": "555-101-0002",
        "employee_id": "TECH002",
        "years_experience": 8,
        "specialties": ["refrigerator", "freezer", "dishwasher"],
        "zip_codes": ["90210", "90214", "90215", "90216"],
    },
    {
        "first_name": "David",
        "last_name": "Martinez",
        "email": "dmartinez@searshomeservices.com",
        "phone": "555-101-0003",
        "employee_id": "TECH003",
        "years_experience": 15,
        "specialties": ["hvac", "water_heater"],
        "zip_codes": ["90210", "90211", "90217", "90218"],
    },
    {
        "first_name": "Jennifer",
        "last_name": "Brown",
        "email": "jbrown@searshomeservices.com",
        "phone": "555-101-0004",
        "employee_id": "TECH004",
        "years_experience": 6,
        "specialties": ["oven", "microwave", "dishwasher"],
        "zip_codes": ["90215", "90216", "90219", "90220"],
    },
    {
        "first_name": "Robert",
        "last_name": "Davis",
        "email": "rdavis@searshomeservices.com",
        "phone": "555-101-0005",
        "employee_id": "TECH005",
        "years_experience": 10,
        "specialties": ["washer", "dryer", "refrigerator", "freezer"],
        "zip_codes": ["90211", "90212", "90221", "90222"],
    },
    {
        "first_name": "Emily",
        "last_name": "Wilson",
        "email": "ewilson@searshomeservices.com",
        "phone": "555-101-0006",
        "employee_id": "TECH006",
        "years_experience": 4,
        "specialties": ["garbage_disposal", "dishwasher", "microwave"],
        "zip_codes": ["90213", "90214", "90223", "90224"],
    },
    {
        "first_name": "James",
        "last_name": "Anderson",
        "email": "janderson@searshomeservices.com",
        "phone": "555-101-0007",
        "employee_id": "TECH007",
        "years_experience": 20,
        "specialties": ["hvac", "water_heater", "refrigerator"],
        "zip_codes": ["90217", "90218", "90225", "90226"],
    },
    {
        "first_name": "Lisa",
        "last_name": "Thomas",
        "email": "lthomas@searshomeservices.com",
        "phone": "555-101-0008",
        "employee_id": "TECH008",
        "years_experience": 7,
        "specialties": ["washer", "dryer", "oven"],
        "zip_codes": ["90219", "90220", "90227", "90228"],
    },
    {
        "first_name": "Daniel",
        "last_name": "Garcia",
        "email": "dgarcia@searshomeservices.com",
        "phone": "555-101-0009",
        "employee_id": "TECH009",
        "years_experience": 11,
        "specialties": ["refrigerator", "freezer", "hvac"],
        "zip_codes": ["90221", "90222", "90229", "90230"],
    },
    {
        "first_name": "Amanda",
        "last_name": "Miller",
        "email": "amiller@searshomeservices.com",
        "phone": "555-101-0010",
        "employee_id": "TECH010",
        "years_experience": 9,
        "specialties": ["dishwasher", "garbage_disposal", "microwave", "oven"],
        "zip_codes": ["90223", "90224", "90210", "90211"],
    },
]


def create_specialties(db: Session) -> dict:
    """Create all appliance specialty records."""
    specialties = {}
    
    specialty_descriptions = {
        "washer": "Washing machine repair and maintenance",
        "dryer": "Dryer repair and maintenance",
        "refrigerator": "Refrigerator and fridge repair",
        "dishwasher": "Dishwasher repair and installation",
        "oven": "Oven, range, and stove repair",
        "microwave": "Microwave oven repair",
        "hvac": "Heating, ventilation, and air conditioning",
        "garbage_disposal": "Garbage disposal repair and installation",
        "water_heater": "Water heater repair and installation",
        "freezer": "Standalone freezer repair",
    }
    
    for appliance_type in ApplianceType.ALL_TYPES:
        specialty = TechnicianSpecialty(
            appliance_type=appliance_type,
            description=specialty_descriptions.get(appliance_type, "")
        )
        db.add(specialty)
        specialties[appliance_type] = specialty
    
    db.flush()
    return specialties


def create_time_slots(db: Session, technician: Technician, days_ahead: int = 14) -> List[TimeSlot]:
    """Create available time slots for a technician."""
    slots = []
    today = date.today()
    
    # Standard appointment windows
    slot_times = [
        (time(8, 0), time(10, 0)),   # 8 AM - 10 AM
        (time(10, 0), time(12, 0)),  # 10 AM - 12 PM
        (time(13, 0), time(15, 0)),  # 1 PM - 3 PM
        (time(15, 0), time(17, 0)),  # 3 PM - 5 PM
    ]
    
    for day_offset in range(1, days_ahead + 1):
        slot_date = today + timedelta(days=day_offset)
        
        # Skip weekends
        if slot_date.weekday() >= 5:
            continue
        
        # Randomly select which slots are available (simulate existing bookings)
        available_slots = random.sample(slot_times, random.randint(2, 4))
        
        for start, end in available_slots:
            slot = TimeSlot(
                technician_id=technician.id,
                date=slot_date,
                start_time=start,
                end_time=end,
                is_available=True,
                is_blocked=False
            )
            db.add(slot)
            slots.append(slot)
    
    return slots


def seed_database(db: Session) -> None:
    """Seed the database with sample data."""
    
    # Check if data already exists
    existing_techs = db.query(Technician).count()
    if existing_techs > 0:
        print(f"Database already has {existing_techs} technicians. Skipping seed.")
        return
    
    print("Seeding database with sample data...")
    
    # Create specialties first
    specialties = create_specialties(db)
    db.flush()
    
    # Create technicians
    for tech_data in TECHNICIANS:
        technician = Technician(
            first_name=tech_data["first_name"],
            last_name=tech_data["last_name"],
            email=tech_data["email"],
            phone=tech_data["phone"],
            employee_id=tech_data["employee_id"],
            years_experience=tech_data["years_experience"],
            is_active=True
        )
        db.add(technician)
        db.flush()
        
        # Add specialties
        for specialty_name in tech_data["specialties"]:
            if specialty_name in specialties:
                technician.specialties.append(specialties[specialty_name])
        
        # Add service areas
        for i, zip_code in enumerate(tech_data["zip_codes"]):
            service_area = TechnicianServiceArea(
                technician_id=technician.id,
                zip_code=zip_code,
                is_primary=(i == 0)
            )
            db.add(service_area)
        
        # Create time slots
        create_time_slots(db, technician)
        
        print(f"  Created technician: {technician.full_name}")
    
    db.commit()
    print(f"Database seeded with {len(TECHNICIANS)} technicians.")


def clear_and_reseed(db: Session) -> None:
    """Clear all data and reseed the database."""
    print("Clearing existing data...")
    
    # Delete in correct order due to foreign keys
    db.query(TimeSlot).delete()
    db.query(TechnicianServiceArea).delete()
    # Clear the association table
    db.execute(
        "DELETE FROM technician_specialty_association"
    )
    db.query(Technician).delete()
    db.query(TechnicianSpecialty).delete()
    db.commit()
    
    seed_database(db)


if __name__ == "__main__":
    from app.database import SessionLocal, init_db
    
    init_db()
    
    with SessionLocal() as db:
        seed_database(db)
