---
name: slides
description: Create slides from plain text; use when asked to make a presentation.
---
Convert text into a presentation deck in PPTX format.

1. Review text first; flag any apparent omissions or inconsistencies.

2. Prepare slides.md.
Format:
   - YAML frontmatter (instead of title slide): title, subtitle (optional), author, date
   - `---` to separate slides
   - `#` Section dividers (heading only)
   - `##` Slide titles
   - Slide content:
      - paragraphs/bullets
      - markdown tables when >3 data rows
      - use 2 or 3 column layout where appropriate, delimiting columns with `||`
      - Speaker Notes: `<!-- Notes: ... -->`
Instructions:
   - Group information for slides by meaning, not size only
   - Preserve original well though out content
   - Occasional abbreviations allowed to match terse presentation style:
      - Extract explanatory passages (>2 sentences) to Speaker Notes.
      - Extract duplications into the Speaker Notes.
   - **Leave multiline code blocks intact**, even if they overflow one slide!
   - Add Agenda slide as the first slide (list all sections/major topics)
3. Generate PPTX using the `md2pptx.py`:
   - Supported formatting:
      - Bullets: */- (nested items with indentation)
      - Tables: standard markdown tables
      - Inline: **bold**, *italic*, `code`, [link text](url)
   - Run the script: `python3 scripts/md2pptx.py slides.md -o "<title>-<ddHHMM>.pptx"`
