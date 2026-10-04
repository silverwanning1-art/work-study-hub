"""ORM models. Money is stored as integer cents, quantities as thousandths."""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import ForeignKey, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all tables."""


class InvoiceStatus(StrEnum):
    """Lifecycle of an invoice: draft, issued, then paid or cancelled."""

    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    CANCELLED = "cancelled"


class Profile(Base):
    """The issuer's own master data. A single row with id 1."""

    __tablename__ = "profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    street: Mapped[str] = mapped_column(String(200), default="")
    postal_code: Mapped[str] = mapped_column(String(20), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(100), default="Deutschland")
    tax_number: Mapped[str] = mapped_column(String(50), default="")
    vat_id: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    bank_name: Mapped[str] = mapped_column(String(100), default="")
    iban: Mapped[str] = mapped_column(String(50), default="")
    bic: Mapped[str] = mapped_column(String(20), default="")
    tax_exemption_note: Mapped[str] = mapped_column(Text, default="")
    payment_terms_days: Mapped[int] = mapped_column(default=14)


class Customer(Base):
    """An invoice recipient."""

    __tablename__ = "customer"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    street: Mapped[str] = mapped_column(String(200), default="")
    postal_code: Mapped[str] = mapped_column(String(20), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    country: Mapped[str] = mapped_column(String(100), default="Deutschland")
    vat_id: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(200), default="")


class Project(Base):
    """A freelance project belonging to a customer."""

    __tablename__ = "project"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"))
    name: Mapped[str] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, default="")


class Invoice(Base):
    """An invoice or credit note (``cancels_invoice_id`` set)."""

    __tablename__ = "invoice"
    __table_args__ = (UniqueConstraint("number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[str] = mapped_column(String(10), default=InvoiceStatus.DRAFT)
    number: Mapped[str | None] = mapped_column(String(20), default=None)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customer.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("project.id"), default=None)
    issue_date: Mapped[date | None] = mapped_column(default=None)
    service_start: Mapped[date | None] = mapped_column(default=None)
    service_end: Mapped[date | None] = mapped_column(default=None)
    note: Mapped[str] = mapped_column(Text, default="")
    cancels_invoice_id: Mapped[int | None] = mapped_column(ForeignKey("invoice.id"), default=None)
    # Frozen copy of issuer, recipient and items taken when the invoice is issued.
    snapshot_json: Mapped[str | None] = mapped_column(Text, default=None)
    pdf: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    issued_at: Mapped[datetime | None] = mapped_column(default=None)
    paid_on: Mapped[date | None] = mapped_column(default=None)

    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
        order_by="InvoiceItem.position",
    )


class InvoiceItem(Base):
    """One invoice line."""

    __tablename__ = "invoice_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoice.id"))
    position: Mapped[int]
    description: Mapped[str] = mapped_column(Text)
    quantity_milli: Mapped[int]
    unit: Mapped[str] = mapped_column(String(20), default="Std.")
    unit_price_cents: Mapped[int]
    tax_rate_percent: Mapped[int] = mapped_column(default=19)

    invoice: Mapped[Invoice] = relationship(back_populates="items")


class NumberCounter(Base):
    """Last invoice sequence number used per calendar year."""

    __tablename__ = "number_counter"

    year: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    last_number: Mapped[int] = mapped_column(default=0)
