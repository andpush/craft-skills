# Craft Skills

Keep a codebase healthy while agents keep changing it. Over a long run of features and fixes, agents tend to erode architecture, security, maintainability and reliability a little at a time. Craft adds what stops that: executable acceptance, an independent review, mechanically enforced architecture, and visual pages that show you only what deserves your attention.

You delegate the coding, not the decisions. Craft surfaces expensive-to-undo decisions (data model, boundaries, contracts) while they're cheap to change, recommends, and lets you steer.

**Success means** less context to read, less human review effort, fewer regressions and a smaller change radius. It doesn't mean more lines, tests or findings.

Ships one plugin, **`craft`**.

## Installation

```claude
/plugin marketplace add andpush/craft-skills
/plugin install craft
```

Recommended companion skills: `simplify`, `code-review`, `security-review`, `playwright-cli`.

## How it works

`prod → arch3 → guard → spec → build3 → review`

Each skill answers one question. Each works greenfield (define with you) or brownfield (derive from code, then confirm), adopting existing files rather than clobbering them.

| Skill | Question | Output | Decides? |
| --- | --- | --- | --- |
| `prod` | What are we building and why? | `docs/PRODUCT.md` | Yes, with you |
| `arch3` | What is our architecture, and is it sound? | `docs/architecture.yaml`, `AGENTS.md`, findings, a page | Yes, with you |
| `guard` | How do we stop it degrading? | `verify` and its checks; set up once, rerun when `architecture.yaml` changes | No, it enforces |
| `spec` / `task` | What will this change do? | A build-ready item in `docs/ready/` | Yes, with you |
| `build3` | Build it | A branch, merged or waiting for you | No, it follows the item |
| `review` | What did this change actually do? | Risk tier, findings, a page | No, it flags for you |
| `audit` | What's the state of the whole repo? | Findings | No, it reports |

Model effort: bigger models with a good thinking budget for the one-time `prod` and `arch3` (Opus/high), medium for `spec` (Opus/medium), and faster, cheaper models for `build3`, which runs unattended once permissions are granted. `/goal` or any other agent still works too.

Three rules keep the skills from overlapping:

1. **One detector.** Mechanical findings live only in `arch3/scripts/validate.py`. Everything else calls it.
2. **Judgement has two owners.** `arch3` looks at the whole system, `review` at one change. Findings that take reading code belong only to these two.
3. **One place to decide.** A finding is fixed, made a rule or accepted only in `arch3`. Its page shows it, `verify` blocks new ones, `review` flags them.

So a finding's life is: `validate.py` or `arch3` finds it → you decide in `arch3` → it's fixed, or frozen in the baseline or gate file → `verify` blocks anything new → `review` shows it to you.

### The gate: `verify`

One command, named in `AGENTS.md`, that runs the build, lint, tests and architecture checks. It fails on any failure, including a test filter that matches nothing. The agent, you and any pipeline all run the same command, and a pipeline has no checks of its own.

Craft depends on no particular pipeline or git host. `build3` runs `verify` before every merge, and your pipeline should call it too, before deploy: an agent's report of its own run isn't independent, and nothing else re-checks a change that skipped `build3`.

`verify` only catches what's mechanical. For drift in meaning, `spec` runs `arch3` reconcile when a change adds a component or a contract, and `audit` runs it periodically.

### The pattern

1. **Plan.** `spec` or `task` commits an item to `docs/ready/` on main.
2. **Build.** `build3`, on a schedule or by hand, builds it on a `craft/<item>` branch in its own worktree. It writes acceptance tests first, implements, runs `verify`, gets an independent `review`, closes the docs in the branch and runs `verify` again.
3. **Merge.** 🟢 green merges to local main by itself. 🟡 yellow and 🔴 red wait on the branch for you. Set `Auto-merge: off` in `AGENTS.md` if everything should wait. If your main checkout has uncommitted changes, the branch waits rather than touching them.
4. **Sync.** Periodically, anyone working on the repo runs `git pull --no-rebase`, runs `verify`, fixes anything red and runs `git push`. Two changes can each pass and still fail together, so `verify` runs after the pull. If both sides changed `architecture.yaml`, regenerate the gate file with `validate.py --gate`. No skill pulls or pushes, so deploying stays your call, and any git host works.

How `build3` keeps this trustworthy:

- **Acceptance tests come first and are committed red.** A separate agent writes them from the spec alone, and the commit records what was agreed. Tests may later follow a rename, which is flagged for you, but deleting or skipping one turns the change red.
- **The reviewer isn't the author.** A fresh agent runs `/code-review` and `/security-review`, checks what those can't know (the spec, contracts, `architecture.yaml`), and turns suspicions into failing tests.
- **The tier is computed by a script,** never chosen by an agent.
- **Each item lands as one merge commit,** with its code, docs and move to `docs/done/` together. It's never squashed, and one revert undoes the whole item.

Claims are local branches, so runs on one machine never grab the same item. Two developers building from the same queue could, so each builds the items they created, or syncs before a scheduled run. A duplicate shows up as a conflict at sync, and one branch gets dropped.

## Where you spend attention

Review where mistakes are expensive to undo, and read contracts and flagged items rather than every line. Agents can cheaply rewrite internals, but a bad data model, API or security decision gets more costly as code builds on it.

| When | Trigger | What you do |
| --- | --- | --- |
| Before code | Every `spec` | Approve the plan on the spec page: the goal, contract changes, acceptance criteria, open questions. This is your best use of time |
| Before merge | 🟢 green: none of the below | Nothing |
| | 🟡 yellow: new relation, other architecture changes, edited acceptance test, files outside the spec's target, uncovered callers, unaccepted findings, anything not checked | Skim the change page, then merge |
| | 🔴 red: new dependency, schema, API or event change, security or CI paths, wider exposure, new data writer, new deficiency, weakened rule, deleted or skipped test, doc edits outside the spec, deviation from the spec, confirmed high finding, failing acceptance test | `review walk`, then merge or send back fixes |
| Periodically | After a batch of items | Run `audit`, look at the architecture page, and decide on findings in `arch3` |

The change page and `review walk` put the data model and API first, then deviations, other contracts, findings and blast radius, so if time runs out you've covered what matters most. Open code only where an item points you. Run manual acceptance criteria yourself, because no test covers them. Every item has an ID, so you can discuss it in the terminal ("H3 — why not reuse X?").

Ask these for each item:

- Is this hard to reverse?
- Does it change what the system promises to others?
- Does it widen who can reach or change what?
- Does it match what I approved?

If all the answers are comfortable, move on quickly.

For your first 10 or so items, also skim the green ones. If one should have been flagged, add a trigger. If most changes land on red for trivial reasons, narrow the list. The tiers need calibrating before you can fully trust them.

To see the architecture at any time, ask "show me the architecture", or run `uv run --quiet <craft-skills>/craft/skills/arch3/scripts/render.py` from the project root.

## Skills

Invoke by name in your agent host (`/prod`, `/spec <feature>`, …).

| Skill | Does |
| --- | --- |
| `prod` | define the product → `docs/PRODUCT.md` |
| `arch3` | define, derive or reconcile architecture → `docs/architecture.yaml`, `AGENTS.md`; decides findings with you; shows it as one HTML page |
| `guard` | make `architecture.yaml` executable: `verify`, gate file, architecture checks, baseline; ready for any pipeline to call |
| `spec <feature>` | frame a feature into a build-ready item (`feat-<slug>`) in `docs/ready/`: contract changes, AC as commands, doc impact |
| `task <task>` | terse handoff for a small task (`task-<slug>`, one component, no contract changes) into `docs/ready/` |
| `build3 [all\|<item>]` | branch → AC tests → implement → verify → `review` → close → verify → merge or wait |
| `review [<item>\|<branch>\|walk]` | risk tier, contracts, counterexample tests → `<item>.review.json`; guided walk |
| `idea <hunch>` | one-file capture + `docs/PRODUCT.md` alignment check |
| `audit` | deep repo health check: structure, maintainability, security |
| `whereami` | reorient after a break: focus, parked ideas, next step; reads claims from branches |
| `init` | macro chaining `prod`, `arch3` and `guard` for a small or fresh project |
| `sa` | design a technical solution for `arch3` and `spec` — system, component, or change |
| `ba` | requirements decomposition |
| `doc-refactor <in> -> <out> [goal]` | merge, dedupe, restructure docs, preserving knowledge |
| `tests-optimizer` | prune low-value tests, prove the suite is faster and still green |
| `compare` | compare two codebases, with a winner |
| `slides` | decks from markdown |
| `ui-mockup` | clickable HTML mockups |
| `uiux-design` | UI/UX design |
| `arch` | old format, kept for reading only |
| `build [all\|<file>]` | old executor, kept until `build3` is proven |
| `code-reviewer` | old code review, kept until `review` is proven |

For larger projects run `/prod` and `/arch3` separately so each can be revisited; `/craft:init` only chains them for a quick start.

## Files

One file per work item or decision. Filenames are the index, and content is scannable, not prose.

| File | Holds | By |
| --- | --- | --- |
| `docs/PRODUCT.md` | ≤150 lines: purpose, users, value, constraints, MVP scope | `prod` |
| `docs/architecture.yaml` | components, relations, security, data, flows, rules, notes | `arch3` |
| `docs/architecture.gate.json`, `docs/architecture.baseline` | what `verify` enforces, generated from `architecture.yaml`, and frozen violations | `guard` |
| `docs/ideas/idea-*.md` | idea backlog (images beside); unvalidated; optional `priority: high\|low` steers `whereami`; `spec` validates on pickup (pursue/defer/reject) | `idea` |
| `docs/ready/*.md` | the execution queue — build-ready `feat-`/`task-`/promoted `idea-` items; `status:` = `draft`\|`ready`\|`blocked`; the claim is a `craft/<item>` branch | `spec`, `task` |
| `docs/done/*.md` | archive of shipped (`done`) and rejected items, with `<item>.review.json` | `build3`, `spec` |
| `docs/adr/YYYY-MM-DD-*.md` | one decision per file: Context / Decision / Rejected / Consequences; optional `supersedes` | `sa`, `build3` |
| `docs/audit-*.md` | repo health snapshot: findings, scores, action items | `audit` |
| `docs/tests-optimizer-*.md` | flagged low-value tests, before/after metrics | `tests-optimizer` |
| `AGENTS.md` | ≤60 lines every agent loads: commands incl. `verify`, invariants, auto-merge and sync, pointers; `CLAUDE.md` = `@AGENTS.md` | `arch3`, `guard` |
| `README.md` | onboarding for humans; read as a source | human |

**Work items** flow `ideas/ → ready/ → done/`. Each is `type-slug.md`, with the type as a prefix (`idea-`/`feat-`/`task-`) and `slug` unique across all items. A split sequence uses `-a-`, `-b-` after the type. Queue order is `priority: high` first, then `created:`. The **name never changes** once minted; a pursued idea keeps its `idea-` name into the queue. The **folder** is the coarse state. A claim is a `craft/<item>` branch. Images and review files sit beside their item under the same basename and move with it. Closed work is archived (moved to `done/`), not deleted; deleting a file to drop it is your call. `/whereami` flags items left in the wrong folder.

## Design principles

For anyone developing these skills:

- **Markdown and YAML are the source of truth.** HTML pages are rendered by a script into one logic-free template, opened from a temp folder and never committed. A page belongs to the skill whose question it answers.
- **One fact, one place.** Link, don't restate. Stable IDs (rule id, `AC2`, ADR slug, component name) tie docs to code and tests.
- **Intent is never silently rewritten to match code.** Drift means fixing the code, fixing a stale line, or making an explicit decision.
- **One file feeds checks, pages and agents:** `docs/architecture.yaml`.
- **Deterministic where possible:** checks, triggers, diagrams, pages. AI writes the implementation and is verified separately.
- **Not checked ≠ passed.** Skipped, unsupported or an empty selection is a failure or an explicit "not checked".
- **Depth matches risk.** Sections without content are omitted, and small changes stay small.
- **Anything stored must be something a check can catch drifting.** Derive rather than store.
- **No pipeline or host lock-in.** `verify` is the interface, and no skill needs a particular CI or git host.
- **Skills hold only what a model can't work out itself:** project facts, how skills connect, and checks on the agent's own work. However capable a model gets, it shouldn't grade its own work. Generic good practice doesn't belong in a skill.

## Status

Skills with the suffix `3` are the new versions. Once they're reviewed and proven, the old `arch`, `build` and `code-reviewer` go away and `arch3` and `build3` lose the suffix.

**Proven.** On a Kotlin fixture (2026-10-28, run stopped halfway), `build3` and `review` wrote acceptance tests red first, and `review` proved a spec gap with a failing test, so a red change wasn't merged. On travelai (2026-11-02), `guard`'s Kotlin and Dart checks and deploy test each went red on a planted violation. Python was proven on a throwaway repo.

**Not yet run.** `build3` and `review` on the current `architecture.yaml` format; the worktree flow; a full `verify` on travelai; blocked → resume; a green merge; the TypeScript, Go and Rust/Swift adapters.

**Next.** Trim every skill, then a trial with planted defects: a forbidden dependency, an unauthorized writer, a consumer without dedupe.

## License

MIT
