"""Message payloads and command handling of the client/server interface (spec 08).

Payload shapes follow `data/messages.schema.json` (a copy of `docs/specification/data/messages.schema.json`,
IF-004). Broadcast payloads are built synchronously on the event loop, so each one is a consistent snapshot
(IF-020, ENG-040). Incoming command payloads are validated; malformed ones get a `success=false` reply
(IF-051).
"""

import json
from collections.abc import Callable
from importlib.resources import files
from typing import Any

import fastjsonschema

from brewberrypi.engine import Engine, Reply
from brewberrypi.goals import Goal
from brewberrypi.hal import Hal
from brewberrypi.recipes import RecipeCatalogue

HARDWARE_STATUS = "/hardware/status"
PROCESS_STATE = "/process/state"
RECIPES = "/process/recipes"
CHART = "/process/chart"
REPLY = "/process/reply"
"""Topic of the CommandReply sent to the issuing client only (IF-050)."""

_SCHEMA: dict[str, Any] = json.loads(
    files("brewberrypi").joinpath("data/messages.schema.json").read_text("utf-8")
)


def validator(definition: str) -> Callable[[Any], Any]:
    """A validator for one payload definition of the messages schema, e.g. `ProcessState`."""
    return fastjsonschema.compile({"$ref": f"#/$defs/{definition}", "$defs": _SCHEMA["$defs"]})  # type: ignore[no-any-return]


# --- broadcasts (spec 8.2) ---


def hardware_status(hal: Hal) -> dict[str, Any]:
    """IF-010: temperature as a JSON number with one decimal or `null` if INVALID (FIX-02, FIX-16)."""
    temperature = hal.get_temperature()
    return {
        "temperature": None if temperature is None else round(float(temperature), 1),
        "pumpstatus": hal.get_pump_status(),
        "heatingstatus": hal.get_heating_status(),
    }


def process_state(engine: Engine) -> dict[str, Any]:
    """IF-020: `{"state": "NoProcess"}` (FIX-18) or the loaded process with all goals."""
    process = engine.process
    if process is None:
        return {"state": "NoProcess"}
    return {
        "processid": process.process_id,
        "processname": process.process_name,
        "state": process.state,
        "goals": [_goal(goal) for goal in process.goals],
    }


def _goal(goal: Goal) -> dict[str, Any]:
    progress = goal.progress
    payload: dict[str, Any] = {
        "name": goal.name,
        "description": goal.description,
        "status": goal.status,
        "statuspercent": progress.percent,
        "statusmessage": progress.message,
    }
    request = goal.active_request
    if request is not None:  # omitted without a request (legacy)
        payload["activeRequest"] = {"message": request.message, "options": list(request.options)}
    return payload


def recipe_list(recipes: RecipeCatalogue) -> list[dict[str, str]]:
    """IF-030, in catalogue order."""
    return recipes.summaries()


# --- commands (spec 8.3) ---

_COMMANDS: dict[str, tuple[str, str]] = {
    "/service/process/load": ("load", "LoadCommand"),
    "/service/process/unload": ("unload", "EmptyCommand"),
    "/service/process/start": ("start", "EmptyCommand"),
    "/service/process/pause": ("pause", "EmptyCommand"),
    "/service/process/stop": ("stop", "EmptyCommand"),
    "/service/process/request": ("respond", "RespondCommand"),
}
_VALIDATORS = {topic: validator(definition) for topic, (_, definition) in _COMMANDS.items()}


def is_command(topic: str) -> bool:
    return topic in _COMMANDS


def handle_command(engine: Engine, topic: str, payload: Any) -> dict[str, Any]:
    """Run a command and return its CommandReply (IF-050). Never raises for bad input (IF-051)."""
    command, _ = _COMMANDS[topic]
    payload = {} if payload is None else payload
    if command == "load" and isinstance(payload, dict) and "recipe" not in payload:
        reply = engine.load(None)  # legacy text "parameter 'recipe' not set."
    else:
        try:
            _VALIDATORS[topic](payload)
        except fastjsonschema.JsonSchemaValueException as error:
            message: str = error.message
            reply = Reply(
                False, f"Invalid {command} command: {message.removeprefix('data ').removeprefix('data.')}"
            )
        else:
            reply = _run(engine, command, payload)
    return {"command": command, "success": reply.success, "message": reply.message}


def _run(engine: Engine, command: str, payload: dict[str, Any]) -> Reply:
    match command:
        case "load":
            return engine.load(payload["recipe"])
        case "unload":
            return engine.unload()
        case "start":
            return engine.start()
        case "pause":
            return engine.pause()
        case "stop":
            return engine.stop()
        case _:
            return engine.respond(payload["response"])
