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
correct them. Ask in small batches, confirm, make decisions providing user options and grounding recommendation.

Done when reached shared understanding on:
- purpose and core function; actors; external systems
- scale: users, data volume, request and event rates, expected growth
- dominant qualities: availability, latency, consistency, security and compliance, cost
- hosting and deployment
- hard constraints and tech stack preferences

Then design per the `sa` skill against these drivers.

## 2b. Brownfield: describe the code as it is

Explore with evidence: build and deploy files, imports, routes and API
specs, clients and configured URLs, migrations and ORM mappings, topics, security config and deploy
flags, status enums, architecture tests. Large repo: fan out `Explore` agents by territory.

Record what the code has, including what you'd question, and raise that as a finding (step 4).

Ask the user only what the code can't tell and you need to know; if they don't know either, record
it as an open question (step 4) rather than a guess.

Done when every production source directory belongs to a component.

## 2c. Reconcile

Diff the code against `architecture.yaml` and go through each difference with the user:
- **finding** (step 4): the code should change later;
- **architecture change**, only on the user's yes: not applied here. Offer `feat` for it, one per
  group of related changes; its Doc impact carries the `architecture.yaml` and `README.md` edits, the
  ADR, and a check for any new `must` rule;
- **open question** (step 4): the user has no clear opinion yet.

## 3. Intent

Structure shows what exists, not what is meant. Collect what a competent reader would still get
wrong — deliberate oddities, false boundaries, hidden reasons — and check it against the code. What
must keep holding becomes a rule, the rest a note. Point README References to existing convention files.

## 4. Findings

`validate.py` reports the mechanical ones; add what reading the code against the `sa` lenses
reveals. Write them and the open questions to a new `.craft/findings/arch-<YYYYMMDD>-<N>.md`
([template](reference/findings-template.md)); don't consult or update older findings files. This
skill fixes `architecture.yaml`, not the code.

## 5. Write `architecture.yaml`

Every line passes one test: would a reader otherwise reconstruct it from code, and can a check catch
it drifting? Detail follows risk: data, contracts and security in detail, stable parts coarse.
Relations are an allowlist, so list them completely. Paths stay relative to the repo root; the
schema stays in this skill.

## 6. `README.md`, `AGENTS.md`, `CLAUDE.md`

`README.md` is the digest every agent loads: current decided state, at most 100 lines, one line per
fact, from [reference/readme-template.md](reference/readme-template.md). Its sections come first; an
existing README keeps its wording and other sections. On a rerun, fix only what is wrong. Long prose
moves to topic files (`CONTRIBUTING.md`, `docs/<topic>.md`), reasons to ADRs — after the user confirms.

`AGENTS.md` starts with `@README.md`; `CLAUDE.md` contains `@AGENTS.md`. Create them with just
that line; in existing ones add only the line.

## 7. Verify and confirm

1. `uv run --quiet <this-skill-dir>/scripts/validate.py .craft/architecture.yaml` exits 0; fix or
   explain warnings.
2. Run the `sa` Verify checklist.
3. Walk the user through the draft and findings; apply their changes and re-validate.

Done when the validator passes, the user approved `architecture.yaml`, and README matches it.

## View

```bash
uv run --quiet <this-skill-dir>/scripts/arch2html.py [.craft/architecture.yaml]
```

Renders `architecture.yaml`, ADRs and validator findings to `<tmp>/craft-views/arch-<system>.html` and opens it. Flags: `--no-open`, `--out <file>`. Display only: a new kind of finding goes in `validate.py`; a `Diagram error` is a bug in `arch2html.py`.

## Report

A few lines: files written, counts of findings and questions, `feat`s offered, next step `guard`.
