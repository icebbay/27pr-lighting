"""Sync lighting_tool/walls_<F>.svg with model v46 (owner plan keyplan3d, 2026-10-11), on top of the v42 door zones.

Same method as patch_walls_v42.py, but every zone now takes its walls / doors from the v46 horizontal section
(_v46_section.json, GF z = 1.0, FF z = 4.3 above the window sills, exported from the live v46 on 2026-10-13):
  v42 zones   north-bath door, bedroom 2 (now 主卧) door, GF stair -> kitchen 762 door, GF sofa wall
  v46 zones   主卧 door 860; FF front inner face 0.150 (主卧 / 主卫), 主卧 front-left nib removed (次卧 front 0.765 left as PPT: 54 mm,
              and its windows would come out as bare gaps);
              主卫 一门两用 partition 1.150-1.250 + 衣帽间 partition 2.429-2.549; 主客厅 sofa wall face -0.600;
              kitchen / laundry opening 2.12 (new 300 pier V47_Kitchen_Pier_300_L); laundry corner fill.
  v47 zones   (2026-10-14, model v47 = owner keyplan screenshot, section now _v47_section.json): 300 pier removed again
              (opening 2.42); laundry rear door moved to x 2.650-3.530 (old door walled up, rear window gone); laundry -> kitchen
              door replaced by a plain opening 2.070-2.830; breakfast French door moved 91 (frame 8.764-10.405, 600 from the wall).
Always patches from walls_<F>_ppt.svg (the PPT original), so it is idempotent and replaces patch_walls_v42.py.

    python products/trade_drawings/patch_walls_v46.py      (then lighting_tool/build_data_js.py for the web tool)
"""
import json, os, re, shutil
from shapely.geometry import box
from shapely.ops import unary_union, polygonize
from plan_base import Frame, TOOL
from patch_walls_v42 import WALLISH, DOORISH, evenodd, to_d, from_d

HERE = os.path.dirname(os.path.abspath(__file__))
WALLISH = re.compile(WALLISH.pattern + r"|Pier|CornerFill|PreWall")
NONE = (0, 0, 0, 0)
# named door paths redrawn as a box (x0, x1, y0, y1): 后书房 bath door hinge at the alcove end (y 9.264, owner plan / 后书房 Rev F),
# open leaf 690 into the study — model v47 flipped to match (owner 2026-10-15: "方向开错了，朝外开")
DOOR_BOX = {"FF": {"墙_V39_DoorLeaf_Bath": (2.590, 3.280, 9.264, 9.304)}}
# floor: [(name, wall zone (x0, x1, y0, y1), door zone)] in Blender metres
ZONES = {
    "FF": [("北卫门", (-2.95, -2.45, 6.45, 7.70), (-3.60, -2.45, 6.45, 7.70)),
           ("主卧门 860", (1.45, 2.75, 4.20, 4.75), (1.45, 2.75, 3.55, 4.75)),
           ("二楼前墙内面 0.150（主卧 / 主卫），主卧方正", (-0.70, 4.40, -0.10, 0.90), NONE),
           ("主卫一门两用隔墙 + 衣帽间隔墙", (-0.70, 1.30, 0.90, 3.40), NONE)],
    "GF": [("厨房门", (2.30, 3.50, 7.85, 8.30), (2.30, 3.50, 7.85, 9.00)),
           ("主客厅沙发墙（墙面 -0.600）", (-0.80, -0.58, 0.80, 4.30), NONE),
           ("厨房 / 洗衣房洞口 300 墙垛", (1.20, 1.65, 11.80, 12.15), NONE),
           ("洗衣房角补墙", (4.25, 4.45, 15.85, 16.10), NONE),
           ("v47 洗衣房后门挪位 + 补墙", (1.03, 4.42, 15.98, 16.30), (1.15, 4.42, 15.90, 16.30)),
           ("v47 洗衣房 / 厨房无门洞口", (1.20, 4.30, 14.65, 14.90), (1.15, 2.95, 14.60, 15.70)),
           ("v47 早餐区法式门挪 91", (1.00, 1.30, 8.55, 10.50), (0.30, 1.30, 8.55, 10.50))],
}


def closed(segs, tol=0.25):
    """The wall shell is cut open at door openings, so its section has dangling ends; join them pairwise
    (nearest first) before the even-odd fill, otherwise the whole floor fills solid."""
    from collections import Counter
    c = Counter()
    for a, b, cc, d in segs: c[(round(a, 4), round(b, 4))] += 1; c[(round(cc, 4), round(d, 4))] += 1
    odd = [k for k, v in c.items() if v % 2]
    pairs = sorted(((((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** 0.5, i, j) for i, p in enumerate(odd)
                    for j, q in enumerate(odd) if i < j), key=lambda t: t[0])
    used, extra = set(), []
    for dist, i, j in pairs:
        if dist > tol or i in used or j in used: continue
        used |= {i, j}; extra.append((*odd[i], *odd[j]))
    return parity_fill(list(segs) + extra)


def parity_fill(segs):
    """Even-odd fill of a planar line graph: keep the faces whose inside point sees an odd number of edges on a ray."""
    from shapely.geometry import LineString
    S = [((round(a, 4), round(b, 4)), (round(c, 4), round(d, 4))) for a, b, c, d in segs]
    faces = polygonize(unary_union([LineString(s) for s in S]))
    keep = []
    for f in faces:
        px, py = f.representative_point().coords[0]
        n = 0
        for (x1, y1), (x2, y2) in S:
            if (y1 > py) != (y2 > py) and px < x1 + (py - y1) * (x2 - x1) / (y2 - y1): n += 1
        if n % 2: keep.append(f)
    return unary_union(keep) if keep else None


def patch(F):
    fr = Frame(F)
    src = os.path.join(TOOL, f"walls_{F}_ppt.svg"); dst = os.path.join(TOOL, f"walls_{F}.svg")
    svg = open(src, encoding="utf-8").read()
    sec = json.load(open(os.path.join(HERE, "_v47_section.json"), encoding="utf-8"))[F]
    by = {}
    for n, a, b, c, d in sec: by.setdefault(n, []).append((a, b, c, d))
    v46 = {n: closed(s) for n, s in by.items()}
    wz = unary_union([box(x0, y0, x1, y1) for _, (x0, x1, y0, y1), _ in ZONES[F]])
    dz = unary_union([box(x0, y0, x1, y1) for _, _, (x0, x1, y0, y1) in ZONES[F] if x1 > x0])

    def fix_group(m):
        cls, attrs, body = m.group(1), m.group(2), m.group(3)
        if cls not in ("wall", "door"): return m.group(0)
        out, cut, cut_name = [], [], None
        for name, d in re.findall(r'<path data-name="([^"]*)" d="([^"]+)"/>', body):
            g = from_d(d, fr)
            if g is None or g.is_empty: out.append(f'<path data-name="{name}" d="{d}"/>'); continue
            if cls == "wall" and g.intersects(wz):
                cut.append(g.difference(wz)); cut_name = cut_name or name
            elif cls == "door" and not dz.is_empty and g.intersects(dz):
                continue
            else:
                out.append(f'<path data-name="{name}" d="{d}"/>')
        if cls == "wall":
            new = unary_union([v.buffer(0) for n, v in v46.items() if v is not None and WALLISH.search(n)]).intersection(wz)
            g = unary_union(cut + [new]).buffer(0.0005, join_style=2).buffer(-0.0005, join_style=2)
            out.append(f'<path data-name="{cut_name or "墙_v46"}" d="{to_d(g, fr)}"/>')
        else:
            for zn, _, (u0, u1, w0, w1) in ZONES[F]:
                if u1 <= u0: continue
                for n, v in v46.items():
                    if v is not None and DOORISH.search(n) and v.centroid.within(box(u0, w0, u1, w1)):
                        out.append(f'<path data-name="墙_v46_{n}" d="{to_d(v, fr)}"/>')
        return f'<g class="{cls}"{attrs}>\n' + "\n".join(out) + "\n</g>"

    svg = re.sub(r'<g class="(\w+)"([^>]*)>(.*?)</g>', fix_group, svg, flags=re.S)
    for nm, (x0, x1, y0, y1) in DOOR_BOX.get(F, {}).items():
        svg = re.sub(rf'<path data-name="{re.escape(nm)}" d="[^"]+"/>', f'<path data-name="{nm}" d="{to_d(box(x0, y0, x1, y1), fr)}"/>', svg)
    open(dst, "w", encoding="utf-8").write(svg)
    print(F, "patched ->", dst)


if __name__ == "__main__":
    for F in ZONES:
        patch(F)
