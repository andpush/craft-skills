# Lens: domain and decomposition

Load when a change adds or moves a component, an entity, or a boundary.

## Boundaries

- **Default: a modular monolith.** One deployable, components as modules with enforced
  `uses`. Split a deployable only for a named driver: independent scaling, a separate team,
  a different release cadence, or isolation of a failure or a secret.
- **Draw boundaries around data and its rules,** not around layers or technical roles. A component
  that owns no data and no rule is usually a folder, not a component.
- **A bounded context** is where a word has one meaning. When "order" means a cart in one place and
  a shipment in another, that's two contexts — name both in the glossary.
- **Dependencies point toward stability:** volatile code (UI, integrations) depends on stable code
  (domain rules), never the reverse. The graph stays acyclic.

## Aggregates from invariants

- Start from the rule that must always hold ("an order's total equals its lines"). The smallest set
  of objects that rule needs to read and change together is the aggregate. It has one owner and is
  written in one transaction.
- Other aggregates are referenced **by id** (`refs`), never held. Rules spanning aggregates are
  eventually consistent — say how (event, scheduled check), and what the user sees meanwhile.
- In `docs/architecture.yaml`: `has` for parts of the aggregate (same owner), `refs` across.

## Deep modules

- A module earns its place by hiding more than it exposes: a small interface over real logic.
  Prefer a few deep modules to many shallow ones.
- **No interface per class.** Add an interface when there are two implementations, or a boundary
  you must fake in tests (clock, network, payment gateway) — not "for testability" in general.
- Pass-through layers (controller → service → manager → repository, each one line) are cost with
  no benefit. Collapse them.
- Put the code where the change will happen: what changes together lives together.

## State

- A lifecycle that matters (payment, order, subscription) gets explicit states and transitions —
  `states` in `architecture.yaml`. Each transition has one owner, one trigger and a guard.
- Illegal transitions must be impossible in code, not just untested: one method per transition, no
  public setter for status.

## Questions to ask

- Which component is the only writer of this data?
- What breaks if this component is down for ten minutes?
- Will the next ordinary change touch one component or three?
- Is there a simpler cut with fewer components that meets the same drivers?
