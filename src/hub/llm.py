"""Thin, replaceable wrapper around the Anthropic Messages API.

The agent runtime only sees plain dicts, so tests can use a scripted fake.
"""

import logging
from typing import Any, Protocol

from anthropic import APIError, APIStatusError, AsyncAnthropic
from pydantic import BaseModel, SecretStr

logger = logging.getLogger(__name__)


class LlmError(Exception):
    """The language model could not answer."""


class LlmResponse(BaseModel):
    """One model turn: ``content`` holds ``text`` and ``tool_use`` blocks as dicts."""

    stop_reason: str | None
    content: list[dict[str, Any]]


class Llm(Protocol):
    """What the agent runtime needs from a language model."""

    async def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> LlmResponse:
        """Run one model turn."""
        ...


class AnthropicLlm:
    """``Llm`` backed by the Anthropic API."""

    def __init__(self, api_key: SecretStr) -> None:
        self._client = AsyncAnthropic(api_key=api_key.get_secret_value())

    async def complete(
        self,
        *,
        model: str,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        max_tokens: int,
    ) -> LlmResponse:
        """Run one model turn against the Anthropic API."""
        try:
            response = await self._client.messages.create(
                model=model,
                system=system,
                messages=messages,  # type: ignore[arg-type]
                tools=tools,  # type: ignore[arg-type]
                max_tokens=max_tokens,
            )
        except APIError as exc:
            # Log only status and the API's own message (e.g. "credit balance is too low"); the
            # exception text and request are not logged, and the key is never part of them.
            if isinstance(exc, APIStatusError):
                logger.error("Anthropic API error %s: %s", exc.status_code, exc.message)
            else:
                logger.error("Anthropic API error: %s", type(exc).__name__)
            raise LlmError(type(exc).__name__) from exc
        blocks: list[dict[str, Any]] = []
        for block in response.content:
            if block.type == "text":
                blocks.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                blocks.append(
                    {"type": "tool_use", "id": block.id, "name": block.name, "input": block.input}
                )
        return LlmResponse(stop_reason=response.stop_reason, content=blocks)
