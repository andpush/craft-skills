---
name: idea
description: Use to capture a user idea into .craft/ideas/ — one small file with a quick alignment check against PRODUCT.md. Capture, not elaboration; the spec is written later via `feat`.
---

Capture the idea fast and move on. Ideas are candidates, not commitments — `feat` validates lazily on pickup (pursue / defer / reject). This skill only records and sanity-checks; it never opens a spec.

Optional: if the first word of the args is `high` or `low`, treat it as the priority and strip it from the idea text (e.g. `/idea low rename cat→pet`).

## Capture

Distill the idea to one line. If it's too vague to write down, ask one clarifying question — not an interview.

Write `.craft/ideas/idea-<slug>.md` — one idea per file. `slug` carries the idea and is unique across `.craft/ideas/`, `.craft/draft/`, `.craft/ready/` and `.craft/done/`. Filenames are the index — a directory listing is the scan. Format:

```markdown
---
status: open
priority: high | low      # optional — omit when unset (untriaged)
created: YYYY-MM-DD
updated: YYYY-MM-DD
target: <area>
---

# The idea in one line

Why it might matter; attached thinking the user provided, verbatim-ish.
```

`priority` is optional. Set it only if the user signals one at capture ("this matters" / "minor, someday"); otherwise omit it — an unset priority means untriaged, and `whereami` will surface it for triage. It can be added or changed by hand later. `high` = pull forward, `low` = backlog.

Don't elaborate beyond what was said. Deleting an idea is just deleting its file — the user's call, never yours.

## Lifecycle (owned by `feat`, recorded here)

An idea is born in `.craft/ideas/` and stays there, `status: open`, until picked up. Names never change: an idea keeps `idea-<slug>.md` through every folder move. `feat` records the verdict on pickup:

- `status: open` — captured, unvalidated. Lives in `.craft/ideas/`.
- `status: deferred` — evaluated, not now; stays in `.craft/ideas/` (the live scan pool).
- **pursued** — `feat` moves the idea (same name) to `.craft/draft/`, elaborates it into a build-ready item, then moves it to `.craft/ready/`, dropping `status:`. The idea now flows like any queued item; `build3` executes it and archives it to `.craft/done/`.
- `status: rejected` — move the file to `.craft/done/` so the idea is archived and not re-proposed.

When status leaves `open`, set `verdict:` — the one-line rationale (quote it if it contains a colon) — and bump `updated`. On any move, `git mv` when tracked so history follows, and carry same-basename images along.

## Removal ideas

Temporary code — a feature flag, an adapter, a dual write, a compatibility shim — gets an idea when it's introduced (`build3` files these at close): `idea-remove-<slug>.md`, `priority: high`, with the removal condition as the body's first line — `Remove when: all clients send the key`. `whereami` surfaces them; they're debt with a due date, not candidates.

## Check alignment

Skim `PRODUCT.md`. If the idea conflicts with it or falls outside scope, tell the user in one line and record the tension in the file — still capture it. No verdict: pursue/defer/reject belongs to `feat` on pickup.

If `PRODUCT.md` doesn't exist, capture without the check and say so.

## Images

If the user pastes an image, save it next to the idea as `.craft/ideas/idea-<slug>-<picslug>.<ext>` (idea's basename + a short pic slug) and embed it from the idea file. On pursue, the item — and its images — move together into the queue.

## Report

One line: file created, plus the alignment note if any.
