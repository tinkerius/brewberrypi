"""Recipe catalogue: loading and validation (RCP-001..005, spec 07).

Recipes live in a directory, one file per recipe: `<id>.json` holds the recipe with that id, in the format
`data/recipe.schema.json`. The legacy catalogue is shipped as `data/recipes/` (identical to
`docs/specification/data/recipes/`, RCP-002) and is used when no recipe directory is configured and none
exists (Q-22). An invalid recipe file is logged and skipped; the other recipes are loaded (RCP-003). Only a
configured directory that cannot be read raises `RecipeDirectoryError` (startup exit code 3).
"""

import json
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
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

RECIPE_ID = re.compile(r"[A-Za-z0-9_-]+")
"""A recipe id, which is also the recipe's file name without `.json`."""


class RecipeError(Exception):
    """A recipe file cannot be read or is invalid; that recipe is skipped (RCP-003)."""


class RecipeDirectoryError(Exception):
    """The configured recipe directory cannot be read; the application refuses to start (RCP-001, Q-22)."""


@dataclass(frozen=True)
class GoalDefinition:
    """One step of a recipe as written in the recipe file (spec 7.2)."""

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
    """Read-only list of recipes, sorted by id (RCP-002, RCP-004)."""

    recipes: tuple[Recipe, ...]
    source: str
    """The recipe directory, or `built-in` for the shipped catalogue."""

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
    """Read the recipe directory (`recipes.directory`), or the shipped catalogue (RCP-001, Q-22)."""
    directory = config.directory
    if not config.explicit and not directory.exists():
        log.info("no recipe directory %s, using the built-in recipe catalogue", directory)
        return read_catalogue(_BUILT_IN_DIRECTORY, BUILT_IN)
    if not directory.is_dir():
        raise RecipeDirectoryError(f"{directory}: recipe directory not found")
    try:
        catalogue = read_catalogue(directory, str(directory))
    except OSError as error:
        raise RecipeDirectoryError(f"{directory}: cannot read recipe directory: {error.strerror}") from None
    log.info("%d recipes read from %s", len(catalogue), directory)
    return catalogue


def read_catalogue(directory: Traversable, source: str) -> RecipeCatalogue:
    """Each `<id>.json` file of the directory, sorted by id; invalid ones are logged and skipped (RCP-003)."""
    recipes: list[Recipe] = []
    for file in directory.iterdir():
        if not file.name.endswith(".json") or not file.is_file():
            continue  # other files and subdirectories are not recipes
        location = f"{source}/{file.name}"
        try:
            try:
                text = file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                raise RecipeError(f"{location}: cannot read recipe file: {error}") from None
            recipes.append(parse_recipe(file.name.removesuffix(".json"), text, location))
        except RecipeError as error:
            log.error("invalid recipe file, recipe skipped: %s", error)
    recipes.sort(key=lambda recipe: recipe.id)
    return RecipeCatalogue(recipes=tuple(recipes), source=source)


def parse_recipe(recipe_id: str, text: str, source: str) -> Recipe:
    """Parse and validate one recipe file; errors name the file, recipe id and goal (RCP-003)."""
    if RECIPE_ID.fullmatch(recipe_id) is None:
        raise RecipeError(f"{source}: {recipe_id!r} is not a recipe id (letters, digits, _ and - only)")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as error:
        raise RecipeError(f"{source}:{error.lineno}:{error.colno}: invalid JSON: {error.msg}") from None
    recipe = repr(recipe_id)
    try:
        _validate(raw)
    except fastjsonschema.JsonSchemaValueException as error:
        raise RecipeError(f"{source}: {_describe(raw, recipe, error.message, error.name)}") from None

    goals = []
    for goal_index, raw_goal in enumerate(raw["goals"]):
        # The schema's dependentRequired (draft 2019-09) is not evaluated by fastjsonschema.
        if raw_goal["type"] == "Rest" and ("name" in raw_goal) != ("description" in raw_goal):
            where = _goal_location(recipe, goal_index, raw_goal)
            raise RecipeError(f"{source}: {where}: a Rest needs both name and description, or neither")
        goals.append(GoalDefinition(**raw_goal))
    return Recipe(id=recipe_id, name=raw["name"], goals=tuple(goals))


def _goal_location(recipe: str, goal_index: int, raw_goal: Any) -> str:
    """`recipe 'ZORA', goal 5 (index 4, Rest)`: goals numbered from 1 as in spec 7.3, plus the JSON index."""
    goal_type = raw_goal.get("type") if isinstance(raw_goal, dict) else None
    kind = f", {goal_type}" if isinstance(goal_type, str) else ""
    return f"recipe {recipe}, goal {goal_index + 1} (index {goal_index}{kind})"


_GOAL_PATH = re.compile(r"^data\.goals\[(\d+)\]")


def _describe(raw: Any, recipe: str, message: str, name: str) -> str:
    """Turn a schema error into a message with recipe id and goal number instead of a JSON path."""
    problem = message.removeprefix(name).strip()
    match = _GOAL_PATH.match(name)
    if match is None:
        field = name.removeprefix("data").removeprefix(".")
        return f"recipe {recipe}: {field} {problem}" if field else f"recipe {recipe}: {problem}"
    goal_index = int(match.group(1))
    rest = name[match.end() :].removeprefix(".")
    field = f"{rest} " if rest else ""
    return f"{_goal_location(recipe, goal_index, raw['goals'][goal_index])}: {field}{problem}"


_BUILT_IN_DIRECTORY = files("brewberrypi").joinpath("data/recipes")
_validate = fastjsonschema.compile(
    json.loads(files("brewberrypi").joinpath("data/recipe.schema.json").read_text("utf-8"))
)
