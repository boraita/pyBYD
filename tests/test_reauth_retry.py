"""Tests for session-reauth retry semantics."""

from __future__ import annotations

import pytest

from pybyd.client import BydClient
from pybyd.config import BydConfig
from pybyd.exceptions import BydSessionExpiredError


def _make_client() -> BydClient:
    config = BydConfig(username="user@example.com", password="secret")
    return BydClient(config)


def _patch_reauth(client: BydClient, calls: list[str]) -> None:
    """Stub out the network-touching reauth steps."""

    async def fake_ensure_session():  # type: ignore[no-untyped-def]
        calls.append("ensure_session")
        return None

    client.ensure_session = fake_ensure_session  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_call_with_reauth_retries_once_by_default() -> None:
    """Default behavior: one retry after session expiry."""
    client = _make_client()
    calls: list[str] = []
    _patch_reauth(client, calls)
    attempts = 0

    async def fn() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise BydSessionExpiredError("expired", code="401", endpoint="/x")
        return "ok"

    result = await client._call_with_reauth(fn)  # noqa: SLF001
    assert result == "ok"
    assert attempts == 2
    assert "ensure_session" in calls


@pytest.mark.asyncio
async def test_call_with_reauth_vetoed_after_trigger_dispatch() -> None:
    """retry_if=False must propagate the expiry without re-running fn."""
    client = _make_client()
    calls: list[str] = []
    _patch_reauth(client, calls)
    attempts = 0

    async def fn() -> str:
        nonlocal attempts
        attempts += 1
        raise BydSessionExpiredError("expired", code="401", endpoint="/x")

    with pytest.raises(BydSessionExpiredError):
        await client._call_with_reauth(fn, retry_if=lambda: False)  # noqa: SLF001

    assert attempts == 1
    assert calls == []  # no reauth attempted; nothing to retry into


@pytest.mark.asyncio
async def test_call_with_reauth_retry_if_true_still_retries() -> None:
    """retry_if=True keeps the single-retry behavior."""
    client = _make_client()
    calls: list[str] = []
    _patch_reauth(client, calls)
    attempts = 0

    async def fn() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise BydSessionExpiredError("expired", code="401", endpoint="/x")
        return "ok"

    result = await client._call_with_reauth(fn, retry_if=lambda: True)  # noqa: SLF001
    assert result == "ok"
    assert attempts == 2
