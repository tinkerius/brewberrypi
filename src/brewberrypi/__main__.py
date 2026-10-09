"""Command-line entry point (`brewberrypi`).

Milestone M0 skeleton: the options of NFR-020 are accepted, but configuration loading (M1)
and the startup sequence (M10) are not implemented yet.
"""

import argparse
import sys
from collections.abc import Sequence

from brewberrypi import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brewberrypi", description="BrewberryPi mash kettle controller")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--dummymode", action="store_true", help="use the simulation HAL instead of GPIO")
    parser.add_argument("--config", metavar="PATH", help="configuration file (JSON)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    build_parser().parse_args(argv)
    print(f"BrewberryPi {__version__}: not implemented yet (milestone M0 skeleton).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
