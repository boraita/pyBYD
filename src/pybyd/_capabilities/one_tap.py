"""One-tap pre-conditioning and shutdown capability.

These capabilities are a best-effort wrapper around the
``ONETAPPREP`` and ``ONECLICKSHUTDOWN`` ``commandType`` values that
appear in the BYD Latest Config under ``functionNo`` ``1030`` and
``1031`` respectively.

> **WARNING: command payload is unverified.**
>
> Unlike ``LOCKDOOR`` / ``OPENAIR`` etc., we do not yet have a captured
> request body from the BYD app for these commands.  This module
> currently sends them as fire-and-forget (no ``controlParams``), based
> on the assumption that the cloud derives the sub-system selection
> (A/C + seats + steering wheel heat) from per-VIN profile settings
> rather than from request params.
>
> If the cloud returns a ``code=1001`` / ``code=1009`` error when
> invoking either of these, the most likely fix is to add a typed
> ``OneTapParams`` model with the appropriate per-feature flags.  The
> Latest Config sub-codes that hint at the schema:
>   - ``10300001`` (A/C)
>   - ``10300003`` (Seats)
>   - ``10300004`` (Steering wheel heat)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pybyd.exceptions import BydEndpointNotSupportedError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class OneTapCapability:
    """One-tap pre-conditioning (``ONETAPPREP``) and shutdown
    (``ONECLICKSHUTDOWN``) commands.

    Implemented as fire-and-forget mirrors of :class:`FinderCapability`
    until the exact payload schema is reverse-engineered.
    """

    def __init__(
        self,
        *,
        prep_fn: Callable[..., Awaitable[Any]],
        shutdown_fn: Callable[..., Awaitable[Any]],
        vin: str,
        execute_command: Callable[..., Awaitable[None]],
        prep_available: bool | None = True,
        shutdown_available: bool | None = True,
    ) -> None:
        self._prep_fn = prep_fn
        self._shutdown_fn = shutdown_fn
        self._vin = vin
        self._execute = execute_command
        self._prep_available = prep_available
        self._shutdown_available = shutdown_available

    @property
    def prep_available(self) -> bool:
        return bool(self._prep_available)

    @property
    def shutdown_available(self) -> bool:
        return bool(self._shutdown_available)

    async def prep(self) -> None:
        """Start the configured pre-conditioning profile.

        Sends ``commandType=ONETAPPREP`` with no ``controlParams``.  The
        car-side profile (which seats, target temperature, steering wheel
        heat) is assumed to be configured per-VIN via the BYD app.
        """
        if not self.prep_available:
            raise BydEndpointNotSupportedError(
                f"One-tap prep capability not supported for VIN {self._vin}",
                code="capability_unsupported",
                endpoint="one_tap.prep",
            )

        async def _cmd() -> Any:
            return await self._prep_fn(self._vin)

        await self._execute(_cmd, [])

    async def shutdown(self) -> None:
        """Shut down any active pre-conditioning (``ONECLICKSHUTDOWN``)."""
        if not self.shutdown_available:
            raise BydEndpointNotSupportedError(
                f"One-tap shutdown capability not supported for VIN {self._vin}",
                code="capability_unsupported",
                endpoint="one_tap.shutdown",
            )

        async def _cmd() -> Any:
            return await self._shutdown_fn(self._vin)

        await self._execute(_cmd, [])
