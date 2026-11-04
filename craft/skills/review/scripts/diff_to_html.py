#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "markdown-it-py>=3", "pyyaml>=6"]
# ///
"""Render <item>.review.json as one HTML page in a temp folder: what changed, and is it risky?

Usage: uv run diff_to_html.py <item>.review.json [--spec FILE] [--repo DIR] [--editor E] [--no-open] [--out FILE]
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review as rv  # noqa: E402 — git, diff, triggers

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "arch3" / "scripts"))
import render  # noqa: E402 — the component map
from page import esc, md, pill, section, split_frontmatter, split_sections, write  # noqa: E402

EXCERPT_WINDOW = 15  # lines kept around the focus range when a hunk is long
SNIPPET_CONTEXT = 3
NEAR = 4  # lines shown around the focus before "show full hunk"
WHERE = re.compile(r"^(.+?):(\d+)(?:-(\d+))?$")
DATA_KINDS = {"schema", "data-writer", "data-copy"}
API_KINDS = {"api", "event"}
TIER = {"red": "🔴 red — walkthrough required", "yellow": "🟡 yellow — skim the flagged items", "green": "🟢 green — no triggers"}
TONE = {"red": "red", "yellow": "yellow", "green": "green", "high": "red", "medium": "yellow", "confirmed": "red",
        "plausible": "yellow", "fixed": "green", "pass": "green", "fail": "red", "not-run": "yellow",
        "accept": "green", "change": "red", "discuss": "yellow",
        "compatible": "green", "breaking": "red", "needs-migration": "yellow", "needs-versioning": "yellow"}


def tone(v):
    return TONE.get(str(v or "").lower(), "")


# ---------- code excerpts ----------

def trim(hunk, a, b):
    lines, last, keep = hunk["lines"], hunk["new"], []
    for i, l in enumerate(lines):
        last = l["n"] if l["n"] is not None else last
        if a - EXCERPT_WINDOW <= last <= b + EXCERPT_WINDOW:
            keep.append(i)
    return {"header": hunk["header"], "lines": lines[keep[0]:keep[-1] + 1] if keep else lines}


def excerpt(repo, head, diff, where):
    m = WHERE.match(where or "")
    if not m:
        return None
    path, a = m[1], int(m[2])
    b = int(m[3] or a)
    hits = [h for h in diff.get(path, []) if h["new"] <= b and a <= h["new"] + max(h["newLen"], 1) - 1]
    if hits:
        return {"file": path, "focus": (a, b), "hunks": [trim(h, a, b) for h in hits]}
    try:
        src = rv.git(repo, "show", f"{head}:{path}").splitlines()
    except RuntimeError:
        return {"file": path, "missing": True}
    lo, hi = max(1, a - SNIPPET_CONTEXT), min(len(src), b + SNIPPET_CONTEXT)
    return {"file": path, "focus": (a, b),
            "hunks": [{"header": f"{path} (unchanged code at {head[:8]})",
                       "lines": [{"t": " ", "o": None, "n": i, "s": src[i - 1]} for i in range(lo, hi + 1)]}]}


def diff_table(header, rows):
    return f'<table class="diff"><tr class="hdr"><td colspan="3">{esc(header)}</td></tr>{"".join(rows)}</table>'


def diff_row(line, focus):
    kind = {"+": "tadd", "-": "tdel"}.get(line["t"], "")
    hit = focus and line["n"] is not None and focus[0] <= line["n"] <= focus[1]
    return (f'<tr class="{kind}{" focus" if hit else ""}"><td class="ln">{line["o"] or ""}</td><td class="ln">{line["n"] or ""}</td>'
            f'<td class="code">{esc(line["t"])} {esc(line["s"])}</td></tr>')


def excerpt_html(x):
    if not x:
        return ""
    if x.get("missing"):
        return f'<div class="muted">{esc(x["file"])}: not found at head</div>'
    focus, out = x.get("focus"), []
    for hunk in x["hunks"]:
        last, near = 0, []
        for line in hunk["lines"]:
            last = line["n"] if line["n"] is not None else last
            if not focus or focus[0] - NEAR <= last <= focus[1] + NEAR:
                near.append(diff_row(line, focus))
        out.append(diff_table(hunk["header"], near))
        hidden = len(hunk["lines"]) - len(near)
        if hidden:
            out.append(f"<details><summary>show full hunk (+{hidden} lines)</summary>"
                       + diff_table(hunk["header"], [diff_row(l, focus) for l in hunk["lines"]]) + "</details>")
    return f'<div class="excerpt">{"".join(out)}</div>'


# ---------- gathering ----------

def gather(review, repo, raw):
    """Excerpts by item id, changed files, and which trigger kinds each file matched."""
    got = {"notes": [], "excerpts": {}, "files": [], "trigger_files": {}, "file_diffs": {}, "range": "", "changed": set()}
    head = rv.resolve(repo, review.get("head")) or rv.resolve(repo, "HEAD")
    base = rv.resolve(repo, review.get("base")) or (rv.default_base(repo, head) if head else None)
    if not head or not base:
        got["notes"].append("Base commit not found: code excerpts unavailable.")
        return got
    got["range"] = f"{base[:8]}..{head[:8]}"
    diff = rv.parse_diff(rv.git(repo, "diff", "--no-color", "-U3", base, head))
    for group in ("deviations", "contracts", "findings", "blast"):
        for entry in review.get(group, []):
            x = excerpt(repo, head, diff, entry.get("where"))
            if x and entry.get("id"):
                got["excerpts"][entry["id"]] = x
    units, triggers = rv.units_of(raw), rv.triggers_of(raw)
    for status, file in rv.changed_files(repo, base, head):
        comp = rv.component_of(file, units)
        got["changed"].add(comp)
        got["files"].append((status, file, comp))
        for kind, globs in triggers.items():
            if any(rv.matches(file, g) for g in globs):
                got["trigger_files"].setdefault(kind, []).append(file)
                if kind == "schema":  # migrations are short and decisive: show them whole
                    got["file_diffs"][file] = {"file": file, "hunks": diff.get(file, [])}
    return got


# ---------- the page ----------

class Page:
    def __init__(self, review, got, repo, editor):
        self.r, self.got, self.repo, self.editor = review, got, repo, editor

    def loc(self, where):
        if not where:
            return ""
        m = WHERE.match(where)
        if not m or self.editor == "none":
            return f'<code class="loc">{esc(where)}</code>'
        abs_path = f"{self.repo}/{m[1]}"
        href = (f"idea://open?file={quote(abs_path, safe='')}&line={m[2]}" if self.editor == "idea"
                else f"{self.editor}://file{quote(abs_path)}:{m[2]}")
        return f'<a class="loc mono" href="{esc(href)}">{esc(where)}</a>'

    def verdict(self, item_id):
        v = self.r.get("verdicts", {}).get(item_id)
        return pill(f"verdict: {v}", tone(v)) if v else ""

    def x(self, item_id):
        return excerpt_html(self.got["excerpts"].get(item_id))

    def deviation(self, d):
        return (f'<div class="item red"><div class="item-head"><span class="id">{esc(d.get("id", ""))}</span>{pill("deviation", "red")}'
                f'{self.loc(d.get("where"))}{self.verdict(d.get("id"))}</div><div class="what">{esc(d.get("what", ""))}</div>{self.x(d.get("id"))}</div>')

    def contract(self, c):
        pills = pill(c.get("kind") or "contract", "chip")
        pills += pill(c["compat"], tone(c["compat"])) if c.get("compat") else ""
        pills += pill(f"migration: {c['migration']}") if c.get("migration") else ""
        why = f'<div class="consequence">{esc(c["consequence"])}</div>' if c.get("consequence") else ""
        return (f'<div class="item red"><div class="item-head"><span class="id">{esc(c.get("id", ""))}</span>{pills}{self.loc(c.get("where"))}'
                f'{self.verdict(c.get("id"))}</div><div class="what">{esc(c.get("what", ""))}</div>{why}{self.x(c.get("id"))}</div>')

    def finding(self, f):
        status = f.get("status") or "plausible"
        colour = tone(status if status in ("confirmed", "fixed") else f.get("severity"))
        facts = "".join(f"<dt>{k}</dt><dd>{esc(f[v])}</dd>" for k, v in (("Invariant", "invariant"), ("Scenario", "scenario"),
                        ("Consequence", "consequence"), ("Fix", "fix")) if f.get(v))
        facts += f'<dt>Test</dt><dd><code>{esc(f["test"])}</code></dd>' if f.get("test") else ""
        return (f'<div class="item {colour}"><div class="item-head"><span class="id">{esc(f.get("id", ""))}</span>'
                f'{pill(f.get("severity") or "?", tone(f.get("severity")))}{pill(status, tone(status))}{self.loc(f.get("where"))}{self.verdict(f.get("id"))}</div>'
                f'<dl class="facts">{facts}</dl>{self.x(f.get("id"))}</div>')

    def blast(self, b):
        callers = "".join(f"<div>{self.loc(c)}</div>" for c in b.get("callers", []))
        covered = "".join(f"<div><code>{esc(t)}</code></div>" for t in b.get("covered_by", [])) or pill("no covering test", "yellow")
        return (f'<div class="item {"" if b.get("covered_by") else "yellow"}"><div class="item-head"><span class="id">{esc(b.get("id", ""))}</span>'
                f'<code>{esc(b.get("symbol", ""))}</code>{self.loc(b.get("where"))}{self.verdict(b.get("id"))}</div><div>{esc(b.get("change", ""))}</div>'
                f'<dl class="facts">{f"<dt>Callers</dt><dd>{callers}</dd>" if callers else ""}<dt>Covered by</dt><dd>{covered}</dd></dl>{self.x(b.get("id"))}</div>')

    def key_group(self, title, kinds, files):
        """Contracts plus the files the diff actually touched, so a change the review failed to report still shows."""
        cs = [c for c in self.r.get("contracts", []) if c.get("kind") in kinds]
        if not cs and not files:
            return ""
        out = f"<h3>{esc(title)}</h3>"
        if files and not cs:
            out += (f'<div class="note">{len(files)} changed file(s) match the {esc(title)} triggers, but the review reports '
                    f"no {esc(title)} change — check before approving.</div>")
        out += f'<div class="items">{"".join(self.contract(c) for c in cs)}</div>'
        if files:
            shown = {self.got["excerpts"].get(c.get("id"), {}).get("file") for c in cs}
            whole = "".join(excerpt_html(self.got["file_diffs"][f]) for f in files if f in self.got["file_diffs"] and f not in shown)
            out += ('<div class="card" style="margin-top:10px"><div class="kicker">Changed files</div>'
                    + "".join(f"<div>{self.loc(f'{f}:1')}</div>" for f in files) + whole + "</div>")
        return out


def build(review, got, repo, raw, spec_path, editor):
    p, tf = Page(review, got, repo, editor), got["trigger_files"]
    all_contracts = review.get("contracts", [])
    key = [c for c in all_contracts if c.get("kind") in DATA_KINDS | API_KINDS]
    other = [c for c in all_contracts if c not in key]
    data_files, api_files = tf.get("schema", []), [*tf.get("api", []), *tf.get("event", [])]
    rank = lambda f: {"confirmed": 0, "fixed": 6}.get(f.get("status"), 3) + {"high": 0, "medium": 1, "low": 2}.get(f.get("severity"), 2)
    findings = sorted(review.get("findings", []), key=rank)

    groups = []  # anchor, title, count, html
    if key or data_files or api_files:
        groups.append(("data-api", "Data model & API", len(key),
                       p.key_group("Data model", DATA_KINDS, data_files) + p.key_group("API", API_KINDS, api_files)))
    for anchor, title, items, draw in (("deviations", "Deviations from spec", review.get("deviations", []), p.deviation),
                                       ("contracts", "Other contract changes", other, p.contract),
                                       ("findings", "Findings", findings, p.finding),
                                       ("blast", "Blast radius", review.get("blast", []), p.blast)):
        if items:
            groups.append((anchor, title, len(items), f'<div class="items">{"".join(draw(i) for i in items)}</div>'))

    item = review.get("item") or "branch"
    tier = review.get("tier")
    rng = f'<span class="mono muted">{esc(got["range"])}</span>' if got["range"] else ""
    out = [f'<header class="narrow"><div class="kicker">Change review</div><h1>{esc(item)}</h1><div class="meta">'
           f'{pill(TIER.get(tier, tier or "tier: n/a"), f"big {tone(tier)}")}{rng}<span class="muted">{len(got["files"])} files</span></div></header><main class="narrow">']
    if review.get("triggers"):
        out.append('<div class="card"><div class="kicker">Why this tier</div><div class="chips">'
                   + "".join(pill(t["what"], tone(t["tier"])) for t in review["triggers"]) + "</div></div>")
    out += [f'<div class="note">{esc(n)}</div>' for n in got["notes"]]
    if groups:
        out.append('<p class="walk"><span class="muted">Walk order:</span> '
                   + "".join(f'<a href="#{a}">{pill(f"{t} · {n}", "red" if a == "data-api" else "")}</a> ' for a, t, n, _ in groups) + "</p>")
    if spec_path:
        _, sections = split_sections(split_frontmatter(spec_path.read_text(encoding="utf-8"))[1])
        brief = next((s["md"] for s in sections if "review brief" in s["title"].lower()), "")
        if brief:
            out.append(section("Spec brief", f'<div class="card">{md(brief)}</div>', open=False))
    out += [section(t, h, n or None, anchor=a) for a, t, n, h in groups]

    if raw and raw.get("components"):
        edges = [tuple(x.strip() for x in e.split("->", 1)) for e in review.get("new_edges", []) if "->" in e]
        count = f"{len(edges)} new edge{'s' * (len(edges) > 1)}" if edges else None
        out.append(section("Architecture impact", render.mermaid(render.impact_map(render.Architecture(raw), got["changed"], edges))
                           + '<div class="legend">Highlighted: components this diff touches. Red: dependencies new in this change.</div>', count))
    if review.get("evidence"):
        rows = "".join(f'<tr><td class="id">{esc(e.get("ac", ""))}</td><td>{esc(e.get("criterion", ""))}</td>'
                       f'<td>{f"<code>{esc(e["command"])}</code>" if e.get("command") else "manual"}</td>'
                       f'<td>{pill(e.get("result") or "not-run", tone(e.get("result")))}</td></tr>' for e in review["evidence"])
        out.append(section("Acceptance evidence", f"<table><tr><th>AC</th><th>Criterion</th><th>Command</th><th>Result</th></tr>{rows}</table>", len(review["evidence"])))
    if review.get("not_checked"):
        out.append(section("Not checked", '<div class="card"><ul>' + "".join(f"<li>{esc(n)}</li>" for n in review["not_checked"]) + "</ul></div>", len(review["not_checked"])))
    if got["files"]:
        by_comp = {}
        for status, file, comp in got["files"]:
            by_comp.setdefault(comp or "(outside architecture.yaml)", []).append((status, file))
        body = "".join(f"<h3>{esc(c)}</h3>" + "".join(
            f'<div class="mono">{pill(s, {"A": "green", "D": "red"}.get(s, ""))} {esc(f)}</div>' for s, f in fs) for c, fs in by_comp.items())
        out.append(section("Files changed", f'<div class="card">{body}</div>', len(got["files"]), open=False))
    out.append(f'</main><footer class="narrow">{esc(spec_path or "")}</footer>')
    return item, "".join(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--spec", help="the item's spec (default: found by item name)")
    ap.add_argument("--repo", help="git repo (default: the review file's repo)")
    ap.add_argument("--editor", default=os.environ.get("CRAFT_EDITOR", "vscode"), choices=["vscode", "cursor", "idea", "none"],
                    help="file:line links open in this editor")
    ap.add_argument("--out", help="output file (default: <tmp>/craft-views/)")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()

    path = Path(args.file).resolve()
    review = json.loads(path.read_text(encoding="utf-8"))
    repo = Path(args.repo).resolve() if args.repo else rv.repo_root(path.parent)
    if not repo:
        sys.exit(f"{path} is not in a git repository; pass --repo")
    name = review.get("item") or path.name.removesuffix(".review.json")
    spec_path = Path(args.spec) if args.spec else next(
        (p for p in [path.with_name(f"{name}.md"), *repo.glob(f"docs/*/{name}.md")] if p.exists()), None)
    head = rv.resolve(repo, review.get("head")) or rv.resolve(repo, "HEAD")
    raw = rv.raw_at(repo, head, rv.ARCHITECTURE_FILE) if head else None
    item, body = build(review, gather(review, repo, raw), repo, raw, spec_path, args.editor)
    write(f"changes: {item}", body, f"changes-{name}", args.out, not args.no_open)


if __name__ == "__main__":
    main()
