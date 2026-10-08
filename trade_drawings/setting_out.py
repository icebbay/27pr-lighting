# -*- coding: utf-8 -*-
"""27PR 点位定位尺寸图（插座 / 开关 / 灯 / 给排水点）— DRAFT.

Every point gets: room, which wall (compass name, seen from inside the room), distance from the left / right end of that
wall face (corner, door or window edge) and a mounting height above the room's finished floor.  Wall faces come from the
same wall drawing as the trade drawings (walls_<F>.svg, synced to model v42); heights from the rules below + model v42
furniture / openings (_v42_objects.json).

Orientation (model): -Y = west (front), +Y = east (rear garden), -X = north, +X = south.
"""
import json, math, os, re
from shapely.geometry import Polygon, Point, LineString, MultiPolygon, box
from shapely.ops import unary_union
import plan_base as pb
from plan_base import Frame, load_tool, TOOL

HERE = os.path.dirname(os.path.abspath(__file__))
OBJ = json.load(open(os.path.join(HERE, "_v42_objects.json"), encoding="utf-8"))

# ---------------- height rules (mm, to the centre of the box, above the room's finished floor) ----------------
H = dict(switch=1200, socket=300, outdoor=600, bedside_over=150, worktop_over=200, fcu=1100, dp=1200, ev=1000, lift_dp=1200)
CEIL = {"GF": 2600, "FF_front": 2500, "FF_rear": 2856}


def floor_z(F, x, y):
    if F == "GF": return 0.0
    return 2.852 if (y > 7.97 and x > 1.0) else 3.208      # rear annex (卧室 4 / 后卫 / 书房二) is 356 lower


def ceil_h(F, x, y):
    if F == "GF": return CEIL["GF"]
    return CEIL["FF_rear"] if floor_z(F, x, y) < 3.0 else CEIL["FF_front"]


def ob(name):   # [x0, y0, z0, x1, y1, z1]
    return OBJ[name]


# ---------------- geometry ----------------
def evenodd_paths(F, cls):
    fr = Frame(F)
    svg = open(os.path.join(TOOL, f"walls_{F}.svg"), encoding="utf-8").read()
    out = []
    for g in re.finditer(r'<g class="(\w+)"[^>]*>(.*?)</g>', svg, re.S):
        if g.group(1) != cls: continue
        for name, d in re.findall(r'data-name="([^"]*)" d="([^"]+)"', g.group(2)):
            geo = None
            for sub in re.split(r'(?=M)', d):
                nums = [float(v) for v in re.sub('[MLZ]', ' ', sub).split()]
                if len(nums) < 6: continue
                p = Polygon([fr.t2b(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]).buffer(0)
                geo = p if geo is None else geo.symmetric_difference(p)
            if geo is not None and not geo.is_empty: out.append((name, geo))
    return out


class Plan:
    def __init__(self, F):
        self.F = F
        # walls / doors straight from the model v42 section (the PPT wall drawing misses e.g. the 客厅 / 起居室 wall V12)
        from patch_walls_v42 import evenodd
        sec = json.load(open(os.path.join(HERE, "_v42_section.json"), encoding="utf-8"))[F]
        by = {}
        for n, a, b, c, d in sec: by.setdefault(n, []).append((a, b, c, d))
        geo = {n: evenodd(s) for n, s in by.items()}
        isdoor = lambda n: re.search(r"Leaf|Jamb|Lining|Door", n)
        model = [g.buffer(0) for n, g in geo.items() if g is not None and not isdoor(n) and "RearBoundary" not in n]
        drawn = [g for _, g in evenodd_paths(F, "wall")]          # + the drawing (fills pieces the 1 m / 4.1 m cut misses)
        self.walls = unary_union(model + drawn).buffer(0.01, join_style=2).buffer(-0.01, join_style=2)
        self.doors = unary_union([g.buffer(0) for n, g in geo.items() if g is not None and isdoor(n)] + [g for _, g in evenodd_paths(F, "door")])
        self.windows = unary_union([g for _, g in evenodd_paths(F, "window")])
        _, self.rooms = pb.walls(F)
        if F == "GF": self.rooms.append(("门厅", 3.75, 1.0))     # not labelled on the PPT plan
        self.runs = []                       # (a, b) wall-face segments after merging collinear points
        polys = self.walls.geoms if isinstance(self.walls, MultiPolygon) else [self.walls]
        for P in polys:
            for ring in [P.exterior] + list(P.interiors):
                pts = list(ring.simplify(0.008).coords)
                for a, b in zip(pts, pts[1:]):
                    if math.dist(a, b) > 0.02: self.runs.append((a, b, pts))
        self.openings = self._openings()

    def _openings(self):
        """Blender windows / doors on this floor: (name, kind, plan polygon, sill, head) with sill/head above local floor"""
        out = []
        for n, (x0, y0, z0, x1, y1, z1) in OBJ.items():
            if not (n.startswith("WD_") or n.endswith("SmallWindow")): continue
            zc = (z0 + z1) / 2
            if (self.F == "GF") != (zc < 2.7): continue
            fz = floor_z(self.F, (x0 + x1) / 2, (y0 + y1) / 2)
            kind = "door" if "Door" in n else "window"
            out.append((n, kind, box(x0, y0, x1, y1), round((z0 - fz) * 1000, -1), round((z1 - fz) * 1000, -1)))
        return out

    def room_polys(self, k):
        """free space with openings closed: k = half the widest gap that gets sealed"""
        if not hasattr(self, "_rp"): self._rp = {}
        if k not in self._rp:
            solid = unary_union([self.walls, self.doors, self.windows] + [o[2] for o in self.openings])
            closed = solid.buffer(k, join_style=2).buffer(-k, join_style=2)
            x0, y0, x1, y1 = self.walls.bounds
            free = box(x0 - 1, y0 - 1, x1 + 1, y1 + 1).difference(closed)
            self._rp[k] = list(free.geoms) if hasattr(free, "geoms") else [free]
        return self._rp[k]

    def room_at(self, p):
        P = Point(p)
        first = None
        for k in (0.3, 0.6, 0.95):          # small rooms first; if two rooms merged through a wide opening, seal wider openings
            for poly in self.room_polys(k):
                if poly.contains(P) and poly.area < 150:
                    inside = sorted((math.dist(p, (x, y)), t) for t, x, y in self.rooms if poly.contains(Point(x, y)))
                    if len({t for _, t in inside}) == 1: return inside[0][1]
                    if inside and first is None: first = inside[0][1]
        if first: return first
        best = None
        for t, x, y in self.rooms:
            d = math.dist(p, (x, y))
            if LineString([p, (x, y)]).intersects(self.walls): d += 50
            if best is None or d < best[0]: best = (d, t)
        return best[1] if best else "?"

    def face(self, p, max_d=0.6):
        """nearest wall face to p -> dict(a, b, n, foot, dist)"""
        P = Point(p)
        cand = sorted((LineString([a, b]).distance(P), a, b, ring) for a, b, ring in self.runs)
        if not cand or cand[0][0] > max_d: return None
        best = next((c for c in cand if math.dist(c[1], c[2]) >= 0.4 and c[0] <= cand[0][0] + 0.12), cand[0])   # skip 10–30 cm stubs
        d, a, b, ring = best
        L = LineString([a, b]); foot = L.interpolate(L.project(P)).coords[0]
        ux, uy = (b[0] - a[0]) / math.dist(a, b), (b[1] - a[1]) / math.dist(a, b)
        n = (-uy, ux)
        if (p[0] - foot[0]) * n[0] + (p[1] - foot[1]) * n[1] < 0: n = (uy, -ux)
        # room side of an on-wall point: test a point 5 cm off the face
        if self.walls.contains(Point(foot[0] + n[0] * 0.05, foot[1] + n[1] * 0.05)): n = (-n[0], -n[1])
        return dict(a=a, b=b, n=n, foot=foot, dist=d, ring=ring)

    def end_kind(self, f, end):
        """what stops the wall face at this end: 墙角 / 门洞边 / 窗洞边 / 墙端"""
        q = Point(end)
        for n, kind, poly, sill, head in self.openings:
            if poly.buffer(0.12).contains(q): return ("门洞边" if kind == "door" else "窗洞边"), n
        if self.doors.distance(q) < 0.12: return "门洞边", None
        if self.windows.distance(q) < 0.12: return "窗洞边", None
        # inside corner: the next face turns into the room
        ring = f["ring"]; i = min(range(len(ring)), key=lambda k: math.dist(ring[k], end))
        nb = [ring[(i - 1) % (len(ring) - 1)], ring[(i + 1) % (len(ring) - 1)]]
        other = max(nb, key=lambda v: abs((v[0] - end[0]) * f["n"][0] + (v[1] - end[1]) * f["n"][1]))
        into = (other[0] - end[0]) * f["n"][0] + (other[1] - end[1]) * f["n"][1]
        return ("墙角" if into > 0.01 else "墙端"), None


def compass(n):
    """wall name from the inward normal n (wall lies on the -n side)"""
    if abs(n[0]) >= abs(n[1]): return "北墙" if n[0] > 0 else "南墙"
    return "西墙" if n[1] > 0 else "东墙"


def left_right(f):
    fx, fy = -f["n"][0], -f["n"][1]           # looking at the wall
    r = (fy, -fx)                             # viewer's right
    a, b = f["a"], f["b"]
    if (b[0] - a[0]) * r[0] + (b[1] - a[1]) * r[1] > 0: return a, b, r
    return b, a, r


def r10(v): return int(round(v / 10.0) * 10)


# ---------------- items ----------------
BEDSIDE = {"FF": ["F03.001", "F04.001", "F07.001", "F08.001"], "GF": []}
TOPS = {"GF": ["WORKTOP_A", "WORKTOP_B", "WORKTOP_C", "WORKTOP_D", "G02.001", "G04.001"], "FF": ["F21a.001"]}
AC = {"FF": [(0.73, 1.57, 7.72, 7.93, 5.25, 5.55), (1.72, 2.56, 8.11, 8.32, 5.24, 5.55)]}   # indoor units (x0,x1,y0,y1,z0,z1)
WALL_LIGHT_Z = {"F32": "F32.001", "G26_1": "G26_1", "G26_2": "G26_2", "G26_3": "G26_3", "G26_4": "G26_4_FloodLight_SOLLA"}
KIND_CN = {"double": "双联插座", "single": "单联插座", "outdoor": "户外防水插座 IP66", "high": "空调插座"}
WATER_RULE = {   # fixture type: (supply note, supply h, drain note, drain h)
    "WC": ("马桶角阀 h 150，距马桶中线约 200（按马桶型号）", 150, "后出水中心 h 180（模型）/ 地排按坑距", 180),
    "B": ("冷 / 热角阀 h 550，左右各距中线 75", 550, "台盆排水：落进楼板（柜内地面出）", 0),
    "SH": ("明装恒温淋浴杆阀 h 1050，冷热 150 c/c", 1050, "淋浴排水：西卫墙排地漏 / 其余淋浴盘地漏", 0),
    "KS": ("岛台柜内地面出：冷 / 热 / 净水（预埋）", 0, "岛台地面出 40 废水（预埋）", 0),
    "DW": ("洗碗机阀 h 500（水槽柜内）", 500, "接水槽存水弯侧口", 0),
    "LD": ("洗衣机冷 / 热阀 h 1050（洗衣柜侧板）", 1050, "40 立管存水弯 h 600", 600),
    "OB": ("户外水斗龙头 h 900（DCV + 防冻）", 900, "32 废水穿后墙", 300),
    "FT": ("洗车龙头 h 380（DCV + 室内隔离 / 泄水阀）", 380, "车道排水", 0)}


WATER_AT = {"WC1": (0.79, 2.33), "SH1": (-0.07, 2.33)}     # outlet point on the intended wall (west-bath false walls, P-08)


def near_box(p, name, pad=0.25):
    x0, y0, z0, x1, y1, z1 = ob(name)
    return box(x0, y0, x1, y1).buffer(pad).contains(Point(p))


def collect(F):
    fr = Frame(F); J = load_tool(F)
    P = json.load(open(os.path.join(TOOL, f"power_{F}.json"), encoding="utf-8"))
    hi = {"卧室 3": "WP3", "卧室 4": "WP4"}
    items = []

    def add(**k): items.append(k)
    for i, s in enumerate(P["sockets"], 1):
        p = fr.t2b(s["x"], s["y"]); fz = floor_z(F, *p); h = H["socket"]; why = "300（业主原定，与模型一致）"
        circ = hi.get(s["room"], s["c"]["A"]) if s["kind"] == "high" else s["c"]["A"]
        if s["kind"] == "outdoor":
            h, why = H["outdoor"], "户外 600，防水盖朝下"
        elif s["kind"] == "high":
            u = min(AC.get(F, []), key=lambda u: math.dist(p, ((u[0] + u[1]) / 2, (u[2] + u[3]) / 2)))
            h = r10(((u[4] + u[5]) / 2 - fz) * 1000); why = f"空调内机侧面，与机身中高齐平（内机底 {r10((u[4] - fz) * 1000)}）"
        add(cat="socket", id=f"C{i:02d}", name=KIND_CN[s["kind"]], room=s["room"], circ=circ, p=p, h=h, why=why, mount="wall", kind=s["kind"])
    for i, it in enumerate(P["items"], 1):
        p = fr.t2b(it["x"], it["y"]); lab = it["label"].split("（")[0]
        mount = "wall"
        if it.get("alarm"):
            h, why, nm, mount = ceil_h(F, *p), "厨房天花，市电，接一层照明回路；距锅炉水平 1–3 m", "温感 + 一氧化碳报警器", "ceiling"
        elif "锅炉" in it["label"]:
            h, why, nm = 700, "软水机旁，一块双联面板：锅炉 FCU 3A（固定接线）+ 软水机 13A 插座", "锅炉 FCU 3A + 软水机插座（双联）"
        elif "抽油烟机" in it["label"]:
            h, why, nm = 2200, "烟机罩内高位插座", "抽油烟机高位插座"
        elif "地暖分水器" in it["label"]:
            h, why, nm = H["fcu"], "分水器旁，给接线中心 + 混水泵供电", "FCU 3A · 地暖分水器 UF1"
        elif it.get("fcu"):
            h, why, nm = H["fcu"], "FCU 装在台面上方 / 相邻柜内可触及处", f"FCU 13A · {lab}"
        elif "控制开关" in it["label"]:
            h, why, nm = H["dp"], "40A 双极隔离开关（充电桩室内总控）", "DP 40A · 充电桩总控"
        elif "充电桩" in it["label"]:
            h, why, nm = H["ev"], "充电桩底座约 1000（按产品说明书）", "EV 充电桩（外墙）"
        else:
            h, why, nm = H["lift_dp"], "电梯隔离开关，位置 / 高度以厂家为准", "DP · 电梯"
        add(cat="power", id=f"D{i:02d}", name=nm, room="", circ=it["c"].get("B", it["c"].get("A")), p=p, h=h, why=why, mount=mount)
    for s in J["plates"]:
        p = fr.t2b(s["x"], s["y"])
        add(cat="switch", id=s["id"], name=f"{s['gangs']} 联开关 · 键 {'/'.join(s['keys'])}" + (f"（叠在 {s['stack_above']} 正上方）" if s.get("stack_above") else ""), room="", circ="", p=p,
            h=H["switch"] + (130 if s.get("stack_above") else 0),
            why="开关中心 1200（原施工图 / 模型）", mount="wall", loc=s["location"])
    for i, l in enumerate(J["lights"], 1):
        p = fr.t2b(l["x"], l["y"]); fz = floor_z(F, *p); k = l["kind"]; lid = l["id"].split(" ")[-1]
        if k == "壁灯":
            if lid == "G25":
                add(cat="light", id=f"L{i:02d}", name="门廊吊灯 G25（户外）", room="门廊", circ="", p=p, h=2600, why="吊在门廊顶（模型 v42 顶高 2600）", mount="ceiling")
                continue
            src = WALL_LIGHT_Z.get(lid)
            z = (ob(src)[2] + ob(src)[5]) / 2 if src else fz + 1.8
            add(cat="light", id=f"L{i:02d}", name=f"壁灯 {lid}" + ("（户外）" if l.get("outdoor") else ""), room="", circ="", p=p,
                h=r10((z - (0 if l.get("outdoor") else fz)) * 1000), why=f"模型 v42 灯具中心高度（{src or '—'}）", mount="wall")
        elif k == "地灯":
            add(cat="light", id=f"L{i:02d}", name="围栏地灯（户外）", room="后花园", circ="", p=p, h=0, why="地面安装，SWA 埋地 ≥ 450", mount="ground")
        else:
            nm = {"筒灯": "GU10 筒灯", "主灯": f"主灯 {lid}", "待选": "主灯位（灯具待选）"}.get(k, k)
            add(cat="light", id=f"L{i:02d}", name=nm, room="", circ="", p=p, h=ceil_h(F, *p), why="天花安装（吸顶 / 吊灯线盒）", mount="ceiling")
    import plumbing as PB
    for fid, (fl, x, y, name, sup, (dk, ds)) in PB.FIX.items():
        if fl != F: continue
        code = PB.CODE[fid]; t = code.split("-")[0].rstrip("0123456789")
        rule = WATER_RULE.get(t, ("按产品", 0, "按产品", 0))
        add(cat="water", id=code, name=name.split("（")[0], room="", circ=sup, p=WATER_AT.get(code, (x, y)), h=rule[1], why=rule[0] + ("；西卫：出在后墙假墙完成面上（方案 B，假墙尽量薄），假墙厚度定后复核水平尺寸" if code in WATER_AT else ""), mount="wall" if rule[1] else "floor",
            drain=rule[2], drain_h=rule[3], dk=f"{dk} Ø{ds}" if ds else dk)
    if F == "FF":     # gaps found while checking (draft additions, flagged)
        for code, x, y, nm in (("WC1", 1.0, 2.33, "西卫智能马桶"),):   # 北卫 WC2: shares the plate with its towel rail (N-TR2), owner 2026-10-08
            add(cat="new", id=f"N-{code}", name=f"{nm}电源出线面板（新增）", room="", circ="WX8", p=(x, y), h=300,
                why="马桶侧后方出线面板 h 300，FCU 13A 装在卫生间外开关旁 h 1100", mount="wall")
        x0, y0, z0, x1, y1, z1 = ob("F31_master_bath"); fz = floor_z(F, (x0 + x1) / 2, (y0 + y1) / 2)
        add(cat="new", id="N-TR1", name="西卫电热毛巾架出线面板（新增）", room="", circ="WX8",
            p=((x0 + x1) / 2, (y0 + y1) / 2), h=r10((z0 - fz) * 1000 + 100), why="毛巾架下沿旁出线面板（模型位置），FCU 13A 装在卫生间外 h 1100", mount="wall")
        # 北卫 (owner 2026-10-08): towel rail moved onto the rear wall right beside the WC (rail x -2.07..-1.57, 200 from the WC);
        # one double flex-outlet plate in the gap for the smart WC + the towel rail, h 300; both FCUs outside the door at 1100
        add(cat="new", id="N-TR2", name="北卫智能马桶 + 电热毛巾架出线面板（双联，新增）", room="", circ="WX7",
            p=(-1.47, 7.88), h=300, why="马桶与毛巾架之间的双联出线面板 h 300（毛巾架挪到马桶旁后墙，离马桶约 200）；两个 FCU 13A 装在卫生间门外 h 1100", mount="wall")
    fix_points(F, items)
    return [i for i in items if i["cat"] != "water"]   # owner 2026-10-08: water points live on the plumbing drawings only


# 2026-10-08 (owner: no open points left) — final positions:
#  * GF points that differed from the model: use the model (owner's site points of 2026-10-01)
#  * FF S3: above the nightstand on the C19 side, 700 (two-way with S4 at the door) — the wall middle is behind the F01 headboard
#  * sockets blocked by furniture: the proposals of _points_review_v44.json (TV cabinets -> 600, others slid past the furniture)
POS_FIX = {"GF": {"C02": (2.33, 4.354), "C15": (-0.607, 7.141), "C21": (1.04, 12.256), "C25": (2.564, 14.714), "C27": (4.29, 8.752),
                  "C28": (-4.29, 3.185), "C34": (-4.285, 1.074), "S3": (2.358, 4.234),
                  "D08": (-3.765, 1.65),    # EV 40A isolator: 550 from the door edge, clear of S9 (was on top of it)
                  "D06": (-0.89, 5.823)},  # lift isolator: off the 120 mm stub by the lift onto the straight wall beside C11
           "FF": {"S3": (-0.76, 3.86)}}
H_FIX = {"FF": {"S3": (700, "床头柜上方 700（与门口 S4 双控），避开床头板")}}


def fix_points(F, items):
    rev = json.load(open(os.path.join(HERE, "_points_review_v44.json"), encoding="utf-8")) if os.path.exists(os.path.join(HERE, "_points_review_v44.json")) else []
    clash = {o["id"]: o for o in rev if o["F"] == F and o.get("new") and not o["id"].startswith(("S3", "N-"))}
    for it in items:
        if it["id"] in POS_FIX.get(F, {}):
            it["p"] = POS_FIX[F][it["id"]]
            if it["id"] == "D08": it["why"] = "40A 双极隔离开关（充电桩室内总控）；离门洞边 550，与 S9 错开"
            elif it["id"] == "D06": it["why"] = "电梯隔离开关：挪到 C11 旁直墙上（原位置在电梯旁 120 宽墙头）；高度以厂家为准"
            elif F == "GF": it["why"] = it.get("why", "") + "；位置按模型（业主现场定）"
        elif it["id"] in clash and it["cat"] == "socket":
            q = clash[it["id"]]["new"]; it["p"] = (q["x"] + q["n"][0] * 0.05, q["y"] + q["n"][1] * 0.05)
            if "TV" in clash[it["id"]].get("rule", ""): it["h"] = 600; it["why"] = "电视柜上方 600（原位置被电视柜挡住）"
            else: it["why"] = it.get("why", "") + "；已挪到家具外侧（原位置被家具挡住）"
        if it["id"] in H_FIX.get(F, {}):
            it["h"], it["why"] = H_FIX[F][it["id"]]


def locate(F):
    PLN = Plan(F); items = collect(F); out = []
    for it in items:
        p = it["p"]; r = dict(it, floor=F)
        f = PLN.face(p) if it["mount"] == "wall" else None
        if it["mount"] == "wall":
            if f is None and any(near_box(p, t, 0.3) for t in TOPS.get(F, [])):
                it = dict(it, mount="island"); r.update(mount="island", h=800, why="岛台端板插座 h 800（或改台面弹起插座）")
            elif f is None:
                r.update(wall="—", flag="离墙 > 0.6 m，现场确认", room=r["room"] or PLN.room_at(p))
            if f is not None:
                L, R, rv = left_right(f)
                s = (f["foot"][0] - L[0]) * rv[0] + (f["foot"][1] - L[1]) * rv[1]
                length = math.dist(L, R)
                kl, _ = PLN.end_kind(f, L); kr, _ = PLN.end_kind(f, R)
                pin = (f["foot"][0] + f["n"][0] * 0.3, f["foot"][1] + f["n"][1] * 0.3)
                if not r["room"]: r["room"] = PLN.room_at(pin)
                r.update(wall=compass(f["n"]), L=L, R=R, n=f["n"], s=r10(s * 1000), rest=r10((length - s) * 1000), run=r10(length * 1000),
                         lk=kl, rk=kr, off=r10(f["dist"] * 1000), foot=f["foot"])
                fl = []
                if f["dist"] > 0.25: fl.append(f"原点位离墙面 {r10(f['dist'] * 1000)}，已按墙面定位")
                if it["cat"] in ("socket", "switch") and min(s, length - s) < 0.1: fl.append("离墙角 / 洞口 < 100，现场确认")
                if it.get("kind") in ("double", "single"):     # furniture in front of the socket, same room (no wall in between)
                    q = (f["foot"][0] + f["n"][0] * 0.05, f["foot"][1] + f["n"][1] * 0.05); fz = floor_z(F, *p)
                    for t, pad, over, txt in [(t, 0.3, H["bedside_over"], "床头柜面 {} + 150（略高于柜面）") for t in BEDSIDE[F]] +                                              [(t, 0.15, H["worktop_over"], "台面 {} 上方（底边离台面约 150）") for t in TOPS[F]]:
                        x0, y0, z0, x1, y1, z1 = ob(t); c = ((x0 + x1) / 2, (y0 + y1) / 2)
                        if near_box(q, t, pad) and (c[0] - q[0]) * f["n"][0] + (c[1] - q[1]) * f["n"][1] > -0.05 and not LineString([q, c]).intersects(PLN.walls):
                            top = (z1 - fz) * 1000; r["h"] = r10(top + over); r["why"] = txt.format(r10(top))
                            if t in BEDSIDE[F] and PLN.room_at(pin) != r["room"]:
                                fl.append(f"数据里房间为「{r['room']}」，按位置是{PLN.room_at(pin)}床头"); r["room"] = PLN.room_at(pin)
                if it["cat"] in ("socket", "switch", "power"):          # hidden behind furniture (model v42 boxes)?
                    fz = floor_z(F, *p); face_ln = LineString([f["a"], f["b"]])
                    for nm, (x0, y0, z0, x1, y1, z1) in OBJ.items():
                        if not re.match(r"^[FG]\d\d", nm) or nm in BEDSIDE[F] + TOPS[F] or z0 - fz > 0.5 or z1 - fz < 0.3: continue
                        if (z0 < 2.7) != (F == "GF"): continue
                        bx = box(x0, y0, x1, y1)
                        c = bx.centroid.coords[0]
                        if bx.distance(face_ln) > 0.15 or (c[0] - f["foot"][0]) * f["n"][0] + (c[1] - f["foot"][1]) * f["n"][1] < 0.05: continue
                        xs = [((c[0] - L[0]) * rv[0] + (c[1] - L[1]) * rv[1]) for c in bx.exterior.coords]
                        if min(xs) + 0.05 < s < max(xs) - 0.05 and r["h"] < (z1 - fz) * 1000:
                            fl.append(f"在 {nm.split('.')[0]}（高 {r10((z1 - fz) * 1000)}）后面会被挡住，建议移到侧边或抬高"); break
                r["flag"] = "；".join(fl)
        if r.get("mount", it["mount"]) != "wall":
            r["room"] = r["room"] or PLN.room_at(p)
            d = {}
            stops = [(PLN.walls, "墙"), (unary_union([PLN.doors, PLN.windows] + [o[2] for o in PLN.openings]), "门窗洞")]
            for name, (dx, dy) in (("北", (-1, 0)), ("南", (1, 0)), ("西", (0, -1)), ("东", (0, 1))):
                ray = LineString([p, (p[0] + dx * 12, p[1] + dy * 12)])
                hits = [(Point(p).distance(ray.intersection(g)), w) for g, w in stops if not ray.intersection(g).is_empty]
                if hits:
                    dd, w = min(hits); d[name + w] = r10(dd * 1000)
            ns = min([k for k in d if k[0] in "北南"], key=lambda k: (k.endswith("洞"), d[k]), default=None)
            we = min([k for k in d if k[0] in "西东"], key=lambda k: (k.endswith("洞"), d[k]), default=None)
            r.update(wall={"ceiling": "天花", "floor": "地面", "ground": "室外地面", "island": "岛台"}[r.get("mount", it["mount"])], dx=(ns, d.get(ns)), dy=(we, d.get(we)), flag=r.get("flag", ""))
        if "户外" in r["name"] or r["id"] in ("OB", "FT") or r["name"].startswith("EV"): r["room"] = "户外"
        out.append(r)
    return PLN, out


if __name__ == "__main__":
    for F in ("GF", "FF"):
        _, rows = locate(F)
        for r in rows:
            if r["wall"] in ("天花", "地面", "室外地面"):
                print(F, r["id"], r["name"], r["room"], r["wall"], r["dx"], r["dy"], r["h"])
            else:
                print(F, r["id"], r["name"], r["room"], r.get("wall"), r.get("lk"), r.get("s"), "|", r.get("rk"), r.get("rest"), "h", r["h"], r.get("flag", ""))
