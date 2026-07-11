---
name: ui-mockup
description: Creates UI mockup (clickable prototype) based on product specifications as HTML with asset folder.
---

Create a clickable UI prototype that opens directly in a browser, from the requirements the caller provides.

## Inputs

The calling context supplies the requirements, expected functionality, UI references, and the `[output path]` and `[name]`. Read `PRODUCT.md` as the main source; follow a Design System / UI-UX guide and reference designs in `docs/` when present.

## Output

- HTML file: `[output path]/[name].html`
- Assets folder: `[output path]/[name]-assets/`

## Variants

When exploring design direction (no established Design System yet), generate 2-3 variants in parallel — one subagent each, same requirements, each with a distinct style brief derived from the product's domain and audience (e.g. minimalist/calm, elegant/high-end, corporate/dense). Output `[name]-variant1.html`, `[name]-variant2.html`, …; suggest the user open them in a browser and pick — the chosen variant becomes the design reference.

## Design

Design for the personas' goals, the primary flows, and a clear visual hierarchy.

- Embed all CSS in `<style>` and JS in `<script>` tags
- Inline SVGs or base64 images for icons/small graphics
- CDN allowed for: Tailwind CSS, Google Fonts, Shadcn components
- Realistic placeholder content that demonstrates the interface

Verify before finishing: opens correctly in a browser, responsive across mobile/tablet/desktop, interactive elements work, accessible, matches the requirements and keeps a consistent visual design.
