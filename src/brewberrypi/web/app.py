"""The web application: UI files and the real-time channel on one port (IF-001, IF-002, ADR-0001).

Real-time channel: WebSocket at `/ws`. Every message in both directions is one JSON text message
`{"topic": "<topic>", "payload": <payload>}` with the logical topic names of spec 08. The server broadcasts
`/hardware/status`, `/process/state`, `/process/recipes` and `/process/chart`; the client sends commands on
`/service/process/*` and receives each command's reply on `/process/reply`.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket

from brewberrypi import __version__
from brewberrypi.chart import TemperatureChart
from brewberrypi.clock import Clock, SystemClock
from brewberrypi.config import Config
from brewberrypi.engine import Engine
from brewberrypi.hal import Hal
from brewberrypi.notify import Notifier
from brewberrypi.recipes import RecipeCatalogue
from brewberrypi.web.hub import Client, Hub, Topic, envelope
from brewberrypi.web.messages import (
    CHART,
    HARDWARE_STATUS,
    PROCESS_STATE,
    RECIPES,
    REPLY,
    handle_command,
    hardware_status,
    is_command,
    process_state,
    recipe_list,
)

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def create_app(  # noqa: PLR0913  (clocks and UI folder are injectable for tests)
    config: Config,
    recipes: RecipeCatalogue,
    hal: Hal,
    clock: Clock,
    *,
    broadcast_clock: Clock | None = None,
    static_dir: Path = STATIC_DIR,
    notifier: Notifier | None = None,
) -> Starlette:
    """The application. `clock` drives the engine and the chart timestamps (scaled in simulation, HW-064);
    `broadcast_clock` paces the broadcasts in real time."""
    broadcast_clock = SystemClock() if broadcast_clock is None else broadcast_clock
    notifier = Notifier() if notifier is None else notifier

    @asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        await hal.start()  # sensor loop, first reading (HW-030, HW-034); outputs are already off (HW-020)
        engine = Engine(hal, clock, recipes, config)
        topics, chart = _broadcasts(config, recipes, hal, clock, engine)
        hub = Hub(broadcast_clock, topics)
        app.state.engine, app.state.hub, app.state.chart = engine, hub, chart
        broadcasts = asyncio.create_task(hub.run())
        background = [broadcasts]
        if notifier.watchdog_seconds is not None:

            def alive() -> bool:
                return engine.alive() and not broadcasts.done()

            watchdog = _watchdog(notifier, broadcast_clock, notifier.watchdog_seconds, alive)
            background.append(asyncio.create_task(watchdog))

        def ready() -> None:
            """Startup step 6 of NFR-021, once the server is listening."""
            log.info("BrewberryPI ready for brewing :-)")
            hal.short_beep()
            notifier.notify("READY=1")

        app.state.ready = ready
        try:
            yield
        finally:
            log.info("Shutting down BrewberryPi.")  # NFR-022
            notifier.notify("STOPPING=1")
            for task in background:
                task.cancel()
            await asyncio.gather(*background, return_exceptions=True)
            await engine.shutdown()  # outputs off on every shutdown path (HW-021, ADR-0001)
            await hal.close()  # buzzer off, GPIO released

    routes: list[Route | WebSocketRoute | Mount] = [
        WebSocketRoute("/ws", _realtime),
        Route("/healthz", _healthz),
    ]
    if (static_dir / "index.html").is_file():
        routes.append(Mount("/", StaticFiles(directory=static_dir, html=True)))
    else:
        routes.append(Route("/", _front_end_missing))
    return Starlette(routes=routes, lifespan=lifespan)


async def _realtime(websocket: WebSocket) -> None:
    """One browser on the real-time channel: broadcasts out, commands in, replies out (spec 08)."""
    engine: Engine = websocket.app.state.engine
    hub: Hub = websocket.app.state.hub
    await websocket.accept()
    client = Client(websocket.send_text)
    hub.connect(client)
    sender = asyncio.create_task(client.run())
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            text = message.get("text")
            if text is not None:
                _handle(engine, client, text)
    finally:
        hub.disconnect(client)
        sender.cancel()
        await asyncio.gather(sender, return_exceptions=True)


async def _healthz(request: Request) -> Response:
    """Runtime contract §5."""
    engine: Engine = request.app.state.engine
    return JSONResponse({"status": "ok", "version": __version__, "engine": engine.state})


def _handle(engine: Engine, client: Client, text: str) -> None:
    """Run one incoming command; anything malformed is logged and never disturbs the server (IF-051)."""
    try:
        message = json.loads(text)
    except json.JSONDecodeError:
        log.warning("ignored a message that is not JSON")
        return
    topic = message.get("topic") if isinstance(message, dict) else None
    if not isinstance(topic, str) or not is_command(topic):
        log.warning("ignored a message for unknown topic %r", topic)
        return
    client.reply(envelope(REPLY, handle_command(engine, topic, message.get("payload"))))


def _broadcasts(
    config: Config, recipes: RecipeCatalogue, hal: Hal, clock: Clock, engine: Engine
) -> tuple[list[Topic], TemperatureChart]:
    """The broadcast topics of spec 8.2 with their configured periods, and the chart history they share."""
    periods = config.broadcast
    chart = TemperatureChart(config.chart.max_points)
    topics = [
        Topic(HARDWARE_STATUS, periods.hardware_status_milliseconds / 1000, lambda: hardware_status(hal)),
        Topic(PROCESS_STATE, periods.process_state_milliseconds / 1000, lambda: process_state(engine)),
        Topic(RECIPES, periods.recipes_milliseconds / 1000, lambda: recipe_list(recipes)),
        Topic(
            CHART,
            periods.chart_milliseconds / 1000,
            chart.data,
            before=lambda: chart.sample(clock.wall_time(), hal.get_temperature()),
        ),
    ]
    return topics, chart


async def _watchdog(notifier: Notifier, clock: Clock, interval: float, alive: Callable[[], bool]) -> None:
    """WATCHDOG=1 only while the engine and the broadcasts are alive, so a hang stops the pings (§4)."""
    healthy = True
    while True:
        if alive():
            notifier.notify("WATCHDOG=1")
            healthy = True
        elif healthy:
            log.error("engine or broadcast loop is not alive; no more watchdog pings")
            healthy = False
        await clock.sleep(interval)


async def _front_end_missing(request: Request) -> Response:
    return PlainTextResponse(
        "The front end is not built. Run `make build`, or use `make dev`.", status_code=503
    )
