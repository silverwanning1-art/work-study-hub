"""Business logic of the invoice plugin. Every public method is one transaction."""

from collections.abc import Callable
from datetime import date
from typing import NoReturn

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from action_invoice.errors import NotFoundError
from action_invoice.models import Customer, Profile, Project
from action_invoice.schemas import (
    CustomerIn,
    CustomerList,
    CustomerOut,
    ProfileData,
    ProjectIn,
    ProjectList,
    ProjectOut,
)

PROFILE_ID = 1


class InvoiceService:
    """Master data, drafts and the invoice lifecycle."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        today: Callable[[], date] = date.today,
    ) -> None:
        self._sessions = session_factory
        self._today = today

    # --- profile ---

    def get_profile(self) -> ProfileData:
        """Return the issuer's master data (defaults while still empty)."""
        with self._sessions() as session:
            profile = session.get(Profile, PROFILE_ID)
            if profile is None:
                return ProfileData()
            return ProfileData.model_validate(profile, from_attributes=True)

    def save_profile(self, data: ProfileData) -> ProfileData:
        """Replace the issuer's master data."""
        with self._sessions.begin() as session:
            profile = session.get(Profile, PROFILE_ID) or Profile(id=PROFILE_ID)
            for field, value in data.model_dump().items():
                setattr(profile, field, value)
            session.add(profile)
        return data

    # --- customers ---

    def list_customers(self) -> CustomerList:
        """Return all customers ordered by name."""
        with self._sessions() as session:
            rows = session.scalars(select(Customer).order_by(Customer.name)).all()
            return CustomerList(
                customers=[CustomerOut.model_validate(c, from_attributes=True) for c in rows]
            )

    def save_customer(self, data: CustomerIn) -> CustomerOut:
        """Create or update a customer."""
        with self._sessions.begin() as session:
            if data.id is None:
                customer = Customer(name=data.name)
            else:
                customer = session.get(Customer, data.id) or _missing("Kunde")
            for field, value in data.model_dump(exclude={"id"}).items():
                setattr(customer, field, value)
            session.add(customer)
            session.flush()
            return CustomerOut.model_validate(customer, from_attributes=True)

    # --- projects ---

    def list_projects(self, customer_id: int | None = None) -> ProjectList:
        """Return projects, optionally limited to one customer."""
        with self._sessions() as session:
            query = select(Project).order_by(Project.name)
            if customer_id is not None:
                query = query.where(Project.customer_id == customer_id)
            rows = session.scalars(query).all()
            return ProjectList(
                projects=[ProjectOut.model_validate(p, from_attributes=True) for p in rows]
            )

    def save_project(self, data: ProjectIn) -> ProjectOut:
        """Create or update a project of an existing customer."""
        with self._sessions.begin() as session:
            if session.get(Customer, data.customer_id) is None:
                _missing("Kunde")
            if data.id is None:
                project = Project(customer_id=data.customer_id, name=data.name)
            else:
                project = session.get(Project, data.id) or _missing("Projekt")
            for field, value in data.model_dump(exclude={"id"}).items():
                setattr(project, field, value)
            session.add(project)
            session.flush()
            return ProjectOut.model_validate(project, from_attributes=True)


def _missing(what: str) -> NoReturn:
    raise NotFoundError(f"{what} nicht gefunden")
