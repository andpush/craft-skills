---
name: idea
description: Use to capture a user idea into .craft/draft/ — one small file with a quick alignment check against PRODUCT.md. Capture, not elaboration; the spec is written later via `feat`.
---

Capture the idea fast and move on. Ideas are candidates, not commitments — `feat` validates lazily on pickup (implement / postpone / reject). This skill only records and sanity-checks; it never opens a spec.

Optional: if the first word of the args is `high` or `low`, treat it as the priority and strip it from the idea text (e.g. `/idea low rename cat→pet`).

## Capture

Distill the idea to one line. If it's too vague to write down, ask one clarifying question — not an interview.

Write `.craft/draft/idea-<slug>.md` — one idea per file. `slug` carries the idea and is unique across `.craft/draft/`, `.craft/ready/` and `.craft/done/`. Filenames are the index — a directory listing is the scan. Format:

```markdown
---
priority: high | low      # optional — omit when unset (untriaged)
created: YYYY-MM-DD
updated: YYYY-MM-DD
target: <area>
---

# The idea in one line

Why it might matter; attached thinking the user provided, verbatim-ish.
```

`priority` is optional. Set it only if the user signals one at capture ("this matters" / "minor, someday"); otherwise omit it — an unset priority means untriaged, and `whereami` will surface it for triage. It can be added or changed by hand later. `high` = pull forward, `low` = backlog.

Don't elaborate beyond what was said.

## Lifecycle (owned by `feat`, recorded here)

An idea is born in `.craft/draft/` and stays there until picked up. With no `resolution:`, nobody has looked at it yet. On pickup:

- **Postpone** — add `resolution: postpone — <why>`; it stays in `.craft/draft/`.
- **Reject** — add `resolution: reject — <why>` and `git mv` it, with its images, to `.craft/done/`, so it isn't proposed again.
- **Implement** — `feat` or `task` writes a new item, carrying over anything still useful, images included. Delete the idea in the same commit that puts that item in `.craft/ready/`.

Quote `resolution:` if the reason contains a colon, and bump `updated`. Otherwise, deleting an idea is the user's call, never yours.

## Removal ideas

Temporary code — a feature flag, an adapter, a dual write, a compatibility shim — gets an idea when it's introduced (`build` files these at close): `idea-remove-<slug>.md`, `priority: high`, with the removal condition as the body's first line — `Remove when: all clients send the key`. `whereami` surfaces them; they're debt with a due date, not candidates.

## Check alignment

Skim `PRODUCT.md`. If the idea conflicts with it or falls outside scope, tell the user in one line and record the tension in the file — still capture it. No resolution: that belongs to `feat` on pickup.

If `PRODUCT.md` doesn't exist, capture without the check and say so.

## Images

If the user pastes an image, save it next to the idea as `.craft/draft/idea-<slug>-<picslug>.<ext>` (idea's basename + a short pic slug) and embed it from the idea file. On implement, the new item takes over the images it needs, renamed to its basename.

## Report

One line: file created, plus the alignment note if any.
