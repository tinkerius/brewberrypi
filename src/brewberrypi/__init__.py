"""BrewberryPi: Raspberry Pi controller for a home-brewing mash kettle."""

import re
from importlib.metadata import PackageNotFoundError, version

_PEP440_PRE_RELEASE = re.compile(r"(\d+\.\d+\.\d+)(a|b|rc)(\d+)")
_SEMVER_PRE_RELEASE = {"a": "alpha", "b": "beta", "rc": "rc"}


def semver(installed: str) -> str:
    """Convert an installed (PEP 440 normalised) version back to the release tag's semver form.

    `pyproject.toml` holds `0.2.0-alpha.1`, which the package metadata normalises to `0.2.0a1`.
    The image tag, its version label and `/healthz` all use `0.2.0-alpha.1` (runtime contract §1).
    """
    match = _PEP440_PRE_RELEASE.fullmatch(installed)
    if match is None:
        return installed
    release, kind, number = match.groups()
    return f"{release}-{_SEMVER_PRE_RELEASE[kind]}.{number}"


try:
    __version__ = semver(version("brewberrypi"))
except PackageNotFoundError:  # source tree without installation
    __version__ = "0.0.0"
