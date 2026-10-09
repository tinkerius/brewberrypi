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

Build, test and run commands (`make build`, `make test`, `uv run brewberrypi --dummymode`, …) are added in
milestone M0.
