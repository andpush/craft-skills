# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema>=4.18", "pyyaml>=6"]
# ///
"""Render .craft/architecture.yaml and its ADRs as one HTML page in a temp folder.

Usage: uv run arch2html.py [.craft/architecture.yaml] [--no-open] [--out FILE]
Prints the page path and the number of architecture problems.
"""
import importlib.util
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from html_utils import esc, write  # noqa: E402

HERE = Path(__file__).resolve().parent
VALIDATOR = HERE / "validate.py"
APP_TYPES = {"web-app", "mobile-app", "desktop-app"}
NOT_ON_NETWORK = {"native", "cli", "schedule"}


def ml(v):
    """Text for a mermaid label."""
    return str(v).replace('"', "#quot;").replace("<", "‹").replace(">", "›").replace(";", "#59;")


def nid(prefix, name):
    return prefix + re.sub(r"\W", "_", name)


def as_list(v):
    return [] if v is None else v if isinstance(v, list) else [v]


def joined(v):
    return ", ".join(str(x) for x in as_list(v))


def chips(d):
    return "".join(f'<span class="chip"><b>{esc(k)}</b>{esc(joined(v))}</span>' for k, v in (d or {}).items())


def mermaid(code, wide=False):
    return f'<div class="diagram{" wide" if wide else ""}"><pre class="mermaid">{esc(code)}</pre></div>'


def arrow(item):
    text, label = (item, None) if isinstance(item, str) else next(iter(item.items()))
    a, op, b = re.match(r"^(\S+) (->|~>) (\S+)$", text).groups()
    return a, op, b, label


class Architecture:
    def __init__(self, data):
        self.d = data
        self.actors = data.get("actors") or {}
        self.externals = data.get("external") or {}
        self.components = {c["component"]: c for c in data.get("components") or []}
        self.root_modules = {m["module"]: m for m in data.get("modules") or []}
        self.notes = data.get("notes") or []
        self.stores = {s["datastore"]: s for s in data.get("datastores") or []}
        self.queues = {q["queue"]: q for q in data.get("queues") or []}
        self.private = {}  # store id -> (component, store)
        for c in self.components.values():
            for s in c.get("datastores") or []:
                self.private[s["datastore"]] = (c["component"], s)
        self.entity_home = {}
        for sid, s in [*self.stores.items(), *((k, v[1]) for k, v in self.private.items()), *self.queues.items()]:
            for e in s.get("entities") or {}:
                self.entity_home[e] = sid

    def holders(self, comp):
        """(module name or None, relation holder) for a component and its modules."""
        c = self.components[comp]
        return [(None, c)] + [(m["module"], m) for m in c.get("modules") or []]

    def access(self, rel, target):
        """[(component, module, entities)] for reads/writes/produces/consumes on target."""
        out = []
        for comp in self.components:
            for mod, h in self.holders(comp):
                if target in (h.get(rel) or {}):
                    out.append((comp, mod, (h.get(rel) or {})[target]))
        return out

    def who(self, rel, target, entity):
        names = []
        for comp, mod, ents in self.access(rel, target):
            if ents is None or entity in ents:
                names.append(f"{comp}.{mod}" if mod else comp)
        return names


# ---------- diagrams ----------

MAP_CLASSES = [
    "  classDef actor fill:#fde9c9,stroke:#c98a1b,color:#3b2a08",
    "  classDef comp fill:#dce8fb,stroke:#2f6fde,color:#0f2346",
    "  classDef store fill:#dff3e6,stroke:#2e7d4f,color:#0f2e1b",
    "  classDef private fill:#eef7f1,stroke:#2e7d4f,stroke-dasharray:4 3,color:#0f2e1b",
    "  classDef queue fill:#efe3fb,stroke:#7b43c9,color:#2a1047",
    "  classDef ext fill:#eceef1,stroke:#7a808a,stroke-dasharray:5 4,color:#22252a",
]


def system_map(m):
    L = ["flowchart LR"]
    for a, spec in m.actors.items():
        L.append(f'  {nid("a_", a)}(["{ml(a)}"]):::actor')
    L.append(f'  subgraph sys["{ml(m.d["system"])}"]')
    for name, c in m.components.items():
        lang = (c.get("tech") or {}).get("language")
        sub = " · ".join(x for x in [c.get("type"), joined(lang) if lang else None] if x)
        label = f"{ml(name)}<br/><small>{ml(sub)}</small>"
        t = c.get("type")
        shape = f'("{label}")' if t in APP_TYPES else f'[/"{label}"/]' if t == "console-app" else f'["{label}"]'
        L.append(f"    {nid('c_', name)}{shape}:::comp")
    for sid, (owner, s) in m.private.items():
        L.append(f'    {nid("s_", sid)}[("{ml(sid)}<br/><small>{ml(s.get("engine", ""))}</small>")]:::private')
    for sid, s in m.stores.items():
        L.append(f'    {nid("s_", sid)}[("{ml(sid)}<br/><small>{ml(s.get("engine", ""))}</small>")]:::store')
    for qid, q in m.queues.items():
        L.append(f'    {nid("q_", qid)}>"{ml(qid)}<br/><small>{ml(q.get("engine", ""))}</small>"]:::queue')
    L.append("  end")
    for x, spec in m.externals.items():
        L.append(f'  {nid("x_", x)}["{ml(x)}<br/><small>{ml(joined(spec.get("does")))}</small>"]:::ext')

    edges = {}  # (src, style, dst) -> labels

    def edge(src, style, dst, label=None):
        labels = edges.setdefault((src, style, dst), [])
        if label and label not in labels:
            labels.append(label)

    def node(ref):
        head = ref.split(".")[0]
        if head in m.components:
            return nid("c_", head), ref.split(".", 1)[1] if "." in ref else None
        if head in m.externals:
            return nid("x_", head), None
        return None, None

    for a, spec in m.actors.items():
        for comp in as_list(spec.get("uses")):
            if comp in m.components:
                ui = (m.components[comp].get("ui_endpoints") or {}).values()
                how = [s.get("address") or s.get("protocol") for s in ui if a in as_list(s.get("for"))]
                edge(nid("a_", a), "-->", nid("c_", comp), joined(how) or None)
    for x, spec in m.externals.items():
        for ref in as_list(spec.get("calls")):
            dst, ep = node(ref)
            if dst:
                edge(nid("x_", x), "-->", dst, ep)
    for comp in m.components:
        src = nid("c_", comp)
        for _, h in m.holders(comp):
            for ref in as_list(h.get("calls")):
                dst, ep = node(ref)
                if dst and dst != src:
                    edge(src, "-->", dst, ep)
            for q in h.get("produces") or {}:
                edge(src, "-.->", nid("q_", q))
            for q in h.get("consumes") or {}:
                edge(nid("q_", q), "-.->", src)
            for s in h.get("writes") or {}:
                edge(src, "==>", nid("s_", s), "writes")
            for s in h.get("reads") or {}:
                if (src, "==>", nid("s_", s)) not in edges:
                    edge(src, "-->", nid("s_", s), "reads")
    for sid, (owner, _) in m.private.items():
        edge(nid("c_", owner), "===", nid("s_", sid), "owns")
    for (src, style, dst), labels in edges.items():
        if style == "-->" and (src, "==>", dst) in edges:
            continue
        lab = f'|"{ml(", ".join(labels))}"|' if labels else ""
        L.append(f"  {src} {style}{lab} {dst}")
    L += ["  style sys fill:none,stroke:#8a909a,stroke-dasharray:6 4", *MAP_CLASSES]
    return "\n".join(L)


def impact_map(m, changed=(), new_edges=()):
    """Components and their dependencies only: `changed` highlighted, `new_edges` (from, to) in red."""
    names = [*m.components, *m.root_modules]
    deps = {(comp, str(ref).split()[0].split(".")[0]) for comp in m.components for _, h in m.holders(comp)
            for ref in [*as_list(h.get("uses")), *as_list(h.get("calls"))]}
    deps = sorted((a, b) for a, b in deps | set(new_edges) if a != b and a in names and b in names)
    L = ["flowchart LR", *(f'  {nid("c_", n)}["{ml(n)}"]:::comp' for n in names)]
    L += [f'  {nid("c_", a)} {"-. new .->" if (a, b) in new_edges else "-->"} {nid("c_", b)}' for a, b in deps]
    red = [str(i) for i, e in enumerate(deps) if e in new_edges]
    if red:
        L.append(f"  linkStyle {','.join(red)} stroke:#dc2626,stroke-width:2px,color:#dc2626")
    L += [f"  style {nid('c_', n)} fill:#fde68a,stroke:#b45309,stroke-width:3px,color:#111" for n in names if n in changed]
    return "\n".join([*L, *MAP_CLASSES])


def entity_label(rel, ents, per_line=3):
    """'writes: a, b, c<br/>d' for an edge; just the relation when entities aren't detailed."""
    names = [ml(e) for e in ents or []]
    lines = [", ".join(names[i:i + per_line]) for i in range(0, len(names), per_line)]
    return f"{rel}: " + "<br/>".join(lines) if lines else rel


def module_box(name, spec=None):
    does = "<br/>".join(ml(d) for d in as_list((spec or {}).get("does")))
    return f'["<b>{ml(name)}</b>' + (f"<br/><small>{does}</small>" if does else "") + '"]'


def module_map(m, comp):
    """A component's modules with what each does, uses, calls, stores and publishes.

    Relations declared on the component start at its border: they apply to every module.
    """
    c = m.components[comp]
    mods = c.get("modules") or []
    local = {x["module"] for x in mods}
    border = nid("g_", comp)
    L = ["flowchart LR", f'  subgraph {border}["{ml(comp)}"]']
    L += [f'    {nid("m_", x["module"])}{module_box(x["module"], x)}:::mod' for x in mods]
    L.append("  end")
    nodes, edges = {}, {}

    def edge(src, style, dst, label):
        labels = edges.setdefault((src, style, dst), [])
        if label not in labels:
            labels.append(label)

    def peer(name):
        """Node for something outside this component: a name not in architecture.yaml draws as external."""
        if name in m.components:
            node, cls = nid("c_", name), "comp"
        elif name in m.actors:
            node = nid("a_", name)
            nodes[node] = f'(["{ml(name)}"]):::actor'
            return node
        else:
            node, cls = nid("x_", name), "ext"
        nodes[node] = f'["{ml(name)}"]:::{cls}'
        return node

    def serving(ep):
        return [nid("m_", x["module"]) for x in mods if ep in as_list(x.get("serves"))] or [border]

    def store(sid):
        engine = (m.stores.get(sid) or (m.private.get(sid) or (None, {}))[1]).get("engine", "")
        cls = "store" if sid in m.stores else "private"
        nodes[nid("s_", sid)] = f'[("{ml(sid)}<br/><small>{ml(engine)}</small>")]:::{cls}'
        return nid("s_", sid)

    def queue(qid):
        engine = (m.queues.get(qid) or {}).get("engine", "")
        nodes[nid("q_", qid)] = f'>"{ml(qid)}<br/><small>{ml(engine)}</small>"]:::queue'
        return nid("q_", qid)

    for name, h in m.holders(comp):
        src = nid("m_", name) if name else border
        for u in as_list(h.get("uses")):
            ref, _, scope = u.partition(" ")
            ref = ref.removeprefix(f"{comp}.")
            dst = nid("m_", ref)
            if ref not in local:
                nodes[dst] = f"{module_box(ref, m.root_modules.get(ref))}:::lib"
            edge(src, "-->", dst, f"uses ({scope})" if scope else "uses")
        for ref in as_list(h.get("calls")):
            head, _, ep = ref.partition(".")
            if head == comp:
                continue
            if head in m.components or head in m.externals:
                edge(src, "-->", peer(head), ml(ep) if ep else "calls")
        for s, ents in (h.get("writes") or {}).items():
            edge(src, "==>", store(s), entity_label("writes", ents))
        for s, ents in (h.get("reads") or {}).items():
            edge(src, "-->", store(s), entity_label("reads", ents))
        for q, ents in (h.get("produces") or {}).items():
            edge(src, "-.->", queue(q), entity_label("produces", ents))
        for q, ents in (h.get("consumes") or {}).items():
            edge(queue(q), "-.->", src, entity_label("consumes", ents))
    for s in c.get("datastores") or []:
        edge(border, "===", store(s["datastore"]), "owns")

    others = [n for n in m.components if n != comp]
    for ep, spec in (c.get("endpoints") or {}).items():
        ref = f"{comp}.{ep}"
        callers = [n for n in others if any(ref in as_list(h.get("calls")) for _, h in m.holders(n))]
        callers += [x for x, s in m.externals.items() if ref in as_list(s.get("calls"))]
        callers += [a for a in as_list(spec.get("for")) if a not in m.components and a not in m.externals]
        for name in callers:
            for dst in serving(ep):
                edge(peer(name), "-->", dst, ml(ep))
    for n in others:
        if any(comp in as_list(h.get("calls")) for _, h in m.holders(n)):
            edge(peer(n), "-->", border, "calls")
    for ep, spec in (c.get("ui_endpoints") or {}).items():
        for actor in as_list(spec.get("for")):
            for dst in serving(ep):
                edge(peer(actor), "-->", dst, ml(ep))

    L += [f"  {node}{shape}" for node, shape in nodes.items()]
    L += [f'  {src} {style}|"{"<br/>".join(labels)}"| {dst}' for (src, style, dst), labels in edges.items()]
    L += [f"  style {border} fill:none,stroke:#8a909a,stroke-dasharray:6 4", *MAP_CLASSES,
          "  classDef mod fill:#dce8fb,stroke:#2f6fde,color:#0f2346",
          "  classDef lib fill:#eceef1,stroke:#7a808a,stroke-dasharray:5 4,color:#22252a"]
    return "\n".join(L)


def key_fields(fields):
    out = []
    for f in fields or []:
        parts = f.split()
        if "pk" in parts or any(p.startswith("uk") for p in parts) or "->" in parts:
            out.append(f)
    return out


def data_map(m):
    groups = [(sid, s, None) for sid, s in m.stores.items()] + [(sid, s, o) for sid, (o, s) in m.private.items()]
    if not any(s.get("entities") for _, s, _ in groups):
        return None
    L = ["flowchart LR"]
    for sid, s, owner in groups:
        title = f"{sid} · {owner}" if owner else sid
        L.append(f'  subgraph {nid("g_", sid)}["{ml(title)}"]')
        for e, fields in (s.get("entities") or {}).items():
            rows = "<br/>".join(ml(f.replace(" -> ", " → ")) for f in key_fields(fields))
            label = f"<b>{ml(e)}</b>" + (f"<br/><small>{rows}</small>" if rows else "")
            L.append(f'    {nid("e_", e)}["{label}"]:::ent')
        L.append("  end")
        L.append(f"  style {nid('g_', sid)} fill:none,stroke:#8a909a,stroke-dasharray:6 4")
    for sid, s, _ in groups:
        for e, fields in (s.get("entities") or {}).items():
            for f in fields or []:
                ref = re.search(r"-> (\S+)", f)
                if not ref:
                    continue
                target = ref.group(1).split(".")[0]
                if target not in m.entity_home or m.entity_home[target] in m.queues:
                    continue
                style = "-->" if m.entity_home[target] == sid else "-.->"
                L.append(f'  {nid("e_", e)} {style}|"{ml(f.split()[0])}"| {nid("e_", target)}')
    L.append("  classDef ent fill:#dff3e6,stroke:#2e7d4f,color:#0f2e1b,text-align:left")
    return "\n".join(L)


def state_diagram(transitions):
    L = ["stateDiagram-v2", "  direction LR"]
    states, incoming, outgoing = [], set(), set()
    for t in transitions:
        a, _, b, label = arrow(t)
        for s in (a, b):
            if s not in states:
                states.append(s)
        outgoing.add(a)
        incoming.add(b)
    sid = {s: nid("st_", s) for s in states}
    for s in states:
        L.append(f'  state "{ml(s)}" as {sid[s]}')
    for s in states:
        if s not in incoming:
            L.append(f"  [*] --> {sid[s]}")
    for t in transitions:
        a, _, b, label = arrow(t)
        L.append(f"  {sid[a]} --> {sid[b]}" + (f": {ml(label)}" if label else ""))
    for s in states:
        if s not in outgoing:
            L.append(f"  {sid[s]} --> [*]")
    return "\n".join(L)


def sequence(m, steps):
    """One lifeline per component; modules appear on the arrow labels."""
    def lifeline(p):
        head, _, mod = p.partition(".")
        return (head, mod) if mod and head in m.components else (p, None)

    L = ["sequenceDiagram", "  autonumber"]
    order = []
    for step in steps:
        a, _, b, _ = arrow(step)
        for p in (lifeline(a)[0], lifeline(b)[0]):
            if p not in order:
                order.append(p)
    pid = {p: f"p{i}" for i, p in enumerate(order)}
    for p in order:
        kind = "actor" if p in m.actors else "participant"
        L.append(f'  {kind} {pid[p]} as {ml(p)}')
    for step in steps:
        a, op, b, label = arrow(step)
        (src, src_mod), (dst, dst_mod) = lifeline(a), lifeline(b)
        text = " → ".join(x for x in (src_mod, label, dst_mod) if x)
        L.append(f"  {pid[src]} {'->>' if op == '->' else '--)'} {pid[dst]}: {ml(text)}")
    return "\n".join(L)


# ---------- sections ----------

def rel_rows(h):
    """kv rows for a relation holder."""
    rows = []
    if h.get("serves"):
        rows.append(("serves", joined(h["serves"])))
    if h.get("uses"):
        rows.append(("uses", joined(h["uses"])))
    if h.get("calls"):
        rows.append(("calls", joined(h["calls"])))
    for rel in ("produces", "consumes", "writes", "reads"):
        for target, ents in (h.get(rel) or {}).items():
            rows.append((rel, f"{target}: {joined(ents) if ents else 'all'}"))
    return rows


def kv(rows):
    if not rows:
        return ""
    return '<dl class="kv">' + "".join(f"<dt>{esc(k)}</dt><dd>{v}</dd>" for k, v in rows) + "</dl>"


def callouts(notes, ids):
    """Notes about any of these ids."""
    return "".join(f'<div class="note">{esc(n["note"])}</div>' for n in notes if set(n["about"]) & set(ids))


def notes_section(notes):
    return "".join(f'<div class="note">{esc(n["note"])}<div class="about">{esc(joined(n["about"]))}</div></div>'
                   for n in notes)


def auth_text(auth):
    return "none" if auth == "none" else "; ".join(f"{p}: {joined(v)}" for p, v in (auth or {}).items())


def security_section(m):
    """One row per network endpoint, most exposed first."""
    rows = []
    for name, c in m.components.items():
        for field in ("endpoints", "ui_endpoints"):
            for ep, spec in (c.get(field) or {}).items():
                if spec.get("protocol") in NOT_ON_NETWORK:
                    continue
                auth, exposure = spec.get("auth"), spec.get("exposure", c.get("exposure"))
                is_open = auth == "none" or any(p.endswith("-optional") for p in auth or {})
                rank = (0 if is_open else 1) if exposure == "internet" else {None: 2, "private": 3, "local": 4}[exposure]
                rows.append((rank, name, ep, spec, exposure, is_open))
    if not rows:
        return ""
    badge = {0: "must", 1: "should", 2: "should"}
    html = []
    for rank, name, ep, spec, exposure, is_open in sorted(rows, key=lambda r: r[0]):
        access = f"<span class='badge {badge.get(rank, 'current')}'>{esc(exposure or 'not set')}</span>"
        auth = auth_text(spec.get("auth")) + (" (open)" if is_open and spec.get("auth") != "none" else "")
        html.append(f"<tr><td><b>{esc(name)}.{esc(ep)}</b><div class='muted mono'>{esc(spec.get('address', ''))}</div></td>"
                    f"<td>{access}</td><td>{esc(auth)}</td><td>{esc(spec.get('identity', '—'))}</td>"
                    f"<td>{esc(joined(spec.get('authz')) or '—')}</td><td>{esc(joined(spec.get('for')))}</td></tr>")
    return ("<table><tr><th>endpoint</th><th>exposure</th><th>auth</th><th>identity</th><th>authz</th><th>for</th></tr>"
            + "".join(html) + "</table>")


def component_card(m, name, c):
    does = as_list(c.get("does"))
    rows = []
    for field, label in (("endpoints", "endpoint"), ("ui_endpoints", "ui endpoint")):
        for ep, spec in (c.get(field) or {}).items():
            auth = spec.get("auth")
            bits = [spec.get("protocol"), spec.get("address"), "idempotent" if spec.get("idempotent") else None,
                    f"for {joined(spec['for'])}" if spec.get("for") else None,
                    "no auth" if auth == "none" else auth_text(auth), spec.get("exposure", c.get("exposure")),
                    f"identity {spec['identity']}" if spec.get("identity") else None,
                    f"needs {joined(spec['authz'])}" if spec.get("authz") else None]
            spec_link = f' <span class="muted mono">{esc(spec["spec"])}</span>' if spec.get("spec") else ""
            rows.append((label, f"<b>{esc(ep)}</b> <span class='muted'>{esc(' · '.join(str(b) for b in bits if b))}</span>{spec_link}"))
    for s in c.get("datastores") or []:
        rows.append(("private store", f"<b>{esc(s['datastore'])}</b> <span class='muted'>{esc(s.get('engine', ''))}</span>"))
    rows += [(k, esc(v)) for k, v in rel_rows(c)]
    mods = c.get("modules") or []
    mod_html = ""
    if mods:
        items = []
        for x in mods:
            pk = f' <span class="muted mono">{esc(joined(x.get("packages")))}</span>'
            items.append(f'<div class="module"><b>{esc(x["module"])}</b> — {esc(joined(x.get("does")))}{pk}'
                         f'{kv([(k, esc(v)) for k, v in rel_rows(x)])}</div>')
        legend = ('<div class="legend">Solid arrow: uses, calls (label = endpoint) or reads · thick: writes · dashed: '
                  'message via queue · at the border: the component as a whole or code outside the listed '
                  'modules.</div>')
        mod_html = (f'<div class="modules"><h3>Modules</h3>{mermaid(module_map(m, name))}{legend}'
                    f'{"".join(items)}</div>')
    path = f'<span class="muted mono">{esc(c["source_path"])}</span>' if c.get("source_path") else ""
    ids = [name, *(f"{name}.{x['module']}" for x in mods), *(f"{name}.{e}" for e in c.get("endpoints") or {}),
           *(f"{name}.{e}" for e in c.get("ui_endpoints") or {})]
    return (f'<div class="card" id="c-{esc(name)}"><div class="head"><h3>{esc(name)}</h3>'
            f'<span class="badge">{esc(c.get("type", ""))}</span>{path}</div>'
            f'<ul class="does">{"".join(f"<li>{esc(d)}</li>" for d in does)}</ul>{callouts(m.notes, ids)}'
            f'<div class="chips">{chips(c.get("tech"))}</div>{kv(rows)}{mod_html}</div>')


def store_ids(sid, s):
    ents = s.get("entities") or {}
    return [sid, *ents, *(f"{e}.{str(f).split(' ')[0]}" for e, fields in ents.items() for f in fields or [])]


def data_section(m):
    parts = []
    dm = data_map(m)
    if dm:
        parts.append(mermaid(dm, wide=True))
        parts.append('<div class="legend">Keys and references only. Solid arrow: reference inside a store; '
                     'dashed: logical reference across stores.</div>')
    for sid, s in m.stores.items():
        meta = " · ".join(x for x in [s.get("engine"), s.get("deploy"), "shared",
                                       f"schema owner {s['schema_owner']}" if s.get("schema_owner") else None,
                                       s.get("source_path"), f"login {s['credential']}" if s.get("credential") else None] if x)
        rows = "".join(
            f"<tr><td><b>{esc(e)}</b></td><td class='mono'>{esc(', '.join(fields or []))}</td>"
            f"<td>{esc(', '.join(m.who('writes', sid, e)) or '—')}</td>"
            f"<td>{esc(', '.join(m.who('reads', sid, e)) or '—')}</td></tr>"
            for e, fields in (s.get("entities") or {}).items())
        parts.append(f'<div class="store"><h3>{esc(sid)}</h3><p class="meta">{esc(meta)}</p>{callouts(m.notes, store_ids(sid, s))}'
                     f"<table><tr><th>entity</th><th>fields</th><th>written by</th><th>read by</th></tr>{rows}</table></div>")
    for sid, (owner, s) in m.private.items():
        meta = " · ".join(x for x in [s.get("engine"), s.get("deploy"), f"private to {owner}",
                                       f"login {s['credential']}" if s.get("credential") else None] if x)
        rows = "".join(f"<tr><td><b>{esc(e)}</b></td><td class='mono'>{esc(', '.join(fields or []))}</td></tr>"
                       for e, fields in (s.get("entities") or {}).items())
        parts.append(f'<div class="store"><h3>{esc(sid)}</h3><p class="meta">{esc(meta)}</p>{callouts(m.notes, store_ids(sid, s))}'
                     f"<table><tr><th>entity</th><th>fields</th></tr>{rows}</table></div>")
    for qid, q in m.queues.items():
        meta = " · ".join(x for x in [q.get("engine"), q.get("deploy"), q.get("address"),
                                       f"schema owner {q['schema_owner']}" if q.get("schema_owner") else None] if x)
        rows = "".join(
            f"<tr><td><b>{esc(e)}</b></td><td class='mono'>{esc(', '.join(fields or []))}</td>"
            f"<td>{esc(', '.join(m.who('produces', qid, e)) or '—')}</td>"
            f"<td>{esc(', '.join(m.who('consumes', qid, e)) or '—')}</td></tr>"
            for e, fields in (q.get("entities") or {}).items())
        parts.append(f'<div class="store"><h3>{esc(qid)} <span class="badge">queue</span></h3><p class="meta">{esc(meta)}</p>'
                     f"<table><tr><th>message</th><th>fields</th><th>produced by</th><th>consumed by</th></tr>{rows}</table></div>")
    return "".join(parts)


def rules_section(rules):
    rows = []
    for r in rules:
        level = r.get("level", "must")
        sel = "; ".join(f"{k}: {joined(v)}" for k, v in (r.get("applies_to") or {}).items()) or "whole system"
        check = f'<span class="mono">{esc(r["check"])}</span>' if r.get("check") else '<span class="muted">review</span>'
        why = f'<div class="muted">{esc(r["rationale"])}</div>' if r.get("rationale") else ""
        rows.append(f"<tr><td><b>{esc(r['rule'])}</b></td><td><span class='badge {esc(level)}'>{esc(level)}</span></td>"
                    f"<td>{esc(r['statement'])}{why}</td><td>{esc(sel)}</td><td>{check}</td></tr>")
    return ("<table><tr><th>rule</th><th>level</th><th>statement</th><th>applies to</th><th>enforced by</th></tr>"
            + "".join(rows) + "</table>")


# ---------- decisions ----------

def load_adrs(folder):
    adrs = []
    if not folder.is_dir():
        return adrs
    for f in sorted(folder.glob("*.md")):
        mt = re.match(r"(\d{4}-\d{2}-\d{2})-(.+)\.md$", f.name)
        if not mt:
            continue
        text, fm = f.read_text(), {}
        if text.startswith("---"):
            _, front, text = text.split("---", 2)
            fm = yaml.safe_load(front) or {}
        title = re.search(r"^# (.+)$", text, re.M)
        sections = {k.strip().lower(): v.strip() for k, v in re.findall(r"^## (.+?)\n(.*?)(?=^## |\Z)", text, re.M | re.S)}
        rejected = []
        for line in re.findall(r"^[-*] (.+)$", sections.get("rejected", ""), re.M):
            opt, why = (re.split(r" — | -- | - |: ", line, maxsplit=1) + [""])[:2]
            revisit = re.search(r"revisit if (.+)$", why)
            rejected.append({"option": opt.strip(), "why": re.sub(r";?\s*(revisit if .+|no revisit)$", "", why).strip(),
                             "revisit": revisit.group(1).strip() if revisit else None})
        decision = sections.get("decision", "").split("\n\n")[0].strip()
        adrs.append({"stem": f.stem, "date": mt.group(1), "slug": mt.group(2), "path": f,
                     "title": title.group(1).strip() if title else mt.group(2),
                     "supersedes": [str(s) for s in as_list(fm.get("supersedes"))],
                     "decision": decision, "rejected": rejected, "superseded_by": None})
    by_key = {a["stem"]: a for a in adrs} | {a["slug"]: a for a in adrs}
    for a in adrs:
        for s in a["supersedes"]:
            if s in by_key:
                by_key[s]["superseded_by"] = a
    return adrs


def findings_section(deficiencies, improvements):
    def block(title, items, css):
        if not items:
            return ""
        return f'<div class="{css}"><b>{title}</b><ul>{"".join(f"<li>{esc(i)}</li>" for i in items)}</ul></div>'
    return block("Deficiencies", deficiencies, "problems") + block("Improvements", improvements, "problems warn")


def decisions_section(adrs):
    items = []
    for a in adrs:
        status = (f'<span class="badge superseded">superseded</span>' if a["superseded_by"]
                  else '<span class="badge current">current</span>')
        rel = []
        if a["superseded_by"]:
            s = a["superseded_by"]
            rel.append(f'superseded by <a href="#adr-{esc(s["stem"])}">{esc(s["title"])}</a>')
        for s in a["supersedes"]:
            rel.append(f'replaces <a href="#adr-{esc(s)}">{esc(s)}</a>')
        branches = "".join(
            f'<li><span class="opt">{esc(r["option"])}</span>'
            + (f" — {esc(r['why'])}" if r["why"] else "")
            + (f' <span class="revisit">↺ revisit if {esc(r["revisit"])}</span>' if r["revisit"] else "")
            + "</li>" for r in a["rejected"])
        items.append(
            f'<li class="adr {"superseded" if a["superseded_by"] else "current"}" id="adr-{esc(a["stem"])}">'
            f'<div class="head"><time>{esc(a["date"])}</time>'
            f'<a class="title" href="{esc(a["path"].as_uri())}">{esc(a["title"])}</a>{status}</div>'
            + (f'<p class="decision">{esc(a["decision"])}</p>' if a["decision"] else "")
            + (f'<div class="rel">{" · ".join(rel)}</div>' if rel else "")
            + (f'<ul class="branches">{branches}</ul>' if branches else "")
            + "</li>")
    return f'<ol class="timeline">{"".join(items)}</ol>'


# ---------- page ----------

def problems(path):
    if not VALIDATOR.exists():
        return [], ["validator not found: architecture not checked"], [], []
    spec = importlib.util.spec_from_file_location("arch_validate", VALIDATOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    errors, warnings = mod.check(path)
    return list(errors), list(warnings), list(mod.deficiencies), list(mod.improvements)


def render(path):
    data = yaml.safe_load(path.read_text())
    errors, warnings, deficiencies, improvements = problems(path)
    m = Architecture(data)
    root = path.resolve().parent
    if root.name == ".craft":  # architecture.yaml lives in .craft/; its paths are relative to the repo root
        root = root.parent
    adrs = load_adrs(root / (data.get("decisions") or ".craft/adr"))

    sections = []  # (anchor, title, html)
    if m.components:
        legend = ("Solid arrow: sync call (label = endpoint) · dashed: message via queue · thick: writes · "
                  "cylinder: datastore (dashed border = private) · flag: queue · dashed box: external system")
        sections.append(("map", "System map", mermaid(system_map(m), wide=True) + f'<div class="legend">{esc(legend)}</div>'))
        if m.notes:
            sections.append(("notes", "Read before changing", notes_section(m.notes)))
        cards = "".join(component_card(m, n, c) for n, c in m.components.items())
        libs = "".join(
            f'<div class="card"><div class="head"><h3>{esc(n)}</h3><span class="badge">library</span>'
            f'<span class="muted mono">{esc(x.get("artifact", ""))}</span></div>'
            f'<ul class="does"><li>{esc(joined(x.get("does")))}</li></ul>{callouts(m.notes, [n])}{kv([(k, esc(v)) for k, v in rel_rows(x)])}</div>'
            for n, x in m.root_modules.items())
        sections.append(("components", "Components", f'<div class="grid">{cards}{libs}</div>'))
        surface = security_section(m)
        if surface:
            sections.append(("exposure", "Exposure", surface))
    if m.stores or m.private or m.queues:
        sections.append(("data", "Data", data_section(m)))
    if data.get("states"):
        sections.append(("states", "Lifecycles", '<div class="two">' + "".join(
            f'<div><h3>{esc(k)}</h3>{mermaid(state_diagram(v))}</div>' for k, v in data["states"].items()) + "</div>"))
    if data.get("flows"):
        sections.append(("flows", "Main flows", "".join(
            f'<div class="store"><h3>{esc(k)}</h3>{mermaid(sequence(m, v))}</div>' for k, v in data["flows"].items())))
    if data.get("rules"):
        sections.append(("rules", "Rules", rules_section(data["rules"])))
    if data.get("glossary"):
        sections.append(("glossary", "Glossary", '<dl class="glossary">' + "".join(
            f"<dt>{esc(k)}</dt><dd>{esc(v or '')}</dd>" for k, v in data["glossary"].items()) + "</dl>"))
    if adrs:
        current = sum(1 for a in adrs if not a["superseded_by"])
        rejected = sum(len(a["rejected"]) for a in adrs)
        sections.append(("decisions", "Decisions",
                         f'<p class="muted">{len(adrs)} decisions, {current} current, {rejected} rejected options.</p>'
                         + decisions_section(adrs)))
    if deficiencies or improvements:
        sections.append(("findings", "Findings", findings_section(deficiencies, improvements)))

    counts = [f"{len(m.components)} components", f"{len(m.stores) + len(m.private)} datastores",
              f"{len(m.queues)} queues", f"{len(m.externals)} external systems",
              f"{len(data.get('rules') or [])} rules", f"{len(adrs)} decisions",
              f"{len(deficiencies)} deficiencies", f"{len(improvements)} improvements"]
    banner = ""
    if errors:
        banner += (f'<div class="problems"><b>{len(errors)} architecture errors</b> — fix with arch3'
                   f'<ul>{"".join(f"<li>{esc(e)}</li>" for e in errors)}</ul></div>')
    if warnings:
        banner += (f'<div class="problems warn"><b>{len(warnings)} warnings</b>'
                   f'<ul>{"".join(f"<li>{esc(w)}</li>" for w in warnings)}</ul></div>')
    actors = ", ".join(f"{a} ({joined(s.get('does'))})" for a, s in m.actors.items())
    head = (f'<header><h1>{esc(data["system"])}</h1><p class="summary">{esc(data.get("summary", ""))}</p>'
            f'<div class="chips">{chips(data.get("tech"))}</div>'
            + (f'<p class="counts">Actors: {esc(actors)}</p>' if actors else "")
            + f'<p class="counts">{esc(" · ".join(counts))}</p>{banner}</header>')
    nav = '<nav><div>' + "".join(f'<a href="#{a}">{esc(t)}</a>' for a, t, _ in sections) + "</div></nav>"
    body = head + nav + "<main>" + "".join(f'<section id="{a}"><h2>{esc(t)}</h2>{h}</section>' for a, t, h in sections) + "</main>"
    return f"{data['system']} architecture", body, errors, warnings


def main():
    args = sys.argv[1:]
    out = None
    if "--out" in args:
        i = args.index("--out")
        out = Path(args[i + 1])
        del args[i:i + 2]
    files = [a for a in args if not a.startswith("--")]
    path = Path(files[0] if files else ".craft/architecture.yaml")
    if not path.exists():
        print(f"{path} not found — create it with the arch3 skill")
        return 2
    title, body, errors, warnings = render(path)
    system = re.sub(r"\W+", "-", title.removesuffix(" architecture")).lower()
    write(title, body, f"arch-{system}", out, "--no-open" not in args)
    print(f"{len(errors)} architecture errors, {len(warnings)} warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
