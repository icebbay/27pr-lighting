"""GF lighting construction drawing set (UK practice) from the user's annotated PPT v4, slide 2.

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\make_lighting_drawings.py

Output: Downloads\\27PR_一层照明施工图_RevA.pptx (only the drawing sheets; v4/v5/v6 untouched)
  E-GF-00  key plan: whole floor, switch IDs, sheet zones
  E-GF-01..03  enlarged zone plans: lights with circuit letters, numbered switches, short switch legs only,
               two-way strappers drawn between switch pairs (3C+E), cross references instead of long lines
  E-GF-04  switch plate schedule: every plate, location, height, gang-by-gang (left -> right) function, 2-way partner
  E-GF-05  circuit schedule
Circuit data (who controls what) comes from make_lighting_plan.py (user's colour frames on slide 2).
"""
import math, copy, importlib.util
from pptx.util import Emu, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.dml import MSO_LINE_DASH_STYLE
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.oxml.ns import qn
from lxml import etree

_spec = importlib.util.spec_from_file_location("lp", __file__.replace("make_lighting_drawings.py", "make_lighting_plan.py"))
_src = open(_spec.origin, encoding="utf-8").read()
_src = _src[:_src.index("# ---------- slide 1: plan ----------")]
NS = {"__file__": _spec.origin}
exec(compile(_src, _spec.origin, "exec"), NS)
p, src = NS["p"], NS["src"]
LP, MOUNT, PANEL, KEY2PANEL, CIRC, U = NS["LP"], NS["MOUNT"], NS["PANEL"], NS["KEY2PANEL"], NS["CIRC"], NS["U"]
FLOOR = NS["FLOOR"]; M_BASE = NS["M_BASE"]; PLAN_GROUP = NS["PLAN_GROUP"]
FL_CN, FL_EN, FC = ("二层", "FIRST FLOOR", "FF") if FLOOR == "FF" else ("一层", "GROUND FLOOR", "GF")
DST = rf"C:\Users\jcjia\Downloads\27PR_{FL_CN}照明施工图_RevB_英式.pptx"
DST = __import__("os").environ.get("DST_OVERRIDE", DST)
INK = RGBColor(0x1A, 0x1A, 0x1A); WIRE = RGBColor(0x1F, 0x4E, 0x79); GREY = RGBColor(0x80, 0x80, 0x80)
RED = RGBColor(0xC0, 0x00, 0x00); WHITE = RGBColor(255, 255, 255)
W, H = 12192000, 6858000
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'

# ---------------- data ----------------
LET = "abcdefghijklmnopqrstu"
CL = {c[0]: LET[i] for i, c in enumerate(CIRC)}
DESC = {"L1": "门厅吊灯 G08", "L2": "前储物间筒灯（+门控开关）", "L3": "门廊壁灯 G25（户外）", "L4": "起居室主灯 G06",
        "L5": "起居室筒灯 上两排（含电梯旁）", "L6": "起居室筒灯 右列+下排", "L7": "G07 区主灯", "L8": "G07 区筒灯 上排+左",
        "L9": "G07 区筒灯 右+下排", "L10": "G15 吊灯", "L11": "G16 吊灯", "L12": "G15 区筒灯 上排+左",
        "L13": "G15 区筒灯 下排+右", "L14": "楼梯壁灯 F32", "L15": "卫生间筒灯", "L16": "后花园壁灯 G26_2、G26_3",
        "L17": "围栏地灯 ×4（户外）", "L18": "吧台区吊灯（待选）", "L19": "厨房主灯（待选）", "L20": "洗衣房筒灯",
        "L21": "后花园壁灯 G26_1"}
TBC = {}
# Rev B common-sense resolutions (2026-10-03)
ASSUMED = {"L12": "一个回路 4 盏筒灯，S8、S9、S7 三处控制（S7 装中途开关）", "L20": "38 号键控洗衣房筒灯",
           "L17": "围栏地灯按第 2 页为 4 盏（模型多出的 GroundLED_3 删除）", "L2": "前储物间加门控开关：开门亮灯，与 S2 键 2 并联"}
# switch plates: id, PANEL key, location, sheet
PLATES = [("S1", "四联开关 3", "门厅 · 前门内侧", 1), ("S2", "双联开关 1", "门厅 · 前储物间旁", 1),
          ("S3", "三联开关 2", "起居室侧 · 拱门旁", 1), ("S4", "四联开关 4", "楼梯口 · 拱门旁", 1),
          ("S5", "三联开关 1", "G07 区侧 · 拱门旁", 1), ("S6", "单联开关 6", "楼梯底", 1),
          ("S7", "单联开关 1", "G07 区东侧 · 卫生间走道口", 1), ("S8", "四联开关 1", "G15 区南门旁", 2),
          ("S9", "四联开关 2", "G15 区 · 储物间门旁", 2), ("S10", "单联开关 2", "卫生间门外", 2),
          ("S11", "风扇隔离开关 1", "卫生间门外", 2), ("S12", "双联开关 3", "G15 区 · 通后花园门旁", 3),
          ("S13", "单联开关 3", "厨房后门旁（吧台区）", 3), ("S14", "双联开关 2", "厨房入口", 3),
          ("S15", "单联开关 4", "洗衣房门旁", 3), ("S16", "单联开关 5", "洗衣房后门旁", 3)]
FCUS = [("FCU1", "带保险插座开关 3", "37"), ("FCU2", "带保险插座开关 2", "36"), ("FCU3", "带保险插座开关 1", "35"),
        ("FCU4", "带保险插座开关 5", "34"), ("FCU5", "带保险插座开关 4", "39")]
FCU_KEYS = {"带保险插座开关 1": "37", "带保险插座开关 2": "39", "带保险插座开关 3": "36", "带保险插座开关 4": "35", "带保险插座开关 5": "34"}
FCUS = [] if FLOOR == "FF" else [(f"FCU{i+1}", pn, FCU_KEYS[pn]) for i, pn in enumerate(sorted(FCU_KEYS, key=lambda k: MOUNT[k][0]))]
PID = {pn: sid for sid, pn, _, _ in PLATES}
PSHEET = {pn: sh for _, pn, _, sh in PLATES}
KEY_CIRC = {k: c[0] for c in CIRC for k in c[2]}
# sheet zones in 2000-px display units of the user's slide (member = which lights belong; view = what is drawn)
ZONES = {1: dict(name="起居室 · G07 区 · 门厅 · 楼梯", view=(70, 520, 1110, 1085), member=(60, 545, 1085, 1100)),
         2: dict(name="G15 区 · 卫生间 · 储物间", view=(150, 140, 1110, 580), member=(150, 140, 1085, 545)),
         3: dict(name="厨房 · 洗衣房 · 后花园", view=(990, 150, 1990, 1100), member=(1085, 140, 2000, 1110))}

EXTRA_KEYS = {"30": "二层楼梯吊灯 F06（与二层 S12、S13 三控）", "29": "卫生间排气扇（FI）"}
VERSION, BASIS = "Rev B · 2026-10-03（按常理补全 4 项，见说明）", "PPT v4 第 2 页按键标注；Blender v37"
MIDDLE = {"S7"}           # intermediate switches
KEYPLAN_NOTE = "4. 按常理补全：l 回路 S7 为中途开关三控；38 控洗衣房筒灯；围栏地灯 4 盏；前储物间加门控开关。"
PLATE_NOTE5 = "5. 前储物间门框锁侧加门控开关 DS1（开门亮灯），与 S2 键 2 并联控制 b。"
FCU_ROW = True
if FLOOR == "FF":
    VERSION, BASIS = "Rev B · 2026-10-03（按常理补全，见说明）", "PPT v6 第 6 页按键标注；Blender v37"
    DESC = {"L1": "主卧主灯 F19", "L2": "主卧主灯位（待选）", "L3": "北卫生间筒灯", "L4": "走廊吸顶灯 F11 ×2", "L5": "卧室3 主灯 F22",
            "L6": "衣帽间筒灯 ×2", "L7": "盥洗室筒灯", "L8": "西卫生间筒灯", "L9": "卧室2 主灯 F20", "L10": "卧室2 筒灯 ×2",
            "L11": "楼梯吊灯 F06（三控：一层 S6 + 二层 S12、S13）", "L12": "书房主灯 F23", "L13": "后卫生间筒灯"}
    ASSUMED = {}
    PLATES = [("S1", "单联开关 6", "盥洗室门旁", 1), ("S2", "单联开关 6B", "西卫生间门外", 1), ("S3", "风扇隔离开关 1", "西卫生间门外", 1),
              ("S4", "单联开关 2", "主卧门旁", 1), ("S5", "双联开关 1", "主卧东墙 · 床头侧", 1), ("S6", "单联开关 5", "衣帽间门旁", 1),
              ("S7", "双联开关 2", "卧室2 门旁", 1), ("S8", "双联开关 3", "卧室2 床头侧", 1), ("S9", "单联开关 3", "走廊北端", 2),
              ("S10", "单联开关 1", "北卫生间门外", 2), ("S11", "单联开关 4", "卧室3 门旁", 2), ("S12", "双联开关 4", "走廊南端 · 楼梯口", 2),
              ("S13", "单联开关 7", "楼梯顶", 2), ("S14", "单联开关 8", "书房门旁", 2), ("S15", "单联开关 9", "后卫生间门外", 2),
              ("S16", "风扇隔离开关 2", "后卫生间门外", 2)]
    FCUS = []
    PID = {pn: sid for sid, pn, _, _ in PLATES}
    PSHEET = {pn: sh for _, pn, _, sh in PLATES}
    ZONES = {1: dict(name="主卧 · 盥洗室 · 西卫 · 衣帽间 · 卧室2", view=(360, 150, 1010, 1100), member=(350, 140, 860, 1110)),
             2: dict(name="走廊 · 北卫 · 卧室3 · 楼梯 · 书房 · 后卫", view=(840, 150, 1640, 1100), member=(860, 140, 1650, 1110))}
    EXTRA_KEYS = {"18": "西卫生间排气扇（FI）", "19": "后卫生间排气扇（FI）"}
    MIDDLE = {"S12"}
    KEYPLAN_NOTE = "4. 楼梯吊灯 F06 三控：一层 S6（楼梯底）、二层 S13（楼梯顶）为两路开关，S12 键 2 为中途开关。"
    PLATE_NOTE5 = "5. S2 原图标为“6+”，按常理作为西卫生间筒灯的独立单联开关，与 S3 排气扇隔离开关并排装在门外。"
    FCU_ROW = False
# generic forms of the floor-specific special cases (the web tool's JSON replaces all of these, see lighting_tool/lighting_io.py)
EXTRA_TAG = {"30": "F06", "29": "FI", "18": "FI", "19": "FI"}          # short label of keys that drive no circuit here
REMOTE = {"L11": ["一层 S6"]} if FLOOR == "FF" else {}                # extra control points on the other floor
MIDDLE_KEYS = {("S12", "17")} if FLOOR == "FF" else {("S7", "28")}    # (plate, key) = intermediate switch
MIDDLE = {sid for sid, _ in MIDDLE_KEYS}
REV_CN = "Rev B 2026-10-03"                                         # revision in the 国标 title block
RISER = {} if FLOOR == "FF" else {"30": "↑ 引至二层楼梯吊灯 F06"}       # keys whose switch leg rises to the other floor
DOORSW = [] if FLOOR == "FF" else [dict(id="MK", x=500 * U, y=968 * U, sheet=1, circuit="L2", location="前储物间门框锁侧",
                                        label="前储物间门控开关", parallel="S2 键 2", schedule="b 前储物间筒灯（与 S2 键 2 并联）")]


def sheet_of_light(name):
    x, y = LP[name][0] / U, LP[name][1] / U
    for s, z in ZONES.items():
        a, b, c, d = z["member"]
        if a <= x <= c and b <= y <= d:
            return s
    return 0


LSHEET = {n: sheet_of_light(n) for n in LP}
if FLOOR == "FF": LSHEET["主灯位待选 主灯待选_主卧"] = 1   # sits in the master bedroom
if __import__("os").environ.get("LIGHTING_JSON"):   # data from the web tool replaces everything above
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "lighting_tool"))
    import lighting_io; lighting_io.apply_en(globals())
HAS_FI = any(PANEL[pn][0] == 0 for _, pn, _, _ in PLATES)
missing = [n for c in CIRC for n in c[3] if LSHEET.get(n, 0) == 0]
print("lights without sheet:", missing)

# ---------------- plan group (walls + room names only) ----------------
g536 = [x for x in src.shapes if x.name == PLAN_GROUP][0]
BASE = copy.deepcopy(g536._element)
for ch in list(BASE):
    nv = ch.find('.//' + qn('p:cNvPr'))
    if ch.tag in (qn('p:sp'), qn('p:grpSp'), qn('p:cxnSp'), qn('p:pic')) and nv is not None and not nv.get('name', '').startswith(("墙体", "房间名")):
        BASE.remove(ch)
_x = BASE.find(qn('p:grpSpPr')).find(A + 'xfrm')
GOX, GOY = int(_x.find(A + 'off').get('x')), int(_x.find(A + 'off').get('y'))
GEX, GEY = int(_x.find(A + 'ext').get('cx')), int(_x.find(A + 'ext').get('cy'))
GCX = int(_x.find(A + 'chExt').get('cx'))
C_OLD = (GOX + GEX / 2, GOY + GEY / 2)
M_OLD = M_BASE * GEX / GCX           # EMU per metre on the user's slide


class View:
    def __init__(self, zone_px, box):
        a, b, c, d = [v * U for v in zone_px]; bx0, by0, bx1, by1 = box
        self.K = min((bx1 - bx0) / (c - a), (by1 - by0) / (d - b))
        self.zc = ((a + c) / 2, (b + d) / 2); self.bc = ((bx0 + bx1) / 2, (by0 + by1) / 2); self.box = box

    def T(self, pt):
        return (self.bc[0] + (pt[0] - self.zc[0]) * self.K, self.bc[1] + (pt[1] - self.zc[1]) * self.K)

    def inside(self, pt, m=0):
        x, y = pt; bx0, by0, bx1, by1 = self.box
        return bx0 - m <= x <= bx1 + m and by0 - m <= y <= by1 + m

    def plan(self, slide):
        el = copy.deepcopy(BASE); x = el.find(qn('p:grpSpPr')).find(A + 'xfrm')
        c = self.T(C_OLD); ex, ey = GEX * self.K, GEY * self.K
        x.find(A + 'off').set('x', str(int(c[0] - ex / 2))); x.find(A + 'off').set('y', str(int(c[1] - ey / 2)))
        x.find(A + 'ext').set('cx', str(int(ex))); x.find(A + 'ext').set('cy', str(int(ey)))
        for rp in el.iter(A + 'rPr', A + 'endParaRPr', A + 'defRPr'):
            if rp.get('sz'):
                rp.set('sz', str(int(min(1400, max(700, int(rp.get('sz')) * self.K)))))
        slide.shapes._spTree.append(el)
        return M_OLD * self.K


# ---------------- drawing primitives ----------------
class Pen:
    def __init__(self, slide, scale=1.0):
        self.s = slide; self.k = scale

    def text(self, x, y, w, h, s, size=7, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
        t = self.s.shapes.add_textbox(Emu(int(x)), Emu(int(y)), Emu(int(w)), Emu(int(h)))
        tf = t.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
        for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
            setattr(tf, m, 0)
        for i, ln in enumerate(s.split("\n")):
            para = tf.paragraphs[0] if i == 0 else tf.add_paragraph(); para.alignment = align
            r = para.add_run(); r.text = ln; r.font.size = Pt(size); r.font.bold = bold; r.font.color.rgb = color
            r.font.name = "Microsoft YaHei"
        return t

    def line(self, x0, y0, x1, y1, w=0.75, color=INK, dash=None):
        c = self.s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Emu(int(x0)), Emu(int(y0)), Emu(int(x1)), Emu(int(y1)))
        c.line.color.rgb = color; c.line.width = Pt(w)
        if dash: c.line.dash_style = dash
        return c

    def shape(self, kind, cx, cy, w, h, fill=WHITE, lw=0.75, color=INK, dash=None):
        s = self.s.shapes.add_shape(kind, Emu(int(cx - w / 2)), Emu(int(cy - h / 2)), Emu(int(w)), Emu(int(h)))
        if fill is None: s.fill.background()
        else: s.fill.solid(); s.fill.fore_color.rgb = fill
        if lw: s.line.color.rgb = color; s.line.width = Pt(lw)
        else: s.line.fill.background()
        if dash: s.line.dash_style = dash
        s.shadow.inherit = False
        return s

    def poly(self, pts, close, fill=None, lw=0.75, color=INK, dash=None):
        fb = self.s.shapes.build_freeform(int(pts[0][0]), int(pts[0][1]), scale=1.0)
        fb.add_line_segments([(int(a), int(b)) for a, b in pts[1:]], close=close)
        s = fb.convert_to_shape()
        if fill is None: s.fill.background()
        else: s.fill.solid(); s.fill.fore_color.rgb = fill
        s.line.color.rgb = color; s.line.width = Pt(lw); s.shadow.inherit = False
        if dash: s.line.dash_style = dash
        return s

    def curve(self, a, b, bulge=0.2, lw=0.75, color=WIRE, dash=MSO_LINE_DASH_STYLE.DASH):
        (x0, y0), (x1, y1) = a, b; mx, my = (x0 + x1) / 2, (y0 + y1) / 2; dx, dy = x1 - x0, y1 - y0
        cx, cy = mx - dy * bulge, my + dx * bulge
        pts = [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)
               for t in [i / 16 for i in range(17)]]
        return self.poly(pts, False, lw=lw, color=color, dash=dash)

    # symbols, r = nominal radius
    def pendant(self, x, y, r, pending=False):
        self.shape(MSO_SHAPE.OVAL, x, y, 2.4 * r, 2.4 * r, dash=MSO_LINE_DASH_STYLE.DASH if pending else None)
        d = 1.2 * r * 0.707; self.line(x - d, y - d, x + d, y + d); self.line(x - d, y + d, x + d, y - d)

    def down(self, x, y, r):
        self.shape(MSO_SHAPE.OVAL, x, y, 1.6 * r, 1.6 * r); self.shape(MSO_SHAPE.OVAL, x, y, 0.5 * r, 0.5 * r, fill=INK, lw=0)

    def wall(self, x, y, r):
        pts = [(x + r * math.cos(a), y - r * math.sin(a)) for a in [math.pi * i / 16 for i in range(17)]]
        self.poly(pts + [pts[0]], True, fill=INK); self.line(x - 1.3 * r, y, x + 1.3 * r, y, w=1.25)

    def ground(self, x, y, r):
        self.shape(MSO_SHAPE.OVAL, x, y, 1.4 * r, 1.4 * r)
        tri = [(x, y - 0.45 * r), (x - 0.4 * r, y + 0.3 * r), (x + 0.4 * r, y + 0.3 * r)]
        self.poly(tri + [tri[0]], True, fill=INK, lw=0.5)

    def light(self, name, x, y, r):
        if name.startswith("主灯位待选"): self.pendant(x, y, r, True)
        elif name.startswith("主灯"): self.pendant(x, y, r)
        elif name.startswith("射灯"): self.down(x, y, r)
        elif name.startswith("壁灯"): self.wall(x, y, r)
        else: self.ground(x, y, r)

    def switch(self, x, y, gangs, r):
        self.shape(MSO_SHAPE.OVAL, x, y, 0.9 * r, 0.9 * r, fill=INK, lw=0)
        ang = math.radians(50); L = 2.6 * r; ex, ey = x + L * math.cos(ang), y - L * math.sin(ang)
        self.line(x, y, ex, ey, w=1.25)
        for gi in range(max(gangs, 1)):
            t = 1 - gi * 0.17; px, py = x + (ex - x) * t, y + (ey - y) * t
            self.line(px, py, px + math.sin(ang) * 0.65 * r, py + math.cos(ang) * 0.65 * r, w=1.25)
        return ex, ey

    def box(self, x, y, s, r, size=5):
        self.shape(MSO_SHAPE.RECTANGLE, x, y, 3.4 * r, 1.7 * r)
        self.text(x - 1.7 * r, y - 0.85 * r, 3.4 * r, 1.7 * r, s, size, True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

    def tag(self, x, y, s, size=9):   # switch / FCU id in a rounded box
        w = (len(s) * 0.62 + 0.8) * size * 12700
        b = self.shape(MSO_SHAPE.ROUNDED_RECTANGLE, x + w / 2, y, w, size * 12700 * 1.7, lw=1.0)
        self.text(x, y - size * 12700 * 0.85, w, size * 12700 * 1.7, s, size, True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)


def new_slide():
    s = p.slides.add_slide(src.slide_layout)
    for ph in list(s.placeholders):
        ph._element.getparent().remove(ph._element)
    return s


RIGHT = 8650000


def frame(pen, title_cn, title_en, number, extra_rows=()):
    pen.shape(MSO_SHAPE.RECTANGLE, W / 2, H / 2, W - 200000, H - 200000, fill=None, lw=1.5)
    pen.text(250000, 180000, 8000000, 300000, title_cn, 15, True)
    pen.text(250000, 470000, 8000000, 200000, title_en, 7.5, color=GREY)
    tbx, tby, tbw, tbh = RIGHT, 5100000, W - 100000 - RIGHT, 1658000
    pen.shape(MSO_SHAPE.RECTANGLE, tbx + tbw / 2, tby + tbh / 2, tbw, tbh, fill=None, lw=1.0)
    cells = [("项目", f"27PR 住宅改造 · {FL_CN}照明"), ("图名", title_cn), ("图号", number), ("版本", VERSION), ("依据", BASIS)]
    rh = tbh / len(cells)
    for i, (k, v) in enumerate(cells):
        y = tby + i * rh
        if i: pen.line(tbx, y, tbx + tbw, y, w=0.5)
        pen.text(tbx + 60000, y, 480000, rh, k, 7, True, anchor=MSO_ANCHOR.MIDDLE)
        pen.text(tbx + 600000, y, tbw - 650000, rh, v, 7, anchor=MSO_ANCHOR.MIDDLE)
    pen.line(tbx + 540000, tby, tbx + 540000, tby + tbh, w=0.5)


def legend(pen, x0, y0, r):
    rows = [("pend", "吊灯 / 吸顶主灯"), ("pending", "主灯位（产品待选）"), ("down", "嵌入式筒灯 GU10"), ("wall", "壁灯 / 户外墙灯"),
            ("ground", "围栏地灯（户外）"), ("sw", "开关（短划数 = 联数），S# = 开关编号"), ("fcu", "FCU 带保险丝开关；FI 排气扇隔离开关" if HAS_FI else "FCU 带保险丝开关"),
            ("leg", "开关线（只画到最近一盏灯）"), ("strap", "双控 / 三控联络线 3C+E"), ("let", "a–u 回路字母（灯旁字母 = 控制它的键）")]
    for i, (k, s) in enumerate(rows):
        y = y0 + i * 2.9 * r; x = x0 + 1.8 * r
        if k == "pend": pen.pendant(x, y, r)
        elif k == "pending": pen.pendant(x, y, r, True)
        elif k == "down": pen.down(x, y, r)
        elif k == "wall": pen.wall(x, y, r)
        elif k == "ground": pen.ground(x, y, r)
        elif k == "sw": pen.switch(x - 0.8 * r, y + 0.8 * r, 2, r)
        elif k == "fcu": pen.box(x, y, "FCU", r)
        elif k == "leg": pen.curve((x - 1.6 * r, y + 0.5 * r), (x + 1.6 * r, y + 0.5 * r), 0.35)
        elif k == "strap": pen.line(x - 1.6 * r, y, x + 1.6 * r, y, w=2.0, color=RED)
        elif k == "let": pen.text(x - 0.5 * r, y - 1.2 * r, 2 * r, 2 * r, "a", 9, True, color=WIRE)
        pen.text(x0 + 4.2 * r, y - 1.1 * r, 3200000, 2.2 * r, s, 6.5, anchor=MSO_ANCHOR.MIDDLE)


def gang_letters(pn):
    out = []
    for k in PANEL[pn][1]:
        c = KEY_CIRC.get(k)
        out.append(CL[c] if c else EXTRA_TAG.get(k, "?"))
    return out


# ---------------- key plan ----------------
s0 = new_slide(); pen = Pen(s0)
V0 = View((40, 120, 1990, 1110), (300000, 900000, RIGHT - 250000, 6650000))
m0 = V0.plan(s0)
frame(pen, f"{FL_CN}照明总平面（索引图）", f"{FL_EN} LIGHTING — KEY PLAN", f"E-{FC}-00")
r0 = 30000
for z, d in ZONES.items():
    a, b, c, e = d["view"]; (x0, y0), (x1, y1) = V0.T((a * U, b * U)), V0.T((c * U, e * U))
    pen.shape(MSO_SHAPE.RECTANGLE, (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0, fill=None, lw=1.25, color=RED, dash=MSO_LINE_DASH_STYLE.LONG_DASH)
    pen.text(x0 + 40000, y0 + 30000, 2400000, 200000, f"E-{FC}-0{z} 放大图：{d['name']}", 8, True, color=RED)
for n, pt in LP.items():
    x, y = V0.T(pt); pen.light(n, x, y, r0)
for sid, pn, loc, sh in PLATES:
    x, y = V0.T(MOUNT[pn])
    if PANEL[pn][0] == 0: pen.box(x, y, "FI", r0)
    else: pen.switch(x, y, PANEL[pn][0], r0)
    pen.text(x - 250000, y + 30000, 240000, 120000, sid, 6.5, True, align=PP_ALIGN.RIGHT)
for fid, pn, k in FCUS:
    x, y = V0.T(MOUNT[pn]); pen.box(x, y, "FCU", r0, 4)
legend(pen, RIGHT + 80000, 400000, 60000)
pen.text(RIGHT + 80000, 3450000, 3300000, 1500000,
         f"说明：\n1. 本图只表示位置与编号，接线见 E-{FC}-01~0{len(ZONES)} 放大图。\n2. 开关面板逐键功能见 E-{FC}-04 开关面板表；回路见 E-{FC}-05。\n"
         "3. 开关中心离地 1200 mm，设在门开启侧（锁侧），距门框 150 mm。\n" + KEYPLAN_NOTE, 7)
sb = m0
for i in range(3):
    pen.shape(MSO_SHAPE.RECTANGLE, 400000 + sb * (i + 0.5), 6500000, sb, 40000, fill=INK if i % 2 == 0 else WHITE, lw=0.5)
pen.text(400000 + sb * 3 + 40000, 6440000, 300000, 120000, "3 m", 6)

# ---------------- E-GF-01..03 zone plans ----------------
PANEL_TEXT_X = RIGHT + 80000
for z, d in ZONES.items():
    sl = new_slide(); pen = Pen(sl)
    V = View(d["view"], (300000, 850000, RIGHT - 200000, 6650000))
    mpm = V.plan(sl)
    # white masks outside the viewport so neighbouring rooms do not show
    bx0, by0, bx1, by1 = V.box
    for (mx0, my0, mx1, my1) in ((0, 0, W, by0), (0, by1, W, H), (0, by0, bx0, by1), (bx1, by0, W, by1)):
        pen.shape(MSO_SHAPE.RECTANGLE, (mx0 + mx1) / 2, (my0 + my1) / 2, mx1 - mx0, my1 - my0, fill=WHITE, lw=0)
    frame(pen, f"{FL_CN}照明放大图 {z}：{d['name']}", f"{FL_EN} LIGHTING & SWITCHING — ZONE {z}", f"E-{FC}-0{z}")
    r = 0.11 * mpm      # symbol radius ~ 110 mm
    my_plates = [(sid, pn) for sid, pn, _, sh in PLATES if sh == z]
    notes = []
    # strappers between switches of the same circuit on this sheet
    pairs = {}; straps = []
    for cid, desc, keys, lights in CIRC:
        pns = [pn for k in keys for pn in KEY2PANEL.get(k, [])]
        for i in range(len(pns) - 1):
            a, b = pns[i], pns[i + 1]
            if a != b: pairs.setdefault(tuple(sorted((a, b))), []).append(CL[cid])
    for (a, b), lets in pairs.items():
        on = [PSHEET.get(a) == z, PSHEET.get(b) == z]
        if all(on):
            (x0, y0), (x1, y1) = V.T(MOUNT[a]), V.T(MOUNT[b])
            pen.line(x0, y0, x1, y1, w=2.0, color=RED)
            wn = f"W{len(straps) + 1}"; straps.append(f"{wn}：{PID[a]} ↔ {PID[b]}  3C+E  回路 {' '.join(lets)}")
            mx_, my_ = x0 + (x1 - x0) * 0.35, y0 + (y1 - y0) * 0.35
            pen.shape(MSO_SHAPE.OVAL, mx_, my_, 200000, 140000, fill=WHITE, lw=0.75, color=RED)
            pen.text(mx_ - 100000, my_ - 70000, 200000, 140000, wn, 6, True, color=RED, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        elif any(on):
            here, there = (a, b) if on[0] else (b, a)
            notes.append(f"{PID[here]} 与 {PID[there]}（E-{FC}-0{PSHEET[there]}）双控：{' '.join(lets)}")
    # switch legs + light chains
    for cid, desc, keys, lights in CIRC:
        pts = [(n, V.T(LP[n])) for n in lights if LSHEET.get(n) == z]
        sws = [(pn, V.T(MOUNT[pn])) for k in keys for pn in KEY2PANEL.get(k, []) if PSHEET.get(pn) == z]
        if pts:
            if sws:
                for pn, m in sws:
                    first = min(pts, key=lambda t: math.hypot(t[1][0] - m[0], t[1][1] - m[1]))[1]
                    pen.curve(m, first, 0.2)
                cur = min(pts, key=lambda t: math.hypot(t[1][0] - sws[0][1][0], t[1][1] - sws[0][1][1]))
            else:
                cur = pts[0]
                others = sorted({PID[pn] for k in keys for pn in KEY2PANEL.get(k, [])})
                x, y = cur[1]
                pen.text(x + 1.4 * r, y + 0.6 * r, 1500000, 130000, f"← {'/'.join(others)}（另图）", 6.5, color=WIRE)
            rest = [t for t in pts if t is not cur]
            while rest:
                n = min(rest, key=lambda t: math.hypot(t[1][0] - cur[1][0], t[1][1] - cur[1][1]))
                pen.curve(cur[1], n[1], 0.15); cur = n; rest.remove(n)
        elif sws:
            for pn, m in sws:
                pen.text(m[0] + 0.5 * r, m[1] + 0.7 * r, 1400000, 130000, f"{CL[cid]} → 见另图", 6.5, color=WIRE)
    # lights
    for n, pt in LP.items():
        if LSHEET.get(n) != z: continue
        x, y = V.T(pt); pen.light(n, x, y, r)
        cid = next((c[0] for c in CIRC if n in c[3]), None)
        if cid:
            pen.text(x + 1.2 * r, y - 2.4 * r, 2 * r, 1.6 * r, CL[cid], 9, True, color=RED if cid in TBC else WIRE)
    # switches
    for sid, pn in my_plates:
        x, y = V.T(MOUNT[pn])
        if PANEL[pn][0] == 0:
            pen.box(x, y, "FI", r * 0.8); pen.tag(x + 1.6 * r, y - 1.8 * r, sid, 8)
            continue
        ex, ey = pen.switch(x, y, PANEL[pn][0], r * 0.8)
        pen.tag(ex + 0.2 * r, ey - 0.5 * r, sid, 9)
    for fid, pn, k in FCUS:
        if LSHEET.get("") is None and not V.inside(V.T(MOUNT[pn])): continue
        x, y = V.T(MOUNT[pn]); pen.box(x, y, "FCU", r * 0.8, 5); pen.text(x - 2 * r, y + 1.0 * r, 4 * r, 1.4 * r, fid, 6.5, True, align=PP_ALIGN.CENTER)
    # right panel: switches on this sheet
    y = 400000
    pen.text(PANEL_TEXT_X, y, 3300000, 180000, "本图开关（从左到右逐键）", 8.5, True); y += 230000
    for sid, pn in my_plates:
        gl = gang_letters(pn); g = PANEL[pn][0]
        typ = "FI 隔离开关" if g == 0 else f"{g} 联"
        loc = next(l for s_, p_, l, _ in PLATES if s_ == sid)
        pen.text(PANEL_TEXT_X, y, 3300000, 150000, f"{sid}  {typ} · {loc}", 7, True); y += 165000
        pen.text(PANEL_TEXT_X + 250000, y, 3100000, 150000, "  ".join(f"键{i+1}={x}" for i, x in enumerate(gl)), 7, color=WIRE); y += 200000
    y += 60000; pen.text(PANEL_TEXT_X, y, 3300000, 160000, "双控联络线（红粗线）", 8, True, color=RED); y += 190000
    for st in straps:
        pen.text(PANEL_TEXT_X, y, 3300000, 160000, "· " + st, 6.5, color=RED); y += 170000
    pen.text(PANEL_TEXT_X, y, 3300000, 300000, "红线只表示连接关系，实际走线沿墙 / 吊顶内，现场定。", 6.5, color=RED); y += 260000
    if notes:
        y += 60000; pen.text(PANEL_TEXT_X, y, 3300000, 160000, "跨图双控", 8, True); y += 190000
        for nt in notes:
            pen.text(PANEL_TEXT_X, y, 3300000, 300000, "· " + nt, 6.5); y += 180000
    tbc = [f"{CL[c]}：{TBC[c]}" for c in TBC if any(LSHEET.get(n) == z for n in next(cc for cc in CIRC if cc[0] == c)[3])]
    if tbc:
        y += 60000; pen.text(PANEL_TEXT_X, y, 3300000, 160000, "待确认（红色字母）", 8, True, color=RED); y += 190000
        for t in tbc:
            pen.text(PANEL_TEXT_X, y, 3300000, 300000, "· " + t, 6.5, color=RED); y += 180000
    for i in range(2):
        pen.shape(MSO_SHAPE.RECTANGLE, 400000 + mpm * (i + 0.5), 6560000, mpm, 40000, fill=INK if i % 2 == 0 else WHITE, lw=0.5)
    pen.text(400000 + mpm * 2 + 40000, 6500000, 300000, 120000, "2 m", 6)


# ---------------- tables ----------------
def border(cell, color="808080", w=6350):
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        ln = etree.SubElement(tcPr, qn(tag), w=str(w)); sf = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(sf, qn("a:srgbClr"), val=color)


def table(slide, x, y, widths, rows, rh=260000, size=7.5, red_rows=()):
    tbl = slide.shapes.add_table(len(rows), len(widths), Emu(x), Emu(y), Emu(sum(widths)), Emu(rh * len(rows))).table
    tbl.first_row = True; tbl.horz_banding = False
    for j, w in enumerate(widths): tbl.columns[j].width = Emu(w)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Emu(rh)
        for j, v in enumerate(row):
            c = tbl.cell(i, j); c.text = v; c.fill.solid()
            c.fill.fore_color.rgb = RGBColor(0xE7, 0xE6, 0xE6) if i == 0 else WHITE
            c.margin_top = c.margin_bottom = Emu(15000); c.margin_left = c.margin_right = Emu(40000)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE; border(c)
            for para in c.text_frame.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(size); run.font.bold = (i == 0 or j == 0); run.font.name = "Microsoft YaHei"
                    run.font.color.rgb = RED if i in red_rows and j else INK
    return tbl


# E-GF-04 switch plate schedule
s4 = new_slide(); pen = Pen(s4)
frame(pen, f"{FL_CN}开关面板表（逐键）", "SWITCH PLATE SCHEDULE — GANGS NUMBERED LEFT TO RIGHT", f"E-{FC}-04")
rows = [["编号", "位置", "面板", "键 1", "键 2", "键 3", "键 4", "双控 / 三控对端"]]
redc = set()
for sid, pn, loc, sh in PLATES:
    g, keys = PANEL[pn]
    cells, partners = [], []
    for j, k in enumerate(keys):
        c = KEY_CIRC.get(k)
        if c:
            cells.append(f"{CL[c]} {DESC[c]}")
            if c in TBC: redc.add((len(rows), 3 + j))
            for pn2 in [pp for kk in next(cc for cc in CIRC if cc[0] == c)[2] for pp in KEY2PANEL.get(kk, [])]:
                if pn2 != pn and f"{CL[c]}↔{PID[pn2]}" not in partners: partners.append(f"{CL[c]}↔{PID[pn2]}")
        else:
            cells.append(EXTRA_KEYS.get(k, f"原{k}"))
    cells += [""] * (4 - len(cells))
    typ = {0: "FI 隔离", 1: "1 联", 2: "2 联", 3: "3 联", 4: "4 联"}[g]
    if sid in MIDDLE: typ += "（含中途开关）"
    rows.append([sid, loc, typ, *cells, "，".join(partners)])
if FCU_ROW: rows.append(["FCU1–5", "厨房 / 洗衣房台面后墙（见 E-GF-03）", "FCU 13A ×5", "各供一台电器，用途待填", "", "", "", ""])
t4 = table(s4, 250000, 780000, (380000, 1150000, 620000, 1250000, 1250000, 1250000, 1250000, 1050000), rows, 205000, 6)
for (i, j) in redc:
    for para in t4.cell(i, j).text_frame.paragraphs:
        for run in para.runs: run.font.color.rgb = RED
NOTE4 = ["说明：", "1. 键 1 → 键 4 为面板上从左到右的顺序（按 PPT 标注顺序）。", f"2. 字母 = 回路，见 E-{FC}-05；位置见 E-{FC}-00~0{len(ZONES)}。",
         "3. 开关中心离地 1200 mm；FCU 在台面上 150 mm。",
         "4. 双控每对开关之间需敷设联络线 3C+E；三控回路需两只两路开关 + 一只中途开关（intermediate）。",
         PLATE_NOTE5, "6. 面板统一 NAB 古铜系列；联数与本表一致。"]
pen.text(RIGHT + 80000, 400000, 3300000, 4000000, chr(10).join(NOTE4), 7.5)

# E-GF-05 circuit schedule
s5 = new_slide(); pen = Pen(s5)
frame(pen, f"{FL_CN}照明回路表", f"{FL_EN} LIGHTING CIRCUIT SCHEDULE", f"E-{FC}-05")
rows = [["字母", "回路", "控制灯具", "灯数", "开关（编号-键）", "方式", "图"]]
red = []
for cid, desc, keys, lights in CIRC:
    sw = []
    for k in keys:
        for pn in KEY2PANEL.get(k, []):
            sw.append(f"{PID[pn]}-键{PANEL[pn][1].index(k) + 1}")
    sw += REMOTE.get(cid, [])
    mode = {1: "单控", 2: "双控", 3: "三控"}.get(len(sw), "")
    sheets = sorted({LSHEET.get(n) for n in lights})
    rows.append([CL[cid], cid, DESC[cid] + ("（待确认）" if cid in TBC else ""), str(len(lights)), "，".join(sw), mode,
                 "，".join(f"0{s}" for s in sheets)])
    if cid in TBC: red.append(len(rows) - 1)
table(s5, 250000, 800000, (420000, 450000, 2900000, 450000, 2500000, 550000, 600000), rows, 235000, 7.5, red)

# ---------------- keep only the new sheets ----------------
n_new = 3 + len(ZONES)
ids = list(p.slides._sldIdLst)
for sid_el in ids[:-n_new]:
    p.part.drop_rel(sid_el.rId); p.slides._sldIdLst.remove(sid_el)
p.save(DST)
print("saved", DST)
