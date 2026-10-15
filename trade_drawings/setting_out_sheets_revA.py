# -*- coding: utf-8 -*-
"""27PR 点位定位尺寸图 Rev A — A3 sheets from setting_out.py.

    python products/trade_drawings/setting_out_sheets.py      -> out/27PR_点位定位尺寸图_RevA.pdf (+ out/png/SO-*.png)
"""
import html, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import setting_out as so
from plan_base import Sheet, BASE_CSS, MM, table, wrap

E = html.escape
REV = dict(rev="A", date="2026-10-08")
COL = {"socket": "#1565c0", "power": "#6a1b9a", "switch": "#111111", "light": "#e65100", "water": "#00897b", "new": "#c62828"}
CAT = {"socket": "插座", "power": "专用 / FCU", "switch": "开关", "light": "灯", "water": "给排水点", "new": "新增"}
CSS = BASE_CSS + ".lbl{fill:#222}"
FLN = {"GF": "一层", "FF": "二层"}


def sym(x, y, cat, r=1.3):
    c = COL[cat]
    if cat == "socket": return f'<rect x="{x-r:.2f}" y="{y-r:.2f}" width="{2*r:.2f}" height="{2*r:.2f}" fill="#fff" stroke="{c}" stroke-width=".35"/><line x1="{x-r*.5:.2f}" y1="{y:.2f}" x2="{x+r*.5:.2f}" y2="{y:.2f}" stroke="{c}" stroke-width=".3"/>'
    if cat == "power": return f'<rect x="{x-r:.2f}" y="{y-r:.2f}" width="{2*r:.2f}" height="{2*r:.2f}" fill="{c}" fill-opacity=".15" stroke="{c}" stroke-width=".35"/>'
    if cat == "switch": return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r*.8:.2f}" fill="{c}"/>'
    if cat == "light": return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="#fff" stroke="{c}" stroke-width=".35"/><path d="M{x-r*.7:.2f} {y-r*.7:.2f} L{x+r*.7:.2f} {y+r*.7:.2f} M{x+r*.7:.2f} {y-r*.7:.2f} L{x-r*.7:.2f} {y+r*.7:.2f}" stroke="{c}" stroke-width=".3"/>'
    if cat == "water": return f'<path d="M{x:.2f} {y-r*1.1:.2f} L{x+r:.2f} {y+r*.8:.2f} L{x-r:.2f} {y+r*.8:.2f} Z" fill="#fff" stroke="{c}" stroke-width=".35"/>'
    return f'<path d="M{x:.2f} {y-r:.2f} L{x+r:.2f} {y:.2f} L{x:.2f} {y+r:.2f} L{x-r:.2f} {y:.2f} Z" fill="#fff" stroke="{c}" stroke-width=".4"/>'


def legend(s, x, y):
    s.add(f'<text x="{x}" y="{y}" font-size="2.4" font-weight="bold">图例</text>')
    for i, c in enumerate(CAT):
        yy = y + 4.2 + i * 3.8
        s.add(sym(x + 2, yy - 0.7, c) + f'<text x="{x+5}" y="{yy}" font-size="2" fill="{COL[c]}">{E(CAT[c])}</text>')


# ---------------- data ----------------
DATA = {F: so.locate(F) for F in ("GF", "FF")}


def groups(F):
    """wall runs that carry points -> elevation ids"""
    G = {}
    for r in DATA[F][1]:
        if r.get("wall") in (None, "—") or "L" not in r: continue
        k = (round(r["L"][0], 3), round(r["L"][1], 3), round(r["R"][0], 3), round(r["R"][1], 3))
        G.setdefault(k, []).append(r)
    out = []
    for i, (k, rows) in enumerate(sorted(G.items(), key=lambda kv: (kv[1][0]["room"], kv[1][0]["wall"])), 1):
        eid = f"{'1' if F == 'GF' else '2'}E{i:02d}"
        for r in rows: r["elev"] = eid
        out.append((eid, rows))
    return out


GROUPS = {F: groups(F) for F in ("GF", "FF")}


# ---------------- sheets ----------------
def cover():
    s = Sheet("点位定位尺寸图 说明 Setting-out notes", "SO-00", "", ((0, 1), (0, 1)), scale_note="—", discipline="电气定位 Setting out", **REV)
    A = s.add
    A('<text x="16" y="32" font-size="3.4" font-weight="bold">怎么读这套图</text>')
    how = ["• 每个点位有编号：C 插座、D 专用电器 / FCU / 隔离开关、S 开关、L 灯、N 新增。编号前的 1 / 2 表示一层 / 二层（表里另列楼层）。",
           "• 墙面名称按「站在房间里看这面墙」：北墙 / 南墙 / 西墙 / 东墙（前门朝西、后花园在东）。",
           "• 水平尺寸：从这面墙「左端」量到点位中心（面对墙看的左手边），同时给出到右端的距离，两个数加起来 = 这面墙的净长，可用来核对。",
           "   左 / 右端是什么也写出来了：墙角（阴角）/ 门洞边 / 窗洞边 / 墙端（阳角）。量的是完成墙面，抹灰 / 石膏板后的面。",
           "• 高度：从该房间完成地面量到底盒中心（灯为天花高度）。二层前部完成面 3.208、后部（卧室 4 / 后卫 / 书房二）2.852，各自从本房间地面起量。",
           "• 天花上的灯：给出到两个方向最近墙面（或门窗洞）的距离。",
           "• 立面图（SO-1x）：每面有点位的墙一张，平面图上的 1E05 / 2E12 等就是立面编号，箭头指向被看的那面墙。"]
    for i, t in enumerate(how): A(f'<text x="20" y="{40+i*5.2}" font-size="2.35">{E(t)}</text>')
    A('<text x="16" y="84" font-size="3.4" font-weight="bold">高度标准（底盒中心，离本房间完成地面）</text>')
    rows = [["开关（全部）", "1200", "原施工图 / 模型 v42；Part M 450–1200。叠放的开关（S5 在 S4 上方）中心再高 130"],
            ["一般插座", "300", "业主原定，与模型一致"],
            ["床头插座 / 床头开关", "630 / 650 / 700", "床头柜面（主卧 485、卧室 2 500，模型 v42）+ 约 150；主卧 S3 在床头柜上方 700"],
            ["厨房台面插座 / FCU", "1100", "台面 902（模型）上方，底边离台面约 150；FCU 同高、装在可触及处"],
            ["餐边柜 / 洗衣柜 / 书桌上方", "1110 / 1200 / 970", "柜面或桌面（907 / 1002 / 766）+ 200"],
            ["电视柜上方插座", "600", "原位置被电视柜（高 452）挡住，抬到柜面上方"],
            ["空调插座", "2190 / 2540", "在内机侧面，与机身中高齐平（内机底：卧室 3 2040、卧室 4 2390，模型 v42）"],
            ["户外插座", "600", "户外 IP66 带盖"],
            ["EV 充电桩 / 室内 40A 总控", "1000 / 1200", "按充电桩说明书；隔离开关 1200"],
            ["壁灯", "按模型", "楼梯壁灯 F32 1930；后花园壁灯 1770–1800；投光灯 3350（模型 v42 灯具中心）"]]
    table(s, 16, 90, [("项", 52), ("高度 mm", 26), ("依据", 300)], rows, fs=2.1)
    A('<text x="16" y="152" font-size="3.4" font-weight="bold">精度与误差（重要）</text>')
    tol = ["• 点位来源：照明 / 插座设计（网页工具 Rev J、PPT 标注）+ Blender 模型 v42 的墙体、门窗、家具。图上点位标在墙边，本稿已把每个点「推」到所属墙面，再从墙端量尺寸，取整到 10 mm。",
           "• 估计误差：插座 / 开关 / 灯水平位置 ±30 mm（原标注是示意位置）；表中「原点位离墙面 xxx」= 原图标记离墙较远，已按墙面定位，请重点确认这些点在哪一面墙。",
           "• 高度为设计值，按本图施工；家具、洁具定版后若尺寸变化，床头 / 台面 / 洁具相关点位跟着调整。墙体以现场完成面为准，与图差 > 50 mm 时先停工联系业主。",
           "• 「离墙角 / 洞口 < 100」的点：贴得太近，门框 / 踢脚线 / 墙角可能装不下底盒，现场定位时请移到 ≥ 150。",]
    for i, t in enumerate(tol):
        for j, l in enumerate(wrap(t, 120)): A(f'<text x="20" y="{160+i*7.2+j*3.4:.1f}" font-size="2.25">{E(l)}</text>')
    A('<text x="16" y="196" font-size="3.4" font-weight="bold">核对后的处理（业主 2026-10-08 定稿）</text>')
    issues = ["1. 高度：开关 1200、普通插座 300（与原施工图 / 模型一致）；床头插座 = 床头柜面 + 150，台面插座离台面约 150；S5 叠在 S4 正上方（1330）。",
              "2. 智能马桶 / 电热毛巾架电源：西卫 N-WC1、N-TR1；北卫马桶 + 毛巾架共用 N-TR2 双联出线面板（毛巾架挪到马桶旁后墙）。FCU 13A 都装在卫生间门外开关旁。",
              "3. 一层 C02 / C15 / C21 / C25 / C27 / C28 / C34 / S3 按模型位置（业主 2026-10-01 现场定）。",
              "4. 二层 S3（主卧主灯，与门口 S4 双控）：放在 C19 一侧床头柜上方 700，避开床头板。",
              "5. 被家具挡住的插座已挪开：电视柜后抬到 600；沙发、衣架、床、梳妆台、矮柜后的挪到家具外侧 150。",
              "6. 一层客厅 / 起居室之间的沙发墙已按模型 v42 补齐。",
              "7. 专用电器的开关 / FCU（洗碗机、烤箱、冰箱、洗衣机、烘干机、锅炉 + 软水机、烟机、地暖分水器、电梯、充电桩总控、报警器）本图不定位：由业主与电工现场确定，计划集中放在楼梯下。回路见插座动力图。"]
    for i, t in enumerate(issues):
        for j, l in enumerate(wrap(t, 120)): A(f'<text x="20" y="{203+i*7.4+j*3.4:.1f}" font-size="2.25">{E(l)}</text>')
    legend(s, 330, 32)
    s.frame()
    return s


def plan(F, number):
    PLN, rows = DATA[F]
    s = Sheet(f"{FLN[F]}点位定位总平面 Setting-out plan", number, F, ((-4.6, 4.6), (-1.0, 17.2)) if F == "GF" else ((-4.6, 4.6), (-0.6, 12.2)),
              discipline="电气定位 Setting out", **REV)
    s.base_plan(F)
    A = s.add
    for eid, rs in GROUPS[F]:            # elevation index marks
        r = rs[0]; mx, my = (r["L"][0] + r["R"][0]) / 2, (r["L"][1] + r["R"][1]) / 2
        q = (mx + r["n"][0] * 0.55, my + r["n"][1] * 0.55); px, py = s.P(*q); tx, ty = s.P(mx + r["n"][0] * 0.2, my + r["n"][1] * 0.2)
        A(f'<line x1="{px:.2f}" y1="{py:.2f}" x2="{tx:.2f}" y2="{ty:.2f}" stroke="#888" stroke-width=".25" marker-end="url(#ar)"/>'
          f'<rect x="{px-3.4:.2f}" y="{py-1.6:.2f}" width="6.8" height="3.2" rx="1" fill="#fff" stroke="#888" stroke-width=".25"/><text x="{px:.2f}" y="{py+0.8:.2f}" font-size="1.8" text-anchor="middle" fill="#555">{eid}</text>')
    s.defs.append('<marker id="ar" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto"><path d="M0 0 L4 2 L0 4 Z" fill="#888"/></marker>')
    # labels: points at the same spot share one label ("S4 / S5"); close labels are pushed down so they never overlap (owner 2026-10-08)
    pos = [(r, s.P(*(r.get("foot") or r["p"]))) for r in rows]
    groups = []
    for r, (x, y) in pos:
        for g in groups:
            if abs(g[1] - x) < 0.6 and abs(g[2] - y) < 0.6: g[0].append(r); break
        else: groups.append([[r], x, y])
    placed = []
    for rs, x, y in groups:
        for r in rs: A(sym(x, y, r["cat"], 1.1))
        txt = " / ".join(r["id"] for r in rs); w = len(txt) * 0.95 + 0.4
        lx, ly = x + 1.5, y - 1.3
        for _ in range(12):
            box = (lx, ly - 1.5, lx + w, ly + 0.4)
            if not any(box[0] < b[2] and box[2] > b[0] and box[1] < b[3] and box[3] > b[1] for b in placed): break
            ly += 2.0
        placed.append(box)
        if ly - (y - 1.3) > 0.1: A(f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{lx:.2f}" y2="{ly-0.5:.2f}" stroke="#999" stroke-width=".15"/>')
        A(f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="1.6" fill="{COL[rs[0]["cat"]]}">{E(txt)}</text>')
    legend(s, 300, 32)
    A(f'<text x="300" y="66" font-size="2" fill="#555">立面编号框 → 指向被看的墙（立面图见 SO-1x）</text>')
    s.frame(["说明 Notes", "1. 点位已推到所属墙面（平面上的位置 = 墙面位置）；尺寸见定位表和立面图。",
              "2. 高度标准见 SO-00；开关 1200、一般插座 300、床头 630 / 650、台面上方 1100。", "3. 给排水点位见给排水施工图。"])
    return s


def schedule_sheets(F, start):
    PLN, rows = DATA[F]
    wall = [r for r in rows if r.get("wall") not in ("天花", "地面", "室外地面", "岛台")]
    other = [r for r in rows if r.get("wall") in ("天花", "地面", "室外地面", "岛台")]
    order = {"switch": 0, "socket": 1, "power": 2, "new": 3, "water": 4, "light": 5}
    nat = lambda t: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", t)]
    wall.sort(key=lambda r: (order[r["cat"]], nat(r["id"])))
    for r in wall:
        if r["cat"] == "switch": r["room"], r["why"] = r["loc"], "开关中心 1100"; r["loc"] = ""
    W = [[r["id"], CAT[r["cat"]] + " · " + r["name"], r["room"], f'{r["wall"]}（{r.get("elev", "")}）' if r.get("wall") != "—" else "—",
          f'{r.get("lk", "")} {r.get("s", "")}', f'{r.get("rk", "")} {r.get("rest", "")}', r["h"],
          (r.get("why", "") + ("；" + r["flag"] if r.get("flag") else "") + ("；位置：" + r["loc"] if r.get("loc") else "")
           + (f'；排水：{r["drain"]}' if r.get("drain") else ""))] for r in wall]
    O = [[r["id"], CAT[r["cat"]] + " · " + r["name"], r["room"], r["wall"],
          f'{r["dx"][0] or ""} {r["dx"][1] or ""}', f'{r["dy"][0] or ""} {r["dy"][1] or ""}', r["h"], r.get("why", "")] for r in other]
    cols_w = [("编号", 11), ("类型 / 名称", 62), ("房间", 20), ("墙面（立面）", 24), ("距左端 mm", 22), ("距右端 mm", 22), ("高度", 11), ("依据 / 备注", 220)]
    cols_o = [("编号", 11), ("类型 / 名称", 62), ("房间", 20), ("位置", 18), ("南北向：距墙", 26), ("东西向：距墙", 26), ("高度", 11), ("备注", 218)]
    sheets, n = [], start
    for title, cols, data in ((f"{FLN[F]}墙面点位定位表（插座 / 开关 / 专用 / 壁灯）", cols_w, W), (f"{FLN[F]}天花灯位 / 地面点位定位表", cols_o, O)):
        i = 0
        while i < len(data):
            s = Sheet(title + "", f"SO-{n:02d}", "", ((0, 1), (0, 1)), scale_note="—", discipline="电气定位 Setting out", **REV)
            chunk = []; est = 0
            while i < len(data) and est < 62:
                chunk.append(data[i]); est += max(1, math.ceil(len(str(data[i][-1])) / 105)) * 0.75 + 0.4; i += 1
            table(s, 14, 30, cols, chunk, fs=1.75, title=title + "（尺寸 mm；距左 / 右端 = 面对墙看的左 / 右；高度 = 底盒中心离本房间完成地面）")
            s.frame(); sheets.append(s); n += 1
    return sheets, n


def elevation_sheets(F, start):
    PLN, rows = DATA[F]
    K = 20.0            # 1:50
    items = []
    for eid, rs in GROUPS[F]:
        r0 = rs[0]; L, R, n = r0["L"], r0["R"], r0["n"]; run = math.dist(L, R)
        mid = ((L[0] + R[0]) / 2 + n[0] * 0.3, (L[1] + R[1]) / 2 + n[1] * 0.3)
        Hh = max(so.ceil_h(F, *mid), max(r["h"] for r in rs) + 200) / 1000
        items.append((eid, rs, L, R, n, run, Hh))
    sheets, n_ = [], start
    x, y, rowh, s = 16.0, 30.0, 0.0, None

    def new():
        nonlocal s, n_
        s = Sheet(f"{FLN[F]}墙面立面 Wall elevations 1:50", f"SO-{n_:02d}", "", ((0, 1), (0, 1)), scale_note="1:50 立面", discipline="电气定位 Setting out", **REV)
        sheets.append(s); n_ += 1
    new()
    for eid, rs, L, R, nrm, run, Hh in items:
        w, h = run * K + 30, Hh * K + 30
        if x + w > 408:
            x, y, rowh = 16.0, y + rowh + 6, 0.0
        if y + h > 252 or (y + h > 222 and x + w > 296):
            new(); x, y, rowh = 16.0, 30.0, 0.0
        draw_elev(s, x + 14, y + 8, eid, rs, L, R, nrm, run, Hh, K, F, PLN)
        x += w + 6; rowh = max(rowh, h)
    for s_ in sheets: s_.frame()
    return sheets, n_


def draw_elev(s, ox, oy, eid, rs, L, R, nrm, run, Hh, K, F, PLN):
    A = s.add
    W_, H_ = run * K, Hh * K
    base = oy + H_
    r0 = rs[0]
    A(f'<text x="{ox-12:.2f}" y="{oy-3:.2f}" font-size="2.2" font-weight="bold">{eid} · {E(r0["room"])} · {E(r0["wall"])}</text>')
    A(f'<rect x="{ox:.2f}" y="{oy:.2f}" width="{W_:.2f}" height="{H_:.2f}" fill="#fafafa" stroke="#555" stroke-width=".3"/>')
    A(f'<line x1="{ox-2:.2f}" y1="{base:.2f}" x2="{ox+W_+2:.2f}" y2="{base:.2f}" stroke="#b00020" stroke-width=".45"/>')
    rv = ((R[0] - L[0]) / run, (R[1] - L[1]) / run)
    fz = so.floor_z(F, (L[0] + R[0]) / 2 + nrm[0] * 0.3, (L[1] + R[1]) / 2 + nrm[1] * 0.3)
    face = so.LineString([L, R])
    for name, kind, poly, sill, head in PLN.openings:      # windows / doors in this wall face
        if poly.distance(face) > 0.3: continue
        xs = [((c[0] - L[0]) * rv[0] + (c[1] - L[1]) * rv[1]) for c in poly.exterior.coords]
        a, b = max(0, min(xs)), min(run, max(xs))
        if b - a < 0.1: continue
        A(f'<rect x="{ox+a*K:.2f}" y="{base-head/1000*K:.2f}" width="{(b-a)*K:.2f}" height="{(head-sill)/1000*K:.2f}" fill="#e3f0fa" stroke="#7a9cb8" stroke-width=".25"/>'
          f'<text x="{ox+(a+b)/2*K:.2f}" y="{base-head/1000*K+2.4:.2f}" font-size="1.4" text-anchor="middle" fill="#557">{"门" if kind == "door" else "窗"} {int(sill)}–{int(head)}</text>')
    furn = so.BEDSIDE.get(F, []) + so.TOPS.get(F, [])
    for t in furn:                                            # furniture in front of the wall (dashed)
        x0, y0, z0, x1, y1, z1 = so.ob(t)
        bx = so.box(x0, y0, x1, y1)
        if bx.distance(face) > 0.35: continue
        xs = [((c[0] - L[0]) * rv[0] + (c[1] - L[1]) * rv[1]) for c in bx.exterior.coords]
        a, b = max(0, min(xs)), min(run, max(xs)); top = (z1 - fz) * 1000
        if b - a < 0.05: continue
        A(f'<rect x="{ox+a*K:.2f}" y="{base-top/1000*K:.2f}" width="{(b-a)*K:.2f}" height="{top/1000*K:.2f}" fill="none" stroke="#999" stroke-width=".25" stroke-dasharray="1 .6"/>'
          f'<text x="{ox+(a+b)/2*K:.2f}" y="{base-top/1000*K-0.8:.2f}" font-size="1.3" text-anchor="middle" fill="#888">面 {so.r10(top)}</text>')
    pts = sorted(rs, key=lambda r: r["s"])
    lvl = {}
    for i, r in enumerate(pts):
        px, py = ox + r["s"] / 1000 * K, base - r["h"] / 1000 * K
        A(sym(px, py, r["cat"], 1.0))
        A(f'<text x="{px:.2f}" y="{py-1.7:.2f}" font-size="1.45" text-anchor="middle" fill="{COL[r["cat"]]}" font-weight="bold">{E(r["id"])}</text>'
          f'<text x="{px+1.4:.2f}" y="{py+0.5:.2f}" font-size="1.3" fill="#333">{r["h"]}</text>')
        A(f'<line x1="{px:.2f}" y1="{py+1.1:.2f}" x2="{px:.2f}" y2="{base+1.5:.2f}" stroke="{COL[r["cat"]]}" stroke-width=".12" stroke-dasharray=".6 .5"/>')
        k = 0
        while any(abs(px - q) < 3.2 for q in lvl.get(k, [])): k += 1
        lvl.setdefault(k, []).append(px)
        A(f'<text x="{px:.2f}" y="{base+3.6+k*2.3:.2f}" font-size="1.45" text-anchor="middle" fill="{COL[r["cat"]]}">{r["s"]}</text>')
    nl = max(lvl) + 1 if lvl else 1
    A(f'<text x="{ox:.2f}" y="{base+4.6+nl*2.3:.2f}" font-size="1.4" fill="#555">← 左端：{E(rs[0]["lk"])}（0）　净长 {so.r10(run*1000)}　右端：{E(rs[0]["rk"])} →</text>')
    A(f'<text x="{ox-1.2:.2f}" y="{base:.2f}" font-size="1.3" text-anchor="end" fill="#b00020">FFL</text>'
      f'<text x="{ox-1.2:.2f}" y="{oy+1.2:.2f}" font-size="1.3" text-anchor="end" fill="#555">{so.r10(Hh*1000)}</text>')


def sheets():
    out = [cover(), plan("GF", "SO-01"), plan("FF", "SO-02")]
    n = 3
    for F in ("GF", "FF"):
        ss, n = schedule_sheets(F, n); out += ss
    n = max(n, 10)
    for F in ("GF", "FF"):
        ss, n = elevation_sheets(F, n); out += ss
    return out


if __name__ == "__main__":
    from build_drawings import build

    class M:
        CSS = CSS
        sheets = staticmethod(sheets)
    build("27PR_点位定位尺寸图_RevA", M)
