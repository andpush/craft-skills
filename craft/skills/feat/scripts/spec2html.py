#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "markdown-it-py>=3", "pyyaml>=6"]
# ///
"""Render a spec as one HTML page in a temp folder, so a human can check the plan.

Usage: uv run spec2html.py .craft/draft/<item>.md [--no-open] [--out FILE]
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "arch" / "scripts"))
import arch2html  # noqa: E402 — the component map
from html_utils import esc, inline, md, pill, section, write  # noqa: E402
from md_utils import split_frontmatter, split_sections  # noqa: E402

ARCHITECTURE_FILE = ".craft/architecture.yaml"
PROMOTE = re.compile(r"open questions?|migration plan|data model|api contracts?|api changes", re.I)
OPEN = re.compile(r"verification|acceptance|open question|contract|migration", re.I)
KEY_KINDS = {"schema", "data-writer", "data-copy", "api", "event"}
CONTRACTS = re.compile(r"\s*[-*]\s+\*\*Contract changes|#{3,4}\s+Contract changes", re.I)
CONTRACT = re.compile(r"(?:\*\*)?(C\d+)\s+([\w-]+)\s*:\s*(?:\*\*)?\s*(.*)", re.S)


def promote_subsections(sections):
    """Lift decision-relevant ### subsections to just after the Review Brief."""
    lifted = []
    for s in sections:
        kept, cur = [], None
        for line in s["md"].splitlines():
            m = re.match(r"###\s+(.+?)\s*$", line)
            if m:
                cur = {"title": m.group(1), "md": []} if PROMOTE.search(m.group(1)) else None
                if cur:
                    lifted.append(cur)
                    continue
            elif re.match(r"#{1,2}\s", line):
                cur = None
            (cur["md"] if cur else kept).append(line)
        s["md"] = "\n".join(kept).strip()
    for s in lifted:
        s["md"] = "\n".join(s["md"]).strip()
    lifted = [s for s in lifted if s["md"]]
    at = next((i + 1 for i, s in enumerate(sections) if "review brief" in s["title"].lower()), 0)
    return sections[:at] + lifted + [s for s in sections[at:] if s["md"]]


def lift_contracts(brief):
    """Take the contract list out of the brief: (brief without it, items as text)."""
    lines = brief.splitlines()
    start = next((i for i, l in enumerate(lines) if CONTRACTS.match(l)), None)
    if start is None:
        return brief, []
    bullet = lines[start].lstrip()[0] != "#"
    indent = len(lines[start]) - len(lines[start].lstrip())
    items, end = [], start + 1
    for line in lines[start + 1:]:
        deeper = len(line) - len(line.lstrip()) > indent
        if line.strip() and (bullet and not deeper or not bullet and not (deeper or line.lstrip()[0] in "-*")):
            break
        end += 1
        b = re.match(r"\s*[-*]\s+(.*)", line)
        if b:
            items.append(b[1])
        elif items and line.strip():
            items[-1] += " " + line.strip()
    if not items:
        return brief, []
    return "\n".join(lines[:start] + lines[end:]).strip(), items


def contract_card(text):
    m = CONTRACT.match(text)
    kind = m[2].lower() if m else ""
    what, _, why = (m[3] if m else text).partition(" — ")
    head = (f'<div class="item-head"><span class="id">{esc(m[1])}</span>{pill(kind, "chip")}</div>' if m else "")
    return kind, (f'<div class="item {"red" if kind in KEY_KINDS else "yellow"}">{head}<div class="what">{inline(what)}</div>'
                  + (f'<div class="consequence">{inline(why)}</div>' if why else "") + "</div>")


def contract_cards(items):
    cards = [contract_card(i) for i in items]
    key = [c for k, c in cards if k in KEY_KINDS]
    other = [c for k, c in cards if k not in KEY_KINDS]
    out = f'<h3>Data model &amp; API changes</h3><div class="cards">{"".join(key)}</div>' if key else ""
    if other:
        out += f'<h3>{"Other contract changes" if key else "Contract changes"}</h3><div class="cards">{"".join(other)}</div>'
    return out


def repo_root(start):
    r = subprocess.run(["git", "-C", str(start), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(r.stdout.strip()) if r.returncode == 0 else None


def page_body(path):
    fm, text = split_frontmatter(path.read_text(encoding="utf-8"))
    title, sections = split_sections(text)
    sections = promote_subsections(sections)
    targets = [t.strip() for t in fm.get("target", "").split(",") if t.strip()]
    meta = [pill("blocked", "red")] if fm.get("blocked") else []
    meta += [pill(t, "chip") for t in targets]
    meta += [f'<span class="muted">{k} {esc(fm[k])}</span>' for k in ("created", "updated") if fm.get(k)]
    out = [f'<header class="narrow"><div class="kicker">Spec review</div><h1>{esc(title or path.name)}</h1>'
           f'<div class="meta">{"".join(meta)}</div></header><main class="narrow">']

    brief = next((s for s in sections if "review brief" in s["title"].lower()), None)
    if brief:
        rest, items = lift_contracts(brief["md"])
        out.append(f'<div class="card brief"><h2>Review brief</h2>{md(rest)}{contract_cards(items)}</div>')

    arch_file = (repo_root(path.parent) or path.parent) / ARCHITECTURE_FILE
    if arch_file.exists():
        m = arch2html.Architecture(yaml.safe_load(arch_file.read_text(encoding="utf-8")) or {})
        if m.components:
            out.append(section("Affected components", arch2html.mermaid(arch2html.impact_map(m, changed=targets))
                               + '<div class="legend">Highlighted: the spec\'s targets.</div>'))
    for s in sections:
        if s is not brief:
            out.append(section(s["title"] or "Notes", f'<div class="card">{md(s["md"])}</div>', open=bool(OPEN.search(s["title"]))))
    out.append(f'</main><footer class="narrow">{esc(path)}</footer>')
    return title or path.stem, "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--out", help="output file (default: <tmp>/craft-views/)")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    path = Path(args.file).resolve()
    title, body = page_body(path)
    write(f"spec: {title}", body, f"spec-{path.stem}", args.out, not args.no_open)


if __name__ == "__main__":
    main()
