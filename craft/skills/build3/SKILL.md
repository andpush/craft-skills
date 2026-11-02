---
name: build3
description: Implement a build-ready item from `docs/ready/` on its own branch — acceptance tests first, implementation, verify, independent `review`, docs closed in the same branch, then a PR or merge per the project's policy. Use for "build", "build next", "build <item>", "build all". Replaces `build` once proven.
---

Turn a ready item into a verified, reviewed branch that lands code, docs and the item's move to `done/` in one merge. The item is the brief: `spec` or `task` wrote it to execute from cold. If it needs a design decision, it wasn't ready — stop and send it back to `spec`.

You orchestrate; subagents write the tests and the code, and a fresh one reviews. Keep your own context for the queue, the gates and the report.

## Before the first item

- `AGENTS.md` names the `verify` command. No `verify` → stop and offer `guard3`; without it there is no gate.
- The worktree is clean, you're on main, and main is current (`git pull --ff-only` when a remote exists).
- Read the merge policy in `AGENTS.md`: `Merge: pr | local`, `Auto-merge: off | green`. Missing: `pr` when a remote exists, else `local`; auto-merge `off`.

## The queue

`docs/ready/` holds `feat-`, `task-` and promoted `idea-` items. Status lives in the frontmatter: `ready`, `blocked` (with `blocked: <reason>`), `done`. The claim is the branch `craft/<item>` — there is no in-progress status and no owner field.

## Invocation

- `build3` — the next item, then stop.
- `build3 <item>` — that item; resumes its branch if it exists.
- `build3 all` — item after item until the queue is empty or one fails.

## Process

### 1. Pick

Unclaimed = `status: ready` and no `craft/<item>` branch, local or remote (`git ls-remote --heads origin 'craft/*'`). Order: `priority: high` first, then `created`. Check it's buildable: a goal, `target:` components, an Acceptance table. If not, skip it and say why.

### 2. Claim

```bash
git switch -c craft/<item> main
git push -u origin craft/<item>     # when a remote exists; rejected = someone else has it, pick the next
```

Resuming: read the branch's commits and continue from the first step not done (an AC commit means step 3 is done).

### 3. Acceptance tests first — feat and idea items

Skip for `task` items: their tests come with the code.

A subagent gets only the item path, `AGENTS.md` and this brief:
- Write a test for each AC that has a command, named `AC<n>_<behavior>` so the command selects it.
- Test behavior through public interfaces, as the criterion states it.
- No production code. In a compiled language, a compile error on a symbol the spec names counts as failing.

Then run each AC command yourself. Each must fail, on an assertion or on that missing symbol — not on a typo or a harness error. A test that already passes is vacuous or the behavior exists: give the subagent one try to fix it, otherwise note it for the report. Commit:

```bash
git commit -m "test: acceptance tests for <item>"
```

`review` finds this commit by its subject and flags later edits to its files.

### 4. Implement

A subagent gets the item path, `AGENTS.md`, the AC commit's file list, and these rules:
- Stay inside the `target` components and the relations `docs/architecture.yaml` lists for them.
- Read the model's `notes` about what you touch. If the change would make one false, stop and raise it.
- Don't edit the AC test files. If one looks wrong, stop and report it — that's a spec question, not a code one.
- Don't edit `docs/architecture.yaml`, `docs/PRODUCT.md` or `AGENTS.md`: you apply the doc impact at close.
- Commit in small commits; report what changed and anything done differently from the spec, with the reason.

A small `task` item may be done inline.

### 5. Simplify, then verify

Run the `simplify` skill on `main...HEAD` and commit its fixes. Then run `verify` and show the exit code and the tail of the output in the transcript — the gate is what was shown, not what was claimed. Red → back to the implementer with the failure; after three red runs, the item is blocked.

### 6. Review

Spawn a fresh subagent with: "Run the `review` skill for item `docs/ready/<item>.md` on branch `craft/<item>`, base `<merge-base>`, head `<sha>`. Report the tier, the red reasons and a fix list." It writes `docs/ready/<item>.review.json` and commits its counterexample tests.

Fix what has a clear fix: confirmed findings, failing ACs, deviations, model violations. Leave to the human: contract decisions, plausible findings, anything that changes the spec. When the human decides one, amend the item in the branch first — Review Brief contracts, an AC row for the new behavior — and commit (`spec: <item> — <decision>`); then it's a fix like the others. The implementer gets the fix list (ID → fix) and makes the counterexample tests green without editing them. Verify, then spawn a fresh reviewer for the fix: "Re-review item `<item>`: the reviewed head was `<sha>`." At most two fix rounds; whatever remains stays in the review for the human. Close only on a green `verify`: a confirmed finding still open after the rounds is a Fail with `blocked: <IDs> open — review walk`.

### 7. Close in the branch

1. Apply the item's **Doc impact** exactly — the only doc edits this skill makes.
   If that changed `docs/architecture.yaml`, re-run `gate.py` (see `guard3`). If it refuses a new deficiency, stop and ask the user; never pass `--accept` yourself.
2. Write the ADRs the item agreed to, in the format of [../sa/reference/adr.md](../sa/reference/adr.md).
3. File an idea (`docs/ideas/idea-<slug>.md`) for each piece of deferred work and each temporary flag or adapter, with its removal condition.
4. Commit these with the review file (`docs: <item>`), then rerun the review script without `--base` so the tier covers the docs too:
   ```bash
   uv run --quiet <this-skill-dir>/../review/scripts/review.py docs/ready/<item>.md
   ```
5. Set `status: done` and `updated:`, `git mv` the item and its same-basename files (`<item>.review.json`, `<item>-*.png`) to `docs/done/`, and commit (`done: <item>`).

### 8. Integrate

If main moved, merge it into the branch — don't rebase: the review's refs must stay reachable. Rerun `verify`; if the merge touched the changed files, re-review.

| Policy | 🟢 green with `Auto-merge: green` | otherwise |
|---|---|---|
| `pr` | `gh pr create`, then `gh pr merge --auto --squash` — merges when CI is green (no branch protection: `gh pr checks --watch`, then `gh pr merge --squash`) | `gh pr create`; the PR waits for the human |
| `local` | `git switch main && git merge --ff-only craft/<item>`, delete the branch | leave the branch; the human merges |

PR body, short: the goal, the tier and its reasons, the AC evidence, what wasn't checked, and the line `review: docs/done/<item>.review.json`. Then open the change page:

```bash
uv run --quiet <this-skill-dir>/../view/scripts/view.py change docs/done/<item>.review.json
```

### 9. Report

Per item, at most six lines: the tier and red reasons, the PR or branch, and what needs the human — a `review walk` for red, manual ACs, what wasn't checked. For `build3 all`, end with: merged, waiting, blocked, left.

## Fail

Set `status: blocked` and `blocked: <one-line reason>` on the branch, commit, push, and open a draft PR when there's a remote (`gh pr create --draft`). The branch keeps the item claimed until the human clears it. Stop — `build3 all` stops here too.

## Notes

- **`build3 all`** starts each item from main. An item that needs another item's unmerged code waits; say so and move on.
- **No subagents on this host:** do steps 3–4 inline, then stop after verify and ask the user to run `review` in a new session. The author doesn't review its own change.
- Item names never change across folders; only `status:` and location move.
