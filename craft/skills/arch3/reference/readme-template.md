<!--
The skeleton `arch3` writes at the root README.md, ≤100 lines, loaded by every agent through
CLAUDE.md → AGENTS.md → README.md. These sections come first; people may reword them and add their own after. Current,
decided state only, one line per fact. Reasons go in ADRs, long prose in topic files under References.
Drop any line that restates architecture.yaml or says the obvious.
-->

# <system>

<2–4 sentences from PRODUCT.md: what it is, for whom, the value.>

## Architecture

<Shape in one line, from `summary`.> Stack: <languages, frameworks, stores, major versions>.

- `<component>` (`<source_path>`, <tech>): <job>. Hides <…>; never <…>.

Data: <stores, owners, copies, consistency>. Failures: <retries, compensation, what fails closed>.
Testing: <what each level covers; what is never faked>.
Invariants: `<rule id>` <what it forbids>; <other things no one may break, e.g. never edit a committed migration>

## Commands

- verify: `<…>` · AC: `<runner filter AC1_>`   ← `guard` sets these
- `<component>`: build `<…>` · test `<…>` · run `<…>`

## Craft

Work items move `.craft/draft/` → `ready/` → `done/`; `build3` builds each on a `craft/<item>` branch, merges 🟢 to local main and leaves 🟡/🔴 for `review walk`. Syncing with the remote is by hand: `git pull --no-rebase`, verify, `git push`.

## Prerequisites

<toolchains and versions, local services, env vars — one line>

## References

Only files that exist:
- `.craft/architecture.yaml`: before changing a component, relation, endpoint or data; `notes`, `glossary`
- `PRODUCT.md`: scope and purpose · `DESIGN.md`: before UI changes · `CONTRIBUTING.md`: commits, branches, releases
- `.craft/adr/`: why things are as they are; before reversing a decision
- `<topic file>`: when <trigger> (convention files, prose moved out of this README)
