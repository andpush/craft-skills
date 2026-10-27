<!--
The skeleton `arch` writes at AGENTS.md — always loaded by every agent, so ≤60 lines.
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

<3–7 lines, the ones an agent would break without knowing. Each links its source by ID.>
- Only `orders` writes orders data (R2).
- Never edit a committed migration; add a new one.

## Workflow

- Work items: `docs/ideas/` → `docs/ready/` → `docs/done/`, named `<type>-<slug>.md`.
- One branch per item: `craft/<item>`. The branch is the claim.
- Merge: pr          # pr | local
- Auto-merge: off    # off | green — green merges 🟢 changes by itself once CI passes

## Pointers

- Product: PRODUCT.md
- Architecture: ARCHITECTURE.md (prose, glossary) · architecture.yaml (the model) · docs/adr/
- Conventions: ARCHITECTURE.md § Rules and Conventions
