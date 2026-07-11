---
status: draft   # draft (still shaping) | ready (claimable) | in-progress | blocked | done — build owns the last three
updated: YYYY-MM-DD
target: <components / area this touches>
---

# <Title>

## Review Brief

*Terse summary for fast human-review.*

- **Goal:** What to be done and why, in a line.
- **Approach:** the solution approach in a sentence.
- **Diagram:** a flow/sequence/component sketch a reviewer can grasp at a glance (ASCII <120 chars or Mermaid). Include for any non-trivial change.
- **Key decisions and tradeoffs:** summary, details are below.
- **Impact:** components / data / API touched.
- **Risks:** main risk and what's explicitly not done.

## Goal

*What this delivers, the expected behavior, the motivation and value.*

### Constraints & assumptions  *[as appropriate]*

*Hard constraints (tech, performance, compliance) and the assumptions the solution rests on.*

### Non-goals  *[as appropriate]*

*What this explicitly does not do, and briefly why. Deferred ideas go to `docs/ideas/` on build.*

## Solution

### Description

*Describe the solution approach.*

### Parallelization *[if applicable]*

*When the plan contains independent pieces of work, list which parts can be implemented concurrently so the implementor can parallelize execution. Note any ordering dependencies between them.*

### Architecture  *[diagram expected for non-trivial changes]*

*The detailed diagram(s): components, boundaries, interactions, data flow, sequence, or state — whatever the change needs. Use ASCII (<120 chars wide) or Mermaid for more complex diagrams. The Review Brief's at-a-glance sketch is the entry point; this is where depth lives.*

### Key decisions & rejected approaches *[if any]*

*Brief ~ one line per decision. Rejected approaches should answer WHY?*

### Architectural changes *[if any]*

*Significant architecural changes that need to be remembered.*

At implementation, write each as `docs/adr/YYYY-MM-DD-<slug>.md`:

```markdown
---
updated: YYYY-MM-DD
target: <component>
---

# Short title

**Decision:** one sentence — what we chose.
**Why:** one or two sentences — why it beat the alternative (and what was rejected).
```

### Affected components & files

*Not an exhaustive set: the build may discover more. Group by component; tree layout.*

- **<component>**
  - `<path>` — <briefly: changes>

### API contracts *[as appropriate]*

*Affected/new endpoints.*

### Data model & migrations *[as appropriate]*

*Affected/new entities / schema changes (DDL or type shapes) / required migrations. Note the source of truth / owner when an entity is new or its ownership shifts.*

### State & lifecycle  *[as appropriate]*

*State sets and transitions, who owns each transition, and lifecycle rules (creation, validity, expiry, deletion) — when the change introduces or alters them.*

### UI changes  *[as appropriate]*

*Screens, components, routing/state. Visual tokens defer to `DESIGN.md`.*

### Error handling  *[as appropriate]*

*Failure modes and how they're handled — validation, retries, fallbacks, user-facing messages.*

### Testing approach

*What to test and at which layer, and how (tools, mocks, fixtures).*

*For a refactor: define green safety net that locks current behavior before any code moves.*

### Open questions that block implementation *[if any]*

*Anything that should be resolved before building.*

## Verification

### Acceptance criteria

*Append the checklist below to enforce additional criteria of Done for the implementing agent.*

- [ ] Tests written and passing green
- [ ] Code is buildable and runnable without errors
- [ ] `simplify` or similar skill invoked: no duplications, no dead code, no unjustified complexity
- [ ] `code-review` and `security-review` (or similar) agents spawned and finished, without pointing to any major issues
- [ ] Code is consistent with `ARCHITECTURE.md`
- [ ] Memory updated: inlined *Architectural changes* transcribed to `docs/adr/`; deferred ideas to `docs/ideas/`; `README.md` and `ARCHITECTURE.md` updated to stay in sync if required
- [ ] Item flipped to `status: done`, `updated` bumped, and moved to `docs/done/` (with same-basename images) — the final act, only once every box above holds
- [ ] Changes committed with proper message
