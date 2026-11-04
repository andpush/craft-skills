# Developing Craft

## Status

The `3` suffix marks new versions. It goes away once they're proven and the old skills are removed.

**Proven.** On a Kotlin fixture (2026-10-28, run stopped halfway), `build3` and `review` wrote acceptance tests red first, and `review` proved a spec gap with a failing test, blocking the merge. On travelai (2026-11-02), `guard`'s Kotlin and Dart checks and deploy test went red on planted violations. Python was proven on a throwaway repo.

**Not yet run.** `build3` and `review` on the current `architecture.yaml` format; the worktree flow, `review walk` and merge steps with a real item (their git steps passed on a throwaway repo); `feat`'s `draft/` flow; a full `verify` on travelai; blocked → resume; a green merge; the TypeScript, Go and Rust/Swift adapters.

**Next.** Trim every skill, then a trial with planted defects: a forbidden dependency, an unauthorized writer, a consumer without dedupe.

## Design principles

- **Markdown and YAML are the source of truth;** pages are rendered by script into one logic-free template.
- **One fact, one place.** Stable IDs (rule id, `AC2`, ADR slug, component name) tie docs to code and tests.
- **Intent is never silently rewritten to match code.** Drift means fixing the code, fixing a stale line, or an explicit decision.
- **Deterministic where possible;** AI writes the implementation and is verified separately.
- **Not checked ≠ passed.** Skipped, unsupported or empty is a failure or an explicit "not checked".
- **Depth matches risk.** Omit empty sections, keep small changes small.
- **Derive rather than store;** anything stored must be something a check can catch drifting.
- **No pipeline or host lock-in.** `verify` is the interface.
- **Skills hold only what a model can't work out itself:** project facts, how skills connect, checks on the agent's own work.
