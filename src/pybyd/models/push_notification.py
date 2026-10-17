"""Push notification state model.

The EU endpoint ``/vehicle/vehicleswitch/getPushSwitchState`` returns a LIST of
per-notification-type switches, e.g. ``[{"state":1,"type":1}, ...]`` — not a
single boolean. ``type 701`` is the vehicle real-time status push (mirrors the
``vehicleStatusPushLearnInfo`` capability flag); when ON the cloud is expected
to relay car-originated status onto the MQTT result topic without a poll.
"""

from __future__ import annotations

from pybyd.models._base import BydBaseModel

# Notification "type" code for the vehicle real-time status push.
VEHICLE_STATUS_PUSH_TYPE = 701


class PushSwitch(BydBaseModel):
    """A single per-type push notification switch."""

    type: int | None = None
    state: int | None = None


class PushNotificationState(BydBaseModel):
    """Per-type push notification switch states for a vehicle."""

    vin: str = ""
    switches: list[PushSwitch] = []

    def state_for(self, push_type: int) -> int | None:
        """Return the on/off state (1/0) for a notification ``type``, or None."""
        for sw in self.switches:
            if sw.type == push_type:
                return sw.state
        return None

    @property
    def status_push_enabled(self) -> bool:
        """Whether the vehicle real-time status push (type 701) is enabled."""
        return self.state_for(VEHICLE_STATUS_PUSH_TYPE) == 1

    @property
    def is_enabled(self) -> bool:
        """Legacy alias — True when the vehicle status push (701) is on."""
        return self.status_push_enabled
