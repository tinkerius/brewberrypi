"""Command-line entry point (`brewberrypi`).

Startup (NFR-021): read and validate the configuration and the recipe file, create the HAL (simulation with
`--dummymode`; the Raspberry Pi HAL follows in M9), then serve the web application. Refuses to start with the
exit codes of the runtime contract. Readiness notification, watchdog and `/healthz` follow in M10.
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from starlette.types import ASGIApp

from brewberrypi import __version__
from brewberrypi.clock import Clock, ScaledClock, SystemClock
from brewberrypi.config import ConfigError, load_config
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
    if not args.dummymode:
        log.error(
            "hardware initialisation failed: the Raspberry Pi HAL is not implemented yet (milestone M9)"
        )
        return EXIT_HARDWARE
    clock = create_clock(config.simulation.time_scale)
    hal = SimulationHal(clock, config.simulation, find_player())
    return serve(create_app(config, recipes, hal, clock), config.server.port)


def serve(app: ASGIApp, port: int) -> int:
    """Run the web server until SIGINT/SIGTERM; the app switches the outputs off on shutdown.

    Returns the exit code. A server that cannot start (e.g. the port is in use) is an unexpected error (1);
    uvicorn's own exit code 3 would mean "invalid recipe file" to the host (runtime contract §2).
    """
    log.info("web server on port %d", port)
    # All interfaces: the UI is used from other devices in the LAN (IF-002).
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=port, log_config=None))
    try:
        server.run()
    except SystemExit:  # uvicorn exits with its own code 3 when it cannot bind the port
        log.error("the web server could not start")
        return EXIT_ERROR
    return EXIT_OK


def create_clock(time_scale: float) -> Clock:
    """The application clock; accelerated by `simulation.timeScale` in simulation mode only (HW-064)."""
    return SystemClock() if time_scale == 1 else ScaledClock(SystemClock(), time_scale)


if __name__ == "__main__":
    raise SystemExit(main())
