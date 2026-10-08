---
name: spec-question
description: Record an open question about the specification instead of guessing. Use whenever the specification is ambiguous, contradictory or seems wrong.
argument-hint: "<question>"
---

# Record a specification question

Question: $ARGUMENTS

1. Read `docs/specification/13-open-questions.md` and check whether the question is already covered.
2. Find the affected requirement IDs in `docs/specification/`.
3. Append a row with the next free `Q-nn`: the question, the current default (what the
   implementation does until it is answered) and the affected IDs.
4. If the user answers right away: update the affected specification sections, mark the
   question as answered (keep the row; add the answer and the date), and add a line to
   `docs/recovery/bug-and-deviation-log.md` if the answer changes legacy behaviour.
