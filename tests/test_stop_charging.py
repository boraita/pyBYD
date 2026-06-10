"""Tests for the stop_charging command gate.

``stop_charging`` mirrors ``start_charging``: both gate on the
``RESERVATIONCHARGING`` capability (``functionNo "1012"``) and toggle
``/control/smartCharge/changeChargeStatue`` (``status: "0"`` to stop).
"""

from __future__ import annotations

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


def test_stop_charge_supported_with_1012() -> None:
    """Gate is supported when the car exposes functionNo 1012."""
    verdict = evaluate_command_gate(RemoteCommand.STOP_CHARGE, _caps_with(["1012"]))
    assert verdict.supported is True


def test_stop_charge_blocked_without_1012() -> None:
    """Gate is blocked when the car lacks functionNo 1012."""
    verdict = evaluate_command_gate(RemoteCommand.STOP_CHARGE, _caps_with(["1005"]))
    assert verdict.supported is False


def test_stop_charge_gate_mirrors_start_charge() -> None:
    """Start and stop gate on the same capability — symmetric availability."""
    caps = _caps_with(["1012"])
    start = evaluate_command_gate(RemoteCommand.START_CHARGE, caps)
    stop = evaluate_command_gate(RemoteCommand.STOP_CHARGE, caps)
    assert start.supported == stop.supported is True

    caps_no = _caps_with([])
    start_no = evaluate_command_gate(RemoteCommand.START_CHARGE, caps_no)
    stop_no = evaluate_command_gate(RemoteCommand.STOP_CHARGE, caps_no)
    assert start_no.supported == stop_no.supported is False
