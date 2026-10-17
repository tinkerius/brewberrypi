"""M1: configuration (NFR-020, NFR-030, HW-010..013, AC-082, Q-19, Q-21)."""

import json
import logging
from pathlib import Path
from typing import Any

import pytest

from brewberrypi.config import ConfigError, load_config

SPEC_DATA = Path(__file__).parents[1] / "docs" / "specification" / "data"
EXAMPLE = SPEC_DATA / "config.example.json"


def write_config(tmp_path: Path, content: Any, name: str = "config.json") -> Path:
    file = tmp_path / name
    file.write_text(json.dumps(content))
    return file


def test_AC_082_example_config_has_the_legacy_wiring() -> None:
    hardware = load_config(EXAMPLE).hardware
    assert (hardware.heating.pin, hardware.heating.active_low) == (23, True)
    assert (hardware.pump.pin, hardware.pump.active_low) == (22, True)
    assert (hardware.buzzer.pin, hardware.buzzer.active_low) == (10, False)


def test_built_in_defaults_equal_the_example_config(tmp_path: Path) -> None:
    defaults = load_config(cwd=tmp_path)
    example = load_config(EXAMPLE)
    assert defaults.source is None
    assert example.source == EXAMPLE
    for section in ("server", "hardware", "control", "engine", "ui", "events", "chart", "simulation"):
        assert getattr(defaults, section) == getattr(example, section), section
    assert defaults.recipes.directory.name == example.recipes.directory.name == "recipes"


def test_default_values() -> None:
    config = load_config(EXAMPLE)
    assert config.server.port == 8080
    assert config.hardware.heating.mode == "dutycycle"
    assert config.hardware.heating.min_phase_milliseconds == 10000  # FIX-26
    assert config.hardware.sensor.sensor_id == "auto"
    assert config.hardware.sensor.devices_path == Path("/sys/bus/w1/devices")
    assert config.hardware.sensor.stale_after_seconds == 5
    assert config.control.hysteresis_lower_offset == -0.1
    assert config.engine.tick_milliseconds == 500
    assert config.simulation.heating_rate_per_second == 0.085


def test_Q21_config_json_in_the_working_directory_is_read(tmp_path: Path) -> None:
    write_config(tmp_path, {"server": {"port": 9000}})
    config = load_config(cwd=tmp_path)
    assert config.source == tmp_path / "config.json"
    assert config.server.port == 9000


def test_Q21_without_config_file_the_built_in_defaults_are_used(tmp_path: Path) -> None:
    config = load_config(cwd=tmp_path)
    assert config.source is None
    assert config.recipes.directory == tmp_path / "recipes"
    assert not config.recipes.explicit


def test_missing_values_are_filled_with_defaults(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, {"hardware": {"heating": {"pin": 17}}}))
    assert config.hardware.heating.pin == 17
    assert config.hardware.heating.active_low is True
    assert config.hardware.pump.pin == 22
    assert config.server.port == 8080


def test_Q19_recipe_directory_resolves_against_the_config_file_directory(tmp_path: Path) -> None:
    (tmp_path / "etc").mkdir()
    file = write_config(tmp_path / "etc", {"recipes": {"directory": "my-recipes"}})
    config = load_config(Path("etc/config.json"), cwd=tmp_path)
    assert config.source == file
    assert config.recipes.directory == tmp_path / "etc" / "my-recipes"
    assert config.recipes.explicit


def test_Q19_absolute_recipe_directory_is_kept(tmp_path: Path) -> None:
    config = load_config(write_config(tmp_path, {"recipes": {"directory": "/srv/recipes"}}))
    assert config.recipes.directory == Path("/srv/recipes")


def test_unknown_keys_only_warn(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    file = write_config(tmp_path, {"colour": "red", "hardware": {"pump": {"pin": 5, "speed": 3}}})
    with caplog.at_level(logging.WARNING):
        config = load_config(file)
    assert config.hardware.pump.pin == 5
    warnings = [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]
    assert f"{file}: unknown configuration key colour is ignored" in warnings
    assert f"{file}: unknown configuration key hardware.pump.speed is ignored" in warnings


def test_schema_key_is_not_unknown(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        load_config(EXAMPLE)
    assert not [record for record in caplog.records if record.levelno >= logging.WARNING]


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ({"hardware": {"heating": {"pin": 28}}}, "hardware.heating.pin must be smaller than or equal to 27"),
        ({"hardware": {"pump": {"activeLow": "yes"}}}, "hardware.pump.activeLow must be boolean"),
        ({"hardware": {"heating": {"mode": "pwm"}}}, "hardware.heating.mode must be one of"),
        ({"hardware": {"sensor": {"sensorId": "29-x"}}}, "hardware.sensor.sensorId must match pattern"),
        ({"server": {"port": 0}}, "server.port must be bigger than or equal to 1"),
        ({"control": {"nearTargetPower": 0}}, "control.nearTargetPower must be bigger than 0"),
        ({"server": 8080}, "server must be object"),
        ([], "must be a JSON object"),
    ],
)
def test_invalid_values_refuse_to_start(tmp_path: Path, content: Any, expected: str) -> None:
    file = write_config(tmp_path, content)
    with pytest.raises(ConfigError) as error:
        load_config(file)
    assert str(error.value).startswith(f"{file}: ")
    assert expected in str(error.value)


def test_invalid_json_names_file_line_and_column(tmp_path: Path) -> None:
    file = tmp_path / "config.json"
    file.write_text('{\n  "server": }')
    with pytest.raises(ConfigError, match=r"config.json:2:\d+: invalid JSON"):
        load_config(file)


def test_missing_explicit_config_file_refuses_to_start(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="configuration file not found"):
        load_config(tmp_path / "missing.json")


def test_configuration_is_read_only() -> None:
    config = load_config(EXAMPLE)
    with pytest.raises(AttributeError):
        config.server.port = 1  # type: ignore[misc]
