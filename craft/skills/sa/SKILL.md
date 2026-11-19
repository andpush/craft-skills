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
- On a substantial fork, produce 2–3 genuinely different options — include one simpler than feels comfortable and, when useful, one non-obvious. Consider build vs. buy vs. integrate for substantial pieces. Recommend one option and say why it beats the others.
- Pull expensive-to-reverse decisions forward (boundaries, data ownership, contracts, consistency); cheap details can wait.
- Surface what wasn't asked: edge cases, failure modes, cheap-now/expensive-later choices.

## Lenses

- **Boundaries:** along bounded contexts (DDD): data ownership, dependencies, lifecycle, independent scaling needs, not technical layers; dependencies point toward stability (SDP).
- **Data** (needs special care): shape entities and relations based on query patterns, consistency and concurrency needs, future growth. Prefer one writer per entity.
- **Privacy:** which personal data, where every copy lives, retention and deletion, applicable regulation and residency.
- **State:** minimize the state space: derive rather than store, make illegal states unrepresentable; model state machines where a wrong transition is costly.
- **Contracts:** additive vs breaking; compatibility and versioning; errors; sync vs async, retries, idempotency, ordering, timeouts, partial failure of externals.

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
