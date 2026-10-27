---
name: guard
description: Use to set up the project's gate — one `verify` command, architecture checks generated from `architecture.yaml`, a baseline for existing violations, a CI workflow that runs `verify`, and branch protection. Run once after `arch`, and again whenever `architecture.yaml` or its rules change. Idempotent.
---

Make the rules in `architecture.yaml` executable, and put one command between the agent and main. The agent, the human and CI all run the same `verify`; CI never has checks of its own. A rule nobody checks is not a rule — it's `manual`, and `review` checks it by hand.

Idempotent: on a rerun, fix what drifted and leave what's right alone.

## Inputs

`architecture.yaml` (components, `depends_on`, entities, rules) and `AGENTS.md`. No model → offer `arch` first. Load [reference/stacks.md](reference/stacks.md) for the detected stack only.

## Process

### 1. Detect

- The stack, build tool and test runner, from the manifests.
- The remote and its host. With GitHub: `gh auth status`, and whether the active account can push (`gh repo view --json viewerPermission`). Missing `gh` → say how to install it and skip steps 7–8; the rest still works locally.

### 2. `verify`

One command that runs build, lint, tests and the architecture checks, and exits non-zero on any failure — including a test filter that matches nothing, so an AC command can't pass by selecting no tests. Reuse what the project has (`check`, `test`, `lint` scripts); add only the wiring. Record it in `AGENTS.md` under Commands as `verify: <command>`, plus the AC command form (`AC command: <runner> <filter AC1_>`).

Prove the empty-selection rule: run an AC-style filter that matches nothing and see it fail. If the runner passes on empty, wrap it (stacks.md has the trap list).

### 3. Component check from the model

Write the stack adapter that reads `architecture.yaml` at test time (or generates config with a freshness check, where the tool can't read YAML). One check, three parts:

- **Dependencies:** code in a component imports only itself, its `depends_on` components, and third-party code.
- **I/O placement,** derived, never declared:
  - persistence APIs only in components that own an entity;
  - HTTP and messaging clients only in components whose `depends_on` lists an external;
  - server and controller APIs only in components an external `calls`.
- **Paths:** every component `path` exists and every production source file belongs to exactly one component. Unowned code is a violation, so new code can't slip past the map.

Name each failure after the model: `orders -> notify: not in depends_on`, `catalog: persistence import, but owns no entity`.

### 4. Rule checks

For each `MUST` rule the component check doesn't already cover, write one test named after the rule ID (`R2_onlyOrdersWritesOrdersTable`) and set its `checked_by` to that test. A rule no tool can express stays `SHOULD` with `checked_by: manual` — ask the user rather than writing a check that only looks like one.

### 5. Baseline

Existing violations go into a frozen baseline (ArchUnit `FreezingArchRule`, dependency-cruiser known-violations, or a list file the check reads). New violations fail; fixed ones leave the baseline. Mark the rule `exceptions: baseline`. Report the baseline size — it's debt, and `audit` tracks it.

### 6. Prove each check

For the component check and each rule test: introduce one violation, run `verify`, see it red with the expected message, revert. A check that never went red is not checked. Show the red output in the transcript.

### 7. CI

A workflow that sets up the toolchain and runs `verify` — nothing else. GitHub: `.github/workflows/verify.yml`, job named `verify`, on `pull_request` and on push to main. Cache dependencies. Commit, push, and watch the first run (`gh run watch`).

### 8. Branch protection — ask first

This changes a GitHub repository setting, so confirm with the user. Then require the `verify` check on main:

```bash
gh api -X PUT repos/{owner}/{repo}/branches/main/protection --input - <<'EOF'
{"required_status_checks": {"strict": false, "contexts": ["verify"]},
 "enforce_admins": false, "required_pull_request_reviews": null, "restrictions": null}
EOF
```

- **Solo repo:** no required approvals; GitHub doesn't let you approve your own PR.
- **Private repo on GitHub Free:** protection isn't available. Say so. The gate is then `verify` in build3 plus the merge policy, and `gh pr merge --auto` won't work.

Offer to allow auto-merge on the repo too (`gh repo edit --enable-auto-merge`), but only if `AGENTS.md` sets `Auto-merge: green`.

### 9. Review triggers

Add the gate's own paths to `review_triggers` in `architecture.yaml` (under `arch-check` and `ci`): the `verify` wiring, the check sources and config, the baseline. A change that weakens the gate must turn the review red.

## Report

At most 8 lines:
- the `verify` command;
- the checks, with the rule IDs each one covers;
- the baseline size;
- the CI run link;
- whether branch protection is on;
- what stays manual.

Next step: `spec` or `task`.
