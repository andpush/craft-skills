# Complex systems × AI — idea bank

## Target

- Less code reading; preserve intent across sessions; local changes; low ceremony.
- Human defines initial model; model becomes maintenance memory + AI context + verification contract.
- Matt Pocock workflow + architecture contracts + deterministic checks. One workflow; selected specialist skills.
- Success: less context/review effort; fewer regressions; smaller change radius. Not LOC/test/finding counts.

## Why decay

- Local task success beats system invariants; rationale lost; bad patterns copied; complexity accumulates.
- Tests repeat implementation assumptions; passing build ≠ sound architecture/security.
- Wrappers/options persist; coupling makes ordinary changes spread.

## Architecture model

- Three views: intended architecture / extracted implementation / conformance diff.
- Intent never silently rewritten to match code. Drift → fix code, correct stale description, or explicit decision.
- One authority per fact; generated views non-authoritative. Stable IDs → code, schema, tests, ADRs.
- Small always-loaded map; relevant context contracts + adjacent interfaces loaded on demand.
- Glossary = meaning; ADR = non-obvious tradeoff + consequences; contracts = current obligations.
- Existing formats first; thin linking layer; custom DSL only for demonstrated gaps.
- Same model → visuals, checks, AI instructions. Avoid independent diagram/checker definitions.
- Deterministic generation: interfaces/schemas/checker configs/diagrams. AI generation: implementation within contracts; verify separately.
- Model useful throughout maintenance, not just initial generation. Contract diff = review surface.

## DDD / boundaries

- Ubiquitous language per bounded context; same term may differ across contexts.
- Context ≠ package ≠ service ≠ deployment ≠ database; explicit mapping.
- Aggregate from atomic invariants, not ORM graph/UI shape. Mutations through invariant-preserving operations.
- Cross-aggregate work: coordinator, consistency, recovery. One transaction/aggregate = heuristic.
- Translate external models at boundaries; distinguish domain/integration events.
- Deep modules: small complete interface, hidden complexity, local reasoning, contract-level tests.
- No interface-per-class ritual; abstractions earn cost by hiding complexity or isolating variation/effects.
- Modular monolith viable; services require operational justification. Narrow shared kernel; no universal shared model.

## Module / operation contract

- Responsibility; exports; visibility; allowed consumers; direct/transitive dependencies; forbidden edges.
- Inputs/outputs/errors; units/ranges/null semantics; pre/postconditions; invariants.
- Owned state; reads; modifies; external effects; lifetime; cancellation; concurrency; cost bounds.
- Visibility ≠ dependency permission ≠ effect permission.
- `in` ≠ pure; immutable reference ≠ immutable object; readonly ≠ deep immutability.
- Capability-style dependencies: pass required resource access, not global service locator.
- Pure decision logic + explicit effect boundary where useful.

## Data authority / lineage

- Authority per business fact/attribute/context/time meaning; not blanket “master Customer”.
- Declare meaning/type, origin/trust, transformations, authority, writers, copies, freshness, retention/deletion, reconciliation/rebuild.
- Distinguish authority / replica / projection / cache / historical snapshot.
- Snapshot = fact-at-time; must not automatically follow current source.
- Denormalization intentional; each copy has purpose + sync/recovery policy.
- Multiple writers require conflict protocol. No accidental cross-context writes.
- Derived values retain lineage; externally asserted vs internally verified values distinguishable.

## API / async

- Runtime validation at external boundary; static types insufficient. Transport DTO ≠ ORM entity.
- Auth: subject/action/resource/tenant; all entry paths incl. jobs/admin.
- Contract includes errors, effects, atomicity, idempotency, timeout, cancellation, limits, compatibility.
- Accepted ≠ completed; timeout ≠ failed; unknown outcome → operation ID + status/reconciliation.
- Local tasks: owner/lifetime, cancellation, error propagation, bounded concurrency; no orphan fire-and-forget.
- Messages: command vs fact vs query; schema/version; producer/consumers; event/correlation IDs.
- Declare delivery, ordering scope, duplicates, retry/backoff/budget, dead-letter handling, replay, backpressure.
- Outbox connects durable write/publication; consumer dedupe still needed.
- Idempotency: key scope, payload mismatch, retention, atomic effect/result recording; test concurrent duplicates.
- No assumed end-to-end exactly-once. Compensation ≠ rollback; durable process state; manual recovery path.
- Projection lag measurable; stale reads acceptable only per contract.
- Trace business operation across calls/events/retries; queue age + projection lag, not errors alone.

## SQL / evolution

- Schema/table owner + permitted readers/writers; shared DB ≠ shared ownership.
- Constraints near data: nullability, uniqueness, FK, valid values; application-only checks race.
- Explicit isolation/versioning/locking; test lost updates, double execution, write skew where relevant.
- Migrate: expand → controlled writes → resumable backfill → reconcile → switch reads → contract.
- Mixed-version compatibility; lock/load budget; stop/recover/roll-forward plan. Down migration ≠ data recovery.
- Temporary dual writes/flags/adapters: owner + removal condition.

## Verification / security

- Rule: ID, intent, scope, rationale, severity, checker, exceptions, result + code/rule revision.
- Structural analysis / schema compatibility / DB permissions / contract tests / property tests / model checks / runtime signals.
- Distinguish passed-in-scope / violated / not checked. Unsupported, skipped, empty selection ≠ pass.
- Deliberately violate rules to verify checkers. Model proof ≠ implementation proof; tests ≠ exhaustive proof.
- Negative cases: other user/tenant, revoked rights, duplicates, reordering, concurrency, partial failure.
- AI cannot quietly weaken tests/rules, widen exclusions, refresh debt baseline.
- Existing debt baseline; no new violations; exceptions: rationale + owner + revisit trigger.
- Least-privilege DB/service access; preserve tenant identity across jobs/events; protect secrets/logged data.

## Review / complexity

- Human reviews contract changes + impact + evidence; drills into risky code.
- Local change: automate/sample. New API/dependency/copy/event: architecture diff. Auth/authority/transactions/migration: deeper review.
- Packet: behavior delta; boundaries; new state/effects; data ownership; failure/retry; compatibility; evidence; unknowns; decision needed.
- Independent adversarial reviewer: requirements + contracts + diff + surrounding code; seek reproducible counterexample.
- Finding: location → invariant → scenario → consequence → minimal fix. Zero findings valid.
- Two lenses: correctness/security + maintainability/change cost. Recheck fixes; periodic whole-context review.
- Track trends: cycles, new edges, change radius, co-change, churn×complexity, API growth, states/flags, duplicated rules, multiple writers.
- Metrics = investigation signals; formatting/large commits distort co-change. No universal quality score.
- Ask: which next ordinary task became harder? Remove obsolete paths before adding another mode.

## Visuals

- C4 context/container → orientation; context map → semantics/ownership.
- Sequence incl. failure → operation; state machine → lifecycle; ER + authority → data.
- Dataflow + trust boundaries → security; deployment → runtime; dependency matrix → dense coupling.
- One question/level per view; labeled edges; drill-down; intended vs actual; before/after diff.
- Distinguish checked/unverified, authority/replica/snapshot. Link node/rule → code + evidence.

## Language leverage / limits

| Language | Use | Watch |
|---|---|---|
| Java | module/package visibility, explicit APIs, ArchUnit | final/record ≠ deep immutable; reflection/runtime edges |
| Kotlin | module/internal, sealed states, structured coroutines; JVM ArchUnit | val/read-only collections ≠ immutable; suspend ≠ pure/nonblocking/background |
| Dart | libraries/exports, private `_`, analyzer/import rules, task ownership | library-scoped privacy; final ≠ immutable; show/hide ≠ global access policy |
| Swift | targets/modules, value semantics, actors/Sendable | nested references; actor state may change across await |
| Rust | crates/modules, ownership/borrowing, Result/enums | interior mutability; memory safety ≠ business/effect guarantees |
| TS | strict unions, domain IDs, runtime schemas, dependency-cruiser | erased types; any/assertions; shallow readonly |
| SQL | constraints, roles, transactions, safe migrations | engine/isolation-specific; races; cross-row invariants |

## Proposed skills

- `domain-contract`: glossary, context/aggregate boundaries, invariants, public operations.
- `data-authority`: facts, origins, writers, copies, freshness/rebuild/deletion.
- `interaction-contract`: API/events, effects, compatibility, retries/order/failure.
- `architecture-impact`: intent/actual diff; affected consumers; minimal human review packet.
- `architecture-check`: checkers; validate coverage; expose skipped rules; protect constraints.
- `evolution`: migrations, exceptions, cleanup, ADR replacement, session handoff.
- Loop: locate owner → load contracts → assess delta → implement → verify/review → update affected records.

## Sources / building blocks

- [Matt skills](https://github.com/mattpocock/skills): domain-modeling, codebase-design, improve-codebase-architecture, wayfinder.
- [wshobson](https://github.com/wshobson/agents): selective API/architecture/CQRS/projection/saga/workflow guidance.
- [DDD skills](https://github.com/TU-hayaoki/ddd-agent-skills), [luckys](https://github.com/luckys/agent-skills): detailed material; small projects; adapt critically.
- [OpenSpec](https://github.com/Fission-AI/OpenSpec): evolving specs/change records; architecture policy still needed.
- [ArchUnit](https://www.archunit.org/userguide/html/000_Index.html), [dependency-cruiser](https://github.com/sverweij/dependency-cruiser): mechanical boundaries.
- [Structurizr](https://docs.structurizr.com/dsl), [LikeC4](https://likec4.dev/): model→views; conformance requires integration.
- [EventCatalog](https://www.eventcatalog.dev/): domains/services/messages/schemas/owners; architecture context for agents.
- [archagent](https://github.com/BenedatLLC/archagent): model→checks experiment; inspect [implemented checks](https://github.com/BenedatLLC/archagent/blob/main/docs/CHECKING.md).
- TypeSpec/OpenAPI/AsyncAPI: interfaces; XState: executable states; Temporal: durable workflows; Cedar: access policies.
- SPARK/Dafny: contract/frame-condition inspiration; Koka: effects; Quint/TLA+: critical protocol models. Specialized, not default stack.
- BMad/Spec Kit: too ceremonial for preferred workflow. Superpowers: useful execution discipline, limited architecture focus.
- Tool observations from discussion, Oct 2026; capabilities/adoption require rechecking before selection.

## First experiment

- One changing context; real feature; 5–10 useful rules; data authority registry; one visual view.
- Seed forbidden dependency + unauthorized writer + duplicate delivery; expose violations/coverage gaps.
- Compare context read, clarification count, review effort, change radius, defects. Expand where benefit demonstrated.
- Core opportunity: compact, versioned, checkable + visualizable architecture contract; long-term maintenance first.
