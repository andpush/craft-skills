#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""Render a craft review page — spec, change or model — into one HTML file and open it.

  view.py spec   <item.md>              [--model docs/architecture.yaml]
  view.py change <item.review.json>     [--spec item.md] [--repo DIR]
  view.py model  [docs/architecture.yaml]

Run with `uv run view.py …`. Markdown and mermaid render in the browser; output goes to a temp
dir, never the repo.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import webbrowser
from fnmatch import fnmatchcase
from pathlib import Path

import yaml

TEMPLATE = Path(__file__).with_name("template.html")
MODEL_FILE = "docs/architecture.yaml"
EXCERPT_WINDOW = 15  # lines kept around the focus range when a hunk is long
SNIPPET_CONTEXT = 3

# Changed paths that make a change red. A model's review_triggers add project paths to these.
DEFAULT_TRIGGERS = {
    "dependency": ["package.json", "**/package.json", "*lock.json", "*lock.yaml", "yarn.lock", "**/build.gradle*",
                   "**/settings.gradle*", "**/libs.versions.toml", "**/pom.xml", "go.mod", "go.sum", "Cargo.toml",
                   "Cargo.lock", "pyproject.toml", "uv.lock", "requirements*.txt", "Gemfile*", "**/*.csproj",
                   "pubspec.yaml", "Package.swift"],
    "schema": ["**/migration/**", "**/migrations/**", "**/*.sql", "**/schema.prisma"],
    "api": ["**/openapi*.yaml", "**/openapi*.yml", "**/openapi*.json", "**/*.proto", "**/*.graphql"],
    "security": ["**/auth/**", "**/security/**", "**/*crypto*", "**/*secret*", "**/.env*"],
    "ci": [".github/workflows/**", ".gitlab-ci.yml", "Jenkinsfile", ".circleci/**"],
    "arch-check": ["**/architecture.gate.json", "**/architecture.baseline", "**/archunit_store/**", "**/.dependency-cruiser*", "**/ArchitectureTest*"],
}


# ---------- markdown ----------

def split_frontmatter(md: str) -> tuple[dict, str]:
    m = re.match(r"---\n(.*?)\n---\n?", md, re.S)
    if not m:
        return {}, md
    fm = {}
    for line in m.group(1).splitlines():
        key, sep, val = line.partition(":")
        if sep and key and not key[0].isspace():
            fm[key.strip()] = val.split(" #", 1)[0].strip()
    return fm, md[m.end():]


def split_sections(body: str) -> tuple[str, list[dict]]:
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


PROMOTE = re.compile(r"open questions?|migration plan|data model|api contracts?|api changes", re.I)


def promote_subsections(sections: list[dict]) -> list[dict]:
    """Lift decision-relevant ### subsections (open questions, migration plan, data, API) to the top."""
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


# ---------- model (docs/architecture.yaml) ----------

def as_list(v) -> list[str]:
    if v is None:
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


ARROW = re.compile(r"^\s*(.+?)\s*(->|~>)\s*(.+?)\s*$")


def pairs(items) -> list[tuple[str, str]]:
    """`a -> b: label` items: YAML reads them as one-key maps, or as plain strings without a label."""
    out = []
    for it in items or []:
        if isinstance(it, dict):
            out += [(str(k), "" if v is None else str(v)) for k, v in it.items()]
        else:
            out.append((str(it), ""))
    return out


def arrows(items, where: str, problems: list[str]) -> list[dict]:
    steps = []
    for head, label in pairs(items):
        m = ARROW.match(head)
        if not m:
            problems.append(f"{where}: '{head}' is not 'a -> b' or 'a ~> b'")
            continue
        steps.append({"from": m[1], "to": m[3], "async": m[2] == "~>", "label": label})
    return steps


def from_arch_define(raw: dict) -> dict:
    """Convert the arch-define format (components as a list) to the shape load_model reads."""
    def text(v) -> str:
        return "; ".join(as_list(v))

    def heads(refs) -> list[str]:
        """'payments.payments-api' -> payments; 'shared-kernel test' -> shared-kernel."""
        return list(dict.fromkeys(str(r).split()[0].split(".")[0] for r in refs or []))

    def dep_refs(unit: dict) -> list:
        return [*(unit.get("uses") or []), *(unit.get("calls") or [])]

    comps, entities = {}, {}

    def add_entities(store: dict, owner: str) -> None:
        for name, fields in (store.get("entities") or {}).items():
            refs = [m[1].split(".")[0] for m in (re.search(r"->\s*(\S+)", str(f)) for f in fields or []) if m]
            entities[str(name)] = {"owner": owner, "refs": list(dict.fromkeys(refs)), "states": []}

    for c in raw["components"]:
        if not (isinstance(c, dict) and c.get("component")):
            continue
        name, modules = str(c["component"]), c.get("modules") or []
        own = {str(m.get("module")) for m in modules} | {name}
        refs = dep_refs(c) + [r for m in modules for r in dep_refs(m)]
        comps[name] = {"does": text(c.get("does")), "path": c.get("source_path"),
                       "depends_on": [d for d in heads(refs) if d not in own]}
        for store in c.get("datastores") or []:
            add_entities(store, name)
    for m in raw.get("modules") or []:   # root modules: shared libraries; only directory globs map to files
        comps[str(m.get("module"))] = {"does": text(m.get("does")), "depends_on": heads(dep_refs(m)),
                                       "path": [p for p in as_list(m.get("packages")) if "/" in p]}
    for store in raw.get("datastores") or []:
        add_entities(store, str(store.get("schema_owner") or ""))
    for key, steps in (raw.get("states") or {}).items():
        if str(key).split(".")[0] in entities:
            entities[str(key).split(".")[0]]["states"] += steps or []

    outside = {str(k): {"does": text(a.get("does")), "calls": heads(a.get("uses"))}
               for k, a in (raw.get("actors") or {}).items()}
    outside |= {str(k): {"does": text(e.get("does")), "calls": heads(e.get("calls"))}
                for k, e in (raw.get("external") or {}).items()}
    rules = [{"id": r.get("rule"), "level": r.get("level", "must"), "rule": r.get("statement", ""),
              "scope": [f"{k}: {text(v)}" for k, v in (r.get("applies_to") or {}).items()],
              "checked_by": r.get("check") or "manual"} for r in raw.get("rules") or []]
    stores = [*(raw.get("datastores") or []), *(s for c in raw["components"] for s in c.get("datastores") or [])]
    surfaces = [s for c in raw["components"] for f in ("endpoints", "ui_endpoints") for s in (c.get(f) or {}).values()]
    triggers = {str(k): as_list(v) for k, v in (raw.get("review_triggers") or {}).items()}
    triggers.setdefault("api", []).extend(s["spec"] for s in surfaces if s.get("spec"))
    triggers.setdefault("schema", []).extend(f"{s['source_path'].rstrip('/')}/**" for s in stores if s.get("source_path"))
    triggers.setdefault("arch-check", []).extend(r["check"] for r in raw.get("rules") or [] if r.get("check"))
    return {"system": raw.get("system"), "does": raw.get("summary"), "external": outside, "components": comps,
            "entities": entities, "flows": raw.get("flows"), "rules": rules, "review_triggers": triggers}


def load_model(path: Path | None) -> dict:
    """Normalize docs/architecture.yaml; collect problems instead of failing so the page still renders."""
    empty = {"system": "", "does": "", "external": [], "components": [], "entities": [], "flows": [], "rules": [],
             "triggers": DEFAULT_TRIGGERS, "problems": [], "file": None}
    if not path or not path.exists():
        return empty
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        return {**empty, "file": str(path), "problems": [f"{path.name} is not valid YAML: {e}"]}
    problems = []
    arch_define = isinstance(raw.get("components"), list)
    if arch_define:
        raw = from_arch_define(raw)

    ext = []
    for name, e in (raw.get("external") or {}).items():
        e = e if isinstance(e, dict) else {"does": e}
        ext.append({"name": str(name), "does": str(e.get("does") or ""), "calls": as_list(e.get("calls"))})
    comps = [{"name": str(name), "paths": as_list(c.get("path")), "deps": as_list(c.get("depends_on")),
              "does": c.get("does", "")}
             for name, c in (raw.get("components") or {}).items() if isinstance(c, dict)]
    names, outside = {c["name"] for c in comps}, {e["name"] for e in ext}
    deps = {c["name"]: set(c["deps"]) for c in comps}
    for c in comps:
        problems += [f"{c['name']} depends on unknown '{d}'" for d in c["deps"] if d not in names | outside]
        if not c["paths"]:
            problems.append(f"{c['name']} has no path")
    for e in ext:
        problems += [f"external {e['name']} calls unknown component '{d}'" for d in e["calls"] if d not in names]

    ents = []
    for name, e in (raw.get("entities") or {}).items():
        e = e if isinstance(e, dict) else {}
        copies = []
        for of, how in pairs(e.get("copies")):
            kind, _, why = how.strip().partition(" ")
            copies.append({"of": of, "kind": kind, "why": why.strip(" —–-")})
        ents.append({"name": str(name), "owner": str(e.get("owner") or ""), "has": as_list(e.get("has")),
                     "refs": as_list(e.get("refs")), "copies": copies,
                     "states": arrows(e.get("states"), f"{name} states", problems)})
    by_name = {e["name"]: e for e in ents}
    for e in ents:
        if e["owner"] not in names:
            problems.append(f"entity {e['name']} has unknown owner '{e['owner']}'")
        for other in e["has"] + e["refs"] + [c["of"].split(".")[0] for c in e["copies"]]:
            if other not in by_name:
                problems.append(f"entity {e['name']} refers to unknown entity '{other}'")
        for part in e["has"]:
            if part in by_name and by_name[part]["owner"] != e["owner"]:
                problems.append(f"{e['name']} has {part}, but they have different owners — use refs")

    flows = []
    for title, items in (raw.get("flows") or {}).items():
        steps = arrows(items, f"flow '{title}'", problems)
        for s in steps:
            a, b = s["from"], s["to"]
            problems += [f"flow '{title}': unknown participant '{n}'" for n in (a, b) if n not in names | outside]
            if s["async"] or a == b:
                continue
            if a in names and b in names | outside and b not in deps[a]:
                problems.append(f"flow '{title}': {a} -> {b} is not in {a}.depends_on")
            if a in outside and b in names and b not in next(e["calls"] for e in ext if e["name"] == a):
                problems.append(f"flow '{title}': {a} -> {b} is not in external {a}.calls")
        flows.append({"title": str(title), "steps": steps})

    rules = []
    for r in raw.get("rules") or []:
        checker = str(r.get("checked_by", "") or "")
        rules.append({"id": str(r.get("id", "?")), "level": str(r.get("level", "")).upper(), "scope": as_list(r.get("scope")),
                      "text": r.get("rule", ""), "checker": "" if checker == "manual" else checker,
                      "manual": checker in ("", "manual"), "exceptions": r.get("exceptions", "")})
        if rules[-1]["level"] == "MUST" and rules[-1]["manual"]:
            problems.append(f"{rules[-1]['id']} is MUST but has no checker")
    triggers = {k: list(v) for k, v in DEFAULT_TRIGGERS.items()}
    for kind, globs in (raw.get("review_triggers") or {}).items():
        triggers.setdefault(str(kind), []).extend(g for g in as_list(globs) if g not in triggers.get(str(kind), []))
    if arch_define:   # its rules differ (a must rule without a check goes to review); validate.py checks this format
        problems = []
    return {"system": str(raw.get("system") or ""), "does": str(raw.get("does") or ""), "external": ext,
            "components": comps, "entities": ents, "flows": flows, "rules": rules, "triggers": triggers,
            "problems": problems, "file": str(path)}


def find_model(start: Path, explicit: str | None) -> Path | None:
    if explicit:
        return Path(explicit)
    root = repo_root(start) or start
    for p in [start, *start.parents]:
        if (p / MODEL_FILE).exists():
            return p / MODEL_FILE
        if p == root:
            break
    return None


def mermaid(comps: list[dict], changed=(), new_edges=()) -> str:
    if not comps:
        return ""
    by_name = {c["name"]: c for c in comps}
    names = [c["name"] for c in comps]
    for edge in new_edges:
        names += [n for n in edge if n not in names]
    nid = {n: f"n{i}" for i, n in enumerate(names)}
    out = ["flowchart LR"]
    for n in names:
        out.append(f'  {nid[n]}["{esc(n)}"]')
    links = 0
    for c in comps:
        for d in c["deps"]:
            if d in nid:
                out.append(f"  {nid[c['name']]} --> {nid[d]}")
                links += 1
    for a, b in new_edges:
        out.append(f"  {nid[a]} -. new .-> {nid[b]}")
        out.append(f"  linkStyle {links} stroke:#dc2626,stroke-width:2px,color:#dc2626")
        links += 1
    out.append("  classDef changed fill:#fde68a,stroke:#b45309,stroke-width:2px,color:#111")
    out.append("  classDef unknown stroke-dasharray:4 3")
    hit = [nid[n] for n in names if n in changed]
    if hit:
        out.append(f"  class {','.join(hit)} changed")
    unknown = [nid[n] for n in names if n not in by_name]
    if unknown:
        out.append(f"  class {','.join(unknown)} unknown")
    return "\n".join(out)


def esc(text: str) -> str:
    return str(text).replace('"', "#quot;").replace(";", ",")


def context_mermaid(m: dict) -> str:
    if not m["external"]:
        return ""
    users: dict[str, list[str]] = {}
    for c in m["components"]:
        for d in c["deps"]:
            users.setdefault(d, []).append(c["name"])
    system = m["system"] or "system"
    out = ["flowchart LR", f'  ctx[["{esc(system)}"]]']
    for i, e in enumerate(m["external"]):
        label = esc(e["name"]) + (f"<br/>{esc(e['does'])}" if e["does"] else "")
        out.append(f'  cx{i}(["{label}"])' if e["calls"] else f'  cx{i}["{label}"]')
        if e["calls"]:
            out.append(f'  cx{i} -->|"{esc(", ".join(e["calls"]))}"| ctx')
        if users.get(e["name"]):
            out.append(f'  ctx -->|"{esc(", ".join(users[e["name"]]))}"| cx{i}')
    out.append("  classDef sys fill:#2f5bd3,stroke:#2f5bd3,color:#fff,font-weight:bold")
    out.append("  class ctx sys")
    return "\n".join(out)


def entities_mermaid(m: dict) -> str:
    ents = m["entities"]
    if not ents:
        return ""
    eid = {e["name"]: f"en{i}" for i, e in enumerate(ents)}
    out, groups = ["flowchart LR"], {}
    for e in ents:
        groups.setdefault(e["owner"], []).append(e)
    for j, (owner, members) in enumerate(groups.items()):
        out.append(f'  subgraph eg{j}["{esc(owner or "no owner")}"]')
        out += [f'    {eid[e["name"]]}["{esc(e["name"])}{" ⟳" if e["states"] else ""}"]' for e in members]
        out.append("  end")
    links, copies = 0, []
    for e in ents:
        a = eid[e["name"]]
        for b in e["has"]:
            if b in eid:
                out.append(f"  {a} -->|has| {eid[b]}")
                links += 1
        for b in e["refs"]:
            if b in eid:
                out.append(f"  {a} -.->|ref| {eid[b]}")
                links += 1
        for c in e["copies"]:
            target, _, field = c["of"].partition(".")
            if target in eid:
                out.append(f'  {a} ==>|"copies {esc(field or target)} · {esc(c["kind"])}"| {eid[target]}')
                copies.append(links)
                links += 1
    if copies:
        out.append(f"  linkStyle {','.join(map(str, copies))} stroke:#d97706,color:#d97706")
    return "\n".join(out)


def state_mermaid(steps: list[dict], prefix: str) -> str:
    sid: dict[str, str] = {}
    for s in steps:
        for n in (s["from"], s["to"]):
            sid.setdefault(n, f"{prefix}s{len(sid)}")
    out = ["stateDiagram-v2", "  direction LR"]
    out += [f'  state "{esc(n)}" as {i}' for n, i in sid.items()]
    out.append(f"  [*] --> {sid[steps[0]['from']]}")
    out += [f"  {sid[s['from']]} --> {sid[s['to']]}" + (f": {esc(s['label'])}" if s["label"] else "") for s in steps]
    sources = {s["from"] for s in steps}
    out += [f"  {i} --> [*]" for n, i in sid.items() if n not in sources]
    return "\n".join(out)


def sequence_mermaid(steps: list[dict], m: dict, prefix: str) -> str:
    actors = {e["name"] for e in m["external"] if e["calls"]}
    pid: dict[str, str] = {}
    out = ["sequenceDiagram", "  autonumber"]
    for s in steps:
        for n in (s["from"], s["to"]):
            if n not in pid:
                pid[n] = f"{prefix}p{len(pid)}"
                out.append(f"  {'actor' if n in actors else 'participant'} {pid[n]} as {n}")
    out += [f"  {pid[s['from']]}{'-)' if s['async'] else '->>'}{pid[s['to']]}: {esc(s['label']) or ' '}" for s in steps]
    return "\n".join(out)


# ---------- decisions (docs/adr) ----------

ADR_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$")
REJECTED = re.compile(r"rejected|options|alternatives", re.I)


def load_decisions(root: Path) -> list[dict]:
    """ADRs in date order: the title is the decision, rejected options are its side branches."""
    adrs = []
    for p in sorted((root / "docs" / "adr").glob("*.md")):
        m = ADR_NAME.match(p.name)
        if not m:
            continue
        fm, body = split_frontmatter(p.read_text(encoding="utf-8"))
        title, sections = split_sections(body)
        rejected = []
        for s in sections:
            if REJECTED.search(s["title"]):
                for line in s["md"].splitlines():
                    b = re.match(r"[-*]\s+(.+)", line)
                    if b:
                        what, why = (re.split(r"\s+(?:—|–|--?)\s+", b[1], maxsplit=1) + [""])[:2]
                        rejected.append({"what": what.replace("**", ""), "why": why})
        sup = [x.strip().removesuffix(".md") for x in fm.get("supersedes", "").strip("[]").split(",") if x.strip()]
        adrs.append({"date": m[1], "slug": p.stem, "title": title or m[2], "file": str(p.relative_to(root)),
                     "supersedes": sup, "rejected": rejected, "superseded_by": None})
    for a in adrs:
        for old in a["supersedes"]:
            for b in adrs:
                if b["slug"] == old or b["slug"].endswith("-" + old):
                    b["superseded_by"] = a["slug"]
    return adrs


def matches(path: str, glob: str) -> bool:
    return fnmatchcase(path, glob) or (glob.startswith("**/") and fnmatchcase(path, glob[3:]))


def component_of(path: str, comps: list[dict]) -> str | None:
    best, size = None, -1
    for c in comps:
        for p in c["paths"]:
            if "*" in p:
                if matches(path, p) and len(p) > size:
                    best, size = c["name"], len(p)
                continue
            p = p.rstrip("/")
            if (path == p or path.startswith(p + "/")) and len(p) > size:
                best, size = c["name"], len(p)
    return best


# ---------- git ----------

def git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stderr.strip() or f"git {' '.join(args)} failed")
    return r.stdout


def repo_root(start: Path) -> Path | None:
    try:
        return Path(git(start, "rev-parse", "--show-toplevel").strip())
    except (RuntimeError, FileNotFoundError):
        return None


def resolve(repo: Path, ref: str | None) -> str | None:
    if not ref:
        return None
    try:
        return git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}").strip()
    except RuntimeError:
        return None


def default_base(repo: Path, head: str) -> str | None:
    for main in ("main", "master", "origin/main", "origin/master"):
        try:
            return git(repo, "merge-base", main, head).strip()
        except RuntimeError:
            continue
    return None


def parse_diff(text: str) -> dict[str, list[dict]]:
    files: dict[str, list[dict]] = {}
    cur = hunk = None
    old_path = None
    o = n = 0
    for line in text.splitlines():
        if line.startswith("diff --git"):
            cur = hunk = None
            continue
        if hunk is None and line.startswith("--- "):
            old_path = line[4:].removeprefix("a/")
            continue
        if hunk is None and line.startswith("+++ "):
            path = line[4:].removeprefix("b/")
            cur = files.setdefault(old_path if path == "/dev/null" else path, [])
            continue
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m and cur is not None:
            hunk = {"header": line, "new": int(m[3]), "newLen": int(m[4] if m[4] is not None else 1), "lines": []}
            cur.append(hunk)
            o, n = int(m[1]), int(m[3])
            continue
        if hunk is not None and line[:1] in ("+", "-", " "):
            t = line[:1]
            hunk["lines"].append({"t": t, "o": o if t != "+" else None, "n": n if t != "-" else None, "s": line[1:]})
            o += t != "+"
            n += t != "-"
    return files


def trim(hunk: dict, a: int, b: int) -> dict:
    lines, last_n, keep = hunk["lines"], hunk["new"], []
    for i, l in enumerate(lines):
        last_n = l["n"] if l["n"] is not None else last_n
        if a - EXCERPT_WINDOW <= last_n <= b + EXCERPT_WINDOW:
            keep.append(i)
    if not keep or len(keep) == len(lines):
        return {"header": hunk["header"], "lines": lines}
    return {"header": hunk["header"], "lines": lines[keep[0]:keep[-1] + 1], "truncated": True}


WHERE = re.compile(r"^(.+?):(\d+)(?:-(\d+))?$")


def excerpt(repo: Path, head: str, diff: dict, where: str | None) -> dict | None:
    m = WHERE.match(where or "")
    if not m:
        return None
    path, a = m[1], int(m[2])
    b = int(m[3] or a)
    hits = [h for h in diff.get(path, []) if h["new"] <= b and a <= h["new"] + max(h["newLen"], 1) - 1]
    if hits:
        return {"file": path, "kind": "diff", "focus": [a, b], "hunks": [trim(h, a, b) for h in hits]}
    try:
        src = git(repo, "show", f"{head}:{path}").splitlines()
    except RuntimeError:
        return {"file": path, "kind": "missing", "focus": [a, b]}
    lo, hi = max(1, a - SNIPPET_CONTEXT), min(len(src), b + SNIPPET_CONTEXT)
    return {"file": path, "kind": "snippet", "focus": [a, b],
            "hunks": [{"header": f"{path} (unchanged code at {head[:8]})",
                       "lines": [{"t": " ", "o": None, "n": i, "s": src[i - 1]} for i in range(lo, hi + 1)]}]}


# ---------- pages ----------

def spec_page(args) -> tuple[str, dict]:
    path = Path(args.file).resolve()
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    title, sections = split_sections(body)
    sections = promote_subsections(sections)
    model = load_model(find_model(path.parent, args.model))
    comps = model["components"]
    wanted = {t.lower() for t in re.split(r"[,\s/]+", fm.get("target", "")) if t}
    targets = [c["name"] for c in comps if c["name"].lower() in wanted] or sorted(wanted)
    return path.stem, {
        "kind": "spec", "file": str(path), "title": title, "frontmatter": fm, "sections": sections,
        "targets": targets, "diagram": mermaid(comps, changed=set(targets)),
    }


def change_page(args) -> tuple[str, dict]:
    path = Path(args.file).resolve()
    review = json.loads(path.read_text(encoding="utf-8"))
    repo = Path(args.repo).resolve() if args.repo else repo_root(path.parent)
    payload = {"kind": "change", "review": review, "excerpts": {}, "files": [], "diagram": "",
               "trigger_files": {}, "file_diffs": {}, "repo": str(repo) if repo else None, "notes": []}
    item = review.get("item") or path.name.removesuffix(".review.json")
    payload["title"] = item

    spec_path = Path(args.spec) if args.spec else next(
        (p for p in [path.with_name(f"{item}.md"), *(repo.glob(f"docs/*/{item}.md") if repo else [])] if p.exists()), None)
    if spec_path:
        _, body = split_frontmatter(spec_path.read_text(encoding="utf-8"))
        title, sections = split_sections(body)
        brief = next((s["md"] for s in sections if "review brief" in s["title"].lower()), "")
        payload["spec"] = {"file": str(spec_path), "title": title, "brief": brief}

    model = load_model(find_model(repo or path.parent, args.model))
    comps = model["components"]
    new_edges = [tuple(x.strip() for x in e.split("->", 1)) for e in review.get("new_edges", []) if "->" in e]

    if not repo:
        payload["notes"].append("Not a git repository: code excerpts unavailable.")
        payload["diagram"] = mermaid(comps, new_edges=new_edges)
        return item, payload

    head = resolve(repo, review.get("head")) or resolve(repo, "HEAD")
    base = resolve(repo, review.get("base")) or default_base(repo, head)
    if not base:
        payload["notes"].append("Base commit not found: code excerpts unavailable.")
        payload["diagram"] = mermaid(comps, new_edges=new_edges)
        return item, payload
    payload["base"], payload["head"] = base[:8], head[:8]

    diff = parse_diff(git(repo, "diff", "--no-color", "-U3", base, head))
    for group in ("deviations", "contracts", "findings", "blast"):
        for entry in review.get(group, []):
            x = excerpt(repo, head, diff, entry.get("where"))
            if x and entry.get("id"):
                payload["excerpts"][entry["id"]] = x

    changed = set()
    for row in git(repo, "diff", "--name-status", base, head).splitlines():
        status, *paths = row.split("\t")
        file = paths[-1]
        comp = component_of(file, comps)
        changed.add(comp)
        payload["files"].append({"status": status[0], "path": file, "component": comp})
        for kind, globs in model["triggers"].items():
            if any(matches(file, g) for g in globs):
                payload["trigger_files"].setdefault(kind, []).append(file)
                if kind == "schema":  # migrations are short and decisive: show them whole
                    payload["file_diffs"][file] = {"file": file, "kind": "diff", "hunks": diff.get(file, [])}
    payload["diagram"] = mermaid(comps, changed=changed, new_edges=new_edges)
    return item, payload


def model_page(args) -> tuple[str, dict]:
    path = Path(args.file).resolve() if args.file else find_model(Path.cwd(), args.model)
    if not path or not path.exists():
        sys.exit(f"{MODEL_FILE} not found")
    m = load_model(path)
    root = repo_root(path.parent) or (path.parent.parent if path.parent.name == "docs" else path.parent)
    return "model", {
        "kind": "model", "title": m["system"] or "Architecture", **m, "repo": str(root),
        "context": context_mermaid(m), "diagram": mermaid(m["components"]), "entity_diagram": entities_mermaid(m),
        "lifecycles": [{"entity": e["name"], "diagram": state_mermaid(e["states"], f"l{i}")}
                       for i, e in enumerate(m["entities"]) if e["states"]],
        "flow_diagrams": [{"title": f["title"], "diagram": sequence_mermaid(f["steps"], m, f"f{i}")}
                          for i, f in enumerate(m["flows"]) if f["steps"]],
        "decisions": load_decisions(root),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["spec", "change", "model"])
    ap.add_argument("file", nargs="?")
    ap.add_argument("--model", help=f"{MODEL_FILE} (default: nearest up to the repo root)")
    ap.add_argument("--spec", help="change: the item's spec (default: found by item name)")
    ap.add_argument("--repo", help="change: git repo (default: the review file's repo)")
    ap.add_argument("--editor", default=os.environ.get("CRAFT_EDITOR", "vscode"),
                    choices=["vscode", "cursor", "idea", "none"], help="file:line links open in this editor")
    ap.add_argument("--out", help="output dir (default: <tmp>/craft-views)")
    ap.add_argument("--no-open", action="store_true")
    args = ap.parse_args()
    if args.kind != "model" and not args.file:
        ap.error(f"{args.kind} needs a file")

    stem, payload = {"spec": spec_page, "change": change_page, "model": model_page}[args.kind](args)
    payload["editor"] = args.editor
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*__PAYLOAD__*/null", data)

    out_dir = Path(args.out) if args.out else Path(tempfile.gettempdir()) / "craft-views"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{args.kind}-{stem}.html"
    out.write_text(html, encoding="utf-8")
    print(out)
    if not args.no_open:
        webbrowser.open(out.as_uri())
    if args.kind == "model" and payload["problems"]:
        sys.exit("model problems:\n" + "\n".join(f"- {p}" for p in payload["problems"]))


if __name__ == "__main__":
    main()
