"""Parse the Markdown files craft works with: frontmatter and sections."""
import re


def split_frontmatter(text):
    m = re.match(r"---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).splitlines():
        key, sep, val = line.partition(":")
        if sep and key and not key[0].isspace():
            fm[key.strip()] = val.split(" #", 1)[0].strip()
    return fm, text[m.end():]


def split_sections(body):
    """Split on level-1/2 headings outside code fences. The first H1 is the title."""
    title, sections, cur, fence = "", [], None, False
    for line in body.splitlines():
        if line.lstrip().startswith("```"):
            fence = not fence
        m = None if fence else re.match(r"(#{1,2})\s+(.+?)\s*$", line)
        if m and len(m.group(1)) == 1 and not title:
            title = m.group(2)
            continue
        if m:
            cur = {"title": m.group(2), "md": []}
            sections.append(cur)
            continue
        if cur is None:
            cur = {"title": "", "md": []}
            sections.append(cur)
        cur["md"].append(line)
    for s in sections:
        s["md"] = "\n".join(s["md"]).strip()
    return title, [s for s in sections if s["title"] or s["md"]]
