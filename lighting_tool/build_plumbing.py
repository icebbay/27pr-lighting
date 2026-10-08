# -*- coding: utf-8 -*-
"""Export the 给排水 design (trade_drawings/plumbing.py, Blender metres) to plumbing_data.js for plumbing.html.

Points are converted to the tool frame (slide EMU of walls_<F>.svg) with plan_base.Frame(F).b2t, so the pipes sit on the same
wall drawing as the lighting / power pages.  Pipe numbers are the same as the circled numbers of the PDF sheets
(P-01 / P-02 supply, P-03 / P-04 drainage, P-07 garden).

    python products/lighting_tool/build_plumbing.py
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
TD = os.path.join(os.path.dirname(HERE), "trade_drawings")
sys.path.insert(0, TD)
os.environ["WB_VARIANT"] = "B"
import plumbing as P
from plan_base import Frame

SUPPLY = ["mdpe", "hard", "yard", "soft", "hot", "pure"]
DRAIN = ["soil", "waste", "ug", "sw"]
SHEET = {("GF", "supply"): "P-01", ("FF", "supply"): "P-02", ("GF", "drain"): "P-03", ("FF", "drain"): "P-04"}


def r(v): return round(v)


def main():
    out = dict(rev="给排水施工图 Rev C · 2026-10-08（西卫按方案 B：走北墙）",
               style={k: dict(color=c, w=w, dash=d, label=t, short=P.SHORT[k], sys="supply" if k in SUPPLY else "drain")
                      for k, (c, w, d, t) in P.STYLE.items()},
               floors={})
    for F in ("GF", "FF"):
        fr = Frame(F)
        T = lambda x, y: [r(v) for v in fr.b2t(x, y)]
        units = json.load(open(os.path.join(HERE, f"lighting_{F}.json"), encoding="utf-8"))["units"]
        pipes = []
        for which, kinds in (("supply", SUPPLY), ("drain", DRAIN)):
            n = 0
            for fl, kind, size, pts, label in P.PIPES:
                if fl != F or kind not in kinds: continue
                no = None
                if label: n += 1; no = n
                pipes.append(dict(sys=which, kind=kind, size=size, no=no, sheet=SHEET[(F, which)], label=label, pts=[T(*p) for p in pts]))
        if F == "GF":   # garden (P-07): only the runs not already on P-01 / P-03
            have = {(k, tuple(map(tuple, p))) for _, k, _, p, _ in P.PIPES}
            for i, (kind, size, pts, label) in enumerate(P.GARDEN_PIPES, 1):
                if (kind, tuple(map(tuple, pts))) in have: continue
                pipes.append(dict(sys="supply" if kind in SUPPLY else "drain", kind=kind, size=size, no=i, sheet="P-07", label=label, pts=[T(*p) for p in pts]))
        fixtures = [dict(code=P.CODE[k], name=v[3], sup=v[4], drain=(f"{v[5][0]} Ø{v[5][1]}" if v[5][1] else "车道排水"), p=T(v[1], v[2]))
                    for k, v in P.FIX.items() if v[0] == F]
        equip = [dict(id=e, name=t, p=T(x, y), w=w, d=d) for e, fl, x, y, w, d, t in P.EQUIP if fl == F]
        stacks = [dict(id=s, name=t, p=T(x, y)) for s, x, y, t in P.STACKS]
        marks = []   # polygons drawn on the plan (Blender rects -> tool)
        x0, x1, y0, y1 = P.S2_BOX
        marks.append(dict(kind="box", name="S2 箱封 200×200" + ("（二层高 1200，顶部 AAV + 检修门）" if F == "FF" else "（一层到天花，底部检修口）"),
                          pts=[T(x0, y0), T(x1, y0), T(x1, y1), T(x0, y1)]))
        pts_extra = []
        if F == "GF":
            pts_extra = [dict(id=c, name=t, p=T(x, y), kind="ic") for c, x, y, t in P.CHAMBERS] + \
                        [dict(id=g, name=t, p=T(x, y), kind="gully") for g, x, y, t in P.GULLIES] + \
                        [dict(id=g, name=t, p=T(x, y), kind="ic" if c == "ic" else "eq") for g, x, y, w, d, t, c in P.GARDEN_PTS]
            marks.append(dict(kind="pond", name="后花园水池", pts=[T(*p) for p in P.POND_IN]))
            xx, ya, yb = P.CHANNEL
            marks.append(dict(kind="channel", name="地沟 CH 100 宽", pts=[T(xx - 0.05, ya), T(xx + 0.05, ya), T(xx + 0.05, yb), T(xx - 0.05, yb)]))
        else:
            for nm, (a0, a1, b0, b1) in (("西卫淋浴段假墙到天花（尽量薄，能借原墙就借；两个壁龛）", P.WB_SHOWER_WALL), ("西卫马桶段假墙高 1100（顶面平台，110 横管起点 + AAV）", P.WB_WC_WALL)):
                marks.append(dict(kind="wall", name=nm, pts=[T(a0, b0), T(a1, b0), T(a1, b1), T(a0, b1)]))
            for a0, a1 in P.WB_NICHES:
                marks.append(dict(kind="niche", name="壁龛 300 宽 × 深 80，离地 850–1750", pts=[T(a0, P.NICHE_Y[0]), T(a1, P.NICHE_Y[0]), T(a1, P.NICHE_Y[1]), T(a0, P.NICHE_Y[1])]))
        # view box: walls + everything drawn, with a margin
        near = [q for q in pipes if q["kind"] != "sw"]; pe = [e for e in pts_extra if e["id"] != "SA"]   # soakaway far down the lawn: pan to it
        xs = [p[0] for q in near for p in q["pts"]] + [f["p"][0] for f in fixtures] + [e["p"][0] for e in pe]
        ys = [p[1] for q in near for p in q["pts"]] + [f["p"][1] for f in fixtures] + [e["p"][1] for e in pe]
        vb = units["view_box"]
        ax0, ay0 = min(xs + [vb[0]]), min(ys + [vb[1]]); ax1, ay1 = max(xs + [vb[0] + vb[2]]), max(ys + [vb[1] + vb[3]])
        mg = 0.4 * units["emu_per_m"]
        out["floors"][F] = dict(view_box=[ax0 - mg, ay0 - mg, ax1 - ax0 + 2 * mg, ay1 - ay0 + 2 * mg], emu_per_m=units["emu_per_m"],
                                pipes=pipes, fixtures=fixtures, equip=equip, stacks=stacks, points=pts_extra, marks=marks,
                                notes=dict(supply=P.floor_notes(P.NOTES_SUPPLY, F)[1:], drain=P.floor_notes(P.NOTES_DRAIN, F)[1:]))
    out["garden_notes"] = P.NOTES_GARDEN[1:]
    open(os.path.join(HERE, "plumbing_data.js"), "w", encoding="utf-8").write(
        "// generated by build_plumbing.py from trade_drawings/plumbing.py (Blender m -> tool EMU)\nwindow.PLUMBING = " + json.dumps(out, ensure_ascii=False) + ";\n")
    print("plumbing_data.js:", {F: len(v["pipes"]) for F, v in out["floors"].items()}, "pipes")


if __name__ == "__main__":
    main()
