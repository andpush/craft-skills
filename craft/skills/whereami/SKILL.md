---
name: whereami
description: Use when user asks about the state of the project to orient fast after a context switch — recall where work was left off, what was being solved, whether it landed, and the likely next step.
---

Reload the user's mental context in seconds. Read the artifacts, infer the story, report it compressed. NOT a code review — surface only what's needed to recall and continue.

## Gather (skip what's absent)

Three folders under `docs/`: `ideas/` (raw candidates), `ready/` (the execution queue — build-ready `feat-`/`task-`/promoted `idea-` items), and `done/` (archive of shipped + rejected items). `ideas/` + `ready/` are the live set; `done/` is the timeline, not live work. Filenames (`type-slug`) are the index — don't open files unless needed.

- `docs/PRODUCT.md` first lines — what this is.
- The queue and archive, newest last:
```bash
ls -1 docs/ready/*.md docs/done/*.md 2>/dev/null | sort
```
- Queue state — what's live vs claimed vs stuck (an item's `status:` distinguishes them within `docs/ready/`):
```bash
grep -H '^status:\|^priority:' docs/ready/*.md 2>/dev/null
```
  `ready` = queued. `in-progress` is legacy `build`; with `build3` a claim is a branch.
- Claims — branches and PRs. `craft/<item>` = claimed; its tip says how far it got:
```bash
git branch -a --list '*craft/*' --format='%(refname:short) %(committerdate:relative) %(subject)'
gh pr list --search 'head:craft/' --json number,title,headRefName,isDraft,statusCheckRollup 2>/dev/null
```
  A draft PR or `status: blocked` on the branch (`git show craft/<item>:docs/ready/<item>.md | grep '^status:\|^blocked:'`) = a build failed it. An open PR = waiting for the human; its tier is in `<item>.review.json` on the branch. A branch with no PR and no recent commit = stale claim. Lead the report with blocked, then waiting-for-review, then in progress.
- Decisions (`ls -1 docs/adr/*.md 2>/dev/null | tail -5`, or legacy `ADR.md` tail) — recent architectural changes; filenames carry date + slug, open only if needed.
- Ideas (`grep -H '^status:\|^priority:' docs/ideas/*.md 2>/dev/null`) — candidates, not commitments; report them parked, not as tasks. `open`/`deferred` here are the live pool. Weight by priority: lead with `high`, fold `low` into a count, flag ideas with no `priority` as awaiting triage.
- Misplaced (closed but still in the queue — bookkeeping): items that finished but weren't moved to `docs/done/`:
```bash
grep -l '^status: done' docs/ready/*.md 2>/dev/null
```

For git repos, also check for uncommitted changes, unmerged branches, and recent commits.

## Infer

- Last contribution: newest queue/done items + commits — what was being solved.
- Stuck? A `blocked` item in WIP, dangling uncommitted edits, big unfinished refactoring, or a branch that hasn't landed in a while.
- Next: PRs waiting for review (red first → `review walk`), `blocked` to unstick, claims to finish, `ready` to pick up, `idea-remove-*` whose condition holds, parked ideas to promote, uncommitted files.

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