"""Invoice export. Only PDF exists today; formats like XRechnung implement ``InvoiceExporter``."""

from datetime import timedelta
from pathlib import Path
from typing import Protocol

from jinja2 import Environment, FileSystemLoader

from action_invoice import calc
from action_invoice.snapshot import InvoiceSnapshot

# src/action_invoice/pdf.py -> plugin folder (also /app in the container)
DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"


class InvoiceExporter(Protocol):
    """Turns a frozen invoice into a file. Add a class here for XRechnung/ZUGFeRD later."""

    def export(self, snapshot: InvoiceSnapshot) -> bytes:
        """Return the file content for ``snapshot``."""
        ...


def _eur(cents: int) -> str:
    text = calc.cents_to_str(cents)
    sign = "-" if text.startswith("-") else ""
    whole, fraction = text.lstrip("-").split(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    return f"{sign}{grouped},{fraction} €"


def _qty(milli: int) -> str:
    return calc.milli_to_str(milli).replace(".", ",")


def _de_date(value: object) -> str:
    return value.strftime("%d.%m.%Y") if hasattr(value, "strftime") else str(value)


class PdfExporter:
    """Renders ``templates/invoice.html`` with WeasyPrint."""

    def __init__(self, template_dir: Path = DEFAULT_TEMPLATE_DIR) -> None:
        # Autoescape on: user text such as descriptions must never be interpreted as HTML.
        self._env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)
        self._env.filters["eur"] = _eur
        self._env.filters["qty"] = _qty
        self._env.filters["de_date"] = _de_date

    def render_html(self, snapshot: InvoiceSnapshot) -> str:
        """Return the HTML that is turned into the PDF."""
        return self._env.get_template("invoice.html").render(
            inv=snapshot,
            title="Stornorechnung" if snapshot.cancels_number else "Rechnung",
            totals=snapshot.totals,
            due_date=snapshot.issue_date + timedelta(days=snapshot.payment_terms_days),
        )

    def export(self, snapshot: InvoiceSnapshot) -> bytes:
        """Render the PDF. WeasyPrint is imported lazily because it needs native Pango."""
        from weasyprint import HTML
        from weasyprint.urls import URLFetcher

        # The template references no external resources; refuse all fetching.
        fetcher = URLFetcher(allowed_protocols=("data",))
        document = HTML(string=self.render_html(snapshot), url_fetcher=fetcher)
        return bytes(document.write_pdf())
