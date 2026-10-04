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
