# -*- coding: utf-8 -*-
"""27PR 点位定位尺寸图 Rev C (2026-10-14, model v47; Rev B 2026-10-09) — built from the FINAL wall-elevation sets (owner-approved 2026-10-09).

    python points_final.py          -> _points_final.json (positions taken from wall_elev.py)
    python setting_out_sheets.py    -> out/27PR_点位定位尺寸图_RevC.pdf (+ out/png/SO-*.png)

Rev A (setting_out_sheets_revA.py) drew its own 1:50 elevations from the old point data; since Rev B the wall-elevation
sets (W1-xx / W2-xx) ARE the elevations, and this set gives the whole-floor plans + full schedules that point to them.
"""
import html, json, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plan_base import Sheet, BASE_CSS, table, wrap

HERE = os.path.dirname(os.path.abspath(__file__))
E = html.escape
REV = dict(rev="C", date="2026-10-14")
COL = {"socket": "#1565c0", "power": "#6a1b9a", "switch": "#111111", "light": "#e65100", "water": "#00897b", "new": "#c62828", "smoke": "#c62828"}
CAT = {"socket": "插座", "switch": "开关", "new": "专用 / FCU / 新增", "light": "灯", "smoke": "烟感", "water": "给排水点"}
CSS = BASE_CSS + ".lbl{fill:#222}"
FLN = {"GF": "一层", "FF": "二层"}
D = json.load(open(os.path.join(HERE, "_points_final.json"), encoding="utf-8"))
nat = lambda t: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", t)]


def sym(x, y, cat, r=1.3):
    c = COL[cat]
    if cat == "socket": return f'<rect x="{x-r:.2f}" y="{y-r:.2f}" width="{2*r:.2f}" height="{2*r:.2f}" fill="#fff" stroke="{c}" stroke-width=".35"/><line x1="{x-r*.5:.2f}" y1="{y:.2f}" x2="{x+r*.5:.2f}" y2="{y:.2f}" stroke="{c}" stroke-width=".3"/>'
    if cat == "switch": return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r*.8:.2f}" fill="{c}"/>'
    if cat in ("light", "smoke"): return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="#fff" stroke="{c}" stroke-width=".35"/><path d="M{x-r*.7:.2f} {y-r*.7:.2f} L{x+r*.7:.2f} {y+r*.7:.2f} M{x+r*.7:.2f} {y-r*.7:.2f} L{x-r*.7:.2f} {y+r*.7:.2f}" stroke="{c}" stroke-width=".3"/>'
    if cat == "water": return f'<path d="M{x:.2f} {y-r*1.1:.2f} L{x+r:.2f} {y+r*.8:.2f} L{x-r:.2f} {y+r*.8:.2f} Z" fill="#fff" stroke="{c}" stroke-width=".35"/>'
    return f'<path d="M{x:.2f} {y-r:.2f} L{x+r:.2f} {y:.2f} L{x:.2f} {y+r:.2f} L{x-r:.2f} {y:.2f} Z" fill="#fff" stroke="{c}" stroke-width=".4"/>'


def legend(s, x, y):
    s.add(f'<text x="{x}" y="{y}" font-size="2.4" font-weight="bold">图例</text>')
    for i, c in enumerate(CAT):
        yy = y + 4.2 + i * 3.8
        s.add(sym(x + 2, yy - 0.7, c) + f'<text x="{x+5}" y="{yy}" font-size="2" fill="{COL[c]}">{E(CAT[c])}</text>')


def sets_used():
    out = []
    for r in D["wall"] + D["ceiling"]:
        if r["set"] not in out: out.append(r["set"])
    return out


# ---------------- sheets ----------------
def cover():
    s = Sheet("点位定位尺寸图 说明 Setting-out notes", "SO-00", "", ((0, 1), (0, 1)), scale_note="—", discipline="电气定位 Setting out", **REV)
    A = s.add
    A('<text x="16" y="32" font-size="3.4" font-weight="bold">Rev C（2026-10-14）：按模型 v47 —— 洗衣房后门挪位 / 无门洞口、冰箱挪位、电器 FCU 集中（洗衣房 + 楼梯下柜内）、洗衣房白色面板</text>')
    how = ["• 本版所有点位的位置、高度、回路、备注都直接取自已完成的墙面立面图（业主逐面确认），立面图是准，本图是全屋汇总。",
           "• 每个点位在表里都写了「立面图号」（W1-xx-x 一层 / W2-xx-x 二层）：施工时按那张立面图上的尺寸放线。",
           "• 墙面名称按「站在房间里看这面墙」；水平尺寸从左端量到底盒中心，同时给到右端的距离，两数之和 = 墙净长，可核对。",
           "• 高度：从本房间完成地面量到底盒中心；天花灯给出到四面墙（完成面）的距离。",
           "• 同一编号可能在不同房间各有一个（如地暖温控 TH、智能马桶开关 SM / ST）：以「房间 + 编号」区分。",
           "• 给排水出口位置见给排水施工图（立面图只画了靠近电气点的几个：SH1、FT、户外台盆 OW / OD）。"]
    for i, t in enumerate(how):
        for j, l in enumerate(wrap(t, 125)): A(f'<text x="20" y="{40+i*5.6+j*3.4:.1f}" font-size="2.3">{E(l)}</text>')
    A('<text x="16" y="80" font-size="3.4" font-weight="bold">高度标准（底盒中心，离本房间完成地面；个别点以立面图为准）</text>')
    rows = [["开关", "1200", "主卫 / 主卧套间部分开关 1500（主卧套间 Rev L）；卫生间排风扇开关 1800"],
            ["一般插座", "450", "英国规格（业主 2026-10-08）"],
            ["厨房台面插座", "1200", "台面（900，Wren 橱柜图 S8097782/1）上方 300（业主 2026-10-09）"],
            ["专用插座（在柜内 / 机器后）", "300–450 / 1900", "洗碗机 C38 h450、灶 / 烤箱 C39 h300、洗衣机 / 烘干机 C12 h450、烟机 C40 在烟机柜内 h1900；按管道 / 电器调整"],
            ["电器开关 FCU（单联 fused switch）", "1200", "洗衣房锅炉下 4 个 FU1–FU4（洗衣机 / 烘干机 / 锅炉 / 地暖电子控制，白色）；楼梯下柜内 4 个 FD / FO1–FO3（洗碗机 / 烤箱 / 灶 / 烟机，白色）；二层卫生间 SM / ST 不变"],
            ["户外插座 / 户外壁灯", "600 / 2000", "户外插座 IP66 带盖（后院 C41 已取消，Rev C）；后院 B 墙壁灯 h2000；L08 挪到洗衣房后门左边"],
            ["EV 充电桩", "1050", "前门凹位北侧墙（前院 Rev B 预留位）"]]
    table(s, 16, 86, [("项", 52), ("高度 mm", 30), ("说明", 296)], rows, fs=2.1)
    A('<text x="16" y="140" font-size="3.4" font-weight="bold">依据的立面图（全部已完成）</text>')
    for i, n in enumerate(sets_used()):
        A(f'<text x="20" y="{147+i*4.2:.1f}" font-size="2.3">• {E(n)}.pdf</text>')
    y0 = 147 + len(sets_used()) * 4.2 + 6
    A(f'<text x="16" y="{y0:.1f}" font-size="3.4" font-weight="bold">与 Rev A 相比取消 / 合并的点位</text>')
    for i, m in enumerate(D["missing"]):
        A(f'<text x="20" y="{y0+7+i*4.2:.1f}" font-size="2.3">• {E(("一层 " if m[0] == "GF" else "二层 ") + m[1])}：{E(m[4])}</text>')
    legend(s, 330, 32)
    s.frame()
    return s


def base_plan_new_names(s, F):
    """base plan walls without the old (v42) room names; current room names from the elevation sets instead"""
    n0 = len(s.parts); s.base_plan(F)
    s.parts[n0:] = [q for q in s.parts[n0:] if 'class="room"' not in q]
    from shapely.geometry import Polygon as _P
    for a in D["areas"]:
        if a["F"] != F: continue
        c = _P(a["poly"]).representative_point(); px, py = s.P(c.x, c.y)
        s.add(f'<text x="{px:.2f}" y="{py:.2f}" font-size="2.8" text-anchor="middle" fill="#9e9e9e">{E(a["room"])}</text>')


def plan(F, number):
    s = Sheet(f"{FLN[F]}点位定位总平面 Setting-out plan", number, F, ((-4.6, 4.6), (-1.0, 17.2)) if F == "GF" else ((-4.6, 4.6), (-0.6, 12.2)),
              discipline="电气定位 Setting out", **REV)
    base_plan_new_names(s, F)
    A = s.add
    pts = [(r, r["cat"]) for r in D["wall"] if r["F"] == F] + [(r, r["cat"]) for r in D["ceiling"] if r["F"] == F] + \
          [(r, r["cat"]) for r in D["other"] if r["F"] == F]
    pos = [(r, c, s.P(*r["p"])) for r, c in pts]
    groups = []
    for r, c, (x, y) in pos:
        for g in groups:
            if abs(g[1] - x) < 0.6 and abs(g[2] - y) < 0.6: g[0].append((r, c)); break
        else: groups.append([[(r, c)], x, y])
    placed = []
    for rs, x, y in groups:
        for r, c in rs: A(sym(x, y, c, 1.1))
        txt = " / ".join(r["id"] for r, _ in rs); w = len(txt) * 0.95 + 0.4
        lx, ly = x + 1.5, y - 1.3
        for _ in range(14):
            bx = (lx, ly - 1.5, lx + w, ly + 0.4)
            if not any(bx[0] < b[2] and bx[2] > b[0] and bx[1] < b[3] and bx[3] > b[1] for b in placed): break
            ly += 2.0
        placed.append(bx)
        if ly - (y - 1.3) > 0.1: A(f'<line x1="{x:.2f}" y1="{y:.2f}" x2="{lx:.2f}" y2="{ly-0.5:.2f}" stroke="#999" stroke-width=".15"/>')
        A(f'<text x="{lx:.2f}" y="{ly:.2f}" font-size="1.6" fill="{COL[rs[0][1]]}">{E(txt)}</text>')
    legend(s, 300, 32)
    s.frame(["说明 Notes", "1. Rev B：点位全部按已完成的墙面立面图（业主 2026-10-09 确认）。Rev C（2026-10-14）：厨房区 Rev C / 后院 Rev D / 主客厅区 Rev I（模型 v47）；洗衣房开关插座白色；柜内插座 C26 / C38 / C39 / C40 白色；C01 / C02 / C38 改双位。",
             "2. 平面上的位置 = 墙面位置；放线尺寸、高度见定位表里的立面图号（W1- / W2-），哪个区域看哪个立面图文件见 SO-03 / SO-04。",
             "3. 给排水出口见给排水施工图。"])
    return s


PAL = ["#ef9a9a", "#90caf9", "#a5d6a7", "#ffe082", "#ce93d8", "#80cbc4", "#ffab91", "#b0bec5", "#f48fb1", "#c5e1a5"]


def set_short(st):
    t = st.split("_")
    return t[2], t[3], st


def index_sheet(F, number):
    """which elevation set (printed PDF) covers which area: areas shaded per set, sheet prefix on the plan + file list"""
    s = Sheet(f"{FLN[F]}立面图索引 Which elevation set to read", number, F, ((-4.6, 4.6), (-1.0, 17.2)) if F == "GF" else ((-4.6, 4.6), (-0.6, 12.2)),
              discipline="电气定位 Setting out", **REV)
    A = s.add
    order = sets_used()
    col = {st: PAL[i % len(PAL)] for i, st in enumerate(order)}
    areas = [a for a in D["areas"] if a["F"] == F]
    from shapely.geometry import Polygon as _P, box as _box
    page = _box(-4.6, -1.0, 4.6, 17.2) if F == "GF" else _box(-4.6, -0.6, 4.6, 12.2)
    for a in areas:                                                     # shade first (clipped to the sheet), walls on top
        g = _P(a["poly"]).intersection(page)
        if g.is_empty or g.geom_type != "Polygon": continue
        d = "M" + " L".join(f"{x:.2f} {y:.2f}" for x, y in (s.P(*c) for c in g.exterior.coords)) + " Z"
        A(f'<path d="{d}" fill="{col[a["set"]]}" fill-opacity=".55" stroke="{col[a["set"]]}" stroke-width=".4"/>')
    base_plan_new_names(s, F)
    for a in areas:
        c = _P(a["poly"]).intersection(page).representative_point(); px, py = s.P(c.x, c.y)
        nm = set_short(a["set"])[0]
        A(f'<text x="{px:.2f}" y="{py+4.5:.2f}" font-size="2.6" text-anchor="middle" font-weight="bold" fill="#000" style="paint-order:stroke;stroke:#fff;stroke-width:.9">{E(a["prefix"])}</text>'
          f'<text x="{px:.2f}" y="{py+7.6:.2f}" font-size="2" text-anchor="middle" fill="#333" style="paint-order:stroke;stroke:#fff;stroke-width:.8">{E(nm)}</text>')
    x0, y0 = 300, 34
    A(f'<text x="{x0}" y="{y0}" font-size="3" font-weight="bold">按区域找立面图文件（打印的立面图）</text>')
    sets_f = [st for st in order if any(a["set"] == st for a in areas)]
    y = y0 + 6
    for st in sets_f:
        nm, rev, full = set_short(st)
        pre = sorted({a["prefix"] for a in areas if a["set"] == st})
        rooms = "、".join(a["room"] for a in areas if a["set"] == st)
        A(f'<rect x="{x0}" y="{y-3:.1f}" width="6" height="4" fill="{col[st]}" fill-opacity=".55" stroke="{col[st]}" stroke-width=".4"/>'
          f'<text x="{x0+8}" y="{y:.1f}" font-size="2.5" font-weight="bold">{E(nm)}  {E(" / ".join(pre))}-x  （{E(rev)}）</text>')
        for j, l in enumerate(wrap("文件：" + full + ".pdf", 50)):
            A(f'<text x="{x0+8}" y="{y+3.6+j*3.1:.1f}" font-size="2" fill="#333">{E(l)}</text>')
        n = len(wrap("文件：" + full + ".pdf", 50))
        A(f'<text x="{x0+8}" y="{y+3.6+n*3.1:.1f}" font-size="2" fill="#666">房间：{E(rooms)}</text>')
        y += 9 + n * 3.1
    s.frame(["怎么用 How to use", "1. 定位表里每个点位都写了立面图号，例如 W1-04-6：前面 W1-04 = 区域（本图颜色块），后面 -6 = 该立面图文件里的第 6 张。",
             "2. 按颜色块找到对应的立面图文件（已完成，打印版），翻到那一张按尺寸放线。", "3. W1- 为一层，W2- 为二层。"])
    return s


def schedule_sheets(F, start):
    order = {"switch": 0, "socket": 1, "new": 2, "water": 3, "light": 4}
    wall = sorted([r for r in D["wall"] if r["F"] == F], key=lambda r: (order.get(r["cat"], 9), nat(r["id"]), r["room"]))
    W = [[r["id"], CAT.get(r["cat"], r["cat"]) + " · " + r["name"], r["room"], f'{r["face"]} · {r["face_nm"]}', r["sheet"],
          f'{r["ends"][0]} {r["sL"]}', f'{r["ends"][1]} {r["sR"]}', r["h"], r["circ"], r["note"]] for r in wall]
    ceil = sorted([r for r in D["ceiling"] if r["F"] == F], key=lambda r: nat(r["id"]))
    O = [[r["id"], CAT[r["cat"]] + " · " + r["name"], r["room"], r["sheet"], f'北 {r["d"]["N"]} / 南 {r["d"]["S"]}', f'西 {r["d"]["W"]} / 东 {r["d"]["E"]}',
          r["h"], r["circ"], r["switch"]] for r in ceil]
    O += [[r["id"], CAT[r["cat"]] + " · " + r["name"], r["room"], "（平面）", "—", "—", r["h"], "", f'{r["where"]}；{r["note"]}'] for r in D["other"] if r["F"] == F]
    cols_w = [("编号", 11), ("类型 / 名称", 58), ("房间", 18), ("墙面", 30), ("立面图号（见 SO-03 / 04）", 30), ("左端 mm", 26), ("右端 mm", 26), ("高度", 10), ("回路", 18), ("备注（立面图）", 156)]
    cols_o = [("编号", 11), ("类型 / 名称", 70), ("房间", 20), ("天花图号（见 SO-03 / 04）", 30), ("南北向：距墙", 34), ("东西向：距墙", 34), ("天花高", 14), ("回路", 14), ("开关 / 备注", 156)]
    sheets, n = [], start
    for title, cols, data in ((f"{FLN[F]}墙面点位定位表（插座 / 开关 / 专用 / 壁灯）", cols_w, W), (f"{FLN[F]}天花灯位 / 其他点位定位表", cols_o, O)):
        i = 0
        while i < len(data):
            s = Sheet(title, f"SO-{n:02d}", "", ((0, 1), (0, 1)), scale_note="—", discipline="电气定位 Setting out", **REV)
            chunk = []; est = 0
            while i < len(data) and est < 60:
                chunk.append(data[i]); est += max(1, math.ceil(len(str(data[i][-1])) / 80)) * 0.75 + 0.4; i += 1
            table(s, 14, 30, cols, chunk, fs=1.7, title=title + "（尺寸 mm；左 / 右端 = 面对墙看的左 / 右；高度 = 底盒中心离本房间完成地面；按立面图号放线）")
            s.frame(); sheets.append(s); n += 1
    return sheets, n


def sheets():
    out = [cover(), plan("GF", "SO-01"), plan("FF", "SO-02"), index_sheet("GF", "SO-03"), index_sheet("FF", "SO-04")]
    n = 5
    for F in ("GF", "FF"):
        ss, n = schedule_sheets(F, n); out += ss
    return out


if __name__ == "__main__":
    from build_drawings import build

    class M:
        CSS = CSS
        sheets = staticmethod(sheets)
    build("27PR_点位定位尺寸图_RevC", M)
