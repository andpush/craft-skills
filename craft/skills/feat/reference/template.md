---
status: draft   # draft (still shaping) | ready (claimable) — build3 owns blocked
created: YYYY-MM-DD
updated: YYYY-MM-DD
target: <component names from docs/architecture.yaml, comma-separated>
# priority: high   # optional; the queue takes high first, then by created
---

# <Title>

## Review Brief

*The decision surface a human approves from — the spec page shows it first.*

- **Goal:** what is done and why, in a line.
- **Approach:** the solution in a sentence.
- **Diagram:** a flow/sequence/component sketch a reviewer grasps at a glance (Mermaid, or ASCII <120 chars). For any non-trivial change.
- **Contract changes:** *[if any — one per item, nothing else nested here]*
  - C1 schema: `<what>` — <consequence: migration, compatibility, rollback>
  - C2 api: `<what>` — <consequence: who breaks, versioning>
- **Key decisions:** one line each; details below.
- **Impact:** components / data / API touched.
- **Risks:** the main risk, and what's explicitly not done.

*Contract kinds: `dependency` (new or upgraded), `schema`, `api`, `event`, `data-writer` (a new writer
of an entity), `data-copy` (a new copy of another owner's data), `external-call`, `config`.*

## Goal

*What this delivers, the expected behavior, the motivation and value.*

### Constraints & assumptions  *[as appropriate]*

### Non-goals  *[as appropriate]*

*What this explicitly does not do, and briefly why. Deferred ideas go to `docs/ideas/` at close.*

## Solution

### Description

*The solution approach.*

### Parallelization *[if applicable]*

*Independent pieces that can be built concurrently, and any ordering between them.*

### Architecture  *[diagram expected for non-trivial changes]*

*The detailed diagram(s) — only what the change needs: sequence with failures for an operation,
state for a lifecycle, ER with owners for data.*

### Key decisions & rejected approaches *[if any]*

*One line per decision; rejected approaches say why. Mark the ones that need an ADR —
`ADR: <slug>` — `build3` writes them at close in the format of `sa/reference/adr.md`.*

### Affected components & files

*Not exhaustive: the build may discover more. Group by component.*

- **<component>**
  - `<path>` — <briefly: changes>

### API contracts *[as appropriate]*

*Affected or new endpoints and events: shape, errors, compatibility.*

### Data model & migrations *[as appropriate]*

*Affected or new entities, schema changes (DDL or type shapes), owner for each new entity.*

### Migration plan *[for any schema or stored-format change]*

*Steps — expand → backfill → switch → contract — and which this change contains. Mixed-version
behavior. Roll-forward or rollback per step. See `sa/reference/migrations.md`.*

### State & lifecycle  *[as appropriate]*

*States and transitions, the owner and trigger of each.*

### UI changes  *[as appropriate]*

*Screens, components, routing/state. Visual tokens defer to `DESIGN.md`.*

### Error handling  *[as appropriate]*

*Failure modes and how they're handled — validation, retries, fallbacks, user-facing messages. For each
multi-step operation: if a step succeeds and the next fails or times out, what state is left, and
what does a retry with the same input do?*

### Testing approach

*What to test, at which layer, and how. Negative cases where they apply: another user's or tenant's
data, revoked rights, duplicates, reordering, concurrency, partial failure. For a refactor: the green
safety net that locks current behavior before code moves.*

### Doc impact *[if any]*

*The exact edits this change makes to `docs/PRODUCT.md`, `AGENTS.md` or
`docs/architecture.yaml` — the only doc edits `build3` may apply. "None" when none.*

- `docs/architecture.yaml`: <e.g. orders.uses += notify>

### Open questions *[if any]*

*Non-blocking ones only — a blocking question keeps the spec in `draft`.*

## Acceptance

*The implementor's stop condition. Each test carries the AC ID in its name (`AC2_retryIsIdempotent`);
the command selects exactly those tests and fails if it selects none. Use the AC command form from
`AGENTS.md`. Always implied: `verify` exits 0.*

| ID | Criterion | Command |
|---|---|---|
| AC1 | <observable behavior> | `<runner filter AC1_>` |
| AC2 | <behavior a test can't show> (manual) | — |
