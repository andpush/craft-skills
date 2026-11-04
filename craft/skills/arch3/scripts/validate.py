# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "pyyaml>=6"]
# ///
"""Validate docs/architecture.yaml: schema, references, flows, states, ownership.

Usage: uv run validate.py [docs/architecture.yaml] [--skip-paths] [--gate [--accept]]
Exit 1 on errors; warnings and findings (deficiencies, improvements) are printed but pass.
--gate also writes docs/architecture.gate.json, what `verify` enforces, flattened from architecture.yaml.
Stack checks read only that file and fail when its architecture_sha256 no longer matches the file.
A new deficiency exits 1 unless --accept; fixed ones drop out.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

import jsonschema
import yaml

SCHEMA = Path(__file__).resolve().parent.parent / "reference" / "architecture.schema.json"
RELATIONS = ("uses", "calls", "produces", "consumes", "reads", "writes")
CLIENT_TYPES = {"web-app", "mobile-app", "desktop-app", "console-app"}  # run outside our network
NOT_ON_NETWORK = {"native", "cli", "schedule"}
errors, warnings = [], []
deficiencies, improvements = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def deficiency(msg):
    deficiencies.append(msg)


def improve(msg):
    improvements.append(msg)


def cycles(graph):
    """Groups of nodes that depend on each other, directly or through others."""
    def reach(start):
        seen, stack = set(), list(graph.get(start, ()))
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                stack.extend(graph.get(n, ()))
        return seen
    reached = {n: reach(n) for n in graph}
    done, out = set(), []
    for n in sorted(graph):
        if n in reached[n] and n not in done:
            group = sorted(x for x in reached[n] if n in reached.get(x, ()))
            done |= set(group)
            out.append(group)
    return out


def as_list(v):
    return [] if v is None else v if isinstance(v, list) else [v]


def arrow(item):
    """('a', '->', 'b', label) from 'a -> b' or {'a -> b': label}."""
    text, label = (item, None) if isinstance(item, str) else next(iter(item.items()))
    a, op, b = re.match(r"^(\S+) (->|~>) (\S+)$", text).groups()
    return a, op, b, label


def check(path, skip_paths=False):
    """Validate the architecture file at path; return (errors, warnings). Findings land in deficiencies and improvements."""
    for found in (errors, warnings, deficiencies, improvements):
        found.clear()
    arch = yaml.safe_load(Path(path).read_text())
    path = Path(path)
    root = path.resolve().parent
    if root.name == "docs":  # architecture.yaml lives in docs/; its paths are relative to the repo root
        root = root.parent

    schema_errors = list(jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(arch))
    for e in schema_errors:
        err(f"schema: {e.json_path}: {e.message}")
    if schema_errors:
        return errors, warnings

    actors = arch.get("actors") or {}
    externals = arch.get("external") or {}
    components = {c["component"]: c for c in arch["components"]}
    root_modules = {m["module"]: m for m in arch.get("modules") or []}
    stores = {d["datastore"]: d for d in arch.get("datastores") or []}
    queues = {q["queue"]: q for q in arch.get("queues") or []}

    # entities: name -> fields; where each lives
    entities, entity_home, messages = {}, {}, {}
    def add_entities(owner, ents, kind):
        for name, fields in (ents or {}).items():
            if name in entities:
                err(f"entity '{name}' defined twice ({entity_home[name]}, {owner})")
            entities[name], entity_home[name] = fields or [], owner
            if kind == "queue":
                messages[name] = owner
    for s in stores.values():
        add_entities(s["datastore"], s.get("entities"), "store")
    for q in queues.values():
        add_entities(q["queue"], q.get("entities"), "queue")
    private_stores = {}
    for c in components.values():
        for d in c.get("datastores") or []:
            private_stores[d["datastore"]] = c["component"]
            add_entities(d["datastore"], d.get("entities"), "store")

    top_ids = [*actors, *externals, *components, *root_modules, *stores, *queues, *private_stores]
    for i in {x for x in top_ids if top_ids.count(x) > 1}:
        err(f"id '{i}' is not unique at top level")

    def endpoints(comp):
        return set((components[comp].get("endpoints") or {}).keys())

    def resolve_module(ref, comp):
        if "." in ref:
            c, m = ref.split(".", 1)
            return c in components and any(x["module"] == m for x in components[c].get("modules") or [])
        own = comp and any(x["module"] == ref for x in components[comp].get("modules") or [])
        return own or ref in root_modules

    def resolve_call(ref):
        if "." in ref:
            c, e = ref.split(".", 1)
            return c in components and e in endpoints(c)
        return ref in components or ref in externals

    def check_relations(holder, where, comp):
        for u in as_list(holder.get("uses")):
            if not resolve_module(u.split(" ")[0], comp):
                err(f"{where}: uses '{u}' — no such module")
        for c in as_list(holder.get("calls")):
            if not resolve_call(c):
                err(f"{where}: calls '{c}' — no such component, endpoint or external")
        own = {s for s, owner in private_stores.items() if owner == comp}
        for rel, pool in (("produces", queues), ("consumes", queues), ("reads", {*stores, *own}), ("writes", {*stores, *own})):
            for target, ents in (holder.get(rel) or {}).items():
                if target not in pool:
                    hint = f" (private to {private_stores[target]})" if target in private_stores else ""
                    err(f"{where}: {rel} '{target}' — no such root {'queue' if pool is queues else 'datastore'}{hint}")
                    continue
                for e in ents or []:
                    if entity_home.get(e) != target:
                        err(f"{where}: {rel} {target}.{e} — no such entity there")

    def allowed(comp, module=None):
        """Union of relations of a component and (one or all of) its modules."""
        mods = components[comp].get("modules") or []
        holders = [components[comp]] + [m for m in mods if module is None or m["module"] == module]
        out = {r: set() for r in RELATIONS}
        for h in holders:
            out["calls"] |= set(as_list(h.get("calls")))
            for r in ("produces", "consumes", "reads", "writes"):
                for target, ents in (h.get(r) or {}).items():
                    out[r] |= {(target, e) for e in ents or [None]}
        return out

    for c in components.values():
        name = c["component"]
        check_relations(c, f"component {name}", name)
        surfaces = {**(c.get("endpoints") or {}), **(c.get("ui_endpoints") or {})}
        served = set()
        for m in c.get("modules") or []:
            check_relations(m, f"module {name}.{m['module']}", name)
            for ep in as_list(m.get("serves")):
                served.add(ep)
                if ep not in surfaces:
                    err(f"module {name}.{m['module']}: serves '{ep}' — no such endpoint in {name}")
        if c.get("modules"):
            for ep in sorted(set(surfaces) - served):
                warn(f"endpoint {name}.{ep}: served by no listed module")
        if not skip_paths and c.get("source_path") and not (root / c["source_path"]).exists():
            err(f"component {name}: source_path '{c['source_path']}' does not exist")
        for ep, spec in (c.get("ui_endpoints") or {}).items():
            for actor in as_list(spec.get("for")):
                if actor not in actors:
                    err(f"ui endpoint {name}.{ep}: for '{actor}' not in actors")
                elif name not in as_list(actors[actor].get("uses")):
                    warn(f"ui endpoint {name}.{ep}: for lists '{actor}', but actor's uses doesn't list {name}")
    for m in root_modules.values():
        check_relations(m, f"module {m['module']}", None)
        if m.get("serves"):
            err(f"module {m['module']}: serves — a root module has no endpoints")

    for a, spec in actors.items():
        for u in as_list(spec.get("uses")):
            if u not in components:
                err(f"actor {a}: uses '{u}' — no such component")
                continue
            ui = (components[u].get("ui_endpoints") or {}).values()
            if ui and not any(a in as_list(s.get("for")) for s in ui):
                warn(f"actor {a}: uses {u}, but none of its ui_endpoints is for {a}")
    for x, spec in externals.items():
        for c in as_list(spec.get("calls")):
            if "." not in c or not resolve_call(c):
                err(f"external {x}: calls '{c}' — no such endpoint")

    # endpoint audience against declared callers; names outside architecture.yaml are not checked
    for name, c in components.items():
        for ep, spec in (c.get("endpoints") or {}).items():
            if "for" not in spec:
                continue
            ref, audience = f"{name}.{ep}", as_list(spec["for"])
            callers = {n for n in components if ref in allowed(n)["calls"]}
            callers |= {x for x, s in externals.items() if ref in as_list(s.get("calls"))}
            coarse = {n for n in components if name in allowed(n)["calls"]}
            for caller in sorted(callers - set(audience)):
                warn(f"endpoint {ref}: called by {caller}, which is not in its for")
            for target in audience:
                if (target in components or target in externals) and target not in callers | coarse:
                    warn(f"endpoint {ref}: for lists {target}, which doesn't call it")

    # security
    def module_reach(name, ep):
        """What the code behind an endpoint calls or changes."""
        c = components[name]
        mods = [m for m in c.get("modules") or [] if ep in as_list(m.get("serves"))] or [c]
        return sorted({x for m in mods for x in [*as_list(m.get("calls")), *(k for k in m.get("writes") or {} if private_stores.get(k) != name), *(m.get("produces") or {})]})

    for name, c in components.items():
        for kind in ("endpoints", "ui_endpoints"):
            for ep, spec in (c.get(kind) or {}).items():
                if spec.get("protocol") in NOT_ON_NETWORK:
                    continue
                ref, auth, audience = f"{name}.{ep}", spec.get("auth"), as_list(spec.get("for"))
                exposure = spec.get("exposure", c.get("exposure"))
                is_open = auth == "none" or any(p.endswith("-optional") for p in auth or {})
                if not exposure:
                    warn(f"endpoint {ref}: no exposure")
                if auth == "none" and spec.get("identity") not in (None, "none"):
                    warn(f"endpoint {ref}: identity {spec['identity']}, but auth is none")
                if is_open and spec.get("authz"):
                    deficiency(f"{ref}: needs {', '.join(as_list(spec['authz']))}, but anonymous calls are allowed. Split the route.")
                if audience == ["unused"] and exposure != "local":
                    improve(f"{ref}: reachable, but nothing consumes it. Remove it or wire it up.")
                if exposure != "internet":
                    continue
                reach = module_reach(name, ep)
                if is_open and reach:
                    deficiency(f"{ref}: open to the internet, and its code reaches {', '.join(reach[:3])}. Require a token or a limit.")
                elif audience != ["unused"] and audience and all(
                        a in components and components[a].get("type") not in CLIENT_TYPES for a in audience):
                    improve(f"{ref}: on the internet, but only our own services consume it. Narrow its ingress.")
    logins = {}
    for s in stores.values():
        logins.setdefault(s.get("credential"), set()).add(s.get("schema_owner") or s["datastore"])
    for c in components.values():
        for d in c.get("datastores") or []:
            logins.setdefault(d.get("credential"), set()).add(c["component"])
    for login, owners in logins.items():
        if login and len(owners) > 1:
            deficiency(f"{', '.join(sorted(owners))} share the login {login}: compromising one exposes the other's data.")

    # structure
    def targets(holders, me):
        """Components and root modules these holders depend on; 'core.api test' -> core."""
        refs = [r for h in holders for r in [*as_list(h.get("calls")), *as_list(h.get("uses"))]]
        return {t for t in (r.split(" ")[0].split(".")[0] for r in refs)
                if t != me and (t in components or t in root_modules)}
    top = {n: targets([c, *(c.get("modules") or [])], n) for n, c in components.items()}
    top |= {n: targets([m], n) for n, m in root_modules.items()}
    for group in cycles(top):
        deficiency(f"Dependency cycle between {', '.join(group)}.")
    for n, c in components.items():
        names = {m["module"] for m in c.get("modules") or []}
        inner = {m["module"]: {r.split(" ")[0].removeprefix(f"{n}.") for r in as_list(m.get("uses"))} & names
                 for m in c.get("modules") or []}
        for group in cycles(inner):
            deficiency(f"{n}: dependency cycle between modules {', '.join(group)}.")
    for s in [*stores.values(), *queues.values()]:
        if not s.get("schema_owner"):
            deficiency(f"{s.get('datastore') or s.get('queue')}: shared, with no schema_owner.")
    unchecked = [r["rule"] for r in arch.get("rules") or [] if r.get("level", "must") == "must" and not r.get("check")]
    if unchecked:
        improve(f"Must rules that only review enforces: {', '.join(unchecked)}. Add a check where one is possible.")

    # notes
    known = set(top_ids) | set(entities)
    for c in components.values():
        for field in ("endpoints", "ui_endpoints"):
            known |= {f"{c['component']}.{e}" for e in c.get(field) or {}}
        known |= {f"{c['component']}.{m['module']}" for m in c.get("modules") or []}
    for ent, fields in entities.items():
        known |= {f"{ent}.{f.split(' ')[0]}" for f in fields}
    for n in arch.get("notes") or []:
        for a in n["about"]:
            if a not in known:
                err(f"note about '{a}': no such thing in architecture.yaml — {n['note'][:50]}")

    # entity references and ownership
    for name, fields in entities.items():
        for f in fields:
            ref = re.search(r"-> (\S+)", f)
            if ref and ref.group(1).split(".")[0] not in entities:
                err(f"entity {name}: field '{f}' refers to unknown entity")
    writers = {}
    for c in components:
        for target, e in allowed(c)["writes"]:
            for ent in [e] if e else [n for n, h in entity_home.items() if h == target]:
                writers.setdefault(ent, set()).add(c)
    for ent, ws in writers.items():
        if len(ws) > 1:
            deficiency(f"{ent}: written by several components ({', '.join(sorted(ws))}).")
    for s in stores.values():
        if s.get("schema_owner") and s["schema_owner"] not in components:
            err(f"datastore {s['datastore']}: schema_owner '{s['schema_owner']}' is not a component")
    for q in queues.values():
        if q.get("schema_owner") and q["schema_owner"] not in components:
            err(f"queue {q['queue']}: schema_owner '{q['schema_owner']}' is not a component")

    # states
    for key in arch.get("states") or {}:
        ent, _, field = key.partition(".")
        if ent not in entities:
            err(f"states {key}: no such entity")
        elif field and field not in [f.split(" ")[0] for f in entities[ent]]:
            err(f"states {key}: entity {ent} has no field '{field}'")

    # flows
    def participant(p):
        if p in actors: return "actor", p, None
        if p in externals: return "external", p, None
        if p in components: return "component", p, None
        if p in stores or p in private_stores: return "datastore", p, None
        if p in queues: return "queue", p, None
        if "." in p:
            c, m = p.split(".", 1)
            if c in components and any(x["module"] == m for x in components[c].get("modules") or []):
                return "component", c, m
        return None, p, None

    for flow, steps in (arch.get("flows") or {}).items():
        for step in steps:
            a, op, b, label = arrow(step)
            (ka, ca, ma), (kb, cb, mb) = participant(a), participant(b)
            where = f"flow '{flow}': {a} {op} {b}"
            if ka is None or kb is None:
                err(f"{where} — unknown participant '{a if ka is None else b}'")
                continue
            if op == "~>":
                msg = (label or "").split(" ")[0]
                if msg not in messages:
                    err(f"{where} — label must start with a queue message entity")
                    continue
                q = messages[msg]
                if ka == "component" and (q, msg) not in allowed(ca, ma)["produces"]:
                    err(f"{where} — {a} doesn't produce {msg}")
                if kb == "component" and (q, msg) not in allowed(cb)["consumes"]:
                    err(f"{where} — {b} doesn't consume {msg}")
                continue
            if ka == "actor":
                ok = kb == "component" and cb in as_list(actors[a].get("uses"))
            elif ka == "external":
                ok = kb == "component" and any(r.split(".")[0] == cb for r in as_list(externals[a].get("calls")))
            elif ka == "component" and kb == "datastore":
                rel = allowed(ca, ma)
                ok = private_stores.get(cb) == ca or any(t == cb for t, _ in rel["reads"] | rel["writes"])
            elif ka == "component" and ca == cb and ma and mb:
                source = next(x for x in components[ca]["modules"] if x["module"] == ma)
                used = as_list(components[ca].get("uses")) + as_list(source.get("uses"))
                ok = any(u.split(" ")[0].removeprefix(f"{ca}.") == mb for u in used)
            elif ka == "component":
                calls = allowed(ca, ma)["calls"]
                ok = any(r == cb or r.split(".")[0] == cb for r in calls) if kb == "component" else b in calls
            else:
                ok = False
            if not ok:
                err(f"{where} — not allowed by declared relations")

    # rules
    for r in arch.get("rules") or []:
        sel = r.get("applies_to") or {}
        for c in as_list(sel.get("components")):
            if c not in components:
                err(f"rule {r['rule']}: applies_to component '{c}' unknown")
        for q in as_list(sel.get("queues")):
            if q not in queues:
                err(f"rule {r['rule']}: applies_to queue '{q}' unknown")
        if not skip_paths and r.get("check") and not (root / r["check"]).exists():
            err(f"rule {r['rule']}: check '{r['check']}' does not exist")
    return errors, warnings


def report():
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    for d in deficiencies:
        print(f"deficiency: {d}")
    for i in improvements:
        print(f"improvement: {i}")
    print(f"{len(errors)} errors, {len(warnings)} warnings, {len(deficiencies)} deficiencies, {len(improvements)} improvements")
    return 1 if errors else 0


def io_of(holder):
    out = set()
    if holder.get("reads") or holder.get("writes"):
        out.add("persistence")
    if holder.get("produces") or holder.get("consumes"):
        out.add("messaging")
    if holder.get("calls"):
        out.add("client")
    return out


def imports(refs, comp, roots):
    """Unit ids that code may import. `calls` go over the network, so they never allow an import."""
    out = set()
    own = {m["module"] for m in comp.get("modules") or []} if comp else set()
    for ref in refs:
        name, _, scope = ref.partition(" ")
        if scope in ("runtime", "test"):
            continue
        out.add(f"{comp['component']}.{name}" if name in own else name)
    return out


def units_of(arch):
    roots = {m["module"] for m in arch.get("modules") or []}
    units = {}
    for c in arch["components"]:
        name, mods = c["component"], c.get("modules") or []
        base = io_of(c)
        owned = {"persistence"} if c.get("datastores") else set()
        surfaces = {**(c.get("endpoints") or {}), **(c.get("ui_endpoints") or {})}
        shared = imports(as_list(c.get("uses")), c, roots)
        units[name] = {
            "paths": as_list(c.get("source_path")),
            "imports": sorted(shared | {f"{name}.{m['module']}" for m in mods}),
            "io": sorted(base | owned | ({"server"} if any(s.get("protocol") not in NOT_ON_NETWORK for s in surfaces.values()) else set())),
        }
        for m in mods:
            units[f"{name}.{m['module']}"] = {
                "paths": as_list(m.get("packages")),
                "imports": sorted(shared | imports(as_list(m.get("uses")), c, roots) | {name}),
                "io": sorted(base | io_of(m) | ({"server"} if m.get("serves") else set())),
            }
    for m in arch.get("modules") or []:
        units[m["module"]] = {"paths": as_list(m.get("packages")),
                              "imports": sorted(imports(as_list(m.get("uses")), None, roots)), "io": sorted(io_of(m))}
    return units


def surface_of(arch):
    out = {}
    for c in arch["components"]:
        for spec_group in ("endpoints", "ui_endpoints"):
            for ep, s in (c.get(spec_group) or {}).items():
                if s.get("protocol") in NOT_ON_NETWORK:
                    continue
                auth = s.get("auth")
                out[f"{c['component']}.{ep}"] = {
                    "exposure": s.get("exposure", c.get("exposure")), "address": s.get("address"),
                    "open": auth == "none" or any(p.endswith("-optional") for p in auth or {}),
                    "authz": as_list(s.get("authz"))}
    return out


def write_gate(path, accept):
    """Write architecture.gate.json next to architecture.yaml. Its deficiencies are a ratchet: new ones need `accept`."""
    out = path.with_name("architecture.gate.json")
    known = set(json.loads(out.read_text())["deficiencies"]) if out.exists() else None
    current = sorted(deficiencies)
    new = [d for d in current if known is not None and d not in known]
    if new and not accept:
        print("New deficiencies. Fix them, or ask the user whether to accept them with --accept:")
        print("\n".join(f"- {d}" for d in new))
        return 1
    arch = yaml.safe_load(path.read_text())
    out.write_text(json.dumps({
        "architecture_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "deficiencies": current, "units": units_of(arch), "surface": surface_of(arch)}, indent=1) + "\n")
    print(f"{out}: {len(current)} deficiencies, {len((known or set()) - set(current))} fixed, {len(new)} newly accepted")
    return 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = Path(args[0] if args else "docs/architecture.yaml")
    check(path, "--skip-paths" in sys.argv)
    code = report()
    return code or (write_gate(path, "--accept" in sys.argv) if "--gate" in sys.argv else 0)


if __name__ == "__main__":
    sys.exit(main())
