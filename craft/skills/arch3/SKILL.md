---
name: arch3
description: Define a project's `architecture.yaml` — the reference architecture.
---
Establish durable engineering context:
- `.craft/architecture.yaml` - dense architecture definition
- `README.md` - short overview, links and rules; referenced from `AGENTS.md` and `CLAUDE.md`
- `.craft/adr/` - important architectural decisions

`architecture.yaml` has three jobs:
- **Orientation:** an agent reads it first and knows the parts, their boundaries and where data lives without exploring.
- **Drift detection:** code vs architecture. Over time accumulated changes may lead to architecture decay. `guard` detects where code goes beyond the agreed definition (e.g. new dependencies)
- **Diagram source:** render architectural diagrams from it.

The architecture can be:
- defined with the user for a new project,
- derived from the code for an existing one, or
- reconciled when it has drifted.

In addition, the skill presents the architecture visually, as an HTML page that is easy for a human to grasp ("show me the architecture").

**To only show the architecture,** skip the rest: see [View](#view).

Before drafting read:
- [YAML format](reference/architecture.schema.json)
- [Example](reference/architecture.example.yaml)

## 1. Ground

- Read `PRODUCT.md` and `.craft/adr/` when present, and anything the user points you to.
- With no `PRODUCT.md`, offer to run `prod` first: the architecture needs a purpose to design against.
- Pick the branch: no production code → **greenfield**; code → **brownfield**; `.craft/architecture.yaml`
  already exists → **reconcile**.

## 2a. Greenfield: shared understanding, then design

Lead the discussion: state the assumptions you draw from the inputs and let the user confirm or
correct them. Ask in small batches, confirm, make decisions providing user options and grounding recommendation.

Done when reached shared understanding on:
- purpose and core function; actors; external systems
- scale: users, data volume, request and event rates, expected growth
- dominant qualities: availability, latency, consistency, security and compliance, cost
- hosting and deployment
- hard constraints and tech stack preferences

Pay attention to data ownership, scaling, failure isolation, NFRs and risks that matter.
Design with the `sa` skill against the drivers. Each real fork (monolith vs services, shared vs
private store, sync vs async, build vs buy) goes to the user as options with a recommendation;
settled defaults go straight into the draft.

Document decisions with reasoning in ADRs, per `sa` rules, using the [ADR template](../sa/reference/adr.md).

## 2b. Brownfield: describe the code as it is

Explore with evidence. Large repo: fan out `Explore` agents by territory, each reporting the
dimensions below with `file:line`. Small repo: one pass yourself.

| Evidence | Fills |
|---|---|
| build files, Dockerfiles, deploy manifests, entry points | components, `type`, `source_path`, `tech` |
| packages, their size and the imports between them, contract and entity definitions | `modules`, `uses` |
| routes, OpenAPI/proto/GraphQL, schedulers | `endpoints`, and `serves` from the package of each handler |
| UI routes, CLI commands, agent tools | `ui_endpoints`, `serves` |
| HTTP/gRPC clients, SDKs, configured URLs | `calls`, `external`, endpoint `for` |
| migrations, ORM mappings, repositories — who writes which table | `datastores`, entities, `reads`, `writes` |
| topics, producers, listeners | `queues`, `produces`, `consumes` |
| security config, permission checks, deploy flags, service-to-service auth, DB logins | `auth`, `authz`, `exposure`, `identity`, `credential` |
| status enums and the code that changes them | `states` |
| architecture tests, lint configs | `rules` with `check` |

Record the relations the code actually has: `architecture.yaml` is a true baseline, and `guard` freezes
existing violations. Then ask the user, in batches, only what code can't tell: actors, the purpose
of components and externals, endpoint consumers outside the repo, which flows are the main ones,
which lifecycles matter, which rules they intend, and why the components are cut the way they
are. With no ADR for the cut yet, record that answer as one, on the user's yes.

Done when every production source directory belongs to a component and every relation in the
draft has evidence.

## 2c. Reconcile: compare `architecture.yaml` with the code

Collect the same evidence as brownfield and diff it against the existing `architecture.yaml`. Each difference
gets one of three outcomes, chosen by the user: fix the code (park it with `idea`), fix a stale
line in it, or record an explicit decision. `architecture.yaml` keeps its intent; code that contradicts it is
a finding, never a silent edit.

## 3. Intent

Structure shows what exists, not what is meant. From the user, prose docs and code comments, collect
what a competent reader would still get wrong: deliberate oddities, false boundaries, effects wider
than they look, hidden reasons. Check each against the code; a contradiction is a finding. What must
keep holding becomes a rule, the rest a one- or two-sentence note. How-to-work content goes to
`README.md`. Coding conventions: point to the project's existing convention files
from README References; write new ones only if project-specific, with the user.

## 4. Findings

`validate.py` reports the mechanical ones: cycles, several writers, open or over-exposed endpoints,
shared logins. Add what takes reading the code: gates missing on a sibling route, open paths that
cost money or touch personal data, chatty sync calls, externals without timeout or fallback,
at-least-once consumers without dedupe, retried non-idempotent calls, a `utils` module holding
business logic, and in greenfield parts that no driver demands.

Each finding: what, evidence (`file:line` or `architecture.yaml` line), consequence, direction. Suggest each one
as an `idea`; the user confirms, makes it a rule, or accepts it. This skill fixes `architecture.yaml`, not the
code.

## 5. Write `architecture.yaml`

`.craft/architecture.yaml`. Paths inside it (`source_path`, `check`, `decisions`) stay relative to the repo root. The schema stays in this skill: don't copy it into the project
or reference it from `architecture.yaml`.

Every line passes one test: would a reader otherwise reconstruct it from code, and can a check
catch it drifting?
- **Detail follows risk.** Data, contracts and boundaries in detail; stable or simple parts coarse.
- **Components** are deployables.
- **Modules** are only the code units with a structural or functional role: they provide distinct
  business value, hold API or SPI contracts, define entities, contain a lot of code, or have many
  dependencies in or out. Leave out the rest, however cleanly they are packaged. A module lists the
  endpoints it handles in `serves`.
- **Endpoints** are API surfaces. Each has `for`: the services and clients expected to consume it, as
  ids from this file, or a short name for consumers outside it (`partner-apps`). Each also has `auth`:
  protocol and providers, or `none` when it is deliberately open. Schedule endpoints have neither:
  they are the component's own trigger.
- **Security:** `exposure` comes from the deploy config, not from `auth`. Routes that differ in
  `exposure`, `auth`, `identity` or `authz` are separate endpoints.
- **UI endpoints** have the same structure, for people and agents: `for` lists actors, and `protocol`
  is the real one (`http` for a web UI). Nothing `calls` them.
- **Relations** list everything allowed. A missing one becomes a violation later, so the list is
  complete. A relation a listed module has goes on that module, so the file shows who works with
  each store (private ones too), queue and outside system. The component keeps only what applies to all its code or
  comes from code outside the listed modules. `uses` names only listed modules.
- **Entities:** keys and references at minimum; other fields where the location of data matters (money, personal data).
- **States:** only lifecycles where an illegal transition costs money or trust.
- **Flows:** one to three main success paths, with the reads and writes that matter: they show when
  data is saved.
- **Rules:** only what relations can't express. `must` blocks a merge, `should` needs a stated reason;
  `check` names a file that exists.
- **Tech:** names with major versions. **Glossary:** non-obvious terms only.

## 6. `README.md`, `AGENTS.md`, `CLAUDE.md`

`README.md` is the digest humans read and every agent loads, so it holds only the current, decided
state, tersely. Write it from [reference/readme-template.md](reference/readme-template.md): vision
from `PRODUCT.md`, the architecture digest from `architecture.yaml`, commands, prerequisites, and
References with a "read when" for each file that exists. At most 100 lines, one line per fact.

- These sections come first. An existing README keeps its wording and its other sections: add
  what's missing, adopting a section that already says the same thing.
- On a rerun or reconcile, don't rewrite for style. Fix only what is wrong: a contradiction with
  `architecture.yaml` or `PRODUCT.md`, a command or prerequisite that no longer works, a reference
  to a file that's gone or a missing one.
- An existing README that is long or holds prose (guides, rationale, history): extract it into
  files with speaking names (`CONTRIBUTING.md`, `docs/deployment.md`), reasons into ADRs, and link
  them from References. Propose the split; apply it after the user confirms.

`AGENTS.md` starts with the line `@README.md`, and `CLAUDE.md` contains `@AGENTS.md`, so every
agent loads README and through its References finds the rest. Create them with just that line;
in existing ones add only the line, and leave everything else as it is.

## 7. Verify and confirm

1. `uv run --quiet <this-skill-dir>/scripts/validate.py .craft/architecture.yaml` exits 0. It checks the
   schema, every reference, flows against relations, states against entity fields, endpoint `for`
   against callers, `serves` against endpoints, what each note is `about`, and paths.
   Warnings need fixing or explaining; findings go to step 4.
2. Run the `sa` skill's Verify checklist against `architecture.yaml`.
3. Walk the user through the draft: components and their jobs, data ownership, exposure, flows, rules,
   notes, findings, open questions. Apply their changes, then re-run step 1.

Done when the validator exits 0, the user has approved `architecture.yaml`, and the README digest
(step 6) matches it.

## View

```bash
uv run --quiet <this-skill-dir>/scripts/arch2html.py [.craft/architecture.yaml]
```

Renders `architecture.yaml`, ADRs and validator findings to `<tmp>/craft-views/arch-<system>.html` and opens it. Flags: `--no-open`, `--out <file>`. Display only: it decides nothing and has no findings of its own. A new kind of finding goes in `validate.py`. A `Diagram error` is a bug in `arch2html.py`.

## Report

In a few lines: the files written, findings and their outcomes, open questions, and the next
step — `guard`, to turn relations and rules into checks.
