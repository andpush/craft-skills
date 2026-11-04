---
name: review
description: Use to review a change before it merges — a craft item's branch or any other branch. Computes the risk tier, describes contract changes (data model, API, dependencies), runs independent reviewers, turns suspicions into failing tests, and writes `<item>.review.json`. `review walk` then guides the human through what matters, in the terminal. `build3` calls it after verify.
---

Find what a human must look at, prove what you can, and say plainly what wasn't checked. The tier is computed by a script, never chosen by you. Zero findings is a valid result; padding is not.

**Independence.** The reviewer is not the author. If this conversation wrote the change, run this skill in a subagent given only the item path, the base and head refs, and this skill.

## Invocation

- `review` — the current branch (`craft/<item>` finds the item) against main.
- `review <item | branch>` — that item or branch against main.
- `review walk` — guide the human through an existing review (below).

## Process

### 1. Triage

```bash
uv run --quiet <this-skill-dir>/scripts/review.py [item] [--base REF] [--head REF]
```

It writes `<item>.review.json` next to the item (no item: a temp file), with triggers from the diff and `architecture.yaml`, new dependency edges, the tier, the AC skeleton from the spec's Acceptance table, and a `not_checked` list seeded with the reviewers and `manual` rules. It prints what is still incomplete. Rerunning keeps your fields and recomputes the rest.

### 2. Automated reviewers

Run the `code-review` skill on base..head (effort `high` when red, `medium` otherwise) and the `security-review` skill. Fold their findings in as `plausible` unless they're proven. Then remove their lines from `not_checked`. If a tool isn't available on this host, do that pass yourself and say so in `not_checked`.

### 3. Own lenses — what those tools miss

- **Spec conformance** → `deviations`: what the diff does that the spec didn't ask for, does differently, or leaves out. An edited AC test must still check its criterion; a weakened one is a finding.
- **Contracts** → `contracts`, one per dependency/schema/api/event trigger and per architecture change to externals or data. Each needs `what`, `consequence`, `compat` and `migration`.
  - **Schema:** read the migration whole. Check for destructive steps, NOT NULL without a default, locking index builds, backfill, and whether old code runs against the new schema.
  - **API and events:** check for removed, renamed or newly required fields, changed semantics, versioning, and consumers' idempotency and ordering.
- **Architecture:** code that imports what `uses` in `architecture.yaml` doesn't list is a deviation. A write its `writes` doesn't list is a high finding.
- **Blast radius** → `blast`: for each changed public symbol, list the callers outside the diff (LSP references, or grep) and the tests that cover them. Stop after the five symbols with the most callers.
- **Negative cases:** check the spec's testing approach, then the usual suspects: another user's or tenant's data, revoked rights, duplicates, reordering, concurrency, partial failure. An untested one is a suspicion.
- **Manual rules:** check each `manual` rule in `not_checked` against the diff, then remove it. A violation becomes a finding.
- **Change cost:** if this change makes the next ordinary change harder (new coupling, duplicated logic), record it as one low finding.

Finding = `where` → `invariant` → `scenario` → `consequence` → minimal `fix`. IDs are `H`/`M`/`L` by severity plus a number that's never reused across rounds (`H1`, `M2`, `L3`).

### 4. Counterexamples

For each high or medium suspicion, write the smallest test that fails because of it. Name it `<ID>_<behavior>` (e.g. `H1_retriedSubmitReturnsSameOrder`) and run it.

- **Fails:** mark the finding `confirmed` and set `test`.
- **Passes:** drop the finding, or mark it `plausible` if the test couldn't reach the scenario.

Give each one a single attempt; don't fight the harness. On a `craft/` branch, commit the tests as `test: counterexamples H1, H3`. A red `verify` is then the gate that keeps the bug from merging. On someone else's branch, leave them uncommitted and say so.

### 5. Evidence

Run every AC command and record `pass` or `fail`. Manual ACs stay `manual`, and the human checks them during the walk.

### 6. Close

Rerun the script, and resolve every `incomplete` line, or state why in `not_checked`. Don't fix the code: fixes belong to `build3` or the user. Then open the changes view:

```bash
uv run --quiet <this-skill-dir>/scripts/diff_to_html.py <item>.review.json
```

Excerpts come from the real diff, so each `where` must be `path:line` or `path:start-end` at head. Flags: `--editor vscode|cursor|idea|none` (default `$CRAFT_EDITOR` or `vscode`), `--spec`, `--repo`, `--no-open`, `--out`.

Report in at most 8 lines: the tier, the red reasons, and what needs the human.

## review walk

Open the changes view, then go through the items in this order:

1. data model & API contracts
2. deviations
3. other contracts
4. confirmed findings
5. blast radius (uncovered first)
6. plausible findings
7. manual ACs

For each item, at most six lines:
- the ID and a clickable `path:line`;
- what changed, in one line;
- the one question to check;
- your recommendation (accept or change), with the reason.

Ask for the verdict with AskUserQuestion: accept / change / discuss. You may group up to four low-risk items in one call. On "discuss", answer and ask again. Record each verdict in `verdicts`.

The tier sets the depth:
- **🟢 green:** no walk.
- **🟡 yellow:** the page is enough, unless the user wants a walk.
- **🔴 red:** a walk is required before merge.

The walk ends one of two ways:
- **All accepted:** ask, then merge as `build3`'s Integrate step does.
- **Any "change":** produce a fix list (ID → minimal fix).

## Re-review after a fix

Read only the fix diff (`git diff <reviewed head>..HEAD`). Rerun each finding's test: green → `fixed`, still red → keep it and say why. Run step 2's reviewers (effort `medium`) and step 3's lenses on the fix diff; new problems get new IDs. Then rerun the script without `--base`, so the tier still covers the whole change.

## review.json — your fields

```json
"deviations": [{"id": "D1", "what": "", "where": "path:line"}],
"contracts":  [{"id": "C1", "kind": "dependency|schema|api|event|data-writer|data-copy|external-call|config",
                "what": "", "consequence": "", "compat": "compatible|breaking|needs-migration|needs-versioning",
                "migration": "expand-only|backfill|contract|none", "where": "path:line"}],
"blast":      [{"id": "B1", "symbol": "", "change": "", "callers": ["path:line"], "covered_by": ["test"], "where": "path:line"}],
"findings":   [{"id": "H1", "severity": "high|medium|low", "status": "confirmed|plausible|fixed", "where": "path:10-24",
                "invariant": "", "scenario": "", "consequence": "", "fix": "", "test": ""}],
"evidence":   [{"ac": "AC1", "criterion": "", "command": "", "result": "pass|fail|not-run|manual"}],
"not_checked": ["what was not checked, and why"],
"verdicts":   {"H1": "accept|change|discuss"}
```

`where` is at head. The changes view uses it to cut the real diff hunk, so it must be precise. The script owns `item`, `base`, `head`, `tier`, `triggers` and `new_edges`.
