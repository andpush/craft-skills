---
name: feat
description: Use to plan a feature, service, refactoring, or any other non-trivial change: clarify intent, discover requirements, design the approach, and hand off a spec for autonomous build.
---

Turn an intent, through dialogue, into a spec the user has confirmed and an agent can build from cold, with no further questions or design decisions. The spec is the deliverable, not code.

## Context gates

`PRODUCT.md` or `.craft/architecture.yaml` missing or placeholder-only → offer to run `prod`/`arch` now, or stop so the user runs `init`.

## Match the depth to the problem

Scale the session to the request. A focused, low-risk change earns a couple of sentences and a single confirmation; a nuanced or risky one earns real exploration — alternatives, trade-offs, a sketch.

## Lead the conversation

Proactively involve the user and drive the discovery: you get precious information, they gain direction and can steer. Value the user's time: be terse, pragmatic, ask only what affects the solution, no Q&A theatre.

- You're the tech lead, the user the domain expert.
- Reflect the problem back, then ask the sharpest unknown; the user corrects rather than writing it from scratch.
- One thread at a time, top-down: confirm the common ground, then the details.
- Challenge shaky assumptions and contradictions, offer the simpler path, and raise what wasn't asked, each with your recommendation.

## Process

### 1. Explore the context

- Read the `notes` in `.craft/architecture.yaml` about what the change touches. Before proposing an option, grep the ADRs' `## Rejected` for it.
- A change that adds a component, affects a contract or a persisted entity: check that the code it touches complies with `architecture.yaml`. If it doesn't, stop and offer `arch` reconcile, so the spec doesn't build on a stale baseline.

### 2. Frame the problem

Turn the request into concrete goals: if it's a solution, find the motivation; pin the core value and the acceptance criteria.

If the request originates as an idea (picked from `.craft/draft/` or a fresh hunch), validate it before writing the spec: does it serve `PRODUCT.md`, is it worth doing now? Recommend **implement**, **postpone**, or **reject** — rejection is a legitimate outcome, not a failure. Record the outcome per the `idea` skill's Lifecycle.

If the request spans several independent subsystems, or assumes too many changes, confirm if the user wants to split it and suggest options.

### 3. Design the solution

Design the approach per the `sa` skill ([../sa/SKILL.md](../sa/SKILL.md)). As new information arises, iterate between the solution and the problem framing; they shape each other.

### 4. Write the spec

- Use [reference/template.md](reference/template.md); name it `feat-<YYYYMMDD>-<slug>.md`, unique across `.craft/draft/`, `ready/` and `done/`. Names never change; only the folder does. An item that needs another built first lists it in `depends_on:`.
- Lead with the **Review Brief**, the surface a human approves from; execution detail below, only where needed.
- Be concrete; link to `PRODUCT.md` and `.craft/architecture.yaml` instead of restating them.
- YAGNI: focus on the core value. Capture deferred work as an idea only when the user agrees to; don't pile them up.
- Where the change path crosses code smells, fold targeted fixes in; no unrelated refactoring.
- **Contract changes** outlive the code: the human reviews them first.
- A new component, relation, entity, wider exposure or rule, or a change to what `README.md` states, goes in **Doc impact** as an exact edit; `build` applies only those.
- **Acceptance:** `build` has the AC tests written first by an agent that sees only the spec, so each criterion must be testable from the spec alone.

### 5. Present and confirm

- Write the item to `.craft/draft/` and open the spec page — Review Brief first, the component diagram with the targets highlighted, contract changes as cards, the AC table:
  ```bash
  uv run --quiet <this-skill-dir>/scripts/spec2html.py .craft/draft/<item>.md
  ```
- In the terminal, lead with what needs the human: open questions, contract changes, anything the page flags. Every item has an ID (`C1`, `AC3`) to discuss by.
- Obtain confirmation that the spec captures the intent and is ready to build. If not, iterate and re-render.

## Quality checklist

Self-review the spec with fresh eyes before declaring it ready:
- [ ] The spec is minimal but sufficient to implement on empty context
- [ ] Every AC has a command, or is marked manual
- [ ] Every contract change states its consequence; every schema change has a migration plan
- [ ] Doc impact is exact, or "None"
- [ ] No contradictions between sections (e.g. scope vs. acceptance criteria)
- [ ] No requirement that reads two ways

## When done

- if no open blockers — move the item and its images to `.craft/ready/` (it's now claimable from the queue), delete the idea it implements if any, and commit to main; otherwise it stays in `.craft/draft/` until resolved.
- report it's ready to execute and give the next step: `build <item>`, or the goal line for a `/goal` run:
  `/goal Item .craft/ready/<item>.md built per build: verify exited 0 with output shown, review tier reported`

`build` archives it; you don't.
