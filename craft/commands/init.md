---
description: Run `prod` then `arch` skills to quickstart with `PRODUCT.md` and `ARCHITECTURE.md`.
argument-hint: [one-line idea or repo note]
---
# Command Instructions

Establish this project's durable context in one sitting by running two craft skills back to back. Aimed at small or fresh projects — keep both docs minimal and move fast; surface only the decisions that are expensive to reverse, don't over-elaborate.

## Context

Optional seed from the user: $ARGUMENTS — a one-line product idea, a pointer to existing material, or nothing. Treat it as a starting point, not the final answer.

Greenfield (empty/early repo) → define with the user. Brownfield (existing code) → derive, then confirm. Each skill detects which mode applies.

## Task

1. Run the `prod` skill to establish `PRODUCT.md`.
2. Then run the `arch` skill to establish `ARCHITECTURE.md`.

Scale to a small project: a quick problem/users/scope pass for product, a simple stack/components/conventions pass for architecture. Don't manufacture process the size doesn't warrant.

When both exist, stop and point the user at `/spec <first feature>` as the next step.

For a larger or evolving project, prefer running `/prod` and `/arch` separately so each can be revisited on its own.
