"""Synthetic test data only. Never put real names, addresses or tax numbers here."""

from datetime import date
from decimal import Decimal

from action_invoice.schemas import CustomerIn, InvoiceDraftIn, ItemIn, ProfileData
from action_invoice.service import InvoiceService

PROFILE = ProfileData(
    name="Erika Beispiel",
    street="Teststraße 1",
    postal_code="12345",
    city="Teststadt",
    tax_number="00/000/00000",
    email="erika@example.invalid",
    bank_name="Testbank",
    iban="DE00000000000000000000",
    bic="TESTDEXX",
)

CUSTOMER = CustomerIn(
    name="Beispiel GmbH", street="Musterweg 2", postal_code="54321", city="Musterstadt"
)


def make_item(price: str = "80.00", quantity: str = "2.5", rate: int = 19) -> ItemIn:
    return ItemIn(
        description="Workshop",
        quantity=Decimal(quantity),
        unit_price=Decimal(price),
        tax_rate_percent=rate,  # type: ignore[arg-type]
    )


def ready_draft(service: InvoiceService, **overrides: object) -> int:
    """Create a complete profile, customer and draft; return the draft id."""
    service.save_profile(PROFILE)
    customer = service.save_customer(CUSTOMER)
    data = InvoiceDraftIn(
        customer_id=customer.id,
        service_start=date(2026, 11, 10),
        service_end=date(2026, 11, 11),
        items=[make_item()],
    ).model_copy(update=overrides)
    return service.save_draft(data).id
