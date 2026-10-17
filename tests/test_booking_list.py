"""Tests for the getBookingList model (scheduled-climate timers).

Payload shape captured live from a Sealion 7 (EU)::

    {"allowSetting": 0, "configData": 0,
     "listInfo": [{"bookingTime": 1780938216, "mainSettingTemp": 23,
                   "mainSettingTempNew": 23.0, "timeSpan": 1, "acSwitch": 0,
                   "cycleMode": 2, "windLevel": 0, "windMode": 0,
                   "airConditionTempRange": 7, "bookingId": 1216038691305533440}]}
"""

from __future__ import annotations

from pybyd.models.booking import BookingList

_CAPTURED = {
    "allowSetting": 0,
    "configData": 0,
    "listInfo": [
        {
            "bookingTime": 1780938216,
            "mainSettingTemp": 23,
            "airConditionTempRange": 7,
            "cycleMode": 2,
            "windLevel": 0,
            "timeSpan": 1,
            "mainSettingTempNew": 23.0,
            "acSwitch": 0,
            "bookingId": 1216038691305533440,
            "windMode": 0,
        }
    ],
}


def test_parses_captured_payload() -> None:
    bl = BookingList.model_validate({"vin": "TESTVIN", **_CAPTURED})
    assert bl.vin == "TESTVIN"
    assert bl.allow_setting == 0
    assert len(bl.bookings) == 1
    b = bl.bookings[0]
    assert b.booking_id == 1216038691305533440  # 64-bit id preserved
    assert b.main_setting_temp == 23
    assert b.main_setting_temp_new == 23.0
    assert b.time_span == 1
    assert b.ac_switch == 0
    assert b.cycle_mode == 2
    assert b.booking_time is not None  # epoch -> datetime


def test_empty_payload_yields_no_bookings() -> None:
    """The endpoint can return {} even when a booking exists; degrade gracefully."""
    bl = BookingList.model_validate({"vin": "TESTVIN"})
    assert bl.bookings == []
    assert bl.allow_setting is None
