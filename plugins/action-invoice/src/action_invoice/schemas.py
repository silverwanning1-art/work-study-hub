"""Pydantic models for tool inputs and outputs."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Line = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Long = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]

TaxRate = Literal[0, 7, 19]


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileData(_Input):
    """The issuer's master data; every field may be empty until issuing."""

    name: Line = ""
    street: Line = ""
    postal_code: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] = ""
    city: Line = ""
    country: Line = "Deutschland"
    tax_number: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] = ""
    vat_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] = ""
    email: Line = ""
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] = ""
    bank_name: Line = ""
    iban: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] = ""
    bic: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] = ""
    tax_exemption_note: Long = ""
    payment_terms_days: Annotated[int, Field(ge=0, le=365)] = 14


class CustomerIn(_Input):
    """Create (``id`` empty) or update a customer."""

    id: int | None = None
    name: Name
    street: Line = ""
    postal_code: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] = ""
    city: Line = ""
    country: Line = "Deutschland"
    vat_id: Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)] = ""
    email: Line = ""


class CustomerOut(CustomerIn):
    """A stored customer."""

    id: int


class CustomerList(BaseModel):
    """All customers."""

    customers: list[CustomerOut]


class ProjectIn(_Input):
    """Create (``id`` empty) or update a project."""

    id: int | None = None
    customer_id: int
    name: Name
    notes: Long = ""


class ProjectOut(ProjectIn):
    """A stored project."""

    id: int


class ProjectList(BaseModel):
    """Projects, optionally of one customer."""

    projects: list[ProjectOut]


class ItemIn(_Input):
    """One invoice line as entered by the user."""

    description: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
    ]
    quantity: Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=3)]
    unit: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)] = (
        "Std."
    )
    unit_price: Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
    tax_rate_percent: TaxRate = 19


class InvoiceDraftIn(_Input):
    """Create (``id`` empty) or replace a draft. Completeness is checked on issuing."""

    id: int | None = None
    customer_id: int
    project_id: int | None = None
    issue_date: date | None = None
    service_start: date | None = None
    service_end: date | None = None
    note: Long = ""
    items: Annotated[list[ItemIn], Field(max_length=100)] = []


class ItemOut(BaseModel):
    """An invoice line with its computed net amount. Amounts are decimal strings."""

    position: int
    description: str
    quantity: str
    unit: str
    unit_price: str
    tax_rate_percent: int
    net: str


class TaxLine(BaseModel):
    """Net and tax for one tax rate."""

    tax_rate_percent: int
    net: str
    tax: str


class TotalsOut(BaseModel):
    """Invoice totals. Amounts are decimal strings."""

    net: str
    tax_lines: list[TaxLine]
    tax: str
    gross: str


class InvoiceOut(BaseModel):
    """An invoice as shown in the UI."""

    id: int
    status: str
    number: str | None
    customer_id: int
    project_id: int | None
    issue_date: date | None
    service_start: date | None
    service_end: date | None
    note: str
    items: list[ItemOut]
    totals: TotalsOut
    cancels_number: str | None = None
    tax_exemption_note: str = ""


class InvoiceList(BaseModel):
    """Invoices with their totals."""

    invoices: list[InvoiceOut]


class PdfFile(BaseModel):
    """A PDF transferred through MCP as base64."""

    filename: str
    content_base64: str
