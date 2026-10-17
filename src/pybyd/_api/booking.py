"""Booking-list endpoint.

Endpoints:
  - /control/getBookingList  (read scheduled-climate timers)
"""

from __future__ import annotations

from pybyd._api._common import ENDPOINT_NOT_SUPPORTED_CODES, build_inner_base, post_token_json
from pybyd._transport import Transport
from pybyd.config import BydConfig
from pybyd.models.booking import BookingList
from pybyd.session import Session

_ENDPOINT = "/control/getBookingList"


async def fetch_booking_list(
    config: BydConfig,
    session: Session,
    transport: Transport,
    vin: str,
) -> BookingList:
    """Fetch the vehicle's scheduled-climate (``BOOKINGAIR``) timers.

    The endpoint occasionally returns an empty object even when a booking
    exists; an empty :class:`BookingList.bookings` therefore means
    "none reported", not a guaranteed "no bookings set".
    """
    inner = build_inner_base(config, vin=vin)
    decoded = await post_token_json(
        endpoint=_ENDPOINT,
        config=config,
        session=session,
        transport=transport,
        inner=inner,
        vin=vin,
        not_supported_codes=ENDPOINT_NOT_SUPPORTED_CODES,
    )
    raw = decoded if isinstance(decoded, dict) else {}
    return BookingList.model_validate({"vin": vin, **raw})
