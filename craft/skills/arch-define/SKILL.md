---
name: arch-define
description: Use to define a project's `docs/architecture.yaml` — the reference architecture and durable skeletal context for agents — designed with the user for a new project, derived from the code for an existing one, or reconciled when it has drifted.
---

`docs/architecture.yaml` is the project's architecture in one file, with three jobs:
- **Orientation:** an agent reads it first and knows the parts, their boundaries and where data lives without exploring.
- **Drift baseline:** relations are an allowlist, so anything the code does beyond them is degradation to fix or decide on.
- **Diagram source:** context, containers, modules, ER, lifecycles and sequences render from it.

The format is [reference/architecture.schema.json](reference/architecture.schema.json). Read it and
[reference/architecture.example.yaml](reference/architecture.example.yaml) before drafting.

## 1. Ground

- Read the product inputs: `docs/PRODUCT.md`, `README.md`, vision, requirements and PRDs under `docs/`,
  and `docs/ARCHITECTURE.md` and `docs/adr/` when present.
- With no product purpose anywhere, offer to run `prod` first: the model needs a purpose to design against.
- Pick the branch: no production code → **greenfield**; code → **brownfield**; `docs/architecture.yaml`
  already exists → **reconcile**.

## 2a. Greenfield: shared understanding, then design

Lead the discussion: state the assumptions you draw from the inputs and let the user confirm or
correct them. Ask in small batches, each question with a recommended answer; skip what the inputs
already answer.

Done when the user has confirmed a **drivers** summary of at most ten lines:
- purpose and core function; actors; external systems
- scale: users, data volume, request and event rates, expected growth
- dominant qualities: availability, latency, consistency, security and compliance, cost
- team size and ops capacity; hosting; preferred or mandated stack
- hard constraints: existing systems, budget, deadlines

Then design with the `sa` skill against the drivers. Each real fork (monolith vs services, shared vs
private store, sync vs async, build vs buy) goes to the user as options with a recommendation;
settled defaults go straight into the draft.

## 2b. Brownfield: model the code as it is

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

Record the relations the code actually has: the model is a true baseline, and `guard` freezes
existing violations. Then ask the user, in batches, only what code can't tell: actors, the purpose
of components and externals, endpoint consumers outside the repo, which flows are the main ones,
which lifecycles matter, which rules they intend.

Done when every production source directory belongs to a component and every relation in the
draft has evidence.

## 2c. Reconcile: compare the model with the code

Collect the same evidence as brownfield and diff it against the existing model. Each difference
gets one of three outcomes, chosen by the user: fix the code (park it with `idea`), fix a stale
model line, or record an explicit decision. The model keeps its intent; code that contradicts it is
a finding, never a silent edit.

## 3. Intent

Structure shows what exists, not what is meant. From the user, prose docs and code comments, collect
what a competent reader would still get wrong: deliberate oddities, false boundaries, effects wider
than they look, hidden reasons. Check each against the code; a contradiction is a finding. What must
keep holding becomes a rule, the rest a one- or two-sentence note. How-to-work content goes to
`AGENTS.md` or `README.md`.

## 4. Findings

`validate.py` reports the mechanical ones: cycles, several writers, open or over-exposed endpoints,
shared logins. Add what takes reading the code: gates missing on a sibling route, open paths that
cost money or touch personal data, chatty sync calls, externals without timeout or fallback,
at-least-once consumers without dedupe, retried non-idempotent calls, a `utils` module holding
business logic, and in greenfield parts that no driver demands.

Each finding: what, evidence (`file:line` or model line), consequence, direction. Suggest each one
as an `idea`; the user confirms, makes it a rule, or accepts it. This skill fixes the model, not the
code.

## 5. Write the model

`docs/architecture.yaml`. Paths inside it (`source_path`, `check`, `decisions`) stay relative to the repo root. The schema stays in this skill: don't copy it into the project
or reference it from the model.

Every line passes one test: would a reader otherwise reconstruct it from code, and can a check
catch it drifting?
- **Detail follows risk.** Data, contracts and boundaries in detail; stable or simple parts coarse.
- **Components** are deployables.
- **Modules** are only the code units with a structural or functional role: they provide distinct
  business value, hold API or SPI contracts, define entities, contain a lot of code, or have many
  dependencies in or out. Leave out the rest, however cleanly they are packaged. A module lists the
  endpoints it handles in `serves`.
- **Endpoints** are API surfaces. Each has `for`: the services and clients expected to consume it, as
  model ids, or a short name for consumers outside the model (`partner-apps`). Each also has `auth`:
  protocol and providers, or `none` when it is deliberately open. Schedule endpoints have neither:
  they are the component's own trigger.
- **Security:** `exposure` comes from the deploy config, not from `auth`. Routes that differ in
  `exposure`, `auth`, `identity` or `authz` are separate endpoints.
- **UI endpoints** have the same structure, for people and agents: `for` lists actors, and `protocol`
  is the real one (`http` for a web UI). Nothing `calls` them.
- **Relations** list everything allowed. A missing one becomes a violation later, so the list is
  complete. A relation a listed module has goes on that module, so the model shows who works with
  each store, queue and outside system. The component keeps only what applies to all its code or
  comes from code outside the listed modules. `uses` names only listed modules.
- **Entities:** keys and references at minimum; other fields where the location of data matters (money, personal data).
- **States:** only lifecycles where an illegal transition costs money or trust.
- **Flows:** one to three main success paths, with the reads and writes that matter: they show when
  data is saved.
- **Rules:** only what relations can't express. `must` blocks a merge, `should` needs a stated reason;
  `check` names a file that exists.
- **Tech:** names with major versions. **Glossary:** non-obvious terms only.

## 6. Verify and confirm

1. `uv run --quiet <this-skill-dir>/scripts/validate.py docs/architecture.yaml` exits 0. It checks the
   schema, every reference, flows against relations, states against entity fields, endpoint `for`
   against callers, `serves` against endpoints, what each note is `about`, and paths.
   Warnings need fixing or explaining; findings go to step 4.
2. Run the `sa` skill's Verify checklist against the model.
3. Walk the user through the draft: components and their jobs, data ownership, exposure, flows, rules,
   notes, findings, open questions. Apply their changes, then re-run step 1.

Done when the validator exits 0 and the user has approved the model.

Report in a few lines: the file written, findings and their outcomes, open questions, and the next
step — `guard`, to turn relations and rules into checks.
