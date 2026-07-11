---
name: arch
description: Use to define or derive project architecture - into a durable `ARCHITECTURE.md` that the `spec` skill can rely on.
---

Establish the durable engineering context for a software project — architecture, component/module map, tech stack, and coding conventions — either by defining them with the user (greenfield) or deriving them from existing code (brownfield).

Produces or updates `ARCHITECTURE.md`, which `spec` consumes. Run once or after foundations change.

## Initial context

Refer to `PRODUCT.md` and root `README.md` for context on WHAT we build. If both are missing or placeholder — offer to **Establish product context now** — run `prod` skill in this session, then continue with `arch`.

Never invent product purpose, users, or constraints from architecture preferences alone.

Map the well-known files. If the repo already contains conventions (e.g. `rules*.md`), reference them from `ARCHITECTURE.md` instead of restating.

Load [reference/architecture-template.md](reference/architecture-template.md) as a guide for the architecture context structure.

## Greenfield: define with the user

1. Understand the product purpose, users, constraints.

2. Propose architecture and stack — design per the `sa` skill ([../sa/SKILL.md](../sa/SKILL.md)): start simple, iterate arch↔stack to coherence, options on substantial forks.
   - Present the forks to the user. Don't bikeshed settled defaults; riskier decisions are closer to data and API boundaries. Examples of real forks: monolith vs. services, pre-built vs. bespoke, paid vs. open-source, relational vs. object, message queue vs. database, persistent vs. in-memory.

3. **Write `ARCHITECTURE.md`** in collaboration with the user, link to existing docs instead of restating them.

4. **Seed `Rules and Conventions`** from [reference/conventions-seed.md](reference/conventions-seed.md). Take only the sections that fit the chosen stack, adapt with the user, keep only the non-obvious or project-specific.

## Brownfield: derive from the code, then confirm

1. **Explore the codebase:**
- Orient first (`PRODUCT.md`, `README.md`, layout, config, dir tree);
- Large repo -> fan out `Explore` agents partitioned by territory, each reports its slice along fixed dimensions — purpose, entry points & boundaries, data, external calls, conventions & tests, backed by `file:line` and snippets. Consolidate in the main context
- Small, flat, or tangled repo -> do a single pass yourself, reading code and taking notes.
2. Draft `ARCHITECTURE.md` ([reference/architecture-template.md](reference/architecture-template.md)) describing the system as it is.
3. Never leave an agreed decision unwritten. Surface questionable parts as findings — don't discard working decisions. Suggest parking improvements using `idea` skill.
4. Confirm with the user, then write `ARCHITECTURE.md`, including a `Rules and Conventions` section for the patterns and practices the code already follows.
5. If README restates structure, slim it to a pointer to `ARCHITECTURE.md`.

## Architecture quality checklist

Before writing, verify the design against the `sa` skill's Verify checklist — boundaries graspable, acyclic dependencies, one owner per datum, trade-offs stated, complexity matched to scale.

Report whether `ARCHITECTURE.md` was created vs. adopted and the next step (`/spec <first feature>`). A few lines.
