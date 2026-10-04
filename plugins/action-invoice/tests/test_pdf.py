from datetime import date
from importlib.util import find_spec

import pytest
from action_invoice.pdf import PdfExporter
from action_invoice.snapshot import InvoiceSnapshot, Party, Seller, SnapshotItem


def snapshot(**overrides: object) -> InvoiceSnapshot:
    data: dict[str, object] = {
        "number": "2026-0001",
        "issue_date": date(2026, 11, 3),
        "service_start": date(2026, 11, 10),
        "service_end": date(2026, 11, 11),
        "seller": Seller(
            name="Erika Beispiel",
            street="Teststraße 1",
            postal_code="12345",
            city="Teststadt",
            country="Deutschland",
            tax_number="00/000/00000",
            iban="DE00000000000000000000",
        ),
        "buyer": Party(
            name="Beispiel GmbH",
            street="Musterweg 2",
            postal_code="54321",
            city="Musterstadt",
            country="Deutschland",
        ),
        "items": [
            SnapshotItem(
                position=1,
                description="Workshop",
                quantity_milli=2500,
                unit="Std.",
                unit_price_cents=8000,
                tax_rate_percent=19,
            )
        ],
    }
    return InvoiceSnapshot.model_validate(data | overrides)


def pango_available() -> bool:
    if find_spec("weasyprint") is None:
        return False
    try:
        import weasyprint  # noqa: F401
    except OSError:
        return False
    return True


def test_html_contains_mandatory_information() -> None:
    html = PdfExporter().render_html(snapshot())

    for expected in (
        "Rechnung",
        "2026-0001",
        "03.11.2026",
        "10.11.2026 – 11.11.2026",
        "Erika Beispiel",
        "Teststraße 1",
        "00/000/00000",
        "Beispiel GmbH",
        "Workshop",
        "2,5",
        "80,00 €",
        "200,00 €",
        "zzgl. 19 % USt auf 200,00 €",
        "38,00 €",
        "238,00 €",
        "17.11.2026",
    ):
        assert expected in html


def test_html_escapes_user_text() -> None:
    items = [
        SnapshotItem(
            position=1,
            description="<script>alert(1)</script>",
            quantity_milli=1000,
            unit="Stk.",
            unit_price_cents=100,
            tax_rate_percent=19,
        )
    ]

    html = PdfExporter().render_html(snapshot(items=items))

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_exemption_note_is_printed_without_tax_line() -> None:
    items = [
        SnapshotItem(
            position=1,
            description="Workshop",
            quantity_milli=1000,
            unit="Stk.",
            unit_price_cents=10000,
            tax_rate_percent=0,
        )
    ]

    html = PdfExporter().render_html(snapshot(items=items, exemption_note="Hinweistext zur Steuer"))

    assert "Hinweistext zur Steuer" in html
    assert "zzgl." not in html


def test_credit_note_is_titled_and_references_original() -> None:
    html = PdfExporter().render_html(snapshot(cancels_number="2026-0001", number="2026-0002"))

    assert "Stornorechnung" in html
    assert "Rechnung 2026-0001" in html
    assert "Bitte überweisen" not in html


@pytest.mark.skipif(
    not pango_available(), reason="WeasyPrint needs native Pango (brew install pango)"
)
def test_pdf_is_rendered() -> None:
    pdf = PdfExporter().export(snapshot())

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
