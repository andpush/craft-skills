---
name: tests-optimizer
description: Review a test suite to find and remove low-value tests — trivial assertions, never-fail, tests for removed functionality, redundant duplicates, over-costly integration/e2e tests that belong lower in the pyramid, and tests left obsolete by refactoring. Use whenever the user wants to prune, clean up, slim down, de-duplicate, or speed up their tests, audit test value, or trim a slow/bloated suite.
---

## Goal

A test suite earns its keep by catching regressions cheaply. Tests that can't fail meaningfully, that duplicate each other, or that cost more to run and maintain than the confidence they buy are liabilities — they slow CI, obscure real signal, and make refactoring painful. Find them, justify each, get the user's sign-off, remove them, and prove the suite is faster and still green.

## Process

1. **Map the suite.** Detect components and test frameworks, how layers are split (unit / integration / e2e).
2. **Baseline metrics.** Run the suite (or per-layer) to capture counts and wall-clock time. If running is infeasible, count statically and estimate time from a prior run or markers — say so. Record the **Before** table (see Metrics).
3. **Review the suite.** Read tests against the code they cover, not in isolation — a duplicate or stale test is only visible relative to the rest.
4. **Report** flagged tests, each with `file:line`, a one-line rationale, and the safe-to-cut justification.
5. **Confirm.** Present the report and ask the user to approve removals — per dimension or per test. Do not delete anything before sign-off.
6. **Clean up** the approved set. Where a duplicate cluster has value as a single parametrized case, prefer merging over plain deletion.
7. **Re-measure and prove it.** Re-run the suite: it must stay green and coverage of real code must not drop. Record the **After** table and the delta.

## Output Metrics

Report Before and After as a table — rows by layer and by component, columns count and time — plus the delta.

```
| Layer       | Component | Tests (before→after) | Time (before→after) |
|-------------|-----------|----------------------|---------------------|
| unit        | auth      | 48 → 41              | 1.2s → 1.0s         |
| integration | auth      | 12 → 7               | 8.4s → 4.9s         |
| e2e         | checkout  | 6 → 5                | 41s → 33s           |
| **Total**   |           | **N → M**            | **Ts → Us**         |
```
