---
name: task
description: Record a small, focused change as a ready-to-build brief in `.craft/ready/`: too concrete for `idea`, too small for `feat`.
---

Turn a small, concrete request into a brief an implementor executes from cold, without coming back to the user. The deliverable is the doc, not code. The *what* is roughly decided and the change is usually one component, with no architecture decisions.

## When to escalate to `feat`

If exploration reveals the task spans several components, forces an architecture decision (new boundary, data model change, source-of-truth shift, new dependency), changes a contract (schema, public API or event, a new writer or copy of data, a new external call), or carries real design risk — stop and recommend `feat` instead. Don't quietly grow a task doc into a spec; say so and let the user choose.

## Process

### 1. Frame & explore
Reflect the request back in one line. Locate the affected component and read the relevant code — enough to ground the task in real files and names, no more. Note what already exists that the implementor will touch or follow.

### 2. Confirm & close gaps
Ask only the unknowns the implementor would otherwise stop on, with a recommendation for each. State your understanding and get the nod before writing.

### 3. Write the doc
`.craft/ready/task-<YYYYMMDD>-<slug>.md`, with a name unique across `draft/`, `ready/` and `done/`. A brief, not a spec: one screen, and cut any section that adds nothing.

```markdown
---
created: YYYY-MM-DD
updated: YYYY-MM-DD
target: <component name from .craft/architecture.yaml>
# depends_on: [<item>]   # optional; built only after these are in .craft/done/
---

# <Task in one line>

**Goal:** what to do and why, in a sentence or two.

**Context:** the files/component to touch and any existing code, pattern, or convention to follow. Link, don't restate.

**Do:** the concrete change — bullet steps if it helps.

**Acceptance:** observable behavior, as commands. Tests carry the AC ID in their name; `verify` exiting 0 is implied.

| ID | Criterion | Command |
|---|---|---|
| AC1 | <behavior> | `<AC command form from README.md, filter AC1_>` |

**Doc impact:** the exact doc edits, if any — the only ones `build` may apply. Omit if none.

**Notes:** decisions resolved in this session and constraints the implementor must respect — one line each, the decision not the debate, so nothing has to be re-asked. Omit if none.
```

### 4. Report
One or two lines: file created, plus the next step — `build <item>` to have craft execute it (or `/goal <file>` / a subagent). If you recommended escalating to `feat`, say that instead.

## Lifecycle

Commit it to main; it's now in the queue. If it implements an idea, delete the idea in the same commit, after carrying over anything useful. Deleting a task is the user's call.
