"""Command-line entry point (`brewberrypi`).

Startup (NFR-021): read and validate the configuration and the recipe file, create the HAL (simulation with
`--dummymode`, else the Raspberry Pi), then serve the web application. Refuses to start with the
exit codes of the runtime contract (§2).
"""

import argparse
import contextlib
import logging
import socket
import sys
from collections.abc import Callable, Generator, Sequence
from pathlib import Path

import uvicorn
from starlette.applications import Starlette

from brewberrypi import __version__
from brewberrypi.clock import Clock, ScaledClock, SystemClock
from brewberrypi.config import ConfigError, load_config
from brewberrypi.hal import Hal
from brewberrypi.hal.gpio import GpioError
from brewberrypi.hal.raspberry_pi import RaspberryPiHal
from brewberrypi.hal.simulation import SimulationHal
from brewberrypi.hal.sound import find_player
from brewberrypi.recipes import RecipeError, load_recipes
from brewberrypi.web.app import create_app

log = logging.getLogger("brewberrypi")

# Exit codes (docs/deployment/runtime-contract.md §2).
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INVALID_CONFIG = 2
EXIT_INVALID_RECIPES = 3
EXIT_HARDWARE = 4


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brewberrypi", description="BrewberryPi mash kettle controller")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--dummymode", action="store_true", help="use the simulation HAL instead of GPIO")
    parser.add_argument(
        "--config",
        metavar="PATH",
        type=Path,
        help="configuration file (JSON); default: ./config.json if it exists, else the built-in defaults",
    )
    return parser


def configure_logging() -> None:
    """Standard output with timestamp, level and component (NFR-040)."""
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        force=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()
    log.info(
        "BrewberryPi %s starting%s", __version__, " in simulation (--dummymode)" if args.dummymode else ""
    )
    try:
        config = load_config(args.config)
    except ConfigError as error:
        log.error("invalid configuration, refusing to start: %s", error)
        return EXIT_INVALID_CONFIG
    try:
        recipes = load_recipes(config.recipes)
    except RecipeError as error:
        log.error("invalid recipe file, refusing to start: %s", error)
        return EXIT_INVALID_RECIPES
    log.info("recipes: %s", ", ".join(recipe.id for recipe in recipes))
    clock: Clock
    hal: Hal
    if args.dummymode:
        clock = create_clock(config.simulation.time_scale)
        hal = SimulationHal(clock, config.simulation, find_player())
    else:
        clock = SystemClock()  # simulation.timeScale does not apply to real hardware (HW-064)
        try:
            hal = RaspberryPiHal(clock, config.hardware)
        except GpioError as error:
            log.error("hardware initialisation failed: %s", error)
            return EXIT_HARDWARE
    return serve(create_app(config, recipes, hal, clock), config.server.port)


def serve(app: Starlette, port: int) -> int:
    """Run the web server until SIGINT/SIGTERM and return the exit code (runtime contract §2).

    When the server listens, the app announces readiness (NFR-021 step 6). On SIGINT/SIGTERM the app shuts
    down gracefully, switching the outputs off, and the process exits with 0. A server that cannot start
    (e.g. the port is in use) is an unexpected error (1); uvicorn's own exit code 3 would mean "invalid
    recipe file" to the host.
    """
    log.info("web server on port %d", port)
    # All interfaces: the UI is used from other devices in the LAN (IF-002).
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_config=None, timeout_graceful_shutdown=2)

    def announce_ready() -> None:
        app.state.ready()  # set by the app's lifespan startup

    server = _Server(config, on_started=announce_ready)
    try:
        server.run()
    except SystemExit:  # uvicorn exits with its own code 3 when it cannot bind the port
        log.error("the web server could not start")
        return EXIT_ERROR
    return EXIT_OK


class _Server(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, on_started: Callable[[], None]) -> None:
        super().__init__(config)
        self._on_started = on_started

    async def startup(self, sockets: list[socket.socket] | None = None) -> None:
        await super().startup(sockets=sockets)
        if self.started:
            self._on_started()

    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None, None, None]:
        """Like uvicorn's, but a handled SIGTERM/SIGINT is not raised again after the graceful shutdown,
        so the process exits with 0 instead of 143/130 (runtime contract §2, NFR-022)."""
        with super().capture_signals():
            try:
                yield
            finally:
                self._captured_signals.clear()


def create_clock(time_scale: float) -> Clock:
    """The application clock; accelerated by `simulation.timeScale` in simulation mode only (HW-064)."""
    return SystemClock() if time_scale == 1 else ScaledClock(SystemClock(), time_scale)


if __name__ == "__main__":
    raise SystemExit(main())
