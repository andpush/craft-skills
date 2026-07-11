---
name: audit
description: Deep audit of the entire repo (not a diff review) - structure, maintainability, security.
---

## Audit goal

Review the entire repo, not just recent changes, no sampling.
Goal: cleanup, improve maintainability, remove duplications and dead code. It is important to keep it simple and logical. Flag any unjustified complexity and suggest a simpler alternative.

## Audit process

Look at different angles and levels:

### 1. Architectural
Start with `ARCHITECTURE.md`, readmes, config, dir tree. Explore the major components, their boundaries and interaction. Their API contracts and boundaries should be adequate to minimize tangling, ensure clear responsibilities, consider security and scalability challenges. Watch dependencies: flag circular and avoidable ones.

Ensure tech stack is adequate, external dependencies and indirection layers are justified. Flag reinventing the wheel, promote reuse of existing proven solutions, grep/skim for repeated patterns, collect duplication suspects, identify areas of focus for the detailed review.

Make sure the architecture is consistent within repo and with docs. Flag inconsistencies, note whether it is the code or doc to be updated.

### 2. Detailed Analysis
Perform each major component review. List findings and per-component quality score.
- For large repos -> fan out read-only subagents partitioned by territory. Give each: its directory scope, the audit goals above. Each reports its slice in 5 dimensions {arch design, code issues, test suite coverage and quality, security, performance (clear-cut issues only) }, backed by `file:line` and snippets. Consolidate in the main context.
- Small, flat, or tangled repo -> do the same in a single pass.


## Report
Prioritize findings with `file:line` and a concrete minimal fix each if possible. Uncertain findings go in a separate section.

Quality score 1–10 per component and overall, where 10 = nothing to fix,
7 = minor cleanup, 5 = notable debt slowing changes, 3 = structural problems/unmaintainable/complete redesign pending.
One sentence of justification each.

Change no code; the only file you write is the report: `docs/audit-YYYY-MM-DD.md`, unless the user specified otherwise.