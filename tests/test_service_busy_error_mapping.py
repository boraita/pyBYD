"""Tests for the default 1008/6002 API error-code mappings.

``_raise_for_code`` applies these mappings on *every* endpoint, after any
per-call ``extra_code_map`` overrides:

- ``1008`` (backend busy / soft rate-limit) -> :class:`BydServiceBusyError`
- ``6002`` (vehicle unreachable) -> :class:`BydDataUnavailableError`
"""

from __future__ import annotations

import pytest

from pybyd._api._common import _raise_for_code
from pybyd.exceptions import (
    BydApiError,
    BydDataUnavailableError,
    BydRemoteControlError,
    BydServiceBusyError,
)


@pytest.mark.parametrize(
    "endpoint",
    [
        "/control/remoteControl",
        "/vehicleInfo/vehicle/vehicleRealTimeRequest",
        "/control/smartCharge/homePage",
    ],
)
def test_1008_maps_to_service_busy_on_every_endpoint(endpoint: str) -> None:
    """1008 surfaces as BydServiceBusyError regardless of endpoint."""
    with pytest.raises(BydServiceBusyError) as exc_info:
        _raise_for_code(endpoint=endpoint, code="1008", message="Error de servicio")

    assert exc_info.value.code == "1008"
    assert exc_info.value.endpoint == endpoint


@pytest.mark.parametrize(
    "endpoint",
    [
        "/control/remoteControl",
        "/vehicleInfo/vehicle/vehicleRealTimeRequest",
    ],
)
def test_6002_maps_to_data_unavailable_on_every_endpoint(endpoint: str) -> None:
    """6002 surfaces as BydDataUnavailableError regardless of endpoint."""
    with pytest.raises(BydDataUnavailableError) as exc_info:
        _raise_for_code(endpoint=endpoint, code="6002", message="weak signal")

    assert exc_info.value.code == "6002"


def test_service_busy_is_apierror_subclass() -> None:
    """Non-breaking: existing ``except BydApiError`` callers still catch it."""
    assert issubclass(BydServiceBusyError, BydApiError)
    with pytest.raises(BydApiError):
        _raise_for_code(endpoint="/x", code="1008", message="m")


def test_per_call_override_takes_precedence_over_default() -> None:
    """A per-call ``extra_code_map`` entry wins over the default 1008 mapping."""
    with pytest.raises(BydRemoteControlError) as exc_info:
        _raise_for_code(
            endpoint="/control/remoteControl",
            code="1008",
            message="m",
            extra_code_map={frozenset({"1008"}): BydRemoteControlError},
        )

    assert exc_info.value.code == "1008"


def test_unmapped_code_still_generic_api_error() -> None:
    """Codes outside the default sets keep falling back to BydApiError."""
    with pytest.raises(BydApiError) as exc_info:
        _raise_for_code(endpoint="/x", code="9999", message="unknown")

    # Not one of the specialised subclasses.
    assert type(exc_info.value) is BydApiError
    assert exc_info.value.code == "9999"
