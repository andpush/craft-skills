# Lens: interactions and contracts

Load when a change adds or changes an API, an event, a message consumer, or a call to an external.

## Contracts

- A public API or event is a contract with consumers you may not control. Additive changes are safe
  (optional field, new endpoint). Removing, renaming, making a field required, or changing what a
  value means is breaking — version it or run both shapes during a migration.
- Write the contract down where tools read it: OpenAPI, proto, GraphQL schema, AsyncAPI or a typed
  event class. A contract that exists only in code review is not a contract.
- Errors are part of the contract: status codes, error shapes, which ones are retryable.

## Sync or async

- **Sync** when the caller needs the answer to continue and both sides share an availability budget.
- **Async** when the caller only needs "it will happen", when the work is slow, or when the callee's
  outage must not fail the caller.
- **Accepted ≠ completed.** An async request returns "accepted" with an id; the caller learns the
  outcome later (poll, callback, event). Never return success for work that hasn't happened.

## Delivery

- Assume **at-least-once** delivery and retries everywhere. Every consumer and every mutating
  endpoint that can be retried is **idempotent**: an idempotency key or a natural key, stored with
  a unique constraint, checked in the same transaction as the effect.
- **Outbox:** to change state and publish an event reliably, write the event to an outbox table in
  the same transaction, and publish from there. Never "save, then publish" in two steps.
- **Ordering:** don't rely on it unless the transport guarantees it per key. Use versions or
  timestamps so a consumer can drop a stale message.
- **Retries:** bounded, with backoff and jitter; a dead-letter destination; an alert on it.
- **Timeouts** on every outbound call, shorter than the caller's own deadline.

## Externals

- Each external sits behind one component (`calls` in the model). Its client never leaks into
  other components.
- Decide the failure behavior up front: fail, degrade, or queue and retry. Partial failure — the
  external did the work but the response was lost — needs reconciliation or an idempotent retry.

## Questions to ask

- What happens if this message arrives twice? Out of order? Never?
- What does the caller do when the callee times out after succeeding?
- In a multi-step operation, if one step succeeds and the next fails, what state is left, and
  what does a retry with the same input do?
- Which consumers break if this field changes, and how will we find out before they do?
