---
name: arch-view
description: Use to show the project's architecture as one HTML page in the browser — system map, notes, components, endpoint exposure, data ownership, lifecycles, main flows, rules, the ADR decision timeline and findings — rendered from `docs/architecture.yaml` for a quick human review.
---

A script renders the page deterministically from `docs/architecture.yaml` and `docs/adr/`. Run it and
report; leave reading the model and writing HTML to the script.

```bash
uv run --quiet <this-skill-dir>/scripts/render.py [docs/architecture.yaml]
```

It writes `<tmp>/craft-views/arch-<system>.html`, prints the path and the count of model problems,
and opens the browser. Flags: `--no-open`, `--out <file>`. No `docs/architecture.yaml` → offer the
`arch-define` skill.

The page, top to bottom:
- **Header:** system, summary, tech, actors, counts, and model problems from `arch-define`'s validator.
- **System map:** actors, components, datastores, queues and external systems, with calls (labelled
  by endpoint), messages, writes and reads.
- **Components:** one full-width card each, with jobs, tech, endpoints, ui endpoints, relations, and
  a module diagram: what each module does, who calls the endpoints it serves, and labelled arrows to
  what it uses, calls, stores and publishes.
- **Data:** a keys-and-references map across stores; per store, every entity with who writes and
  reads it; per queue, who produces and consumes each message.
- **Lifecycles** as state diagrams, **main flows** as sequence diagrams with one lifeline per
  component and modules on the arrow labels, **rules**, **glossary**.
- **Decisions:** ADRs as a timeline, with current vs superseded status and rejected options drawn as
  abandoned side branches, each with its "revisit if".

Report in one or two lines: the page is open, plus the model problems count when non-zero. Fix
model problems with `arch-define`. A `Diagram error` on the page is a renderer bug: fix it in
`render.py`.
