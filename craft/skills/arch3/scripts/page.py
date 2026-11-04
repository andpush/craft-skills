"""What the architecture page, spec page and changes view share: escaping, markdown, the template, writing."""
import html
import re
import tempfile
import webbrowser
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.html")
MERMAID_BLOCK = re.compile(r'<pre><code class="language-mermaid">(.*?)</code></pre>', re.S)


def esc(v):
    return html.escape(str(v))


def _markdown():
    from markdown_it import MarkdownIt  # only the spec page and changes view need it
    return MarkdownIt("commonmark", {"html": False}).enable("table")


def md(text):
    """Markdown to HTML; raw HTML in the source stays text, mermaid blocks become diagrams."""
    return '<div class="md">' + MERMAID_BLOCK.sub(r'<pre class="mermaid">\1</pre>', _markdown().render(text or "")) + "</div>"


def inline(text):
    return _markdown().renderInline(text or "")


def pill(text, tone=""):
    return f'<span class="pill {tone}">{esc(text)}</span>'


def section(title, body, count=None, open=True, anchor=None):
    badge = f' <span class="count">{esc(count)}</span>' if count else ""
    return (f'<details class="section"{" open" if open else ""}{f" id={anchor!r}" if anchor else ""}>'
            f"<summary><h2>{esc(title)}{badge}</h2></summary>{body}</details>")


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


def targets_of(fm):
    """A spec's `target:` as names: `a, b`, `a/b` and `[a, b]` all work."""
    return [t for t in re.split(r"[,\s/]+", fm.get("target", "").strip("[] ")) if t]


def write(title, body, name, out=None, show=True):
    """Fill the template, write to a temp dir unless `out` is given, print the path, open it."""
    page = TEMPLATE.read_text(encoding="utf-8").replace("{{TITLE}}", esc(title)).replace("{{BODY}}", body)
    if out:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        folder = Path(tempfile.gettempdir()) / "craft-views"
        folder.mkdir(exist_ok=True)
        path = folder / f"{name}.html"
    path.write_text(page, encoding="utf-8")
    print(path)
    if show:
        webbrowser.open(path.resolve().as_uri())
    return path
