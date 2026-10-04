"""Business logic of the invoice plugin. Every public method is one transaction."""

from collections.abc import Callable
from datetime import date
from typing import NoReturn

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from action_invoice import calc
from action_invoice.errors import (
    ImmutableInvoiceError,
    InvalidInputError,
    NotFoundError,
)
from action_invoice.models import (
    Customer,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    Profile,
    Project,
)
from action_invoice.schemas import (
    CustomerIn,
    CustomerList,
    CustomerOut,
    InvoiceDraftIn,
    InvoiceList,
    InvoiceOut,
    ItemOut,
    ProfileData,
    ProjectIn,
    ProjectList,
    ProjectOut,
    TaxLine,
    TotalsOut,
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

    # --- invoices ---

    def list_invoices(self, status: str | None = None) -> InvoiceList:
        """Return invoices, newest first, optionally filtered by status."""
        with self._sessions() as session:
            query = select(Invoice).order_by(Invoice.id.desc())
            if status is not None:
                query = query.where(Invoice.status == status)
            rows = session.scalars(query).all()
            exempt = self._is_exempt(session)
            return InvoiceList(invoices=[_to_out(session, i, exempt) for i in rows])

    def get_invoice(self, invoice_id: int) -> InvoiceOut:
        """Return one invoice."""
        with self._sessions() as session:
            invoice = session.get(Invoice, invoice_id) or _missing("Rechnung")
            return _to_out(session, invoice, self._is_exempt(session))

    def save_draft(self, data: InvoiceDraftIn) -> InvoiceOut:
        """Create a draft, or replace an existing draft completely."""
        if (
            data.service_start is not None
            and data.service_end is not None
            and data.service_end < data.service_start
        ):
            raise InvalidInputError("Das Leistungsende liegt vor dem Leistungsbeginn")
        with self._sessions.begin() as session:
            if session.get(Customer, data.customer_id) is None:
                _missing("Kunde")
            if data.project_id is not None:
                project = session.get(Project, data.project_id) or _missing("Projekt")
                if project.customer_id != data.customer_id:
                    raise InvalidInputError("Das Projekt gehört nicht zu diesem Kunden")
            if data.id is None:
                invoice = Invoice(customer_id=data.customer_id)
            else:
                invoice = session.get(Invoice, data.id) or _missing("Rechnung")
                if invoice.status != InvoiceStatus.DRAFT:
                    raise ImmutableInvoiceError(
                        "Eine ausgestellte Rechnung kann nicht mehr geändert werden"
                    )
            invoice.customer_id = data.customer_id
            invoice.project_id = data.project_id
            invoice.issue_date = data.issue_date
            invoice.service_start = data.service_start
            invoice.service_end = data.service_end
            invoice.note = data.note
            invoice.items = [
                InvoiceItem(
                    position=position,
                    description=item.description,
                    quantity_milli=int(item.quantity * 1000),
                    unit=item.unit,
                    unit_price_cents=int(item.unit_price * 100),
                    tax_rate_percent=item.tax_rate_percent,
                )
                for position, item in enumerate(data.items, start=1)
            ]
            session.add(invoice)
            session.flush()
            return _to_out(session, invoice, self._is_exempt(session))

    def delete_draft(self, invoice_id: int) -> None:
        """Delete a draft. Issued invoices can never be deleted."""
        with self._sessions.begin() as session:
            invoice = session.get(Invoice, invoice_id) or _missing("Rechnung")
            if invoice.status != InvoiceStatus.DRAFT:
                raise ImmutableInvoiceError("Nur Entwürfe können gelöscht werden")
            session.delete(invoice)

    @staticmethod
    def _is_exempt(session: Session) -> bool:
        profile = session.get(Profile, PROFILE_ID)
        return profile is not None and bool(profile.tax_exemption_note.strip())


def _to_out(session: Session, invoice: Invoice, exempt: bool) -> InvoiceOut:
    lines = [
        calc.Line(i.quantity_milli, i.unit_price_cents, i.tax_rate_percent) for i in invoice.items
    ]
    totals = calc.compute_totals(lines, exempt=exempt)
    items = [
        ItemOut(
            position=i.position,
            description=i.description,
            quantity=calc.milli_to_str(i.quantity_milli),
            unit=i.unit,
            unit_price=calc.cents_to_str(i.unit_price_cents),
            tax_rate_percent=0 if exempt else i.tax_rate_percent,
            net=calc.cents_to_str(calc.line_net_cents(line)),
        )
        for i, line in zip(invoice.items, lines, strict=True)
    ]
    cancelled = (
        session.get(Invoice, invoice.cancels_invoice_id) if invoice.cancels_invoice_id else None
    )
    return InvoiceOut(
        id=invoice.id,
        status=str(invoice.status),
        number=invoice.number,
        customer_id=invoice.customer_id,
        project_id=invoice.project_id,
        issue_date=invoice.issue_date,
        service_start=invoice.service_start,
        service_end=invoice.service_end,
        note=invoice.note,
        items=items,
        totals=TotalsOut(
            net=calc.cents_to_str(totals.net_cents),
            tax_lines=[
                TaxLine(
                    tax_rate_percent=g.tax_rate_percent,
                    net=calc.cents_to_str(g.net_cents),
                    tax=calc.cents_to_str(g.tax_cents),
                )
                for g in totals.groups
            ],
            tax=calc.cents_to_str(totals.tax_cents),
            gross=calc.cents_to_str(totals.gross_cents),
        ),
        cancels_number=cancelled.number if cancelled else None,
    )


def _missing(what: str) -> NoReturn:
    raise NotFoundError(f"{what} nicht gefunden")
