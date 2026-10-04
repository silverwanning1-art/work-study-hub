import pytest

from hub.confirmations import ConfirmationError, ConfirmationStore, TooManyPendingError


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_consume_returns_stored_call() -> None:
    store = ConfirmationStore()
    pending = store.create("action-x", "issue", {"id": 1})

    call = store.consume(pending.id)

    assert (call.plugin_id, call.tool, call.arguments) == ("action-x", "issue", {"id": 1})


def test_confirmation_works_only_once() -> None:
    store = ConfirmationStore()
    pending = store.create("action-x", "issue", {})
    store.consume(pending.id)

    with pytest.raises(ConfirmationError):
        store.consume(pending.id)


def test_unknown_id_is_rejected() -> None:
    with pytest.raises(ConfirmationError):
        ConfirmationStore().consume("nope")


def test_expired_confirmation_is_rejected() -> None:
    clock = FakeClock()
    store = ConfirmationStore(ttl_seconds=60, clock=clock)
    pending = store.create("action-x", "issue", {})

    clock.now = 61

    with pytest.raises(ConfirmationError):
        store.consume(pending.id)


def test_ids_are_unique_and_unguessable() -> None:
    store = ConfirmationStore()

    ids = {store.create("p", "t", {}).id for _ in range(50)}

    assert len(ids) == 50
    assert all(len(i) >= 32 for i in ids)


def test_pending_limit_is_enforced_and_expired_calls_free_slots() -> None:
    clock = FakeClock()
    store = ConfirmationStore(ttl_seconds=60, max_pending=2, clock=clock)
    store.create("p", "t", {})
    store.create("p", "t", {})

    with pytest.raises(TooManyPendingError):
        store.create("p", "t", {})

    clock.now = 61
    store.create("p", "t", {})
