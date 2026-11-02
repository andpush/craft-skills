---
name: guard
description: Use to set up the project's gate — one `verify` command, architecture checks driven by `docs/architecture.yaml`, a baseline for existing violations, a CI workflow that runs `verify`, and branch protection. Run once after `arch-define`, and again whenever the model or its rules change. Idempotent.
---

Put one command between the agent and main, and make the model executable. The agent, the human and CI all run the same `verify`; CI has no checks of its own. On a rerun, fix what drifted and leave the rest.

Needs `docs/architecture.yaml`; without it, offer `arch-define` first. Load [reference/stacks.md](reference/stacks.md) for the detected stack only.

## 1. Detect

The stack, build tool and test runner, from the manifests. The remote: with GitHub, `gh auth status` and `gh repo view --json viewerPermission`. No `gh` → say how to install it and skip steps 7–8.

## 2. `verify`

One command that runs build, lint, tests and the architecture checks, and exits non-zero on any failure. Reuse the project's scripts and add only the wiring. Record it in `AGENTS.md` under Commands: `verify: <command>` and `AC command: <runner> <filter AC1_>`.

Run an AC filter that matches nothing and see it fail. If it passes, wrap it (stacks.md).

## 3. Gate file

```bash
uv run --quiet <arch-define-dir>/scripts/validate.py docs/architecture.yaml --gate
```

Writes `docs/architecture.gate.json`, the flat form of the model that checks read, so CI needs neither Python nor this plugin. It refuses new model deficiencies unless passed `--accept`. Only the user decides that; fixed ones drop out by themselves.

## 4. Architecture check

One test file reads the gate file and fails on:

- **Stale gate:** the SHA-256 of `docs/architecture.yaml` differs from `model_sha256`.
- **Imports:** code in a unit imports another unit not listed in its `imports`. The owner of a file is the unit with the most specific match in `paths`; third-party code is free.
- **I/O:** a unit imports a library of a kind missing from its `io` (`persistence`, `client`, `messaging`, `server`).
- **Unowned:** a production source file belongs to no unit.

Each violation is one stable line named after the model, without line numbers: `orders -> billing: import not allowed`, `catalog: persistence import`. Existing ones go in `docs/architecture.baseline`, one per line: a new line fails, and so does a baseline line that no longer occurs, so debt only shrinks. Report the baseline size.

## 5. Other checks

- **Rules:** each `must` rule the check above doesn't cover gets one test, named in the rule's `check`. A rule no tool can express becomes `should`; ask the user rather than writing a check that only looks like one.
- **Surface:** one test compares the gate file's `surface` with what the project really deploys: ingress flags, public routes, security config. A route checked in its handler instead of config goes in a commented list inside the test.

## 6. Prove each check

For each check: introduce one violation, run `verify`, see it red with the expected message, revert. A check that never went red isn't one. Show the red output.

## 7. CI

A workflow that sets up the toolchain and runs `verify`, nothing else: `.github/workflows/verify.yml`, job `verify`, on `pull_request` and push to main. Commit, push, watch the first run (`gh run watch`).

## 8. Branch protection — ask first

This changes a repository setting, so confirm with the user. Then require `verify` on main:

```bash
gh api -X PUT repos/{owner}/{repo}/branches/main/protection --input - <<'JSON'
{"required_status_checks": {"strict": false, "contexts": ["verify"]},
 "enforce_admins": false, "required_pull_request_reviews": null, "restrictions": null}
JSON
```

On a private repo on GitHub Free, protection isn't available: say so. The gate is then `verify` in `build3` plus the merge policy. Offer `gh repo edit --enable-auto-merge` only if `AGENTS.md` sets `Auto-merge: green`.

## 9. Protect the gate

An agent must not be able to loosen its own gate. `review` turns red on changes to the gate file, the baseline, rule checks and new model deficiencies, and red needs a human. Add what it can't derive to `review_triggers` in the model: the `verify` wiring and CI under `ci`, deploy and auth config under `security`. Then re-run step 3.

## Report

At most 8 lines: the `verify` command, the checks and rules each covers, baseline size, deficiencies accepted, the CI run link, whether branch protection is on, what stays unchecked. Next step: `spec` or `task`.
