---
name: view
description: Use to show a spec, a change review, or the architecture model as an HTML page in the browser, so a human can skim and approve instead of reading markdown. `spec` calls it before approval, `build3` after a build; also on request ("show me the spec / the change / the architecture").
---

Show, don't make the human read. A script renders the page deterministically — never hand-write the HTML, and never put the output in the repo.

## Run

The script lives in this skill's directory; `uv` resolves its one dependency (PyYAML):

```bash
uv run --quiet <this-skill-dir>/scripts/view.py spec   docs/ready/<item>.md
uv run --quiet <this-skill-dir>/scripts/view.py change docs/ready/<item>.review.json   # or docs/done/
uv run --quiet <this-skill-dir>/scripts/view.py model                                  # architecture.yaml
```

It writes `<tmp>/craft-views/<kind>-<name>.html`, prints the path and opens the browser. Flags: `--no-open`, `--model <file>`, `--spec <file>`, `--repo <dir>`, `--editor vscode|cursor|idea|none` (default `$CRAFT_EDITOR` or `vscode`; makes `file:line` links open in the IDE).

## What the pages read

Pages are only as good as their sources. When writing those sources, keep them renderable:

- **Model** — `architecture.yaml` at the repo root (`system`, `does`, `external`, `components`, `entities`, `flows`, `rules`, `review_triggers`) and the ADRs in `docs/adr/`. The page shows context, decomposition, entities by owner, lifecycles (`states`), main flows as sequences, and the decision timeline (ADR title, `## Rejected` bullets as branches, `supersedes`). Model problems are listed on top: unknown names, missing paths, `has` across owners, flow calls that `depends_on` doesn't allow, MUST rules without a checker.
- **Spec** — frontmatter `target:` lists component names from the model (highlighted in the diagram). The `## Review Brief` section is shown first; inside it, contract changes as a nested list under `- **Contract changes:**`, one per item: `C1 <kind>: <what> — <consequence>`. Kinds `schema`, `data-writer`, `data-copy`, `api`, `event` are grouped first as data model & API changes. `### Open questions`, `### Migration plan`, `### Data model…` and `### API contracts` are lifted to the top. Mermaid code blocks render as diagrams.
- **Change** — `<item>.review.json`, as produced by `review`. `base`/`head` are git refs; code excerpts come from the real diff, so `where` must be `path:line` or `path:start-end` at head. Data model & API lead the page: contracts of those kinds (with `compat` and `migration` when known), plus changed files matching the `schema`/`api`/`event` triggers (built-in defaults plus the model's `review_triggers`) — a warning appears when such files changed but no matching contract was reported.

## After opening

Tell the user the page is open in one line, plus anything the page flags that needs them (open questions, red tier, model problems). Every item has an ID (`C2`, `H3`, `D1`) — the user discusses in the terminal by ID ("H3: why not reuse X?"); answer and act there. If the page shows a `Diagram error`, fix the mermaid source and re-render.
