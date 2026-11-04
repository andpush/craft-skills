# Lens: migrations and evolution

Load when a change alters a schema, a stored format, a contract, or replaces a component.

## Expand / contract

Never change a shape in place while code depends on it. Split it into deployable steps:

1. **Expand** — add the new shape next to the old (nullable column, new table, new field, new
   endpoint). Old code ignores it.
2. **Backfill** — fill the new shape for existing data, in batches, idempotent, resumable.
3. **Switch** — code writes both and reads the new; then writes only the new.
4. **Contract** — remove the old shape, in a later release, once nothing reads it.

Each step ships and runs on its own. A spec lists which steps it contains; a change that contains
expand and contract together is a red flag.

## Mixed versions

During a deploy, old and new code run at the same time against the same data and the same queues.
For each step check:
- Old code against the new schema: does it break on the new column, table or enum value?
- New code against old data: does it handle rows the backfill hasn't reached yet?
- Messages written by one version and read by the other.

## Dangerous steps

- `NOT NULL` without a default on a large table; type changes; renames (they're a drop plus an add).
- Index builds that lock the table — use the database's concurrent or online option.
- Dropping a column or table in the same release that stops using it.
- Backfills in the migration transaction — run them as a separate job.

## Roll-forward

Prefer rolling forward to rolling back: a migration that dropped data can't be undone. Each step must
be safe to leave in place if the next one is delayed. State the rollback of each step, or "roll
forward only" and why.

## Temporary code

Feature flags, adapters, dual writes and compatibility shims are debt with a due date. For each one,
file an idea (`.craft/draft/idea-remove-<slug>.md`) with its removal condition: "remove after all
clients send the key" or "after backfill is verified". `build3` files these at close.

## Questions to ask

- Can this deploy be stopped halfway without harm?
- What does the old version do when it meets the new data?
- How long until the contract step, and who will remember it?
