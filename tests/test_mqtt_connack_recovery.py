"""Tests for MQTT CONNACK-refusal recovery.

When the broker refuses our CONNECT (e.g. the shared account's MQTT session
was taken over), paho retries the same stale credentials forever. After
``_MQTT_CONNACK_REFUSAL_THRESHOLD`` consecutive refusals the client forces a
re-login, with exponential backoff + jitter and a max-attempts ceiling. Only a
successful CONNACK resets the counters.

These exercise the decision logic on a bare client (no I/O) with stubs for
``_stop_mqtt`` / ``_mqtt_recover_via_login``.
"""

from __future__ import annotations

import asyncio

import pytest

from pybyd.client import BydClient


def _bare_client() -> BydClient:
    client = BydClient.__new__(BydClient)  # no __init__: avoid network/config
    client._mqtt_recovery_attempts = 0
    client._mqtt_recovery_last_at = 0.0
    client._on_mqtt_connect_cb = None
    client._stop_mqtt = lambda: None  # type: ignore[method-assign]
    return client


def test_below_threshold_does_nothing() -> None:
    """Fewer than THRESHOLD consecutive refusals must not trigger recovery."""
    client = _bare_client()
    for n in range(1, BydClient._MQTT_CONNACK_REFUSAL_THRESHOLD):
        client._on_mqtt_connack_refused(n)
    assert client._mqtt_recovery_attempts == 0
    assert client._mqtt_recovery_last_at == 0.0


def test_on_connected_resets_counters_and_forwards_callback() -> None:
    """A successful CONNACK resets recovery state and forwards the cloud cb."""
    client = _bare_client()
    client._mqtt_recovery_attempts = 4
    client._mqtt_recovery_last_at = 123.0
    calls: list[bool] = []
    client._on_mqtt_connect_cb = lambda: calls.append(True)

    client._on_mqtt_connected()

    assert client._mqtt_recovery_attempts == 0
    assert client._mqtt_recovery_last_at == 0.0
    assert calls == [True]


@pytest.mark.asyncio
async def test_threshold_schedules_one_relogin() -> None:
    """Hitting the threshold schedules exactly one re-login and counts it."""
    client = _bare_client()
    scheduled: list[bool] = []

    async def _recover() -> None:
        scheduled.append(True)

    client._mqtt_recover_via_login = _recover  # type: ignore[method-assign]

    client._on_mqtt_connack_refused(BydClient._MQTT_CONNACK_REFUSAL_THRESHOLD)

    assert client._mqtt_recovery_attempts == 1
    assert client._mqtt_recovery_last_at > 0.0
    await asyncio.sleep(0)  # let the scheduled task run
    assert scheduled == [True]


@pytest.mark.asyncio
async def test_backoff_window_blocks_immediate_retry() -> None:
    """A second refusal inside the backoff window must not re-trigger."""
    client = _bare_client()

    async def _recover() -> None:
        return None

    client._mqtt_recover_via_login = _recover  # type: ignore[method-assign]

    client._on_mqtt_connack_refused(BydClient._MQTT_CONNACK_REFUSAL_THRESHOLD)
    assert client._mqtt_recovery_attempts == 1

    client._on_mqtt_connack_refused(BydClient._MQTT_CONNACK_REFUSAL_THRESHOLD + 1)
    assert client._mqtt_recovery_attempts == 1  # still inside backoff
    await asyncio.sleep(0)


def test_ceiling_stops_channel() -> None:
    """At the attempt ceiling, stop the push channel instead of relogging."""
    client = _bare_client()
    client._mqtt_recovery_attempts = BydClient._MQTT_RECOVERY_MAX_ATTEMPTS
    stopped: list[bool] = []
    client._stop_mqtt = lambda: stopped.append(True)  # type: ignore[method-assign]

    client._on_mqtt_connack_refused(99)

    assert stopped == [True]
    assert client._mqtt_recovery_attempts == BydClient._MQTT_RECOVERY_MAX_ATTEMPTS
