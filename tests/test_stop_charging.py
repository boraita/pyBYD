"""Tests for stop_charging.

The BYD cloud has no working stop-charge command: the
``changeChargeStatue`` ``status: "0"`` path is a verified no-op (returns
``res: 2 "Operation successful"`` while the vehicle keeps charging — see
``references/changeChargeStatue.md``). ``BydClient.stop_charging`` therefore
raises instead of reporting a false success.

The ``STOP_CHARGE`` enum member and gate rule are retained as metadata (the
command type exists in BYD's catalogue) and are still exercised here.
"""

from __future__ import annotations

import pytest

from pybyd.client import BydClient
from pybyd.exceptions import BydEndpointNotSupportedError
from pybyd.models.command_gating import evaluate_command_gate
from pybyd.models.control import RemoteCommand
from pybyd.models.latest_config import VehicleCapabilities


def _caps_with(function_nos: list[str]) -> VehicleCapabilities:
    return VehicleCapabilities.model_validate(
        {
            "vin": "TEST" + "X" * 13,
            "source": "test_fixture",
            "functionNos": function_nos,
        }
    )


def test_stop_charge_enum_value() -> None:
    """Synthetic enum member carries the BYD commandType string."""
    assert RemoteCommand.STOP_CHARGE == "SMARTCHARGESTOP"


def test_stop_charge_gate_present_and_mirrors_start() -> None:
    """The stop_charge gate exists and gates on the same capability as start."""
    caps = _caps_with(["1012"])
    assert evaluate_command_gate(RemoteCommand.STOP_CHARGE, caps).supported is True
    assert evaluate_command_gate(RemoteCommand.START_CHARGE, caps).supported is True

    caps_no = _caps_with([])
    assert evaluate_command_gate(RemoteCommand.STOP_CHARGE, caps_no).supported is False


@pytest.mark.asyncio
async def test_stop_charging_raises_unsupported() -> None:
    """stop_charging refuses rather than issuing the known no-op request.

    It must raise BEFORE any network/session work, so calling it on a bare
    client instance (no session) still raises the unsupported error.
    """
    client = BydClient.__new__(BydClient)  # no __init__: prove no I/O happens
    with pytest.raises(BydEndpointNotSupportedError) as exc_info:
        await client.stop_charging("TEST" + "X" * 13)

    assert exc_info.value.code == "cloud_stop_unsupported"
    assert "no-op" in str(exc_info.value).lower()
