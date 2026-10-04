"""Server-side confirmations for tool calls that change something (``writes: true``)."""

import secrets
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class ConfirmationError(Exception):
    """The confirmation is unknown, expired or was already used."""


class TooManyPendingError(Exception):
    """Too many unconfirmed calls are waiting; refuse new ones."""


@dataclass(frozen=True)
class PendingCall:
    """A tool call that waits for the user's explicit confirmation."""

    id: str
    plugin_id: str
    tool: str
    arguments: dict[str, Any]
    expires_at: float


class ConfirmationStore:
    """In-memory, single-use confirmations with a short lifetime.

    Arguments are kept on the server, so the confirm request cannot change what runs.
    """

    def __init__(
        self,
        ttl_seconds: float = 300.0,
        max_pending: int = 100,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_pending = max_pending
        self._clock = clock
        self._pending: dict[str, PendingCall] = {}

    def create(self, plugin_id: str, tool: str, arguments: dict[str, Any]) -> PendingCall:
        """Store a call and return it with a fresh unguessable id."""
        self._purge_expired()
        if len(self._pending) >= self._max_pending:
            raise TooManyPendingError
        call = PendingCall(
            id=secrets.token_urlsafe(32),
            plugin_id=plugin_id,
            tool=tool,
            arguments=arguments,
            expires_at=self._clock() + self._ttl,
        )
        self._pending[call.id] = call
        return call

    def consume(self, confirmation_id: str) -> PendingCall:
        """Return the call and invalidate the id; it works exactly once."""
        self._purge_expired()
        call = self._pending.pop(confirmation_id, None)
        if call is None:
            raise ConfirmationError
        return call

    def _purge_expired(self) -> None:
        now = self._clock()
        self._pending = {k: v for k, v in self._pending.items() if v.expires_at > now}
