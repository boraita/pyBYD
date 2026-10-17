"""Scheduled-climate booking list model.

``/control/getBookingList`` returns the vehicle's scheduled HVAC timers
(the ``BOOKINGAIR`` bookings), e.g.::

    {"allowSetting": 0, "configData": 0,
     "listInfo": [{"bookingTime": 1780938216, "mainSettingTemp": 23,
                   "mainSettingTempNew": 23.0, "timeSpan": 1, "acSwitch": 0,
                   "cycleMode": 2, "windLevel": 0, "windMode": 0,
                   "airConditionTempRange": 7, "bookingId": 1216038691305533440}]}

Note: this endpoint has been observed to return an empty ``{}`` intermittently
even when a booking is set, so callers should treat an empty list as
"unknown / try again" rather than "no bookings".
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from pybyd.models._base import BydBaseModel, BydTimestamp


class ClimateBooking(BydBaseModel):
    """A single scheduled-climate timer (one ``listInfo`` entry)."""

    booking_id: int | None = None
    """Server-assigned booking id (64-bit); required to modify/remove it."""
    booking_time: BydTimestamp = None
    """When the climate timer fires (parsed from epoch seconds)."""
    main_setting_temp: int | None = None
    """Driver setpoint on BYD's raw scale."""
    main_setting_temp_new: float | None = None
    """Driver setpoint in °C."""
    time_span: int | None = None
    """Run-duration code: 1=10min, 2=15min, 3=20min, 4=25min, 5=30min."""
    ac_switch: int | None = None
    """A/C on (1) / off (0) for the scheduled run."""
    cycle_mode: int | None = None
    """Air recirculation: 1=fresh, 2=recirculate."""
    wind_level: int | None = None
    wind_mode: int | None = None
    air_condition_temp_range: int | None = None


class BookingList(BydBaseModel):
    """Scheduled-climate bookings for a vehicle (``getBookingList`` response)."""

    _KEY_ALIASES: ClassVar[dict[str, str]] = {
        "listInfo": "bookings",
    }

    vin: str = ""
    allow_setting: int | None = None
    config_data: int | None = None
    bookings: list[ClimateBooking] = Field(default_factory=list)
