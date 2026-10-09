# BrewberryPi

Raspberry Pi controller for a home-brewing mash kettle. It switches the heater and
the circulation pump, reads a DS18B20 temperature probe, works through a recipe
step by step (heat up, rest, mash in, iodine test, …) and is operated from any
browser in the local network.

## Status

| Phase | Content | Status |
|---|---|---|
| 1 — Specification | Technology-neutral functional specification, recovered from the original 2014 Java implementation | ✅ done |
| 2 — Implementation | Technology decision (ADR-0001), then implementation milestone by milestone | ⏳ next |

## Documentation

| Document | Purpose |
|---|---|
| [docs/specification/00-index.md](docs/specification/00-index.md) | Functional specification (start here) |
| [docs/specification/11-acceptance-criteria.md](docs/specification/11-acceptance-criteria.md) | Testable acceptance criteria |
| [docs/specification/13-open-questions.md](docs/specification/13-open-questions.md) | Open decisions for the product owner |
| [docs/recovery/bug-and-deviation-log.md](docs/recovery/bug-and-deviation-log.md) | Where and why the spec deviates from the original implementation |
| [docs/adr/](docs/adr/) | Architecture decision records |
| [docs/implementation-plan.md](docs/implementation-plan.md) | Milestones M0–M12 |

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
Python 3.13, `python3-libgpiod`), plus uv, Node 22, make, the GitHub CLI, Claude Code (CLI and VS Code
extension) and access to the host's Docker. On first start it runs `make setup`.

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
| `make format` | Auto-format and auto-fix lint findings |

CI (`.github/workflows/ci.yml`) runs lint, test and build on every push and pull request, and builds the image
for `linux/arm64` and `linux/amd64`. A tag `v<version>` (matching `pyproject.toml`) also pushes the image to
GHCR and signs it with cosign v2. It then verifies the image against the device's signature policy; see
[deploy/signing/README.md](deploy/signing/README.md).
