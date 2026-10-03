"""Export the current Rev B lighting data of one floor to ref_RevB/lighting_<FLOOR>.json + walls_<FLOOR>.svg (input of the web tool).

    set FLOOR=GF  (or FF)
    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\export_lighting_json.py

Data = exactly what make_lighting_drawings(.py/_cn.py) draw from (CIRC / PANEL / MOUNT / PLATES / WL ...), so replaying the JSON
through lighting_io.py must give identical PPTs (tests T1 / T2).  Geometry: walls, doors, windows, stairs and room names from the
plan group of the user's PPT (GF: v4 slide 2 "Group 536"; FF: v6 slide 6 "二层平面（横向）"), in slide EMU like every other coordinate.
Writes ref_RevB/lighting_<FLOOR>.json (reference answer for T1/T2) and walls_<FLOOR>.svg. The working data lighting_<F>.json is made
from it by apply_revC.py, which also rebuilds lighting_data.js (build_data_js.py).
"""
import os, re, json, math

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.dirname(HERE)
FLOOR = os.environ.get("FLOOR", "GF")
os.environ.pop("LIGHTING_JSON", None)

# ---- 1. the drawing scripts' own data (cn top part execs the en data part, which execs make_lighting_plan) ----
_path = os.path.join(PROD, "make_lighting_drawings_cn.py")
_src = open(_path, encoding="utf-8").read()
G = {"__file__": _path}
exec(compile(_src[:_src.index("# ---------------- Chinese symbols ----------------")], _path, "exec"), G)
_notes = _src[_src.index("NOTES = [\"设计说明\""):_src.index("NOTES = CN_NOTES or NOTES")]
exec(_notes, G)

U = G["U"]; A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'


# ---- 2. geometry from the plan group ----
def xf(el):
    x = el.find(A + 'xfrm')
    rot = int(x.get('rot', '0')) / 60000
    o, e = x.find(A + 'off'), x.find(A + 'ext')
    co, ce = x.find(A + 'chOff'), x.find(A + 'chExt')
    r = dict(ox=int(o.get('x')), oy=int(o.get('y')), ex=int(e.get('cx')), ey=int(e.get('cy')), rot=rot,
             fh=x.get('flipH') == '1', fv=x.get('flipV') == '1')
    if co is not None:
        r.update(cx=int(co.get('x')), cy=int(co.get('y')), cex=int(ce.get('cx')), cey=int(ce.get('cy')))
    return r


def placer(T, d, child):
    """Map a point of the frame (group child space, or a shape's own box when child=False) into T's space."""
    mx, my = d['ox'] + d['ex'] / 2, d['oy'] + d['ey'] / 2; a = math.radians(d['rot'])

    def f(px, py):
        if child:
            X = d['ox'] + (px - d['cx']) * d['ex'] / (d['cex'] or 1); Y = d['oy'] + (py - d['cy']) * d['ey'] / (d['cey'] or 1)
        else:
            X, Y = px, py
        if d['fh']: X = 2 * mx - X
        if d['fv']: Y = 2 * my - Y
        dx, dy = X - mx, Y - my
        return T(mx + dx * math.cos(a) - dy * math.sin(a), my + dx * math.sin(a) + dy * math.cos(a))
    return f


def walk(shapes, T, par=()):
    for x in shapes:
        yield x, T, par
        if x.shape_type == 6:
            yield from walk(x.shapes, placer(T, xf(x._element.grpSpPr), True), par + (x.name,))


def shape_paths(sp, T):
    """Freeform / rectangle outline -> list of subpaths [(x, y), ...] (closed flag) in slide EMU."""
    spPr = sp._element.spPr; d = xf(spPr); S = placer(T, d, False)
    geo = spPr.find(A + 'custGeom'); out = []
    if geo is None:   # preset shape: use its box
        pts = [(d['ox'], d['oy']), (d['ox'] + d['ex'], d['oy']), (d['ox'] + d['ex'], d['oy'] + d['ey']), (d['ox'], d['oy'] + d['ey'])]
        return [([S(*p) for p in pts], True)]
    for path in geo.find(A + 'pathLst'):
        w = int(path.get('w', d['ex']) or 1); h = int(path.get('h', d['ey']) or 1)
        L = lambda px, py: S(d['ox'] + px * d['ex'] / w, d['oy'] + py * d['ey'] / h)
        cur, sub, last = [], None, (0, 0)
        for cmd in path:
            tag = cmd.tag.replace(A, '')
            pts = [(int(p.get('x')), int(p.get('y'))) for p in cmd.findall(A + 'pt')]
            if tag == 'moveTo':
                if sub and len(sub) > 1: out.append((sub, False))
                sub = [L(*pts[0])]; last = pts[0]
            elif tag == 'lnTo':
                sub.append(L(*pts[0])); last = pts[0]
            elif tag in ('cubicBezTo', 'quadBezTo'):
                p0 = last; ctrl = pts
                for i in range(1, 9):
                    t = i / 8
                    if tag == 'cubicBezTo':
                        q = [(1 - t) ** 3 * p0[k] + 3 * (1 - t) ** 2 * t * ctrl[0][k] + 3 * (1 - t) * t * t * ctrl[1][k] + t ** 3 * ctrl[2][k] for k in (0, 1)]
                    else:
                        q = [(1 - t) ** 2 * p0[k] + 2 * (1 - t) * t * ctrl[0][k] + t * t * ctrl[1][k] for k in (0, 1)]
                    sub.append(L(*q))
                last = pts[-1]
            elif tag == 'arcTo':
                wr, hr = int(cmd.get('wR')), int(cmd.get('hR')); st, sw = int(cmd.get('stAng')) / 60000, int(cmd.get('swAng')) / 60000
                a0 = math.radians(st); cx, cy = last[0] - wr * math.cos(a0), last[1] - hr * math.sin(a0)
                for i in range(1, 13):
                    a = math.radians(st + sw * i / 12); q = (cx + wr * math.cos(a), cy + hr * math.sin(a)); sub.append(L(*q))
                last = q
            elif tag == 'close':
                if sub and len(sub) > 1: out.append((sub, True))
                sub = None
        if sub and len(sub) > 1: out.append((sub, False))
    return out


def classify(name):
    n = name[2:] if name.startswith("墙_") else name
    if re.search(r"Door|Leaf|Jamb|jamb|DDA_|Architrave|Reveal|Astragal|Mould|SP_|Transom|Bifold|WR_|Room199|Rear215|Casing", n): return "door"
    if re.search(r"Window", n): return "window"
    if re.search(r"Stair|Baluster|Landing|Winder|Lift|Understair|V11_", n): return "stair"
    return "wall"


p, src = G["p"], G["src"]
plan = [x for x in src.shapes if x.name == G["PLAN_GROUP"]][0]
ident = lambda a, b: (a, b)
layers = {"wall": [], "door": [], "window": [], "stair": []}
rooms = []
for x, T, par in walk(src.shapes, ident):
    if G["PLAN_GROUP"] not in par:
        continue
    if any(q.startswith("墙体") for q in par) or (x.name == "墙" and x.shape_type == 5):
        if x.shape_type != 6:
            for pts, closed in shape_paths(x, T):
                layers[classify(x.name)].append(dict(name=x.name, pts=[(round(a), round(b)) for a, b in pts], closed=closed))
    elif any(q.startswith("房间名") for q in par) and x.has_text_frame and x.text_frame.text.strip():
        c = T(x.left + x.width / 2, x.top + x.height / 2)
        rooms.append(dict(name=x.text_frame.text.strip(), x=round(c[0]), y=round(c[1])))

allpts = [q for L in layers.values() for s in L for q in s["pts"]]
X0, Y0 = min(a for a, b in allpts), min(b for a, b in allpts)
X1, Y1 = max(a for a, b in allpts), max(b for a, b in allpts)
pad = 300000
VB = (X0 - pad, Y0 - pad, X1 - X0 + 2 * pad, Y1 - Y0 + 2 * pad)

STY = {"wall": 'fill="#9E9E9E" stroke="#595959"', "door": 'fill="#d9c7a7" stroke="#8a6d3b"',
       "window": 'fill="#cfe3f3" stroke="#5b8db8"', "stair": 'fill="none" stroke="#9a9a9a"'}
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{" ".join(str(v) for v in VB)}" data-floor="{FLOOR}" data-units="slide EMU">']
for k in ("stair", "window", "door", "wall"):
    svg.append(f'<g class="{k}" {STY[k]} stroke-width="3810" fill-rule="evenodd">')
    for s in layers[k]:
        d = "M" + " L".join(f"{a} {b}" for a, b in s["pts"]) + (" Z" if s["closed"] else "")
        svg.append(f'<path data-name="{s["name"]}" d="{d}"/>')
    svg.append('</g>')
svg.append('<g class="rooms" font-size="110" fill="#555" text-anchor="middle" dominant-baseline="middle">')   # text in 1/1000 scale (browsers cap font size)
for r in rooms:
    svg.append(f'<text transform="translate({r["x"]} {r["y"]}) scale(1000)">{r["name"]}</text>')
svg.append('</g></svg>')
svg_text = "\n".join(svg)
open(os.path.join(HERE, f"walls_{FLOOR}.svg"), "w", encoding="utf-8").write(svg_text)

# ---- 3. JSON ----
LP, PANEL, MOUNT, CIRC, CL, DESC = G["LP"], G["PANEL"], G["MOUNT"], G["CIRC"], G["CL"], G["DESC"]


def kind(n):
    if n.startswith("主灯位待选"): return "待选"
    if n.startswith("主灯"): return "主灯"
    if n.startswith("射灯"): return "筒灯"
    if n.startswith("壁灯"): return "壁灯"
    return "地灯"


OUTDOOR = re.compile(r"G25|G26|地灯")
lights = [dict(id=n, kind=kind(n), x=pt[0], y=pt[1], sheet=G["LSHEET"].get(n, 0), outdoor=bool(OUTDOOR.search(n))) for n, pt in LP.items()]
special = {}
for k, t in G["EXTRA_KEYS"].items():
    special[k] = dict(text=t, tag=G["EXTRA_TAG"].get(k, "?"))
    if k in G["RISER"]: special[k]["riser"] = G["RISER"][k]
    if t.endswith("（FI）"): special[k]["fan"] = True
if FLOOR == "GF": special["30"]["link"] = dict(floor="FF", circuit="L11")
plates = []
for sid, pn, loc, sh in G["PLATES"]:
    g, keys = PANEL[pn]
    plates.append(dict(id=sid, panel=pn, gangs=g, keys=list(keys), x=MOUNT[pn][0], y=MOUNT[pn][1], location=loc, sheet=sh,
                       middle_keys=[k for s, k in sorted(G["MIDDLE_KEYS"]) if s == sid]))
fcus = [dict(id=f, panel=pn, key=k, x=MOUNT[pn][0], y=MOUNT[pn][1]) for f, pn, k in G["FCUS"]]
circuits = []
for cid, desc, keys, ls in CIRC:
    c = dict(id=cid, letter=CL[cid], name=DESC[cid], keys=list(keys), lights=list(ls), wl=G["C2W"][cid])
    if cid in G["ASSUMED"]: c["assumed"] = G["ASSUMED"][cid]
    if cid in G["TBC"]: c["tbc"] = G["TBC"][cid]
    if G["REMOTE"].get(cid): c["remote"] = list(G["REMOTE"][cid])
    if FLOOR == "FF" and cid == "L11": c["remote_links"] = [dict(floor="GF", plate="S6", key="30")]
    circuits.append(c)
wl = {w: dict(name=d["name"], br=d["br"], circ=list(d["circ"]), n=d.get("n")) for w, d in G["WL"].items()}
other = G["WL_FF"] if FLOOR == "GF" else G["WL_GF_DEF"]
data = dict(
    schema="27pr-lighting/1", floor=FLOOR,
    source=dict(pptx=G["NS"]["SRC"], slide=G["NS"]["SLIDE"] + 1, plan_group=G["PLAN_GROUP"], m_base=G["M_BASE"]),
    units=dict(coords="slide EMU (12192000 x 6858000 slide)", emu_per_px=U, emu_per_m=G["M_OLD"], view_box=VB),
    meta=dict(version=G["VERSION"], basis=G["BASIS"], keyplan_note=G["KEYPLAN_NOTE"], plate_note5=G["PLATE_NOTE5"],
              fcu_row=G["FCU_ROW"], cn_notes=G["NOTES"]),
    rooms=rooms, zones={str(z): dict(name=d["name"], view=list(d["view"]), member=list(d["member"])) for z, d in G["ZONES"].items()},
    lights=lights, plates=plates, special_keys=special, fcus=fcus,
    door_switches=[dict(d) for d in G["DOORSW"]], circuits=circuits, wl=wl,
    wl_other={w: dict(name=d["name"], br=d["br"], circ=list(d["circ"]), n=d.get("n")) for w, d in other.items()},
    board=dict(x=G["AL1"][0], y=G["AL1"][1], label=G["BOARD_LABEL"], riser=FLOOR == "FF"),
    doors=[dict(name=s["name"], pts=s["pts"]) for s in layers["door"]],
    walls_svg=f"walls_{FLOOR}.svg")
os.makedirs(os.path.join(HERE, "ref_RevB"), exist_ok=True)   # Rev B reference only; the working data (Rev C …) is lighting_<F>.json, see apply_revC.py
open(os.path.join(HERE, "ref_RevB", f"lighting_{FLOOR}.json"), "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, indent=1))

print(FLOOR, "lights", len(lights), "plates", len(plates), "circuits", len(circuits), "rooms", len(rooms),
      {k: len(v) for k, v in layers.items()}, "viewBox", VB)
