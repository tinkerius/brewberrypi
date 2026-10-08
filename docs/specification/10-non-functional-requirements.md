# 10 — Non-Functional Requirements

## 10.1 Safety (highest priority — mains-powered heater)

- `NFR-001` **Heater off by default.** Every path that is not actively controlling temperature leaves the heater off: startup, pause, stop, unload, finish, errors in goal logic (`ENG-023`), invalid temperature (`HW-022`), shutdown (`HW-021`).
- `NFR-002` Relay outputs are driven to the off state **before** any other initialisation (`HW-020`).
- `NFR-003` `[NEW]` Abnormal termination (crash, kill -9): the deployment SHOULD ensure outputs return to off (e.g. service manager post-stop action that resets the GPIO lines, or a hardware watchdog). Legacy: GPIO lines kept their last state — a crash while heating left the heater **on**.
- `NFR-004` No command from any client can switch the heater on directly; heating is only controlled by goal logic.
- `NFR-005` All timing-critical logic (countdowns, duty cycle, staleness) uses a **monotonic clock**, not wall-clock time. `[FIX-25]` (A Raspberry Pi has no RTC; NTP synchronisation after boot makes the wall clock jump, which in legacy could shorten or extend rests.) Wall-clock time is used only for chart timestamps and logs.

## 10.2 Startup and shutdown

- `NFR-020` Command line:
  - `--dummymode` → simulation HAL (legacy flag name, keep).
  - `--config <path>` `[NEW]` → configuration file (default: `config.json` next to the application; if missing, built-in defaults = [data/config.example.json](data/config.example.json)).
- `NFR-021` Startup order `[FIX-21]` (legacy started the web server before the engine and services existed):
  1. read & validate configuration → fail fast with clear message;
  2. read & validate recipe file (`RCP-003`);
  3. initialise HAL (outputs off), start sensor loop, wait ≤ 2 s for first reading (`HW-034`);
  4. create engine (state `NoProcess`);
  5. start web server + real-time channel + broadcast loops;
  6. log `BrewberryPI ready for brewing :-)` and play **short beep**.
- `NFR-022` Graceful shutdown on SIGINT/SIGTERM: stop engine loop, `switchEverythingOff`, buzzer off, release GPIO, log `Shutting down BrewberryPi.`.
- `NFR-023` `[NEW]` The application SHOULD be installable as a system service that starts on boot and restarts on failure (legacy: manual start via `brewberrypi.sh` with `sudo`).
- `NFR-024` `[NEW]` The application SHOULD run as a non-root user with GPIO access rights (legacy ran as root via `sudo`).

## 10.3 Configuration

- `NFR-030` All tunable constants of this spec have a configuration key with the documented default ([data/config.schema.json](data/config.schema.json)). Unknown keys → warning; invalid values → refuse to start.
- `NFR-031` Configuration is read at startup only (no hot reload required).

## 10.4 Logging

- `NFR-040` Log to standard output with timestamp, level, component. Levels: `ERROR` (goal failures, broadcast failures), `WARN` (sensor read failures, rejected commands, invalid answers), `INFO` (lifecycle events: startup, commands received, process loaded/started/paused/stopped/finished, goal started/finished, heating power changes, pump changes), `DEBUG` (per-tick controller decisions, countdown remaining time, duty-cycle phases).
- `NFR-041` Log messages from legacy worth keeping (for operators familiar with the old system): `starting goal <name>`, `goal <name> finished`, `change heating status to <p>`, `reading DS18b20 sensor failed`.

## 10.5 Platform and performance

- `NFR-050` Target: Raspberry Pi running Raspberry Pi OS (Linux, 32- or 64-bit ARM). Must run on Raspberry Pi 3, 4 and 5 (Pi 5 uses a different GPIO chip — the GPIO access method must support it). Legacy ran on an early Pi with Java 7 (armhf).
- `NFR-051` Simulation mode MUST run on a developer PC (Linux, Windows, macOS) without GPIO hardware.
- `NFR-052` CPU usage in idle < 10 % on a Raspberry Pi 3; memory footprint suitable for 1 GB RAM.
- `NFR-053` UI latency: a state change on the server is visible in all connected browsers within **1 s**.
- `NFR-054` Supports at least **5** concurrently connected browsers.

## 10.6 Testability and maintainability

- `NFR-060` Engine, goals and controller are testable against a **mock HAL** with a **controllable clock** (no real sleeps in unit tests).
- `NFR-061` Every acceptance criterion in [11](11-acceptance-criteria.md) is covered by an automated test (unit, integration, or simulation-based).
- `NFR-062` Hardware-dependent code is isolated behind the HAL (`HW-001`).
- `NFR-063` Source code, build and tests are reproducible from a clean checkout with documented commands (README).
