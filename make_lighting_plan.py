"""Build a professional GF lighting & switching plan from the user's annotated PPT v4 (slide 2).

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\make_lighting_plan.py

Adds two slides and saves Blender模型户型图_灯_插座_水路_可编辑_v5_照明控制图.pptx next to v4 (v4 untouched):
  1. 一层照明控制平面图: user's rotated plan (walls, rooms, light symbols), switch symbols at the mounting dots,
     dashed switch-leg arcs from each key to the lights of its circuit, one colour per circuit, 2W/3W tags.
  2. 一层照明回路表: circuit schedule (circuit / lights / keys / switch locations / single, 2-way, 3-way / notes).
Circuit list = the user's colour frames on slide 2, read on 2026-10-03 (keys 28 and 38 still to confirm).
"""
import math, copy
from pptx import Presentation
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR

import os
FLOOR = os.environ.get("FLOOR", "GF")   # GF = ground floor (v4 slide 2); FF = first floor (v6 slide 6, user-marked 10-03)
if FLOOR == "FF":
    SRC = r"C:\Users\jcjia\Downloads\Blender模型户型图_灯_插座_水路_可编辑_v6_照明控制图_专业版.pptx"
    SLIDE, PLAN_GROUP, M_BASE = 5, "二层平面（横向）", 405900
else:
    SRC = r"C:\Users\jcjia\Downloads\Blender模型户型图_灯_插座_水路_可编辑_v4.pptx"
    SLIDE, PLAN_GROUP, M_BASE = 1, "Group 536", 247977
DST = r"C:\Users\jcjia\Downloads\Blender模型户型图_灯_插座_水路_可编辑_v5_照明控制图.pptx"
if not os.path.exists(SRC):   # other machines (GitHub copy): the same PPT is kept in source_pptx/ next to this script
    SRC = os.path.join(os.path.dirname(os.path.abspath(globals().get("__file__", "make_lighting_plan.py"))), "source_pptx", os.path.basename(SRC))
p = Presentation(SRC)
src = p.slides[SLIDE]
U = 6096  # 2000-px display unit -> EMU (slide is 12192000 wide)
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'


def xf(g):
    x = g._element.grpSpPr.find(A + 'xfrm'); rot = int(x.get('rot', '0')) / 60000
    o, e, co, ce = [x.find(A + t) for t in ('off', 'ext', 'chOff', 'chExt')]
    return (int(o.get('x')), int(o.get('y')), int(e.get('cx')), int(e.get('cy')),
            int(co.get('x')), int(co.get('y')), int(ce.get('cx')), int(ce.get('cy')), rot)


def mk(T, g):
    ox, oy, ex, ey, cx, cy, cex, cey, rot = xf(g); mx, my = ox + ex / 2, oy + ey / 2; a = math.radians(rot)

    def f(px, py):
        X = ox + (px - cx) * ex / cex; Y = oy + (py - cy) * ey / cey; dx, dy = X - mx, Y - my
        return T(mx + dx * math.cos(a) - dy * math.sin(a), my + dx * math.sin(a) + dy * math.cos(a))
    return f


def walk(shapes, T):
    for x in shapes:
        yield x, T
        if x.shape_type == 6:
            yield from walk(x.shapes, mk(T, x))


# light symbol centres in slide coordinates (the plan group is rotated 90 deg and scaled)
LP = {}
for x, T in walk(src.shapes, lambda a, b: (a, b)):
    if x.name.startswith(("射灯", "主灯", "壁灯", "主灯位", "地灯")):
        if x.shape_type == 6:
            T2 = mk(T, x)
            sym = [y for y in x.shapes if not (y.has_text_frame and y.text_frame.text.strip())]
            y = sym[0] if sym else x
            pt = T2(y.left + y.width / 2, y.top + y.height / 2)
        else:
            pt = T(x.left + x.width / 2, x.top + x.height / 2)
        LP[x.name if x.name not in LP else x.name + "#2"] = pt   # FF has two F11 and two 衣帽间 symbols

MOUNT = {k: (a * U, b * U) for k, (a, b) in {
    "双联开关 1": (452, 950), "四联开关 3": (329, 896), "三联开关 2": (690, 833), "三联开关 1": (735, 867),
    "四联开关 4": (719, 915), "四联开关 2": (460, 312), "四联开关 1": (694, 527), "单联开关 1": (1035, 717),
    "单联开关 2": (942, 438), "风扇隔离开关 1": (992, 444), "双联开关 3": (1035, 271), "单联开关 3": (1277, 769),
    "双联开关 2": (1098, 850), "单联开关 4": (1704, 852), "单联开关 5": (1785, 852), "单联开关 6": (735, 1019),
    "带保险插座开关 1": (1596, 1023), "带保险插座开关 2": (1540, 1033), "带保险插座开关 3": (1327, 1023),
    "带保险插座开关 4": (1769, 1019), "带保险插座开关 5": (1717, 1015)}.items()}
PANEL = {"双联开关 1": (2, ["1", "2"]), "四联开关 3": (4, ["3", "4", "5", "6"]), "三联开关 2": (3, ["23", "24", "25"]),
         "三联开关 1": (3, ["7", "8", "9"]), "四联开关 4": (4, ["18", "19", "20", "21"]),
         "四联开关 2": (4, ["14", "15", "16", "17"]), "四联开关 1": (4, ["10", "11", "12", "13"]),
         "单联开关 1": (1, ["28"]), "单联开关 2": (1, ["22"]), "风扇隔离开关 1": (0, ["29"]),
         "双联开关 3": (2, ["26", "27"]), "单联开关 3": (2, ["26", "27"]), "双联开关 2": (2, ["31", "32"]),
         "单联开关 4": (1, ["38"]), "单联开关 5": (1, ["40"]), "单联开关 6": (1, ["30"])}
KEY2PANEL = {}
for pn, (g, ks) in PANEL.items():
    for k in ks:
        KEY2PANEL.setdefault(k, []).append(pn)


def C(*n):
    return [f"射灯 GU10_GF_{x}" for x in n]


CIRC = [("L1", "G08 吊灯（储物间旁）", ["1"], ["主灯 G08"]),
        ("L2", "前储物间筒灯", ["2"], C("储物间_1")),
        ("L3", "G25 门廊壁灯", ["3"], ["壁灯 G25"]),
        ("L4", "G06 起居室主灯", ["4", "19"], ["主灯 G06"]),
        ("L5", "起居室筒灯（上两组）", ["5", "20"], C("电梯井_1", "起居室_4", "起居室_5", "起居室_6")),
        ("L6", "起居室筒灯（右、下）", ["6", "21"], C("起居室_1", "起居室_7", "起居室_2", "起居室_3")),
        ("L7", "G07 餐厅主灯", ["7", "23"], ["主灯 G07"]),
        ("L8", "餐厅筒灯（上排+左）", ["8", "24"], C("餐厅_3", "餐厅_4", "餐厅_5", "餐厅_6")),
        ("L9", "餐厅筒灯（右+下排）", ["9", "25"], C("餐厅_7", "餐厅_9", "餐厅_2", "餐厅_1")),
        ("L10", "G15 吊灯", ["10", "14"], ["主灯 G15"]),
        ("L11", "G16 吊灯", ["11", "15"], ["主灯 G16"]),
        ("L12", "北间筒灯（上排+左）", ["12", "16", "28"], C("客厅_3", "客厅_4", "客厅_5", "客厅_6")),
        ("L13", "北间筒灯（下排+右）", ["13", "17"], C("客厅_7", "客厅_11", "客厅_2", "客厅_1")),
        ("L14", "F32 楼梯壁灯", ["18"], ["壁灯 F32"]),
        ("L15", "卫生间筒灯", ["22"], C("客厅_13")),
        ("L16", "G26_2 / G26_3 后花园壁灯", ["26"], ["壁灯 G26_2", "壁灯 G26_3"]),
        ("L17", "围栏地灯 ×5", ["27"], sorted(n for n in LP if n.startswith("地灯"))),
        ("L18", "厨房吧台区吊灯（待选）", ["31"], ["主灯位待选 主灯待选_厨房吧台区"]),
        ("L19", "厨房主灯（待选）", ["32"], ["主灯位待选 主灯待选_厨房"]),
        ("L20", "洗衣房筒灯", ["38"], C("洗衣房_1")),
        ("L21", "G26_1 后花园壁灯", ["40"], ["壁灯 G26_1"])]
if FLOOR == "FF":
    MOUNT = {k: (a * U, b * U) for k, (a, b) in {
        "单联开关 1": (1056, 315), "双联开关 1": (829, 465), "单联开关 2": (646, 538), "单联开关 3": (938, 579),
        "单联开关 4": (973, 656), "单联开关 5": (792, 771), "单联开关 6": (435, 760), "单联开关 6B": (507, 650),
        "风扇隔离开关 1": (521, 706), "双联开关 2": (460, 1065), "双联开关 3": (827, 902), "双联开关 4": (1000, 912),
        "单联开关 7": (1140, 906), "单联开关 8": (1242, 883), "单联开关 9": (1446, 788), "风扇隔离开关 2": (1500, 835)}.items()}
    PANEL = {"单联开关 1": (1, ["1"]), "双联开关 1": (2, ["10", "11"]), "单联开关 2": (1, ["2"]), "单联开关 3": (1, ["3"]),
             "单联开关 4": (1, ["4"]), "单联开关 5": (1, ["5"]), "单联开关 6": (1, ["6"]), "单联开关 6B": (1, ["6+"]),
             "风扇隔离开关 1": (0, ["18"]), "双联开关 2": (2, ["12", "13"]), "双联开关 3": (2, ["14", "15"]),
             "双联开关 4": (2, ["16", "17"]), "单联开关 7": (1, ["7"]), "单联开关 8": (1, ["8"]), "单联开关 9": (1, ["9"]),
             "风扇隔离开关 2": (0, ["19"])}
    KEY2PANEL = {}
    for pn, (g, ks) in PANEL.items():
        for k in ks:
            KEY2PANEL.setdefault(k, []).append(pn)

    def F(*n):
        return [f"射灯 GU10_FF_{x}" for x in n]

    CIRC = [("L1", "主卧主灯 F19", ["2", "10"], ["主灯 F19"]),
            ("L2", "主卧主灯位（待选）", ["11"], ["主灯位待选 主灯待选_主卧"]),
            ("L3", "卫生间筒灯", ["1"], F("卫生间_1")),
            ("L4", "走廊吸顶灯 F11 ×2", ["3", "16"], ["主灯 F11", "主灯 F11#2"]),
            ("L5", "卧室主灯 F22", ["4"], ["主灯 F22"]),
            ("L6", "衣帽间筒灯 ×2", ["5"], ["射灯 GU10_FF_衣帽间_1", "射灯 GU10_FF_衣帽间_1#2"]),
            ("L7", "走廊筒灯（主卫外）", ["6"], F("走廊_2")),
            ("L8", "主卫筒灯", ["6+"], F("主卫_1")),
            ("L9", "卧室2 主灯 F20", ["12", "14"], ["主灯 F20"]),
            ("L10", "卧室2 筒灯 ×2", ["13", "15"], F("卧室2_1", "卧室2_2")),
            ("L11", "楼梯吊灯 F06", ["17", "7"], ["主灯 F06"]),
            ("L12", "书房主灯 F23", ["8"], ["主灯 F23"]),
            ("L13", "后卫生间筒灯", ["9"], F("卧室4_1"))]
PAL = ["E6194B", "3CB44B", "4363D8", "F58231", "911EB4", "0097A7", "F032E6", "9A6324", "800000", "469990",
       "000075", "808000", "C79100", "1B9E77", "D95F02", "7570B3", "E7298A", "66A61E", "A6761D", "1F78B4", "B15928"]
missing = [l for c in CIRC for l in c[3] if l not in LP]
print("lights not found:", missing)

# ---------- slide 1: plan ----------
sl = p.slides.add_slide(src.slide_layout)
for ph in list(sl.placeholders):
    ph._element.getparent().remove(ph._element)
g536 = [x for x in src.shapes if x.name == "Group 536"][0]
sl.shapes._spTree.append(copy.deepcopy(g536._element))


def tb(slide, x, y, w, h, text, size=9, bold=False, color="222222", align=PP_ALIGN.LEFT):
    t = slide.shapes.add_textbox(Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h))); tf = t.text_frame; tf.word_wrap = True
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, 0)
    r = tf.paragraphs[0].add_run(); r.text = text; r.font.size = Pt(size); r.font.bold = bold
    r.font.color.rgb = RGBColor.from_string(color); tf.paragraphs[0].alignment = align
    return t


tb(sl, 320040, 150000, 9000000, 420000, "一层照明控制平面图（开关回路）", 22, True)
tb(sl, 320040, 560000, 11500000, 260000,
   "黑点 + 斜线 = 开关安装点（斜线数 = 联数）；彩色虚线弧 = 开关回路（同色同回路，L 编号见回路表）；"
   "开关旁数字 = 按键编号（沿用第 2 页）；回路号后 2W = 双控、3W = 三控；方框 FCU = 带保险丝开关。", 10, False, "C00000")


def arc(a, b, col, bulge=0.18, w=1.25):
    (x0, y0), (x1, y1) = a, b; mx, my = (x0 + x1) / 2, (y0 + y1) / 2; dx, dy = x1 - x0, y1 - y0
    cx, cy = mx - dy * bulge, my + dx * bulge
    pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)
           for t in [i / 14 for i in range(15)]]
    fb = sl.shapes.build_freeform(int(pts[0][0]), int(pts[0][1]), scale=1.0)
    fb.add_line_segments([(int(u), int(v)) for u, v in pts[1:]], close=False)
    s = fb.convert_to_shape(); s.fill.background(); s.line.color.rgb = RGBColor.from_string(col); s.line.width = Pt(w)
    s.line.dash_style = MSO_LINE_DASH_STYLE.DASH; s.shadow.inherit = False
    return s


def chain(start, targets):
    out, cur, rest = [], start, list(targets)
    while rest:
        n = min(rest, key=lambda t: math.hypot(t[0] - cur[0], t[1] - cur[1])); out.append((cur, n)); cur = n; rest.remove(n)
    return out


for i, (cid, desc, keys, lights) in enumerate(CIRC):
    col = PAL[i % len(PAL)]; pts = [LP[l] for l in lights if l in LP]
    if not pts:
        continue
    starts = [(k, pn) for k in keys for pn in KEY2PANEL.get(k, [])]
    way = len(starts)
    for k, pn in starts:
        m = MOUNT[pn]; first = min(pts, key=lambda t: math.hypot(t[0] - m[0], t[1] - m[1]))
        arc(m, first, col)
    for a, b in chain(min(pts, key=lambda t: math.hypot(t[0] - MOUNT[starts[0][1]][0], t[1] - MOUNT[starts[0][1]][1])), pts):
        if a != b:
            arc(a, b, col, bulge=0.12)
    lx, ly = min(pts, key=lambda t: t[1])
    tb(sl, lx + 60000, ly - 210000, 700000, 150000, cid + (f" {way}W" if way > 1 else ""), 9, True, col)

for pn, (gang, ks) in PANEL.items():
    x, y = MOUNT[pn]; d = 70000
    dot = sl.shapes.add_shape(MSO_SHAPE.OVAL, Emu(int(x - d / 2)), Emu(int(y - d / 2)), Emu(d), Emu(d))
    dot.fill.solid(); dot.fill.fore_color.rgb = RGBColor(0, 0, 0); dot.line.fill.background(); dot.shadow.inherit = False
    for gi in range(max(gang, 1)):
        ln = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Emu(int(x)), Emu(int(y)),
                                     Emu(int(x + 110000 + gi * 32000)), Emu(int(y - 110000 + gi * 22000)))
        ln.line.color.rgb = RGBColor(0, 0, 0); ln.line.width = Pt(1.25)
    lab = "FI 风扇隔离" if gang == 0 else f"{gang}G"
    tb(sl, x + 140000, y - 40000, 900000, 140000, lab + " " + "/".join(ks), 7, False, "000000")
for pn in [k for k in MOUNT if k.startswith("带保险")]:
    x, y = MOUNT[pn]
    s = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(int(x - 45000)), Emu(int(y - 45000)), Emu(90000), Emu(90000))
    s.fill.solid(); s.fill.fore_color.rgb = RGBColor(255, 255, 255); s.line.color.rgb = RGBColor(0, 0, 0)
    s.line.width = Pt(1); s.shadow.inherit = False
    tb(sl, x - 250000, y + 60000, 500000, 130000, "FCU", 7, True, "000000", PP_ALIGN.CENTER)
x, y = MOUNT["单联开关 6"]
arc((x, y), (x - 250000, y - 650000), "808000", bulge=0.1)
tb(sl, x - 1500000, y - 820000, 1500000, 150000, "30 → 至二层楼梯吊灯 F06", 8, True, "808000")
x, y = MOUNT["风扇隔离开关 1"]
tb(sl, x + 40000, y + 70000, 900000, 140000, "29 → 卫生间排气扇", 7, True, "800000")

# ---------- slide 2: schedule ----------
s2 = p.slides.add_slide(src.slide_layout)
for ph in list(s2.placeholders):
    ph._element.getparent().remove(ph._element)
tb(s2, 320040, 150000, 9000000, 420000, "一层照明回路表", 22, True)
NOTE = {"L12": "28 是否参与三控待确认", "L20": "38 控洗衣房筒灯待确认",
        "L16": "洗衣房 + 厨房后门", "L17": "洗衣房 + 厨房后门"}
SHORT = {"单联开关": "1G", "双联开关": "2G", "三联开关": "3G", "四联开关": "4G"}
def short(pn):
    for k, v in SHORT.items():
        if pn.startswith(k): return v + "-" + pn.split()[-1]
    return pn
half = (len(CIRC) + 1) // 2
for part, x0 in ((CIRC[:half], 320040), (CIRC[half:], 6250000)):
    rows = len(part) + 1
    tbl = s2.shapes.add_table(rows, 5, Emu(x0), Emu(650000), Emu(5700000), Emu(rows * 300000)).table
    for j, h in enumerate(["回路", "控制灯具", "开关（按键@面板）", "方式", "备注"]):
        tbl.cell(0, j).text = h
    for i, (cid, desc, keys, lights) in enumerate(part, 1):
        pans = [f"{k}@{short(pn)}" for k in keys for pn in KEY2PANEL.get(k, [])]
        mode = {1: "单控", 2: "双控", 3: "三控"}.get(len(pans), f"{len(pans)}控")
        for j, v in enumerate([cid, desc, "，".join(pans), mode, NOTE.get(cid, "")]):
            tbl.cell(i, j).text = v
    for r_ in range(rows):
        for j in range(5):
            c = tbl.cell(r_, j); c.margin_top = c.margin_bottom = Emu(20000); c.margin_left = c.margin_right = Emu(40000)
            for para in c.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9); run.font.bold = (r_ == 0)
        tbl.rows[r_].height = Emu(300000)
    for j, w in enumerate((450000, 1700000, 1800000, 500000, 1250000)):
        tbl.columns[j].width = Emu(w)
tb(s2, 320040, 650000 + (half + 1) * 300000 + 200000, 11500000, 300000,
   "面板：1G/2G/3G/4G = 单/双/三/四联开关，编号同第 2 页。另：29 = 卫生间排气扇隔离开关；30 = 二层楼梯吊灯 F06；34–37、39 = 带保险丝开关（FCU，供电器）。", 10)
p.save(DST)
print("saved", DST, "slides", len(p.slides))
