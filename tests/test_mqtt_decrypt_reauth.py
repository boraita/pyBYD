"""Tests for the MQTT decrypt-failure re-auth guard (hass-byd-vehicle#195).

Payloads for another session on the same account land on our topic but are
encrypted with that session's key. Re-logging in can't fix that, so a
decrypt failure only triggers a re-login while the current key is
unconfirmed, and at most ``_MQTT_DECRYPT_REAUTH_MAX`` times until a payload
decrypts again.
"""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pybyd._crypto.aes import aes_encrypt_hex
from pybyd._mqtt import BydMqttRuntime, MqttBootstrap
from pybyd.client import BydClient

OUR_KEY = "00112233445566778899AABBCCDDEEFF"
OTHER_KEY = "FFEEDDCCBBAA99887766554433221100"


def _payload(key_hex: str) -> SimpleNamespace:
    body = json.dumps({"event": "vehicleInfo", "vin": "VIN", "data": {}})
    return SimpleNamespace(topic="t", payload=aes_encrypt_hex(body, key_hex).encode())


class _Loop:
    """Runs call_soon_threadsafe callbacks inline."""

    def call_soon_threadsafe(self, fn: Any, *args: Any) -> None:
        fn(*args)


def _runtime() -> tuple[BydMqttRuntime, list[Any], list[bool], Any]:
    events: list[Any] = []
    decrypt_errors: list[bool] = []
    runtime = BydMqttRuntime(
        loop=_Loop(),  # type: ignore[arg-type]
        decrypt_key_hex=OUR_KEY,
        on_event=events.append,
        on_decrypt_error=lambda: decrypt_errors.append(True),
    )
    bootstrap = MqttBootstrap(
        user_id="u",
        broker_host="h",
        broker_port=8883,
        topic="t",
        client_id="c",
        username="u",
        password="p",
    )
    paho_client = MagicMock()
    with patch("pybyd._mqtt.mqtt.Client", return_value=paho_client):
        runtime.start(bootstrap)
    return runtime, events, decrypt_errors, paho_client.on_message


def test_failure_before_any_decrypt_requests_reauth() -> None:
    _, events, decrypt_errors, on_message = _runtime()
    on_message(None, None, _payload(OTHER_KEY))
    assert decrypt_errors == [True]
    assert events == []


def test_failure_after_decrypt_is_ignored() -> None:
    _, events, decrypt_errors, on_message = _runtime()
    on_message(None, None, _payload(OUR_KEY))
    on_message(None, None, _payload(OTHER_KEY))
    assert len(events) == 1
    assert decrypt_errors == []


def test_new_key_must_be_confirmed_again() -> None:
    runtime, _, decrypt_errors, on_message = _runtime()
    on_message(None, None, _payload(OUR_KEY))
    runtime.update_decrypt_key(OTHER_KEY)
    on_message(None, None, _payload(OUR_KEY))
    assert decrypt_errors == [True]


def _bare_client() -> BydClient:
    client = BydClient.__new__(BydClient)  # no __init__: avoid network/config
    client._mqtt_reauth_at = 0.0
    client._mqtt_decrypt_reauths = 0
    client._mqtt_waiters = []
    client._on_vehicle_info = None
    client._on_mqtt_event_cb = None
    return client


@pytest.mark.asyncio
async def test_reauth_stops_when_failures_survive_a_relogin(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _bare_client()
    logins: list[bool] = []

    async def _login() -> None:
        logins.append(True)

    client.login = _login  # type: ignore[method-assign]
    clock = iter(range(1000, 100000, 120))
    monkeypatch.setattr("pybyd.client.time.monotonic", lambda: float(next(clock)))

    for _ in range(4):
        client._schedule_mqtt_reauth()
        await asyncio.sleep(0)

    assert logins == [True]


@pytest.mark.asyncio
async def test_decrypted_payload_rearms_reauth(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _bare_client()
    client._mqtt_decrypt_reauths = BydClient._MQTT_DECRYPT_REAUTH_MAX + 1
    logins: list[bool] = []

    async def _login() -> None:
        logins.append(True)

    client.login = _login  # type: ignore[method-assign]
    monkeypatch.setattr("pybyd.client.time.monotonic", lambda: 1000.0)

    client._on_mqtt_event(SimpleNamespace(event="unknown", vin=None, topic="t", payload={}))  # type: ignore[arg-type]
    client._schedule_mqtt_reauth()
    await asyncio.sleep(0)

    assert logins == [True]
