# Implementation Plan (phase 2)

Technology-neutral milestone plan. Each milestone ends with its acceptance
criteria green. Tick the boxes as milestones are completed.

| # | Milestone | Spec | Done when | Status |
|---|---|---|---|---|
| M0 | **Technology decision** — fill in ADR-0001, set up the project skeleton, build, test runner, linter, CI-less local scripts | ADR-0001, NFR-063 | ADR accepted; project skeleton (source + test folders per the chosen stack's conventions) builds and runs an empty test suite; CLAUDE.md commands updated | ☐ |
| M1 | **Configuration & recipe loading** — config file + schema validation + defaults; recipe file + validation | NFR-020, NFR-030, RCP-001..005, 07 | AC-080, AC-081, AC-082 | ☐ |
| M2 | **HAL interface + mock HAL + controllable clock** | HW-001..003, NFR-060 | Unit tests can drive time and temperature | ☐ |
| M3 | **Temperature controller & progress** | 05 | AC-001..007 | ☐ |
| M4 | **Goals & operator requests** (incl. reminder loop) | 02, 04, DOM-033 | AC-050..057 | ☐ |
| M5 | **Engine lifecycle & execution loop** | 03 | AC-030..039 | ☐ |
| M6 | **Simulation HAL** (physics, beeps, time scale) + `--dummymode` | HW-060..064 | AC-090 (accelerated) | ☐ |
| M7 | **Real-time interface** (broadcasts, commands, replies, chart thinning) | 08 | AC-070..074 | ☐ |
| M8 | **Web UI** | 09 | AC-075..077, manual UI check against 09 §9.1 | ☐ |
| M9 | **Raspberry Pi HAL** (GPIO, duty cycle, DS18B20, buzzer, safety) | 06, CTL-040..046 | AC-010..012, AC-020..023, AC-083 on real hardware | ☐ |
| M10 | **Startup/shutdown, logging, service installation** | NFR-001..005, NFR-020..024, NFR-040 | Service file, install guide, crash-safe outputs verified | ☐ |
| M11 | **Auxiliary tools** | 12 | TOOL-001..003 run on the Pi | ☐ |
| M12 | **End-to-end** — full recipe in simulation, one real water-only brew on hardware | 11 §11.8 | AC-090, AC-091, hardware test protocol signed off | ☐ |

Suggested order is top to bottom; M6 can run in parallel to M7/M8, M9 needs hardware.

## Working rules

- Every commit / PR references requirement IDs (e.g. `ENG-012, AC-033`).
- Tests are named after acceptance criteria where possible (`AC-033 start twice is rejected`).
- Spec changes go through `docs/specification/13-open-questions.md` → product-owner answer → spec edit → then code.
