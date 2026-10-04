import pytest
from action_invoice.errors import (
    ImmutableInvoiceError,
    IncompleteInvoiceError,
    InvalidStateError,
)
from action_invoice.models import Invoice, InvoiceItem
from action_invoice.schemas import CustomerIn, InvoiceDraftIn, ProfileData
from action_invoice.service import InvoiceService

from tests.helpers import CUSTOMER, PROFILE, make_item, ready_draft


def test_issue_assigns_number_status_and_pdf(service: InvoiceService) -> None:
    invoice = service.issue_invoice(ready_draft(service))

    assert invoice.status == "issued"
    assert invoice.number == "2026-0001"
    assert str(invoice.issue_date) == "2026-11-03"
    assert invoice.totals.gross == "238.00"
    filename, pdf = service.get_pdf(invoice.id)
    assert filename == "Rechnung-2026-0001.pdf"
    assert pdf.startswith(b"%PDF")


def test_numbers_are_consecutive_and_unique(service: InvoiceService) -> None:
    numbers = [service.issue_invoice(ready_draft(service)).number for _ in range(5)]

    assert numbers == [f"2026-{n:04d}" for n in range(1, 6)]


def test_failed_issue_does_not_consume_a_number(service: InvoiceService) -> None:
    broken_id = ready_draft(service, items=[])
    with pytest.raises(IncompleteInvoiceError):
        service.issue_invoice(broken_id)

    assert service.issue_invoice(ready_draft(service)).number == "2026-0001"


def test_failing_pdf_rendering_does_not_consume_a_number(service: InvoiceService) -> None:
    draft_id = ready_draft(service)

    class Boom:
        def export(self, snapshot: object) -> bytes:
            raise RuntimeError("render failed")

    good_exporter = service._exporter  # noqa: SLF001
    service._exporter = Boom()  # noqa: SLF001
    with pytest.raises(RuntimeError):
        service.issue_invoice(draft_id)
    service._exporter = good_exporter  # noqa: SLF001

    assert service.issue_invoice(draft_id).number == "2026-0001"


def test_numbering_restarts_per_year(service: InvoiceService) -> None:
    from datetime import date

    first = service.issue_invoice(ready_draft(service))
    other_year = service.issue_invoice(ready_draft(service, issue_date=date(2027, 1, 5)))

    assert (first.number, other_year.number) == ("2026-0001", "2027-0001")


def test_issued_invoice_cannot_be_edited_or_deleted(service: InvoiceService) -> None:
    invoice = service.issue_invoice(ready_draft(service))

    with pytest.raises(ImmutableInvoiceError):
        service.save_draft(InvoiceDraftIn(id=invoice.id, customer_id=invoice.customer_id))
    with pytest.raises(ImmutableInvoiceError):
        service.delete_draft(invoice.id)
    with pytest.raises(InvalidStateError):
        service.issue_invoice(invoice.id)


def test_orm_guard_blocks_direct_changes_to_issued_invoice(service: InvoiceService) -> None:
    invoice = service.issue_invoice(ready_draft(service))

    with service._sessions() as session:  # noqa: SLF001
        row = session.get(Invoice, invoice.id)
        assert row is not None
        row.note = "tampered"
        with pytest.raises(ImmutableInvoiceError):
            session.flush()

    with service._sessions() as session:  # noqa: SLF001
        row = session.get(Invoice, invoice.id)
        assert row is not None
        row.items[0].unit_price_cents = 1
        with pytest.raises(ImmutableInvoiceError):
            session.flush()

    with service._sessions() as session:  # noqa: SLF001
        row = session.get(Invoice, invoice.id)
        assert row is not None
        row.items.append(
            InvoiceItem(
                position=2, description="x", quantity_milli=1000, unit="Stk.", unit_price_cents=1
            )
        )
        with pytest.raises(ImmutableInvoiceError):
            session.flush()

    with service._sessions() as session:  # noqa: SLF001
        row = session.get(Invoice, invoice.id)
        assert row is not None
        session.delete(row)
        with pytest.raises(ImmutableInvoiceError):
            session.flush()

    assert service.get_invoice(invoice.id).note == ""


def test_later_master_data_changes_do_not_alter_issued_invoice(service: InvoiceService) -> None:
    invoice = service.issue_invoice(ready_draft(service))

    service.save_profile(PROFILE.model_copy(update={"name": "Anderer Name"}))
    service.save_customer(CUSTOMER.model_copy(update={"id": invoice.customer_id, "name": "Neu AG"}))
    service.save_profile(PROFILE.model_copy(update={"tax_exemption_note": "Befreit"}))

    again = service.get_invoice(invoice.id)
    assert again.totals.tax == "38.00"
    assert again.tax_exemption_note == ""
    snapshot = service._sessions().get(Invoice, invoice.id)  # noqa: SLF001
    assert snapshot is not None
    assert "Erika Beispiel" in (snapshot.snapshot_json or "")
    assert "Beispiel GmbH" in (snapshot.snapshot_json or "")


@pytest.mark.parametrize(
    ("profile_update", "expected"),
    [
        ({"name": ""}, "Name des Leistenden"),
        ({"street": ""}, "Straße des Leistenden"),
        ({"postal_code": ""}, "PLZ des Leistenden"),
        ({"city": ""}, "Ort des Leistenden"),
        ({"tax_number": ""}, "Steuernummer oder USt-IdNr."),
    ],
)
def test_missing_issuer_data_blocks_issuing(
    service: InvoiceService, profile_update: dict[str, str], expected: str
) -> None:
    draft_id = ready_draft(service)
    service.save_profile(PROFILE.model_copy(update=profile_update))

    with pytest.raises(IncompleteInvoiceError, match=expected):
        service.issue_invoice(draft_id)


def test_vat_id_alone_satisfies_tax_identification(service: InvoiceService) -> None:
    draft_id = ready_draft(service)
    service.save_profile(PROFILE.model_copy(update={"tax_number": "", "vat_id": "DE000000000"}))

    assert service.issue_invoice(draft_id).status == "issued"


@pytest.mark.parametrize(
    ("customer_update", "expected"),
    [
        ({"street": ""}, "Straße des Empfängers"),
        ({"postal_code": ""}, "PLZ des Empfängers"),
        ({"city": ""}, "Ort des Empfängers"),
    ],
)
def test_missing_recipient_data_blocks_issuing(
    service: InvoiceService, customer_update: dict[str, str], expected: str
) -> None:
    draft_id = ready_draft(service)
    customer = service.list_customers().customers[0]
    service.save_customer(CustomerIn(**{**customer.model_dump(), **customer_update}))

    with pytest.raises(IncompleteInvoiceError, match=expected):
        service.issue_invoice(draft_id)


def test_missing_service_date_items_and_amount_block_issuing(service: InvoiceService) -> None:
    no_date = ready_draft(service, service_start=None, service_end=None)
    no_items = ready_draft(service, items=[])
    zero = ready_draft(service, items=[make_item(price="0.00")])

    with pytest.raises(IncompleteInvoiceError, match="Leistungszeitpunkt"):
        service.issue_invoice(no_date)
    with pytest.raises(IncompleteInvoiceError, match="Position"):
        service.issue_invoice(no_items)
    with pytest.raises(IncompleteInvoiceError, match="größer als 0"):
        service.issue_invoice(zero)


def test_all_problems_are_reported_at_once(service: InvoiceService) -> None:
    customer = service.save_customer(CustomerIn(name="Nur Name"))
    draft = service.save_draft(InvoiceDraftIn(customer_id=customer.id))

    with pytest.raises(IncompleteInvoiceError) as caught:
        service.issue_invoice(draft.id)

    assert len(caught.value.problems) >= 8


def test_exemption_note_is_frozen_and_taxes_are_zero(service: InvoiceService) -> None:
    draft_id = ready_draft(service)
    service.save_profile(
        PROFILE.model_copy(update={"tax_exemption_note": "Hinweistext zur Steuer"})
    )

    invoice = service.issue_invoice(draft_id)

    assert invoice.totals.tax == "0.00"
    assert invoice.totals.gross == "200.00"
    assert invoice.tax_exemption_note == "Hinweistext zur Steuer"


def test_blank_profile_cannot_issue(service: InvoiceService) -> None:
    customer = service.save_customer(CUSTOMER)
    draft = service.save_draft(InvoiceDraftIn(customer_id=customer.id, items=[make_item()]))
    service.save_profile(ProfileData())

    with pytest.raises(IncompleteInvoiceError):
        service.issue_invoice(draft.id)
