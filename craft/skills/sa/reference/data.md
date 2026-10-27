# Lens: data authority

Load when a change adds an entity, a store, a copy of data, or a second writer.

## One writer

- Every entity has exactly one owner — the only component that writes it (`owner` in the model).
  Others read through the owner's interface, or hold a copy.
- A second writer is a design change, not an implementation detail. If it's truly needed, move the
  entity, or split it so each part has one writer. `guard` and `review` treat it as red.
- Shared tables between components are a second writer in disguise. A view or read replica is
  fine; a shared write path is not.

## Copies

Every copy of another owner's data is one of four kinds. Name it — `copies` in the model, with why.

| Kind | Meaning | Freshness | Example |
|---|---|---|---|
| `snapshot` | value at a moment, never updated | frozen on purpose | price at purchase |
| `replica` | full copy kept in sync | seconds–minutes | search index of products |
| `projection` | reshaped subset for one reader | eventually consistent | order summary for the dashboard |
| `cache` | disposable, rebuilt on miss | TTL | product lookup |

For each copy, answer:
- How is it updated (event, poll, rebuild) — and what happens when an update is lost?
- What does the user see while it's stale? Is that acceptable?
- Can it be rebuilt from the owner? A copy that can't be rebuilt is a second source of truth.

A snapshot is the right answer more often than people think: an invoice must show the price that
was charged, not today's price.

## Store choice

- Default: one relational database per deployable, a schema or table prefix per component.
- Choose another store only for a query pattern or volume the default can't serve, and name it.
- Consistency: what must be atomic? Keep it inside one aggregate and one transaction.

## Lineage and deletion

- Personal data: where it lives, every copy of it, and how a deletion reaches all of them.
- Derived data: which source it comes from, so a fix in the source can be replayed.

## Questions to ask

- Who is the source of truth for this field, and who only displays it?
- If this copy is wrong for an hour, who notices and what does it cost?
- Does the change create a second writer anywhere — including scripts and admin tools?
