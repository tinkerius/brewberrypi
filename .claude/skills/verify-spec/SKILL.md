---
name: verify-spec
description: Check the implementation against the specification's requirements, acceptance criteria and FIX entries, and report coverage gaps. Read-only.
argument-hint: "[requirement prefix, e.g. ENG, CTL, HW — empty for all]"
---

# Verify the implementation against the specification

Scope: `$ARGUMENTS` (a requirement prefix; empty means everything).

1. Collect all requirement IDs (`XXX-nnn`) and acceptance criteria (`AC-nnn`) in scope from `docs/specification/`.
2. For each one, find the implementing code and its tests, and classify it as
   **covered and tested**, **implemented but untested**, **missing** or **deviates**.
3. Check every `[FIX-nn]` in scope from `docs/recovery/bug-and-deviation-log.md`: the legacy defect must not be present.
4. Check the safety rules in `docs/specification/10-non-functional-requirements.md` §10.1 explicitly.
5. Run the test suite and include the result.
6. Report a table sorted by severity: safety, missing, deviates, untested. Do not change code unless the user asks.
