"""Tests for the EU push-switch endpoint + per-type list parsing.

The EU host serves push switches under ``/vehicle/vehicleswitch/`` (the
``/app/push/`` paths 404) and returns a LIST of ``{type, state}`` entries
rather than a single boolean. ``fetch_push_state`` parses that into
``PushNotificationState.switches`` with ``state_for`` / ``status_push_enabled``
helpers (type 701 = vehicle real-time status push).
"""

from __future__ import annotations

from typing import Any

import pytest

import pybyd._api.push_notifications as push
from pybyd._api.push_notifications import _GET_ENDPOINT, fetch_push_state
from pybyd.models.push_notification import (
    VEHICLE_STATUS_PUSH_TYPE,
    PushNotificationState,
    PushSwitch,
)


def test_endpoint_is_vehicleswitch_namespace() -> None:
    """The EU path lives under /vehicle/vehicleswitch/, not /app/push/."""
    assert _GET_ENDPOINT == "/vehicle/vehicleswitch/getPushSwitchState"


def test_state_for_and_status_push_enabled() -> None:
    """Helpers resolve a per-type switch and the 701 status-push flag."""
    state = PushNotificationState(
        vin="V",
        switches=[PushSwitch(type=1, state=0), PushSwitch(type=701, state=1)],
    )
    assert state.state_for(701) == 1
    assert state.state_for(1) == 0
    assert state.state_for(999) is None
    assert state.status_push_enabled is True
    assert VEHICLE_STATUS_PUSH_TYPE == 701


def test_status_push_disabled_when_701_off() -> None:
    state = PushNotificationState(vin="V", switches=[PushSwitch(type=701, state=0)])
    assert state.status_push_enabled is False


@pytest.mark.asyncio
async def test_fetch_parses_eu_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """A list response is parsed into per-type switches."""
    monkeypatch.setattr(push, "build_inner_base", lambda *a, **k: {})

    async def _fake_post(**kwargs: Any) -> Any:
        return [{"type": 701, "state": 1}, {"type": 1, "state": 0}]

    monkeypatch.setattr(push, "post_token_json", _fake_post)

    result = await fetch_push_state(None, None, None, "VIN")
    assert result.vin == "VIN"
    assert result.status_push_enabled is True
    assert result.state_for(1) == 0


@pytest.mark.asyncio
async def test_fetch_handles_non_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-list response degrades to an empty switch set (no crash)."""
    monkeypatch.setattr(push, "build_inner_base", lambda *a, **k: {})

    async def _fake_post(**kwargs: Any) -> Any:
        return {"unexpected": "shape"}

    monkeypatch.setattr(push, "post_token_json", _fake_post)

    result = await fetch_push_state(None, None, None, "VIN")
    assert result.switches == []
    assert result.status_push_enabled is False
