# Craft Skills

Keep a codebase healthy while agents keep changing it.

Over a long run of features and fixes, agents tend to erode architecture, security, maintainability and reliability a little at a time. Craft adds what stops that: executable acceptance, enforced architecture, and visual pages that show you only what deserves your attention.

You delegate the coding, not the decisions. Craft surfaces expensive-to-undo decisions (data model, boundaries, contracts) while they're cheap to change, recommends, and lets you steer.

**Success means** less human review effort, less architecture drift, fewer regressions and a smaller change radius.

**Fits** a codebase you'll keep evolving, with agents doing most of the coding. Overkill for throwaway prototypes. Still being proven: see [Status](#status).

## How it works

Each skill outputs durable info to your repo, where the next skill reads it.

```text
Once          prod → arch3 → guard
Each change   (idea →) feat or task → build3 (runs verify and review) → merged, or waiting for your review
Quick fix     fix
Periodically  audit → decide on findings in arch3
```

| Skill | Goal | Output | Needs |
| --- | --- | --- | --- |
| `prod` | Define what we are building and why | `PRODUCT.md` | |
| `arch3` | Define the architecture | `architecture.yaml`, `AGENTS.md`, findings, HTML page | a product purpose; existing code if any |
| `guard` | Enforce architecture and code quality | `verify` command with deterministic checks | `architecture.yaml` |
| `idea <hunch>` | Capture an idea for later | `.craft/ideas/idea-*.md`, checked against `PRODUCT.md` | `PRODUCT.md` |
| `feat <feature>` | Define a feature, ready for implementation | `.craft/ready/feat-*.md`: contracts, acceptance criteria, doc impact | `PRODUCT.md`, `architecture.yaml` |
| `task <task>` | Same, for a small change with no contract or architecture impact | One-screen `.craft/ready/task-*.md` | `architecture.yaml`, `AGENTS.md` |
| `build3 [all\|<item>]` | Implement an item | Branch, merged or waiting for your review | `.craft/ready/*.md`, `verify` |
| `review [<item>\|<branch>\|walk]` | Show what a change did and where attention is needed | Risk tier, findings, page. Works on any branch | |
| `fix` | Fix a bug surgically in this session, skipping `build3` and `review` | Minimal change with a test that was red first | |
| `audit` | Assess the health of the whole repo | `.craft/audit-*.md`: findings, scores, actions | |
| `whereami` | Reorient after a break | Status report and HTML dashboard: focus, parked ideas, next step | `.craft/` work items |
| `orient` | Understand an unfamiliar repo | Map of structure, architecture and dependencies, in the session | |
| `sa` | Design a technical solution, also used by `arch3` and `feat` | Options with a recommendation; ADRs in `.craft/adr/` on your yes | |
| `ba` | Decompose requirements | Functional spec: epics, features, user stories with acceptance criteria | |

A skill missing its input offers to run the skill that creates it, e.g. `build3` stops and offers `guard`.

## Getting started

**Requires** `git`, [`uv`](https://docs.astral.sh/uv/), your project's toolchain, and Claude Code or another agent host. Any git host or CI works, or none. Without subagents, `build3` stops after `verify` for you to run `review` in a new session.

```claude
/plugin marketplace add andpush/craft-skills
/plugin install craft
```

Companion skills: `simplify` and `code-review`, `security-review` (used by `build3` and `review`), `playwright-cli` (UI end-to-end tests).

**Onboard:** `/craft:init` for a small project, otherwise `/prod`, `/arch3`, `/guard` separately. Existing files are adopted, not overwritten.

- **New project:** you define the product and architecture together. Rerun `guard` once there's code to check.
- **Existing project:** Craft derives both from the code and asks only what code can't tell. `guard` freezes existing violations in a baseline, so only new ones fail and debt can only shrink.

**Then:** add `verify` to your pipeline, and start with `/feat <feature>` and `/build3`.

**Recommended LLMs:** Opus/high for `prod` and `arch3`, Opus/medium for `feat`, Opus/medium or Sonnet/high for `build3`, which runs unattended once permissions are granted.

## Making a change

1. **Plan.** `feat` or `task` commits an item to `.craft/ready/` on main.
2. **Build.** `build3`, by hand or on a schedule, works on a `craft/<item>` branch in a sibling worktree: acceptance tests (with the code for `task` items), implementation, `verify`, independent `review`, docs, `verify` again.
3. **Merge.** 🟢 merges to local main by itself. 🟡 and 🔴 wait for you, and so does 🟢 if your main checkout has uncommitted changes. Run `review walk` to go through everything waiting and merge what you accept.
4. **Sync.** No skill pulls or pushes, so deploying stays your call. Periodically run `git pull --no-rebase`, `verify`, fix anything red, `git push`. Two changes can each pass and still fail together. If both sides changed `architecture.yaml`, regenerate the gate with `validate.py --gate`.

Why you can trust the result:

- **Acceptance tests are committed red first,** written by a separate agent from the spec alone. Renames are flagged; deleting or skipping a test turns the change red.
- **The reviewer isn't the author.** A fresh agent runs `/code-review` and `/security-review`, checks the spec, contracts and `architecture.yaml`, and turns suspicions into failing tests.
- **A script computes the tier,** not an agent.
- **Each item is one merge commit** with its code and docs, so one revert undoes it.

**Teams:** claims are local branches, so two developers could build the same item. Build the items you created, or sync before a scheduled run. A duplicate shows up as a conflict at sync.

## The gate: `verify`

One command, wired by `guard` from your existing scripts and named in `AGENTS.md`. It runs build, lint, tests and architecture checks, and fails on any failure, including a test filter that matches nothing.

Architecture checks fail on:

- an import between units that `architecture.yaml` doesn't allow
- an undeclared kind of I/O library (persistence, client, messaging, server)
- a production file that belongs to no unit
- a gate file out of date with `architecture.yaml`
- a broken `must` rule, or deployed exposure that differs from what's declared

`guard` proves each check by planting a violation and showing it go red. Recipes cover Python, Kotlin, TypeScript/JavaScript, Go, Rust, Swift and Dart/Flutter.

`build3` runs it before every merge, agents find it in `AGENTS.md`, and you can run it anytime. Call it from CI before deploy too; it needs only your toolchain. Otherwise changes that skip `build3` go unchecked.

`verify` only catches what's mechanical. For justified architecture changes or drift in meaning, use `arch3` reconcile, which `feat` runs when a change adds a component or contract. Rerun `guard` after `architecture.yaml` changes.

## Where you spend attention

Review what's expensive to undo. Agents can cheaply rewrite internals, but a bad data model, API or security decision gets costlier as code builds on it.

| When | Trigger | What you do |
| --- | --- | --- |
| Before code | Every `feat` | Approve the plan: goal, contract changes, acceptance criteria, open questions. Your best use of time |
| Before merge | 🟢 none of the below | Nothing |
| | 🟡 new relation, other architecture changes, edited acceptance test, files outside the spec's target, uncovered callers, unaccepted findings, anything not checked | `review walk`: skim the changes view, merge |
| | 🔴 new dependency, schema, API or event change, security or CI paths, wider exposure, new data writer, new deficiency, weakened rule, deleted or skipped test, doc edits outside the spec, deviation from the spec, confirmed high finding, failing acceptance test | `review walk`: decide each item, merge or send back fixes |
| Periodically | After a batch of items | Run `audit`, view the architecture page, decide findings in `arch3` |

The changes view and `review walk` lead with the data model and API, then deviations, other contracts, findings and blast radius. Open code only where an item points you, and run manual acceptance criteria yourself.

For each item, ask: Is it hard to reverse? Does it change what the system promises? Does it widen who can reach or change what? Does it match what I approved?

**Calibrate:** skim the green items among your first 10 or so. If one should have been flagged, add a trigger. If trivial changes land on red, narrow the list.

To see the architecture, ask "show me the architecture".

## What Craft adds to your repo

```text
AGENTS.md                        # ≤60 lines every agent loads: commands, invariants, workflow
CLAUDE.md                        # @AGENTS.md
PRODUCT.md                       # ≤150 lines: purpose, users, value, constraints, scope
.craft/
├── architecture.yaml            # components, relations, security, data, flows, rules, notes
├── architecture.gate.json       # generated; what verify reads
├── architecture.baseline        # frozen existing violations
├── ideas/idea-*.md              # unvalidated backlog
├── draft/{feat,idea}-*.md       # specs still being shaped
├── ready/{feat,task,idea}-*.md  # build queue
├── done/                        # shipped and rejected items, with <item>.review.json
├── adr/YYYY-MM-DD-*.md          # one decision per file
└── audit-*.md                   # health snapshots
```

`guard` also adds architecture and rule tests to your suite. HTML pages go to a temp folder and are never committed.

**Work items** move `ideas/ → draft/ → ready/ → done/` and keep their `type-slug.md` name throughout. The folder is the state: tasks skip `draft/`, and anything committed in `ready/` can be built. A `craft/<item>` branch is the claim, and a failed build adds a `blocked:` line on it. Order is `priority: high`, then `created:`. Closed work is archived, not deleted.

## Other skills

| Skill | Does |
| --- | --- |
| `doc-refactor <in> -> <out> [goal]` | merge and dedupe docs, preserving knowledge |
| `tests-optimizer` | prune low-value tests, prove the suite is faster and still green |
| `compare` | compare two codebases, pick a winner |
| `slides`, `ui-mockup`, `uiux-design`, `lit-translate` | decks, clickable mockups, UI/UX design, literary translation |

Avoid `arch`, `build` and `code-reviewer`: they're being replaced by `arch3`, `build3` and `review`.

## Status

The `3` suffix marks new versions. It goes away once they're proven and the old skills are removed.

**Proven.** On a Kotlin fixture (2026-10-28, run stopped halfway), `build3` and `review` wrote acceptance tests red first, and `review` proved a spec gap with a failing test, blocking the merge. On travelai (2026-11-02), `guard`'s Kotlin and Dart checks and deploy test went red on planted violations. Python was proven on a throwaway repo.

**Not yet run.** `build3` and `review` on the current `architecture.yaml` format; the worktree flow; a full `verify` on travelai; blocked → resume; a green merge; the TypeScript, Go and Rust/Swift adapters.

**Next.** Trim every skill, then a trial with planted defects: a forbidden dependency, an unauthorized writer, a consumer without dedupe.

## Design principles

For skill developers:

- **Markdown and YAML are the source of truth;** pages are rendered by script into one logic-free template.
- **One fact, one place.** Stable IDs (rule id, `AC2`, ADR slug, component name) tie docs to code and tests.
- **Intent is never silently rewritten to match code.** Drift means fixing the code, fixing a stale line, or an explicit decision.
- **Deterministic where possible;** AI writes the implementation and is verified separately.
- **Not checked ≠ passed.** Skipped, unsupported or empty is a failure or an explicit "not checked".
- **Depth matches risk.** Omit empty sections, keep small changes small.
- **Derive rather than store;** anything stored must be something a check can catch drifting.
- **No pipeline or host lock-in.** `verify` is the interface.
- **Skills hold only what a model can't work out itself:** project facts, how skills connect, checks on the agent's own work.

## License

MIT
