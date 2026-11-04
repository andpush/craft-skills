<!--
The skeleton `arch3` writes at AGENTS.md — always loaded by every agent, so ≤60 lines.
Pointers, commands and invariants only; everything else lives in the docs it points to.
CLAUDE.md contains a single line: @AGENTS.md
-->

# <system>

<One line: what it is and for whom. Details: PRODUCT.md.>

## Commands

- verify: `<one command: build, lint, tests, architecture checks>`   ← `guard` sets this
- AC command: `<runner filter AC1_>`
- run: `<…>`
- <other commands an agent needs and can't guess>

## Invariants

<3–7 lines, the ones an agent would break without knowing. Each names its rule or note.>
- Only `orders` writes orders data (`orders-single-writer`).
- Never edit a committed migration; add a new one.

## Workflow

- Work items: `.craft/ideas/` → `.craft/ready/` → `.craft/done/`, named `<type>-<slug>.md`.
- One branch per item: `craft/<item>`. The branch is the claim.
- Merge: 🟢 changes merge to local main by themselves; 🟡 and 🔴 wait for a human.
- History: each item is one merge commit on main; use `--first-parent` for log and bisect.
- Sync with the remote, by a human or on request: `git pull --no-rebase`, run verify and fix anything red, `git push`.

## Pointers

- Product: PRODUCT.md
- Architecture: .craft/architecture.yaml (read its `notes` before changing what they're about) · .craft/adr/
