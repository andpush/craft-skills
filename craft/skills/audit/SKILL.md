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
Start with `.craft/architecture.yaml`, readmes, config, dir tree. Explore the major components, their boundaries and interaction. Their API contracts and boundaries should be adequate to minimize tangling, ensure clear responsibilities, consider security and scalability challenges. Watch dependencies: flag circular and avoidable ones.

Ensure tech stack is adequate, external dependencies and indirection layers are justified. Flag reinventing the wheel, promote reuse of existing proven solutions, grep/skim for repeated patterns, collect duplication suspects, identify areas of focus for the detailed review.

Make sure the architecture is consistent within repo and with docs. Flag inconsistencies, note whether it is the code or doc to be updated.

### 2. Conformance — when `.craft/architecture.yaml` exists

Deterministic first; these findings need no judgment:
- **Architecture vs code:** run `verify`, then compare the code with `architecture.yaml` for what the checks can't see. Each difference is a finding; deciding them is `arch` reconcile, run by the user.
- **Architecture validity:** `uv run --quiet <this-skill-dir>/../arch/scripts/validate.py .craft/architecture.yaml` prints problems and exits non-zero on errors. Its deficiencies and improvements are findings.
- **Rule coverage:** every `must` rule has a `check` that exists and went red at least once (`guard` proves it). A rule without one that a tool could check is a finding.
- **Baseline:** its size and trend (`git log` on the baseline file). A growing baseline is a finding.
- **Doc drift:** `README.md`, `AGENTS.md`, `PRODUCT.md` and the `notes` in `architecture.yaml`: claims that the code or `architecture.yaml` contradicts. Say which side is wrong; never rewrite intent to match code.
- **Budgets:** `README.md` ≤100 lines, `PRODUCT.md` ≤150; `AGENTS.md` starts with `@README.md`, `CLAUDE.md` contains `@AGENTS.md`.
- **Hotspots:** churn × size. Files changed most in the last six months (`git log --since=6.months --format= --name-only | sort | uniq -c | sort -rn | head -20`), weighed by length or complexity. A big file that changes often is where the next bug is.

### 3. Detailed Analysis
Perform each major component review. List findings and per-component quality score.
- For large repos -> fan out read-only subagents partitioned by territory. Give each: its directory scope, the audit goals above. Each reports its slice in 5 dimensions {arch design, code issues, test suite coverage and quality, security, performance (clear-cut issues only) }, backed by `file:line` and snippets. Consolidate in the main context.
- Small, flat, or tangled repo -> do the same in a single pass.


## Report
Write `.craft/findings/audit-<YYYYMMDD>-<N>.md` ([template](../arch/reference/findings-template.md)): quality scores first, then findings, highest severity first, each with `file:line` and a concrete minimal fix where possible. When only the user can tell whether something is a problem, record it as a `question`.

Quality score 1–10 per component and overall, where 10 = nothing to fix,
7 = minor cleanup, 5 = notable debt slowing changes, 3 = structural problems/unmaintainable/complete redesign pending.
One sentence of justification each.

Change no code; the findings file is the only file you write, unless the user specified otherwise.