---
name: idea
description: Use to capture a user idea into docs/ideas/ — one small file with a quick alignment check against PRODUCT.md. Capture, not elaboration; specing happens later via `spec`.
---

Capture the idea fast and move on. Ideas are candidates, not commitments — `spec` validates lazily on pickup (pursue / defer / reject). This skill only records and sanity-checks; it never opens a spec.

Optional: if the first word of the args is `high` or `low`, treat it as the priority and strip it from the idea text (e.g. `/idea low rename cat→pet`).

## Capture

Distill the idea to one line. If it's too vague to write down, ask one clarifying question — not an interview.

Write `docs/ideas/idea-NNN-slug.md` — one idea per file. `NNN` is the next free number across all work items (`idea-`/`feat-`/`task-` in `docs/ideas/`, `docs/ready/`, `docs/done/`), zero-padded; `slug` carries the idea. Filenames are the index — a directory listing is the scan. Format:

```markdown
---
status: open
priority: high | low      # optional — omit when unset (untriaged)
updated: YYYY-MM-DD
target: <area>
---

# The idea in one line

Why it might matter; attached thinking the user provided, verbatim-ish.
```

`priority` is optional. Set it only if the user signals one at capture ("this matters" / "minor, someday"); otherwise omit it — an unset priority means untriaged, and `whereami` will surface it for triage. It can be added or changed by hand later. `high` = pull forward, `low` = backlog.

Don't elaborate beyond what was said. Deleting an idea is just deleting its file — the user's call, never yours.

## Lifecycle (owned by `spec`, recorded here)

An idea is born in `docs/ideas/` and stays there, `status: open`, until picked up. Names never change: an idea keeps `idea-NNN-slug.md` through every folder move. `spec` records the verdict on pickup:

- `status: open` — captured, unvalidated. Lives in `docs/ideas/`.
- `status: deferred` — evaluated, not now; stays in `docs/ideas/` (the live scan pool).
- **pursued** — `spec` elaborates the idea in place into a build-ready item and moves it (same name) to `docs/ready/`, where it adopts the queue's `status:` (`ready` → `in-progress` → `done`). The idea now flows like any queued item; `build` executes it and archives it to `docs/done/`.
- `status: rejected` — move the file to `docs/done/` so the idea is archived and not re-proposed.

When status leaves `open`, set `verdict:` — the one-line rationale (quote it if it contains a colon) — and bump `updated`. On any move, `git mv` when tracked so history follows, and carry same-basename images along.

## Check alignment

Skim `PRODUCT.md`. If the idea conflicts with it or falls outside scope, tell the user in one line and record the tension in the file — still capture it. No verdict: pursue/defer/reject belongs to `spec` on pickup.

If `PRODUCT.md` doesn't exist, capture without the check and say so.

## Images

If the user pastes an image, save it next to the idea as `docs/ideas/idea-NNN-slug-<picslug>.<ext>` (idea's basename + a short pic slug) and embed it from the idea file. On pursue, the item — and its images — move together into the queue.

## Report

One line: file created, plus the alignment note if any.
