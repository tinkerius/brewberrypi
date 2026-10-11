"""M1: startup steps 1 and 2 of NFR-021 with the exit codes of the runtime contract."""

import json
from pathlib import Path

import pytest

from brewberrypi.__main__ import EXIT_INVALID_CONFIG, EXIT_INVALID_RECIPES, EXIT_OK, main


@pytest.fixture(autouse=True)
def empty_working_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def test_starts_with_built_in_defaults_and_recipes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--dummymode"]) == EXIT_OK
    assert "recipes: ZORA, HANCOCK, HIPA, WIT, BENIWEISS, WaterBoil, Dummy, TEST" in capsys.readouterr().out


def test_log_lines_have_timestamp_level_and_component(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--dummymode"])
    line = capsys.readouterr().out.splitlines()[0]
    assert " INFO brewberrypi: BrewberryPi " in line
    assert line[:4].isdigit()


def test_invalid_configuration_exits_with_code_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (tmp_path / "config.json").write_text(json.dumps({"server": {"port": "eighty"}}))
    assert main(["--config", "config.json"]) == EXIT_INVALID_CONFIG
    assert "ERROR brewberrypi: invalid configuration, refusing to start" in capsys.readouterr().out


def test_AC_081_invalid_recipe_file_exits_with_code_3(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    recipes = {"recipes": [{"id": "R", "name": "r", "goals": [{"type": "Rest", "temperature": 62}]}]}
    (tmp_path / "recipes.json").write_text(json.dumps(recipes))
    assert main(["--dummymode"]) == EXIT_INVALID_RECIPES
    output = capsys.readouterr().out
    assert "ERROR brewberrypi: invalid recipe file, refusing to start" in output
    assert "recipe 'R', goal 1 (index 0, Rest)" in output
