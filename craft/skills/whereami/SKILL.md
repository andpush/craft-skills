---
name: whereami
description: Use when user asks about the state of the project to orient fast after a context switch — recall where work was left off, what was being solved, whether it landed, and the likely next step.
---

Reload the user's mental context in seconds. Read the artifacts, infer the story, report it compressed. NOT a code review — surface only what's needed to recall and continue.

## Gather (skip what's absent)

Four folders under `.craft/`: `ideas/` (raw candidates), `draft/` (specs still being shaped), `ready/` (the execution queue — build-ready `feat-`/`task-`/promoted `idea-` items), and `done/` (archive of shipped + rejected items). `ideas/`, `draft/` and `ready/` are the live set; `done/` is the timeline, not live work. Filenames (`type-slug`) are the index — don't open files unless needed.

- `PRODUCT.md` first lines — what this is.
- The queue and archive, newest last:
```bash
ls -1 .craft/draft/*.md .craft/ready/*.md .craft/done/*.md 2>/dev/null | sort
```
- Queue priorities, and any legacy status:
```bash
grep -H '^status:\|^priority:' .craft/ready/*.md 2>/dev/null
```
  Everything in `.craft/ready/` is queued. `in-progress` is legacy `build`; with `build3` a claim is a branch.
- Claims — branches. `craft/<item>` = claimed; its tip says how far it got:
```bash
git branch -a --list '*craft/*' --format='%(refname:short) %(committerdate:relative) %(subject)'
```
  `status: blocked` on the branch (`git show craft/<item>:.craft/ready/<item>.md | grep '^status:\|^blocked:'`) = a build failed it. A review file on the branch (`git show craft/<item>:.craft/ready/<item>.review.json`) = waiting for the human; report why from that file: `tier` and `triggers`. A 🟢 waits only because the main checkout wasn't clean and on main when it tried to merge, or because the user held it. Neither, and no recent commit = stale claim. Lead the report with blocked, then waiting-for-review, then in progress.
- Decisions (`ls -1 .craft/adr/*.md 2>/dev/null | tail -5`, or legacy `ADR.md` tail) — recent architectural changes; filenames carry date + slug, open only if needed.
- Ideas (`grep -H '^status:\|^priority:' .craft/ideas/*.md 2>/dev/null`) — candidates, not commitments; report them parked, not as tasks. `open`/`deferred` here are the live pool. Weight by priority: lead with `high`, fold `low` into a count, flag ideas with no `priority` as awaiting triage.

For git repos, also check for uncommitted changes, unmerged branches, and recent commits.

## Infer

- Last contribution: newest queue/done items + commits — what was being solved.
- Stuck? A `blocked` item in WIP, dangling uncommitted edits, big unfinished refactoring, or a branch that hasn't landed in a while.
- Next: `review walk` for anything waiting, `blocked` to unstick, drafts and claims to finish, queued items to pick up, `idea-remove-*` whose condition holds, parked ideas to promote, uncommitted files.

## Report

Produce a brief recap and show a glanceable HTML dashboard

### 1. Brief recap

```
PROJECT: <one line>
OVERALL: <Overall estimation of the state — healthy / stalled / etc. Approx completion estimation %.>

STATISTICS:
| IDEAS | READY | WIP |
|---|---|---|
|   |   |   |

LAST ACTIVITIES: <last 3-5 items with dates — what landed, what is still in progress.>
---
NOW:      <focus / last touched / why-stuck if any>
---
NEXT:     <suggest 1-3 most useful next moves>
---
```


### 2. HTML dashboard

For the user reorienting at a glance, plus a non-technical stakeholder — frame it like a JIRA status report. Use status pills (color), font hierarchy, and monospace ASCII bars so the situation lands in one glance.

Keep it cheap: one self-contained file, inline CSS.
Save in temporary dir and prompt to open in a browser. **DO NOT put it in the repo tree**.