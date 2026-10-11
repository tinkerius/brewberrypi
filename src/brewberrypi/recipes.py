"""Recipe catalogue: loading and validation (RCP-001..005, spec 07).

The file format is `data/recipes.schema.json`. The legacy catalogue is shipped as `data/recipes.json`
(identical to `docs/specification/data/recipes.json`, RCP-002) and is used when no recipe file is
configured and none exists (Q-22). Any error raises `RecipeError` (startup exit code 3, RCP-003).
"""

import json
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from importlib.resources import files
from typing import Any, Literal

import fastjsonschema

from brewberrypi.config import RecipesConfig

log = logging.getLogger(__name__)

GoalType = Literal[
    "PourInBrewingWater",
    "HeatUp",
    "MashIn",
    "Rest",
    "IodineTest",
    "Lautering",
    "HeatUpForHopsCooking",
    "CookWater",
]


class RecipeError(Exception):
    """The recipe file cannot be read or is invalid; the application refuses to start (RCP-003)."""


@dataclass(frozen=True)
class GoalDefinition:
    """One step of a recipe as written in the recipe file (spec 7.2). Goal behaviour comes in M4 to M6."""

    type: GoalType
    temperature: float | None = None
    minutes: int | None = None
    name: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    goals: tuple[GoalDefinition, ...]


@dataclass(frozen=True)
class RecipeCatalogue:
    """Read-only list of recipes in file order (RCP-004)."""

    recipes: tuple[Recipe, ...]
    source: str
    """The recipe file, or `built-in` for the shipped catalogue."""

    def __iter__(self) -> Iterator[Recipe]:
        return iter(self.recipes)

    def __len__(self) -> int:
        return len(self.recipes)

    def get(self, recipe_id: str) -> Recipe | None:
        return next((recipe for recipe in self.recipes if recipe.id == recipe_id), None)

    def summaries(self) -> list[dict[str, str]]:
        """`id` and `name` of each recipe, as published to the clients (RCP-005)."""
        return [{"id": recipe.id, "name": recipe.name} for recipe in self.recipes]


BUILT_IN = "built-in"


def load_recipes(config: RecipesConfig) -> RecipeCatalogue:
    """Read the recipe file configured in `recipes.file`, or the shipped catalogue (RCP-001, Q-22)."""
    if not config.explicit and not config.file.exists():
        log.info("no recipe file %s, using the built-in recipe catalogue", config.file)
        return parse_recipes(_BUILT_IN_TEXT, BUILT_IN)
    try:
        text = config.file.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RecipeError(f"{config.file}: recipe file not found") from None
    except OSError as error:
        raise RecipeError(f"{config.file}: cannot read recipe file: {error.strerror}") from None
    catalogue = parse_recipes(text, str(config.file))
    log.info("%d recipes read from %s", len(catalogue), config.file)
    return catalogue


def parse_recipes(text: str, source: str) -> RecipeCatalogue:
    """Parse and validate a recipe file; errors name the file, recipe id and goal (RCP-003)."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise RecipeError(f"{source}:{error.lineno}:{error.colno}: invalid JSON: {error.msg}") from None
    try:
        _validate(raw)
    except fastjsonschema.JsonSchemaValueException as error:
        raise RecipeError(f"{source}: {_describe(raw, error.message, error.name)}") from None

    seen: set[str] = set()
    recipes: list[Recipe] = []
    for recipe_index, raw_recipe in enumerate(raw["recipes"]):
        recipe_id = raw_recipe["id"]
        if recipe_id in seen:
            raise RecipeError(f"{source}: recipe {recipe_index + 1}: duplicate recipe id {recipe_id!r}")
        seen.add(recipe_id)
        goals = []
        for goal_index, raw_goal in enumerate(raw_recipe["goals"]):
            # The schema's dependentRequired (draft 2019-09) is not evaluated by fastjsonschema.
            if raw_goal["type"] == "Rest" and ("name" in raw_goal) != ("description" in raw_goal):
                where = _goal_location(repr(recipe_id), goal_index, raw_goal)
                raise RecipeError(f"{source}: {where}: a Rest needs both name and description, or neither")
            goals.append(GoalDefinition(**raw_goal))
        recipes.append(Recipe(id=recipe_id, name=raw_recipe["name"], goals=tuple(goals)))
    return RecipeCatalogue(recipes=tuple(recipes), source=source)


def _goal_location(recipe: str, goal_index: int, raw_goal: Any) -> str:
    """`recipe 'ZORA', goal 5 (index 4, Rest)`: goals numbered from 1 as in spec 7.3, plus the JSON index."""
    goal_type = raw_goal.get("type") if isinstance(raw_goal, dict) else None
    kind = f", {goal_type}" if isinstance(goal_type, str) else ""
    return f"recipe {recipe}, goal {goal_index + 1} (index {goal_index}{kind})"


_RECIPE_PATH = re.compile(r"^data\.recipes\[(\d+)\](?:\.goals\[(\d+)\])?")


def _describe(raw: Any, message: str, name: str) -> str:
    """Turn a schema error into a message with recipe id and goal number instead of a JSON path."""
    problem = message.removeprefix(name).strip()
    match = _RECIPE_PATH.match(name)
    if match is None:
        return f"{name.removeprefix('data.')} {problem}" if name != "data" else problem
    recipe_index = int(match.group(1))
    raw_recipe = raw["recipes"][recipe_index]
    recipe_id = raw_recipe.get("id") if isinstance(raw_recipe, dict) else None
    recipe = repr(recipe_id) if isinstance(recipe_id, str) else f"number {recipe_index + 1}"
    rest = name[match.end() :].removeprefix(".")
    field = f"{rest} " if rest else ""
    if match.group(2) is None:
        return f"recipe {recipe}: {field}{problem}"
    goal_index = int(match.group(2))
    return f"{_goal_location(recipe, goal_index, raw_recipe['goals'][goal_index])}: {field}{problem}"


_BUILT_IN_TEXT = files("brewberrypi").joinpath("data/recipes.json").read_text("utf-8")
_validate = fastjsonschema.compile(
    json.loads(files("brewberrypi").joinpath("data/recipes.schema.json").read_text("utf-8"))
)
