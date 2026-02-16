"""Service for customer-related operations."""

import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import Appointment, Customer
from app.schemas.customer import CustomerCreate

logger = logging.getLogger(__name__)


class CustomerService:
    """Service class for customer operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_customer(self, phone: str) -> Customer:
        """
        Get an existing customer by phone or create a new one.
        Used when receiving an inbound call.
        """
        customer = self.db.query(Customer).filter(Customer.phone == phone).first()

        if not customer:
            customer = Customer(phone=phone)
            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)

        return customer

    def get_customer_by_id(self, customer_id: int) -> Optional[Customer]:
        """Get a customer by ID."""
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def get_customer_by_phone(self, phone: str) -> Optional[Customer]:
        """Get a customer by phone number."""
        return self.db.query(Customer).filter(Customer.phone == phone).first()

    def get_customer_history(self, customer_id: int) -> List[str]:
        """
        Return a list of human-readable history items for a returning customer.
        This is injected into the session so the agent can greet them personally.
        """
        facts: List[str] = []
        try:
            appointments = (
                self.db.query(Appointment)
                .filter(Appointment.customer_id == customer_id)
                .order_by(Appointment.created_at.desc())
                .limit(5)
                .all()
            )
            if appointments:
                facts.append(
                    f"Returning customer with {len(appointments)} "
                    f"previous appointment(s)."
                )
                latest = appointments[0]
                facts.append(
                    f"Most recent appointment: {latest.appliance_type} - "
                    f"{latest.issue_description} "
                    f"(status: {latest.status.value})"
                )
        except Exception as e:
            logger.warning(f"Could not fetch customer history: {e}")
        return facts

    def update_customer(self, customer_id: int, **kwargs) -> Optional[Customer]:
        """
        Update customer information.

        Accepts any valid customer fields as kwargs.
        """
        customer = self.get_customer_by_id(customer_id)
        if not customer:
            return None

        allowed_fields = [
            "email",
            "first_name",
            "last_name",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "zip_code",
            "preferred_contact_method",
        ]

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                setattr(customer, field, value)

        self.db.commit()
        self.db.refresh(customer)
        return customer

    def create_customer(self, customer_data: CustomerCreate) -> Customer:
        """Create a new customer."""
        customer = Customer(**customer_data.model_dump())
        self.db.add(customer)
        self.db.commit()
        self.db.refresh(customer)
        return customer
