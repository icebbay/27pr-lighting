"""Sockets + dedicated circuits (20-way plan agreed 2026-10-03) -> power_GF/FF.json + power_data.js for power.html / board.html.

Board AL1 = 7 lighting (WL, from lighting_<F>.json) + 6 socket circuits (WX) + 7 dedicated circuits (WP) + 3 spare.
Socket points: the user's coloured dots on the socket pages of the v6 PPT (slide 3 GF, slide 7 FF; olive = double,
blue = single, yellow = outdoor, "高" = high level). Those pages show the plan rotated 90° and scaled; the transform into the
lighting tool's frame (slide EMU of walls_<F>.svg) is fitted on the wall shapes both pages share (error <= 1 EMU).

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\build_power.py
"""
import json, math, os, re, collections
import numpy as np
from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
PPT = os.path.join(HERE, "..", "source_pptx", "Blender模型户型图_灯_插座_水路_可编辑_v6_照明控制图_专业版.pptx")
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
_src = open(os.path.join(HERE, "export_lighting_json.py"), encoding="utf-8").read()
_ns = {"math": math, "A": A}
exec(_src[_src.index("def xf(el):"):_src.index("def shape_paths")], _ns)   # xf / placer / walk: group transforms
LJ = {F: json.load(open(os.path.join(HERE, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
REV = "2026-10-03 · 18 路专业方案"
# one "computer + TV" room per socket circuit: each PC / TV leaks 1–5 mA to earth, and BS 7671 keeps the standing leakage
# on a 30 mA RCBO under 30 % (9 mA); a ring serves <= 100 m²; kitchen and laundry on their own (IET On-Site Guide)
RING = "2.5 mm² 环路（ring，≤ 100 m²）"
BOARD = dict(model="British General CF236MS31", ways=31, spd="40kA Type 2 SPD（自带）", size="宽 387 × 高 483 × 深 116 mm（双排，先量楼梯下位置）",
             main="100A 总闸", rcbo="BG 单模块 RCBO（Type A 30 mA），约 £11–17 / 个", reserve="预留 1 位：大功率工具 32A 径向（位置待定）")

# ---------------- circuits ----------------
# rooms are matched by label index in lighting_<F>.json["rooms"] (names repeat: 储物间 ×3, 卫生间 ×3)
WX = [
    dict(id="WX1", floor="GF", name="一层前区插座（起居室 / 餐厅 / 门厅 / 楼梯）", rooms=["起居室", "餐厅", "储物间#4", "储物间#6", "楼梯"], br="B32 RCBO 30mA", cable=RING, note="起居室电视"),
    dict(id="WX2", floor="GF", name="一层客厅插座（客厅 / 卫生间）", rooms=["客厅", "卫生间", "储物间#12"], br="B32 RCBO 30mA", cable=RING, note="客厅电视"),
    dict(id="WX3", floor="GF", name="厨房插座（厨房 / 吧台区，含冰箱、洗碗机、燃气灶点火）", rooms=["厨房", "厨房（吧台区）"], br="B32 RCBO 30mA", cable="4 mm² 径向 32A（或 2.5 mm² 环路）", note="电水壶等集中在这里，单独一路"),
    dict(id="WX4", floor="GF", name="洗衣房（洗衣机 + 烘干机 + 洗衣房插座）", rooms=["洗衣房"], br="B32 RCBO 30mA", cable="4 mm² 径向", note="两台同时用约 4–5 kW，不和厨房合用"),
    dict(id="WX5", floor="FF", name="主卧插座（主卧 / 北卫 / 走廊 / 楼梯 / 电梯旁）", rooms=["主卧", "卫生间#0", "走廊", "楼梯", "电梯"], br="B32 RCBO 30mA", cable=RING, note="一个电脑 + 电视房间"),
    dict(id="WX6", floor="FF", name="卧室 2 插座（卧室 2 / 衣帽间 / 盥洗室 / 西卫）", rooms=["卧室 2", "衣帽间", "盥洗室", "卫生间#2"], br="B32 RCBO 30mA", cable=RING, note="一个电脑 + 电视房间；电热毛巾架接这里"),
    dict(id="WX7", floor="FF", name="书房 1 插座（卧室 3）", rooms=["卧室 3"], br="B32 RCBO 30mA", cable=RING, note="电脑 + 电视，单独一路防漏电累加误跳"),
    dict(id="WX8", floor="FF", name="书房 2 插座（书房 / 后卫）", rooms=["书房", "卫生间#10"], br="B32 RCBO 30mA", cable=RING, note="电脑 + 电视，单独一路防漏电累加误跳"),
    dict(id="WX9", floor="GF", name="户外插座（前院 + 后花园）", rooms=[], br="B32 RCBO 30mA", cable="4 mm² 径向 32A，出户段 SWA 铠装电缆", note="户外易进水，单独一路；32A 够用花园电动工具"),
]
WP = [
    dict(id="WP1", name="烤箱", br="B20 RCBO 30mA", cable="4 mm² 径向（按烤箱功率复核）"),
    dict(id="WP2", name="电梯", br="按电梯厂家要求（常见 B16–B20）", cable="按厂家", note="厂家通常要求独立隔离开关"),
    dict(id="WP3", name="空调 1", br="按空调型号（常见 B16–B20）", cable="2.5 mm²（按型号复核）", note="位置待定"),
    dict(id="WP4", name="空调 2", br="按空调型号（常见 B16–B20）", cable="2.5 mm²（按型号复核）", note="位置待定"),
    dict(id="WP5", name="充电桩（门口）", br="B32/B40 RCBO Type A + 直流漏电保护（或充电桩自带）", cable="6–10 mm²（按距离复核）", note="7 kW；安装前通知供电公司 DNO；建议加负载管理"),
]


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

# room of each socket = nearest room label (labels sit mid-room); outdoor dots go to WX9
for F in ("GF", "FF"):
    rooms = LJ[F]["rooms"]
    keyof = lambda i: rooms[i]["name"] if sum(r["name"] == rooms[i]["name"] for r in rooms) == 1 else f"{rooms[i]['name']}#{i}"
    circ_of = {r: c["id"] for c in WX if c["floor"] == F for r in c["rooms"]}
    for p in OUT[F]["pts"]:
        if p["kind"] == "outdoor": p["room"], p["c"] = "户外", "WX9"; continue
        i = min(range(len(rooms)), key=lambda i: math.dist((rooms[i]["x"], rooms[i]["y"]), (p["x"], p["y"])))
        p["room"] = rooms[i]["name"]; p["c"] = circ_of.get(keyof(i))
        assert p["c"], f"{F}: no socket circuit for room {keyof(i)}"

# ---------------- dedicated points ----------------
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
       dict(c="WX3", label="冰箱", fcu=kitchen[2]["id"], x=kitchen[2]["x"], y=kitchen[2]["y"], floor="GF", tbc="烤箱 / 冰箱哪个 FCU 待现场定")]
for f, lab in zip(sorted(laundry, key=lambda f: f["x"]), ("洗衣机", "烘干机")):
    DED.append(dict(c="WX4", label=lab, fcu=f["id"], x=f["x"], y=f["y"], floor="GF"))
lift = [(a + b) / 2 for a, b in zip(*[[float(v) for v in re.sub('[MLZ]', ' ', p).split()][:2] for p in
        re.findall(r'data-name="墙_Lift_Guide_Duo_-?1" d="([^"]+)"', open(os.path.join(HERE, "walls_GF.svg"), encoding="utf-8").read())])]
DED.append(dict(c="WP2", label="电梯（控制柜位置待厂家定）", x=round(lift[0]), y=round(lift[1]), floor="GF"))
door = [d for d in LJ["GF"]["doors"] if "Front Entrance Door_UpperPanel" in d["name"]][0]["pts"]
dx, dy = min(p[0] for p in door), sum(p[1] for p in door) / len(door)
DED.append(dict(c="WP5", label="充电桩（门口，位置示意）", x=round(dx - 0.9 * LJ["GF"]["units"]["emu_per_m"]), y=round(dy), floor="GF"))

data = {}
for F in ("GF", "FF"):
    data[F] = dict(sockets=OUT[F]["pts"], items=[d for d in DED if d["floor"] == F])
data["circuits"] = dict(WX=WX, WP=WP, spare=BOARD["ways"], board=BOARD, rev=REV)
for F in ("GF", "FF"):
    json.dump(data[F], open(os.path.join(HERE, f"power_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(data["circuits"], open(os.path.join(HERE, "power_circuits.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(os.path.join(HERE, "power_data.js"), "w", encoding="utf-8").write(
    "// generated by build_power.py (sockets from v6 PPT slides 3 / 7 + 20-way circuit plan)\nwindow.POWER_DEFAULT = " + json.dumps(data, ensure_ascii=False) + ";\n")
for F in ("GF", "FF"):
    c = collections.Counter((p["c"], p["room"]) for p in OUT[F]["pts"])
    print(F, len(OUT[F]["pts"]), "sockets:", dict(sorted(c.items())))
print("dedicated:", [(d["c"], d["label"], d.get("fcu")) for d in DED])
