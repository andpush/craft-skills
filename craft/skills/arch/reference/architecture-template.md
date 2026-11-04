<!--
The skeleton `arch` produces at .craft/ARCHITECTURE.md — prose that explains the model.
The facts (components, paths, dependencies, entities and owners, flows, rules) live in
.craft/architecture.yaml; this file says WHY and never restates them. ≤300 lines; a component
section that outgrows that moves to .craft/modules/<name>.md.
-->

# Architecture

**Updated:** YYYY-MM-DD

## Overview

One or two lines: what the system is and its shape. The model: [architecture.yaml](architecture.yaml)
(`view model` renders it). Product: [PRODUCT.md](PRODUCT.md).

## Why this decomposition

The drivers behind the component cut — data ownership, team, scaling, failure isolation — in a few
lines. What would make us cut differently.

## Components

For each component, only what the model can't say:

### <component>

- **Tech:** stack and the versions that matter; store; entry point or port.
- **Boundary:** what it hides; what it must never do.
- **Run / test / deploy:** commands and config, when they differ from the project-wide ones.

## Data

Why the owners are who they are; the copies and why each is acceptable (by entity name). Stores and
consistency choices.

## Flows

What the main flows in the model don't show: failure paths, retries, compensation.
A diagram only where it explains something the `view model` page can't.

## Architecture drivers / risks

Only constraints, risks and NFRs that shape the architecture: performance, security, compliance,
deployment, scalability, observability, reliability.

## Decisions

Major decisions live in `.craft/adr/` — list them by title with a link, one line each. Small choices
get one line here, with the rejected alternative when it was a real fork.

## Testing strategy

The test pyramid for this system: what's covered at unit / integration / e2e, mocking approach,
tools. Commands are in `AGENTS.md`.

## Glossary

Only terms that are non-obvious or mean different things in different contexts.

| Term | Meaning |
|---|---|
| … | … |

## Open questions

- [ ] Pending decisions that affect implementation.

## Rules and Conventions

Rules with IDs are in `.craft/architecture.yaml`; give the reason for each here in one clause, by ID
("R2 — orders data has one writer so totals can't diverge"). Then the coding conventions that aren't
obvious or that this project deviates on — per stack if several. If other files already define
rules, point to them instead of restating.
