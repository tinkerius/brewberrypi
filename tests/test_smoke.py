"""M0 smoke tests: the package is installed and the command line starts."""

from pathlib import Path

import pytest

from brewberrypi import __version__
from brewberrypi.__main__ import main


def test_package_reports_its_installed_version() -> None:
    assert __version__ != "0.0.0"


def test_version_option_prints_the_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_dummymode_option_is_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("brewberrypi.__main__.serve", lambda app, port: 0)
    assert main(["--dummymode"]) == 0
