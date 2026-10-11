"""Broadcast hub: periodic broadcasts to all connected clients (spec 8.2, IF-001, IF-005).

Each topic has a period and a function that builds its payload. Every period the payload is built once,
serialised once and offered to every client. A client sends from its own task and keeps only the latest
message per topic, so a slow browser never delays the others or the engine. A new client gets the current
value of every topic at once (IF-005). A failing broadcast is logged and its loop continues.
"""

import asyncio
import json
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from brewberrypi.clock import Clock

log = logging.getLogger(__name__)


def envelope(topic: str, payload: Any) -> str:
    """The wire format: one JSON object `{"topic": ..., "payload": ...}` per WebSocket text message."""
    return json.dumps({"topic": topic, "payload": payload}, ensure_ascii=False)


@dataclass(frozen=True)
class Topic:
    name: str
    period_seconds: float
    build: Callable[[], Any]
    """Builds the current payload."""
    before: Callable[[], None] | None = None
    """Runs once per period before `build` (the chart takes its sample here), not on connect."""


class Client:
    """One connected browser."""

    def __init__(self, send: Callable[[str], Awaitable[None]]) -> None:
        self._send = send
        self._latest: dict[str, str] = {}
        self._replies: deque[str] = deque()
        self._wake = asyncio.Event()

    def offer(self, topic: str, message: str) -> None:
        """Queue a broadcast; replaces an unsent older message of the same topic."""
        self._latest[topic] = message
        self._wake.set()

    def reply(self, message: str) -> None:
        """Queue a reply; replies are never dropped."""
        self._replies.append(message)
        self._wake.set()

    async def run(self) -> None:
        """Send queued messages until the connection fails or the task is cancelled."""
        while True:
            await self._wake.wait()
            self._wake.clear()
            while self._replies:
                await self._send(self._replies.popleft())
            latest, self._latest = self._latest, {}
            for message in latest.values():
                await self._send(message)


class Hub:
    def __init__(self, clock: Clock, topics: list[Topic]) -> None:
        self._clock = clock
        self._topics = topics
        self._clients: set[Client] = set()

    @property
    def clients(self) -> int:
        return len(self._clients)

    def connect(self, client: Client) -> None:
        """Register a client and queue the current value of every topic (IF-005)."""
        self._clients.add(client)
        for topic in self._topics:
            message = self._build(topic)
            if message is not None:
                client.offer(topic.name, message)

    def disconnect(self, client: Client) -> None:
        self._clients.discard(client)

    async def run(self) -> None:
        """Run one broadcast loop per topic until cancelled."""
        await asyncio.gather(*(self._loop(topic) for topic in self._topics))

    async def _loop(self, topic: Topic) -> None:
        while True:
            await self._clock.sleep(topic.period_seconds)
            try:
                if topic.before is not None:
                    topic.before()
            except Exception:
                log.exception("preparing broadcast %s failed", topic.name)
            message = self._build(topic)
            if message is not None:
                for client in list(self._clients):
                    client.offer(topic.name, message)

    def _build(self, topic: Topic) -> str | None:
        try:
            return envelope(topic.name, topic.build())
        except Exception:
            log.exception("building broadcast %s failed", topic.name)
            return None
