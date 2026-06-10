"""Tests for remote-control readiness int coercion."""

from __future__ import annotations

from pybyd._api.control import _coerce_int, _is_remote_control_ready


def test_coerce_int_handles_garbage() -> None:
    """Non-numeric cloud values coerce to None instead of raising."""
    assert _coerce_int(3) == 3
    assert _coerce_int("2") == 2
    assert _coerce_int("") is None
    assert _coerce_int("pending") is None
    assert _coerce_int(None) is None


def test_is_remote_control_ready_tolerates_non_numeric_fields() -> None:
    """Garbage controlState/res must not abort the poll loop."""
    assert _is_remote_control_ready({"controlState": ""}) is False
    assert _is_remote_control_ready({"res": "oops"}) is False
    assert _is_remote_control_ready({"controlState": "1"}) is True
    assert _is_remote_control_ready({"res": 2}) is True
    assert _is_remote_control_ready({"res": 1}) is False
    assert _is_remote_control_ready({"res": "garbage", "result": "x"}) is True
