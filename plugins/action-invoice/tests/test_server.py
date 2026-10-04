import asyncio

from action_invoice.server import build_server
from action_invoice.service import InvoiceService
from mcp import Client


def test_master_data_tools_work_over_mcp(service: InvoiceService) -> None:
    async def run() -> dict[str, object] | None:
        async with Client(build_server(service)) as client:
            await client.call_tool("save_customer", {"customer": {"name": "Beispiel GmbH"}})
            result = await client.call_tool("list_customers", {})
        return result.structured_content

    content = asyncio.run(run())

    assert content is not None
    assert [c["name"] for c in content["customers"]] == ["Beispiel GmbH"]  # type: ignore[index]


def test_domain_errors_reach_the_client_with_their_message(service: InvoiceService) -> None:
    async def run() -> tuple[bool, str]:
        async with Client(build_server(service)) as client:
            customer = await client.call_tool("save_customer", {"customer": {"name": "Nur Name"}})
            draft = await client.call_tool(
                "save_invoice_draft",
                {"draft": {"customer_id": customer.structured_content["id"]}},  # type: ignore[index]
            )
            result = await client.call_tool(
                "issue_invoice",
                {"invoice_id": draft.structured_content["id"]},  # type: ignore[index]
            )
        return result.is_error, result.content[0].text  # type: ignore[union-attr]

    is_error, text = asyncio.run(run())

    assert is_error
    assert "Rechnung unvollständig" in text
    assert "Straße des Empfängers fehlt" in text


def test_missing_invoice_gives_readable_message(service: InvoiceService) -> None:
    async def run() -> str:
        async with Client(build_server(service)) as client:
            result = await client.call_tool("get_invoice", {"invoice_id": 999})
        return result.content[0].text  # type: ignore[union-attr]

    assert "Rechnung nicht gefunden" in asyncio.run(run())
