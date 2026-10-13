# BrewberryPi

Raspberry Pi controller for a home-brewing mash kettle. It switches the heater and
the circulation pump, reads a DS18B20 temperature probe, works through a recipe
step by step (heat up, rest, mash in, iodine test, …) and is operated from any
browser in the local network.

## Status

| Phase | Content | Status |
|---|---|---|
| 1 — Specification | Technology-neutral functional specification, recovered from the original 2014 Java implementation | ✅ done |
| 2 — Implementation | Technology decision (ADR-0001), then implementation milestone by milestone ([plan](docs/implementation-plan.md)) | ⏳ in progress |

## Documentation

| Document | Purpose |
|---|---|
| [docs/specification/00-index.md](docs/specification/00-index.md) | Functional specification (start here) |
| [docs/specification/11-acceptance-criteria.md](docs/specification/11-acceptance-criteria.md) | Testable acceptance criteria |
| [docs/specification/13-open-questions.md](docs/specification/13-open-questions.md) | Open decisions for the product owner |
| [docs/recovery/bug-and-deviation-log.md](docs/recovery/bug-and-deviation-log.md) | Where and why the spec deviates from the original implementation |
| [docs/adr/](docs/adr/) | Architecture decision records |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Milestones M0–M12 |
| [docs/hardware/wiring.md](docs/hardware/wiring.md) | Wiring guide and diagram (default pins) |

## Working with Claude Code

Open this folder in VS Code, install the recommended extensions when prompted,
and start Claude Code (Claude Code panel, or `claude` in the integrated terminal).
Claude Code loads [CLAUDE.md](CLAUDE.md) automatically.

Project skills (in `.claude/skills/`):

| Command | Purpose |
|---|---|
| `/choose-stack` | Prepare and record the technology decision (ADR-0001) |
| `/implement-milestone M<n>` | Implement one milestone test-first against its acceptance criteria |
| `/verify-spec [prefix]` | Check the implementation against requirements and acceptance criteria |
| `/spec-question <text>` | Record an open question instead of guessing |

## Development

Technology stack: [ADR-0001](docs/adr/0001-technology-stack.md). In short: Python (Starlette + uvicorn,
WebSocket) and a Vite/Preact front end, shipped as a signed container image. On the Raspberry Pi the image
runs under Podman on BrewberryPi OS, which is developed in the separate repository `tinkerius/brewberrypi-os`.
The interface between the two is the [runtime contract](docs/deployment/runtime-contract.md).

### Development environment

**Recommended: the devcontainer.** Open the folder in VS Code and choose **Reopen in Container**. You need Docker and the
Dev Containers extension. The container has the same OS and Python as the runtime image (Debian Trixie,
Python 3.13, `python3-libgpiod`), plus uv, Node 22, make, cosign v2, the GitHub CLI, Claude Code (CLI and VS Code
extension) and access to the host's Docker (Docker's own `docker-ce-cli`, because Moby packages do not exist
for Trixie). On first start it runs `make setup`. The devcontainer feature versions are pinned in
`.devcontainer/devcontainer-lock.json`; to update them, run `devcontainer upgrade` (Dev Containers CLI) or
*Dev Containers: Update Feature Versions* and commit the new lock file.

**Without the devcontainer** you need Python ≥ 3.11, [uv](https://docs.astral.sh/uv/), Node.js ≥ 22,
make and Docker (or Podman: `make image CONTAINER=podman`).

### Commands

| Command | What it does |
|---|---|
| `make setup` | Install the Python (`uv sync`) and front-end (`npm ci`) dependencies from the lock files |
| `make lint` | ruff (lint + format check), mypy (strict), TypeScript type check |
| `make test` | pytest and Vitest |
| `make build` | Build the front end into the package and the Python wheel (`dist/`) |
| `make image` | Build the container image `ghcr.io/tinkerius/brewberrypi:<version>` for the local platform |
| `make run` | Run in simulation: `uv run brewberrypi --dummymode` |
| `make dev` | `make run` plus the Vite dev server with live reload on http://localhost:5173; Ctrl+C stops both |
| `make format` | Auto-format and auto-fix lint findings |

In VS Code the same commands are available as tasks (*Terminal → Run Task…*, `.vscode/tasks.json`), and
*Run and Debug* (F5, `.vscode/launch.json`) starts the back end in simulation under the debugger, optionally
together with the Vite dev server.

CI (`.github/workflows/ci.yml`) runs lint, test and build on every push and pull request, and builds the image
for `linux/arm64` and `linux/amd64`. A tag `v<version>` (matching `pyproject.toml`) also pushes the image to
GHCR and signs it with cosign v2. It then verifies the image against the device's signature policy; see
[deploy/signing/README.md](deploy/signing/README.md). Finally it creates a GitHub release: a **draft** for
`v1.2.3`, published by hand once the [hardware test protocol](docs/deployment/hardware-test-protocol.md) has
passed, or a published **pre-release** with an untested-on-hardware warning for `v1.2.3-alpha.N`, `-beta.N`
or `-rc.N` (`pyproject.toml` then holds `1.2.3-alpha.N`). BrewberryPi OS installs only `MAJOR.MINOR.PATCH`
versions (runtime contract §1), so a pre-release image has to be run by hand.

### Configuration

`brewberrypi --config <file>` reads a JSON configuration file. Without `--config` it reads `config.json` from
the working directory, or uses the built-in defaults if there is none. Every key is optional. The format is
[config.schema.json](docs/specification/data/config.schema.json), and
[config.example.json](docs/specification/data/config.example.json) lists every key with its default (the legacy
wiring). Unknown keys are ignored with a warning; invalid values stop the start with exit code 2.

In simulation (`--dummymode`) a simulated kettle replaces the hardware: it heats by 0.085 °C per second at
full power and cools by 0.005 °C per second (section `simulation`). `simulation.timeScale` speeds up the
whole application, e.g. `60` runs a 10-minute rest in 10 seconds. Beeps play on the computer's audio output
if `paplay`, `aplay`, `afplay` or Windows sound is available, otherwise they are only logged.

The recipes come from `recipes.json` next to the configuration file (`recipes.file`). Without one, the 8 legacy
recipes built into the application are used. An invalid recipe file stops the start with exit code 3 and names
the recipe and goal. The format is [recipes.schema.json](docs/specification/data/recipes.schema.json); see
[07-recipes.md](docs/specification/07-recipes.md).

### Real-time interface

The server serves the web UI and a WebSocket at `/ws` on one port (`server.port`, default 8080). Every message
is one JSON object `{"topic": ..., "payload": ...}` with the topics and payloads of
[08-client-server-interface.md](docs/specification/08-client-server-interface.md). Commands are sent on
`/service/process/*`, and their reply comes back to the sender on `/process/reply`.

### Running as a service

The container image implements the application side of the
[runtime contract](docs/deployment/runtime-contract.md): exit codes, graceful shutdown on SIGTERM/SIGINT
with all outputs off, the systemd notify protocol (`READY=1`, `STOPPING=1`, `WATCHDOG=1` every
`BREWBERRYPI_WATCHDOG_MS` while the engine and broadcasts are alive) when `NOTIFY_SOCKET` is set, and
`GET /healthz`. `tests/test_contract.py` checks this against the real program.

Before the first real brew, run the [hardware test protocol](docs/deployment/hardware-test-protocol.md) on the Pi.

### Diagnostic tools

Three command-line tools for installation and diagnosis on the Pi ([12-auxiliary-tools.md](docs/specification/12-auxiliary-tools.md)).
They read the same configuration (`--config`), and accept `--dummymode` for a test run without hardware:

| Command | What it does |
|---|---|
| `brewberrypi-temperature-logger [FILE]` | Appends `yyyy/MM/dd HH:mm:ss;<°C>` (or `ERROR`) to `temperatureLog.csv` every second |
| `brewberrypi-sensor-test` | Prints the DS18B20 temperature about once per second, failures on stderr |
| `brewberrypi-gpio-test [--duty-cycle]` | Switches heating, pump and buzzer in a 2-second cycle to check the wiring; all off on Ctrl+C |

The logger and the sensor test only read the sensor, so they can run next to the main application. The GPIO test
needs the GPIO lines, so stop the main application first.
