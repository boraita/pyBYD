"""Window control capability."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pybyd.exceptions import BydEndpointNotSupportedError

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


class WindowsCapability:
    """Window open/close commands.

    Both directions are fire-and-forget.  No projections are
    registered because window state updates arrive asynchronously.

    Open is binary (all windows fully open) on the standard
    ``OPENWINDOW`` endpoint.  Partial position / vent-mode is not
    supported here; see ``openWindowSignalLearnInfo`` in latest config
    for a variant flag that might gate a separate command.
    """

    def __init__(
        self,
        *,
        close_fn: Callable[..., Awaitable[Any]],
        vin: str,
        execute_command: Callable[..., Awaitable[None]],
        close_available: bool | None = True,
        open_fn: Callable[..., Awaitable[Any]] | None = None,
        open_available: bool | None = True,
    ) -> None:
        self._close_fn = close_fn
        self._open_fn = open_fn
        self._vin = vin
        self._execute = execute_command
        self._close_available = close_available
        self._open_available = open_available

    @property
    def close_available(self) -> bool:
        return bool(self._close_available)

    @property
    def open_available(self) -> bool:
        return bool(self._open_available and self._open_fn is not None)

    async def close(self) -> None:
        """Close all windows."""
        if not self.close_available:
            raise BydEndpointNotSupportedError(
                f"Close-windows capability not supported for VIN {self._vin}",
                code="capability_unsupported",
                endpoint="windows.close",
            )

        async def _cmd() -> Any:
            return await self._close_fn(self._vin)

        await self._execute(_cmd, [])

    async def open(self) -> None:
        """Open all windows (fully)."""
        if not self.open_available or self._open_fn is None:
            raise BydEndpointNotSupportedError(
                f"Open-windows capability not supported for VIN {self._vin}",
                code="capability_unsupported",
                endpoint="windows.open",
            )

        async def _cmd() -> Any:
            return await self._open_fn(self._vin)  # type: ignore[misc]

        await self._execute(_cmd, [])
