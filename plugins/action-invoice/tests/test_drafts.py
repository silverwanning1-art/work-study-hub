from datetime import date
from decimal import Decimal

import pytest
from action_invoice.errors import InvalidInputError, NotFoundError
from action_invoice.schemas import CustomerIn, InvoiceDraftIn, ItemIn, ProfileData, ProjectIn
from action_invoice.service import InvoiceService


def item(price: str = "80.00", quantity: str = "2.5", rate: int = 19) -> ItemIn:
    return ItemIn(
        description="Workshop",
        quantity=Decimal(quantity),
        unit_price=Decimal(price),
        tax_rate_percent=rate,  # type: ignore[arg-type]
    )


@pytest.fixture
def customer_id(service: InvoiceService) -> int:
    return service.save_customer(CustomerIn(name="Beispiel GmbH")).id


def test_draft_gets_totals(service: InvoiceService, customer_id: int) -> None:
    draft = service.save_draft(InvoiceDraftIn(customer_id=customer_id, items=[item()]))

    assert draft.status == "draft"
    assert draft.number is None
    assert draft.items[0].net == "200.00"
    assert (draft.totals.net, draft.totals.tax, draft.totals.gross) == ("200.00", "38.00", "238.00")


def test_draft_can_be_replaced(service: InvoiceService, customer_id: int) -> None:
    first = service.save_draft(InvoiceDraftIn(customer_id=customer_id, items=[item(), item()]))

    second = service.save_draft(
        InvoiceDraftIn(
            id=first.id, customer_id=customer_id, items=[item(price="10.00", quantity="1")]
        )
    )

    assert [i.net for i in second.items] == ["10.00"]
    assert len(service.list_invoices().invoices) == 1


def test_exemption_note_sets_tax_to_zero(service: InvoiceService, customer_id: int) -> None:
    service.save_profile(ProfileData(tax_exemption_note="Hinweis auf Steuerbefreiung"))

    draft = service.save_draft(InvoiceDraftIn(customer_id=customer_id, items=[item()]))

    assert (draft.totals.tax, draft.totals.gross) == ("0.00", "200.00")
    assert draft.items[0].tax_rate_percent == 0


def test_unknown_customer_is_rejected(service: InvoiceService) -> None:
    with pytest.raises(NotFoundError):
        service.save_draft(InvoiceDraftIn(customer_id=42))


def test_project_must_belong_to_customer(service: InvoiceService, customer_id: int) -> None:
    other = service.save_customer(CustomerIn(name="Andere AG"))
    project = service.save_project(ProjectIn(customer_id=other.id, name="Konzept"))

    with pytest.raises(InvalidInputError):
        service.save_draft(InvoiceDraftIn(customer_id=customer_id, project_id=project.id))


def test_service_period_must_not_end_before_start(
    service: InvoiceService, customer_id: int
) -> None:
    with pytest.raises(InvalidInputError):
        service.save_draft(
            InvoiceDraftIn(
                customer_id=customer_id,
                service_start=date(2026, 11, 10),
                service_end=date(2026, 11, 9),
            )
        )


def test_draft_can_be_deleted(service: InvoiceService, customer_id: int) -> None:
    draft = service.save_draft(InvoiceDraftIn(customer_id=customer_id))

    service.delete_draft(draft.id)

    assert service.list_invoices().invoices == []


@pytest.mark.parametrize("quantity", ["0", "-1", "1.0001"])
def test_invalid_quantities_are_rejected_by_schema(quantity: str) -> None:
    with pytest.raises(ValueError, match="quantity"):
        ItemIn(description="x", quantity=Decimal(quantity), unit_price=Decimal("1"))
