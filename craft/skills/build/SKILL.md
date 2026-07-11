---
name: build
description: Implement the build-ready work items in `docs/ready/`. Picks the next unclaimed item, implements it, runs a review pass, verifies acceptance, and archives it to docs/done/.
---

Autonomously turn ready work items into shipped, verified changes. Each item in `docs/ready/` is self-contained by design (`spec` and `task` wrote it to execute from cold), so build is execution against a clear brief — not a design session. If an item is ambiguous enough to need decisions, it wasn't ready; stop and send it back to `spec`.

## The queue model

`docs/ready/` is the execution queue: `feat-NNN`, `task-NNN`, and promoted `idea-NNN` items, each carrying a goal and acceptance criteria. The **folder** is the coarse state (ready vs archived); a `status:` field distinguishes claimed from unclaimed so parallel runs don't collide:

- `status: ready` — unclaimed, up for grabs.
- `status: in-progress` — a run has claimed it (see Claim).
- `status: blocked` — a run failed it; carries a one-line reason. Won't be re-picked until a human clears it.
- `status: done` — verified; lives in `docs/done/`.

## Invocation

- `/build` — the next single item, then stop.
- `/build <file>` — a specific item.
- `/build all` — loop through the queue until it's empty or an item fails.

## Process

### 1. Pick
Read the queue: unclaimed items are `status: ready`. Order by `priority: high` first, then ascending number. Skip `in-progress` (unless the owner is stale — see Claim) and `blocked`.

### 2. Claim — before touching any code
Stamp the item `status: in-progress`, `owner: <this session/agent id>`, `started: <ISO ts>` and save it. This is the lock: it's why two executors (or a human and an agent) can work the same queue without both grabbing one item, and why a crashed run is visible rather than silently lost. If an item is already `in-progress` but its owner is clearly gone (process ended, timestamp long stale), reclaim it — overwrite owner/started and continue.

### 3. Build
Implement the item following `ARCHITECTURE.md` conventions and the item's own approach/acceptance. For a substantial `feat`, prefer dispatching a subagent to do the implementation so this executor's context stays clean and it can keep driving the queue; a small `task` is fine inline. The item is the brief — don't re-litigate its decisions.

### 4. Review pass
Before verifying, run a review/simplify pass (the `code-review` and `simplify` skills, or equivalents) and fold in the safe fixes — no duplications, no dead code, no unjustified complexity. Catching this now, in the same context that wrote the code, is cheaper than a later cleanup round.

### 5. Verify — the done gate
The item carries its own acceptance criteria — they're the contract, and meeting them is the only gate. Judge honestly against what the item asked for; don't wave it through. (Criteria always bottom out in: builds, runs, lint clean, tests green, behavior observable — the item may add more.)

### 6. Close
- **Pass:** set `status: done`, bump `updated`, `git mv` the item and any same-basename images (`<item>-*.png`) into `docs/done/`. Commit with a message naming the item. Transcribe any inlined architectural decisions to `docs/adr/`; keep `README.md`/`ARCHITECTURE.md` in sync if the change touched them.
- **Fail:** set `status: blocked` with a one-line reason, leave the item in `docs/ready/`, and stop (`/build all` halts here too — don't skip past a failure silently). Report what blocked it.

### 7. Report
Per item: one line — shipped / blocked and why. For `/build all`, end with a queue summary (N shipped, what's left, any blocked).

## Notes

- **Ready means ready.** If building reveals the item needs a design decision, a new boundary, or spans more than it claimed, stop and recommend re-running `spec` — don't improvise architecture from the executor seat.
- Numbers and names never change across folders — a `feat-007` stays `feat-007` in `done/`. Only `status:` and location move.
