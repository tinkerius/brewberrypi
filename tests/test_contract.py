"""M10: runtime contract tests against the real program (docs/deployment/runtime-contract.md §2, §4, §5).

Each test starts `python -m brewberrypi` as a subprocess, as the host does, with its own notify socket.
These are integration tests: they take real time (a few seconds) and need a free TCP port.
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

READY_TIMEOUT = 20.0


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


def start(
    tmp_path: Path, *args: str, config: dict[str, object] | None = None, env: dict[str, str] | None = None
) -> subprocess.Popen[str]:
    if config is not None:
        (tmp_path / "config.json").write_text(json.dumps(config))
    return subprocess.Popen(
        [sys.executable, "-m", "brewberrypi", *args],
        cwd=tmp_path,
        env={**os.environ, **(env or {})},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


@pytest.fixture
def notify_socket(tmp_path: Path) -> Iterator[socket.socket]:
    receiver = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    receiver.bind(str(tmp_path / "notify.sock"))
    receiver.settimeout(READY_TIMEOUT)
    yield receiver
    receiver.close()


def receive(receiver: socket.socket, expected: str) -> list[str]:
    """Notifications until `expected` arrives."""
    messages: list[str] = []
    while expected not in messages:
        messages.append(receiver.recv(100).decode())
    return messages


def test_contract_ready_healthz_watchdog_and_sigterm(tmp_path: Path, notify_socket: socket.socket) -> None:
    port = free_port()
    process = start(
        tmp_path,
        "--dummymode",
        config={"server": {"port": port}},
        env={"NOTIFY_SOCKET": str(tmp_path / "notify.sock"), "BREWBERRYPI_WATCHDOG_MS": "200"},
    )
    try:
        receive(notify_socket, "READY=1")
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz", timeout=5) as response:
            health = json.load(response)
        assert health["status"] == "ok"
        assert health["engine"] == "NoProcess"
        receive(notify_socket, "WATCHDOG=1")

        sent = time.monotonic()
        process.send_signal(signal.SIGTERM)
        receive(notify_socket, "STOPPING=1")
        assert process.wait(timeout=5) == 0  # exits 0 within 5 s (§2, NFR-022)
        assert time.monotonic() - sent < 5
    finally:
        process.kill()
        output = process.communicate()[0]
    lines = output.splitlines()
    ready = next(i for i, line in enumerate(lines) if "BrewberryPI ready for brewing :-)" in line)
    listening = next(i for i, line in enumerate(lines) if "Uvicorn running on" in line)
    assert listening < ready  # ready only once the server listens (NFR-021 step 6)
    assert any("Shutting down BrewberryPi." in line for line in lines)
    assert any("change pump status" in line or "beep: short" in line for line in lines[ready:])


def test_contract_sigint_also_exits_0(tmp_path: Path, notify_socket: socket.socket) -> None:
    process = start(
        tmp_path,
        "--dummymode",
        config={"server": {"port": free_port()}},
        env={"NOTIFY_SOCKET": str(tmp_path / "notify.sock")},
    )
    try:
        receive(notify_socket, "READY=1")
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=5) == 0
    finally:
        process.kill()
        process.communicate()


@pytest.mark.parametrize(
    ("files", "args", "code"),
    [
        ({"config.json": '{"server": {"port": "x"}}'}, ["--dummymode"], 2),
        ({"recipes.json": '{"recipes": []}'}, ["--dummymode"], 3),
        ({}, ["--config", "missing.json"], 2),
    ],
)
def test_contract_exit_codes(tmp_path: Path, files: dict[str, str], args: list[str], code: int) -> None:
    for name, content in files.items():
        (tmp_path / name).write_text(content)
    process = start(tmp_path, *args)
    assert process.wait(timeout=20) == code
    process.communicate()


def test_contract_hardware_initialisation_failure_exits_4(tmp_path: Path) -> None:
    """Without --dummymode on a machine without GPIO chips (or bindings): exit code 4."""
    process = start(tmp_path)
    assert process.wait(timeout=20) == 4
    assert "hardware initialisation failed" in process.communicate()[0]
