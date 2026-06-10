"""Tests for surfacing real remote-control outcomes.

Two halves of the behaviour:

1. ``_poll_remote_control_once`` raises ``BydRemoteControlError`` instead of
   returning a fabricated tentative-success result when the command can never
   be confirmed (no request serial, or the poll loop times out).
2. ``BydCar._execute_command`` rolls back the optimistic projection and
   re-raises on ``BydRemoteControlError`` rather than swallowing it.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import pybyd._api.control as control
from pybyd._api.control import _poll_remote_control_once
from pybyd.car import BydCar
from pybyd.exceptions import BydRemoteControlError
from pybyd.models.control import RemoteCommand


def _make_fetch_stub(responses: list[tuple[dict[str, Any], str | None]]):
    """Return an async stub for ``_fetch_control_endpoint``.

    Yields the queued ``(result, serial)`` tuples in order; repeats the last
    one once exhausted so poll loops of any length stay fed.
    """
    calls = {"i": 0}

    async def _stub(endpoint: str, *args: Any, **kwargs: Any) -> tuple[dict[str, Any], str | None]:
        idx = min(calls["i"], len(responses) - 1)
        calls["i"] += 1
        return responses[idx]

    return _stub


@pytest.mark.asyncio
async def test_no_serial_raises_instead_of_tentative_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trigger returns a non-terminal result with no serial -> raise."""
    monkeypatch.setattr(
        control,
        "_fetch_control_endpoint",
        _make_fetch_stub([({}, None)]),
    )

    with pytest.raises(BydRemoteControlError) as exc_info:
        await _poll_remote_control_once(None, None, None, "VIN", RemoteCommand.FLASH_LIGHTS, mqtt_result_waiter=None)

    assert exc_info.value.code == "no_serial"


@pytest.mark.asyncio
async def test_timeout_raises_when_poll_never_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    """Serial present but the poll loop never reaches a terminal state -> timeout."""
    # Trigger: has serial, not terminal. Polls: res=1 (in progress) forever.
    monkeypatch.setattr(
        control,
        "_fetch_control_endpoint",
        _make_fetch_stub([({"requestSerial": "S1"}, "S1"), ({"res": 1}, "S1")]),
    )

    with pytest.raises(BydRemoteControlError) as exc_info:
        await _poll_remote_control_once(
            None,
            None,
            None,
            "VIN",
            RemoteCommand.FLASH_LIGHTS,
            poll_attempts=2,
            poll_interval=0,
            mqtt_result_waiter=None,
        )

    assert exc_info.value.code == "timeout"


class _FakeEngine:
    """Minimal state-engine stand-in tracking projection lifecycle calls."""

    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.registered = 0
        self.rolled_back: list[str] = []

    def register_projections(self, specs: Any) -> str:
        self.registered += 1
        return "cmd-1"

    def rollback_projections(self, command_id: str) -> None:
        self.rolled_back.append(command_id)


class _StubCar:
    """Just enough of BydCar to drive _execute_command."""

    def __init__(self) -> None:
        self._engine = _FakeEngine()
        self._vin = "VIN"


@pytest.mark.asyncio
async def test_execute_command_rolls_back_and_reraises_on_control_error() -> None:
    """A BydRemoteControlError rolls back the projection and propagates."""
    car = _StubCar()

    async def _failing() -> None:
        raise BydRemoteControlError("rejected", code="2", endpoint="/control/remoteControl")

    with pytest.raises(BydRemoteControlError):
        await BydCar._execute_command(car, _failing, ["projection"])

    assert car._engine.rolled_back == ["cmd-1"]


@pytest.mark.asyncio
async def test_execute_command_keeps_projection_on_success() -> None:
    """A successful command must NOT roll back the optimistic projection."""
    car = _StubCar()

    async def _ok() -> None:
        return None

    await BydCar._execute_command(car, _ok, ["projection"])

    assert car._engine.registered == 1
    assert car._engine.rolled_back == []
