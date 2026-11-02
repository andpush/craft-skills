# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "pyyaml>=6"]
# ///
"""Validate architecture.yaml: schema, references, flows, states, ownership.

Usage: uv run validate.py [architecture.yaml] [--skip-paths]
Exit 1 on errors; warnings are printed but pass.
"""
import json
import re
import sys
from pathlib import Path

import jsonschema
import yaml

SCHEMA = Path(__file__).resolve().parent.parent / "reference" / "architecture.schema.json"
RELATIONS = ("uses", "calls", "produces", "consumes", "reads", "writes")
errors, warnings = [], []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def as_list(v):
    return [] if v is None else v if isinstance(v, list) else [v]


def arrow(item):
    """('a', '->', 'b', label) from 'a -> b' or {'a -> b': label}."""
    text, label = (item, None) if isinstance(item, str) else next(iter(item.items()))
    a, op, b = re.match(r"^(\S+) (->|~>) (\S+)$", text).groups()
    return a, op, b, label


def check(path, skip_paths=False):
    """Validate the model at path; return (errors, warnings)."""
    errors.clear()
    warnings.clear()
    model = yaml.safe_load(Path(path).read_text())
    path = Path(path)
    root = path.resolve().parent

    schema_errors = list(jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(model))
    for e in schema_errors:
        err(f"schema: {e.json_path}: {e.message}")
    if schema_errors:
        return errors, warnings

    actors = model.get("actors") or {}
    externals = model.get("external") or {}
    components = {c["component"]: c for c in model["components"]}
    root_modules = {m["module"]: m for m in model.get("modules") or []}
    stores = {d["datastore"]: d for d in model.get("datastores") or []}
    queues = {q["queue"]: q for q in model.get("queues") or []}

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
        for rel, pool in (("produces", queues), ("consumes", queues), ("reads", stores), ("writes", stores)):
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
        for m in c.get("modules") or []:
            check_relations(m, f"module {name}.{m['module']}", name)
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

    # endpoint audience against declared callers; names outside the model are not checked
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
            warn(f"entity {ent}: written by several components ({', '.join(sorted(ws))})")
    for s in stores.values():
        if s.get("schema_owner") and s["schema_owner"] not in components:
            err(f"datastore {s['datastore']}: schema_owner '{s['schema_owner']}' is not a component")
    for q in queues.values():
        if q.get("schema_owner") and q["schema_owner"] not in components:
            err(f"queue {q['queue']}: schema_owner '{q['schema_owner']}' is not a component")

    # states
    for key in model.get("states") or {}:
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

    for flow, steps in (model.get("flows") or {}).items():
        for step in steps:
            a, op, b, label = arrow(step)
            (ka, ca, ma), (kb, cb, _) = participant(a), participant(b)
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
            elif ka == "component":
                calls = allowed(ca, ma)["calls"]
                ok = any(r == cb or r.split(".")[0] == cb for r in calls) if kb == "component" else b in calls
            else:
                ok = False
            if not ok:
                err(f"{where} — not allowed by declared relations")

    # rules
    for r in model.get("rules") or []:
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
    print(f"{len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check(args[0] if args else "architecture.yaml", "--skip-paths" in sys.argv)
    return report()


if __name__ == "__main__":
    sys.exit(main())
