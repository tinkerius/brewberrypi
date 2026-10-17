# ADR-0001: Technology Stack for the BrewberryPi Rebuild

- **Status:** Accepted; the "Web/real-time" row is superseded by [ADR-0002](0002-rest-and-server-sent-events.md)
- **Date:** 2026-10-09
- **Deciders:** Benedikt Hauptmann (product owner); proposal and research by Claude Code

## Context

The legacy system (Java 7, Jetty 7/8, CometD 2, Pi4J 1/WiringPi, AngularJS 1.2)
is end-of-life and does not run on current Raspberry Pi models. Phase 1 produced a
technology-neutral specification (`docs/specification/`). Phase 2 must choose a stack that
satisfies in particular:

- `NFR-050` Raspberry Pi 3/4/5 (Pi 5 → libgpiod / gpiochip GPIO access)
- `NFR-051` Simulation mode on Windows/macOS/Linux developer machines
- `NFR-060` Testability with mock HAL and controllable clock
- `IF-002` Real-time bidirectional browser channel with auto-reconnect, single port
- `UI-070` Offline-capable front end (all assets local)
- `NFR-001..005` Safe output handling on shutdown/crash, monotonic timers
- `NFR-023/024` Runs as a system service, non-root

Constraints from the product owner (2026-10-08/09):
- The maintainers know Python.
- The Pi 3 (1 GB) must stay supported.
- A front-end build step is acceptable.
- Deployment should feel like a games console: self-contained, safe to unplug, versions picked from a container registry.
- Everything runs locally, with no vendor cloud.
- No hardware change to the relay board.

Background: [legacy-technology-notes.md](../recovery/legacy-technology-notes.md) §3. Research
done for this decision on 2026-10-08/09 (primary sources, adversarially fact-checked) produced
these facts:

- **GPIO outputs persist after a crash.** On current Raspberry Pi kernels (`rpi-6.12.y`, `rpi-6.18.y`), `persist_gpio_outputs` defaults to true in both `pinctrl-bcm2835` (Pi 3/4) and `pinctrl-rp1` (Pi 5). An output keeps its last level when the owning process dies, so a crash while heating leaves the heater on unless something outside the process resets the pin.
- **The Pi 5 header GPIO chip number is not stable.** It is `gpiochip4` on older kernels and `gpiochip0` since 2024. On the Bookworm 6.12.96 kernel it moved again, to `gpiochip15`.
- **gpiozero cannot follow this reliably.** The Raspberry Pi apt package ignores the `chip=` argument, and PyPI only fixed it in `2.0.1.post3`. lgpio also needs a writable working directory and `chdir()`s the whole process into it.
- **Docker's restart policies have no post-stop hook, and Docker ignores health status.** A hung container is never restarted.
- **Podman + Quadlet is systemd-native.** Its units accept `ExecStopPost=`, `Restart=`, `OnFailure=` and `Notify=true`. It has no daemon to restart, and Raspberry Pi OS Trixie ships it as Podman 5.4.2.

## Options considered

### Application stack

1. **A — Python asyncio, Starlette + uvicorn, plain WebSocket** — one event loop for broadcasts, commands and the engine tick (no locks, consistent snapshots `ENG-040`); few, mostly pure-Python dependencies. Reconnect logic must be written in the client (~30 lines).
2. **B — Python, aiohttp** — one library for HTTP, WebSocket and static files, but several compiled dependencies with less reliable ARM wheels.
3. **C — Python, Flask-SocketIO with threads** — reconnect built in, but heavier protocol and client, thread synchronisation, harder deterministic tests.
4. (Not pursued: Java/Pi4J v2, .NET, Node, Go. The maintainers chose Python.)

### GPIO library

1. **gpiozero on lgpio** (initial proposal) — familiar, but the Pi 5 chip-number problem above makes it unreliable. On a failing lgpio it silently falls back to another pin factory, which is a safety problem for the heater relay.
2. **Own thin HAL on libgpiod v2** — the kernel project's official bindings (`python3-libgpiod` 2.2.1 in Debian Trixie, no compiling). It finds the chip by label and claims output lines with their initial value and bias in one request.

### Delivery and runtime

1. **Native venv + systemd** — fewest moving parts, but not self-contained: OS Python upgrades break venvs.
2. **Docker with a restart policy** — familiar. But it has no hang detection and no host-side pin reset, an `apt upgrade` of Docker stops the running brew, and Watchtower is archived.
3. **Docker supervised by a systemd unit** — gets the pin reset back, but has edge cases (CLI client vs. container, daemon restarts), and Docker advises against it.
4. **Podman + Quadlet, running OCI images built from the same Dockerfile** — systemd-native supervision, pin reset, hang detection, about 2 MB overhead, no daemon.
5. **balenaOS** — the closest fit to the console idea, but it needs a vendor cloud (rejected: local only).

## Decision

**Application (this repository):**

| Concern | Choice |
|---|---|
| Language/runtime | Python ≥ 3.11 (container: Debian Trixie's Python 3.13); `uv` for dependency management and builds on developer machines |
| Web/real-time | *Superseded by ADR-0002 (REST + server-sent events).* Starlette + uvicorn; plain WebSocket with a `{topic, payload}` JSON envelope on the single port (`IF-001..005`); client reconnect with backoff |
| Validation | `fastjsonschema` against the schemas in `docs/specification/data/` |
| GPIO | Own HAL on **libgpiod v2** (`gpiod` module). It finds the header chip by label (`pinctrl-bcm2835` / `pinctrl-bcm2711` / `pinctrl-rp1`, configurable) and requests the relay outputs in the off state with pull-up bias. No gpiozero, no lgpio. |
| Sensor | DS18B20 via 1-Wire sysfs in a background thread, cached (`HW-030`) |
| Front end | Vite + TypeScript + Preact, uPlot for the chart; built assets are served by the back end, all local (`UI-070`) |
| Tests | pytest (+ pytest-asyncio), mock HAL and a controllable monotonic clock (`NFR-060`); Vitest for the front end |
| Lint/types | ruff, mypy (back end); `tsc --noEmit` (front end) |

**Delivery:** the application is published as an **OCI container image**.
- Built from a Dockerfile (`Containerfile`) on `debian:trixie-slim` + `python3-libgpiod`.
- Built for `linux/arm64`, plus `linux/amd64` for simulation on developer machines.
- Signed with a pinned **cosign v2.x** key and pushed to the **private** GitHub Container Registry `ghcr.io/tinkerius/brewberrypi`.

**Runtime:** on the Pi the image runs under **Podman + Quadlet** on a read-only **BrewberryPi OS** image. The OS image, Quadlet unit, update service and safe mode live in the separate repository **`tinkerius/brewberrypi-os`**, which has its own ADRs. What the image expects from the host is fixed in the [runtime contract](../deployment/runtime-contract.md).

## Consequences

- **Positive:**
  - The image is self-contained and independent of OS updates.
  - Versions are picked from the registry.
  - The host resets the pins after every stop, systemd detects hangs, and a non-booting version falls back to the previous one (implemented in `brewberrypi-os`).
  - Developer machines run `--dummymode` natively (`uv run`) or as the amd64 image.
- **Negative / risks:**
  - **64-bit only**: the BrewberryPi OS image builder (rpi-image-gen) supports arm64 only, so the Pi 3 runs a 64-bit OS (see `Q-20`).
  - Signing must stay on **cosign v2.x**, or produce the legacy `sha256-<digest>.sig` signature tag, because Podman 5.4 cannot read cosign v3's default format. CI must verify each image against the device's `policy.json`.
  - The app must cooperate with the supervisor. It sends `READY=1` after startup (`NFR-021`), sends watchdog pings from the control loop, and switches outputs off in the Starlette lifespan shutdown, not after `uvicorn.run()`.
  - The unauthenticated web UI on the LAN is reachable from other web pages in the same LAN (cross-site WebSocket). See `Q-17`.
  - Not yet verified on hardware:
    - Whether the internal pull-up stays effective after the kernel releases a line.
    - Whether libgpiod accepts the pull-up bias on an output line.
    - The relay state during the first seconds after power-on (`Q-18`).
- **Follow-ups:**
  - M0: project skeleton, Containerfile, CI (build, test, sign, push).
  - M2/M9: early hardware spike for the libgpiod HAL.
  - M10: implement the runtime contract on the app side.
  - Spec questions `Q-16`–`Q-20`.
  - `brewberrypi-os` ADR-0001 (OS image, partitions, overlay, update service).

## Amendments

- **2026-10-11 — Styling: Tailwind CSS v4.** The UI is styled with Tailwind CSS v4 through its official Vite plugin, with no UI component library. The CSS is generated at build time, so it adds no runtime dependency, and everything stays local (`UI-070`). React-based component libraries were rejected: shadcn/ui would need React instead of Preact, and MUI/Chakra would only run through `preact/compat` and add 100 KB or more. The look replaces the legacy Bootstrap 3 look, which `09-user-interface.md` §9.1 allows as a visual refresh.
