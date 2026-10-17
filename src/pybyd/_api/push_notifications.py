"""Push notification endpoints.

Endpoints (EU host uses the /vehicle/vehicleswitch/ namespace, same as
getLatestConfig / verifyControlPassword; the /app/push/ paths return 404 on
dilinkappoversea-eu.byd.auto):
  - /vehicle/vehicleswitch/getPushSwitchState  (get current state)
  - /vehicle/vehicleswitch/setPushSwitchState  (toggle on/off)
"""

from __future__ import annotations

from pybyd._api._common import ENDPOINT_NOT_SUPPORTED_CODES, build_inner_base, post_token_json
from pybyd._transport import Transport
from pybyd.config import BydConfig
from pybyd.models.control import CommandAck
from pybyd.models.push_notification import (
    VEHICLE_STATUS_PUSH_TYPE,
    PushNotificationState,
    PushSwitch,
)
from pybyd.session import Session

_GET_ENDPOINT = "/vehicle/vehicleswitch/getPushSwitchState"
_SET_ENDPOINT = "/vehicle/vehicleswitch/setPushSwitchState"


async def fetch_push_state(
    config: BydConfig,
    session: Session,
    transport: Transport,
    vin: str,
) -> PushNotificationState:
    """Fetch the current push notification state for a vehicle.

    Returns
    -------
    PushNotificationState
        Current push notification toggle state.
    """
    inner = build_inner_base(config, vin=vin)
    decoded = await post_token_json(
        endpoint=_GET_ENDPOINT,
        config=config,
        session=session,
        transport=transport,
        inner=inner,
        vin=vin,
        not_supported_codes=ENDPOINT_NOT_SUPPORTED_CODES,
    )
    raw_list = decoded if isinstance(decoded, list) else []
    switches = [
        PushSwitch(type=item.get("type"), state=item.get("state")) for item in raw_list if isinstance(item, dict)
    ]
    return PushNotificationState(vin=vin, switches=switches)


async def set_push_state(
    config: BydConfig,
    session: Session,
    transport: Transport,
    vin: str,
    *,
    enable: bool,
    push_type: int = VEHICLE_STATUS_PUSH_TYPE,
) -> CommandAck:
    """Enable/disable a per-type push notification switch.

    The EU endpoint is keyed by notification ``type`` (the getPushSwitchState
    response is a list of ``{type, state}``). NOTE (Sealion 7 EU): this write
    returns ``code=1001`` ("not supported") for the status-push type — the car
    does not allow enabling vehicle status push remotely. The body below
    ({type, state}) mirrors the read keys but is unverified against a
    successful write.

    Parameters
    ----------
    enable : bool
        True to enable, False to disable.
    push_type : int
        Notification type code to toggle (default: vehicle status push, 701).
    """
    inner = build_inner_base(config, vin=vin)
    inner["type"] = str(push_type)
    inner["state"] = str(1 if enable else 0)
    decoded = await post_token_json(
        endpoint=_SET_ENDPOINT,
        config=config,
        session=session,
        transport=transport,
        inner=inner,
        vin=vin,
        not_supported_codes=ENDPOINT_NOT_SUPPORTED_CODES,
    )
    raw = decoded if isinstance(decoded, dict) else {}
    return CommandAck.model_validate({"vin": vin, **raw, "raw": raw})
