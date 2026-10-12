"""systemd notify protocol for the host's supervision (runtime contract §4).

Active only when `NOTIFY_SOCKET` is set (Podman passes it into the container for a Quadlet service with
`Notify=yes`). `READY=1` after startup, `STOPPING=1` when shutdown begins, `WATCHDOG=1` every
`BREWBERRYPI_WATCHDOG_MS` milliseconds while the application is alive.
"""

import logging
import os
import socket
from collections.abc import Mapping

log = logging.getLogger(__name__)

WATCHDOG_ENV = "BREWBERRYPI_WATCHDOG_MS"


class Notifier:
    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        environ = os.environ if environ is None else environ
        address = environ.get("NOTIFY_SOCKET", "")
        # A leading "@" is an abstract socket address.
        self._address = "\0" + address[1:] if address.startswith("@") else address
        watchdog = environ.get(WATCHDOG_ENV, "")
        self.watchdog_seconds: float | None = (
            int(watchdog) / 1000 if watchdog.isdigit() and int(watchdog) > 0 else None
        )
        """Interval of the watchdog pings; `None` without supervision."""
        if not self._address:
            self.watchdog_seconds = None

    @property
    def enabled(self) -> bool:
        return bool(self._address)

    def notify(self, message: str) -> None:
        """Send one notification; failures are logged and never disturb the application."""
        if not self._address:
            return
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
                sock.sendto(message.encode(), self._address)
        except OSError as error:
            log.warning("sd_notify %s failed: %s", message, error)
