---
name: spec
description: Use to build any non-trivial changes to the software — a feature, service, API, data model, schema, behavior change, or refactoring — to analyse user intent, discover requirements, brainstorm and plan the approach.
---

Turn an intent into a self-contained, build-ready solution spec through collaborative dialogue. The spec is a handoff for a build agent, so it must be clear and concrete enough to execute from cold, without further clarifications or design decisions.

During this collaborative session: understand context -> refine intent -> discover hidden decisions and surface tradeoffs -> define the approach -> define acceptance criteria, confirm readiness for delegated build.

The spec is the deliverable, not code: don't implement during a spec session — it ends only at a spec the user has confirmed.

Once it's ready, the implementation is a delegated execution — via `build` (craft's executor), `/goal`, a dispatched subagent, or any agent.

## Context gates — detect, don't dead-end

`spec` builds on `PRODUCT.md` and `ARCHITECTURE.md`.

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
- Read `PRODUCT.md`, `ARCHITECTURE.md`.
- Peek into dir tree, recent commit log, `docs/ideas/` and `docs/adr/` listings if warranted.
- Explore additional context and zoom in as needed.

### 2. Frame the problem

In touch with user, turn vague requests into concrete goals. Grasp the problem, not just gather requirements. If the request is a proposed solution, establish the motivation. Verify risky assumptions. Challenge contradictions and gaps. Push for clarity on the core value and the acceptance criteria.

If the request originates as an idea (picked from `docs/ideas/` or a fresh hunch), validate it before specing: does it serve `PRODUCT.md`, is it worth doing now? Recommend a verdict — **pursue**, **defer**, or **reject** — rejection is a legitimate outcome, not a failure. Record the verdict in the idea file (see Ideas below). On **pursue** you elaborate the idea itself into the build-ready item — it keeps its `idea-NNN-slug.md` name and moves into the queue; you don't mint a new `feat-`.

If the request spans several independent subsystems, or assumes too many changes, confirm if the user wants to split it and suggest options.

### 3. Design the solution

Design the approach per the `sa` skill ([../sa/SKILL.md](../sa/SKILL.md)): start simple, options on substantial forks with a recommendation, expensive-to-reverse decisions surfaced while they're cheap to change.

As new information arises, iterate between the solution and the problem framing — they shape each other. Involve the user at each fork; refer to the codebase when context is required. Follow defined rules and conventions.

### 4. Write the spec

- Use template [reference/spec-template.md](reference/spec-template.md).
- Lead with the **Review Brief**: the scannable decision surface a human approves from. Keep execution detail below it, and only where it's needed.
- Be concrete, avoid prose, duplications, restatements of `PRODUCT.md`/`ARCHITECTURE.md` - link instead.
- YAGNI: Focus on the core value, and defer non-essential ideas to `docs/ideas/`.
- If the change path crosses code smells (oversized file, tangled responsibilities, unclear boundaries), fold targeted fixes into the spec — improve what you touch. Don't propose unrelated refactoring.
- Flag architectural impact when the feature forces a system-level change: new component, boundary shift, data model change, or new dependency.
- Define a feature-relevant testing approach following the testing pyramid. For UI changes, consider e2e using playwright-cli skill or similar. Gate refactoring with TDD: establish a green safety net before restructuring.
- Acceptance criteria are the implementation agent's stop condition. Minimum: code builds and runs, no lint errors, tests green, behavior change observable. Add criteria where needed to pin down intent.

### 5. Present and confirm

Don't just dump a spec with the details buried in it; present the chosen solution clearly in a way easy to grasp for a human:
- Lead the presentation with the diagram — it's the fastest way for a human to grasp and steer the solution.
- Highlight components affected by the planned changes.
- Obtain confirmation that the spec captures the intent and is ready to build. If not, iterate.

### 6. Emit the spec

Write the item into the execution queue `docs/ready/` using [reference/spec-template.md](reference/spec-template.md):
- A fresh feature → `feat-NNN-slug.md`, where `NNN` is the next free number across all work items (`idea-`/`feat-`/`task-` in `docs/ideas/`, `docs/ready/`, `docs/done/`), zero-padded; `slug` = kebab feature name.
- A pursued idea → keep its `idea-NNN-slug.md` name (and carry its images); elaborate it in place to build-ready and move it (`git mv` when tracked) from `docs/ideas/` into `docs/ready/`.

If one item splits into an ordered sequence, append a letter to the slug: `feat-NNN-a-slug.md`, `feat-NNN-b-slug.md`, … Numbers and names never change afterwards — only `status:` and folder move as `build` executes.


## Ideas

`docs/ideas/` holds candidates, not commitments — filenames are the index; open a file only on pickup. The validation judgment lives in *Frame the problem*; the bookkeeping it triggers — `verdict:`/`status:` fields and the pursued/deferred/rejected file moves — is owned by the `idea` skill ([../idea/SKILL.md](../idea/SKILL.md)), so follow its Lifecycle section rather than duplicating it here. Don't open a spec for an unvalidated idea; deleting idea files is the user's call, never yours.


## Quality checklist

Self-review the spec with fresh eyes before declaring it ready:
- [ ] The spec is minimal but sufficient to implement from cold (on empty context)
- [ ] The acceptance criteria is verifiable
- [ ] Testing approach is defined
- [ ] No contradictions between sections (e.g. scope vs. acceptance criteria)
- [ ] No requirement that reads two ways

## When done

- if no open blockers — set `status: ready` (the item is now claimable from the queue) and commit; otherwise `status: draft` and leave it out of the queue's live set until resolved.
- report it's ready to execute and give the one-line next step: `/build` to have craft execute it (or `/goal <file>` / a subagent brief). A few lines, no narrative.

Execution and archival are owned by `build`: it claims the item (`in-progress`), implements, verifies, and on success flips it to `status: done` and moves it — with any same-basename images — into `docs/done/` (name unchanged). You don't archive here.
