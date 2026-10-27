# Craft Skills

Product development workflow for agentic development — from idea to production. Ships one plugin,
**`craft`**: a lightweight SDD flow **prod → arch → guard → spec → build3 → review**. Discovery is guided and
conversational — craft surfaces expensive-to-undo decisions (data model, boundaries) while they're
cheap to change, recommends, and lets you steer; you delegate the coding, not the decisions.
Token-frugal: no planning that doesn't change the outcome, no questionnaire theatre. Decisions land
in durable, scannable files so build is execution against a clear spec.

## Installation

```claude
/plugin marketplace add andpush/craft-skills
/plugin install craft
```

Recommended companion skills: `simplify`, `code-review`, `playwright-cli`.

## Workflow

`prod → arch → spec → build`; each skill works greenfield (define with you) or brownfield (derive
from code, then confirm), adopting existing files rather than clobbering them.

1. **`prod`** → `PRODUCT.md`, **`arch`** → `ARCHITECTURE.md`. Required for later steps; one-time, so use bigger models (Opus/high). Or write them by hand / via `/impeccable teach`.
2. **`spec`** → a build-ready item in the queue `docs/ready/` (small tasks go straight there via `task`). Medium efforts (Opus/medium, GPT-5.5).
3. **`guard`** (once, after `arch`) → one `verify` command, architecture checks generated from `architecture.yaml`, CI that runs `verify`, branch protection.
4. **`build3`** → per item, on a `craft/<item>` branch: acceptance tests first, implement, verify, an independent `review`, docs closed in the branch, then a PR or merge per the policy in `AGENTS.md`. Faster/cheaper models, unattended once permissions are granted. (`/goal` or any agent still works too.)
5. **`review`** → computes a risk tier, describes contract changes (data model, API, dependencies) and turns suspicions into failing tests; `review walk` guides you through what matters in the terminal, with the change page open in the browser.

The v3 design contract is [docs/craft-v3.md](docs/craft-v3.md). `build` and `code-reviewer` stay until `build3` and `review` prove themselves.

## Skills

Invoke by name in your agent host (`/prod`, `/spec <feature>`, …).

| Skill | Does |
| --- | --- |
| `prod` | define the product → `PRODUCT.md` |
| `arch` | define architecture → `architecture.yaml` (the model), `ARCHITECTURE.md` (prose), `AGENTS.md` |
| `guard` | make the model executable: `verify`, architecture checks, baseline, CI, branch protection |
| `spec <feature>` | frame a feature into a build-ready item (`feat-<slug>`) in `docs/ready/`: contract changes, AC as commands, doc impact |
| `task <task>` | terse handoff for a small task (`task-<slug>`, one component, no contract changes) into `docs/ready/` |
| `build3 [all\|<item>]` | branch → AC tests → implement → verify → `review` → close → PR/merge |
| `review [<item>\|PR#\|walk]` | risk tier, contracts, counterexample tests → `<item>.review.json`; guided walk |
| `view spec\|change\|model` | render a spec, a change review or the architecture model as an HTML page |
| `build [all\|<file>]` | v2 executor, kept until `build3` is proven |
| `idea <hunch>` | one-file capture + `PRODUCT.md` alignment check |
| `audit` | deep repo health check: structure, maintainability, security |
| `doc-refactor <in> -> <out> [goal]` | merge, dedupe, restructure docs, preserving knowledge |
| `whereami` | reorient after a break: focus, parked ideas, next step |
| `init` | macro chaining `prod` then `arch` for a small/fresh project |
| `ba` | requirements decomposition |
| `sa` | design a technical solution — system, component, or change |
| `code-reviewer` | review code quality |
| `tests-optimizer` | prune low-value tests, prove the suite is faster and still green |
| `compare` | compare two codebases, with a winner |
| `slides` | decks from markdown |
| `ui-mockup` | clickable HTML mockups |
| `uiux-design` | UI/UX design |

For larger projects run `/prod` and `/arch` separately so each can be revisited; `/craft:init` only
chains them for a quick start.

## Files

One file per work item / decision — filenames are the index, content is scannable, not prose.

| File | Holds | By |
| --- | --- | --- |
| `PRODUCT.md` | purpose, users, value, constraints, MVP scope | `prod` |
| `architecture.yaml` | the model: context, components, entities, main flows, rules, review triggers | `arch` |
| `ARCHITECTURE.md` | prose that explains the model: why, stack, flows, glossary, conventions | `arch` |
| `docs/ideas/idea-*.md` | idea backlog (images beside); unvalidated; optional `priority: high\|low` steers `whereami`; `spec` validates on pickup (pursue/defer/reject) | `idea` |
| `docs/ready/*.md` | the execution queue — build-ready `feat-`/`task-`/promoted `idea-` items; `status:` = `draft`\|`ready`\|`blocked`; the claim is a `craft/<item>` branch | `spec`, `task` |
| `docs/done/*.md` | archive of shipped (`done`) and rejected items, with `<item>.review.json` | `build3`, `spec` |
| `docs/adr/YYYY-MM-DD-*.md` | one decision per file: Context / Decision / Rejected / Consequences; optional `supersedes` | `sa`, `build3` |
| `docs/audit-*.md` | repo health snapshot: findings, scores, action items | `audit` |
| `docs/tests-optimizer-*.md` | flagged low-value tests, before/after metrics | `tests-optimizer` |
| `AGENTS.md` | ≤60 lines every agent loads: commands incl. `verify`, invariants, merge policy, pointers; `CLAUDE.md` = `@AGENTS.md` | `arch`, `guard` |
| `README.md` | onboarding for humans; read as a source | human |

**Work items** flow `ideas/ → ready/ → done/`. Each is `type-slug.md` — type by prefix
(`idea-`/`feat-`/`task-`), `slug` unique across all items, `created:` in the frontmatter orders the
queue. The **name never changes** once minted; a pursued idea keeps its `idea-` name into the
queue. The **folder** is the coarse state. A claim is a `craft/<item>` branch, pushed at once, so
parallel runs never grab the same item; merging the branch lands the code, the docs and the move
to `done/` together. Images sit beside their item as
`<item>-<picslug>.png` and move with it. Closed work is archived (moved to `done/`), not deleted;
deleting a file to drop it is the user's call. `/whereami` flags items left in the wrong folder.

## Removed: staged commands

The staged `/1`–`/9` commands are gone; use the skills workflow above. Their useful pieces live
on: parallel design variants in `ui-mockup`, competition/NFR sections in the `prod` template,
decisions/testing/open-questions sections in the `arch` template.

## License

MIT
</content>
