# -*- coding: utf-8 -*-
"""27PR 照明布线施工图 (lighting wiring, for the electrician) — generated from the lighting tool data (lighting_<F>.json, Rev I).

UK loop-in with ceiling junction boxes: AL1 -> JB -> JB ... per final circuit (WL, 1.5 mm² 6242Y 2C+E, B6 RCBO 30 mA);
each switched group (circuit letter) has one JB: lamps from the JB (2C+E switched line), switch drop from the JB (2C+E one-way /
first two-way switch), 3C+E strappers between two-way switches and through intermediates. Routes are orthogonal ceiling runs
(through joists / over the plasterboard), drops run vertically in the safe zone above each switch.
Plan B (精简 17 路, chosen 2026-10-08): the GF indoor lighting groups (plan A WL1 + WL2) are one circuit WL1 (B10); same cables.
"""
import html, math
from plan_base import Sheet as _Sheet, BASE_CSS, MM, load_tool, Frame, table


def Sheet(*a, **k):
    k.setdefault("rev", "C"); k.setdefault("date", "2026-10-08")
    return _Sheet(*a, **k)

# positions agreed with the user after Rev I (to be written back to the tool / model): Blender metres
OVERRIDE = {}   # Rev J (2026-10-07) wrote the agreed S7 / S3 positions back into the lighting tool
WLCOL = {"WL1": "#c0392b", "WL2": "#d35400", "WL3": "#16a085", "WL4": "#2c3e8f"}
CSS = BASE_CSS + """
.lamp{fill:#fff;stroke:#222;stroke-width:.25}.jb{fill:#fff;stroke:#111;stroke-width:.3}.sw{fill:#111}.lbl{fill:#222}
.cu{fill:#222}.lblb{fill:#fff;opacity:.85}
"""


def floor_data(F):
    J = load_tool(F); fr = Frame(F)
    # plan B (2026-10-08): circuits regrouped per power_plans.json (GF WL1 + WL2 -> WL1)
    import json, os
    from plan_base import TOOL
    PB = json.load(open(os.path.join(TOOL, "power_plans.json"), encoding="utf-8"))["B"]
    for w in PB["lighting"]:
        if w["floor"] != F: continue
        for c in J["circuits"]:
            if c["id"] in w["circ"]: c["wl"] = w["id"]
    lights = {l["id"]: dict(l, b=fr.t2b(l["x"], l["y"])) for l in J["lights"]}
    plates = {}
    for p in J["plates"]:
        b = OVERRIDE.get((F, p["id"])) or fr.t2b(p["x"], p["y"])
        plates[p["id"]] = dict(p, b=b)
    board = fr.t2b(J["board"]["x"], J["board"]["y"])
    return J, lights, plates, board


FOOT = {}    # floor -> house footprint (shapely), set in design(): routes must stay inside the house


def footprint(F):
    """house outline from the wall drawing: walls + windows + doors, gaps closed by 0.6 m, outer ring filled"""
    from shapely.geometry import Polygon, LineString
    from shapely.ops import unary_union
    from plan_base import walls
    w, _ = walls(F)
    parts = []
    for k in ("wall", "window", "door"):
        for _, pts, closed in w.get(k, []):
            if len(pts) >= 3 and closed: parts.append(Polygon(pts).buffer(0))
            elif len(pts) >= 2: parts.append(LineString(pts).buffer(0.02))
    g = unary_union(parts).buffer(0.6)
    big = max(getattr(g, "geoms", [g]), key=lambda p: p.area)
    return Polygon(big.exterior).buffer(-0.6 + 0.05)


def ortho(a, b):
    """L-shaped ceiling route: along the house (Blender y) first, then across — unless that leaves the house
    (2026-10-08 user: the FF WL4 feed hung outside between 北卫 and 卧室 4), then across first."""
    r1, r2 = [a, (a[0], b[1]), b], [a, (b[0], a[1]), b]
    fp = FOOT.get("cur")
    if fp is None: return r1
    from shapely.geometry import LineString
    out = lambda r: LineString(r).difference(fp).length
    return r1 if out(r1) <= out(r2) + 1e-6 else r2


def mlen(pts):
    return sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))


def design(F):
    J, lights, plates, board = floor_data(F)
    FOOT["cur"] = footprint(F)
    circ = J["circuits"]
    keyplates = {}     # key -> [(plate, middle?)]
    for p in plates.values():
        for k in p["keys"]:
            keyplates.setdefault(k, []).append((p["id"], k in p.get("middle_keys", [])))
    out = dict(F=F, board=board, lights=lights, plates=plates, jbs={}, feeds=[], lamp_runs=[], drops=[], straps=[], schedule=[], remote=[])
    for c in circ:
        ls = [lights[x]["b"] for x in c["lights"] if x in lights]
        if not ls: continue
        ways = [(pid, mid) for k in c["keys"] for pid, mid in keyplates.get(k, [])]
        sw = [plates[pid]["b"] for pid, _ in ways]
        # JB: next to the lamp closest to the switches (or to the lamps' centre)
        tgt = (sum(p[0] for p in sw) / len(sw), sum(p[1] for p in sw) / len(sw)) if sw else ls[0]
        near = min(ls, key=lambda p: math.dist(p, tgt))
        jb = (near[0] + 0.25 * (1 if tgt[0] > near[0] else -1), near[1] + 0.25 * (1 if tgt[1] > near[1] else -1))
        out["jbs"][c["id"]] = dict(pos=jb, letter=c["letter"], wl=c["wl"], name=c["name"])
        # lamps chained from the JB (nearest neighbour)
        rest, cur, runs = list(ls), jb, []
        while rest:
            n = min(rest, key=lambda p: math.dist(p, cur)); rest.remove(n)
            runs.append(ortho(cur, n)); cur = n
        out["lamp_runs"] += [(c["wl"], r) for r in runs]
        # switch wiring: 1 way -> 2C+E drop; 2 ways -> 2C+E drop + 3C+E strapper; 3+ -> intermediates in the middle
        ends = [w for w in ways if not w[1]]; mids = [w for w in ways if w[1]]
        chain = ends[:1] + mids + ends[1:]
        kinds = []
        if chain:
            first = plates[chain[0][0]]["b"]
            out["drops"].append((c["wl"], ortho(jb, first), "2C+E" if len(chain) == 1 else "2C+E (COM)"))
            for a, b in zip(chain, chain[1:]):
                out["straps"].append((c["wl"], ortho(plates[a[0]]["b"], plates[b[0]]["b"])))
            kinds = ["单控 1-way"] if len(chain) == 1 else ["双控 2-way"] if len(chain) == 2 else [f"{len(chain)} 控（{len(mids)} 中途）"]
        if c.get("remote_links"):
            kinds.append("+ 一层 S6 跨层（3C+E 联络线经楼梯井）")
        if F == "GF" and any(k == "30" for k in c["keys"]):
            pass
        lamp_len = sum(mlen(r) for r in runs); sw_len = sum(mlen(ortho(jb, plates[chain[0][0]]["b"])) for _ in chain[:1]) + sum(mlen(ortho(plates[a[0]]["b"], plates[b[0]]["b"])) for a, b in zip(chain, chain[1:]))
        out["schedule"].append([c["wl"], c["letter"], c["name"], len(ls), " ".join(pid + ("(中途)" if m else "") for pid, m in chain) or "—",
                                kinds[0] if kinds else "—", f"{lamp_len + 1:.0f}", f"{sw_len + 2.4 * max(1, len(chain)) :.0f}"])
    # special key 30 on GF S6 -> FF stair pendant (drawn as a riser strapper on the GF)
    if F == "GF":
        for k, v in J.get("special_keys", {}).items():
            for pid, _ in keyplates.get(k, []):
                out["remote"].append((plates[pid]["b"], v.get("riser", "↑ 至二层")))
    # feed loop per WL: board -> nearest JB -> ...
    by = {}
    for cid, j in out["jbs"].items(): by.setdefault(j["wl"], []).append(j["pos"])
    for wl, pts in by.items():
        cur, rest = board, list(pts)
        while rest:
            n = min(rest, key=lambda p: math.dist(p, cur)); rest.remove(n)
            out["feeds"].append((wl, ortho(cur, n))); cur = n
    if F == "GF":   # 2026-10-07 user: the laundry wall light (u) is fed from the garden-door JB (p) along the rear wall, not round the fence
        pos = {j["letter"]: j["pos"] for j in out["jbs"].values()}
        if "p" in pos and "u" in pos:
            p, u = pos["p"], pos["u"]
            out["feeds"] = [(wl, pts) for wl, pts in out["feeds"] if not (wl == "WL3" and math.dist(pts[-1], u) < 1e-6)]
            out["feeds"].append(("WL3", [p, (0.90, p[1]), (0.90, 16.55), (u[0], 16.55), u]))
    out["wl"] = J["wl"]
    return out


def draw_plan(F, number):
    D = design(F)
    fl = "一层 GF" if F == "GF" else "二层 FF"
    s = Sheet(f"{fl} 照明布线平面图 Lighting wiring layout", number, F, ((-4.6, 4.6), (-1.0, 17.2)) if F == "GF" else ((-4.6, 4.6), (-0.6, 12.2)),
              discipline="电气 Electrical (lighting)")
    s.base_plan(F)
    A = s.add

    def path(pts, col, w, dash=""):
        A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in (s.P(*p) for p in pts)) + f'" fill="none" stroke="{col}" stroke-width="{w}" stroke-dasharray="{dash}" stroke-linejoin="round"/>')

    def tag(pts, txt, col):
        a, b = max(zip(pts, pts[1:]), key=lambda e: abs(e[0][0] - e[1][0]) + abs(e[0][1] - e[1][1]))
        if math.dist(a, b) < 0.6: return
        mx, my = s.P((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        A(f'<text x="{mx:.2f}" y="{my-0.8:.2f}" font-size="1.6" fill="{col}" text-anchor="middle">{txt}</text>')

    for wl, pts in D["feeds"]:
        path(pts, WLCOL.get(wl, "#555"), 0.75); tag(pts, f"{wl} 1.5 2C+E", WLCOL.get(wl, "#555"))
    for wl, pts in D["lamp_runs"]:
        path(pts, WLCOL.get(wl, "#555"), 0.35)
    for wl, pts, t in D["drops"]:
        path(pts, "#111", 0.35, "1.6 0.8"); tag(pts, t, "#111")
    for wl, pts in D["straps"]:
        path(pts, "#7a2fb5", 0.45, "3 1"); tag(pts, "3C+E", "#7a2fb5")
    for (x, y), t in D["remote"]:
        px, py = s.P(x, y)
        A(f'<path d="M{px:.2f} {py:.2f} l6 -6" stroke="#7a2fb5" stroke-width=".45" stroke-dasharray="3 1"/><text x="{px+7:.2f}" y="{py-6.5:.2f}" font-size="1.9" fill="#7a2fb5">3C+E {html.escape(t)}（楼梯吊灯 F06 跨层三控）</text>')
    # lamps
    for lid, l in D["lights"].items():
        px, py = s.P(*l["b"]); k = l["kind"]
        if k == "筒灯": A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.1" class="lamp"/><circle cx="{px:.2f}" cy="{py:.2f}" r=".35" fill="#222"/>')
        elif k == "壁灯": A(f'<path d="M{px-1.4:.2f} {py+1:.2f} L{px+1.4:.2f} {py+1:.2f} L{px:.2f} {py-1.4:.2f} Z" class="lamp"/>')
        elif k == "地灯": A(f'<rect x="{px-0.9:.2f}" y="{py-0.9:.2f}" width="1.8" height="1.8" class="lamp" transform="rotate(45 {px:.2f} {py:.2f})"/>')
        else:
            dash = ' stroke-dasharray="0.8 0.5"' if k == "待选" else ""
            A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.8" class="lamp"{dash}/><path d="M{px-1.27:.2f} {py-1.27:.2f} L{px+1.27:.2f} {py+1.27:.2f} M{px+1.27:.2f} {py-1.27:.2f} L{px-1.27:.2f} {py+1.27:.2f}" stroke="#222" stroke-width=".25"/>')
    # JBs
    for cid, j in D["jbs"].items():
        px, py = s.P(*j["pos"])
        A(f'<rect x="{px-1.3:.2f}" y="{py-1.3:.2f}" width="2.6" height="2.6" class="jb"/><text x="{px:.2f}" y="{py+0.7:.2f}" font-size="1.8" text-anchor="middle" font-weight="bold" fill="{WLCOL.get(j["wl"], "#111")}">{j["letter"]}</text>')
    # switches
    placed = []
    for pid, p in D["plates"].items():
        px, py = s.P(*p["b"])
        left = any(math.dist(p["b"], q) < 0.6 for q in placed); placed.append(p["b"])   # neighbour plate: label on the other side
        lx, an = (px - 1.6, "end") if left else (px + 1.6, "start")
        A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.0" class="sw"/><text x="{lx:.2f}" y="{py-1.2:.2f}" font-size="2" font-weight="bold" class="lbl" text-anchor="{an}">{pid}</text>'
          f'<text x="{lx:.2f}" y="{py+1.6:.2f}" font-size="1.6" class="lbl" text-anchor="{an}">{p["gangs"]}G · {"/".join(p["keys"])}</text>')
    # board / riser
    bx, by = s.P(*D["board"])
    A(f'<rect x="{bx-2.6:.2f}" y="{by-1.6:.2f}" width="5.2" height="3.2" class="cu"/><text x="{bx:.2f}" y="{by+5:.2f}" font-size="2.1" text-anchor="middle" font-weight="bold">'
      + ("AL1 配电箱 CU（楼梯下）" if F == "GF" else "↑ WL4 自一层 AL1 沿楼梯井引上") + '</text>')
    # legend + schedules
    L = [("#c0392b", 0.75, "", "WL1 一层室内照明 feed 1.5 mm² 2C+E（B10 RCBO 30 mA，方案 B）"),
         ("#16a085", 0.75, "", "WL3 户外 feed（户外段 SWA / 套管）"), ("#2c3e8f", 0.75, "", "WL4 二层 feed"),
         ("#555", 0.35, "", "JB → 灯 2C+E 1.5（开关线 L 套棕色套管）"), ("#111", 0.35, "1.6 0.8", "JB → 开关 下线 2C+E 1.5（竖直下到开关）"),
         ("#7a2fb5", 0.45, "3 1", "双控 / 中途联络线 3C+E 1.5（L1 / L2）")]
    x0, y0 = 168, 219
    A(f'<rect x="{x0-3}" y="{y0-5}" width="128" height="{8+4.6*(len(L)+4)}" fill="#fff" stroke="#999" stroke-width=".2"/><text x="{x0}" y="{y0}" font-size="2.6" font-weight="bold">图例 Legend</text>')
    for i, (c, w, d, t) in enumerate(L):
        yy = y0 + 4.6 * (i + 1)
        A(f'<line x1="{x0}" y1="{yy}" x2="{x0+12}" y2="{yy}" stroke="{c}" stroke-width="{w}" stroke-dasharray="{d}"/><text x="{x0+15}" y="{yy+0.8}" font-size="2">{html.escape(t)}</text>')
    yy = y0 + 4.6 * (len(L) + 1)
    A(f'<rect x="{x0+4.7}" y="{yy-1.3}" width="2.6" height="2.6" class="jb"/><text x="{x0+15}" y="{yy+0.8}" font-size="2">吊顶接线盒 JB（字母 = 回路，维护可达 / 维护式接头）</text>')
    A(f'<circle cx="{x0+6}" cy="{yy+4.6}" r="1" class="sw"/><text x="{x0+15}" y="{yy+5.4}" font-size="2">开关 S#（nG · 按键号），中心离地 1.2 m，离门框 150 mm</text>')
    A(f'<circle cx="{x0+6}" cy="{yy+9.2}" r="1.6" class="lamp"/><text x="{x0+15}" y="{yy+10}" font-size="2">⊗ 主灯 · ⊙ GU10 筒灯（LED ≤ 7 W）· △ 壁灯 · ◇ 地灯</text>')
    rows = [[r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]] for r in D["schedule"]]
    table(s, 14, 214, [("WL", 8), ("回路", 7), ("名称", 56), ("灯", 5), ("开关", 24), ("控制", 19), ("灯线 m", 10), ("开关线 m", 12)], rows, fs=1.55,
          title="回路与线缆表 Circuit & cable schedule（长度为平面估算，另加竖向与余量）")
    sw_rows = [[pid, p["gangs"], " / ".join(p["keys"]), p["location"], "中途" if p.get("middle_keys") else "—"] for pid, p in D["plates"].items()]
    table(s, 300, 38, [("开关", 10), ("联数", 9), ("按键", 22), ("位置", 44), ("中途键", 12)], sw_rows, fs=1.7, title="开关表 Switch schedule（NAB 古铜系列，1.2 m）")
    s.frame(NOTES_PLAN)
    return s


NOTES_PLAN = [
    "说明 Notes",
    "1. 依据 BS 7671:2018+A2、IET On-Site Guide；属 Part P 须由注册电工施工、测试并出具 EIC。",
    "2. 方案 B：照明 3 路——WL1 一层室内 B10、WL3 户外 B6、WL4 二层 B6（RCBO 30 mA）；线缆 1.5 mm² 6242Y（2C+E）/ 6243Y（3C+E）。",
    "3. 灯具接法：每个回路字母一个吊顶接线盒 JB，灯与开关下线都回到 JB；JB 用维护式接线端子（Wago 221 / 维护可达）。",
    "4. 双控：JB→第一个开关 2C+E（COM），开关之间 3C+E（L1/L2）；三处控制中间为中途开关；所有开关线（蓝 / 灰芯作火线用）套棕色套管。",
    "5. 线路走向：吊顶内沿最短正交路线，穿搁栅中线打孔（≥ 50 mm 距上下缘）；墙内只在开关正上方竖直走（安全区），埋深 < 50 mm 时须 RCD 保护（已满足）。",
    "6. 卫生间灯 IP44 以上、排气扇接卫生间灯回路（随灯开、延时关）；户外灯 IP65+，户外段用 SWA 或套管。",
    "7. 一层 S7 在法式门框东侧（Rev J）。二层 Rev C（照明 Rev K，2026-10-08）：S3 挪回主卧南墙（衣帽间那面墙）主卧一侧、C19 西侧；卧室 2 门旁 S7 装在门西侧短墙的卧室 2 一侧。",
]


def detail_sheet():
    """E-03: switch / JB wiring details (UK colours)."""
    s = Sheet("开关接线详图 Switch & JB wiring details（英标颜色，示意）", "E-03", "", ((0, 1), (0, 1)), scale_note="NTS", discipline="电气 Electrical (lighting)")
    A = s.add
    BR, BL, GY, BK, GN = "#8b4513", "#1f5fbf", "#888", "#222", "#3a9d23"

    def w(pts, col, wd=0.6, dash=""):
        A('<path d="M' + " L".join(f"{a} {b}" for a, b in pts) + f'" fill="none" stroke="{col}" stroke-width="{wd}" stroke-dasharray="{dash}"/>')

    def box(x, y, wd, h, t, fs=2.2):
        A(f'<rect x="{x}" y="{y}" width="{wd}" height="{h}" fill="#fff" stroke="#222" stroke-width=".3" rx="1"/><text x="{x+wd/2}" y="{y-1.4}" font-size="{fs}" text-anchor="middle" font-weight="bold">{html.escape(t)}</text>')

    def term(x, y, t):
        A(f'<circle cx="{x}" cy="{y}" r="0.9" fill="#fff" stroke="#222" stroke-width=".25"/><text x="{x+1.4}" y="{y+0.7}" font-size="1.8">{t}</text>')

    def lamp(x, y):
        A(f'<circle cx="{x}" cy="{y}" r="3" fill="#fff" stroke="#222" stroke-width=".3"/><path d="M{x-2.1} {y-2.1} L{x+2.1} {y+2.1} M{x+2.1} {y-2.1} L{x-2.1} {y+2.1}" stroke="#222" stroke-width=".3"/>')
    # ① one-way via JB
    A('<text x="16" y="30" font-size="3.2" font-weight="bold">① 单控（JB 法）One-way via junction box</text>')
    box(30, 40, 48, 26, "吊顶接线盒 JB")
    for i, t in enumerate(["L 进", "L 出", "N", "SL", "E"]): term(36 + i * 9, 52, t)
    w([(16, 48), (36, 48), (36, 51)], BR); w([(16, 46), (54, 46), (54, 51)], BL); A('<text x="16" y="44" font-size="1.9">2C+E 来自上一个 JB / AL1</text>')
    w([(45, 53), (45, 62), (90, 62)], BR); w([(54, 53), (54, 60), (92, 60)], BL)
    A('<text x="60" y="58" font-size="1.9">2C+E → 下一个 JB</text>')
    w([(63, 53), (63, 80), (66, 80)], BR); A('<text x="66" y="78" font-size="1.9">SL → 灯 L</text>'); lamp(100, 82)
    w([(54, 53), (54, 84), (97, 84)], BL); A('<text x="70" y="88" font-size="1.9">N → 灯 N（灯与灯之间 2C+E 串接）</text>')
    box(30, 100, 24, 16, "单控开关 1-way"); term(36, 110, "COM"); term(48, 110, "L1")
    w([(36, 53), (36, 100)], BR, 0.6); w([(39, 53), (39, 96), (48, 96), (48, 109)], BL, 0.6, "")
    A('<rect x="38" y="70" width="2" height="6" fill="#8b4513"/><text x="42" y="74" font-size="1.8">蓝芯作开关回线：套棕色套管</text>')
    A('<text x="16" y="124" font-size="2">JB→开关：2C+E（棕 = 常火 L，蓝 = 开关回线 SL，须套棕色套管），地线接开关盒接地端子。</text>')
    # ② two-way
    A('<text x="16" y="140" font-size="3.2" font-weight="bold">② 双控 Two-way（3C+E 联络线）</text>')
    box(30, 150, 30, 16, "双控开关 A"); term(36, 160, "COM"); term(46, 156, "L1"); term(46, 164, "L2")
    box(110, 150, 30, 16, "双控开关 B"); term(130, 160, "COM"); term(120, 156, "L1"); term(120, 164, "L2")
    w([(36, 161), (36, 180), (20, 180)], BR); A('<text x="16" y="185" font-size="1.9">2C+E 自 JB：棕 L → A COM</text>')
    w([(130, 161), (130, 180), (150, 180)], BL); A('<text x="134" y="185" font-size="1.9">B COM → SL 回 JB（另一 2C+E 或 3C+E 第三芯）</text>')
    w([(47, 156), (119, 156)], BR); w([(47, 164), (119, 164)], BK)
    A('<text x="62" y="153" font-size="1.9">3C+E：棕 L1–L1，黑 L2–L2（黑、灰芯套棕色套管）</text>')
    # ③ intermediate
    A('<text x="16" y="200" font-size="3.2" font-weight="bold">③ 三处控制 Intermediate（一层 S7 / 二层 S11 键 2）</text>')
    box(30, 210, 26, 16, "双控 A"); box(80, 210, 30, 16, "中途开关 INT"); box(134, 210, 26, 16, "双控 B")
    for x0 in (56,):
        w([(56, 214), (80, 214)], BR); w([(56, 222), (80, 222)], BK)
    w([(110, 214), (134, 222)], BR); w([(110, 222), (134, 214)], BK, 0.6, "1 0.6")
    A('<text x="57" y="232" font-size="1.9">A L1 / L2 → INT 一侧；INT 另一侧 → B L1 / L2，均为 3C+E；INT 内部交叉换接</text>')
    # ④ cross-floor stair
    A('<text x="216" y="30" font-size="3.2" font-weight="bold">④ 楼梯吊灯 F06 跨层三控（一层 S6 + 二层 S11 键 2 中途 + 二层 S12）</text>')
    box(220, 46, 26, 16, "一层 S6 双控"); box(268, 46, 30, 16, "二层 S11 键 2 INT"); box(322, 46, 26, 16, "二层 S12 双控")
    w([(246, 50), (268, 50)], BR); w([(246, 58), (268, 58)], BK); w([(298, 50), (322, 50)], BR); w([(298, 58), (322, 58)], BK)
    A('<text x="222" y="72" font-size="1.9">一层 S6 → 二层：3C+E 沿楼梯井竖向敷设（带套管），回路 L11 由二层 WL4 供电；S6 盒内不得引入一层回路的火线。</text>')
    # ⑤ fan / bathroom
    A('<text x="216" y="92" font-size="3.2" font-weight="bold">⑤ 卫生间灯 + 排气扇（延时型，无隔离开关 · Rev C）</text>')
    box(220, 104, 40, 18, "卫生间 JB"); box(290, 104, 34, 18, "排气扇（带延时 T）")
    for i, t in enumerate(["L", "SL", "N", "E"]): term(226 + i * 9, 114, t)
    w([(235, 115), (235, 130), (300, 130), (300, 123)], BR); A('<text x="262" y="134" font-size="1.9">SL → 风扇 S 端（开灯即开）</text>')
    w([(226, 115), (226, 136), (310, 136), (310, 123)], BR, 0.6, "1.4 0.7"); A('<text x="262" y="140" font-size="1.9">常火 L → 风扇 L 端（延时运转）</text>')
    w([(244, 115), (244, 142), (318, 142), (318, 123)], BL); A('<text x="262" y="146" font-size="1.9">N → 风扇 N（3C+E 至风扇）</text>')
    # ⑥ outdoor floodlight
    A('<text x="216" y="164" font-size="3.2" font-weight="bold">⑥ 户外：后花园投光灯 / 壁灯 / 地灯（WL3）</text>')
    for i, t in enumerate(["WL3 B6 RCBO 30 mA；户外灯具 IP65+（投光灯 SOLLA 150 W IP66，离地 3.5 m）",
                           "穿外墙处用防水接线盒（IP66）+ 套管；户外埋地段（围栏地灯）用 SWA 1.5 mm² 3C，埋深 ≥ 450 mm 并加警示带",
                           "投光灯 v（键 28）、壁灯 p（键 26）、地灯 q（键 27）均由 S11 / S12 两路 + S7 中途三控，接法同 ③",
                           "投光灯光束向下 ≥ 25°，避免照向邻居窗户（Dark Sky / 邻里投诉）"]):
        A(f'<text x="220" y="{174 + i * 6}" font-size="2.1">{html.escape(t)}</text>')
    A('<text x="216" y="214" font-size="3.2" font-weight="bold">⑦ 颜色与测试 Colours & testing</text>')
    for i, t in enumerate(["棕 Brown = L · 蓝 Blue = N · 绿黄 Green/Yellow = E · 3C+E 的灰 / 黑芯作开关线，两端套棕色套管",
                           "完工测试：连续性（R1+R2）、绝缘电阻、极性、Zs、RCBO 动作时间；出具 EIC + Part P 通知"]):
        A(f'<text x="220" y="{224 + i * 6}" font-size="2.1">{html.escape(t)}</text>')
    s.frame()
    return s


def sheets():
    return [draw_plan("GF", "E-01"), draw_plan("FF", "E-02"), detail_sheet()]
