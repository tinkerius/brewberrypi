# ADR-0001: Technology Stack for the BrewberryPi Rebuild

- **Status:** Proposed — **to be decided at the start of phase 2** (with the product owner)
- **Date:** –
- **Deciders:** –

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

Background: [docs/recovery/legacy-technology-notes.md](../recovery/legacy-technology-notes.md) §3 lists candidates.

## Options considered

_To be filled in phase 2._

## Decision

_To be filled in phase 2._

## Consequences

_To be filled in phase 2. Update the "Commands" section of `CLAUDE.md` and the "Development" section of `README.md` after acceptance._
