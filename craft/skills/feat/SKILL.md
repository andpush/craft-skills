---
name: feat
description: Use to plan a feature, service, refactoring, or any other non-trivial change: clarify intent, discover requirements, design the approach, and hand off a spec for autonomous build.
---

Turn an intent, through dialogue with the user, into a build-ready spec: concrete enough for an agent to execute from cold, with no further questions or design decisions.

The spec is the deliverable, not code: don't implement here; the session ends at a spec the user has confirmed.

## Context gates — detect, don't dead-end

`feat` builds on `PRODUCT.md` and `.craft/architecture.yaml`.

If either is missing or placeholder-only — offer a fork:
- **Establish now** — run `prod`/`arch` skills in this session, then continue the spec.
- **Defer** — name what's missing and why it matters, then stop so the user runs `/init` separately.

## Core Principles

### Match the depth to the problem

Scale the session to the request. A focused, low-risk change earns a couple of sentences and a single confirmation; a nuanced or risky one earns real exploration — alternatives, trade-offs, a sketch.

### Lead the conversation

Proactively involve user, drive the discovery: doing so you get precious information, they gain direction and can steer.

Speak as a professional collaborator: you are tech lead, user is domain expert. You guide to reach consensus and shape the best solution.

Be terse, pragmatic, ask only what affects the solution, no Q&A theatre. That means fewer, sharper exchanges, not skipping the dialogue to write faster. Follow this pattern:
- Open by reflecting the problem back in your own words, then ask the sharpest unknown. Make the user react and correct, not author from scratch.
- Pursue one thread before opening the next. A dialogue beats a questionnaire. Top-down: Start each topic with summary that validates shared common ground, then move to details. Each answer should sharpen your next question.
- Challenge. Name the assumption you think is shaky, the contradiction you spotted, the simpler path they may not have considered — and say what you'd do and why. Bring a recommendation to every fork; make the user approve or override, not decide in a vacuum.
- Surface the non-obvious. Part of your value is raising what the user didn't think to ask — edge cases, failure modes, cheap-now/expensive-later decisions.
- Earn the right to write. Summarize and write back to ensure you got it right, and get the nod before writing.

## Process

### 1. Explore the context
Understand the ground you're building on:
- Read `PRODUCT.md` and `.craft/architecture.yaml`, including its `notes` about what the change touches.
- Peek into dir tree, recent commit log, `.craft/draft/` and `.craft/adr/` listings if warranted. Before proposing an option, grep the ADRs' `## Rejected` for it.
- Explore additional context and zoom in as needed.
- A change that adds a component, affects a contract or a persisted entity: check that the code it touches complies with `architecture.yaml`. If it doesn't, stop and offer `arch` reconcile, so the spec doesn't build on a stale baseline.

### 2. Frame the problem

In touch with user, turn vague requests into concrete goals. Grasp the problem, not just gather requirements. If the request is a proposed solution, establish the motivation. Verify risky assumptions. Challenge contradictions and gaps. Push for clarity on the core value and the acceptance criteria.

If the request originates as an idea (picked from `.craft/draft/` or a fresh hunch), validate it before writing the spec: does it serve `PRODUCT.md`, is it worth doing now? Recommend **implement**, **postpone**, or **reject** — rejection is a legitimate outcome, not a failure. See Ideas below for what each one does.

If the request spans several independent subsystems, or assumes too many changes, confirm if the user wants to split it and suggest options.

### 3. Design the solution

Design the approach per the `sa` skill ([../sa/SKILL.md](../sa/SKILL.md)). As new information arises, iterate between the solution and the problem framing; they shape each other.

### 4. Write the spec

- Use [reference/template.md](reference/template.md); name it `feat-<YYYYMMDD>-<slug>.md`, unique across `.craft/draft/`, `ready/` and `done/`. Names never change; only the folder does. An item that needs another built first lists it in `depends_on:`.
- Lead with the **Review Brief**, the surface a human approves from; execution detail below, only where needed.
- Be concrete; link to `PRODUCT.md` and `.craft/architecture.yaml` instead of restating them.
- YAGNI: focus on the core value; defer the rest to `.craft/draft/`.
- Where the change path crosses code smells, fold targeted fixes in; no unrelated refactoring.
- **Contract changes** outlive the code, so the human reviews them first; check each against the `sa` lenses and challenge questions.
- A new component, relation, entity, wider exposure or rule, or a change to what `README.md` states, goes in **Doc impact** as an exact edit; `build` applies only those.
- **Acceptance:** `build` has the AC tests written first by an agent that sees only the spec, so each criterion must be testable from the spec alone.

### 5. Present and confirm

Don't just dump a spec with the details buried in it; present the chosen solution clearly in a way easy to grasp for a human:
- Write the item to `.craft/draft/` and open the spec page — Review Brief first, the component diagram with the targets highlighted, contract changes as cards, the AC table:
  ```bash
  uv run --quiet <this-skill-dir>/scripts/spec2html.py .craft/draft/<item>.md
  ```
- In the terminal, lead with what needs the human: open questions, contract changes, anything the page flags. Every item has an ID (`C1`, `AC3`) to discuss by.
- Obtain confirmation that the spec captures the intent and is ready to build. If not, iterate and re-render.

## Ideas

`idea-*` files in `.craft/draft/` are candidates, not commitments — filenames are the index; open a file only on pickup. The validation judgment lives in *Frame the problem*; the bookkeeping it triggers — the `resolution:` field and the file moves — is owned by the `idea` skill ([../idea/SKILL.md](../idea/SKILL.md)), so follow its Lifecycle section rather than duplicating it here. Don't open a spec for an unvalidated idea.


## Quality checklist

Self-review the spec with fresh eyes before declaring it ready:
- [ ] The spec is minimal but sufficient to implement from cold (on empty context)
- [ ] Every AC has a command, or is marked manual
- [ ] Every contract change states its consequence; every schema change has a migration plan
- [ ] Doc impact is exact, or "None"
- [ ] Testing approach is defined
- [ ] No contradictions between sections (e.g. scope vs. acceptance criteria)
- [ ] No requirement that reads two ways

## When done

- if no open blockers — move the item and its images to `.craft/ready/` (it's now claimable from the queue), delete the idea it implements if any, and commit to main; otherwise it stays in `.craft/draft/` until resolved.
- report it's ready to execute and give the next step: `build <item>`, or the goal line for a `/goal` run:
  `/goal Item .craft/ready/<item>.md built per build: verify exited 0 with output shown, review tier reported`
  A few lines, no narrative.

Execution and archival are owned by `build`: it claims the item with a `craft/<item>` branch, builds and reviews it there, and moves it — with its same-basename files — into `.craft/done/` in the same branch. You don't archive here.
