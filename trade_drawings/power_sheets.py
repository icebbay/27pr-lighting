# -*- coding: utf-8 -*-
"""27PR 插座 / 动力施工图 (sockets + dedicated circuits, for the electrician) — generated from the power tool data
(lighting_tool/power_<F>.json + power_plans.json, plan A 专业 18 路, the default).

Ring finals (2.5 mm² 6242Y, B32 RCBO 30 mA): AL1 -> sockets in nearest-neighbour order -> back to AL1 (return leg dashed);
radials (4 mm², WX4 laundry, WX9 outdoor) stop at the last outlet. Dedicated points (WP) are home runs from AL1.
Routes are orthogonal schematic runs (in practice: down the wall from the ceiling void / along the floor void, safe zones only).
"""
import html, json, math, os
from plan_base import Sheet, BASE_CSS, MM, load_tool, Frame, table, TOOL

PLAN = "A"
PL = json.load(open(os.path.join(TOOL, "power_plans.json"), encoding="utf-8"))[PLAN]
CIRC = {c["id"]: c for c in PL["WX"] + PL["WP"]}
COL = {"WX1": "#1f77b4", "WX2": "#7b2cbf", "WX3": "#e67e22", "WX4": "#0b8a6f", "WX5": "#1f77b4", "WX6": "#c0392b", "WX7": "#7b2cbf",
       "WX8": "#0b8a6f", "WX9": "#2e7d32", "WP1": "#a0522d", "WP2": "#555555", "WP3": "#d81b60", "WP4": "#d81b60", "WP5": "#006d77", "WP6": "#e67e22"}
RADIAL = {"WX4", "WX9"}
KIND = {"double": ("双联插座 13A", "450"), "single": ("单联插座 13A", "450"), "outdoor": ("户外防水插座 IP66", "600"), "high": ("空调高位插座", "2000")}
# the high sockets are the air-conditioner points: their own WP circuits (power_plans notes "见二层插座图「高」")
HIGH_CIRC = {"卧室 3": "WP3", "卧室 4": "WP4"}
CSS = BASE_CSS + """.lbl{fill:#222}.cu{fill:#222}.so{fill:#fff;stroke-width:.35}.fcu{fill:#fff;stroke-width:.35}"""


def data(F):
    P = json.load(open(os.path.join(TOOL, f"power_{F}.json"), encoding="utf-8")); fr = Frame(F)
    socks = []
    for s in P["sockets"]:
        c = HIGH_CIRC.get(s["room"], s["c"][PLAN]) if s["kind"] == "high" else s["c"][PLAN]
        socks.append(dict(s, b=fr.t2b(s["x"], s["y"]), cc=c))
    items = [dict(i, b=fr.t2b(i["x"], i["y"]), cc=i["c"][PLAN]) for i in P["items"]]
    J = load_tool(F)
    return socks, items, fr.t2b(J["board"]["x"], J["board"]["y"])


def ortho(a, b):
    return [a, (a[0], b[1]), b]


def mlen(pts):
    return sum(abs(p[0] - q[0]) + abs(p[1] - q[1]) for p, q in zip(pts, pts[1:]))


def plan_sheet(F, number):
    socks, items, board = data(F)
    fl = "一层 GF" if F == "GF" else "二层 FF"
    s = Sheet(f"{fl} 插座 / 动力平面图 Small power layout", number, F, ((-4.6, 4.6), (-1.0, 17.2)) if F == "GF" else ((-4.6, 4.6), (-0.6, 12.2)),
              discipline="电气 Electrical (power)")
    s.base_plan(F)
    A = s.add

    def path(pts, col, w, dash=""):
        A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in (s.P(*p) for p in pts)) + f'" fill="none" stroke="{col}" stroke-width="{w}" stroke-dasharray="{dash}" stroke-linejoin="round" opacity=".85"/>')

    sched = []
    groups = {}
    for p in socks: groups.setdefault(p["cc"], []).append(("s", p))
    for i in items:
        if i.get("fcu"): groups.setdefault(i["cc"], []).append(("i", i))
    for cid in sorted(groups, key=lambda c: (c[:2] != "WX", int(c[2:]))):
        pts = [x["b"] for _, x in groups[cid]]; col = COL.get(cid, "#333")
        cur, rest, run = board, list(pts), 0.0
        first = True
        while rest:
            n = min(rest, key=lambda p: math.dist(p, cur)); rest.remove(n)
            seg = ortho(cur, n); path(seg, col, 0.6 if first else 0.45); run += mlen(seg); cur = n; first = False
        ring = cid.startswith("WX") and cid not in RADIAL
        if ring:
            seg = ortho(cur, board); path(seg, col, 0.45, "2 1"); run += mlen(seg)
        c = CIRC.get(cid, {})
        kinds = {}
        for t, x in groups[cid]:
            k = KIND[x["kind"]][0] if t == "s" else "FCU"
            kinds[k] = kinds.get(k, 0) + 1
        sched.append([cid, c.get("name", ""), c.get("br", ""), ("环路 ring" if ring else "径向 radial") + " " + c.get("cable", ""),
                      " ".join(f"{k}×{v}" for k, v in kinds.items()), f"{run + 3 * len(pts):.0f}"])
    # dedicated home runs (lift, charger via the indoor isolator)
    ded = [i for i in items if not i.get("fcu")]
    ev = sorted([i for i in ded if i["cc"] == "WP5"], key=lambda i: "控制开关" not in i["label"])
    for cid in sorted({i["cc"] for i in ded}):
        chain = [board] + [i["b"] for i in (ev if cid == "WP5" else [i for i in ded if i["cc"] == cid])]
        run = 0.0
        for a, b in zip(chain, chain[1:]):
            seg = ortho(a, b); path(seg, COL.get(cid, "#333"), 0.8, "4 1.2"); run += mlen(seg)
        c = CIRC.get(cid, {})
        sched.append([cid, c.get("name", ""), c.get("br", ""), "径向 radial " + c.get("cable", ""),
                      "隔离开关 + 充电桩" if cid == "WP5" else "隔离开关（厂家定位）", f"{run + 3:.0f}"])
    if F == "FF":
        for cid in ("WP3", "WP4"):
            c = CIRC[cid]; n = sum(1 for p in socks if p["cc"] == cid)
            sched = [r for r in sched if r[0] != cid] + [[cid, c["name"] + "（" + c["note"][:10] + "）", c["br"], "径向 radial " + c["cable"], f"空调高位插座 / FCU ×{n}", next((r[5] for r in sched if r[0] == cid), "—")]]
    # symbols
    for p in socks:
        px, py = s.P(*p["b"]); col = COL.get(p["cc"], "#333"); k = p["kind"]
        if k == "outdoor":
            A(f'<rect x="{px-1.6:.2f}" y="{py-1.6:.2f}" width="3.2" height="3.2" class="so" stroke="{col}"/><text x="{px:.2f}" y="{py+0.7:.2f}" font-size="1.7" text-anchor="middle" font-weight="bold" fill="{col}">外</text>')
        else:
            A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.5" class="so" stroke="{col}"/><text x="{px:.2f}" y="{py+0.7:.2f}" font-size="1.7" text-anchor="middle" font-weight="bold" fill="{col}">{"2" if k == "double" else "1" if k == "single" else "高"}</text>')
        A(f'<text x="{px+1.9:.2f}" y="{py-1.4:.2f}" font-size="1.4" fill="{col}">{p["cc"]}</text>')
    for i in items:
        px, py = s.P(*i["b"]); col = COL.get(i["cc"], "#333")
        lab = i["label"].split("（")[0]
        if i.get("fcu"):
            A(f'<rect x="{px-2:.2f}" y="{py-1.3:.2f}" width="4" height="2.6" class="fcu" stroke="{col}"/><text x="{px:.2f}" y="{py+0.6:.2f}" font-size="1.3" text-anchor="middle" fill="{col}">FCU</text>'
              f'<text x="{px:.2f}" y="{py+3.9:.2f}" font-size="1.6" text-anchor="middle" fill="{col}">{html.escape(lab)} · {i["cc"]}</text>')
        else:
            iso = "控制开关" in i["label"] or "电梯" in i["label"]
            A(f'<rect x="{px-2.2:.2f}" y="{py-2.2:.2f}" width="4.4" height="4.4" class="fcu" stroke="{col}" stroke-width=".5"/>'
              f'<text x="{px:.2f}" y="{py+0.7:.2f}" font-size="1.6" text-anchor="middle" font-weight="bold" fill="{col}">{"DP" if iso else "EV"}</text>'
              f'<text x="{px+(3 if "控制开关" in i["label"] or "电梯" in i["label"] else 12):.2f}" y="{py+(5.2 if "控制开关" in i["label"] else -2.8):.2f}" font-size="1.7" fill="{col}">{html.escape(i["label"])} · {i["cc"]}</text>')
    if F == "FF":
        ac_overlay(s)
    bx, by = s.P(*board)
    A(f'<rect x="{bx-2.6:.2f}" y="{by-1.6:.2f}" width="5.2" height="3.2" class="cu"/><text x="{bx:.2f}" y="{by+5:.2f}" font-size="2.1" text-anchor="middle" font-weight="bold">'
      + ("AL1 配电箱 CU（楼梯下）" if F == "GF" else "↑ 二层回路自一层 AL1 沿楼梯井引上") + '</text>')
    # legend
    x0, y0 = 168, 219
    A(f'<rect x="{x0-3}" y="{y0-5}" width="128" height="58" fill="#fff" stroke="#999" stroke-width=".2"/><text x="{x0}" y="{y0}" font-size="2.6" font-weight="bold">图例 Legend</text>')
    L = [("#333", 0.6, "", "环路 / 径向出线（颜色 = 回路，见回路表）"), ("#333", 0.45, "2 1", "环路回线 ring return（回到 AL1 同一个 RCBO）"),
         ("#333", 0.8, "4 1.2", "专线 home run（单独 RCBO）")]
    for i, (c, w, d, t) in enumerate(L):
        yy = y0 + 4.6 * (i + 1)
        A(f'<line x1="{x0}" y1="{yy}" x2="{x0+12}" y2="{yy}" stroke="{c}" stroke-width="{w}" stroke-dasharray="{d}"/><text x="{x0+15}" y="{yy+0.8}" font-size="2">{html.escape(t)}</text>')
    syms = [("2", "双联插座 13A（带开关），中心离地 450"), ("1", "单联插座 13A，离地 450"), ("高", "空调高位插座，离地 2000（专线 WP3 / WP4）"),
            ("外", "户外防水插座 IP66，离地 600（WX9，出户段 SWA）"), ("FCU", "带保险开关接线盒 FCU 13A（电器专用，装在可触及处）"),
            ("DP", "双极隔离开关（电梯 / 充电桩室内总控 40A）")]
    for i, (k, t) in enumerate(syms):
        yy = y0 + 4.6 * (len(L) + 1) + i * 4.2
        A(f'<circle cx="{x0+6}" cy="{yy-0.6}" r="1.5" fill="#fff" stroke="#333" stroke-width=".3"/><text x="{x0+6}" y="{yy+0.1}" font-size="1.4" text-anchor="middle" font-weight="bold">{k}</text><text x="{x0+15}" y="{yy+0.2}" font-size="2">{html.escape(t)}</text>')
    table(s, 14, 214, [("回路", 8), ("名称", 38), ("保护", 26), ("线缆", 32), ("出线点", 34), ("估长 m", 10)], sched, fs=1.55,
          title=f"回路与线缆表 Circuit schedule（{PL['name'][:12]}；长度为平面估算 + 每点 3 m 竖向）")
    cnt = {}
    for p in socks: cnt[(p["room"], p["kind"])] = cnt.get((p["room"], p["kind"]), 0) + 1
    rooms = {}
    for (r, k), n in cnt.items(): rooms.setdefault(r, []).append(f"{KIND[k][0].split(' ')[0]}×{n}")
    rows = [[r, "、".join(v), next((p["cc"] for p in socks if p["room"] == r), "")] for r, v in rooms.items()]
    table(s, 300, 32, [("房间", 22), ("插座", 64), ("回路", 12)], rows, fs=1.7, title="房间插座数量 Outlets by room")
    s.frame(NOTES)
    return s


# 空调一拖一 ×2 (2026-10-07, model v41): indoor units on the 卧室 3 / 书房二 party wall, outdoor units on the annex flat roof,
# refrigerant pair + condensate + signal cable through the loft over 卧室 3, out through a weathered roof sleeve.
AC_IN = {"WP3": ((0.73, 1.57, 7.72, 7.93), "卧室 3 内机"), "WP4": ((1.72, 2.56, 8.11, 8.32), "书房二 内机")}
AC_OUT = [((-1.56, -0.71, 6.64, 7.12), "外机 1（卧室 3）"), ((-2.62, -1.76, 6.64, 7.12), "外机 2（书房二）")]   # on the flat roof, z 5.44
AC_ROUTE = [[(1.00, 7.80), (1.00, 7.20)], [(2.00, 8.15), (2.00, 8.02), (2.00, 7.20)],
            [(2.00, 7.20), (-0.64, 7.20), (-0.80, 7.20), (-0.80, 6.60), (-2.62, 6.60)], [(-1.55, 6.60), (-1.55, 6.70)], [(-2.60, 6.60), (-2.60, 6.70)]]


def ac_overlay(s):
    A = s.add; col = "#0077b6"
    for pts in AC_ROUTE:
        A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in (s.P(*p) for p in pts)) + f'" fill="none" stroke="{col}" stroke-width=".7" stroke-dasharray="2.4 .9"/>')
    for (x0, x1, y0, y1), t in list(AC_IN.values()) + AC_OUT:
        (ax, ay), (bx, by) = s.P(x0, y0), s.P(x1, y1)
        out = "外机" in t
        dash = ' stroke-dasharray="1.2 .6"' if out else ""
        A(f'<rect x="{min(ax,bx):.2f}" y="{min(ay,by):.2f}" width="{abs(bx-ax):.2f}" height="{abs(by-ay):.2f}" fill="#e3f2fd" stroke="{col}" stroke-width=".4"{dash}/>')
        cx, cy = (ax + bx) / 2, (ay + by) / 2
        if out:
            A(f'<text x="{cx:.2f}" y="{cy+0.6:.2f}" font-size="1.6" text-anchor="middle" fill="{col}">{html.escape(t.split("（")[0])}</text>')
        else:
            A(f'<text x="{cx:.2f}" y="{cy:.2f}" font-size="1.4" text-anchor="middle" fill="{col}" transform="rotate(-90 {cx:.2f} {cy:.2f})" dy=".5">{html.escape(t)}</text>')
    for (x0, x1, y0, y1), t in AC_OUT:     # roof isolator beside each outdoor unit
        px, py = s.P((x0 + x1) / 2, y1 + 0.14)
        A(f'<rect x="{px-1.2:.2f}" y="{py-1.2:.2f}" width="2.4" height="2.4" fill="#fff" stroke="{col}" stroke-width=".4"/><text x="{px:.2f}" y="{py+0.6:.2f}" font-size="1.2" text-anchor="middle" fill="{col}">DP</text>')
    # note block in the empty area behind the rear wall, leaders to the outdoor units and the roof sleeve
    bx, by, bw = 196.0, 42.0, 80.0
    lines = ["空调一拖一 ×2（虚线 = 屋面上，不在室内）",
             "• 外机 1（卧室 3）、外机 2（书房二）在副楼平屋顶，",
             "\u3000 主卧 / 北卫上方；外机旁各一个 IP65 双极隔离开关 DP",
             "• 冷媒管 + 冷凝水 + 信号线：卧室 3 上方阁楼内走，",
             "\u3000 穿屋面防水套管；墙外不做管槽",
             "• 内机高位插座离地 2000：卧室 3 → WP3，书房二 → WP4"]
    h = 3.0 * len(lines) + 2.5; bold = ' font-weight="bold"'
    A(f'<rect x="{bx}" y="{by}" width="{bw}" height="{h:.1f}" fill="#fff" stroke="{col}" stroke-width=".3"/>')
    for i, t in enumerate(lines):
        A(f'<text x="{bx+1.5}" y="{by+3.6+i*3.0:.1f}" font-size="{2.0 if i == 0 else 1.8}" fill="{col}"{bold if i == 0 else ""}>{html.escape(t)}</text>')
    for x, y in ((-1.13, 7.12), (-2.19, 7.12), (-0.80, 7.20)):
        px, py = s.P(x, y)
        A(f'<path d="M{bx:.2f} {by+h/2:.2f} L{px:.2f} {py:.2f}" stroke="{col}" stroke-width=".2" fill="none"/><circle cx="{px:.2f}" cy="{py:.2f}" r=".4" fill="{col}"/>')


NOTES = [
    "说明 Notes",
    "1. 依据 BS 7671:2018+A2、IET On-Site Guide；Part P 须由注册电工施工、测试并出具 EIC；全部回路 RCBO 30 mA（Type A）。",
    "2. 插座环路 2.5 mm² 6242Y，B32；单个环路服务面积 ≤ 100 m²；洗衣房 WX4、户外 WX9 为 4 mm² 32A 径向。",
    "3. 插座中心离地 450（Part M），厨房台面插座离台面 150；FCU 装在台面上方或相邻柜内可触及处，电器插头不藏在电器背后。",
    "4. 墙内线缆只走安全区（插座 / 开关正上下方及距墙角 150 mm 内），否则用金属保护或 RCD（已全 RCD）。",
    "5. 卫生间 0 / 1 区内不得装插座；电热毛巾架用 FCU 接 WX6。户外插座 IP66，出户段 SWA 铠装电缆。",
    "6. 充电桩 WP5：AL1 → 客厅内 40A 双极隔离开关（离地 1.2 m）→ 穿墙 → 副客厅前门西侧凹进处的充电桩（离地约 1.0 m）。B32/B40 Type A RCBO + 6 mA 直流检测（充电桩自带或另装）；6–10 mm² 按长度复核；建议带负载管理（CT 互感器）；安装前通知 DNO。",
    "7. 电梯 WP2 按厂家要求设独立隔离开关。空调一拖一 ×2：内机高位插座接 WP3 / WP4；外机在副楼平屋顶，电源由内机侧按机型接线（或 WP3 / WP4 直接到屋面隔离开关），外机旁装 IP65 双极隔离开关；冷媒管 / 冷凝水 / 信号线经阁楼走，穿屋面用防水套管；冷凝水接屋面雨水口或带存水弯接污水。",
]


def board_sheet():
    """E-13: consumer-unit schedule (plan A) — every final circuit with breaker, cable and what it feeds."""
    s = Sheet(f"配电箱回路表 Consumer unit schedule（方案 {PLAN}）", "E-13", "", ((0, 1), (0, 1)), scale_note="NTS", discipline="电气 Electrical (power)")
    b = PL["board"]
    rows = [[c["id"], c["name"], c["br"], c.get("cable", "1.5 mm² 6242Y"), c.get("note", "")] for c in PL["lighting"]]
    rows += [[c["id"], c["name"], c["br"], c["cable"], c.get("note", "")] for c in PL["WX"] + PL["WP"]]
    rows += [["备用", b.get("reserve", ""), "", "", ""]]
    y = table(s, 16, 34, [("回路", 12), ("名称", 92), ("保护", 66), ("线缆", 60), ("备注", 150)], rows, fs=2.1, title=f"AL1 配电箱（楼梯下）· {b['model']} · {b['ways']} 位")
    info = [f"总闸 {b['main']}；浪涌保护 {b['spd']}；尺寸 {b['size']}", f"RCBO：{b['rcbo']}",
            "照明 B6、插座环路 B32、径向按线径；全部 30 mA RCBO，单回路故障不影响其它回路。", "完工后贴回路标签（与本表编号一致），出具 EIC 与测试记录。"]
    for i, t in enumerate(info):
        s.add(f'<text x="16" y="{y + 10 + i * 6:.1f}" font-size="2.6">{html.escape(t)}</text>')
    s.frame()
    return s


def sheets():
    return [plan_sheet("GF", "E-11"), plan_sheet("FF", "E-12"), board_sheet()]
