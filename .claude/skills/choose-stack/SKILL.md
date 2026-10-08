---
name: choose-stack
description: Prepare and record the phase-2 technology decision (ADR-0001) together with the user. Use at the start of phase 2, before any application code exists.
disable-model-invocation: true
---

# Choose the technology stack (ADR-0001)

1. Read `docs/adr/0001-technology-stack.md`, `docs/specification/00-index.md`,
   `docs/specification/08-client-server-interface.md`,
   `docs/specification/10-non-functional-requirements.md` and
   `docs/recovery/legacy-technology-notes.md`.
2. Ask the user about constraints the specification does not cover (target Raspberry Pi
   model(s), languages the maintainers know, preference for few dependencies, …) —
   at most four questions.
3. Compare two or three realistic stacks: back end, GPIO library (must support Raspberry Pi 5
   via libgpiod/gpiochip), real-time browser transport, front end, charting, test framework,
   packaging as a system service. Evaluate them against the requirements listed in ADR-0001
   and give a clear recommendation.
4. When the user has decided, complete ADR-0001 (status *Accepted*, date, options, decision,
   consequences) and replace the `_tbd_` entries in the "Commands" section of `CLAUDE.md`
   with the commands that milestone M0 will create.
5. Do not write application code in this skill; the project skeleton is milestone M0
   (`/implement-milestone M0`).
