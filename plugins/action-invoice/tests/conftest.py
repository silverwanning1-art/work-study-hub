from datetime import date

import pytest
from action_invoice.db import init_db, make_engine
from action_invoice.service import InvoiceService

TODAY = date(2026, 11, 3)


@pytest.fixture
def service() -> InvoiceService:
    return InvoiceService(init_db(make_engine("sqlite://")), today=lambda: TODAY)
