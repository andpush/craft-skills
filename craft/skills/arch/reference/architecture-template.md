<!--
The skeleton `arch` skill produces at ARCHITECTURE.md (the canonical engineering contract).
-->

# Architecture

**Updated:** YYYY-MM-DD

## Overview

One or two lines: what the system is and its shape.
Link `PRODUCT.md` for details.

## Components

Components summary:

| Location | Component | Tech Stack | Entry point or port | DB/Storage | Deployment |
|---|---|---|---|---|---|
| … | … | … | … | … | … |

### [Component]

For each component:
    - specify responsibilities
    - define trust/ownership boundaries
    - sketch data model
    - write dev / test / deploy commands and config

## System Architecture

Visualize components interactions and the trust/ownership boundaries.
Prefer ASCII diagrams with <120 characters in width, mermaid for larger diagrams.
Include diagrams that explains architecture the best:
    - Data flow / sequence / activity view — for complex flow.
    - Entity / ERD view — for modules with persistent data.
    - State view — when state machine is central.

## Data model

The key entities and their relationships at a high level — not a full schema.
Use diagram or table view per schema.

## Architecture drivers / risks

Only constraints, risks, NFR that shape architecture: performance, security, compliance, deployment, scalability, observability, caching, reliability.

## Key decisions

Major tech choices with a one-line rationale each (and the alternative rejected, when it was a real fork). Longer-lived decisions go to `docs/adr/` — link, don't restate.

## Testing strategy

The test pyramid for this system: what's covered at unit / integration / e2e, mocking approach, tools, and how to run them.

## Open questions

- [ ] Pending decisions that affect implementation.

## Rules and Conventions

The coding conventions that aren't obvious or that this project deviates on — per stack if several, a subsection each. Keep only what matters for this system. If there are other files already define rules - do not duplicate, slim them to pointers to them.
