#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "pyyaml>=6"]
# ///
"""The deterministic half of a craft review: triggers, architecture diff, skeleton, tier.

  review.py [item.md | slug] [--base REF] [--head REF] [--ac-commit SHA] [--out FILE]

Creates <item>.review.json next to the item, or updates it. The reviewer's fields (deviations,
contracts, blast, findings, evidence results, not_checked, verdicts) are kept; triggers, new_edges
and tier are recomputed from the diff, architecture.yaml and those fields. Prints the tier, why, and what
is still incomplete. Without an item it reviews the branch against main.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from fnmatch import fnmatchcase
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "arch" / "scripts"))
import validate  # noqa: E402 — architecture findings
from md_utils import split_frontmatter  # noqa: E402

ARCHITECTURE_FILE = ".craft/architecture.yaml"

# Changed paths that make a change red. review_triggers in architecture.yaml add project paths to these.
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

TEST_FILE = re.compile(r"(^|/)(tests?|__tests__|spec)/|[._-](test|spec)\.\w+$|Tests?\.(kt|java|scala|cs)$"
                       r"|_test\.(go|py)$|(^|/)test_[^/]*\.py$")
SKIP_MARK = re.compile(r"@Disabled|@Ignore\b|\.skip\(|\bx(it|describe|test)\(|\.only\(|@pytest\.mark\.skip"
                       r"|\bt\.Skip\(|#\[ignore\]")
LOCKFILE = re.compile(r"(\.lock|-lock\.(json|yaml)|\.sum)$")
REACH = {"local": 0, "private": 1, "internet": 2}
DOC_FILES = {"PRODUCT.md", "README.md", "AGENTS.md", "CLAUDE.md", Path(ARCHITECTURE_FILE).name}
CONTRACT_TRIGGERS = ("dependency", "schema", "api", "event")
RED_CONTRACTS = {"dependency", "schema", "api", "event", "data-writer", "data-copy", "external-call"}
AC_COMMIT_SUBJECT = "test: acceptance tests"
AC_ROW = re.compile(r"^\|\s*(AC\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$")


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


def changed_files(repo: Path, base: str, head: str) -> list[tuple[str, str]]:
    """(status letter, path at head)."""
    out = []
    for row in git(repo, "diff", "--name-status", base, head).splitlines():
        status, *paths = row.split("\t")
        out.append((status[0], paths[-1]))
    return out


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
        h = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if h and cur is not None:
            hunk = {"header": line, "new": int(h[3]), "newLen": int(h[4] if h[4] is not None else 1), "lines": []}
            cur.append(hunk)
            o, n = int(h[1]), int(h[3])
            continue
        if hunk is not None and line[:1] in ("+", "-", " "):
            t = line[:1]
            hunk["lines"].append({"t": t, "o": o if t != "+" else None, "n": n if t != "-" else None, "s": line[1:]})
            o += t != "+"
            n += t != "-"
    return files


def matches(path: str, glob: str) -> bool:
    return fnmatchcase(path, glob) or (glob.startswith("**/") and fnmatchcase(path, glob[3:]))


def as_list(v) -> list[str]:
    if v is None:
        return []
    return [str(x) for x in v] if isinstance(v, list) else [str(v)]


# ---------- inputs ----------

def find_item(repo: Path, arg: str | None) -> Path | None:
    if not arg:
        branch = git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip()
        if not branch.startswith("craft/"):
            return None
        arg = branch.removeprefix("craft/")
    p = Path(arg)
    if p.suffix == ".md":
        if not p.exists():
            sys.exit(f"{arg} not found")
        return p.resolve()
    hits = sorted(repo.glob(f".craft/*/{arg}.md"))
    if not hits:
        sys.exit(f"item '{arg}' not found in .craft/*/")
    return hits[0]


def read_item(path: Path) -> dict:
    fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
    impact = re.search(r"^#+\s*Doc impact\s*$(.*?)(?=^#+\s|\Z)", body, re.M | re.S | re.I)
    acs = []
    for line in body.splitlines():
        row = AC_ROW.match(line)
        if row:
            cmd = row[3].strip("`").strip()
            acs.append({"ac": row[1], "criterion": row[2], "command": "" if cmd in ("", "—", "-") else cmd})
    return {"targets": {t.strip() for t in fm.get("target", "").split(",") if t.strip()},
            "doc_impact": impact[1] if impact else "", "acs": acs}


def raw_at(repo: Path, ref: str, rel: str = ARCHITECTURE_FILE) -> dict | None:
    """architecture.yaml at a ref; None when it isn't there or isn't this format."""
    try:
        raw = yaml.safe_load(git(repo, "show", f"{ref}:{rel}"))
    except (RuntimeError, yaml.YAMLError):
        return None
    return raw if isinstance(raw, dict) and isinstance(raw.get("components"), list) else None


def triggers_of(raw: dict | None) -> dict[str, list[str]]:
    """Built-in globs, the file's review_triggers, and what it implies: API specs, store paths, rule checks."""
    out = {k: list(v) for k, v in DEFAULT_TRIGGERS.items()}
    if not raw:
        return out

    def add(kind: str, globs) -> None:
        have = out.setdefault(str(kind), [])
        have.extend(g for g in globs if g not in have)

    for kind, globs in (raw.get("review_triggers") or {}).items():
        add(kind, as_list(globs))
    comps = raw["components"]
    stores = [*(raw.get("datastores") or []), *(s for c in comps for s in c.get("datastores") or [])]
    surfaces = [s for c in comps for f in ("endpoints", "ui_endpoints") for s in (c.get(f) or {}).values()]
    add("api", [s["spec"] for s in surfaces if s.get("spec")])
    add("schema", [f"{s['source_path'].rstrip('/')}/**" for s in stores if s.get("source_path")])
    add("arch-check", [r["check"] for r in raw.get("rules") or [] if r.get("check")])
    return out


def units_of(raw: dict | None) -> list[dict]:
    """What code belongs to: components, and root modules whose packages are directory globs."""
    if not raw:
        return []
    units = [{"name": c["component"], "paths": as_list(c.get("source_path"))} for c in raw["components"]]
    return units + [{"name": x["module"], "paths": [p for p in as_list(x.get("packages")) if "/" in p]}
                    for x in raw.get("modules") or []]


def component_of(path: str, units: list[dict]) -> str | None:
    best, size = None, -1
    for u in units:
        for p in u["paths"]:
            if "*" in p:
                if matches(path, p) and len(p) > size:
                    best, size = u["name"], len(p)
                continue
            p = p.rstrip("/")
            if (path == p or path.startswith(p + "/")) and len(p) > size:
                best, size = u["name"], len(p)
    return best


# ---------- deterministic triggers ----------

def holders(c: dict) -> list[dict]:
    return [c, *(c.get("modules") or [])]


def own_names(c: dict) -> set[str]:
    return {c["component"], *(x["module"] for x in c.get("modules") or [])}


def head_of(ref) -> str:
    """'payments.payments-api' -> payments; 'shared-kernel test' -> shared-kernel."""
    return str(ref).split()[0].split(".")[0]


def edges_of(raw: dict) -> set[tuple[str, str]]:
    """(component, what it uses or calls outside itself)."""
    return {(c["component"], head_of(ref)) for c in raw["components"] for h in holders(c)
            for ref in [*(h.get("uses") or []), *(h.get("calls") or [])] if head_of(ref) not in own_names(c)}


def entity_owners(raw: dict) -> dict[str, str]:
    out = {}
    for s in raw.get("datastores") or []:
        out |= {str(e): str(s.get("schema_owner") or s["datastore"]) for e in s.get("entities") or {}}
    for c in raw["components"]:
        for s in c.get("datastores") or []:
            out |= {str(e): c["component"] for e in s.get("entities") or {}}
    return out


def structure_changes(old: dict | None, new: dict | None) -> tuple[list, list[str]]:
    """Components, externals, dependencies, entities and rules between two versions of architecture.yaml."""
    if not new:
        return [], []
    if not old:
        return [("yellow", f"architecture: {ARCHITECTURE_FILE} added")], []
    out, new_edges = [], []
    was, now = {c["component"] for c in old["components"]}, {c["component"] for c in new["components"]}
    ext_was, ext_now = set(old.get("external") or {}), set(new.get("external") or {})
    out += [("yellow", f"architecture: new component {n}") for n in sorted(now - was)]
    out += [("yellow", f"architecture: component {n} removed") for n in sorted(was - now)]
    out += [("red", f"external-call: new external {e}") for e in sorted(ext_now - ext_was)]
    for a, b in sorted(edges_of(new) - edges_of(old)):
        if b in ext_now:
            out.append(("red", f"external-call: {a} -> {b}"))
        else:
            out.append(("yellow", f"new edge: {a} -> {b}"))
            new_edges.append(f"{a} -> {b}")
    before = entity_owners(old)
    for e, owner in entity_owners(new).items():
        if e not in before:
            out.append(("yellow", f"architecture: new entity {e}"))
        elif before[e] != owner:
            out.append(("red", f"data-writer: {e} owner {before[e]} -> {owner}"))
    states = old.get("states") or {}
    out += [("yellow", f"architecture: {k} lifecycle changed") for k, v in (new.get("states") or {}).items() if k in states and states[k] != v]
    rules = {r["rule"]: r for r in new.get("rules") or []}
    for r in old.get("rules") or []:
        n = rules.get(r["rule"])
        if n is None:
            out.append(("red", f"arch-check: rule {r['rule']} removed"))
        elif (r.get("level", "must") == "must" and n.get("level", "must") != "must") or (r.get("check") and not n.get("check")):
            out.append(("red", f"arch-check: rule {r['rule']} weakened"))
    return out, new_edges


def surface(raw: dict) -> dict:
    """Network endpoints in architecture.yaml: ref -> (component, exposure, spec, open)."""
    out = {}
    for c in raw["components"]:
        for field in ("endpoints", "ui_endpoints"):
            for ep, spec in (c.get(field) or {}).items():
                auth = spec.get("auth")
                is_open = auth == "none" or any(p.endswith("-optional") for p in auth or {})
                out[f"{c['component']}.{ep}"] = (c["component"], spec.get("exposure", c.get("exposure")), spec, is_open)
    return out


def data_access(raw: dict) -> set:
    """(component, relation, target, entity) over each component and its modules; `uses` inside a component."""
    pairs = [(c["component"], h) for c in raw["components"] for h in holders(c)]
    return {(comp, rel, target, e) for comp, h in pairs for rel in ("reads", "writes", "produces", "consumes")
            for target, ents in (h.get(rel) or {}).items() for e in ents or [None]} | {
        (c["component"], "uses", u, None) for c in raw["components"] for h in holders(c)
        for u in h.get("uses") or [] if head_of(u) in own_names(c)}


def deficiencies_of(raw: dict) -> set:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", encoding="utf-8") as f:
        yaml.safe_dump(raw, f)
        f.flush()
        validate.check(f.name, skip_paths=True)
    return set(validate.deficiencies)


def logins(raw: dict) -> set:
    """Pairs of owners that share a store login."""
    owners: dict[str, set] = {}
    for s in raw.get("datastores") or []:
        owners.setdefault(s.get("credential"), set()).add(s.get("schema_owner") or s["datastore"])
    for c in raw["components"]:
        for s in c.get("datastores") or []:
            owners.setdefault(s.get("credential"), set()).add(c["component"])
    return {(k, a, b) for k, o in owners.items() if k for a in o for b in o if a < b}


def define_changes(old: dict | None, new: dict | None) -> list:
    """Security, data, deficiency and note changes between two versions of architecture.yaml."""
    if not (old and new):
        return []
    out, was, now = [], surface(old), surface(new)
    for ref, (_, exposure, spec, is_open) in now.items():
        if ref not in was:
            out.append(("red", f"security: new open endpoint {ref} on the internet") if is_open and exposure == "internet"
                       else ("yellow", f"architecture: new endpoint {ref}"))
            continue
        _, before, old_spec, was_open = was[ref]
        if REACH.get(exposure, -1) > REACH.get(before, -1):
            out.append(("red", f"security: {ref} exposure {before} -> {exposure}"))
        if is_open and not was_open:
            out.append(("red", f"security: {ref} now accepts anonymous calls"))
        elif spec.get("auth") != old_spec.get("auth"):
            out.append(("yellow", f"security: {ref} auth changed"))
        out += [("red", f"security: {ref} no longer needs {a}")
                for a in as_list(old_spec.get("authz")) if a not in as_list(spec.get("authz"))]
        if spec.get("identity") == "user" and old_spec.get("identity") != "user":
            out.append(("red", f"security: user identity now reaches {ref}"))
    def user_side(s):
        return {c for c, _, spec, _ in s.values() if spec.get("identity") == "user"}
    out += [("red", f"security: user identity now reaches {c}") for c in sorted(user_side(now) - user_side(was))]
    out += [("red", f"security: {a} and {b} now share the login {k}") for k, a, b in sorted(logins(new) - logins(old))]
    for comp, rel, target, entity in sorted(data_access(new) - data_access(old), key=str):
        what = f"{comp} {rel} {target}" + (f".{entity}" if entity else "")
        out.append(("red", f"data-writer: {what}") if rel == "writes" else ("yellow", f"architecture: {what}"))
    out += [("red", f"arch-check: new deficiency: {d}") for d in sorted(deficiencies_of(new) - deficiencies_of(old))]
    kept = {n["note"] for n in new.get("notes") or []}
    out += [("yellow", f"architecture: note changed or removed: {n['note'][:60]}") for n in old.get("notes") or [] if n["note"] not in kept]
    return out


def diff_triggers(repo: Path, base: str, head: str, raw: dict | None, item: dict | None, ac_commit: str | None) -> list:
    out = []
    diff = parse_diff(git(repo, "diff", "--no-color", "-U0", base, head))
    files = changed_files(repo, base, head)
    triggers, units = triggers_of(raw), units_of(raw)

    for status, path in files:
        for kind, globs in triggers.items():
            if any(matches(path, g) for g in globs):
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
        ac_files = set(git(repo, "show", "--name-only", "--format=", ac_commit).split())
        # Renames are followed, so moving a file with a rewrite still shows as an edit; deleting one is red.
        for status, path, *_ in (l.split("\t") for l in git(repo, "diff", "--name-status", ac_commit, head).splitlines()):
            if path in ac_files:
                out.append(("red", f"test-weakened: {path} deleted") if status == "D" else ("yellow", f"ac-test-edited: {path}"))

    if item:
        for _, path in files:
            if (Path(path).name in DOC_FILES or path.startswith(".craft/modules/")) and Path(path).name not in item["doc_impact"]:
                out.append(("red", f"doc-outside-impact: {path}"))
        if item["targets"]:
            outside: dict[str, int] = {}
            for _, path in files:
                comp = component_of(path, units)
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
        if f.get("status") == "fixed" or (r.get("verdicts", {}).get(f.get("id")) == "accept" and f.get("severity") != "high"):
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
        if f.get("status") in ("confirmed", "fixed") and not f.get("test"):
            out.append(f"{f.get('id', '?')} is {f['status']} but names no test")
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

    repo = repo_root(Path.cwd()) or sys.exit("not a git repository")
    head = resolve(repo, args.head) or sys.exit(f"unknown ref {args.head}")
    base = (resolve(repo, args.base) if args.base else default_base(repo, head)) or sys.exit("base not found; pass --base")
    item_path = find_item(repo, args.item)
    item = read_item(item_path) if item_path else None

    raw, was = raw_at(repo, head), raw_at(repo, base)
    if raw is None and ARCHITECTURE_FILE in git(repo, "ls-tree", "-r", "--name-only", head).splitlines():
        sys.exit(f"{ARCHITECTURE_FILE} at {head[:8]} can't be read: fix it with arch")
    changes, edges = structure_changes(was, raw)
    changes += define_changes(was, raw)

    ac_commit = args.ac_commit or (git(repo, "log", f"{base}..{head}", "--format=%H", "--grep",
                                         f"^{AC_COMMIT_SUBJECT}").split() or [None])[-1]

    if args.out:
        out = Path(args.out)
    elif item_path:
        out = item_path.with_name(f"{item_path.stem}.review.json")
    else:
        branch = git(repo, "rev-parse", "--abbrev-ref", head).strip().replace("/", "-")
        out = Path(tempfile.gettempdir()) / "craft-reviews" / f"{branch}.review.json"
    r = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {
        "deviations": [], "contracts": [], "blast": [], "findings": [], "evidence": [],
        "not_checked": ["code-review: not run", "security-review: not run"]
                       + [f"{x['rule']} (manual): {x['statement']}" for x in (raw or {}).get("rules") or [] if not x.get("check")],
        "verdicts": {},
    }
    have = {e.get("ac") for e in r.get("evidence", [])}
    r.setdefault("evidence", []).extend(
        {**a, "result": "not-run" if a["command"] else "manual"} for a in (item or {}).get("acs", []) if a["ac"] not in have)

    triggers = changes + diff_triggers(repo, base, head, raw, item, ac_commit)
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
