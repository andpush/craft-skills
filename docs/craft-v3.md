# craft v3 — design contract

Status: agreed 2026-10-27. The contract every v3 skill relies on; change it first, then the skills.

## Goal

Same minimal flow `prod → arch → spec/task → build`, plus what v2 lacks: executable acceptance,
an independent review, a gate outside the agent's reach (branch + CI + PR), mechanically enforced
architecture rules, and visual review pages. Success = less context read, less human review effort,
fewer regressions, smaller change radius — not LOC, test or finding counts.

## Principles

- **Markdown is the source of truth.** HTML views are rendered by a script, never committed.
- **One fact, one place.** Link, don't restate. Stable IDs (`R3`, `AC2`, ADR slug, component name) tie docs to code and tests.
- **Intent is never silently rewritten to match code.** Drift → fix code, fix a stale doc, or an explicit decision.
- **One model feeds checks, diagrams and agents** — `architecture.yaml`.
- **Deterministic where possible:** checks, triggers, diagrams, views. AI writes the implementation and is verified separately.
- **Not checked ≠ passed.** Skipped, unsupported, or empty selection is a failure or an explicit "not checked".
- **Existing formats first** — markdown, ArchUnit, dependency-cruiser, OpenAPI. No custom DSL.
- **Depth matches risk.** Sections without content are omitted; small changes stay small.

## Skills

| Skill | v3 change |
|---|---|
| `prod` | budgets only |
| `arch` | writes `architecture.yaml` (context, components, entities, main flows, rules, triggers); `ARCHITECTURE.md` becomes prose + glossary; writes `AGENTS.md`; next step `guard` |
| `sa` | grep prior ADRs before proposing; ADR on explicit yes; lenses in `reference/` loaded by topic |
| `spec` | contract changes, AC as commands, doc impact, migration plan, opens spec view, emits `/goal` line |
| `task` | AC as commands; slug naming |
| `idea` | slug naming; also records removal of temporary flags/adapters |
| **`build3`** | branch claim → AC tests first → implement → verify → `review` → close in branch → PR/merge per policy |
| **`review`** (new) | risk triage + independent review → `<item>.review.json`; `review walk` guides the human |
| **`guard`** (new) | `verify` entrypoint, checks from the model and rules, baseline, CI workflow, branch protection |
| **`view`** (new) | script renders spec / change review / model to HTML in a temp dir and opens it |
| `audit` | + conformance, rule coverage, budgets, doc drift, churn × complexity hotspots |
| `whereami` | claims live in branches and PRs |

`build` and `code-reviewer` stay until `build3` / `review` prove themselves.

## Files

```
AGENTS.md              ≤60 lines, always loaded: product line, commands (incl. verify), invariants, merge policy, pointers
CLAUDE.md              @AGENTS.md
PRODUCT.md             ≤150 lines
ARCHITECTURE.md        ≤300 lines of prose; a component section moves to docs/modules/<name>.md when it outgrows that
architecture.yaml      the model: context, components, entities, main flows, rules, review triggers
docs/ideas/            <type>-<slug>.md            candidates
docs/ready/            <type>-<slug>.md            build-ready queue (on main = unclaimed)
docs/done/             <type>-<slug>.md + <type>-<slug>.review.json
docs/adr/              YYYY-MM-DD-<slug>.md
```

**Naming.** `<type>-<slug>.md`, type ∈ `idea | feat | task`; `created: YYYY-MM-DD` in frontmatter. The
slug is unique across all folders and never changes. Queue order: `priority: high` first, then
`created`. A split sequence uses `-a-`, `-b-` after the type. Same-basename files (images, review
JSON) move with the item.

## architecture.yaml — the model

Everything that checks, diagrams and review tooling read lives in one YAML file next to
`ARCHITECTURE.md`. `ARCHITECTURE.md` explains it in prose (why this decomposition, flows,
trade-offs, glossary) and links to it — it never restates it. `guard`'s checks read the file at
test time where the tool allows (ArchUnit/Konsist via a YAML library, dependency-cruiser's JS
config); where components are crates or SwiftPM targets, a check compares the manifest with the model. `view model` renders it.

```yaml
system: shop
does: sells catalog products online; one team, one deployable

external:                   # context: who and what sits outside
  customer: {does: browses and orders, calls: [api]}   # calls = inbound; drawn as an actor
  payments: {does: card authorization (Stripe)}        # reached through a component's depends_on

components:
  orders:
    does: order lifecycle, idempotent submission     # one line
    path: src/orders                                 # string or list of paths/globs
    depends_on: [catalog, shared, payments]          # allowed dependencies (components or externals); anything else is a violation

entities:                   # main ones only; fields live in code
  Order:
    owner: orders           # the only writer
    has: [OrderLine]        # same owner — one aggregate
    states:                 # only when the lifecycle matters
      - draft -> submitted: submit
      - submitted -> paid: payment authorized
  OrderLine:
    owner: orders
    refs: [Product]         # by id, may cross owners
    copies: [Product.price: snapshot — price at purchase]   # replica | projection | cache | snapshot

flows:                      # one or two main success paths
  submit order:
    - customer -> api: POST /orders
    - api -> orders: submit(cart, key)
    - orders ~> notify: OrderSubmitted      # ~> async; -> calls must follow depends_on

rules:                      # what the model can't express
  - id: R3
    level: MUST             # MUST | SHOULD
    scope: "src/*/domain"   # component name or path glob
    rule: no framework annotations
    checked_by: ArchitectureTest.R3   # or: manual  (manual rules go to review's checklist)
    exceptions: baseline              # optional: baseline | ADR slug

review_triggers:            # project paths that make a change red; built-in defaults cover manifests, migrations, OpenAPI, CI, auth
  schema: [db/migration/**, "**/*.sql"]
  api: [src/api/**, "**/openapi*.yaml"]
  dependency: [build.gradle.kts, "**/*.lock"]
```

Every section is optional and one line per thing. The test for adding anything: would a reader
otherwise have to reconstruct it from code, and can a check catch it drifting? Fields, endpoints
and secondary flows stay in code and tests.

- `guard` checks dependencies against code and derives I/O rules from the model, mapped to imports by
  the stack adapter: persistence only in entity owners, HTTP clients only in components that depend on
  an external, server/controller code only in components an external `calls`. Anything rarer (clock,
  filesystem, queues) is a rule line when a project cares.
- Rationale for a rule: one clause in `ARCHITECTURE.md` or an ADR link, by rule ID.
- `review_triggers` extend built-in defaults (dependency manifests, migrations, OpenAPI/proto/GraphQL,
  auth/security paths, CI config, arch-check files). `view` uses the `schema` and `api`/`event` ones to
  show data-model and API changes even when a review misses them.
- Validation (`view model`, `audit`): unknown names anywhere, components without a path, `has`
  across owners, flow calls not allowed by `depends_on` or `calls`, MUST rules without a checker.
- Arrow items (`a -> b: label`) need quotes only when the label contains `: `. Globs starting with `*` need quotes.

**Glossary** (in `ARCHITECTURE.md`): only terms that are non-obvious or mean different things in
different contexts.

## ADR

`docs/adr/YYYY-MM-DD-<slug>.md`, one screen, written only after the user's explicit yes. The title
is the decision ("Notify through a transactional outbox"). The date comes from the filename.

```markdown
---
supersedes: 2026-03-05-sync-notify     # optional — the only field
---
# Notify through a transactional outbox

## Context
## Decision
## Rejected
- Kafka — ops cost for a single consumer; revisit if a second consumer appears
## Consequences
```

Status is derived: an ADR is current unless a later one supersedes it. A rejected option comes back
only when its "revisit if" holds — `sa` greps `## Rejected` before proposing. `view model` draws the
ADRs as a timeline: each decision a waypoint, rejected options as side branches, superseded ones
struck through.

## Spec additions

- **Contract changes** (in the Review Brief): new/upgraded dependency, schema change, public
  API/event change, new data writer or copy, new external call — each with its consequence:
  migration, compatibility, versioning, rollback.
- **Migration plan** for any schema change: expand → backfill → switch → contract; mixed-version
  compatibility; roll-forward. See `sa/reference/migrations.md`.
- **Acceptance** as a table. Tests carry the AC ID in their name (`AC2_retryIsIdempotent`).

  | ID | Criterion | Command |
  |---|---|---|
  | AC1 | Duplicate submit creates one order | `./gradlew test --tests '*AC1_*'` |
  | AC2 | Admin screen shows status (manual) | — |

  Always implied: `verify` exits 0. Manual criteria are declared up front; green tests don't cover them.
- **Testing approach** prompts negative cases where relevant: another user's or tenant's resource,
  revoked rights, duplicates, reordering, concurrency, partial failure.
- **Doc impact:** the exact edits to `ARCHITECTURE.md` / `PRODUCT.md` / `AGENTS.md` this change makes.
  The only doc edits `build3` may apply.
- **Goal line:** `/goal Item docs/ready/<item>.md built per build3: verify exited 0 with output shown, review tier reported`.

## verify

One command, named in `AGENTS.md` (`./gradlew verify`, `make verify`, `pnpm verify` …). Runs build,
lint, tests, architecture checks. Non-zero on any failure, including when a test filter matches
nothing. Agent, human and CI all call the same command; CI never has its own checks.

## build3

1. **Pick** an item in `docs/ready/` with `status: ready` and no claim branch.
2. **Claim:** branch `craft/<item>`; push it right away when a remote exists. The branch is the lock.
3. **AC tests first** (feat/idea items; skipped for task): a subagent sees only the spec and
   writes the AC tests; they must fail; commit as `test: acceptance tests for <item>` — `review`
   finds that commit and flags later edits to its files.
4. **Implement** in a subagent. It must not edit the committed AC tests; if one looks wrong, stop and report.
5. **Simplify**, then **verify** (output in the transcript).
6. **Review:** `review` in a fresh context. Fix what has a clear fix (confirmed findings, failing ACs,
   deviations); contract decisions and plausible findings go to the human. A fresh reviewer checks the
   fix diff and marks findings `fixed`; at most two rounds.
7. **Close in the branch:** apply the doc impact, write agreed ADRs, file ideas for deferred work and
   temporary flags, set `status: done`, `git mv` item + same-basename files to `docs/done/`, commit.
8. **Integrate** per merge policy (merge main in, never rebase — the review's refs must stay
   reachable); open the change view; report tier and what needs the human.

**Fail** → commit `status: blocked` + one-line reason on the branch (draft PR when remote), stop.
Merging the PR lands code, docs and the item's move to `done/` in one step.

## review

Two halves. `review/scripts/review.py` is deterministic: triggers from the diff and the trigger
globs, a model diff between base and head (new edges, externals, owners, copies, weakened rules),
test weakening (deleted or skipped tests, edits to AC tests after their commit), doc edits outside
the doc impact, files outside the spec's target, the AC skeleton from the spec, and the tier. It
writes and rewrites `<item>.review.json`, keeping the reviewer's fields, and lists what is still
incomplete (a schema trigger with no schema contract, a confirmed finding without a test, an AC not
run, anything in `not_checked`).

The agent half, in a context that didn't write the code:
1. `/code-review` and `/security-review` (or equivalents on other hosts).
2. Own lenses: spec conformance → deviations; contracts with compat and migration (migrations read
   whole); undeclared edges and non-owner writes; blast radius (changed symbols → callers outside
   the diff → covering tests); negative cases; `manual` rules; change cost.
3. Counterexamples: each high/medium suspicion → the smallest failing test `H1_<behavior>`; fails →
   `confirmed`. On a `craft/` branch they are committed, so a red `verify` blocks the merge.
4. Evidence: every AC command run.

Finding = location → invariant → scenario → consequence → minimal fix. Zero findings is valid.
The reviewer never fixes code.

`review walk` — in the terminal, beside the change page: data model & API → deviations → other
contracts → confirmed findings → blast radius → plausible findings → manual ACs. Each item: clickable
`path:line`, what changed, the one question to check, a recommendation; verdict via a question
(`accept | change | discuss`) recorded in the JSON. Ends with merge per policy, or a fix list whose
fix diff is reviewed alone.

### Risk tiers

Computed by the script from triggers and the review's content; the agent never sets it.

| 🔴 red — walkthrough required | 🟡 yellow — skim the page | 🟢 green |
|---|---|---|
| any trigger glob (dependency, schema, api, event, security, ci, arch-check, project kinds); new external or external call; owner change or new data copy; rule removed or weakened; test deleted/skipped; AC test edited after its commit; doc edits outside doc impact; deviation; dependency/schema/api/event/data/external contract; confirmed high finding; failing AC | new component edge; other model changes; files outside the spec's target; other findings not accepted; blast radius with uncovered callers; AC not run; anything in `not_checked` | none of these |

### review.json

```json
{
  "item": "feat-offline-mode", "base": "<sha>", "head": "<sha>", "tier": "red",
  "triggers":    [{"tier": "red", "what": "dependency: build.gradle.kts +implementation(...)"}],
  "deviations":  [{"id": "D1", "what": "", "where": "path:line"}],
  "contracts":   [{"id": "C1", "kind": "dependency|schema|api|event|data-writer|data-copy|external-call|config", "what": "", "consequence": "",
                   "compat": "compatible|breaking|needs-migration|needs-versioning", "migration": "expand-only|backfill|contract|none", "where": ""}],
  "blast":       [{"id": "B1", "symbol": "", "change": "", "callers": ["path:line"], "covered_by": ["test"], "where": ""}],
  "findings":    [{"id": "H1", "severity": "high|medium|low", "status": "confirmed|plausible|fixed", "where": "path:10-24", "invariant": "", "scenario": "", "consequence": "", "fix": "", "test": ""}],
  "evidence":    [{"ac": "AC1", "criterion": "", "command": "", "result": "pass|fail|not-run|manual"}],
  "not_checked": [""],
  "verdicts":    {"H1": "accept"},
  "new_edges":   ["orders -> notify"]
}
```

The script owns `item`, `base`, `head`, `tier`, `triggers`, `new_edges`; the reviewer the rest.

## view

`view` holds one stdlib Python script and one HTML template. Markdown, mermaid and code
highlighting render in the browser from pinned CDN versions. Output goes to a temp dir and opens in
the browser — nothing in the repo. Pages:

- **Spec** — opened by `spec` before approval: Review Brief, component diagram from the model with
  the changed parts highlighted, contract-change cards, AC table, open questions.
- **Change** — opened by `build3`: tier; **data model & API first** (schema/API/event contracts with
  compatibility, full migration diffs, a warning when trigger paths changed but the review reported
  nothing); deviations, other contracts, findings, blast radius with the real `git diff` hunks inline;
  AC evidence; not-checked list.
- **Model** — context, decomposition, entities (by owner, with copies), lifecycles, main flows as
  sequences, and the ADR decision timeline; model problems on top; components, rules and triggers
  collapsed. Later: intended vs extracted dependencies with violations in red.

Diagram choice: one question per view — container for orientation, sequence (with failures) for an
operation, state for a lifecycle, ER + authority for data, trust boundaries for security. Only when
the spec touches that area.

Every item carries an ID (`C2`, `H3`); discussion happens in the terminal ("H3 — why not reuse X?").

## guard

One-time, idempotent; rerun after `arch` changes `architecture.yaml`.

1. Detect the stack; check `gh` is installed and the active account can push to the remote.
2. Create or fix `verify` (fails on empty test selection); record it in `AGENTS.md`.
3. Write the stack adapter that reads `architecture.yaml` (ArchUnit/Konsist for JVM,
   dependency-cruiser for TS, grimp for Python; manifest comparison for Rust/Swift). See
   `reference/stacks.md`.
4. A check per `MUST` rule the component map can't express, named by rule ID.
5. Existing violations → frozen baseline (ArchUnit `FreezingArchRule`, dependency-cruiser known-violations). No new violations.
6. Prove each check: introduce a violation, see red, revert.
7. CI workflow that only runs `verify`.
8. With the user's confirmation: branch protection requiring the CI check. Solo repos: no
   required approvals — GitHub doesn't let you approve your own PR.
9. Add project paths to `review_triggers` in `architecture.yaml` (the `verify` script, check config, baselines).

## Merge policy

In `AGENTS.md`: `Merge: pr | local` (default `pr` when a remote exists) and
`Auto-merge: off | green` (default `off`). 🟡/🔴 always wait for the human; 🟢 merges by itself only
with `Auto-merge: green` and CI green.

## sa lenses

`sa/reference/` — each ≤60 lines, loaded only when the change touches the topic:
`domain.md` (bounded contexts, aggregates from invariants, deep modules, no interface-per-class,
modular monolith default) · `data.md` (authority, copies, writers, snapshots, lineage) ·
`interactions.md` (API/async contracts, idempotency, accepted ≠ completed, outbox, ordering,
retries) · `migrations.md` (expand/contract, backfill, mixed versions, roll-forward, temporary
adapters with removal condition).

## Acceptance trial

A small Kotlin or TS fixture repo and one real feature, with three planted defects:
a forbidden dependency, an unauthorized writer, a consumer without dedupe.
Pass: `guard`/`verify` catch the first two mechanically; `review` produces a failing test for the
third. Compare with v2 on context read, clarification count, review effort, change radius.

## Order of work

1. `view`  2. `review`  3. `build3`  4. `guard` + `reference/stacks.md`
5. `arch`, `spec`, `sa` + lenses, `task`, `idea`, `whereami`, `audit`  6. trial, then cut what didn't pay off.
