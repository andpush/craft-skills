# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "pyyaml>=6"]
# ///
"""Write docs/architecture.gate.json: what `verify` enforces, flattened from the model.

Usage: uv run gate.py [docs/architecture.yaml] [--accept]
The file's deficiencies are a ratchet: a new one exits 1 unless --accept; fixed ones drop out.
Stack checks read only this file and fail when model_sha256 no longer matches the model.
"""
import hashlib
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate  # noqa: E402

NOT_ON_NETWORK = validate.NOT_ON_NETWORK
as_list = validate.as_list


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


def units_of(model):
    roots = {m["module"] for m in model.get("modules") or []}
    units = {}
    for c in model["components"]:
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
    for m in model.get("modules") or []:
        units[m["module"]] = {"paths": as_list(m.get("packages")),
                              "imports": sorted(imports(as_list(m.get("uses")), None, roots)), "io": sorted(io_of(m))}
    return units


def surface_of(model):
    out = {}
    for c in model["components"]:
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


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = Path(args[0] if args else "docs/architecture.yaml")
    errors, _ = validate.check(path)
    if errors:
        validate.report()
        return 1
    out = path.with_name("architecture.gate.json")
    known = set(json.loads(out.read_text())["deficiencies"]) if out.exists() else None
    current = sorted(validate.deficiencies)
    new = [d for d in current if known is not None and d not in known]
    if new and "--accept" not in sys.argv:
        print("New deficiencies. Fix them, or ask the user whether to accept them with --accept:")
        print("\n".join(f"- {d}" for d in new))
        return 1
    model = yaml.safe_load(path.read_text())
    out.write_text(json.dumps({
        "model_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "deficiencies": current, "units": units_of(model), "surface": surface_of(model)}, indent=1) + "\n")
    fixed = (known or set()) - set(current)
    print(f"{out}: {len(current)} deficiencies, {len(fixed)} fixed, {len(new)} newly accepted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
