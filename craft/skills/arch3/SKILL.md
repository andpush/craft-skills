---
name: arch3
description: Define, derive, reconcile or show the project architecture in `architecture.yaml`.
---
Establish durable engineering context:
- `.craft/architecture.yaml` - dense architecture definition
- `README.md` - short overview, links and rules; referenced from `AGENTS.md` and `CLAUDE.md`
- `.craft/adr/YYYY-MM-DD-*.md` - important architectural decisions

`architecture.yaml` has three jobs:
- **Orientation:** an agent reads it first and knows the parts, their boundaries and where data lives without exploring.
- **Drift detection:** code <=> architecture. Over time changes add up to architecture decay. `guard` detects where code goes beyond it (e.g. an undeclared dependency).
- **Diagram source:** render architectural diagrams from it.

**To only show the architecture** ("show me the architecture"), skip the rest: see [View](#view).



## 1. Ground

- Goals:
  - Read `PRODUCT.md` and `.craft/adr/` when present, and anything the user points you to.
  - With no `PRODUCT.md`, offer to run `prod` first: the architecture needs a purpose to design against.

- Mode:
  - `.craft/architecture.yaml` exists → **reconcile**
  - production code → **brownfield**
  - otherwise → **greenfield**

- Before drafting read:
  - [YAML format](reference/architecture.schema.json)
  - [Example](reference/architecture.example.yaml)

## 2a. Greenfield: shared understanding, then design

Lead the discussion: state the assumptions you draw from the inputs and let the user confirm or
correct them. Interview relentlessly, a few questions at a time, until no driver is a guess. For
each decision, give options and a grounded recommendation.

Reach shared understanding on:
- purpose and core functions; actors; external systems
- scale: users, data volume, request and event rates, expected growth
- NFRs: availability, latency, consistency, security and compliance, cost
- hosting and deployment
- hard constraints and tech stack preferences

Then design per the `sa` skill against these drivers.

## 2b. Brownfield: describe the code as it is

Explore with evidence: build and deploy files, imports, routes, migrations, config. Large repo: fan
out `Explore` agents by territory.

Record what the code has, including what you'd question, and raise that as a finding (step 3).

Ask the user only what the code can't tell and you need to know; if they don't know either, record
it as an open question (step 3) rather than a guess.

Done when every production source directory belongs to a component.

## 2c. Reconcile

Analyse the code against `architecture.yaml` and against itself; find contradictions. Go through
them with the user, grounding why each matters, and settle each one:
- **update the architecture**, on the user's yes: edit it in this session (step 4) with an ADR;
- **change the code:** offer a `feat` for related fixes, or record a finding (step 3);
- **open question** (step 3): the user has no clear opinion yet;
- **skip:** the difference doesn't matter.

## 3. Findings

Collect findings (problems, with a direction: fix the code, change the architecture, or options) and
open questions from step 2, plus what reading the code against the `sa` lenses
reveals. Write them to a new `.craft/findings/arch-<YYYYMMDD>-<N>.md` ([template](reference/findings-template.md)).

## 4. Write the architecture

Greenfield and brownfield write it whole; reconcile applies only what the user approved (2c).

`architecture.yaml`: every line passes one test: would a reader otherwise reconstruct it from code,
and can a check catch it drifting? Detail follows risk: data, contracts and security in detail,
stable parts coarse. Relations are an allowlist, so list them completely.

`README.md` is the digest every agent loads, per [reference/readme-template.md](reference/readme-template.md).
An existing README keeps its wording and other sections; on a rerun, fix only what is wrong. Move
long prose and reasons out only after the user confirms.

`AGENTS.md` starts with `@README.md`; `CLAUDE.md` contains `@AGENTS.md`. Create them with just
that line; in existing ones add only the line.

## 5. Verify and confirm

1. `uv run --quiet <this-skill-dir>/scripts/validate.py .craft/architecture.yaml` exits 0; fix or
   explain warnings. In reconcile, only if `architecture.yaml` changed.
2. Run the `sa` Verify checklist.
3. Walk the user through the draft and findings; apply their changes and re-validate.

Done when the validator passes, the user approved `architecture.yaml`, and README matches it.

## View

```bash
uv run --quiet <this-skill-dir>/scripts/arch2html.py [.craft/architecture.yaml]
```

Renders `architecture.yaml`, ADRs and validator findings to `<tmp>/craft-views/arch-<system>.html` and opens it. Flags: `--no-open`, `--out <file>`.

## Report

A few lines: files written, counts of findings and questions, `feat`s offered, next step `guard`.
