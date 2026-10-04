"""MCP server exposing the invoice service as tools (Streamable HTTP)."""

import logging
import sys

from mcp.server.mcpserver import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse

from action_invoice.config import Settings
from action_invoice.db import init_db, make_engine
from action_invoice.schemas import (
    CustomerIn,
    CustomerList,
    CustomerOut,
    InvoiceDraftIn,
    InvoiceList,
    InvoiceOut,
    ProfileData,
    ProjectIn,
    ProjectList,
    ProjectOut,
)
from action_invoice.service import InvoiceService


def build_server(service: InvoiceService) -> MCPServer:
    """Create the MCP server with all tools bound to ``service``."""
    server = MCPServer("action-invoice")

    @server.tool()
    def get_profile() -> ProfileData:
        """Return the issuer's master data."""
        return service.get_profile()

    @server.tool()
    def save_profile(profile: ProfileData) -> ProfileData:
        """Replace the issuer's master data (name, address, tax number, bank, ...)."""
        return service.save_profile(profile)

    @server.tool()
    def list_customers() -> CustomerList:
        """List all customers."""
        return service.list_customers()

    @server.tool()
    def save_customer(customer: CustomerIn) -> CustomerOut:
        """Create a customer, or update it when ``id`` is set."""
        return service.save_customer(customer)

    @server.tool()
    def list_projects(customer_id: int | None = None) -> ProjectList:
        """List projects, optionally of one customer."""
        return service.list_projects(customer_id)

    @server.tool()
    def save_project(project: ProjectIn) -> ProjectOut:
        """Create a project, or update it when ``id`` is set."""
        return service.save_project(project)

    @server.tool()
    def list_invoices(status: str | None = None) -> InvoiceList:
        """List invoices (newest first), optionally only one status."""
        return service.list_invoices(status)

    @server.tool()
    def get_invoice(invoice_id: int) -> InvoiceOut:
        """Return one invoice with items and totals."""
        return service.get_invoice(invoice_id)

    @server.tool()
    def save_invoice_draft(draft: InvoiceDraftIn) -> InvoiceOut:
        """Create a draft, or replace the draft with the given id. Drafts are freely editable."""
        return service.save_draft(draft)

    @server.tool()
    def delete_invoice_draft(invoice_id: int) -> dict[str, bool]:
        """Delete a draft. Issued invoices cannot be deleted."""
        service.delete_draft(invoice_id)
        return {"deleted": True}

    @server.custom_route("/health", methods=["GET"])  # type: ignore[untyped-decorator]
    async def health(_request: Request) -> JSONResponse:
        """Liveness check for the container runtime."""
        return JSONResponse({"status": "ok"})

    return server


def main() -> None:
    """Start the server with settings from the environment."""
    settings = Settings()
    logging.basicConfig(stream=sys.stdout, level=settings.log_level)
    session_factory = init_db(make_engine(f"sqlite:///{settings.invoice_db_path}"))
    server = build_server(InvoiceService(session_factory))
    server.run("streamable-http", host="0.0.0.0", port=8000)  # noqa: S104 - container-internal


if __name__ == "__main__":
    main()
