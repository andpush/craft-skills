# architecture.yaml — the model

One file at the repo root that checks (`guard`), pages (`view`) and review tooling (`review`) read.
`ARCHITECTURE.md` explains it in prose and links to it; it never restates it.

```yaml
system: shop
does: sells catalog products online; one team, one deployable

external:                   # context: who and what sits outside
  customer: {does: browses and orders, calls: [api]}   # calls = inbound; drawn as an actor
  payments: {does: card authorization (Stripe)}        # reached through a component's depends_on

components:
  orders:
    does: order lifecycle, idempotent submission     # one line
    path: src/orders                                 # string or list of paths/globs
    depends_on: [catalog, shared, payments]          # allowed dependencies (components or externals); anything else is a violation

entities:                   # main ones only; fields live in code
  Order:
    owner: orders           # the only writer
    has: [OrderLine]        # same owner — one aggregate
    states:                 # only when the lifecycle matters
      - draft -> submitted: submit
      - submitted -> paid: payment authorized
  OrderLine:
    owner: orders
    refs: [Product]         # by id, may cross owners
    copies: [Product.price: snapshot — price at purchase]   # replica | projection | cache | snapshot

flows:                      # one or two main success paths
  submit order:
    - customer -> api: POST /orders
    - api -> orders: submit(cart, key)
    - orders ~> notify: OrderSubmitted      # ~> async; -> calls must follow depends_on

rules:                      # what the model can't express
  - id: R3
    level: MUST             # MUST | SHOULD
    scope: "src/*/domain"   # component name or path glob
    rule: no framework annotations
    checked_by: ArchitectureTest.R3   # or: manual  (manual rules go to review's checklist)
    exceptions: baseline              # optional: baseline | ADR slug

review_triggers:            # project paths that make a change red; built-in defaults cover manifests, migrations, OpenAPI, CI, auth
  schema: [db/migration/**, "**/*.sql"]
  api: [src/api/**, "**/openapi*.yaml"]
```

## What goes in

Every section is optional, one line per thing. The test for adding anything: would a reader
otherwise have to reconstruct it from code, **and** can a check catch it drifting? Fields,
endpoints and secondary flows stay in code and tests.

- **Components** cover all production code: every source file belongs to one component's `path`.
  A small shared kernel (`shared`) is fine; a `utils` everyone depends on is a smell.
- **I/O placement is derived,** not declared: persistence only in components that own an entity,
  HTTP/messaging clients only in components whose `depends_on` lists an external, server code only
  in components an external `calls`. Something rarer (clock, filesystem, queues) is a rule line.
- **Entities:** the ones a newcomer must know, with their owner. `states` only for a lifecycle
  where an illegal transition costs money or trust.
- **Flows:** the one or two paths that explain the system. Sync calls (`->`) must be allowed by
  `depends_on` or `calls`; async (`~>`) don't.
- **Rules** have stable IDs. `MUST` needs a `checked_by` that `guard` wrote; a rule no tool can
  check is `SHOULD` with `checked_by: manual`. The reason for a rule is one clause in
  `ARCHITECTURE.md` or an ADR link, by rule ID.
- **Review triggers** extend built-in defaults (dependency manifests, migrations, OpenAPI/proto/
  GraphQL, auth paths, CI config, arch-check files). Add the project's own schema and API paths.

## Syntax

- Arrow items (`a -> b: label`) need quotes only when the label contains `: `.
- Globs starting with `*` need quotes.

## Validate

```bash
uv run --quiet <arch-skill-dir>/../view/scripts/view.py model
```

Model problems show on top of the page and are printed, with a non-zero exit: unknown names, components without a path, `has` across
owners, flow calls `depends_on` doesn't allow, `MUST` rules without a checker. Fix them all.
