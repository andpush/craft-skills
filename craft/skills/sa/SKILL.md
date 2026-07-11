---
name: sa
description: Use to design a technical solution — the architecture of a system, component, or change - decompose, weigh options, choose the tech stack and approach.
---

Construct a solid technical solution: a chosen approach with rationale. The design is the deliverable; caller skills (`arch`, `spec`) may decide what to document.

## Ground

- Anchor in reality: `PRODUCT.md`/`ARCHITECTURE.md` if present, the existing stack, the code as it is.
- Name the drivers before designing: core function, dominant quality attributes, hard constraints, scale. Design against them, not generic best practice.

## Shape

- Start simple. Every component, store, queue, or indirection layer must earn its place against a named driver.
- Architecture and stack shape each other — iterate both to coherence: propose components with preliminary tech, validate the tech against the components, refine.
- Draw component boundaries by data ownership, dependencies, lifecycle, and independent scaling needs.
- Give the data layer extra care: entities, relations, and a store choice justified by query patterns, consistency needs, and volume.
- On a substantial fork, produce 2–3 genuinely different options — include one simpler than feels comfortable and, when useful, one non-obvious. Consider build vs. buy vs. integrate for substantial pieces. Recommend one option and say why it beats the others.
- Pull expensive-to-reverse decisions forward: data ownership and source of truth, component boundaries and contracts, state and lifecycle, consistency model, sync vs. async. Cheap-to-change details can wait.
- Surface what wasn't asked: edge cases, failure modes, cheap-now/expensive-later choices.

## Verify

- [ ] Boundaries: each unit graspable without reading its internals; internals can change without breaking consumers.
- [ ] Dependency graph acyclic; every shared datum has one owner.
- [ ] Trade-offs of the chosen approach stated explicitly; stack choices concrete, with specific versions where they matter.
- [ ] Security, deployment, testing, observability addressed where the drivers demand them.
- [ ] Complexity matches the problem's actual scale — no speculative generality.

End with the chosen approach, its rationale, and any decisions still open for the user. What happens next — a spec, `ARCHITECTURE.md`, direct build — belongs to the caller.
