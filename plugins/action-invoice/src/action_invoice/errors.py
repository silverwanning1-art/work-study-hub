"""Domain errors. Messages are written for the user and never contain internals."""


class InvoiceError(Exception):
    """Base class for all domain errors."""


class NotFoundError(InvoiceError):
    """The requested record does not exist."""


class InvalidStateError(InvoiceError):
    """The action is not allowed in the invoice's current status."""


class ImmutableInvoiceError(InvoiceError):
    """An issued invoice must not be changed."""


class IncompleteInvoiceError(InvoiceError):
    """Mandatory information for issuing is missing."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("Rechnung unvollständig: " + "; ".join(problems))
        self.problems = problems
