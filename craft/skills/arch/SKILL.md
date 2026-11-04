---
name: arch
description: Use to define or derive project architecture — into `docs/architecture.yaml` (the model checks and pages read), `docs/ARCHITECTURE.md` (the prose) and `AGENTS.md` (what every agent loads), that `feat`, `guard` and `build3` rely on.
---

Establish the durable engineering context for a software project — architecture, component/module map, tech stack, and coding conventions — either by defining them with the user (greenfield) or deriving them from existing code (brownfield).

Produces or updates three files. Run once, or after foundations change:
- `docs/architecture.yaml` — the model: context, components, entities, main flows, rules, review triggers. Format: [reference/model.md](reference/model.md).
- `docs/ARCHITECTURE.md` — prose that explains the model, plus the glossary. It never restates the model.
- `AGENTS.md` — ≤60 lines every agent loads: [reference/agents-template.md](reference/agents-template.md). `CLAUDE.md` is the single line `@AGENTS.md`. If `CLAUDE.md` already has project content, propose moving it into `AGENTS.md` and confirm first.

## Initial context

Refer to `docs/PRODUCT.md` and root `README.md` for context on WHAT we build. If both are missing or placeholder — offer to **Establish product context now** — run `prod` skill in this session, then continue with `arch`.

Never invent product purpose, users, or constraints from architecture preferences alone.

Map the well-known files. If the repo already contains conventions (e.g. `rules*.md`), reference them from `docs/ARCHITECTURE.md` instead of restating.

Load [reference/architecture-template.md](reference/architecture-template.md) as a guide for the prose structure.

## Greenfield: define with the user

1. Understand the product purpose, users, constraints.

2. Propose architecture and stack — design per the `sa` skill ([../sa/SKILL.md](../sa/SKILL.md)): start simple, iterate arch↔stack to coherence, options on substantial forks.
   - Present the forks to the user. Don't bikeshed settled defaults; riskier decisions are closer to data and API boundaries. Examples of real forks: monolith vs. services, pre-built vs. bespoke, paid vs. open-source, relational vs. object, message queue vs. database, persistent vs. in-memory.

3. **Write the model, then the prose,** in collaboration with the user: `docs/architecture.yaml` first, then `docs/ARCHITECTURE.md`, which links to existing docs instead of restating them. Decisions on real forks become ADRs on the user's yes ([../sa/reference/adr.md](../sa/reference/adr.md)).

4. **Seed `Rules and Conventions`** from [reference/conventions-seed.md](reference/conventions-seed.md). Take only the sections that fit the chosen stack, adapt with the user, keep only the non-obvious or project-specific.

## Brownfield: derive from the code, then confirm

1. **Explore the codebase:**
- Orient first (`docs/PRODUCT.md`, `README.md`, layout, config, dir tree);
- Large repo -> fan out `Explore` agents partitioned by territory, each reports its slice along fixed dimensions — purpose, entry points & boundaries, data, external calls, conventions & tests, backed by `file:line` and snippets. Consolidate in the main context
- Small, flat, or tangled repo -> do a single pass yourself, reading code and taking notes.
2. Draft `docs/architecture.yaml` from the code as it is: components from the source layout, `depends_on` from the imports that actually exist, entity owners from where the persistence code is. Existing violations are findings, not reasons to bend the model — `guard` will baseline them. Then draft `docs/ARCHITECTURE.md` ([reference/architecture-template.md](reference/architecture-template.md)).
3. Never leave an agreed decision unwritten. Surface questionable parts as findings — don't discard working decisions. Suggest parking improvements using `idea` skill.
4. Confirm with the user, then write the files, including the rules the code already follows: checkable ones as `rules` in the model, the rest as prose in `Rules and Conventions`.
5. If README restates structure, slim it to a pointer to `docs/ARCHITECTURE.md`.

## Architecture quality checklist

Before writing, verify the design against the `sa` skill's Verify checklist — boundaries graspable, acyclic dependencies, one owner per datum, trade-offs stated, complexity matched to scale.

After writing, check the model by hand and fix every problem: see [reference/model.md](reference/model.md#check).

Report what was created vs. adopted, and the next step: `guard`, to make the rules executable — then `feat <first feature>`. A few lines.
