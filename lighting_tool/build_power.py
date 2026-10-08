"""Sockets + dedicated circuits for two candidate plans -> power_GF/FF.json + power_plans.json + power_data.js (power.html / board.html).

Plans (2026-10-03/04, still being discussed — the lighting page switches between them too, #A / #B):
  A  专业 18 路: lighting 4 (from lighting_<F>.json) + sockets 9 (one computer+TV room per circuit) + dedicated 5
  B  精简 17 路: lighting 3 (downstairs / outdoor / upstairs) + sockets 8 (two studies + corridor share one) + dedicated 6 (fridge on its own)
Socket points: the user's coloured dots on the socket pages of the v10 PPT (= v6 + rear bedroom 4 + bedroom 2 door; slide 3 GF, slide 7 FF; olive = double,
blue = single, yellow = outdoor, "高" = high level). Those pages show the plan rotated 90° and scaled; the transform into the
lighting tool's frame (slide EMU of walls_<F>.svg) is fitted on the wall shapes both pages share (error <= 1 EMU).

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\build_power.py
"""
import json, math, os, re, collections
import numpy as np
from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
PPT = os.path.join(HERE, "..", "source_pptx", "Blender模型户型图_灯_插座_水路_可编辑_v10_照明控制图_专业版_卧室2进门.pptx")   # v10 = v6 + 后卧室 4 / 东侧套卫 + 卧室 2 进门西移 (2026-10-06)
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
_src = open(os.path.join(HERE, "export_lighting_json.py"), encoding="utf-8").read()
_ns = {"math": math, "A": A}
exec(_src[_src.index("def xf(el):"):_src.index("def shape_paths")], _ns)   # xf / placer / walk: group transforms
LJ = {F: json.load(open(os.path.join(HERE, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}

# PC / TV leak ~0.5–1.5 mA each in practice (limit 3.5–5 mA); BS 7671 keeps the standing leakage on a 30 mA RCBO under 9 mA.
# IET On-Site Guide: 32 A ring 2.5 mm² <= 100 m²; 20 A radial 2.5 mm² <= 50 m²; 32 A radial 4 mm² <= 75 m².
RING = "2.5 mm² 环路（ring，≤ 100 m²）"
RAD20 = "2.5 mm² 径向 20A（≤ 50 m²，约 4.6 kW）"
RCBO = "BG 单模块 RCBO（Type A 30 mA），约 £11–16 / 个"
# rooms are matched by label index in lighting_<F>.json["rooms"] (names repeat: 储物间 ×3, 卫生间 ×3)
GF_X = [
    dict(id="WX1", floor="GF", name="一层前区插座（起居室 / 餐厅 / 门厅 / 楼梯）", rooms=["起居室", "餐厅", "储物间#4", "储物间#6", "楼梯"], br="B32 RCBO 30mA", cable=RING, note="起居室电视、吸尘器、电暖器"),
    dict(id="WX2", floor="GF", name="一层客厅插座（客厅 / 卫生间）", rooms=["客厅", "卫生间", "储物间#12"], br="B32 RCBO 30mA", cable=RING, note="客厅电视"),
    dict(id="WX3", floor="GF", name="厨房插座（厨房 / 吧台区，含冰箱、洗碗机、燃气灶点火）", rooms=["厨房", "厨房（吧台区）"], br="B32 RCBO 30mA", cable=RING, note="电水壶等集中，用量接近满载"),
    dict(id="WX4", floor="GF", name="洗衣房（洗衣机 + 烘干机 + 洗衣房插座）", rooms=["洗衣房"], br="B32 RCBO 30mA", cable="4 mm² 径向 32A", note="两台同时用约 4.5 kW"),
]
WP = [
    dict(id="WP1", name="烤箱", br="B20 RCBO 30mA", cable="2.5 mm² 径向（> 4.6 kW 的烤箱改 4 mm² / 32A）"),
    dict(id="WP2", name="电梯", br="按电梯厂家要求（常见 B16–B20）", cable="按厂家", note="厂家通常要求独立隔离开关"),
    dict(id="WP3", name="空调 1", br="按空调型号（常见 B16）", cable="2.5 mm²（按型号复核）", note="书房（卧室 3）北墙，见二层插座图「高」"),
    dict(id="WP4", name="空调 2", br="按空调型号（常见 B16）", cable="2.5 mm²（按型号复核）", note="卧室 4 南墙（2026-10-06 改到南墙），见二层插座图「高」"),
    dict(id="WP5", name="充电桩（门口）", br="B32/B40 RCBO Type A + 直流漏电保护（或充电桩自带）", cable="6–10 mm²（按距离复核）", note="7 kW；配电箱 → 客厅内充电桩背面墙 40A 双极隔离开关（室内总控，随时可断电）→ 门外充电桩；安装前通知供电公司 DNO；建议加负载管理（CT 互感器）"),
]
ALL_GF = [c["id"] for c in LJ["GF"]["circuits"]]
ALL_FF = [c["id"] for c in LJ["FF"]["circuits"]]
GF_OUT = ["L16", "L17", "L21", "L22"]                # back-garden wall lights p, fence lights q, wall lights u, v (porch c stays with the front)
GF_FRONT = ["L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L9", "L14"]
GF_BACK = ["L10", "L11", "L12", "L13", "L15", "L18", "L19", "L20"]
GF_IN = [c for c in ALL_GF if c not in GF_OUT]
PLANS = {
    "A": dict(name="方案 A · 专业 18 路", short="专业 18 路",
        lighting=[dict(id="WL1", floor="GF", name="一层前区照明（门廊 / 门厅 / 起居室 / 餐厅 / 楼梯）", br="B6 1P+N RCBO 30mA", circ=GF_FRONT, note="约 400 W"),
                  dict(id="WL2", floor="GF", name="一层后区照明（客厅 / 卫生间 / 厨房 / 吧台 / 洗衣房）+ 卫生间排气扇", br="B6 1P+N RCBO 30mA", circ=GF_BACK, note="约 280 W"),
                  dict(id="WL3", floor="GF", name="户外照明（后花园壁灯 / 围栏地灯）", br="B6 1P+N RCBO 30mA", circ=GF_OUT, note="约 60 W；户外易进水，单独一路"),
                  dict(id="WL4", floor="FF", name="二层照明 + 卫生间排气扇", br="B6 1P+N RCBO 30mA", circ=ALL_FF, note="约 320 W")],
        WX=GF_X + [
            dict(id="WX5", floor="FF", name="主卧插座（主卧 / 北卫 / 走廊 / 楼梯 / 电梯旁）", rooms=["主卧", "卫生间#0", "走廊", "楼梯", "电梯"], br="B32 RCBO 30mA", cable=RING, note="一个电脑 + 电视房间"),
            dict(id="WX6", floor="FF", name="卧室 2 插座（卧室 2 / 衣帽间 / 盥洗室 / 西卫）", rooms=["卧室 2", "衣帽间", "盥洗室", "卫生间#2"], br="B32 RCBO 30mA", cable=RING, note="一个电脑 + 电视房间；电热毛巾架接这里"),
            dict(id="WX7", floor="FF", name="书房 1 插座（卧室 3）", rooms=["卧室 3"], br="B32 RCBO 30mA", cable=RING, note="电脑 + 电视，单独一路"),
            dict(id="WX8", floor="FF", name="卧室 4 插座（卧室 4 / 套卫）", rooms=["卧室 4", "卫生间#10"], br="B32 RCBO 30mA", cable=RING, note="后房间 2026-10-06 由书房改卧室；电视 + 空调高位插座"),
            dict(id="WX9", floor="GF", name="户外插座（前院 + 后花园）", rooms=[], br="B32 RCBO 30mA", cable="4 mm² 径向 32A，出户段 SWA 铠装电缆", note="户外易进水，单独一路；32A 留给花园大功率工具"),
        ], outdoor="WX9", WP=WP, fridge="WX3",
        board=dict(model="British General CF236MS31", ways=31, price=169.99, code="547EF", url="https://www.screwfix.com/p/british-general-36-module-31-way-part-populated-high-integrity-main-switch-consumer-unit-with-spd/547ef",
                   spd="40kA Type 2 SPD（自带）", size="宽 387 × 高 483 × 深 116 mm（双排，先量楼梯下位置）",
                   main="100A 总闸", rcbo=RCBO, reserve="预留 1 位：大功率工具 32A 径向（位置待定）",
                   alt="单排替代 MK Sentry 21 位（YS5721SMET，518 × 261 mm）：装完只剩 2 个备用"),
        diff=["照明 4 路：一层前区、一层后区、户外、二层，各自一路",
              "二层插座 4 路：主卧、卧室 2、书房、卧室 4 各一路",
              "户外插座 32A（可用花园大功率工具）",
              "冰箱接厨房插座（经带保险开关）",
              "配电箱 31 位双排，剩 12 个备用"],
        pros=["每个「电脑 + 电视」房间独立：不会因漏电累加误跳，哪里出事只断哪里",
              "照明 4 路：一层前后分开、户外单独，一路跳闸不会整层黑",
              "户外 32A、烤箱和两台空调都单独，以后换大功率电器不用改线",
              "31 位箱还剩 12 个备用：加太阳能、电池、热泵、第 3 台空调都不用换箱"],
        cons=["配电箱高 483 mm（双排），先确认楼梯下放得下",
              "冰箱和厨房插座同一路：厨房电器出问题跳闸时冰箱也断电",
              "进箱的线多，接线整理和 EICR 检测项目略多",
              "部分回路功率上「大材小用」（书房、卧室 32A 环路，实际约 1 kW）"]),
    "B": dict(name="方案 B · 精简 17 路", short="精简 17 路",
        lighting=[dict(id="WL1", floor="GF", name="一层照明（门廊 / 门厅 / 起居室 / 餐厅 / 楼梯 / 客厅 / 卫生间 / 厨房 / 洗衣房）+ 卫生间排气扇", br="B10 1P+N RCBO 30mA", circ=GF_IN,
                       note="约 680 W；B10 防几十个 LED 同时开灯误跳"),
                  dict(id="WL3", floor="GF", name="户外照明（后花园壁灯 / 围栏地灯）", br="B6 1P+N RCBO 30mA", circ=GF_OUT, note="约 60 W；户外进水只断户外灯，一楼不会黑"),
                  dict(id="WL4", floor="FF", name="二层照明 + 卫生间排气扇", br="B6 1P+N RCBO 30mA", circ=ALL_FF, note="约 320 W")],
        WX=GF_X + [
            dict(id="WX5", floor="GF", name="户外插座（前院 + 后花园）", rooms=[], br="B20 RCBO 30mA", cable="2.5 mm² 径向 20A，出户段 SWA 铠装电缆", note="插头式电动工具最大 13A，20A 够用"),
            dict(id="WX6", floor="FF", name="书房 + 卧室 4 + 走廊插座（卧室 3 / 卧室 4 / 走廊 / 套卫）", rooms=["卧室 3", "卧室 4", "走廊", "卫生间#10"], br="B20 RCBO 30mA",
                 cable=RAD20 + "；书房、卧室 4 各拉一根线回配电箱，现在接同一个 RCBO", note="后房间改卧室后只剩一台电脑，漏电余量比原来两个书房宽；误跳时把一根线挪到备用位即可拆开"),
            dict(id="WX7", floor="FF", name="主卧插座（主卧 / 北卫 / 楼梯 / 电梯旁）", rooms=["主卧", "卫生间#0", "楼梯", "电梯"], br="B20 RCBO 30mA", cable=RAD20, note="电脑 + 电视"),
            dict(id="WX8", floor="FF", name="次卧插座（卧室 2 / 衣帽间 / 盥洗室 / 西卫）", rooms=["卧室 2", "衣帽间", "盥洗室", "卫生间#2"], br="B20 RCBO 30mA", cable=RAD20, note="电脑 + 电视；电热毛巾架经带保险开关接这里"),
        ], outdoor="WX5", fridge="WP6",
        WP=WP + [dict(id="WP6", name="冰箱", br="B16 RCBO 30mA", cable="2.5 mm² 径向", note="单独一路：别处跳闸冰箱不断电")],
        board=dict(model="British General CF22MS19-01", ways=19, price=79.99, code="562CY", url="https://www.screwfix.com/p/british-general-22-module-19-way-part-populated-high-integrity-main-switch-consumer-unit-with-spd/562cy",
                   spd="40kA Type 2 SPD（自带）", size="宽 496 × 高 231 × 深 116 mm（单排）",
                   main="100A 总闸", rcbo=RCBO, reserve="预留 1 位：书房 / 卧室 4 以后拆成两路（现在各拉一根线，接在同一个 RCBO 上）",
                   alt="充电桩若由安装商单独配小箱，主箱再空出 1–2 位；以后想加太阳能 + 电池，换 British General CF236MS31（31 位，贵 £90）"),
        diff=["照明 3 路：一层合成一路（前后不分），户外单独，二层一路",
              "二层插座 3 路：书房 + 卧室 4 + 走廊合一路，主卧、次卧各一路（20A 径向）",
              "户外插座 20A",
              "冰箱单独一路（别处跳闸冰箱不断电）",
              "配电箱 19 位单排，剩 1 个备用（充电桩另配小箱则剩 3 个）"],
        pros=["按实际用量配：有电脑的房间用 20A 径向，线只拉单程，不「大材小用」",
              "配电箱小一半（单排 496 × 231 mm），材料更省",
              "户外灯单独一路、冰箱单独一路：B 最怕的两个问题已经补上",
              "书房、卧室 4 已各拉一根线，以后误跳挪一根线就能拆开，不用开墙"],
        cons=["一层照明只有一路：一层任何一盏灯出问题，一楼室内灯一起灭",
              "书房和卧室 4 合一路：两边同时开电脑、电视，漏电余量变小，偶尔可能误跳",
              "户外 20A：以后要固定接线的大型工具，需要另拉专线",
              "19 位箱只剩 1 个备用：以后加太阳能 / 电池很可能要换箱"]),
}


# ---------------- socket points from the PPT ----------------
def fit(slide, F):
    """affine from this slide's coordinates to the floor frame, fitted on shared wall shapes"""
    sv = collections.defaultdict(list)
    for n, p in re.findall(r'data-name="([^"]+)" d="([^"]+)"', open(os.path.join(HERE, f"walls_{F}.svg"), encoding="utf-8").read()):
        a = np.array(list(map(float, re.sub('[MLZ]', ' ', p).split()))).reshape(-1, 2); sv[n].append((a.min(0) + a.max(0)) / 2)
    walls = collections.defaultdict(list)
    for x, T, par in _ns["walk"](slide.shapes, lambda a, b: (a, b)):
        if x.name.startswith("墙_") and x.shape_type != 6 and x._element.find('.//' + A + 'xfrm') is not None:
            d = _ns["xf"](x._element.spPr); walls[x.name].append(_ns["placer"](T, d, False)(d['ox'] + d['ex'] / 2, d['oy'] + d['ey'] / 2))
    P = [walls[n][0] for n in walls if len(walls[n]) == 1 and len(sv.get(n, [])) == 1]
    Q = [sv[n][0] for n in walls if len(walls[n]) == 1 and len(sv.get(n, [])) == 1]
    M = np.c_[np.array(P), np.ones(len(P))]; sol, *_ = np.linalg.lstsq(M, np.array(Q), rcond=None)
    err = np.linalg.norm(M @ sol - np.array(Q), axis=1).max()
    assert err < 50, f"{F}: wall fit error {err}"
    return lambda x, y: tuple(float(v) for v in np.array([x, y, 1.0]) @ sol)


def fill_of(s):
    m = re.search(r'<a:solidFill>(.*?)</a:solidFill>', s._element.spPr.xml, re.S)
    return re.search(r'(?:srgbClr|schemeClr) val="(\w+)"', m.group(1)).group(1) if m else ""


pr = Presentation(PPT)
KIND = {"bg2": "double", "tx2": "single", "FFFF00": "outdoor"}
OUT = {}
for F, si in (("GF", 3), ("FF", 7)):
    sl = pr.slides[si - 1]; T = fit(sl, F)
    vb = LJ[F]["units"]["view_box"]
    pts = []
    for s in sl.shapes:
        if not s.name.startswith("Oval"): continue
        x, y = T(s.left + s.width / 2, s.top + s.height / 2)
        if not (vb[0] <= x <= vb[0] + vb[2] and vb[1] <= y <= vb[1] + vb[3]): continue   # legend dots on the right
        txt = s.text_frame.text.strip() if s.has_text_frame else ""
        pts.append(dict(kind="high" if txt == "高" else KIND.get(fill_of(s), "double"), x=round(x), y=round(y)))
    OUT[F] = dict(pts=pts, T=T, slide=sl)

def _t2b(F, x, y):
    M = np.array(json.load(open(os.path.join(HERE, f"b2t_{F}.json"))))
    v = np.linalg.solve(np.array([[M[0][0], M[1][0]], [M[0][1], M[1][1]]]), np.array([x - M[2][0], y - M[2][1]]))
    return float(v[0]), float(v[1])


# 2026-10-07 audit: sockets on a party wall whose nearest label is the wrong room (checked on the plan, Blender metres)
ROOM_FIX = {"FF": {(2.26, 6.23, "d"): "卧室 3", (-0.02, 5.70, "s"): "卧室 3", (-0.38, 7.75, "d"): "卧室 3",   # were 楼梯 / 电梯 / 北卫 → WX5
                   (-0.91, 1.49, "d"): "主卧",                                                                 # was 盥洗室 → WX6
                   # label only (same circuit): no sockets inside the bathrooms
                   (1.40, 2.00, "d"): "卧室 2", (3.22, 10.31, "d"): "卧室 4", (-3.56, 7.79, "d"): "主卧"},
            "GF": {(-0.36, 7.43, "d"): "餐厅",                                                                  # was 卫生间 → WX2
                   (-0.89, 6.08, "s"): "客厅", (-4.09, 7.26, "d"): "客厅",
                   (2.79, 3.50, "d"): "起居室", (2.73, 2.92, "d"): "起居室", (2.75, 2.27, "d"): "起居室"}}
# the two high sockets are the air-conditioner outlets on their own circuits (WP3 卧室 3, WP4 卧室 4)
HIGH_WP = {"卧室 3": "WP3", "卧室 4": "WP4"}
# room of each socket = nearest room label (labels sit mid-room); its circuit in each plan (outdoor dots -> the plan's outdoor circuit)
for F in ("GF", "FF"):
    rooms = LJ[F]["rooms"]
    keyof = lambda i: rooms[i]["name"] if sum(r["name"] == rooms[i]["name"] for r in rooms) == 1 else f"{rooms[i]['name']}#{i}"
    for p in OUT[F]["pts"]:
        if p["kind"] == "outdoor":
            p["room"], k = "户外", None
        else:
            i = min(range(len(rooms)), key=lambda i: math.dist((rooms[i]["x"], rooms[i]["y"]), (p["x"], p["y"])))
            p["room"], k = rooms[i]["name"], keyof(i)
        bx, by = _t2b(F, p["x"], p["y"])
        for (fx, fy, fk), rk in ROOM_FIX.get(F, {}).items():
            if math.dist((bx, by), (fx, fy)) < 0.08:
                p["room"], k = rk.split("#")[0], rk
        p["c"] = {}
        for pid, pl in PLANS.items():
            p["c"][pid] = pl["outdoor"] if k is None else {r: c["id"] for c in pl["WX"] if c["floor"] == F for r in c["rooms"]}.get(k)
            if p["kind"] == "high" and p["room"] in HIGH_WP: p["c"][pid] = HIGH_WP[p["room"]]
            assert p["c"][pid], f"{pid} {F}: no socket circuit for room {k}"

# ---------------- dedicated points (same circuit ids in both plans, except the fridge) ----------------
# dishwasher = the kitchen FCU nearest the 洗碗机 label of the water page (slide 4, same rotated layout as slide 3)
sl4 = pr.slides[3]; T4 = fit(sl4, "GF"); dw = None
for x, T, par in _ns["walk"](sl4.shapes, lambda a, b: (a, b)):
    if x.has_text_frame and x.text_frame.text.strip() == "洗碗机":
        d = _ns["xf"](x._element.spPr); dw = T4(*_ns["placer"](T, d, False)(d['ox'] + d['ex'] / 2, d['oy'] + d['ey'] / 2))
fc = {f["id"]: f for f in LJ["GF"]["fcus"]}
kitchen = sorted([f for f in fc.values() if f["x"] < 10.2e6], key=lambda f: math.dist((f["x"], f["y"]), dw))
laundry = [f for f in fc.values() if f["x"] >= 10.2e6]
DED = [dict(c="WX3", label="洗碗机", fcu=kitchen[0]["id"], x=kitchen[0]["x"], y=kitchen[0]["y"], floor="GF"),
       dict(c="WP1", label="烤箱", fcu=kitchen[1]["id"], x=kitchen[1]["x"], y=kitchen[1]["y"], floor="GF", tbc="烤箱 / 冰箱哪个 FCU 待现场定"),
       dict(c={p: PLANS[p]["fridge"] for p in PLANS}, label="冰箱", fcu=kitchen[2]["id"], x=kitchen[2]["x"], y=kitchen[2]["y"], floor="GF", tbc="烤箱 / 冰箱哪个 FCU 待现场定")]
for f, lab in zip(sorted(laundry, key=lambda f: f["x"]), ("洗衣机", "烘干机")):
    DED.append(dict(c="WX4", label=lab, fcu=f["id"], x=f["x"], y=f["y"], floor="GF"))
lift = [(a + b) / 2 for a, b in zip(*[[float(v) for v in re.sub('[MLZ]', ' ', p).split()][:2] for p in
        re.findall(r'data-name="墙_Lift_Guide_Duo_-?1" d="([^"]+)"', open(os.path.join(HERE, "walls_GF.svg"), encoding="utf-8").read())])]
DED.append(dict(c="WP2", label="电梯（控制柜位置待厂家定）", x=round(lift[0]), y=round(lift[1]), floor="GF"))
door = [d for d in LJ["GF"]["doors"] if "Front Entrance Door_UpperPanel" in d["name"]][0]["pts"]
dx, dy = min(p[0] for p in door), sum(p[1] for p in door) / len(door)
_M = json.load(open(os.path.join(HERE, "b2t_GF.json")))
_b2t = lambda x, y: (round(x * _M[0][0] + y * _M[1][0] + _M[2][0]), round(x * _M[0][1] + y * _M[1][1] + _M[2][1]))
# 2026-10-07 (user sketch): charger by the side-lounge (副客厅) front door in the recess west of it (old-window infill face, Blender -3.38, 1.20), car-wash tap FT
# beside it; indoor double-pole isolator ("power control") on the 客厅 side of that infill wall (-3.40, 1.65)
DED.append(dict(c="WP5", label="充电桩（副客厅前门西侧凹进处外墙，离地约 1.0 m）", x=_b2t(-3.38, 1.20)[0], y=_b2t(-3.38, 1.20)[1], floor="GF"))
DED.append(dict(c="WP5", label="充电桩室内控制开关（40A 双极隔离开关，客厅内充电桩背面墙，离地 1.2 m）", x=_b2t(-3.40, 1.65)[0], y=_b2t(-3.40, 1.65)[1], floor="GF"))

for d in DED:
    if not isinstance(d["c"], dict): d["c"] = {p: d["c"] for p in PLANS}
data = {F: dict(sockets=OUT[F]["pts"], items=[d for d in DED if d["floor"] == F]) for F in ("GF", "FF")}
data["plans"] = {"B": PLANS["B"]}; data["default"] = "B"; data["rev"] = "2026-10-08 · 方案 B（精简 17 路）"   # owner 2026-10-08: plan A dropped from the web pages
for F in ("GF", "FF"):
    json.dump(data[F], open(os.path.join(HERE, f"power_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(PLANS, open(os.path.join(HERE, "power_plans.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
if os.path.exists(os.path.join(HERE, "power_circuits.json")):
    os.remove(os.path.join(HERE, "power_circuits.json"))
open(os.path.join(HERE, "power_data.js"), "w", encoding="utf-8").write(
    "// generated by build_power.py (sockets from v10 PPT slides 3 / 7 + plans A / B)\nwindow.POWER_DEFAULT = " + json.dumps(data, ensure_ascii=False) + ";\n")
for pid in PLANS:
    for F in ("GF", "FF"):
        print(pid, F, dict(sorted(collections.Counter(p["c"][pid] for p in OUT[F]["pts"]).items())))
