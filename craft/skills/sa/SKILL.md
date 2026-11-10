---
name: sa
description: Use to design a technical solution — the architecture of a system, component, or change - decompose, weigh options, choose the tech stack and approach.
---

Construct a solid technical solution: a chosen approach with rationale. The design is the deliverable; caller skills (`arch3`, `feat`) may decide what to document.

## Ground

- Anchor in reality: `PRODUCT.md` and `.craft/architecture.yaml` if present, the existing stack, the code as it is.
- Read the decision history: `.craft/adr/`
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

Consider what the change touches; decide from the use case, not by default:
- **Boundaries:** modular monolith unless a named driver demands a split; cut around data and its rules, not layers; dependencies point toward stability, no cycles.
- **Data:** one writer per entity, including scripts and admin tools; each copy named (snapshot, replica, projection, cache) and rebuildable from its owner; one relational store per deployable unless a query pattern demands otherwise; deleting personal data reaches every copy.
- **State:** explicit lifecycles only where an illegal transition costs money or trust.
- **Concurrency:** concurrent writers, lost updates, locking.
- **Contracts:** additive vs breaking; compatibility and versioning; errors are part of the contract.
- **Delivery:** sync vs async, retries, idempotency, ordering, timeouts, partial failure of externals.
- **Evolution:** expand/contract, old and new versions running side by side during a deploy, roll forward; temporary code gets an `idea-remove-<slug>.md` with its removal condition.
- **Modules:** deep over shallow; no interface without a second implementation or a test seam.

## Challenge the design

Answer applicable questions yourself; raise with the user only an answer that changes the design.
- Is there a simpler cut with fewer components that meets the same drivers?
- Will the next ordinary change touch one component or three?
- What breaks if this component is down for ten minutes?
- What if this message arrives twice? Out of order? Never?
- The callee succeeded but the caller timed out: what state is left, and what does a retry do?
- Can this deploy stop halfway without harm?

## Verify

- [ ] Boundaries: each unit graspable without reading its internals; internals can change without breaking consumers.
- [ ] Dependency graph acyclic; every shared datum has one owner.
- [ ] Trade-offs of the chosen approach stated explicitly; stack choices concrete, with specific versions where they matter.
- [ ] Security, deployment, testing, observability addressed where the drivers demand them.
- [ ] Complexity matches the problem's actual scale — no speculative generality.

End with the chosen approach, its rationale, and any decisions still open for the user. What happens next — a spec, `architecture.yaml`, direct build — belongs to the caller.

An expensive-to-reverse decision becomes an ADR only on the user's explicit yes, in the format of [reference/adr.md](reference/adr.md): written now when there's no build, or listed in the spec for `build3` to write at close.
