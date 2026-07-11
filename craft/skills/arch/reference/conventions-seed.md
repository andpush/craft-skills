<!--
Seed menu for the `arch` skill's `Rules and Conventions` step — consulted, not emitted.
Pick the sections that fit the chosen stack, adapt with the user, keep only what isn't
obvious to a competent engineer, and fold the result into ARCHITECTURE.md. Do NOT copy
sections for stacks the project doesn't use.
-->

# Conventions seed

General:

- Build only what the spec calls for — don't invent features, dependencies, or tech that isn't specified.
- Surgical edits: touch only what the task needs, match surrounding style, don't refactor unrelated code, and drop imports/symbols your change orphaned.
- Package by feature, not by layer; don't pre-create `service`/`repository`/`utils` scaffolding just in case.

Backend:

- Simplified layering: API → Service → Store; expose over REST unless another protocol is specified.
- No parallel `*Dto` unless the wire shape genuinely differs.


Testing:

- TDD for APIs and before refactoring: RED → GREEN → REFACTOR.
- Pyramid: many fast unit, fewer integration, few slow end-to-end.
- Fake only true boundaries (network, filesystem, clock, randomness, payments); never mock your own logic.
- Pin behavior through the public surface, one intent per test; cover acceptance criteria and error paths, not line count.

Webapp:

- One component library and one styling system — don't mix paradigms.
- Keep state local; lift it only when genuinely shared.
- Accessibility is a requirement, not a polish pass: semantic HTML, keyboard paths, WCAG AA.

Flutter:

- Follow official style guide `Effective Dart`.
- One state-management approach, applied consistently.
- Theme centrally (e.g. `MaterialApp.theme`); never hardcode colors/sizes in widgets.
- Responsive sizing — flex/relative over fixed dimensions.
- Log via the platform logger (e.g. `dart:developer` `log`), never `print`/`debugPrint`.

Kotlin:

- Immutable `val`/`data class`; model absence with nullables, not sentinels.
- Sealed types for closed state sets; exhaustive `when`, no `else` catch-all.
- One error convention per module — exceptions or a `Result`/sealed type, not both.
- No `!!` outside tests; resolve null at the boundary.
- Structured concurrency only — scope to lifecycle, no `GlobalScope`; suspend for I/O, never block a dispatcher.

TypeScript:

- `strict` on; no `any` — use `unknown` + narrowing at boundaries.
- Discriminated unions for closed state sets; exhaustive `switch` with a `never` default guard.
- One error convention per module — a thrown `Error` subclass or a typed result.
- Never leave a promise unawaited (`no-floating-promises`).
