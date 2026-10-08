---
name: implement-milestone
description: Implement one milestone from docs/implementation-plan.md test-first against its acceptance criteria.
argument-hint: "M<number>"
disable-model-invocation: true
---

# Implement milestone $ARGUMENTS

1. Check that `docs/adr/0001-technology-stack.md` is *Accepted*. If not, stop and suggest `/choose-stack`.
2. Look up milestone $ARGUMENTS in `docs/implementation-plan.md`. Read the specification
   sections and acceptance criteria it lists, and every `[FIX-nn]` entry they reference in
   `docs/recovery/bug-and-deviation-log.md`.
3. Make a short plan (files, tests). If something is ambiguous in a way that changes
   behaviour, ask the user or record it with `/spec-question` — do not guess.
4. Write the tests for the milestone's acceptance criteria first, named after their IDs,
   then the implementation. Follow the layout and conventions fixed in ADR-0001.
5. Build and run the full test suite; fix until green. Report any remaining failures honestly.
6. Tick the milestone in `docs/implementation-plan.md` only when all of its criteria pass.
7. Summarise what was built, which requirement and AC IDs are covered, and any open points.
