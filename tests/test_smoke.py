"""M0 smoke tests: the package is installed and the command line starts."""

import tomllib
from pathlib import Path

import pytest

from brewberrypi import __version__, semver
from brewberrypi.__main__ import main


def test_package_reports_its_installed_version() -> None:
    assert __version__ != "0.0.0"


def test_reported_version_matches_the_project_version() -> None:
    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text())["project"]
    assert __version__ == project["version"]


@pytest.mark.parametrize(
    ("installed", "expected"),
    [
        ("0.2.0", "0.2.0"),
        ("0.2.0a1", "0.2.0-alpha.1"),
        ("1.10.3b12", "1.10.3-beta.12"),
        ("2.0.0rc2", "2.0.0-rc.2"),
    ],
)
def test_pre_release_versions_are_reported_in_semver_form(installed: str, expected: str) -> None:
    assert semver(installed) == expected


def test_version_option_prints_the_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_dummymode_option_is_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("brewberrypi.__main__.serve", lambda app, port: 0)
    assert main(["--dummymode"]) == 0
