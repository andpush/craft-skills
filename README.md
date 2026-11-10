# Craft Skills

Keep a codebase healthy while agents keep changing it.

Over a long run of features and fixes, agents tend to erode architecture, security, maintainability and reliability a little at a time. Craft adds what stops that: executable acceptance, enforced architecture, and visual pages that show you only what deserves your attention.

You delegate the coding, not the decisions. Craft surfaces expensive-to-undo decisions (data model, boundaries, contracts) while they're cheap to change, recommends, and lets you steer.

**Success means** less human review effort, less architecture drift, fewer regressions and a smaller change radius.

**Fits** a codebase you'll keep evolving, with agents doing most of the coding. Overkill for throwaway prototypes. Still being proven: see [what has and hasn't been run](CONTRIBUTING.md#status).

## How it works

Each skill outputs durable info to your repo, where the next skill reads it.

```text
Once          prod → arch3 → guard
Each change   (idea →) feat or task → build3 (runs verify and review) → merged, or waiting for review walk
Quick fix     fix
Periodically  audit → decide on findings in arch3
```

| Skill | Goal | Output |
| --- | --- | --- |
| `prod` | Define what we are building and why | `PRODUCT.md` |
| `arch3` | Define the architecture; ask "show me the architecture" to view it | `architecture.yaml`, `README.md` digest, `AGENTS.md`, findings, HTML page |
| `guard` | Enforce architecture and code quality; rerun when `architecture.yaml` changes | `verify` command with deterministic checks |
| `idea <hunch>` | Capture an idea for later | `.craft/draft/idea-*.md`, checked against `PRODUCT.md` |
| `feat <feature>` | Define a feature, ready for implementation | `.craft/ready/feat-*.md`: contracts, acceptance criteria, doc impact |
| `task <task>` | Same, for a small change with no contract or architecture impact | One-screen `.craft/ready/task-*.md` |
| `build3 [all\|<item>]` | Implement an item | Branch, merged or waiting for `review walk` |
| `review [<item>\|<branch>]` | Show what a change did and where attention is needed | Risk tier, findings, page. Works on any branch |
| `review walk [<item>]` | Go through everything waiting for you | Your decisions; merges what you accept, sends the rest back |
| `fix` | Fix a bug surgically in this session, skipping `build3` and `review` | Minimal change with a test that was red first |
| `audit` | Assess the health of the whole repo | `.craft/audit-*.md`: findings, scores, actions |
| `whereami` | Reorient after a break | Status report and HTML dashboard: focus, what's waiting and why, parked ideas, next step |

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

Spend your attention on what's expensive to undo. Agents can cheaply rewrite internals, but a bad data model, API or security decision gets costlier as code builds on it.

1. **Plan.** `feat` shapes a spec in `.craft/draft/` and, once you approve it, commits it to `.craft/ready/` on main. `task` commits there directly. Approving the goal, contract changes and acceptance criteria is your best use of time.
2. **Build.** `build3`, by hand or on a schedule, works on a `craft/<item>` branch in a sibling worktree: acceptance tests (with the code for `task` items), implementation, `verify`, independent `review`, docs, `verify` again.
3. **Merge.** A script sets the tier. Run `review walk` from your main checkout to go through everything waiting. It points you to what matters, so open code only where an item sends you.

   | Tier | Typical causes | What happens |
   | --- | --- | --- |
   | 🟢 | None of the below | Merges to local main by itself, unless your main checkout has uncommitted changes or isn't on main |
   | 🟡 | New relation, files outside the spec's target, edited acceptance test, anything not checked | Waits: skim the changes view, then merge |
   | 🔴 | Dependency, schema or API change, wider exposure, weakened test, deviation from the spec, confirmed high finding | Waits: decide each item, then merge or send back fixes |

4. **Sync.** Skills do no git pull or push on their own, so syncing stays your call. Periodically run `git pull --no-rebase`, `verify`, fix anything red, `git push`. Two changes can each pass and still fail together. If both sides changed `architecture.yaml`, regenerate the gate with `validate.py --gate`.

Why you can trust the result:

- **Acceptance tests are committed red first,** written by a separate agent from the spec alone. Renames are flagged; deleting or skipping a test turns the change red.
- **The reviewer isn't the author.** A fresh agent runs `/code-review` and `/security-review`, checks the spec, contracts and `architecture.yaml`, and turns suspicions into failing tests.
- **A script computes the tier,** not an agent.
- **Each item is one merge commit** with its code and docs, so one revert undoes it.

**Teams:** claims are local branches, so two developers could build the same item. Build the items you created, or sync before a scheduled run. A duplicate shows up as a conflict at sync.

## The gate: `verify`

One command, wired by `guard` from your existing scripts and named in `README.md`. It runs build, lint, tests and architecture checks, and fails on any failure, including a test filter that matches nothing. `build3` runs it before every merge. Call it from CI before deploy too, or changes that skip `build3` go unchecked.

Architecture checks fail on:

- an import between units that `architecture.yaml` doesn't allow
- an undeclared kind of I/O library (persistence, client, messaging, server)
- a production file that belongs to no unit
- a gate file out of date with `architecture.yaml`
- a broken `must` rule, or deployed exposure that differs from what's declared

`guard` proves each check by planting a violation and showing it go red. Recipes cover Python, Kotlin, TypeScript/JavaScript, Go, Rust, Swift and Dart/Flutter.

`verify` only catches what's mechanical. For justified architecture changes or drift in meaning, use `arch3` reconcile, which `feat` runs when a change adds a component or contract.

## What Craft adds to your repo

```text
README.md                        # ≤100 lines: vision, architecture digest, commands, references
AGENTS.md                        # @README.md first; the rest is yours
CLAUDE.md                        # @AGENTS.md; the rest is yours
PRODUCT.md                       # ≤150 lines: purpose, users, value, constraints, scope
.craft/
├── architecture.yaml            # components, relations, security, data, flows, rules, notes
├── architecture.gate.json       # generated; what verify reads
├── architecture.baseline        # frozen existing violations
├── draft/{idea,feat}-*.md       # unvalidated ideas, specs still being shaped
├── ready/{feat,task}-*.md       # build queue
├── done/                        # shipped items with <item>.review.json, rejected ideas
├── adr/YYYY-MM-DD-*.md          # one decision per file
└── audit-*.md                   # health snapshots
```

`guard` also adds architecture and rule tests to your suite. HTML pages go to a temp folder and are never committed. Craft writes the first sections of `README.md` and keeps them true; you can reword them and add your own.

**Work items** move `draft/ → ready/ → done/` and keep their `type-slug.md` name throughout. The folder is the state: tasks skip `draft/`, and anything committed in `ready/` can be built. A `craft/<item>` branch is the claim, and a failed build adds a `blocked:` line on it.

**Ideas** wait in `draft/`. A `resolution:` line records `postpone` or `reject` with the reason, and a rejected idea moves to `done/`. An idea you implement is deleted once its `feat-` or `task-` item reaches `ready/`.

The queue's order is `priority: high`, then `created:`. Closed work is archived, not deleted.

## Other skills

In the `craft` plugin:

| Skill | Does |
| --- | --- |
| `sa` | design a technical solution: options with a recommendation, ADRs on your yes; also used by `arch3` and `feat` |
| `ba` | decompose requirements into epics, features and user stories with acceptance criteria |

Plain skills in `misc/skills/`, not installed with the plugin. To use one, copy its folder to `~/.claude/skills/`:

| Skill | Does |
| --- | --- |
| `orient` | map an unfamiliar repo's structure, architecture and dependencies, in the session |
| `doc-refactor <in> -> <out> [goal]` | merge and dedupe docs, preserving knowledge |
| `tests-optimizer` | prune low-value tests, prove the suite is faster and still green |
| `compare` | compare two codebases, pick a winner |
| `slides`, `ui-mockup`, `uiux-design`, `lit-translate` | decks, clickable mockups, UI/UX design, literary translation |

Avoid `arch`, `build` and `code-reviewer`: they're being replaced by `arch3`, `build3` and `review`.

## License

MIT
