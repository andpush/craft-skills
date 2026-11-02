---
name: arch-view
description: Use to show the project's architecture as one HTML page in the browser — system map, components, data ownership, lifecycles, main flows, rules and the ADR decision timeline — rendered from `architecture.yaml` for a quick human review.
---

A script renders the page deterministically from `architecture.yaml` and `docs/adr/`. Run it and
report; leave reading the model and writing HTML to the script.

```bash
uv run --quiet <this-skill-dir>/scripts/render.py [architecture.yaml]
```

It writes `<tmp>/craft-views/arch-<system>.html`, prints the path and the count of model problems,
and opens the browser. Flags: `--no-open`, `--out <file>`. No `architecture.yaml` → offer the
`arch-define` skill.

The page, top to bottom:
- **Header:** system, summary, tech, actors, counts, and model problems from `arch-define`'s validator.
- **System map:** actors, components, datastores, queues and external systems, with calls (labelled
  by endpoint), messages, writes and reads.
- **Components:** cards with jobs, tech, endpoints, ui, auth, relations, and modules with their dependency graph.
- **Data:** a keys-and-references map across stores; per store, every entity with who writes and
  reads it; per queue, who produces and consumes each message.
- **Lifecycles** as state diagrams, **main flows** as sequence diagrams, **rules**, **glossary**.
- **Decisions:** ADRs as a timeline, with current vs superseded status and rejected options drawn as
  abandoned side branches, each with its "revisit if".

Report in one or two lines: the page is open, plus the model problems count when non-zero. Fix
model problems with `arch-define`. A `Diagram error` on the page is a renderer bug: fix it in
`render.py`.
