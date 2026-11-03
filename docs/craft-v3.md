# craft v3 — design contract

Status: updated 2026-11-03. The contract every v3 skill relies on; change it first, then the skills. No migration: there are almost no existing projects, so old formats aren't supported.

## Goal

Avoid architecture (security, maintenance, reliability) degradation over long agentic evolution, where an agent keeps adding features and fixes. On top of the minimal flow `prod → arch → spec/task → build`: executable acceptance, an independent review, a gate outside the agent's reach (branch + CI + PR), mechanically enforced architecture, and visual review pages.

Success = less context read, less human review effort, fewer regressions, smaller change radius — not LOC, test or finding counts.

## Principles

- **Markdown and YAML are the source of truth.** HTML pages are rendered by a script, never committed.
- **One fact, one place.** Link, don't restate. Stable IDs (rule id, `AC2`, ADR slug, component name) tie docs to code and tests.
- **Intent is never silently rewritten to match code.** Drift → fix code, fix a stale line, or an explicit decision.
- **One model feeds checks, pages and agents** — `docs/architecture.yaml`.
- **Deterministic where possible:** checks, triggers, diagrams, pages. AI writes the implementation and is verified separately.
- **Not checked ≠ passed.** Skipped, unsupported, or empty selection is a failure or an explicit "not checked".
- **Depth matches risk.** Sections without content are omitted; small changes stay small.
- **Anything stored must be something a check can catch drifting.** Derive rather than store.

## Who does what

Each skill answers one question.

| Skill | Question | Sees | Output | Decides? |
|---|---|---|---|---|
| `prod` | What are we building and why? | The user | `docs/PRODUCT.md` | Yes, with the user |
| `arch3` | What is our architecture, and is it sound? | Whole system: PRD, user, code | The model, `AGENTS.md`, findings, a page | **Yes, with the user** |
| `guard` | How do we stop it degrading? | The model and stack | `verify`, checks, CI; set up once | No, it enforces |
| `spec` / `task` | What will this change do? | One intent | A work item | Yes, with the user |
| `build3` | Build it | One item | A branch, then a PR or merge | No, it follows the item |
| `review` | What did this change actually do? | One diff | Risk tier, findings, a page | No, it flags for the human |
| `audit` | What's the state of the whole repo? | Whole repo | Findings | No, it reports |

Three rules keep these from overlapping:

1. **One detector.** Mechanical findings live only in `arch3/scripts/validate.py`. Everything else calls it.
2. **Judgement has two owners.** `arch3` looks at the whole system, `review` at one change. Findings that take reading code belong only to these two.
3. **One place to decide.** A finding is fixed, made a rule or accepted only in `arch3`. Its page shows it, `verify` blocks new ones, `review` flags them.

A finding's life: `validate.py` or `arch3` finds it → the user decides in `arch3` → fixed or frozen in the gate file → `verify` blocks anything new → `review` shows it to a human.

**Semantic drift:** `verify` only catches what's mechanical. `spec` runs `arch3` reconcile when a change adds a component or a contract, and `audit` runs it periodically.

Also: `sa` designs for `arch3` and `spec`, `idea` captures candidates, `whereami` reads claims from branches and PRs. `arch`, `build` and `code-reviewer` stay until `arch3`, `build3` and `review` prove themselves; `arch` is kept for reading only.

## Files

```
AGENTS.md                   ≤60 lines, always loaded: commands (incl. verify), invariants, merge policy, pointers
CLAUDE.md                   @AGENTS.md
docs/PRODUCT.md             ≤150 lines
docs/architecture.yaml      the model
docs/architecture.gate.json generated: what verify enforces, flattened from the model
docs/architecture.baseline  frozen code violations, one per line
docs/ideas/                 <type>-<slug>.md   candidates
docs/ready/                 <type>-<slug>.md   build-ready queue (on main = unclaimed)
docs/done/                  <type>-<slug>.md + <type>-<slug>.review.json
docs/adr/                   YYYY-MM-DD-<slug>.md
```

**Naming.** `<type>-<slug>.md`, type ∈ `idea | feat | task`; `created: YYYY-MM-DD` in frontmatter. The slug is unique across all folders and never changes. Queue order: `priority: high` first, then `created`. A split sequence uses `-a-`, `-b-` after the type. Same-basename files (images, review JSON) move with the item.

## The model

Format: `arch3/reference/architecture.schema.json`, example beside it. It holds components, modules, relations (`uses`, `calls`, `reads`, `writes`, `produces`, `consumes`), endpoints with `auth`, security (`exposure`, `identity`, `authz`, `credential`), data, `states`, `flows`, `rules`, `notes`, `glossary` and `review_triggers`.

Every line passes one test: would a reader otherwise reconstruct it from code, and can a check catch it drifting? Relations are an allowlist. Intent the structure can't show goes in `notes` or `rules`; how-to-work goes in `AGENTS.md`.

`validate.py` checks the schema, references, flows against relations, and paths. Its findings are **deficiencies** (cycles, several writers, open internet endpoints that reach other systems, shared logins) and **improvements** (unused endpoints, over-exposure, `must` rules without a check).

## ADR

`docs/adr/YYYY-MM-DD-<slug>.md`, one screen, written only after the user's explicit yes. The title is the decision ("Notify through a transactional outbox"). The date comes from the filename.

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

Status is derived: an ADR is current unless a later one supersedes it. A rejected option comes back only when its "revisit if" holds — `sa` greps `## Rejected` before proposing. The `arch3` page draws ADRs as a timeline.

## Spec additions

- **Contract changes** (in the Review Brief): new/upgraded dependency, schema change, public API/event change, new data writer or copy, new external call — each with its consequence: migration, compatibility, versioning, rollback.
- **Migration plan** for any schema change: expand → backfill → switch → contract; mixed-version compatibility; roll-forward. See `sa/reference/migrations.md`.
- **Acceptance** as a table. Tests carry the AC ID in their name (`AC2_retryIsIdempotent`).

  | ID | Criterion | Command |
  |---|---|---|
  | AC1 | Duplicate submit creates one order | `./gradlew test --tests '*AC1_*'` |
  | AC2 | Admin screen shows status (manual) | — |

  Always implied: `verify` exits 0. Manual criteria are declared up front; green tests don't cover them.
- **Testing approach** prompts negative cases where relevant: another user's or tenant's resource, revoked rights, duplicates, reordering, concurrency, partial failure.
- **Doc impact:** the exact edits to `docs/PRODUCT.md`, `AGENTS.md` and `docs/architecture.yaml` this change makes. The only doc edits `build3` may apply.
- **Goal line:** `/goal Item docs/ready/<item>.md built per build3: verify exited 0 with output shown, review tier reported`.

## verify

One command, named in `AGENTS.md`. Runs build, lint, tests, architecture checks. Non-zero on any failure, including when a test filter matches nothing. Agent, human and CI all call the same command; CI never has its own checks.

## guard

One-time, idempotent; rerun after the model changes.

1. Detect the stack; check `gh` is installed and the active account can push.
2. Create or fix `verify`; record it in `AGENTS.md`.
3. `validate.py --gate` writes the gate file. It refuses new deficiencies without `--accept`, which only the user decides on; fixed ones drop out.
4. One stack test reads the gate file and fails on: a stale gate (model hash), imports a unit doesn't allow, I/O of a kind missing from its unit, unowned code. Violations are stable lines; existing ones go in the baseline, and fixed lines must leave it. See `guard/reference/stacks.md`.
5. A check per `must` rule the above doesn't cover, plus one test comparing the gate file's `surface` with the real deploy config.
6. Prove each check: introduce a violation, see red, revert.
7. CI workflow that only runs `verify`.
8. With the user's confirmation: branch protection requiring it. Solo repos: no required approvals.
9. Add the `verify` wiring and deploy/auth config to `review_triggers`.

## build3

1. **Pick** an item in `docs/ready/` with `status: ready` and no claim branch.
2. **Claim:** branch `craft/<item>`; push it right away when a remote exists. The branch is the lock.
3. **AC tests first** (feat/idea items; skipped for task): a subagent sees only the spec and writes the AC tests; they must fail; commit as `test: acceptance tests for <item>` — `review` finds that commit and flags later edits to its files.
4. **Implement** in a subagent. It must not edit the committed AC tests; if one looks wrong, stop and report.
5. **Simplify**, then **verify** (output in the transcript).
6. **Review:** `review` in a fresh context. Fix what has a clear fix (confirmed findings, failing ACs, deviations); contract decisions and plausible findings go to the human. A fresh reviewer checks the fix diff and marks findings `fixed`; at most two rounds.
7. **Close in the branch:** apply the doc impact and re-run `validate.py --gate` if the model changed (a refused deficiency stops the build for the user), write agreed ADRs, file ideas for deferred work and temporary flags, set `status: done`, `git mv` item + same-basename files to `docs/done/`, commit.
8. **Integrate** per merge policy (merge main in, never rebase — the review's refs must stay reachable); open the change page; report tier and what needs the human.

**Fail** → commit `status: blocked` + one-line reason on the branch (draft PR when remote), stop. Merging the PR lands code, docs and the item's move to `done/` in one step.

## review

Two halves. `review/scripts/review.py` is deterministic: triggers from the diff and the trigger globs; a model diff between base and head (exposure, auth, identity, shared logins, new data access, removed notes, weakened rules); new deficiencies, recomputed so a hand-edited gate file can't hide them; test weakening (deleted or skipped tests, edits to AC tests after their commit); doc edits outside the doc impact; files outside the spec's target; the AC skeleton from the spec; and the tier. It writes and rewrites `<item>.review.json`, keeping the reviewer's fields, and lists what is still incomplete.

The agent half, in a context that didn't write the code:
1. `/code-review` and `/security-review` (or equivalents on other hosts).
2. Own lenses: spec conformance → deviations; contracts with compat and migration (migrations read whole); undeclared relations; blast radius (changed symbols → callers outside the diff → covering tests); negative cases; rules without a check; change cost.
3. Counterexamples: each high/medium suspicion → the smallest failing test `H1_<behavior>`; fails → `confirmed`. On a `craft/` branch they are committed, so a red `verify` blocks the merge.
4. Evidence: every AC command run.

Finding = location → invariant → scenario → consequence → minimal fix. Zero findings is valid. The reviewer never fixes code.

`review walk` — in the terminal, beside the change page: data model & API → deviations → other contracts → confirmed findings → blast radius → plausible findings → manual ACs. Each item: clickable `path:line`, what changed, the one question to check, a recommendation; verdict via a question (`accept | change | discuss`) recorded in the JSON. Ends with merge per policy, or a fix list whose fix diff is reviewed alone.

### Risk tiers

Computed by the script from triggers and the review's content; the agent never sets it.

| 🔴 red — walkthrough required | 🟡 yellow — skim the page | 🟢 green |
|---|---|---|
| any trigger glob (dependency, schema, api, event, security, ci, arch-check, project kinds); new external or external call; new data writer or copy; wider exposure, anonymous access, lost authz, user identity reaching a new place, shared login; new deficiency; rule removed or weakened; test deleted/skipped; AC test edited after its commit; doc edits outside doc impact; deviation; dependency/schema/api/event/data/external contract; confirmed high finding; failing AC | new relation; other model changes; files outside the spec's target; other findings not accepted; blast radius with uncovered callers; AC not run; anything in `not_checked` | none of these |

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

## Pages

There is no separate view skill. A page belongs to the skill whose question it answers, and all pages share one way of working: Python renders finished HTML into one logic-free template, output goes to a temp dir and opens in the browser, nothing lands in the repo.

- **Architecture** (`arch3`): system map, notes, components, exposure, data, lifecycles, flows, rules, glossary, ADR timeline, and findings last. Display only.
- **Spec** (`spec/scripts/spec_page.py`): "is this the right plan?" Review Brief first, component diagram with the targets highlighted, contract-change cards, AC table, open questions.
- **Change** (`review/scripts/change_page.py`): "what changed, and is it risky?" Tier first; **data model & API next** (contracts with compatibility, full migration diffs, a warning when trigger paths changed but the review reported nothing); deviations, other contracts, findings, blast radius with the real `git diff` hunks inline; AC evidence; not-checked list.

`spec` and `review` reuse `page.py`, the template and a components-only map from `arch3/scripts`. Every item carries an ID (`C2`, `H3`); discussion happens in the terminal ("H3 — why not reuse X?").

## Merge policy

In `AGENTS.md`: `Merge: pr | local` (default `pr` when a remote exists) and `Auto-merge: off | green` (default `off`). 🟡/🔴 always wait for the human; 🟢 merges by itself only with `Auto-merge: green` and CI green.

## sa lenses

`sa/reference/` — each ≤60 lines, loaded only when the change touches the topic: `domain.md` (bounded contexts, aggregates from invariants, deep modules, no interface-per-class, modular monolith default) · `data.md` (authority, copies, writers, snapshots, lineage) · `interactions.md` (API/async contracts, idempotency, accepted ≠ completed, outbox, ordering, retries) · `migrations.md` (expand/contract, backfill, mixed versions, roll-forward, temporary adapters with removal condition).

## Status

**Proven.** On a Kotlin fixture (2026-10-28, run stopped halfway): `build3` and `review` wrote AC tests red first, and review proved a spec gap with a failing test, so a red change wasn't merged. On travelai (2026-11-02): `guard`'s Kotlin and Dart checks and deploy test each went red on a planted violation. Python was proven on a throwaway repo.

**Not yet run.** `build3` and `review` on the new model; `guard`'s CI and branch protection; a full `verify` on travelai; blocked → resume; a green merge; the TypeScript, Go and Rust/Swift adapters.

**Next.** Trim every skill, then a trial with planted defects: a forbidden dependency, an unauthorized writer, a consumer without dedupe.
