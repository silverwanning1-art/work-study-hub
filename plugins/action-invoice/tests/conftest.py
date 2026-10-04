from datetime import date

import pytest
from action_invoice.db import init_db, make_engine
from action_invoice.service import InvoiceService
from action_invoice.snapshot import InvoiceSnapshot

TODAY = date(2026, 11, 3)


class FakeExporter:
    """Stands in for WeasyPrint so service tests need no native libraries."""

    def export(self, snapshot: InvoiceSnapshot) -> bytes:
        return b"%PDF-fake " + snapshot.number.encode()


@pytest.fixture
def service() -> InvoiceService:
    return InvoiceService(init_db(make_engine("sqlite://")), FakeExporter(), today=lambda: TODAY)
