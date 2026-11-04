---
name: sa
description: Use to design a technical solution — the architecture of a system, component, or change - decompose, weigh options, choose the tech stack and approach.
---

Construct a solid technical solution: a chosen approach with rationale. The design is the deliverable; caller skills (`arch3`, `spec`) may decide what to document.

## Ground

- Anchor in reality: `docs/PRODUCT.md` and `docs/architecture.yaml` if present, the existing stack, the code as it is.
- Read the decision history before proposing: `docs/adr/` titles, and grep `## Rejected` for each option you consider. A rejected option comes back only when its "revisit if" holds — say which.
- Name the drivers before designing: core function, dominant quality attributes, hard constraints, scale. Design against them, not generic best practice.

## Shape

- Start simple. Every component, store, queue, or indirection layer must earn its place against a named driver.
- Architecture and stack shape each other — iterate both to coherence: propose components with preliminary tech, validate the tech against the components, refine.
- Draw component boundaries by data ownership, dependencies, lifecycle, and independent scaling needs.
- Give the data layer extra care: entities, relations, and a store choice justified by query patterns, consistency needs, and volume.
- On a substantial fork, produce 2–3 genuinely different options — include one simpler than feels comfortable and, when useful, one non-obvious. Consider build vs. buy vs. integrate for substantial pieces. Recommend one option and say why it beats the others.
- Pull expensive-to-reverse decisions forward: data ownership and source of truth, component boundaries and contracts, state and lifecycle, consistency model, sync vs. async. Cheap-to-change details can wait.
- Surface what wasn't asked: edge cases, failure modes, cheap-now/expensive-later choices.

## Lenses

Load only the lens the change touches:
- [reference/domain.md](reference/domain.md) — components, aggregates, boundaries, state
- [reference/data.md](reference/data.md) — owners, writers, copies, stores
- [reference/interactions.md](reference/interactions.md) — APIs, events, idempotency, externals
- [reference/migrations.md](reference/migrations.md) — schema and contract changes, temporary code

## Verify

- [ ] Boundaries: each unit graspable without reading its internals; internals can change without breaking consumers.
- [ ] Dependency graph acyclic; every shared datum has one owner.
- [ ] Trade-offs of the chosen approach stated explicitly; stack choices concrete, with specific versions where they matter.
- [ ] Security, deployment, testing, observability addressed where the drivers demand them.
- [ ] Complexity matches the problem's actual scale — no speculative generality.

End with the chosen approach, its rationale, and any decisions still open for the user. What happens next — a spec, `architecture.yaml`, direct build — belongs to the caller.

An expensive-to-reverse decision becomes an ADR only on the user's explicit yes, in the format of [reference/adr.md](reference/adr.md): written now when there's no build, or listed in the spec for `build3` to write at close.
