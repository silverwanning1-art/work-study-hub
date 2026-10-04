"""Defense in depth: refuse changes to issued invoices at flush time.

The service already checks the status; this guard also stops any code path that
modifies an issued invoice or its items directly through the ORM.
"""

from typing import Any

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from action_invoice.errors import ImmutableInvoiceError
from action_invoice.models import Invoice, InvoiceItem, InvoiceStatus

# After issuing, only the lifecycle may move on.
MUTABLE_AFTER_ISSUE = {"status", "paid_on"}

_MESSAGE = "Eine ausgestellte Rechnung kann nicht mehr geändert werden"


def _original_status(invoice: Invoice) -> str:
    history = inspect(invoice).attrs.status.history
    return str(history.deleted[0]) if history.deleted else str(invoice.status)


def _item_is_locked(session: Session, item: InvoiceItem) -> bool:
    invoice = item.invoice
    if invoice is None or invoice in session.new:
        return False
    return _original_status(invoice) != InvoiceStatus.DRAFT


@event.listens_for(Session, "before_flush")
def _protect_issued_invoices(session: Session, _context: Any, _instances: Any) -> None:
    for obj in session.dirty:
        if isinstance(obj, Invoice) and _original_status(obj) != InvoiceStatus.DRAFT:
            changed = {a.key for a in inspect(obj).attrs if a.history.has_changes()}
            if changed - MUTABLE_AFTER_ISSUE:
                raise ImmutableInvoiceError(_MESSAGE)
        elif isinstance(obj, InvoiceItem) and session.is_modified(obj):
            if _item_is_locked(session, obj):
                raise ImmutableInvoiceError(_MESSAGE)
    for obj in session.deleted:
        if isinstance(obj, Invoice) and _original_status(obj) != InvoiceStatus.DRAFT:
            raise ImmutableInvoiceError(_MESSAGE)
        if isinstance(obj, InvoiceItem) and _item_is_locked(session, obj):
            raise ImmutableInvoiceError(_MESSAGE)
    for obj in session.new:
        if isinstance(obj, InvoiceItem) and _item_is_locked(session, obj):
            raise ImmutableInvoiceError(_MESSAGE)
