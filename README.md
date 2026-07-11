# Craft Skills

Product development workflow for agentic development — from idea to production. Ships one plugin,
**`craft`**: a lightweight SDD flow **prod → arch → spec → build**. Discovery is guided and
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
3. **`build`** → craft's executor drains the queue: claims the next `ready` item, implements, reviews, verifies against acceptance, and archives it to `docs/done/`. Faster/cheaper models (Sonnet, GLM-5.2, Minimax M3), unattended or headless once permissions/auto are granted. (`/goal` or any agent still works too.)

Optionally run `simplify` or `review` (any vendor) in a cleared context to catch quality/reuse
issues — fresh context removes creator bias, a different model (e.g. GPT-5.5) helps more.

## Skills

Invoke by name in your agent host (`/prod`, `/spec <feature>`, …).

| Skill | Does |
| --- | --- |
| `prod` | define the product → `PRODUCT.md` |
| `arch` | define architecture → `ARCHITECTURE.md` |
| `spec <feature>` | frame a feature into a build-ready item (`feat-NNN`) in `docs/ready/`, with verifiable acceptance |
| `task <task>` | terse handoff for a small task (`task-NNN`, one component, no architecture work) into `docs/ready/` |
| `build [all\|<file>]` | execute the ready queue: claim → implement → review → verify → archive to `docs/done/` |
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
| `ARCHITECTURE.md` | components, stack, boundaries, layout, entrypoints, conventions | `arch` |
| `docs/ideas/idea-NNN-*.md` | idea backlog (images beside); unvalidated; optional `priority: high\|low` steers `whereami`; `spec` validates on pickup (pursue/defer/reject) | `idea` |
| `docs/ready/*.md` | the execution queue — build-ready `feat-`/`task-`/promoted `idea-` items; `status:` = `ready`\|`in-progress`\|`blocked` | `spec`, `task` |
| `docs/done/*.md` | archive of shipped (`done`) and rejected items | `build`, `spec` |
| `docs/adr/*.md` | why a choice was made, one decision per file | `arch`/`spec`, over time |
| `docs/audit-*.md` | repo health snapshot: findings, scores, action items | `audit` |
| `docs/tests-optimizer-*.md` | flagged low-value tests, before/after metrics | `tests-optimizer` |
| `CLAUDE.md` \| `AGENTS.md` | onboarding for agents | `arch` or manually |
| `README.md` | onboarding for humans; read as a source | human |

**Work items** flow `ideas/ → ready/ → done/`. Each is `type-NNN-slug.md` — type by prefix
(`idea-`/`feat-`/`task-`), `NNN` a zero-padded number unique across all items, `slug` the name.
The **name never changes** once minted — a `feat-007` stays `feat-007` through every folder move; a
pursued idea keeps its `idea-NNN` name into the queue. The **folder** is the coarse state; a
`status:` field distinguishes claimed (`in-progress`) from unclaimed (`ready`) inside the queue so
parallel `build` runs never grab the same item. Images sit beside their item as
`<item>-<picslug>.png` and move with it. Closed work is archived (moved to `done/`), not deleted;
deleting a file to drop it is the user's call. `/whereami` flags items left in the wrong folder.

## Removed: staged commands

The staged `/1`–`/9` commands are gone; use the skills workflow above. Their useful pieces live
on: parallel design variants in `ui-mockup`, competition/NFR sections in the `prod` template,
decisions/testing/open-questions sections in the `arch` template.

## License

MIT
</content>
