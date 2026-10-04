"""The frozen content of an issued invoice. PDFs are rendered from this, never from live data."""

from datetime import date

from pydantic import BaseModel

from action_invoice import calc


class Party(BaseModel):
    """Name and address of issuer or recipient."""

    name: str
    street: str
    postal_code: str
    city: str
    country: str
    vat_id: str = ""


class Seller(Party):
    """The issuer, including tax and bank details."""

    tax_number: str = ""
    email: str = ""
    phone: str = ""
    bank_name: str = ""
    iban: str = ""
    bic: str = ""


class SnapshotItem(BaseModel):
    """One line; ``tax_rate_percent`` is the effective rate (0 when exempt)."""

    position: int
    description: str
    quantity_milli: int
    unit: str
    unit_price_cents: int
    tax_rate_percent: int

    @property
    def net_cents(self) -> int:
        """Net amount of this line."""
        return calc.line_net_cents(self.to_line())

    def to_line(self) -> calc.Line:
        """Convert to the calculation input."""
        return calc.Line(self.quantity_milli, self.unit_price_cents, self.tax_rate_percent)


class InvoiceSnapshot(BaseModel):
    """Everything printed on an issued invoice or credit note."""

    number: str
    issue_date: date
    service_start: date
    service_end: date
    seller: Seller
    buyer: Party
    project_name: str = ""
    items: list[SnapshotItem]
    exemption_note: str = ""
    note: str = ""
    payment_terms_days: int = 14
    cancels_number: str | None = None

    @property
    def totals(self) -> calc.Totals:
        """Totals computed from the frozen items."""
        return calc.compute_totals(i.to_line() for i in self.items)
