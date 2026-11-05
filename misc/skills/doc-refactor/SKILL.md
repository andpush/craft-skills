---
name: doc-refactor
description: "Refactor document(s) into a single deduplicated, restructured document — preserving contained knowledge. Triggers: 'merge docs A, B, C -> B without duplication', 'remove repeated ideas', 'tighten for agent hand-off'."
---

# doc-refactor — document normalization

Normalize a document by cutting word-for-word and same-meaning duplication, and re-projecting onto a clearer hierarchy, while preserving relevant content.

Most valuable when:
- merging multiple sources
- normalizing source with repeated ideas
- preparing a document for hand-off to another agent (human or LLM) that will need to understand it without reading the inputs.

Inspired by ML concept of feature extraction, applied to human knowledge. In ML Autoencoders reduce dimensions while preserving required features. Similarly, we need to hand-off minimal document, yet enough information for the purpose.

User specifies input documents, an output document or indicate `dryrun`, and optionally a goal. The goal defines relevance; without a goal or clear contextual intent, run losslessly and treat all input knowledge as relevant.

Example: `/doc-refactor PRODUCT.md, README.md -> PRODUCT.md for Product Manager review`.

How it works:
- decompose the inputs into claims,
- cluster the concerns,
- dedupe across the union,
- re-project onto a clearer structure.

The result is denser and more navigable; excluded and conflicting claims are reported.

## Principles
- **Conservative.** If target file already exists, do not overwrite without user confirmation. Think before writing wether it will improve the target file.
- **Terse, pragmatic tone.** But do not overcompress phrasing: achieve density by cutting duplicate claims.
- **Hierarchy is a projection.** Duplication is often an artifact of the *wrong* one — an idea sits in two places because neither is its home; re-project and the duplicate dissolves. So handle knowledge claims and structure (skeleton) separately. If no misplacement detected - keep the input structure.
- Unsure - ask the user; unattended - best guess + flag for review.
- Don't assume orthogonal concerns.

## Pipeline
1. **Skeletons.** Record each input's heading tree as a separate artifact, tagged by source. Never rebuilt from claims, so structure can't dissolve silently.
2. **Decompose → claims.** Break inputs into atomic claims; split conjunctions ("fast **and** secure" → two). Each carries `id`, `text` (short paraphrase, no long verbatim spans, preserve code/ids), `source`, `address` (path in its skeleton), `scope` (qualifier bounding its truth). No concern tags yet.
3. **Concern basis.** Cluster claims *across all inputs* into concerns; tag each with its concern-**set**. One basis over the union is what catches cross-document repeats.
4. **Detect duplicates.** Cluster by *meaning*; classify per the taxonomy. Test is **same claim, same scope** — never similarity alone.
5. **Define draft hierarchy** If no misplacement detected, keep the input structure. Otherwise, propose a new hierarchy based on the concern clusters, up to 4 heading levels + lists. If a concern is mostly contained in one input and section, that's a strong signal for its home; if it's split across sections/inputs, that's a strong signal for a new section. If the goal defines relevance, use it to prioritize concerns.
6. **CHECKPOINT (human, unless unattended).** Present the concerns and the proposed structure as a diff from input skeletons. Flag key moved claims and relevance/conflict calls. If target file in a good shape and no merge is required, suggest only cosmetic chnages instead of full reconstruction. Get user feedback and approval to proceed with the rewrite.
7. **Reconstruct.** Each claim gets **exactly one** home; scope-distinct pairs keep both. The **Intro/Overview is a home like any other**. A second mention of a cross-cutting claim is a **pointer** (e.g.: "... — see `Data model`"), never a restatement.
8. Save the output document **unless `dryrun` was requested**.
9. **Output Report (not save unless asked):** List removed claims, not present in the final document, with `source`, original `address`, `disposition`, and a short reason. Allowed dispositions: `verbatim`, `semantic`, `merged`, `conflict` and if goal was defined: `not-relevant`. Also report summary statistics: compression %, total input claims, duplicate counts by category, and total output claims.
10. When launched in dryrun mode, output the analysis **Verdict**, grounding whether the doc needs refactoring.

## Duplicate taxonomy
| Class | Test | Verdict |
|---|---|---|
| Verbatim | Identical wording | Cut — keep one |
| Semantic | Same claim, same scope, different words | Cut — keep one canonical |
| Cross-cutting | Same claim serves several sections | Keep — one home; every other mention is a **pointer** |
| Reader-aid | Avoids a long-range dependency or misreading in rare cases | As an exception - keep shortened + point to full claim |
| Scope-dependent | Similar, but **different scope** changes its meaning | Keep both — not a duplicate |
| Conflict | Same slot, **incompatible values** | Ask user which holds true, or flag in the report and indicate uncertainty in the result doc |

## VERIFY (subagent, fresh context)
Spawn a subagent given **only** the inputs, output, and removed-claims report — no decomposition notes, so it can't grade its own homework.
1. **Reconstruction** — a fresh agent can regenerate every input claim from the output + report alone (present-but-dead claims fail this).
2. **Reverse-duplication** — re-run steps 2–4 on the output; surviving verbatim/semantic clusters mean dedup failed.
3. **No-fabrication** — every output claim traces to an input claim.
