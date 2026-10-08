# BrewberryPi

Raspberry Pi controller for a home-brewing mash kettle: heater and pump relays,
a DS18B20 temperature sensor and a buzzer, driven by recipes (ordered brewing
steps) and operated through a live web UI. This repository is a rebuild; the
behaviour is fully specified in `docs/specification/`.

## Project status

- Phase 1 (done): technology-neutral functional specification.
- Phase 2 (current): choose the technology stack (`docs/adr/0001-technology-stack.md`, status *Proposed*), then implement milestone by milestone (`docs/implementation-plan.md`).
- No application code exists yet. Do not write any before ADR-0001 is *Accepted* — start with `/choose-stack`.

## Layout

- `docs/specification/` — the specification (`00-index.md` first). Requirement IDs like `ENG-012`, acceptance criteria like `AC-033`.
- `docs/specification/data/` — normative reference data: `recipes.json`, `config.example.json`, JSON schemas for recipes, config and messages.
- `docs/recovery/bug-and-deviation-log.md` — `[FIX-nn]` entries: legacy defects the spec deliberately fixes.
- `docs/adr/` — architecture decision records (copy `0000-template.md`).
- `docs/implementation-plan.md` — milestones M0–M12 and their acceptance criteria.
- Source and test folders: created in milestone M0 following the conventions of the chosen stack.

## Commands

<!-- Fill in during milestone M0, after ADR-0001 is accepted. -->
- Build: _tbd_
- Test: _tbd_
- Run in simulation: _tbd_ `--dummymode`
- Run on the Raspberry Pi: _tbd_

## Rules

- The specification is the single source of truth. If it is ambiguous or seems wrong, do not guess: ask, or record it with `/spec-question`.
- Safety first — this controls a mains-powered heater. Heater off on every path that is not actively controlling temperature, all outputs off before anything else at startup, heater off when the temperature reading is invalid (`docs/specification/10-non-functional-requirements.md` §10.1). Never weaken this, not even in tests or simulation.
- Never re-introduce a defect listed in `docs/recovery/bug-and-deviation-log.md`.
- User-visible texts (goal names, descriptions, request and reply messages) must match the specification verbatim, including legacy spellings, until question `Q-07` is decided.
- Every acceptance criterion gets an automated test named after its ID (e.g. `AC-033 start twice is rejected`). Unit tests use the mock HAL and a controllable clock — no real sleeps.
- GPIO pin numbers are BCM numbers.
- Commit messages reference the requirement or AC IDs they implement.
