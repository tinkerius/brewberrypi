"""Command-line entry point (`brewberrypi`).

Implements startup steps 1 and 2 of NFR-021: read and validate the configuration and the recipe file, and
refuse to start with the exit codes of the runtime contract. The remaining steps follow in M10.
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path

from brewberrypi import __version__
from brewberrypi.clock import Clock, ScaledClock, SystemClock
from brewberrypi.config import ConfigError, load_config
from brewberrypi.hal.simulation import SimulationHal
from brewberrypi.hal.sound import find_player
from brewberrypi.recipes import RecipeError, load_recipes

log = logging.getLogger("brewberrypi")

# Exit codes (docs/deployment/runtime-contract.md §2).
EXIT_OK = 0
EXIT_INVALID_CONFIG = 2
EXIT_INVALID_RECIPES = 3


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
    if args.dummymode:
        clock = create_clock(config.simulation.time_scale)
        SimulationHal(clock, config.simulation, find_player())
    else:
        log.warning("the Raspberry Pi HAL is not implemented yet (milestone M9)")
    log.warning("engine and web server are not started yet (milestones M7, M10); exiting")
    return EXIT_OK


def create_clock(time_scale: float) -> Clock:
    """The application clock; accelerated by `simulation.timeScale` in simulation mode only (HW-064)."""
    return SystemClock() if time_scale == 1 else ScaledClock(SystemClock(), time_scale)


if __name__ == "__main__":
    raise SystemExit(main())
