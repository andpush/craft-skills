# ADR format

An ADR records a decision that is expensive to reverse, written only after the user's explicit yes.
One screen. `docs/adr/YYYY-MM-DD-<slug>.md`; the date comes from the filename.

```markdown
---
supersedes: 2026-03-05-sync-notify     # optional — the only field
---
# Notify through a transactional outbox

## Context
What forces the decision, in a few lines. Link the spec or rule ID, don't restate it.

## Decision
What we do, in one or two sentences.

## Rejected
- Kafka — ops cost for a single consumer; revisit if a second consumer appears
- Sync call to notify — a mail outage would fail checkout

## Consequences
What gets easier, what gets harder, what to watch.
```

- **The title is the decision**, not the topic: "Notify through a transactional outbox", not "Notifications".
- **Status is derived.** An ADR is current unless a later one names it in `supersedes`. Never edit an
  old ADR's decision — supersede it.
- **Rejected** bullets: `option — why; revisit if <condition>`. The condition is what lets a rejected
  option come back; without it, say "no revisit".
- **No other fields.** Owners, status, tags and reviewers rot; git has the author and the date.
- Before proposing an option, grep `docs/adr/` for it under `## Rejected`. If it's there, say so and
  check its "revisit if" before proposing it again.
- `view model` draws ADRs as a timeline: each decision a waypoint, rejected options as side branches,
  superseded ones struck through.
