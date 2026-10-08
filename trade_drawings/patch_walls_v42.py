"""Sync lighting_tool/walls_<F>.svg with the door changes made in model v42 (2026-10-07/08), shared by the trade drawings
and the web tool.

Inside small zones only, the PPT-derived wall / door shapes are replaced by the v42 horizontal section (_v42_section.json,
GF z = 1.0, FF z = 4.1, exported from Blender): north-bath door moved 0.20 m along its west wall, bedroom 2 door 79 mm west +
the 100 mm corridor nib, GF stair -> kitchen opening (x 2.530) with its 762 door, and the full-height GF sofa wall
between 客厅 and 起居室 (V12_Continuous_Flat_Sofa_Wall, missing from the PPT walls).  Everything outside the zones is untouched.
The first run keeps the original as walls_<F>_ppt.svg; later runs always patch from that copy (idempotent).

    python products/trade_drawings/patch_walls_v42.py      (then lighting_tool/build_data_js.py for the web tool)
"""
import json, os, re, shutil
from shapely.geometry import Polygon, box, MultiPolygon, LineString
from shapely.ops import polygonize, unary_union
from plan_base import Frame, TOOL

HERE = os.path.dirname(os.path.abspath(__file__))
WALLISH = re.compile(r"Wall_Shell|Infill|Nib_100|Fill_Bed2|Partition|Sofa_Wall")
DOORISH = re.compile(r"Leaf|Jamb|Lining")
# floor: [(name, wall zone (x0, x1, y0, y1), door zone)] in Blender metres
ZONES = {
    "FF": [("北卫门", (-2.95, -2.45, 6.45, 7.70), (-3.60, -2.45, 6.45, 7.70)),
           ("卧室2门", (1.45, 2.75, 4.20, 4.75), (1.45, 2.75, 3.55, 4.75))],
    "GF": [("厨房门", (2.30, 3.50, 7.85, 8.30), (2.30, 3.50, 7.85, 9.00)),
           ("客厅 / 起居室之间的沙发墙（PPT 漏画，v42 有，到顶）", (-0.80, -0.63, 0.80, 4.30), (-0.70, -0.69, 2.00, 2.01))],
}


def evenodd(segs):
    """closed section loops -> polygon with even-odd fill"""
    g = None
    for p in polygonize([LineString([(a, b), (c, d)]) for a, b, c, d in segs]):
        g = p if g is None else g.symmetric_difference(p)
    return g


def rings(g):
    for p in (g.geoms if isinstance(g, MultiPolygon) else [g]):
        if p.is_empty or p.geom_type != "Polygon": continue
        yield p.exterior.coords
        for r in p.interiors: yield r.coords


def to_d(g, fr):
    out = []
    for r in rings(g):
        pts = [fr.b2t(x, y) for x, y in list(r)[:-1]]
        out.append("M" + " L".join(f"{x:.0f} {y:.0f}" for x, y in pts) + " Z")
    return " ".join(out)


def from_d(d, fr):
    g = None
    for sub in re.split(r'(?=M)', d):
        nums = [float(v) for v in re.sub('[MLZ]', ' ', sub).split()]
        if len(nums) < 6: continue
        p = Polygon([fr.t2b(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]).buffer(0)
        g = p if g is None else g.symmetric_difference(p)
    return g


def patch(F):
    fr = Frame(F)
    src = os.path.join(TOOL, f"walls_{F}_ppt.svg"); dst = os.path.join(TOOL, f"walls_{F}.svg")
    if not os.path.exists(src): shutil.copy(dst, src)
    svg = open(src, encoding="utf-8").read()
    sec = json.load(open(os.path.join(HERE, "_v42_section.json"), encoding="utf-8"))[F]
    by = {}
    for n, a, b, c, d in sec: by.setdefault(n, []).append((a, b, c, d))
    v42 = {n: evenodd(s) for n, s in by.items()}
    wz = unary_union([box(x0, y0, x1, y1) for _, (x0, x1, y0, y1), _ in ZONES[F]])
    dz = unary_union([box(x0, y0, x1, y1) for _, _, (x0, x1, y0, y1) in ZONES[F]])

    def fix_group(m):
        cls, attrs, body = m.group(1), m.group(2), m.group(3)
        if cls not in ("wall", "door"): return m.group(0)
        out, cut, cut_name = [], [], None
        for name, d in re.findall(r'<path data-name="([^"]*)" d="([^"]+)"/>', body):
            g = from_d(d, fr)
            if g is None or g.is_empty: out.append(f'<path data-name="{name}" d="{d}"/>'); continue
            if cls == "wall" and g.intersects(wz):
                cut.append(g.difference(wz)); cut_name = cut_name or name     # merged with the v42 piece below (no seam)
            elif cls == "door" and g.intersects(dz):
                continue
            else:
                out.append(f'<path data-name="{name}" d="{d}"/>')
        if cls == "wall":
            new = unary_union([v.buffer(0) for n, v in v42.items() if v is not None and WALLISH.search(n)]).intersection(wz)
            g = unary_union(cut + [new]).buffer(0.0005, join_style=2).buffer(-0.0005, join_style=2)
            out.append(f'<path data-name="{cut_name or "墙_v42"}" d="{to_d(g, fr)}"/>')
        for zn, (x0, x1, y0, y1), (u0, u1, w0, w1) in ZONES[F]:
            if cls == "door":
                for n, v in v42.items():
                    if v is not None and DOORISH.search(n) and v.centroid.within(box(u0, w0, u1, w1)):
                        out.append(f'<path data-name="墙_v42_{n}" d="{to_d(v, fr)}"/>')
        return f'<g class="{cls}"{attrs}>\n' + "\n".join(out) + "\n</g>"

    svg = re.sub(r'<g class="(\w+)"([^>]*)>(.*?)</g>', fix_group, svg, flags=re.S)
    open(dst, "w", encoding="utf-8").write(svg)
    print(F, "patched ->", dst)


if __name__ == "__main__":
    for F in ZONES: patch(F)
