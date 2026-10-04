from datetime import date

import pytest
from action_invoice.errors import InvalidStateError
from action_invoice.service import InvoiceService

from tests.conftest import TODAY
from tests.helpers import PROFILE, ready_draft


def test_mark_paid(service: InvoiceService) -> None:
    invoice = service.issue_invoice(ready_draft(service))

    paid = service.mark_paid(invoice.id, date(2026, 11, 20))

    assert paid.status == "paid"
    assert paid.number == invoice.number


def test_draft_cannot_be_marked_paid(service: InvoiceService) -> None:
    with pytest.raises(InvalidStateError):
        service.mark_paid(ready_draft(service))


def test_cancel_creates_credit_note_with_own_number(service: InvoiceService) -> None:
    original = service.issue_invoice(ready_draft(service))

    credit_note = service.cancel_invoice(original.id)

    assert credit_note.number == "2026-0002"
    assert credit_note.cancels_number == original.number
    assert credit_note.status == "issued"
    assert (credit_note.totals.net, credit_note.totals.tax, credit_note.totals.gross) == (
        "-200.00",
        "-38.00",
        "-238.00",
    )
    assert service.get_invoice(original.id).status == "cancelled"
    filename, _ = service.get_pdf(credit_note.id)
    assert filename == "Stornorechnung-2026-0002.pdf"


def test_cancel_works_for_paid_invoice(service: InvoiceService) -> None:
    original = service.issue_invoice(ready_draft(service))
    service.mark_paid(original.id)

    assert service.cancel_invoice(original.id).cancels_number == original.number
    assert service.get_invoice(original.id).status == "cancelled"


def test_credit_note_uses_frozen_data_of_original(service: InvoiceService) -> None:
    original = service.issue_invoice(ready_draft(service))
    service.save_profile(PROFILE.model_copy(update={"tax_exemption_note": "Befreit"}))

    credit_note = service.cancel_invoice(original.id)

    assert credit_note.totals.tax == "-38.00"
    assert credit_note.tax_exemption_note == ""


def test_invoice_cannot_be_cancelled_twice_and_credit_note_not_at_all(
    service: InvoiceService,
) -> None:
    original = service.issue_invoice(ready_draft(service))
    credit_note = service.cancel_invoice(original.id)

    with pytest.raises(InvalidStateError):
        service.cancel_invoice(original.id)
    with pytest.raises(InvalidStateError):
        service.cancel_invoice(credit_note.id)
    with pytest.raises(InvalidStateError):
        service.mark_paid(credit_note.id)


def test_draft_cannot_be_cancelled(service: InvoiceService) -> None:
    with pytest.raises(InvalidStateError):
        service.cancel_invoice(ready_draft(service))


def test_credit_note_is_dated_today(service: InvoiceService) -> None:
    original = service.issue_invoice(ready_draft(service, issue_date=date(2026, 10, 1)))

    assert service.cancel_invoice(original.id).issue_date == TODAY


def test_pdf_not_available_for_draft(service: InvoiceService) -> None:
    with pytest.raises(InvalidStateError):
        service.get_pdf(ready_draft(service))


def test_invoices_can_be_listed_by_status(service: InvoiceService) -> None:
    draft = ready_draft(service)
    issued = service.issue_invoice(ready_draft(service))

    assert [i.id for i in service.list_invoices("draft").invoices] == [draft]
    assert [i.id for i in service.list_invoices("issued").invoices] == [issued.id]
