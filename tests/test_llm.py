import logging
from typing import Any

import httpx
import pytest
from anthropic import APIStatusError
from pydantic import SecretStr

from hub.llm import AnthropicLlm, LlmError

pytestmark = pytest.mark.anyio


class FailingMessages:
    async def create(self, **_kwargs: Any) -> Any:
        response = httpx.Response(400, request=httpx.Request("POST", "https://api.example"))
        raise APIStatusError("Your credit balance is too low", response=response, body=None)


class FailingClient:
    messages = FailingMessages()


async def test_api_error_is_logged_with_status_and_message_but_not_the_key(
    caplog: pytest.LogCaptureFixture,
) -> None:
    llm = AnthropicLlm(SecretStr("sk-ant-secret-value"))
    llm._client = FailingClient()  # type: ignore[assignment]  # noqa: SLF001
    with caplog.at_level(logging.ERROR), pytest.raises(LlmError):
        await llm.complete(model="m", system="s", messages=[], tools=[], max_tokens=1)
    assert "400" in caplog.text
    assert "credit balance is too low" in caplog.text
    assert "sk-ant-secret-value" not in caplog.text
