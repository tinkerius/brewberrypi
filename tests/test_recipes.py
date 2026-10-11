"""M1: recipe catalogue (RCP-001..005, AC-080, AC-081, Q-22)."""

import json
from pathlib import Path
from typing import Any

import pytest

from brewberrypi.config import RecipesConfig
from brewberrypi.recipes import BUILT_IN, GoalDefinition, RecipeError, load_recipes, parse_recipes

SPEC_DATA = Path(__file__).parents[1] / "docs" / "specification" / "data"
PACKAGE_DATA = Path(__file__).parents[1] / "src" / "brewberrypi" / "data"
LEGACY_ORDER = ["ZORA", "HANCOCK", "HIPA", "WIT", "BENIWEISS", "WaterBoil", "Dummy", "TEST"]


def write_recipes(tmp_path: Path, goals: list[dict[str, Any]], recipe_id: str = "MyRecipe") -> RecipesConfig:
    file = tmp_path / "recipes.json"
    file.write_text(json.dumps({"recipes": [{"id": recipe_id, "name": "My recipe", "goals": goals}]}))
    return RecipesConfig(file=file, explicit=True)


def test_AC_080_shipped_recipe_file_equals_the_spec_catalogue() -> None:
    assert (PACKAGE_DATA / "recipes.json").read_bytes() == (SPEC_DATA / "recipes.json").read_bytes()
    catalogue = load_recipes(RecipesConfig(file=Path("/nonexistent/recipes.json"), explicit=False))
    assert catalogue.source == BUILT_IN
    assert [recipe.id for recipe in catalogue] == LEGACY_ORDER
    assert [summary["id"] for summary in catalogue.summaries()] == LEGACY_ORDER


@pytest.mark.parametrize("name", ["recipes.schema.json", "config.schema.json"])
def test_shipped_schemas_equal_the_spec(name: str) -> None:
    assert (PACKAGE_DATA / name).read_bytes() == (SPEC_DATA / name).read_bytes()


def test_AC_081_rest_without_minutes_refuses_to_start_naming_recipe_and_goal(tmp_path: Path) -> None:
    config = write_recipes(
        tmp_path, [{"type": "HeatUp", "temperature": 62}, {"type": "Rest", "temperature": 62}]
    )
    with pytest.raises(RecipeError) as error:
        load_recipes(config)
    message = str(error.value)
    assert str(config.file) in message
    assert "recipe 'MyRecipe', goal 2 (index 1, Rest)" in message
    assert "minutes" in message


def test_spec_recipe_file_is_read_with_verbatim_texts() -> None:
    catalogue = load_recipes(RecipesConfig(file=SPEC_DATA / "recipes.json", explicit=True))
    assert catalogue.source == str(SPEC_DATA / "recipes.json")
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


def test_recipe_file_from_the_configuration_is_used(tmp_path: Path) -> None:
    catalogue = load_recipes(write_recipes(tmp_path, [{"type": "MashIn"}]))
    assert catalogue.summaries() == [{"id": "MyRecipe", "name": "My recipe"}]


def test_existing_default_recipe_file_is_used_instead_of_the_built_in_one(tmp_path: Path) -> None:
    config = write_recipes(tmp_path, [{"type": "MashIn"}])
    catalogue = load_recipes(RecipesConfig(file=config.file, explicit=False))
    assert catalogue.source == str(config.file)


def test_missing_configured_recipe_file_refuses_to_start(tmp_path: Path) -> None:
    with pytest.raises(RecipeError, match="recipe file not found"):
        load_recipes(RecipesConfig(file=tmp_path / "missing.json", explicit=True))


def test_invalid_json_names_file_line_and_column() -> None:
    with pytest.raises(RecipeError, match=r"^my.json:2:\d+: invalid JSON"):
        parse_recipes('{"recipes": [\n  oops ]}', "my.json")


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
def test_invalid_goal_refuses_to_start_naming_recipe_and_goal(
    tmp_path: Path, goal: dict[str, Any], expected: str
) -> None:
    with pytest.raises(RecipeError) as error:
        load_recipes(write_recipes(tmp_path, [goal]))
    assert "recipe 'MyRecipe'" in str(error.value)
    assert expected in str(error.value)


def test_rest_with_default_texts_is_valid(tmp_path: Path) -> None:
    catalogue = load_recipes(write_recipes(tmp_path, [{"type": "Rest", "temperature": 62, "minutes": 10}]))
    assert catalogue.recipes[0].goals[0] == GoalDefinition(type="Rest", temperature=62, minutes=10)


def test_duplicate_recipe_ids_refuse_to_start() -> None:
    recipe = {"id": "A", "name": "a", "goals": [{"type": "MashIn"}]}
    with pytest.raises(RecipeError, match="recipe 2: duplicate recipe id 'A'"):
        parse_recipes(json.dumps({"recipes": [recipe, recipe]}), "r.json")


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ({}, "must contain ['recipes']"),
        ({"recipes": []}, "recipes must contain at least 1 items"),
        (
            {"recipes": [{"id": "bad id", "name": "x", "goals": [{"type": "MashIn"}]}]},
            "recipe 'bad id': id must",
        ),
        (
            {"recipes": [{"id": 7, "name": "x", "goals": [{"type": "MashIn"}]}]},
            "recipe number 1: id must be string",
        ),
        ({"recipes": [{"id": "A", "name": "x", "goals": []}]}, "recipe 'A': goals must contain at least 1"),
    ],
)
def test_invalid_recipe_structure_refuses_to_start(content: dict[str, Any], expected: str) -> None:
    with pytest.raises(RecipeError) as error:
        parse_recipes(json.dumps(content), "r.json")
    assert expected in str(error.value)
