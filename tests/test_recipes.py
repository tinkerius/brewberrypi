"""M1: recipe catalogue, one file per recipe (RCP-001..005, AC-080, AC-081, Q-22, Q-27)."""

import json
import logging
import re
from pathlib import Path
from typing import Any

import pytest

from brewberrypi.config import RecipesConfig
from brewberrypi.recipes import (
    BUILT_IN,
    GoalDefinition,
    RecipeDirectoryError,
    RecipeError,
    load_recipes,
    parse_recipe,
)

SPEC_DATA = Path(__file__).parents[1] / "docs" / "specification" / "data"
PACKAGE_DATA = Path(__file__).parents[1] / "src" / "brewberrypi" / "data"
SORTED_IDS = ["BENIWEISS", "Dummy", "HANCOCK", "HIPA", "TEST", "WIT", "WaterBoil", "ZORA"]


def write_recipe(directory: Path, goals: list[dict[str, Any]], recipe_id: str = "MyRecipe") -> Path:
    directory.mkdir(exist_ok=True)
    file = directory / f"{recipe_id}.json"
    file.write_text(json.dumps({"name": f"Recipe {recipe_id}", "goals": goals}))
    return file


def configured(directory: Path) -> RecipesConfig:
    return RecipesConfig(directory=directory, explicit=True)


def test_AC_080_shipped_recipe_files_equal_the_spec_catalogue() -> None:
    spec_files = sorted(file.name for file in (SPEC_DATA / "recipes").iterdir())
    assert spec_files == [f"{recipe_id}.json" for recipe_id in SORTED_IDS]
    for name in spec_files:
        assert (PACKAGE_DATA / "recipes" / name).read_bytes() == (SPEC_DATA / "recipes" / name).read_bytes()
    assert sorted(file.name for file in (PACKAGE_DATA / "recipes").iterdir()) == spec_files
    catalogue = load_recipes(RecipesConfig(directory=Path("/nonexistent/recipes"), explicit=False))
    assert catalogue.source == BUILT_IN
    assert [recipe.id for recipe in catalogue] == SORTED_IDS
    assert [summary["id"] for summary in catalogue.summaries()] == SORTED_IDS


@pytest.mark.parametrize("name", ["recipe.schema.json", "config.schema.json", "messages.schema.json"])
def test_shipped_schemas_equal_the_spec(name: str) -> None:
    assert (PACKAGE_DATA / name).read_bytes() == (SPEC_DATA / name).read_bytes()


def test_AC_081_rest_without_minutes_is_skipped_naming_file_and_goal(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    directory = tmp_path / "recipes"
    bad = write_recipe(
        directory, [{"type": "HeatUp", "temperature": 62}, {"type": "Rest", "temperature": 62}]
    )
    write_recipe(directory, [{"type": "MashIn"}], recipe_id="Good")
    with caplog.at_level(logging.ERROR):
        catalogue = load_recipes(configured(directory))
    assert [recipe.id for recipe in catalogue] == ["Good"]  # the other recipes are loaded
    [record] = caplog.records
    message = record.getMessage()
    assert message.startswith("invalid recipe file, recipe skipped: ")
    assert str(bad) in message
    assert "recipe 'MyRecipe', goal 2 (index 1, Rest)" in message
    assert "minutes" in message


def test_spec_recipe_files_are_read_with_verbatim_texts() -> None:
    catalogue = load_recipes(configured(SPEC_DATA / "recipes"))
    assert catalogue.source == str(SPEC_DATA / "recipes")
    assert [recipe.id for recipe in catalogue] == SORTED_IDS
    hipa = catalogue.get("HIPA")
    assert hipa is not None
    assert hipa.name == "München 12.6 - SUD4:HIPA"
    assert hipa.goals[3] == GoalDefinition(
        type="Rest",
        temperature=68,
        minutes=60,
        name="Verzuckerungsrast",
        description="Verzuckuerungsrast @68 for 60min",  # legacy typo kept (Q-07)
    )
    zora = catalogue.get("ZORA")
    assert zora is not None
    assert len(zora.goals) == 11
    assert zora.goals[9] == GoalDefinition(type="IodineTest", temperature=68, minutes=10)  # Q-05


def test_Q27_file_name_is_the_id_and_the_list_is_sorted_by_it(tmp_path: Path) -> None:
    directory = tmp_path / "recipes"
    for recipe_id in ["b", "A", "a-2", "B_1"]:
        write_recipe(directory, [{"type": "MashIn"}], recipe_id=recipe_id)
    catalogue = load_recipes(configured(directory))
    assert catalogue.summaries() == [
        {"id": "A", "name": "Recipe A"},
        {"id": "B_1", "name": "Recipe B_1"},
        {"id": "a-2", "name": "Recipe a-2"},
        {"id": "b", "name": "Recipe b"},
    ]


def test_Q27_other_files_and_subdirectories_are_ignored(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    directory = tmp_path / "recipes"
    write_recipe(directory, [{"type": "MashIn"}])
    (directory / "README.md").write_text("notes")
    (directory / "MyRecipe.json~").write_text("editor backup")
    (directory / "old.json").mkdir()
    write_recipe(directory / "archive", [{"type": "MashIn"}], recipe_id="Archived")
    with caplog.at_level(logging.ERROR):
        catalogue = load_recipes(configured(directory))
    assert [recipe.id for recipe in catalogue] == ["MyRecipe"]
    assert caplog.records == []


def test_Q27_a_file_name_that_is_no_recipe_id_is_skipped(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    directory = tmp_path / "recipes"
    write_recipe(directory, [{"type": "MashIn"}], recipe_id="my recipe")
    with caplog.at_level(logging.ERROR):
        assert len(load_recipes(configured(directory))) == 0
    assert "'my recipe' is not a recipe id" in caplog.text


def test_an_id_inside_the_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RecipeError, match=re.escape("must not contain {'id'}")):
        parse_recipe("R", json.dumps({"id": "R", "name": "r", "goals": [{"type": "MashIn"}]}), "R.json")


def test_existing_default_recipe_directory_is_used_instead_of_the_built_in_one(tmp_path: Path) -> None:
    directory = tmp_path / "recipes"
    write_recipe(directory, [{"type": "MashIn"}])
    catalogue = load_recipes(RecipesConfig(directory=directory, explicit=False))
    assert catalogue.source == str(directory)
    assert [recipe.id for recipe in catalogue] == ["MyRecipe"]


def test_an_empty_recipe_directory_gives_no_recipes(tmp_path: Path) -> None:
    (tmp_path / "recipes").mkdir()
    assert len(load_recipes(configured(tmp_path / "recipes"))) == 0


def test_missing_configured_recipe_directory_refuses_to_start(tmp_path: Path) -> None:
    with pytest.raises(RecipeDirectoryError, match="recipe directory not found"):
        load_recipes(configured(tmp_path / "missing"))


def test_a_configured_file_instead_of_a_directory_refuses_to_start(tmp_path: Path) -> None:
    (tmp_path / "recipes.json").write_text("{}")
    with pytest.raises(RecipeDirectoryError, match="recipe directory not found"):
        load_recipes(configured(tmp_path / "recipes.json"))


def test_unreadable_recipe_file_is_skipped(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    directory = tmp_path / "recipes"
    directory.mkdir()
    (directory / "Latin1.json").write_bytes('{"name": "Eiweißrast"}'.encode("latin-1"))
    with caplog.at_level(logging.ERROR):
        assert len(load_recipes(configured(directory))) == 0
    assert "Latin1.json: cannot read recipe file" in caplog.text


def test_invalid_json_names_file_line_and_column() -> None:
    with pytest.raises(RecipeError, match=r"^my.json:2:\d+: invalid JSON"):
        parse_recipe("my", '{"name": "x",\n  oops }', "my.json")


@pytest.mark.parametrize(
    ("goal", "expected"),
    [
        ({"type": "Boil"}, "goal 1 (index 0, Boil): type must be one of"),
        ({"type": "HeatUp"}, "goal 1 (index 0, HeatUp): must contain ['temperature']"),
        ({"type": "HeatUp", "temperature": 111}, "temperature must be smaller than or equal to 110"),
        ({"type": "Rest", "temperature": 62, "minutes": -1}, "minutes must be bigger than or equal to 0"),
        ({"type": "Rest", "temperature": 62, "minutes": 1.5}, "minutes must be integer"),
        ({"type": "MashIn", "temperature": 62}, "must not contain {'temperature'}"),
        ({"type": "CookWater", "minutes": 20}, "goal 1 (index 0, CookWater): must contain ["),
        ({"type": "Rest", "temperature": 62, "minutes": 1, "name": "Rast"}, "both name and description"),
    ],
)
def test_invalid_goal_is_reported_naming_recipe_and_goal(goal: dict[str, Any], expected: str) -> None:
    with pytest.raises(RecipeError) as error:
        parse_recipe("MyRecipe", json.dumps({"name": "x", "goals": [goal]}), "MyRecipe.json")
    assert str(error.value).startswith("MyRecipe.json: recipe 'MyRecipe', goal 1")
    assert expected in str(error.value)


def test_rest_with_default_texts_is_valid() -> None:
    recipe = parse_recipe(
        "R",
        json.dumps({"name": "x", "goals": [{"type": "Rest", "temperature": 62, "minutes": 10}]}),
        "R.json",
    )
    assert recipe.goals[0] == GoalDefinition(type="Rest", temperature=62, minutes=10)


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ({}, "recipe 'R': must contain ['goals', 'name']"),
        ([], "recipe 'R': must be object"),
        ({"name": "", "goals": [{"type": "MashIn"}]}, "recipe 'R': name must be longer than or equal to 1"),
        ({"name": "x", "goals": []}, "recipe 'R': goals must contain at least 1"),
    ],
)
def test_invalid_recipe_structure_is_reported(content: Any, expected: str) -> None:
    with pytest.raises(RecipeError) as error:
        parse_recipe("R", json.dumps(content), "R.json")
    assert expected in str(error.value)
