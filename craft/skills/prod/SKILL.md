---
name: prod
description: Use to define the product — WHAT we are building and WHY - the purpose, users, solution, value, constraints, and scope — into a durable PRODUCT.md that `arch` and `spec` rely on.
---

Establish the durable product context — who it's for, what it does, why it matters, what's in and out — either by defining it with the user (greenfield) or deriving it from existing material (brownfield), into a `PRODUCT.md` that the rest of craft builds on.

Run once at project start; again only when the product direction shifts.

`prod` owns the product definition; `arch` consumes it.

If a `PRODUCT.md` already exists — written by hand or generated — update and extend it.

## Discover

Read whatever seed material exists: brief, notes, README, docs the user points to.

Don't synthesize a product from nothing — interview the user to elicit the product context. If the user provides a product description in the initial request, treat it as a proposed vision to be refined.

Use [reference/product-template.md](reference/product-template.md) as a guide for the content and structure of `PRODUCT.md`, adapt as needed.

### Greenfield: define with the user

Discover requirements in a professional conversation. Reach a shared, confirmed view of: the **problem** and **who has it**, the **solution** (the product concept that solves it — not the technical design), the **core value**, the hard **constraints** (tech, budget, timeline, compliance, non-negotiables), and what **success** looks like. Ask about each as it comes up, name the assumptions you're making, and challenge vague or contradictory answers rather than recording them.

### Brownfield: derive, then confirm

1. Peek into the repository enough to infer what the product does and for whom. Verify docs against the code.
2. Surface gaps, contradictions, or unstated assumptions as findings.
3. Discuss and confirm with the user.

## Output

Write the `PRODUCT.md` in a terse, pragmatic tone, link to existing docs instead of restating them, and report on the next step (`arch`), any open product questions the user must still resolve, and whether `PRODUCT.md` was created vs. adopted. A few lines, no narrative.
