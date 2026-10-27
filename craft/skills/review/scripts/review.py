#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6"]
# ///
"""The deterministic half of a craft review: triggers, model diff, skeleton, tier.

  review.py [item.md | slug] [--base REF] [--head REF] [--ac-commit SHA] [--out FILE]

Creates <item>.review.json next to the item, or updates it. The reviewer's fields (deviations,
contracts, blast, findings, evidence results, not_checked, verdicts) are kept; triggers, new_edges
and tier are recomputed from the diff, the model and those fields. Prints the tier, why, and what
is still incomplete. Without an item it reviews the branch against main.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "view" / "scripts"))
import view as m  # noqa: E402 — shared model, git and markdown helpers

TEST_FILE = re.compile(r"(^|/)(tests?|__tests__|spec)/|[._-](test|spec)\.\w+$|Tests?\.(kt|java|scala|cs)$"
                       r"|_test\.(go|py)$|(^|/)test_[^/]*\.py$")
SKIP_MARK = re.compile(r"@Disabled|@Ignore\b|\.skip\(|\bx(it|describe|test)\(|\.only\(|@pytest\.mark\.skip"
                       r"|\bt\.Skip\(|#\[ignore\]")
LOCKFILE = re.compile(r"(\.lock|-lock\.(json|yaml)|\.sum)$")
DOC_FILES = {"PRODUCT.md", "ARCHITECTURE.md", "AGENTS.md", "CLAUDE.md", m.MODEL_FILE}
CONTRACT_TRIGGERS = ("dependency", "schema", "api", "event")
RED_CONTRACTS = {"dependency", "schema", "api", "event", "data-writer", "data-copy", "external-call"}
AC_COMMIT_SUBJECT = "test: acceptance tests"
AC_ROW = re.compile(r"^\|\s*(AC\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")


# ---------- inputs ----------

def find_item(repo: Path, arg: str | None) -> Path | None:
    if not arg:
        branch = m.git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        if not branch.startswith("craft/"):
            return None
        arg = branch.removeprefix("craft/")
    p = Path(arg)
    if p.suffix == ".md":
        if not p.exists():
            sys.exit(f"{arg} not found")
        return p.resolve()
    hits = sorted(repo.glob(f"docs/*/{arg}.md"))
    if not hits:
        sys.exit(f"item '{arg}' not found in docs/*/")
    return hits[0]


def read_item(path: Path) -> dict:
    fm, body = m.split_frontmatter(path.read_text(encoding="utf-8"))
    impact = re.search(r"^#+\s*Doc impact\s*$(.*?)(?=^#+\s|\Z)", body, re.M | re.S | re.I)
    acs = []
    for line in body.splitlines():
        row = AC_ROW.match(line)
        if row:
            cmd = row[3].strip("`").strip()
            acs.append({"ac": row[1], "criterion": row[2], "command": "" if cmd in ("", "—", "-") else cmd})
    return {"targets": {t for t in re.split(r"[,\s/]+", fm.get("target", "")) if t},
            "doc_impact": impact[1] if impact else "", "acs": acs}


def model_at(repo: Path, ref: str, rel: str) -> dict | None:
    try:
        text = m.git(repo, "show", f"{ref}:{rel}")
    except RuntimeError:
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(text)
    return m.load_model(Path(f.name))


# ---------- deterministic triggers ----------

def model_changes(old: dict | None, new: dict | None) -> tuple[list, list[str]]:
    if new is None or old is None:
        return ([("yellow", f"model: {m.MODEL_FILE} added")] if new and new["file"] else []), []
    out, edges = [], []
    oc, nc = {c["name"]: c for c in old["components"]}, {c["name"]: c for c in new["components"]}
    oext, next_ = {e["name"] for e in old["external"]}, {e["name"] for e in new["external"]}
    out += [("yellow", f"model: new component {n}") for n in sorted(nc.keys() - oc.keys())]
    out += [("yellow", f"model: component {n} removed") for n in sorted(oc.keys() - nc.keys())]
    out += [("red", f"external-call: new external {e}") for e in sorted(next_ - oext)]
    for name, c in nc.items():
        before = set(oc[name]["deps"]) if name in oc else set()
        for d in c["deps"]:
            if d in before:
                continue
            if d in next_:
                out.append(("red", f"external-call: {name} -> {d}"))
            else:
                out.append(("yellow", f"new edge: {name} -> {d}"))
                edges.append(f"{name} -> {d}")
    oe = {e["name"]: e for e in old["entities"]}
    for e in new["entities"]:
        was = oe.get(e["name"])
        if was is None:
            out.append(("yellow", f"model: new entity {e['name']}"))
        elif was["owner"] != e["owner"]:
            out.append(("red", f"data-writer: {e['name']} owner {was['owner']} -> {e['owner']}"))
        elif was["states"] != e["states"]:
            out.append(("yellow", f"model: {e['name']} lifecycle changed"))
        known = {c["of"] for c in (was or {}).get("copies", [])}
        out += [("red", f"data-copy: {e['name']} copies {c['of']} ({c['kind']})") for c in e["copies"] if c["of"] not in known]
    nr = {r["id"]: r for r in new["rules"]}
    for r in old["rules"]:
        now = nr.get(r["id"])
        if now is None:
            out.append(("red", f"arch-check: rule {r['id']} removed"))
        elif (r["level"], now["level"]) == ("MUST", "SHOULD") or (now["manual"] and not r["manual"]):
            out.append(("red", f"arch-check: rule {r['id']} weakened"))
    return out, edges


def diff_triggers(repo: Path, base: str, head: str, model: dict, item: dict | None, ac_commit: str | None) -> list:
    out = []
    diff = m.parse_diff(m.git(repo, "diff", "--no-color", "-U0", base, head))
    files = []
    for row in m.git(repo, "diff", "--name-status", base, head).splitlines():
        status, *paths = row.split("\t")
        files.append((status[0], paths[-1]))

    for status, path in files:
        for kind, globs in model["triggers"].items():
            if any(m.matches(path, g) for g in globs):
                added = [l["s"].strip() for h in diff.get(path, []) for l in h["lines"] if l["t"] == "+" and l["s"].strip()]
                detail = "" if kind != "dependency" or LOCKFILE.search(path) or not added else f" +{added[0][:70]}"
                out.append(("red", f"{kind}: {path}{detail}"))
        if TEST_FILE.search(path):
            if status == "D":
                out.append(("red", f"test-weakened: {path} deleted"))
            for h in diff.get(path, []):
                out += [("red", f"test-weakened: {path}:{l['n']} {l['s'].strip()[:60]}")
                        for l in h["lines"] if l["t"] == "+" and SKIP_MARK.search(l["s"])]

    if ac_commit:
        ac_files = set(m.git(repo, "show", "--name-only", "--format=", ac_commit).split())
        edited = set(m.git(repo, "diff", "--name-only", ac_commit, head).split())
        out += [("red", f"ac-test-edited: {p}") for p in sorted(ac_files & edited)]

    if item:
        for _, path in files:
            if (Path(path).name in DOC_FILES or path.startswith("docs/modules/")) and Path(path).name not in item["doc_impact"]:
                out.append(("red", f"doc-outside-impact: {path}"))
        if item["targets"]:
            outside: dict[str, int] = {}
            for _, path in files:
                comp = m.component_of(path, model["components"])
                if comp and comp not in item["targets"] and not TEST_FILE.search(path):
                    outside[comp] = outside.get(comp, 0) + 1
            out += [("yellow", f"outside target: {c} ({n} file{'s' * (n > 1)})") for c, n in outside.items()]
    return out


# ---------- the reviewer's fields ----------

def content_reasons(r: dict, triggered: set[str]) -> list:
    out = [("red", f"deviation {d.get('id', '?')}") for d in r.get("deviations", [])]
    for c in r.get("contracts", []):
        if c.get("kind") not in triggered:  # a schema trigger already says "schema"
            out.append(("red" if c.get("kind") in RED_CONTRACTS else "yellow", f"contract {c.get('id', '?')}: {c.get('kind', '?')}"))
    for f in r.get("findings", []):
        if r.get("verdicts", {}).get(f.get("id")) == "accept" and f.get("severity") != "high":
            continue
        high = f.get("status") == "confirmed" and f.get("severity") == "high"
        out.append(("red" if high else "yellow", f"finding {f.get('id', '?')}: {f.get('severity', '?')}, {f.get('status', '?')}"))
    out += [("yellow", f"blast {b.get('id', '?')}: uncovered callers") for b in r.get("blast", []) if not b.get("covered_by")]
    for result, tier in (("fail", "red"), ("not-run", "yellow")):
        acs = [e.get("ac", "?") for e in r.get("evidence", []) if e.get("result") == result]
        if acs:
            out.append((tier, f"{', '.join(acs)} {'fail' if result == 'fail' else 'not run'}"))
    if r.get("not_checked"):
        out.append(("yellow", f"not checked: {len(r['not_checked'])}"))
    return out


def incomplete(r: dict) -> list[str]:
    kinds = {c.get("kind") for c in r.get("contracts", [])}
    out = []
    for t in r["triggers"]:
        kind = t["what"].split(":", 1)[0]
        if (kind in CONTRACT_TRIGGERS or kind in ("external-call", "data-copy", "data-writer")) and kind not in kinds:
            out.append(f"{t['what']} — no {kind} contract describes it")
            kinds.add(kind)  # once per kind
    for f in r.get("findings", []):
        missing = [k for k in ("where", "invariant", "scenario", "consequence", "fix") if not f.get(k)]
        if missing:
            out.append(f"{f.get('id', '?')} lacks {', '.join(missing)}")
        if f.get("status") == "confirmed" and not f.get("test"):
            out.append(f"{f.get('id', '?')} is confirmed but names no test")
    out += [f"{c.get('id', '?')} ({c.get('kind')}) has no compat" for c in r.get("contracts", [])
            if c.get("kind") in ("schema", "api", "event") and not c.get("compat")]
    out += [f"{e['ac']} not run: {e.get('command') or 'manual'}" for e in r.get("evidence", []) if e.get("result") == "not-run"]
    out += [f"not checked: {x}" for x in r.get("not_checked", [])]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("item", nargs="?", help="item file or slug (default: from the craft/<item> branch)")
    ap.add_argument("--base", help="default: merge-base with main")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--ac-commit", help=f"commit with the AC tests (default: the one titled '{AC_COMMIT_SUBJECT}…')")
    ap.add_argument("--out", help="review file (default: next to the item, or <tmp>/craft-reviews/)")
    args = ap.parse_args()

    repo = m.repo_root(Path.cwd()) or sys.exit("not a git repository")
    head = m.resolve(repo, args.head) or sys.exit(f"unknown ref {args.head}")
    base = (m.resolve(repo, args.base) if args.base else m.default_base(repo, head)) or sys.exit("base not found; pass --base")
    item_path = find_item(repo, args.item)
    item = read_item(item_path) if item_path else None

    model_path = m.find_model(repo, None)
    model = m.load_model(model_path)
    rel = str(model_path.relative_to(repo)) if model_path else m.MODEL_FILE
    changes, edges = model_changes(model_at(repo, base, rel), model_at(repo, head, rel))

    ac_commit = args.ac_commit or (m.git(repo, "log", f"{base}..{head}", "--format=%H", "--grep",
                                         f"^{AC_COMMIT_SUBJECT}").split() or [None])[-1]

    if args.out:
        out = Path(args.out)
    elif item_path:
        out = item_path.with_name(f"{item_path.stem}.review.json")
    else:
        branch = m.git(repo, "rev-parse", "--abbrev-ref", head).strip().replace("/", "-")
        out = Path(tempfile.gettempdir()) / "craft-reviews" / f"{branch}.review.json"
    r = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {
        "deviations": [], "contracts": [], "blast": [], "findings": [], "evidence": [],
        "not_checked": ["code-review: not run", "security-review: not run"]
                       + [f"{x['id']} (manual): {x['text']}" for x in model["rules"] if x["manual"]],
        "verdicts": {},
    }
    have = {e.get("ac") for e in r.get("evidence", [])}
    r.setdefault("evidence", []).extend(
        {**a, "result": "not-run" if a["command"] else "manual"} for a in (item or {}).get("acs", []) if a["ac"] not in have)

    triggers = changes + diff_triggers(repo, base, head, model, item, ac_commit)
    reasons = triggers + content_reasons(r, {w.split(':', 1)[0] for _, w in triggers})
    r["triggers"] = [{"tier": t, "what": w} for t, w in sorted(reasons, key=lambda x: x[0] != "red")]
    tiers = {t["tier"] for t in r["triggers"]}
    r = {"item": item_path.stem if item_path else None, "base": base, "head": head,
         "tier": "red" if "red" in tiers else "yellow" if tiers else "green",
         **{k: v for k, v in r.items() if k not in ("item", "base", "head", "tier")}, "new_edges": edges}

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(r, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out)
    print(f"tier: {r['tier']}")
    for t in r["triggers"]:
        print(f"  {'🔴' if t['tier'] == 'red' else '🟡'} {t['what']}")
    todo = incomplete(r)
    if todo:
        print("incomplete:")
        print("\n".join(f"  - {x}" for x in todo))


if __name__ == "__main__":
    main()
