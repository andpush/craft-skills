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
