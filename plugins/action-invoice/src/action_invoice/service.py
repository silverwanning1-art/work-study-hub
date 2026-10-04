"""Business logic of the invoice plugin. Every public method is one transaction."""

import threading
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import NoReturn

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from action_invoice import calc
from action_invoice.errors import (
    ImmutableInvoiceError,
    IncompleteInvoiceError,
    InvalidInputError,
    InvalidStateError,
    NotFoundError,
)
from action_invoice.models import (
    Customer,
    Invoice,
    InvoiceItem,
    InvoiceStatus,
    NumberCounter,
    Profile,
    Project,
)
from action_invoice.pdf import InvoiceExporter
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
from action_invoice.snapshot import InvoiceSnapshot, Party, Seller, SnapshotItem

PROFILE_ID = 1


class InvoiceService:
    """Master data, drafts and the invoice lifecycle."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        exporter: InvoiceExporter,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._sessions = session_factory
        self._exporter = exporter
        self._today = today
        # Serializes issuing so numbers stay gapless even with parallel requests.
        self._issue_lock = threading.Lock()

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

    def issue_invoice(self, invoice_id: int) -> InvoiceOut:
        """Issue a draft: check mandatory data, assign the next number, freeze and render it."""
        with self._issue_lock, self._sessions.begin() as session:
            invoice = session.get(Invoice, invoice_id) or _missing("Rechnung")
            if invoice.status != InvoiceStatus.DRAFT:
                raise InvalidStateError("Die Rechnung ist bereits ausgestellt")
            # Column defaults only apply on insert, so an unsaved profile needs explicit blanks.
            profile = session.get(Profile, PROFILE_ID) or Profile(
                id=PROFILE_ID, **ProfileData().model_dump()
            )
            customer = session.get(Customer, invoice.customer_id) or _missing("Kunde")
            project = session.get(Project, invoice.project_id) if invoice.project_id else None
            issue_date = invoice.issue_date or self._today()
            problems = _missing_mandatory_data(profile, customer, invoice)
            if problems:
                raise IncompleteInvoiceError(problems)
            exempt_note = profile.tax_exemption_note.strip()
            snapshot = InvoiceSnapshot(
                number=self._next_number(session, issue_date.year),
                issue_date=issue_date,
                service_start=invoice.service_start or issue_date,
                service_end=invoice.service_end or invoice.service_start or issue_date,
                seller=Seller.model_validate(profile, from_attributes=True),
                buyer=Party.model_validate(customer, from_attributes=True),
                project_name=project.name if project else "",
                items=[
                    SnapshotItem(
                        position=i.position,
                        description=i.description,
                        quantity_milli=i.quantity_milli,
                        unit=i.unit,
                        unit_price_cents=i.unit_price_cents,
                        tax_rate_percent=0 if exempt_note else i.tax_rate_percent,
                    )
                    for i in invoice.items
                ],
                exemption_note=exempt_note,
                note=invoice.note,
                payment_terms_days=profile.payment_terms_days,
            )
            self._freeze(invoice, snapshot)
            session.flush()
            return _to_out(session, invoice, exempt=False)

    def mark_paid(self, invoice_id: int, paid_on: date | None = None) -> InvoiceOut:
        """Mark an issued invoice as paid."""
        with self._sessions.begin() as session:
            invoice = session.get(Invoice, invoice_id) or _missing("Rechnung")
            if invoice.status != InvoiceStatus.ISSUED or invoice.cancels_invoice_id:
                raise InvalidStateError(
                    "Nur eine offene, ausgestellte Rechnung kann bezahlt werden"
                )
            invoice.status = InvoiceStatus.PAID
            invoice.paid_on = paid_on or self._today()
            session.flush()
            return _to_out(session, invoice, exempt=False)

    def cancel_invoice(self, invoice_id: int) -> InvoiceOut:
        """Cancel an issued invoice by issuing a credit note; returns the credit note."""
        with self._issue_lock, self._sessions.begin() as session:
            original = session.get(Invoice, invoice_id) or _missing("Rechnung")
            if (
                original.status not in (InvoiceStatus.ISSUED, InvoiceStatus.PAID)
                or original.cancels_invoice_id
                or original.snapshot_json is None
            ):
                raise InvalidStateError("Nur ausgestellte Rechnungen können storniert werden")
            issue_date = self._today()
            source = InvoiceSnapshot.model_validate_json(original.snapshot_json)
            snapshot = source.model_copy(
                update={
                    "number": self._next_number(session, issue_date.year),
                    "issue_date": issue_date,
                    "cancels_number": source.number,
                    "note": f"Storno zu Rechnung {source.number} vom {source.issue_date:%d.%m.%Y}",
                    "items": [
                        i.model_copy(update={"quantity_milli": -i.quantity_milli})
                        for i in source.items
                    ],
                }
            )
            credit_note = Invoice(
                customer_id=original.customer_id,
                project_id=original.project_id,
                service_start=original.service_start,
                service_end=original.service_end,
                cancels_invoice_id=original.id,
                items=[
                    InvoiceItem(
                        position=i.position,
                        description=i.description,
                        quantity_milli=i.quantity_milli,
                        unit=i.unit,
                        unit_price_cents=i.unit_price_cents,
                        tax_rate_percent=i.tax_rate_percent,
                    )
                    for i in snapshot.items
                ],
            )
            session.add(credit_note)
            self._freeze(credit_note, snapshot)
            original.status = InvoiceStatus.CANCELLED
            session.flush()
            return _to_out(session, credit_note, exempt=False)

    def get_pdf(self, invoice_id: int) -> tuple[str, bytes]:
        """Return file name and the PDF that was rendered when the invoice was issued."""
        with self._sessions() as session:
            invoice = session.get(Invoice, invoice_id) or _missing("Rechnung")
            if invoice.pdf is None or invoice.number is None:
                raise InvalidStateError("Für einen Entwurf gibt es noch kein PDF")
            prefix = "Stornorechnung" if invoice.cancels_invoice_id else "Rechnung"
            return f"{prefix}-{invoice.number}.pdf", invoice.pdf

    def _freeze(self, invoice: Invoice, snapshot: InvoiceSnapshot) -> None:
        invoice.number = snapshot.number
        invoice.issue_date = snapshot.issue_date
        invoice.snapshot_json = snapshot.model_dump_json()
        invoice.pdf = self._exporter.export(snapshot)
        invoice.issued_at = datetime.now(UTC).replace(tzinfo=None)
        invoice.status = InvoiceStatus.ISSUED

    @staticmethod
    def _next_number(session: Session, year: int) -> str:
        counter = session.get(NumberCounter, year)
        if counter is None:
            counter = NumberCounter(year=year, last_number=0)
            session.add(counter)
        counter.last_number += 1
        return f"{year}-{counter.last_number:04d}"

    @staticmethod
    def _is_exempt(session: Session) -> bool:
        profile = session.get(Profile, PROFILE_ID)
        return profile is not None and bool(profile.tax_exemption_note.strip())


def _missing_mandatory_data(profile: Profile, customer: Customer, invoice: Invoice) -> list[str]:
    """List what is missing for an invoice that satisfies §14 UStG (German user messages)."""
    problems: list[str] = []
    for label, value in (
        ("Name des Leistenden", profile.name),
        ("Straße des Leistenden", profile.street),
        ("PLZ des Leistenden", profile.postal_code),
        ("Ort des Leistenden", profile.city),
        ("Name des Empfängers", customer.name),
        ("Straße des Empfängers", customer.street),
        ("PLZ des Empfängers", customer.postal_code),
        ("Ort des Empfängers", customer.city),
    ):
        if not value.strip():
            problems.append(f"{label} fehlt")
    if not (profile.tax_number.strip() or profile.vat_id.strip()):
        problems.append("Steuernummer oder USt-IdNr. des Leistenden fehlt")
    if invoice.service_start is None:
        problems.append("Leistungszeitpunkt bzw. Leistungszeitraum fehlt")
    if not invoice.items:
        problems.append("Mindestens eine Position fehlt")
    elif (
        calc.compute_totals(
            calc.Line(i.quantity_milli, i.unit_price_cents, i.tax_rate_percent)
            for i in invoice.items
        ).net_cents
        <= 0
    ):
        problems.append("Der Rechnungsbetrag muss größer als 0 sein")
    return problems


def _to_out(session: Session, invoice: Invoice, exempt: bool) -> InvoiceOut:
    if invoice.snapshot_json is not None:
        return _snapshot_to_out(session, invoice)
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


def _snapshot_to_out(session: Session, invoice: Invoice) -> InvoiceOut:
    """Issued invoices are always shown from their frozen snapshot."""
    snap = InvoiceSnapshot.model_validate_json(invoice.snapshot_json or "")
    totals = snap.totals
    return InvoiceOut(
        id=invoice.id,
        status=str(invoice.status),
        number=snap.number,
        customer_id=invoice.customer_id,
        project_id=invoice.project_id,
        issue_date=snap.issue_date,
        service_start=snap.service_start,
        service_end=snap.service_end,
        note=snap.note,
        items=[
            ItemOut(
                position=i.position,
                description=i.description,
                quantity=calc.milli_to_str(i.quantity_milli),
                unit=i.unit,
                unit_price=calc.cents_to_str(i.unit_price_cents),
                tax_rate_percent=i.tax_rate_percent,
                net=calc.cents_to_str(i.net_cents),
            )
            for i in snap.items
        ],
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
        cancels_number=snap.cancels_number,
        tax_exemption_note=snap.exemption_note,
    )


def _missing(what: str) -> NoReturn:
    raise NotFoundError(f"{what} nicht gefunden")
