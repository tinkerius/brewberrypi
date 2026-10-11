"""M7: real-time interface (spec 08; AC-070..072, AC-005 interface part)."""

import asyncio
import functools
import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from brewberrypi.clock import ManualClock
from brewberrypi.config import load_config
from brewberrypi.engine import Engine
from brewberrypi.hal.mock import MockHal
from brewberrypi.recipes import load_recipes
from brewberrypi.web.app import create_app
from brewberrypi.web.hub import Client, Hub, Topic, envelope
from brewberrypi.web.messages import (
    REPLY,
    handle_command,
    hardware_status,
    process_state,
    recipe_list,
    validator,
)

CONFIG = load_config(Path(__file__).parents[1] / "docs" / "specification" / "data" / "config.example.json")
CATALOGUE = load_recipes(CONFIG.recipes)
HARDWARE_STATUS = validator("HardwareStatus")
PROCESS_STATE = validator("ProcessState")
RECIPE_LIST = validator("RecipeList")
COMMAND_REPLY = validator("CommandReply")


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock()


@pytest.fixture
def hal(clock: ManualClock) -> MockHal:
    return MockHal(clock, temperature=20.0)


@pytest.fixture
async def engine(hal: MockHal, clock: ManualClock) -> AsyncIterator[Engine]:
    engine = Engine(hal, clock, CATALOGUE, CONFIG)
    yield engine
    await engine.shutdown()


# --- payloads (spec 8.2, IF-004) ---


def test_AC_071_temperature_is_a_json_number_with_one_decimal(hal: MockHal) -> None:
    hal.set_temperature(62.5)
    hal.switch_on_pump()
    hal.set_heating(0.5)
    status = hardware_status(hal)
    HARDWARE_STATUS(status)
    assert envelope("/hardware/status", status) == (
        '{"topic": "/hardware/status", '
        '"payload": {"temperature": 62.5, "pumpstatus": true, "heatingstatus": 0.5}}'
    )


def test_AC_005_invalid_temperature_is_null(hal: MockHal) -> None:
    hal.set_temperature(None)
    status = hardware_status(hal)
    HARDWARE_STATUS(status)
    assert status["temperature"] is None
    assert '"temperature": null' in envelope("/hardware/status", status)


def test_AC_072_no_process(engine: Engine) -> None:
    assert process_state(engine) == {"state": "NoProcess"}
    PROCESS_STATE(process_state(engine))


async def test_IF_020_process_state_with_goals_and_active_request(
    engine: Engine, hal: MockHal, clock: ManualClock
) -> None:
    hal.set_temperature(25.0)
    engine.load("TEST")
    state = process_state(engine)
    PROCESS_STATE(state)
    assert state == {
        "processid": "TEST",
        "processname": "Test Process",
        "state": "Loaded",
        "goals": [
            {
                "name": "Iodine Test",
                "description": "Now it's your job to do the iodine test.",
                "status": "Waiting",
                "statuspercent": 0,
                "statusmessage": "0%",
            }
        ],
    }
    engine.start()
    await clock.advance(0)
    goal = process_state(engine)["goals"][0]
    assert goal["activeRequest"] == {"message": "Iodine test successfull?", "options": ["Yes", "No"]}
    assert goal["statusmessage"] == "Waiting for answer"
    PROCESS_STATE(process_state(engine))


def test_IF_030_recipe_list_in_catalogue_order() -> None:
    recipes = recipe_list(CATALOGUE)
    RECIPE_LIST(recipes)
    assert recipes[0] == {"id": "ZORA", "name": "München 12.6 - SUD1:ZORA"}
    assert [r["id"] for r in recipes] == [
        "ZORA",
        "HANCOCK",
        "HIPA",
        "WIT",
        "BENIWEISS",
        "WaterBoil",
        "Dummy",
        "TEST",
    ]


# --- commands (spec 8.3, IF-050, IF-051) ---


@pytest.mark.parametrize(
    ("topic", "payload", "reply"),
    [
        (
            "/service/process/load",
            {"recipe": "ZORA"},
            (True, "Process München 12.6 - SUD1:ZORA (ZORA) loaded."),
        ),
        ("/service/process/load", {}, (False, "parameter 'recipe' not set.")),
        ("/service/process/load", None, (False, "parameter 'recipe' not set.")),
        ("/service/process/load", {"recipe": "NOPE"}, (False, "Unknown recipe 'NOPE'.")),
        ("/service/process/load", {"recipe": 7}, (False, "Invalid load command: recipe must be string")),
        ("/service/process/load", "ZORA", (False, "Invalid load command: must be object")),
        ("/service/process/start", {}, (False, "No process loaded.")),
        (
            "/service/process/start",
            {"now": True},
            (False, "Invalid start command: must not contain {'now'} properties"),
        ),
        ("/service/process/unload", None, (False, "No process loaded.")),
        ("/service/process/pause", {}, (False, "No process loaded.")),
        ("/service/process/stop", {}, (False, "No process loaded.")),
        (
            "/service/process/request",
            {"response": "Yes"},
            (False, "There is no active request to respond to."),
        ),
        (
            "/service/process/request",
            {},
            (False, "Invalid respond command: must contain ['response'] properties"),
        ),
    ],
)
def test_IF_050_every_command_gets_a_reply(
    engine: Engine, topic: str, payload: Any, reply: tuple[bool, str]
) -> None:
    result = handle_command(engine, topic, payload)
    COMMAND_REPLY(result)
    assert (result["success"], result["message"]) == reply


# --- hub (IF-005, broadcast loops) ---


class FakeConnection:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def send(self, text: str) -> None:
        self.messages.append(json.loads(text))

    def topics(self) -> list[str]:
        return [m["topic"] for m in self.messages]


async def test_AC_070_a_new_client_gets_every_topic_at_once(clock: ManualClock) -> None:
    hub = Hub(clock, [Topic(f"/t{i}", 0.5, functools.partial(int, i)) for i in range(4)])
    connection = FakeConnection()
    client = Client(connection.send)
    sender = asyncio.create_task(client.run())
    hub.connect(client)
    await clock.advance(0)
    assert connection.topics() == ["/t0", "/t1", "/t2", "/t3"]
    sender.cancel()


async def test_broadcasts_follow_their_periods(clock: ManualClock) -> None:
    counter = {"fast": 0, "slow": 0}

    def build(name: str) -> int:
        counter[name] += 1
        return counter[name]

    hub = Hub(clock, [Topic("/fast", 0.5, lambda: build("fast")), Topic("/slow", 1.0, lambda: build("slow"))])
    connection = FakeConnection()
    client = Client(connection.send)
    sender = asyncio.create_task(client.run())
    hub.connect(client)
    loops = asyncio.create_task(hub.run())
    await clock.advance(2)
    assert connection.topics().count("/fast") == 1 + 4
    assert connection.topics().count("/slow") == 1 + 2
    loops.cancel()
    sender.cancel()


async def test_a_failing_broadcast_is_logged_and_the_loop_continues(
    clock: ManualClock, caplog: pytest.LogCaptureFixture
) -> None:
    calls = 0

    def flaky() -> int:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("boom")
        return calls

    hub = Hub(clock, [Topic("/flaky", 1.0, flaky)])
    connection = FakeConnection()
    client = Client(connection.send)
    sender = asyncio.create_task(client.run())
    loops = asyncio.create_task(hub.run())
    hub.connect(client)  # call 1
    with caplog.at_level(logging.ERROR):
        await clock.advance(3)  # calls 2 (fails), 3, 4
    assert [m["payload"] for m in connection.messages] == [1, 3, 4]
    assert "building broadcast /flaky failed" in caplog.text
    loops.cancel()
    sender.cancel()


async def test_a_slow_client_only_gets_the_latest_value_per_topic() -> None:
    release = asyncio.Event()
    sent: list[str] = []

    async def slow_send(text: str) -> None:
        await release.wait()
        sent.append(json.loads(text)["payload"])

    client = Client(slow_send)
    sender = asyncio.create_task(client.run())
    client.offer("/a", envelope("/a", 1))
    await asyncio.sleep(0)  # the sender now blocks on message 1
    for value in (2, 3, 4):
        client.offer("/a", envelope("/a", value))
    client.reply(envelope(REPLY, "r"))
    release.set()
    for _ in range(10):
        await asyncio.sleep(0)
    assert sent == [1, "r", 4]  # replies are never dropped, broadcasts are coalesced
    sender.cancel()


# --- the application over a real WebSocket ---


def receive_until(websocket: Any, topic: str, limit: int = 20) -> dict[str, Any]:
    for _ in range(limit):
        message: dict[str, Any] = websocket.receive_json()
        if message["topic"] == topic:
            return message
    raise AssertionError(f"no message on {topic}")


def test_AC_070_websocket_client_gets_all_topics_and_command_replies(
    hal: MockHal, clock: ManualClock
) -> None:
    app = create_app(CONFIG, CATALOGUE, hal, clock)
    with TestClient(app) as http, http.websocket_connect("/ws") as websocket:
        first = {websocket.receive_json()["topic"] for _ in range(4)}
        assert first == {"/hardware/status", "/process/state", "/process/recipes", "/process/chart"}

        websocket.send_text("not json")  # ignored (IF-051)
        websocket.send_json({"topic": "/unknown", "payload": {}})  # ignored
        websocket.send_json({"topic": "/service/process/load", "payload": {"recipe": "Dummy"}})
        reply = receive_until(websocket, REPLY)
        assert reply["payload"] == {
            "command": "load",
            "success": True,
            "message": "Process My Dummy Process (Dummy) loaded.",
        }

        websocket.send_json({"topic": "/service/process/start", "payload": {}})
        assert receive_until(websocket, REPLY)["payload"]["message"] == "Process started."
        state = receive_until(websocket, "/process/state")["payload"]
        assert state["processid"] == "Dummy"
    # leaving the app's lifespan switches everything off
    assert (hal.get_heating_status(), hal.get_pump_status()) == (0.0, False)


def test_replies_go_to_the_sender_only(hal: MockHal, clock: ManualClock) -> None:
    app = create_app(CONFIG, CATALOGUE, hal, clock)
    with TestClient(app) as http, http.websocket_connect("/ws") as one, http.websocket_connect("/ws") as two:
        one.send_json({"topic": "/service/process/load", "payload": {"recipe": "TEST"}})
        assert receive_until(one, REPLY)["payload"]["success"] is True
        two.send_json({"topic": "/service/process/unload", "payload": {}})
        reply = receive_until(two, REPLY)
        assert reply["payload"] == {"command": "unload", "success": True, "message": "Process unloaded."}


def test_static_front_end_is_served(hal: MockHal, clock: ManualClock, tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text("<title>Brewberry Pi</title>")
    with TestClient(create_app(CONFIG, CATALOGUE, hal, clock, static_dir=tmp_path)) as http:
        response = http.get("/")
    assert response.status_code == 200
    assert "Brewberry Pi" in response.text


def test_missing_front_end_is_explained(hal: MockHal, clock: ManualClock, tmp_path: Path) -> None:
    with TestClient(create_app(CONFIG, CATALOGUE, hal, clock, static_dir=tmp_path)) as http:
        response = http.get("/")
    assert response.status_code == 503
    assert "make build" in response.text


async def test_chart_samples_on_its_period_with_the_app_clock(hal: MockHal) -> None:
    """The chart timestamps come from the application clock (simulated time in simulation)."""
    app_clock = ManualClock(wall_start=1_000.0)
    broadcast_clock = ManualClock()
    app = create_app(CONFIG, CATALOGUE, hal, app_clock, broadcast_clock=broadcast_clock)
    async with app.router.lifespan_context(app):
        await app_clock.advance(60)
        await broadcast_clock.advance(1)
        hal.set_temperature(None)
        await broadcast_clock.advance(1)
        assert app.state.chart.data()[0]["values"] == [{"x": 1_060_000, "y": 20.0}]
