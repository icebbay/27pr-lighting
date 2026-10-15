# -*- coding: utf-8 -*-
"""27PR 墙面立面施工图（每个房间：平面索引 + 天花 + 每面墙一张立面）— Rev A draft.

Base: Blender model v44 (27PR_CGI_v44_points_review_20261008.blend, 西卫方案 B): finished wall faces, openings (wall-shell
vertices), ceiling, skirting / coving, furniture boxes.  Points: 点位定位尺寸图 Rev A (setting_out.py) — NOT the switch / socket
objects of the Blender model (EL26_*), which are older (owner 2026-10-08).  Dedicated / FCU points are not drawn (site, under the stairs).

    python wall_elev.py            -> out/27PR_墙面立面_<room>_RevA.pdf (+ out/png/W2-xx-n.png)
"""
import html, json, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shapely.geometry import Polygon, Point, LineString, box
import setting_out as so
from plan_base import Sheet, BASE_CSS, table, wrap

E = html.escape
REV = dict(rev="J", date="2026-10-08")
COL = {"socket": "#1565c0", "switch": "#111111", "light": "#e65100", "new": "#c62828", "water": "#00897b"}
CSS = BASE_CSS + """
.wl{fill:none;stroke:#222;stroke-width:.35}.fl{stroke:#111;stroke-width:.7}.thin{stroke:#999;stroke-width:.15;fill:none}
.cut{fill:#bdbdbd;stroke:#333;stroke-width:.25}.win{fill:#e3f0fa;stroke:#4f7ea8;stroke-width:.3}.door{fill:#f6f1e7;stroke:#8d6e3f;stroke-width:.3}
.furn{fill:none;stroke:#888;stroke-width:.25;stroke-dasharray:1.2 .7}.dim{stroke:#333;stroke-width:.15;fill:none}.dimt{fill:#222}
.ft{fill:#777}.ttl{font-weight:bold;fill:#111}
"""

# ---------------- rooms (Blender metres; faces listed as seen from inside: L = viewer's left end, R = right end) ----------------
ROOMS = {
    "FF_次卧": dict(
        F="FF", cn="次卧", en="Second bedroom", sheet0=1, fz=3.208, ceil=2500, skirt=144, cove=90,
        poly=[(-0.711, 0.820), (-4.199, 0.820), (-4.199, 7.928), (-2.786, 7.928), (-2.786, 6.400), (-2.723, 6.400), (-2.723, 6.279),
              (-1.946, 6.279), (-1.946, 4.474), (-1.884, 4.474), (-1.884, 4.414), (-0.711, 4.414)],
        faces=[  # letter, compass name, description, L, R, (left end kind, right end kind)
            ("A", "西墙", "前窗墙 Front window wall", (-0.711, 0.820), (-4.199, 0.820), ("墙角", "墙角")),
            ("B", "北墙", "北侧长墙 North wall", (-4.199, 0.820), (-4.199, 7.928), ("墙角", "墙角")),
            ("C", "东墙", "后窗墙 Rear window wall", (-4.199, 7.928), (-2.786, 7.928), ("墙角", "墙角")),
            ("D", "南墙", "卫浴门墙 En-suite door wall", (-2.786, 7.928), (-2.786, 6.400), ("墙角", "墙端（阳角）")),
            ("E", "东墙", "入口短墙 Entry wall", (-2.723, 6.279), (-1.946, 6.279), ("墙端（阳角）", "墙角")),
            ("F", "南墙", "房门墙 Entrance door wall", (-1.946, 6.279), (-1.946, 4.474), ("墙角", "门洞边")),
            ("G", "东墙", "门边墙 Wall beside door", (-1.884, 4.414), (-0.711, 4.414), ("门洞边", "墙角")),
            ("H", "南墙", "床头墙 Bed-head wall", (-0.711, 4.414), (-0.711, 0.820), ("墙角", "墙角")),
        ],
        # openings from the v44 wall shell (structural opening; sill / head above this room's FFL)
        openings=[("window", "窗 W1", (-3.734, 0.820), (-2.838, 0.820), 947, 2100), ("window", "窗 W2", (-2.199, 0.820), (-1.303, 0.820), 947, 2100),
                  ("window", "窗 W3", (-3.867, 7.928), (-2.971, 7.928), 947, 2100),
                  # owner 2026-10-08: en-suite door -> 686 x 1981 (F27 type), structural opening 756 (686 + 70 for lining / fixing, as the 762 door
                  # in the kitchen passage got 832); 500 from the opening edge to the wall end by E; hinge on the rear side as before
                  ("door", "卫浴门 F27 686×1981", (-2.786, 7.656), (-2.786, 6.900), 0, 2030),
                  ("door", "房门 762（门扇）", (-1.946, 5.302), (-1.946, 4.474), 0, 2031)],
        swings=[((-2.786, 7.656), (-2.786, 6.970), (-3.472, 7.656)), ((-1.946, 5.269), (-1.946, 4.507), (-2.708, 5.269))],  # hinge, closed tip, open tip
        # furniture boxes from model v44 (evaluated instances): label, [x0, y0, z0, x1, y1, z1]
        furniture=[("床 F01 南辰家（床头板）", so.ob("F01.001")), ("床头柜 F03", so.ob("F03.001")), ("床头柜 F04（尺寸待核）", so.ob("F04.001")),
                   # F29 split into its parts (model v44 = spec: desk 600 x 400 x 750, mirror Ø400 x 500 on the desk, stool 400 x 300 x 430)
                   ("梳妆台 F29", [-4.2, 6.386, 3.208, -3.797, 6.989, 3.959]), ("圆镜 F29（含支架）", [-4.132, 6.465, 3.958, -4.1, 6.91, 4.46]),
                   ("梳妆凳", [-3.694, 6.602, 3.208, -3.382, 7.014, 3.641]),
                   ("衣柜（占位，未选定）", [-4.2, 1.17, 3.21, -3.565, 2.67, 5.31]), ("衣柜（占位，未选定）", [-4.2, 2.67, 3.21, -3.565, 4.17, 5.31])],
        # setting-out points that need a different face than the nearest one (with reason) — owner to confirm
        override={"S3": ("H", 1.844, "床头板水平居中；中心高于床头板顶 150，h=1360"), "S4": ("G", 1.023, "靠 F 墙转角：开关中心距左端 150 mm，离地 1200 mm"), "S9": ("D", 0.350, "卫浴门外 D 墙：离门洞边 150、离墙端 350（业主 2026-10-08：门洞到 E 墙转角留 500）")},
        room_note={"C25": "数据里房间写「电梯」，按位置在次卧入口 E 墙（次卧一侧）",
                   "C22": "⚠ 在模型 v44 的衣柜（深 635、高 2100、y 1170–4170）后面，会被挡住 —— 待业主定：挪出衣柜外，或改到衣柜内"},
    ),
}

ROOMS["FF_次卧卫浴"] = dict(
    F="FF", cn="次卧完整卫浴", en="En-suite", sheet0=2, fz=3.208, ceil=2500, skirt=144, cove=90, plan_kind="带洁具",
    poly=[(-2.662, 6.401), (-0.711, 6.401), (-0.711, 7.928), (-2.662, 7.928)],
    faces=[("A", "西墙", "台盆墙 Basin wall", (-0.711, 6.401), (-2.662, 6.401), ("墙角", "墙角")),
           ("B", "北墙", "门墙 Door wall（次卧一侧是 D 墙）", (-2.662, 6.401), (-2.662, 7.928), ("墙角", "墙角")),
           ("C", "东墙", "后窗墙 Rear window wall", (-2.662, 7.928), (-0.711, 7.928), ("墙角", "墙角")),
           ("D", "南墙", "淋浴墙 Shower wall", (-0.711, 7.928), (-0.711, 6.401), ("墙角", "墙角"))],
    openings=[("window", "窗 W4", (-2.527, 7.928), (-1.630, 7.928), 947, 2100), ("door", "门 F27 686×1981（通次卧）", (-2.662, 7.656), (-2.662, 6.900), 0, 2030)],
    swings=[],                       # the door swings into 次卧 (see W2-01-0)
    furniture=[("马桶 F16 智能马桶", so.ob("F16.001")), ("台盆 F17（挂墙）", so.ob("F17.001")), ("淋浴房 F18 800×900", so.ob("F18_COMPACT_Room199_Shower")),
               ("电热毛巾架 F31（挪到马桶旁）", [-2.07, 7.83, 3.393, -1.57, 7.928, 4.036])],
    water=[("WC2", "智能马桶 Smart WC（后墙东角）", "冷水（软水）15；110 污水直穿后墙 → S1", (-1.05, 7.60)),
           ("B2", "台盆 Basin（西墙，门旁）", "冷 / 热（软水）15；40 废水 → S1", (-2.02, 6.64)),
           ("SH2", "淋浴 Shower 800×900", "冷 / 热（软水）15；40 废水 → S1", (-1.14, 6.84))],
    override={}, room_note={},
    notes5="5. 本房间无梁、无假墙（模型 v44）。给排水预留口：给排水施工图 Rev C 只定了洁具、管径和走向，没有定出口位置 / 高度 —— 按所选洁具安装说明现场定（待业主确认），本图不画。电热毛巾架按业主 2026-10-08 挪到马桶旁后墙（模型 v44 还在旧位置）。",
)
ROOMS["FF_次卧"]["notes5"] = "5. 本房间无梁、无假墙（模型 v44）。E 墙左端外 62 / 121 mm 的小转角不出立面。Rev E：门扇 762×1981×35；暂定门洞 828×2031，右边不变，左侧墙段 977。洞高从完成地面 FFL 起算；从结构地面量需另加地面做法厚度。两侧框及缝合计 66，需复核门扇间隙及框外塞缝；非通用安装定值。门底缝图示 10，按成品复核。"

# Rev H: screenshot dimensions; preserve established door swing and edge relationships.
BR = ROOMS["FF_次卧"]
BA = ROOMS["FF_次卧卫浴"]
BR["rev"] = BA["rev"] = dict(rev="L")
# Rev L (owner 2026-10-08): the shared double outlet N-TR2 (h300 between WC and rail) is replaced by two flex outlets stacked behind
# the smart WC (right-hand side, where the owner circled): lower = smart WC, upper = towel rail; each fed from its own FCU over the door
BA["drop"] = {"N-TR2"}
BA["extra_pts"] = [
    ("C", "N-WC2", "智能马桶出线口", 1760, 400, "马桶后面右侧，被马桶挡住；出线面板（非插座）IPX4；由门上 SM 供电；按马桶说明书核对进线位置", "WX7"),
    ("C", "N-TR2", "电热毛巾架出线口（上）", 1760, 530, "与 N-WC2 上下叠放（中心距 130）；由门上 ST 供电；毛巾架电线从马桶后面上到毛巾架底边（1300），线走墙内或线槽现场定", "WX7"),
]
BA["notes5"] += " Rev L：取消 N-TR2 双联共用面板，改为马桶后面右侧上下两个出线口：下 N-WC2 智能马桶 h400、上 N-TR2 电热毛巾架 h530，离 C 墙左端 1760；分别由门上 SM / ST 供电。"
BR["poly"] = [(-.711,.820),(-4.199,.820),(-4.199,7.928),(-2.721,7.928),(-2.721,6.238),(-1.921,6.238),(-1.921,4.368),(-.711,4.368)]
coords = [(BR["poly"][i], BR["poly"][(i+1)%8]) for i in range(8)]
BR["faces"] = [(f[0],f[1],f[2],*coords[i],f[5]) for i,f in enumerate(BR["faces"])]
BR["openings"][-2:] = [("door","卫浴门 F27 686×1981",(-2.721,7.494),(-2.721,6.738),0,2030),("door","房门 762（门扇）",(-1.921,5.196),(-1.921,4.368),0,2031)]
BR["swings"] = [((-2.721,7.494),(-2.721,6.808),(-3.407,7.494)),((-1.921,5.163),(-1.921,4.401),(-2.683,5.163))]
BR["override"]["S4"] = ("G",1.060,"靠 F 墙转角：开关中心距左端 150，离地 1200")
BR["notes5"] = "5. Rev H：按业主尺寸图，D=1690、E=800、F=1870；右侧及后侧基准保持，重建入口转角。D 门洞 756，靠 E 端墙段 500；F 门洞 828×2031（暂定），靠 G 端不留墙段，另一侧 1042。门扇及开启方向沿用原方案。墙厚图示按 100 衔接（1690-1590），非实测墙厚；平面墙体不再沿用旧模型轮廓。卫浴门旁两个开关 SM 智能马桶 + ST 电热毛巾架（Rev N：门左侧，中心高 1800、间距 130）；此处不装排风扇。洞高从完成地面起算，门框及安装缝按成品复核。"
BA["poly"] = [(-2.621,6.338),(-.711,6.338),(-.711,7.928),(-2.621,7.928)]
bcoords = [(BA["poly"][1],BA["poly"][0]),(BA["poly"][0],BA["poly"][3]),(BA["poly"][3],BA["poly"][2]),(BA["poly"][2],BA["poly"][1])]
BA["faces"] = [(f[0],f[1],f[2],*bcoords[i],f[5]) for i,f in enumerate(BA["faces"])]
BA["openings"][-1] = ("door","门 F27 686×1981（通次卧）",(-2.621,7.494),(-2.621,6.738),0,2030)
BA["furniture"] = [(name, [v[0],v[1]-.063,v[2],v[3],v[4]-.063,v[5]] if name.startswith(("台盆","淋浴")) else v) for name,v in BA["furniture"]]
BA["notes5"] = "5. Rev H：卫生间室内净尺寸 1910×1590，面积约 3.04 m²；台盆、淋浴随所在墙平移，洁具规格及布局不变。门洞与次卧 D 墙贯通，开启方向沿用原方案。墙厚仅示意；洁具接口按产品和现场复核。"

BA["furniture"] = [(name, [v[0], 6.338, v[2], v[3], 7.238, v[5]] if name.startswith("淋浴") else v) for name,v in BA["furniture"]]

BA["furniture"] = [("电热毛巾架 F31（马桶上方）", [-1.303,7.830,4.508,-.803,7.928,5.151]) if name.startswith("电热毛巾架") else (name,v) for name,v in BA["furniture"]]
BA["notes5"] += " Rev J：毛巾架 F31 位于马桶正上方，宽 500、高 643，底边离地 1300、顶边 1943；门上 ST 控制开关位置保留。Rev K：门上 SM（智能马桶）+ ST（毛巾架）两个开关，不装排风扇。"
# Rev M (owner 2026-10-08): en-suite downlight L07 moved away from the shower, a little to the top-right (north 150, east 200)
BA["ceil_move"] = {"L07": (-1.841 - 0.150, 7.058 + 0.200)}
BA["notes5"] += " Rev M：筒灯 L07 离开淋浴区，往北 150、往东 200（中心距西墙 920 / 东墙 670，距北墙 630 / 南墙 1280）。"
BR["rev"] = BA["rev"] = dict(rev="M")
# Rev N = Codex Rev K (L03 / L12 1250 / 1200 from the north wall, owner red circles) + Codex Rev L (C22 3500 from the left corner,
# clear of the wardrobe placeholder) + owner 2026-10-08: UFH control panel beside S4 on G; SM / ST moved beside the en-suite door, h 1800
BR["ceil_move"] = {"L03": (-4.199 + 1.250, 2.946), "L12": (-4.199 + 1.200, 5.573)}
BR["override"]["C22"] = ("B", 3.608, "中心距左侧墙角 3500，距右侧墙角 3608；离地 450；已移出衣柜占位范围")
BR["room_note"].pop("C22", None)
BR["extra_pts"] = [("G", "TH", "地暖温控面板 UFH thermostat", 300, 1200, "S4 右侧同高，中心距 S4 150；有线温控需穿线到地暖分水器接线中心，无线温控也按此位置留底盒；型号由地暖供应商定", "待定")]
BR["notes5"] += " Rev N：主灯 L03 距北墙 1250、L12 距北墙 1200（Codex Rev K）；C22 距左墙角 3500（Codex Rev L）；G 墙 S4 右侧加地暖温控面板 TH（h1200）；SM / ST 挪到卫浴门左侧，离地 1800。"
BR["rev"] = BA["rev"] = dict(rev="N")
# Rev L (after the Rev H wall redraw, so the new H length is used)
_hL, _hR = next((f[3], f[4]) for f in BR["faces"] if f[0] == "H")
_hrun = math.dist(_hL, _hR)
BR["override"]["C19"] = ("H", _hrun - 0.250, "床头插座：中心离左墙角 250（业主 2026-10-08），高 630")
BR["override"]["C20"] = ("H", 0.250, "床头插座：中心离右墙角 250（业主 2026-10-08），高 630")
BR["notes5"] += " Rev L：床头插座 C19 / C20 中心各离墙角 250。"

# ---------------- 主卧 (CGI-site name; old data: 卧室 2) — model v44 -----------------------------------------------------
ROOMS["FF_主卧"] = dict(
    F="FF", cn="主卧", en="Master bedroom", sheet0=3, rev=dict(rev="B"), fz=3.208, ceil=2500, skirt=144, cove=90,
    poly=[(1.230, 0.284), (1.644, 0.284), (1.644, 0.209), (4.290, 0.209), (4.290, 4.354), (1.230, 4.354)],
    faces=[  # letter, compass name, description, L, R, (left end kind, right end kind)
        ("A", "西墙", "前窗墙 Front window wall", (4.290, 0.209), (1.644, 0.209), ("墙角", "墙垛阳角（往北 414 段墙面凸出 75）")),
        ("B", "北墙", "主卫 / 衣帽间入口墙 En-suite & closet wall", (1.230, 0.284), (1.230, 4.354), ("墙角", "墙角")),
        ("C", "东墙", "房门墙 Entrance door wall", (1.230, 4.354), (4.290, 4.354), ("墙角", "墙角")),
        ("D", "南墙", "床头墙 Bed-head wall", (4.290, 4.354), (4.290, 0.209), ("墙角", "墙角")),
    ],
    # openings from the v44 wall shell / door frames (sill / head above FFL)
    openings=[("window", "窗 W5 成品 1000×1600（窗台约 500）", (3.030, 0.209), (2.004, 0.209), 500, 2100),
              ("door", "主卫入口 F25 一门两用", (1.230, 0.504), (1.230, 1.334), 0, 2030),
              ("door", "衣帽间洞口（内装 F27 686 门）", (1.230, 2.957), (1.230, 3.954), 0, 2252),
              ("door", "房门 686（洞 761）", (1.599, 4.354), (2.360, 4.354), 0, 2030)],
    swings=[((2.328, 4.354), (1.642, 4.354), (2.328, 3.668)), ((1.230, 3.763), (1.230, 3.137), (1.856, 3.763))],
    furniture=[("床 F02（床头板）", so.ob("F02.001")), ("床头柜 F07", so.ob("F07.001")), ("床头柜 F08", so.ob("F08.001")),
               ("梳妆台 F05", so.ob("F05.001")), ("半镜柜 F10", so.ob("F10.001"))],
    override={"S1": ("B", 3.960, "主卫入口洞口与前墙之间 220 宽墙垛正中（各 110）；业主 2026-10-08 确认（点位图 Rev A 原落在洞口内）"),
              "S6": ("D", 0.535, "床头侧双联开关，与下方 C04 插座同一中线（点位图两者差 10，取齐）"),
              "S5": ("B", 0.200, "衣帽间洞口与东墙角之间 400 宽墙段正中（各 200），在 F27 合页侧外；业主 2026-10-08 确认（点位图 Rev A 原落在洞口内）"),
              "C05": ("A", 0.210, "中心离窗洞边 150（往北，远离窗，业主确认）；原点位离窗洞边仅 32")},
    extra_pts=[("C", "TH", "地暖温控面板 UFH thermostat", 240, 1350, "⚠ 按次卧做法加（业主 2026-10-08）；S7 所在墙段只有 369（墙角到门洞），并排放不下，改为叠在 S7 正上方，中心距 S7 150 —— 位置待业主确认。有线温控需穿线到地暖分水器接线中心，无线温控也按此位置留底盒；型号由地暖供应商定", "待定")],
    room_note={"C07": "梳妆台 F05 左边缘 2519，面板与柜边重叠约 17 —— 现场核对",
               "S7": "门洞与北墙角之间 369 宽墙段（锁舌侧）"},
    notes5="5. 主卧 = 原数据的「卧室 2」（CGI 网站命名）。墙面、门窗洞、家具按模型 v44；本房间无梁、无假墙，天花 2500。前墙北端 414 段墙面比其余凸出 75（墙垛）。衣帽间洞口 997×2252 内装 F27 686 门，两侧补墙 / 门框做法待定。Rev B（业主 2026-10-08）：S1 / S5 按墙垛建议位确认；C05 挪到离窗洞边 150；房门开关 S7 正上方加地暖温控面板 TH（h1350，位置待确认）。",
)


# Rev C (owner 2026-10-08): 主卧 room height ~2700 (not 2500) -> ceiling 2700; window W5 sill 880 (head 880 + 1600 = 2480)
MB = ROOMS["FF_主卧"]
MB["rev"] = dict(rev="C")
MB["ceil"] = 2700
MB["openings"] = [("window", "窗 W5 成品 1000×1600（窗台 880）", o[2], o[3], 880, 2480) if o[1].startswith("窗 W5") else o for o in MB["openings"]]
MB["notes5"] = MB["notes5"].replace("天花 2500", "天花约 2700（业主 2026-10-08，现场复核）") + " Rev C：房间高约 2700，窗 W5 窗台改 880（洞顶 2480）。"

# Rev P (owner 2026-10-09): as in 主卫 — towel-rail outlet N-TR2 at the rail itself (centred, 100 above its bottom edge 1300 -> h1400,
# hidden behind the rail), not stacked behind the WC; bedside sockets C19 / C20 at h650 like 主卧.
BR["rev"] = BA["rev"] = dict(rev="P")
_cL = next(f[3] for f in BA["faces"] if f[0] == "C")
_rail = next(v for n_, v in BA["furniture"] if n_.startswith("电热毛巾架"))
_s_rail = round((abs((_rail[0] + _rail[3]) / 2 - _cL[0])) * 1000)
BA["extra_pts"] = [e if e[1] != "N-TR2" else ("C", "N-TR2", "电热毛巾架出线口", _s_rail, 1400,
                   "在毛巾架 F31 正中、底边（1300）上方 100，被毛巾架挡住（同主卫做法）；由门边 ST 供电；出线面板（非插座），IPX4", e[6]) for e in BA["extra_pts"]]
BA["notes5"] += f" Rev P：N-TR2 改到毛巾架处（中心离 C 墙左端 {_s_rail}，h1400，在毛巾架后面），不再叠在马桶后面。"
for _id, _d in (("C19", BR["override"]["C19"][1]), ("C20", BR["override"]["C20"][1])):
    BR["override"][_id] = ("H", _d, BR["override"][_id][2].replace("高 630", "高 650（同卧室 2，业主 2026-10-09）"), 650)
BR["notes5"] += " Rev P：床头插座 C19 / C20 改离地 650（同主卧）。"

# ---------------- 主卫 (CGI) = 盥洗室 (vanity zone) + 卫生间 (WC / shower zone, 西卫 scheme B) — model v44 + plumbing Rev C P-07 ----
ROOMS["FF_主卫"] = dict(
    F="FF", cn="主卫", en="Master en-suite", sheet0=4, fz=3.208, ceil=2500, skirt=144, cove=90, rev=dict(rev="B"), plan_kind="带洁具",
    poly=[(-0.589, 0.209), (1.092, 0.209), (1.092, 2.370), (-0.589, 2.370), (-0.589, 1.412), (0.428, 1.412), (0.428, 1.273), (-0.589, 1.273)],
    faces=[
        ("E", "西墙", "盥洗室前窗墙 Vanity-zone window wall", (1.092, 0.209), (-0.589, 0.209), ("墙角", "墙角")),
        ("F", "北墙", "盥洗室台盆墙 Basin wall", (-0.589, 0.209), (-0.589, 1.273), ("墙角", "墙角")),
        ("G", "东墙", "隔墙（盥洗室侧）Partition, vanity side", (-0.589, 1.273), (0.428, 1.273), ("墙角", "墙端（门洞边）")),
        ("H", "南墙", "通主卧洞口 + 毛巾架墙 Wall to bedroom", (1.092, 2.370), (1.092, 0.209), ("墙角（假墙）", "墙角")),
        ("I", "东墙", "卫生间后墙假墙（淋浴 + 马桶）Pre-wall", (-0.589, 2.370), (1.092, 2.370), ("墙角", "墙角")),
        ("J", "北墙", "卫生间淋浴侧墙 Shower side wall", (-0.589, 1.412), (-0.589, 2.370), ("墙角（隔墙）", "墙角（假墙）")),
        ("K", "西墙", "隔墙（卫生间侧）Partition, WC side", (0.428, 1.412), (-0.589, 1.412), ("墙端（门洞边）", "墙角")),
    ],
    openings=[("window", "磨砂窗 W6 成品 1000×1600（窗台约 500，洞延伸到隔墙后）", (1.092, 0.209), (0.237, 0.209), 500, 2100),
              ("door", "通主卧洞口（F25 一门两用）", (1.092, 1.334), (1.092, 0.504), 0, 2030)],
    swings=[],
    furniture=[("台盆柜 F12（挂墙）", so.ob("F12.001")), ("智能马桶 F13", so.ob("F13.001")), ("淋浴区 F14", so.ob("F14_ShowerReserved")),
               ("电热毛巾架 F31", so.ob("F31_master_bath"))],
    # plumbing Rev C P-07 (west bath, scheme B): on the pre-wall E; s = mm from E's left end (x -0.589)
    features=[("I", "淋浴段假墙（做到天花）", 0, 1089, 0, 2500, "pre"), ("I", "马桶段假墙 1100 高 + 置物台", 1089, 1659, 0, 1120, "pre"),
              ("I", "壁龛 1 300×900", 69, 369, 850, 1750, "niche"), ("I", "壁龛 2 300×900", 669, 969, 850, 1750, "niche"),
              ("I", "墙排地漏 600", 139, 739, 0, 60, "drain"), ("I", "AAV 检修口 300×300（约，正对 AAV）", 1229, 1529, 780, 1080, "panel")],
    water_pts=[("I", "SH1", "恒温淋浴杆阀 Thermostatic bar valve", 519, 1050, "冷 / 热 150 c/c，明装；两个壁龛中间（P-07）"),
               ("I", "SH1-H", "顶喷 Ø250 Rain head", 519, 1975, "顶喷中心离地约 1975，带滑杆手持（P-07）")],
    override={}, room_note={
        "C06": "⚠ 卫生间内的插座：BS 7671 701.512.3 要求离淋浴 zone 1 边界 ≥ 3 m（剃须插座 / SELV 除外）；此处与淋浴之间有隔墙 + 门 —— 请电工判定，可能需改为剃须插座或挪出卫生间",
        "N-WC1": "马桶旁出线面板（非插座），FCU 在卫生间外；面板防护 ≥ IPX4",
        "N-TR1": "毛巾架下沿旁出线面板（非插座），FCU 在卫生间外"},
    notes5="5. 主卫 = 盥洗室（外区，挂墙台盆）+ 卫生间（内区，淋浴 + 马桶），中间隔墙 + F25 一门两用门。卫生间后墙为方案 B 假墙（尽量薄，能借原墙就借；厚度现场定），壁龛 / 恒温阀 / 顶喷 / 墙排地漏 / AAV 检修口按给排水施工图 Rev C P-07；台盆、马桶给水出口高度按洁具型号现场定。盥洗室磨砂窗洞（237–1253）延伸到与主卧之间的隔墙后，为现状。",
)

# ---------------- 衣帽间 (CGI) — model v44: F15 three-sided shelving 1700 x 1700 x 2100 fills it ----------------------------
ROOMS["FF_衣帽间"] = dict(
    F="FF", cn="衣帽间", en="Walk-in closet", sheet0=5, fz=3.208, ceil=2500, skirt=144, cove=90, rev=dict(rev="B"),
    poly=[(-0.589, 2.655), (1.092, 2.655), (1.092, 4.353), (-0.589, 4.353)],
    faces=[
        ("L", "西墙", "西侧衣架墙 West shelving wall", (1.092, 2.655), (-0.589, 2.655), ("墙角", "墙角")),
        ("M", "北墙", "北侧衣架墙 North shelving wall", (-0.589, 2.655), (-0.589, 4.353), ("墙角", "墙角")),
        ("N", "东墙", "东侧衣架墙 East shelving wall", (-0.589, 4.353), (1.092, 4.353), ("墙角", "墙角")),
        ("O", "南墙", "门墙（通主卧）Door wall", (1.092, 4.353), (1.092, 2.655), ("墙角", "墙角")),
    ],
    openings=[("door", "衣帽间洞口（内装 F27 686 门）", (1.092, 3.954), (1.092, 2.957), 0, 2252)],
    swings=[],
    furniture=[("三面衣架 F15（产品待定）", so.ob("F15.001"))],
    override={}, room_note={"C01": "预留插座，在 F15 衣架后面（业主 2026-10-08：保持原位，只是预留）", "C09": "预留插座，在 F15 衣架后面（业主 2026-10-08：保持原位，只是预留）"},
    notes5="5. 衣帽间三面墙被 F15 三面衣架（1700×1700×2100，产品待定）占满；本房间无梁，天花 2500。门洞 997×2252 内装 F27 686 门（开向主卧），两侧补墙 / 门框做法待定。开关 S5 在主卧 B 墙。Rev B：C01 / C09 保持在衣架后面，只作预留（业主 2026-10-08）。",
)

# Rev D (owner 2026-10-08): 衣帽间 — the two GU10 L10 + L14 become ONE ceiling light (吸顶灯) in the middle, a little towards the
# door (north 950 / south 731, west 820 = door centre line); F25 / F27 = PD (匹帝维斯) S16 doors: F25 一门两用 main 762 / second 742,
# F27 686 (frame 686 + 2 x 28 = 742).
for _k in ("FF_主卧", "FF_主卫", "FF_衣帽间"): ROOMS[_k]["rev"] = dict(rev="D")
CL = ROOMS["FF_衣帽间"]
CL["drop"] = {"L10"}
CL["ceil_move"] = {"L14": (-0.589 + 0.950, 2.655 + 0.820)}
CL["ceil_name"] = {"L14": "吸顶灯（取代原 L10 + L14 两个筒灯）"}
CL["notes5"] += " Rev D：原 L10 + L14 两个筒灯改为一个吸顶灯 L14，房间中间略偏门口（离北 950、离西 820，对门洞中线）。"
MB["openings"] = [("door", "主卫入口 F25 一门两用（PD S16 主 762）", o[2], o[3], o[4], o[5]) if o[1].startswith("主卫入口") else
                  ("door", "衣帽间洞口（内装 F27 PD S16 686，框 742）", o[2], o[3], o[4], o[5]) if o[1].startswith("衣帽间洞口") else o for o in MB["openings"]]
CL["openings"] = [("door", "衣帽间洞口（内装 F27 PD S16 686，框 742）",) + tuple(o[2:]) for o in CL["openings"]]

# Rev E (owner 2026-10-08): 一门两用 F25 (PD S16) set out from the maker's plan: basin wall F = 1000 -> partition (139) at y 1.209–1.348;
# F25 opening 832 (762 + 2 x 35) with its hinge-side edge on the partition line (y 0.516–1.348), so the leaf turned 90 deg lies along
# the partition and closes the second opening 742 (H-wall face -> partition end, x 1.092 -> 0.350; PD 47 frame on the partition end).
# Bedroom-side pier for S1 = 516 - 284 = 232 (S1 centred, 116).  W6 behind the H wall is intentional (post in front of the big
# push-out window forms the new opening) — no change.
WALL_REBUILD = {}
WALL_EDITS = {"FF": [("sub", (-0.589, 1.273, 0.428, 1.412)), ("add", (-0.589, 1.209, 0.350, 1.348)),
                     ("add", (1.092, 0.504, 1.230, 0.516)), ("sub", (1.092, 1.334, 1.230, 1.348))]}
BT = ROOMS["FF_主卫"]
for _k in ("FF_主卧", "FF_主卫", "FF_衣帽间"): ROOMS[_k]["rev"] = dict(rev="E")
BT["poly"] = [(-0.589, 0.209), (1.092, 0.209), (1.092, 2.370), (-0.589, 2.370), (-0.589, 1.348), (0.350, 1.348), (0.350, 1.209), (-0.589, 1.209)]
_f = {f[0]: f for f in BT["faces"]}
BT["faces"] = [_f["E"],
               ("F",) + _f["F"][1:3] + ((-0.589, 0.209), (-0.589, 1.209), _f["F"][5]),
               ("G",) + _f["G"][1:3] + ((-0.589, 1.209), (0.350, 1.209), _f["G"][5]),
               _f["H"], _f["I"],
               ("J",) + _f["J"][1:3] + ((-0.589, 1.348), (-0.589, 2.370), _f["J"][5]),
               ("K",) + _f["K"][1:3] + ((0.350, 1.348), (-0.589, 1.348), _f["K"][5])]
_F25 = "F25 一门两用 PD S16（主 762，洞 832）"
BT["openings"] = [("door", _F25 + "，通主卧", (1.092, 1.348), (1.092, 0.516), 0, 2030) if o[0] == "door" else o for o in BT["openings"]]
BT["swings"] = [((1.092, 1.313), (1.092, 0.551), (0.330, 1.313))]     # leaf 762 turned 90 deg onto the partition end (20 on the PD stop)
MB["openings"] = [("door", "主卫入口 " + _F25, (1.230, 0.516), (1.230, 1.348), 0, 2030) if o[1].startswith("主卫入口") else o for o in MB["openings"]]
BT["override"]["S2"] = ("G", 0.150, "Rev E 隔墙缩到 939 后，开关中心离隔墙端头 150（端头装 PD 47 框，面板边离框约 60），h1200")
MB["override"]["S1"] = ("B", 4.070 - 0.116, "主卫入口 F25 洞口与前墙之间 232 宽墙垛正中（各 116）；Rev E 按 PD 一门两用定位后墙垛 232")
BT["notes5"] += (" Rev E（业主 2026-10-08，按 PD S16 一门两用厂家图）：台盆墙 F 净 1000 → 隔墙 139 在 1209–1348；F25 洞 832（762 + 2×35），"
                 "合页侧洞边对齐隔墙线，门扇转 90° 贴隔墙端头，关上副洞 742（H 墙面 → 隔墙端头，隔墙长 939，端头装 PD 47 框）。"
                 "主卧一侧 S1 墙垛 232。磨砂窗 W6 有 145 在隔墙后面是有意的：窗太大，在窗前立柱做新门洞，窗为外推窗，不受影响。")
MB["notes5"] += " Rev E：主卫入口 F25 洞改 516–1348（832），S1 所在墙垛 232，S1 居中 116。"

# Rev F (owner 2026-10-09): F25 and F27 are both PD S16, 1981 high overall -> both openings the same height 2030 (closet opening
# 2252 -> 2030, header infill 222 above); closet opening width 997 kept (F27 frame 742 + side infill 255, detail TBC).
for _k in ("FF_主卧", "FF_主卫", "FF_衣帽间"): ROOMS[_k]["rev"] = dict(rev="F")
for _R in (MB, CL):
    _R["openings"] = [o[:5] + (2030,) if o[1].startswith("衣帽间洞口") else o for o in _R["openings"]]
MB["notes5"] += " Rev F：F25 与 F27 同为 PD S16、总高 1981，两个门洞同高 2030；衣帽间洞口由 2252 降到 2030（上方补墙 222），洞宽 997 不变，F27 框 742 两侧补墙 255 做法待定。"
CL["notes5"] = CL["notes5"].replace("门洞 997×2252", "门洞 997×2030（Rev F 由 2252 降低，与 F25 同高）")

# Rev G (owner 2026-10-09): closet opening = F27 frame 742 wide (686 + 2 x 28) x 2030, hinge-side edge by S5 kept (pier 400);
# C wall: TH under S7 (h1050), C07 970 from the door opening edge (behind dresser F05); D wall: bed F02 is 1800 x 2000 (Y00B89),
# C03 / C04 centred on nightstands F07 / F08, S6 over C04 at h850 (reach from bed).  Window W5 position checked v. owner plan (360 from nib).
for _k in ("FF_主卧", "FF_主卫", "FF_衣帽间"): ROOMS[_k]["rev"] = dict(rev="G")
_CL_OP = "衣帽间门洞 F27 PD S16 686（框 742，洞 742）"
MB["openings"] = [("door", _CL_OP, (1.230, 3.212), (1.230, 3.954), 0, 2030) if o[1].startswith("衣帽间洞口") else o for o in MB["openings"]]
CL["openings"] = [("door", _CL_OP, (1.092, 3.954), (1.092, 3.212), 0, 2030)]
MB["swings"] = [MB["swings"][0], ((1.230, 3.926), (1.230, 3.240), (1.916, 3.926))]
WALL_EDITS["FF"].append(("add", (1.092, 2.957, 1.230, 3.212)))
MB["extra_pts"] = [("C", "TH", "地暖温控面板 UFH thermostat", 240, 1050, "S7 正下方，中心距 S7 150（业主 2026-10-09 调整）；有线温控需穿线到地暖分水器接线中心，无线温控也按此位置留底盒；型号由地暖供应商定", "待定")]
MB["override"]["C07"] = ("C", 3.060 - (0.369 + 0.761 + 0.970), "离房门洞边 970（业主 2026-10-09），在梳妆台 F05 后面，h450")
MB["room_note"].pop("C07", None)
MB["furniture"] = [("床 F02 源氏木语 Y00B89（1800×2000）", [2.199, 0.914, 3.208, 4.199, 2.714, 4.258]) if f[0].startswith("床 F02") else f for f in MB["furniture"]]
MB["override"]["C03"] = ("D", 4.145 - (4.354 - 2.998), "床头柜 F07 正中（业主 2026-10-09：床 1800，插座往外挪到床头柜上方），h650")
MB["override"]["C04"] = ("D", 4.145 - (4.354 - 0.634), "床头柜 F08 正中（业主 2026-10-09），h650")
MB["override"]["S6"] = ("D", 4.145 - (4.354 - 0.634), "床头开关：C04 正上方，h850（业主 2026-10-09，躺在床上够得到）", 850)
CL["notes5"] = CL["notes5"].replace("门洞 997×2030（Rev F 由 2252 降低，与 F25 同高）", "门洞 742×2030（Rev G：按 F27 框 742，S5 一侧洞边不动）")
MB["notes5"] += (" Rev G：衣帽间门洞改 742×2030（F27 框 742），S5 一侧洞边不动，左侧补墙 255；TH 挪到 S7 正下方 h1050；C07 离房门洞边 970；"
                 "床 F02 按 1800×2000；C03 / C04 挪到床头柜正中，S6 在 C04 正上方 h850。窗 W5 位置与业主平面一致（离墙垛端 360，宽 1000）。")

# Rev H (owner 2026-10-09):
# - F27 (closet) opens as the PD drawing: hinge on the far side from S5 (left seen from the bedroom), opening into the bedroom
# - C07 450 from the bedroom-door opening edge
# - 主卫 was one space with 主卧: ceiling 2700, W6 sill 880 / head 2480 like W5
# - G and K run the full width and show the second opening 742 (F25 leaf turned 90 deg closes it; bedroom door -> passage -> second
#   opening is one through-space); H split into H1 (vanity side, with F25) and H2 (WC side); switches for smart WC seat, towel rail
#   and extract fan stacked above S2
# - 衣帽间: ceiling 2700, C09 centred on M, C01 300 from the O-wall corner, faces labelled left / right hand on entering
for _k in ("FF_主卧", "FF_主卫", "FF_衣帽间"): ROOMS[_k]["rev"] = dict(rev="H")
MB["swings"] = [MB["swings"][0], ((1.230, 3.240), (1.230, 3.926), (1.916, 3.240))]
MB["override"]["C07"] = ("C", 3.060 - (0.369 + 0.761 + 0.450), "离房门洞边 450（业主 2026-10-09），h450")
BT["ceil"] = 2700
BT["openings"] = [("window", "磨砂窗 W6 成品 1000×1600（窗台 880，洞延伸到隔墙后）", o[2], o[3], 880, 2480) if o[0] == "window" else o for o in BT["openings"]]
BT["features"] = [f[:5] + (2700,) + f[6:] if f[1].startswith("淋浴段假墙") else f for f in BT["features"]]
_SUB = "副门洞 742（F25 转 90° 关）"
BT["openings"] += [("door", _SUB, (0.350, 1.209), (1.092, 1.209), 0, 2030), ("door", _SUB, (1.092, 1.348), (0.350, 1.348), 0, 2030)]
_f = {f[0]: f for f in BT["faces"]}
BT["faces"] = [_f["E"], _f["F"],
               ("G", "东墙", "隔墙 + 副门洞（盥洗室侧）Partition & second opening, vanity side", (-0.589, 1.209), (1.092, 1.209), ("墙角", "墙角")),
               ("H1", "南墙", "盥洗室侧：通主卧洞口 F25 Wall to bedroom, vanity side", (1.092, 1.348), (1.092, 0.209), ("副门洞边", "墙角")),
               ("H2", "南墙", "卫生间侧：毛巾架墙 Towel-rail wall, WC side", (1.092, 2.370), (1.092, 1.348), ("墙角（假墙）", "副门洞边")),
               _f["I"], _f["J"],
               ("K", "西墙", "隔墙 + 副门洞（卫生间侧）Partition & second opening, WC side", (1.092, 1.348), (-0.589, 1.348), ("墙角", "墙角"))]
BT["override"]["S2"] = ("G", 1.681 - 0.789, "隔墙端头往北 150（端头装 PD 47 框，面板边离框约 60），h1200")
BT["extra_pts"] = [("G", "SM", "智能马桶盖开关（带开关 FCU）", 789, 1350, "S2 正上方，中心距 130；供卫生间 N-WC1 出线面板", "FCU→N-WC1"),
                   ("G", "ST", "电热毛巾架开关（带开关 FCU）", 789, 1480, "SM 正上方，中心距 130；供 N-TR1 出线面板", "FCU→N-TR1"),
                   ("G", "SF", "排风扇开关（风扇隔离开关）", 789, 1610, "ST 正上方，中心距 130；排风扇位置在卫生间天花，现场 / 型号定", "待定")]
BT["notes5"] += (" Rev H：主卫原与主卧同一空间，天花 2700，W6 窗台 880（同 W5）。G / K 立面包含副门洞 742（主门 F25 → 通道 → 副门洞贯通，门扇转 90° 关闭副门洞；"
                 "副门洞上方门头 / 挡条按 PD 厂家）。H 墙分 H1（盥洗室侧，F25）与 H2（卫生间侧，毛巾架）。S2 上方叠放 SM 智能马桶盖、ST 电热毛巾架、SF 排风扇开关（中心距 130）。")
CL["ceil"] = 2700
_hand = {"L": "进门左手边", "M": "进门正对面", "N": "进门右手边", "O": "门墙（进门身后）"}
CL["faces"] = [(f[0], f[1], f"{_hand[f[0]]} · {f[2]}") + tuple(f[3:]) for f in CL["faces"]]
CL["override"]["C09"] = ("M", 1.698 / 2, "M 墙正中（业主 2026-10-09），h450")
CL["override"]["C01"] = ("N", 0.300, "离 O 墙（门墙）墙角 300（业主 2026-10-09），h450")
CL["notes5"] = CL["notes5"].replace("天花 2500", "天花 2700") + " Rev H：天花 2700；站在门口往里看：左手 L、正对 M、右手 N、身后 O（门墙）。C09 在 M 墙正中，C01 离门墙墙角 300。F27 合页在离 S5 远的一侧，开向主卧。"
MB["notes5"] += " Rev H：衣帽间 F27 按 PD 图合页在左（离 S5 远的一侧），开向主卧；C07 离房门洞边 450。"

# Rev J (owner 2026-10-09): SM / ST / SF in one row 150 above S2 (h1350, 130 c/c, running left from S2); lights: L04 on the bed
# centre line, a little towards the foot; L14 on the closet-door centre line; extract fan in the WC zone above the WC (purple mark).
for _k in ("FF_主卧", "FF_主卫", "FF_衣帽间"): ROOMS[_k]["rev"] = dict(rev="J")
BT["extra_pts"] = [("G", "SM", "智能马桶盖开关（带开关 FCU）", 529, 1350, "S2 上方一排三个（中心距 130，离地 1350）；供卫生间 N-WC1 出线面板", "FCU→N-WC1"),
                   ("G", "ST", "电热毛巾架开关（带开关 FCU）", 659, 1350, "S2 上方一排三个；供 N-TR1 出线面板", "FCU→N-TR1"),
                   ("G", "SF", "排风扇开关（风扇隔离开关）", 789, 1350, "S2 正上方，中心距 150；控制卫生间天花排风扇 EF", "待定")]
BT["ceil_items"] = [dict(id="EF", name="排风扇（卫生间，马桶上方；SF 控制）", p=(0.674, 1.719), cat="light")]
MB["ceil_move"] = {"L04": (2.350, 1.814)}
CL["ceil_move"] = {"L14": (-0.589 + 0.950, (3.212 + 3.954) / 2)}
BT["notes5"] += " Rev J：SM / ST / SF 改为 S2 上方一排（h1350，中心距 130，SF 在 S2 正上方）；卫生间天花加排风扇 EF（马桶上方，位置按业主标记，型号待定）。"
MB["notes5"] += " Rev J：主灯 L04 挪到床中线上、略往床尾（离北墙 1120）。"
CL["notes5"] += " Rev J：L14 对准衣帽间门洞中线。"

# Rev K (owner 2026-10-09): the purple mark was L13's new place (one light in the WC zone, not a second fitting) -> L13 moved there,
# EF dropped (fan position TBC); remove the model's old F27 infill stub (y 3.792–3.954) that now sits inside the 742 closet opening.
for _k in ("FF_主卧", "FF_主卫", "FF_衣帽间"): ROOMS[_k]["rev"] = dict(rev="K")
BT["ceil_items"] = []
BT["ceil_move"] = {"L13": (0.674, 1.719)}
BT["extra_pts"] = [e if e[1] != "SF" else e[:5] + ("S2 正上方，中心距 150；排风扇位置 / 型号待定", "待定") for e in BT["extra_pts"]]
WALL_EDITS["FF"].append(("sub", (1.092, 3.212, 1.232, 3.954)))
BT["notes5"] = BT["notes5"].replace("卫生间天花加排风扇 EF（马桶上方，位置按业主标记，型号待定）。", "") + " Rev K：L13 挪到卫生间马桶上方（业主标记位置），卫生间只有这一个灯；排风扇位置待定。"
CL["notes5"] += " Rev K：去掉衣帽间门洞内多余的旧门垛（模型旧 F27 补墙）。"

# Rev L (owner 2026-10-09): SM / ST / SF row raised to h1500; note box on G: better place on site is acceptable
for _k in ("FF_主卧", "FF_主卫", "FF_衣帽间"): ROOMS[_k]["rev"] = dict(rev="L")
BT["extra_pts"] = [e[:4] + (1500,) + (e[5].replace("S2 上方一排三个（中心距 130，离地 1350）", "S2 上方一排三个（中心距 130，离地 1500）").replace("S2 正上方，中心距 150", "S2 正上方，离地 1500"),) + e[6:] for e in BT["extra_pts"]]
BT["features"] = BT.get("features", []) + [("G", "注：SM / ST / SF 为建议位置（离地 1500）。|如现场有更合适的位置（方便使用、避开管线），|可与业主确认后换到别的位置。", 40, 900, 1900, 2250, "note")]
BT["notes5"] += " Rev L：SM / ST / SF 改离地 1500；位置为建议位，现场有更好位置可与业主确认后调整。"

# ---------------- 副客厅 (CGI site G03a-c / P03; old data: 客厅) — ground floor, model v44 ----------------------------------
# faces / openings: v44 skirting + evaluated GF_Wall_Shell (booleans) + ray casts; old front window is infilled (Wall_GF_OldWindow_Infill)
ROOMS["GF_副客厅"] = dict(
    F="GF", cn="副客厅", en="Second living room", sheet0=1, fz=0.0, ceil=2600, skirt=144, cove=90, rev=dict(rev="B"),
    poly=[(-1.665, 1.519), (-4.290, 1.519), (-4.290, 7.899), (-1.895, 7.899), (-1.895, 6.274), (-0.775, 6.274), (-0.775, 0.959),
          (-1.549, 0.959), (-1.549, 1.404), (-1.665, 1.404)],
    faces=[
        ("A", "西墙", "前门墙 Front door wall", (-1.665, 1.519), (-4.290, 1.519), ("墙端（阳角）", "墙角")),
        ("B", "北墙", "书柜 / 沙发长墙 North wall", (-4.290, 1.519), (-4.290, 7.899), ("墙角", "墙角")),
        ("C", "东墙", "花园门墙 Garden door wall", (-4.290, 7.899), (-1.895, 7.899), ("墙角", "墙角")),
        ("D", "南墙", "洗手间门墙 WC door wall", (-1.895, 7.899), (-1.895, 6.274), ("墙角", "墙端（阳角）")),
        ("E", "东墙", "洗手间外侧墙（电梯后）Wall behind lift", (-1.895, 6.274), (-0.775, 6.274), ("墙端（阳角）", "墙角")),
        ("F", "南墙", "电视 / 暗门 / 电梯墙 TV wall", (-0.775, 6.274), (-0.775, 0.959), ("墙角", "墙角")),
        ("G", "西墙", "前端凹位墙 Front recess wall", (-0.775, 0.959), (-1.549, 0.959), ("墙角", "墙角")),
        ("H", "北墙", "凹位侧墙 Recess side wall", (-1.549, 0.959), (-1.549, 1.404), ("墙角", "墙端（阳角）")),
    ],
    openings=[("door", "前门 双扇（主扇约 790 + 副扇约 495）", (-1.812, 1.519), (-3.215, 1.519), 0, 2051),
              ("window", "侧窗 SP 450（下段固定玻璃，上段开扇）", (-3.995, 7.899), (-3.545, 7.899), 0, 2012),
              ("door", "花园门 双扇法式门 1200（外开）", (-3.545, 7.899), (-2.345, 7.899), 0, 2012),
              ("door", "洗手间门 620（洞 680）", (-1.895, 7.604), (-1.895, 6.924), 0, 2032),
              ("door", "暗门 V15（通餐厅）", (-0.775, 5.404), (-0.775, 4.294), 0, 2032)],
    swings=[((-1.895, 7.574), (-1.895, 6.954), (-2.515, 7.574))],      # WC door opens into the room (DoorLeaf_WC200)
    furniture=[("L 形沙发 G14", [-4.275, 1.713, 0.002, -2.673, 4.215, 0.854]), ("玻璃门书柜 G18", [-4.265, 4.854, 0.002, -3.794, 5.614, 1.962]),
               ("玻璃门书柜 G17", [-4.265, 5.654, 0.002, -3.794, 7.174, 1.962]), ("电视柜 G22", [-1.21, 2.064, 0.089, -0.86, 3.864, 0.452]),
               ("电视（占位）", [-1.017, 2.239, 0.454, -0.972, 3.689, 1.274]),
               ("家用电梯 Duo Classic（穿楼板）", [-1.737, 5.388, 0.045, -0.813, 6.28, 2.12])],
    override={},
    room_note={"C11": "⚠ 在家用电梯 Duo Classic 外壳后面（外壳离墙约 40），插头插不进、也检修不到 —— 待业主定：挪出电梯范围或取消",
               "C28": "⚠ 在 L 形沙发 G14（高 854，到距左端 2696）后面会被挡住 —— 待业主定；v44 点位审阅模型有建议位 PR_GF_C28_new：沙发端头与书柜 G18 之间，约距左端 2850",
               "C18": "⚠ 中心离门洞边仅约 100，门套外沿约 45，双联面板（146 宽）会压到门套 —— 建议挪到离门洞边 ≥ 250（v44 点位审阅模型原位约 250），待业主确认；数据里房间写「储物间」，按位置在副客厅前门北侧",
               "C30": "数据里房间写「储物间」，按位置在电视墙（电视柜左端）",
               "S9": "数据写「储物间门旁」；按模型 v44 是副客厅前门北侧，离门洞边约 150",
               "S8": "点位数据原点离墙面 290，已按墙面定位；离暗门洞边约 160",
               "S10": "洗手间门外，离门洞边约 140",
               "S11": "⚠ 按点位数据落在侧窗 SP 的玻璃上（侧窗 450 是 v44 新加的）—— 待业主定：挪到侧窗北边 295 宽墙段正中（距左端约 150），或花园门南边 450 宽墙段",
               "C16": "在电视（占位，离墙约 200，立面未画）后面", "C29": "在电视（占位，离墙约 200，立面未画）后面"},
    ceil_labels=((-4.13, 4.5), (-2.35, 6.95)),
    ceil_zones=[("电梯 Duo Classic：穿楼板开洞按厂家图（模型 v44 天花未开洞）", (-1.737, 5.388, -0.813, 6.28))],
    notes5="5. 副客厅 = 原数据的「客厅」（CGI 网站 G03a–c / 全景 P03）。墙面、门窗洞、家具按模型 v44：前墙旧窗已封（Wall_GF_OldWindow_Infill），前门为双扇外门；后墙花园门 1200 + 侧窗 450；南侧暗门 V15 通餐厅；家用电梯 Duo Classic 贴南墙。一层天花 2600、平顶无梁。前端凹位（774×560）及两处约 115 的小转角不另出立面以外的详图。楼下洗手间作为本套第二空间，见 W1-02（业主 2026-10-08）。专用 / FCU 点、户外 EV 充电桩与户外插座 C34 不在本图。",
)

# Rev C (owner 2026-10-08): hidden door V15 -> 762 leaf (opening 828 = 762 + 66, as 次卧); edge by S8 kept, edge by the lift moves
# 282 towards the door (lift to opening now ~266 instead of ~16).  C11 (behind the lift casing) -> D wall, by the outer corner.
LR = ROOMS["GF_副客厅"]
LR["rev"] = dict(rev="C")
LR["openings"][-1] = ("door", "暗门 V15 762（门扇，通餐厅）", (-0.775, 5.122), (-0.775, 4.294), 0, 2032)
LR["override"]["C11"] = ("D", 0.150, "从电梯外壳后面挪到 D 墙右端阳角旁（业主 2026-10-08）：中心离右端 150，离地 450，方便插拔")
LR["room_note"].pop("C11", None)
LR["room_note"]["S8"] = "点位数据原点离墙面 290，已按墙面定位；离暗门洞边约 160（Rev C 暗门改 762 后此边不动）"
LR["notes5"] += " Rev C：暗门 V15 改 762 门扇，洞 828×2032（S8 侧洞边不动）；C11 挪到 D 墙右端旁（离端 150，h450）。"

# Rev D (owner sketch 2026-10-08): C wall — side window SP 450 + 255 pier + French door 1200 become ONE garden-door unit 1650
# (same 295 / 450 wall ends, head 2012): fixed side light | French pair (opens out) | fixed side light; side lights with a rail
# ~1100 as sketched.  Pier removed -> new lintel over 1650 (structural engineer).  S11 was in the glass -> centre of the 295 pier.
# WC door -> 686 x 1981 (F27 type), opening 756 (686 + 70, as 次卧卫浴); S10-side edge kept, hinge side grows 76.
LR["rev"] = dict(rev="D")
_C_UNIT = "花园门组 1650（侧亮 + 法式双开门 + 侧亮）"
LR["openings"] = [o for o in LR["openings"] if not o[1].startswith(("侧窗 SP", "花园门"))]
LR["openings"].insert(1, ("door", _C_UNIT, (-3.995, 7.899), (-2.345, 7.899), 0, 2012))
LR["op_design"] = {_C_UNIT: dict(cuts=[410, 825, 1240], rails={0: [1100], 3: [1100]},
                                 labels=["侧亮 固定", "法式门扇|外开", "法式门扇|外开", "侧亮 固定"])}
LR["override"]["S11"] = ("C", 2.395 - 0.1475, "原位落在新花园门组玻璃上 → 挪到左端 295 宽墙段正中（离左端 148），离地 1200 —— 待业主确认")
LR["room_note"].pop("S11", None)
_WC_DOOR = "洗手间门 F27 686×1981（洞 756）"
LR["openings"] = [("door", _WC_DOOR, (-1.895, 7.680), (-1.895, 6.924), 0, 2032) if o[1].startswith("洗手间门") else o for o in LR["openings"]]
LR["swings"] = [((-1.895, 7.650), (-1.895, 6.964), (-2.581, 7.650))]
LR["room_note"]["S10"] = "洗手间门外，离门洞边约 140（Rev D 门改 686 后此边不动）"
LR["notes5"] += " Rev D：C 墙改一樘花园门组 1650×2012（侧亮 410｜法式双开 415+415 外开｜侧亮 410，侧亮中横档 h1100，成品待门窗厂复核；拆 255 墙垛需新过梁，结构工程师确认）；S11 挪到左端 295 墙段正中；洗手间门改 F27 686，洞 756（S10 侧洞边不动）。"

# ---------------- 楼下洗手间 (CGI site G08; old data: 卫生间) — second space of the 副客厅 set, like 次卧 + 次卧卫浴 ----------------
ROOMS["GF_楼下洗手间"] = dict(
    F="GF", cn="楼下洗手间", en="Ground-floor WC", sheet0=2, fz=0.0, ceil=2600, skirt=144, cove=90, rev=dict(rev="A"), plan_kind="带洁具",
    poly=[(-1.775, 6.394), (-0.775, 6.394), (-0.775, 7.899), (-1.775, 7.899)],
    faces=[("A", "西墙", "台盆墙 Basin wall", (-0.775, 6.394), (-1.775, 6.394), ("墙角", "墙角")),
           ("B", "北墙", "门墙 Door wall（副客厅一侧是 D 墙）", (-1.775, 6.394), (-1.775, 7.899), ("墙角", "墙角")),
           ("C", "东墙", "后窗 / 马桶墙 Rear window & WC wall", (-1.775, 7.899), (-0.775, 7.899), ("墙角", "墙角")),
           ("D", "南墙", "南侧墙 South wall", (-0.775, 7.899), (-0.775, 6.394), ("墙角", "墙角"))],
    openings=[("window", "后窗（独立小窗）600", (-1.575, 7.899), (-0.975, 7.899), 1452, 2012),
              ("door", "门 620（洞 680，开向副客厅）", (-1.775, 7.604), (-1.775, 6.924), 0, 2032)],
    swings=[],                       # the door swings into 副客厅 (see W1-01-0)
    furniture=[("台盆 G19", [-1.54, 6.409, 0.002, -1.01, 6.939, 0.836]), ("马桶 G20", [-1.455, 7.204, 0.022, -1.095, 7.814, 0.808])],
    water=[("WC-G", "马桶 WC（G20，后墙）", "冷水（软水）15；110 污水", (-1.27, 7.62)),
           ("B-G", "台盆 Basin（G19，西墙）", "冷 / 热（软水）15；32 废水", (-1.27, 6.67))],
    override={}, room_note={},
    ceil_labels=((-1.70, 7.12), (-0.90, 7.12)),
    notes5="5. 楼下洗手间 = 原数据的「卫生间」（CGI 网站 G08）。墙面、门窗、洁具按模型 v44；本房间无梁、无假墙，天花 2600。后窗为独立小窗 600（窗台 1452、洞顶 2012）。门 620（洞 680）开向副客厅，开关 S10 在门外副客厅 D 墙（W1-01-4）。无电热毛巾架（业主 2026-10-08）。给排水预留口：给排水施工图 Rev C 只定了洁具、管径和走向，没有定出口位置 / 高度 —— 按所选洁具安装说明现场定，本图不画。点位数据里本房间没有插座，也没有排风扇 —— 是否加排风扇待业主定。",
)

# Rev E (owner sketch 2026-10-08): front door (A wall) -> ONE 1200 leaf, hinged at the mullion (left in the elevation), with a
# fixed side panel 203 in the rest of the existing 1403 opening; latch edge by C18 / S9 unchanged.
LR["rev"] = dict(rev="E")
_FD = "前门 1200 单扇 + 固定侧板"
LR["openings"] = [("door", _FD, (-1.812, 1.519), (-3.215, 1.519), 0, 2051) if o[1].startswith("前门") else o for o in LR["openings"]]
LR["op_design"][_FD] = dict(cuts=[203], kinds=["solid", "solid"], swing=(1, "L"), labels=["固定|侧板", "前门扇 1200|合页在左（侧板一侧）|向内开（待定）"])
LR["swings"].append(((-2.015, 1.519), (-3.215, 1.519), (-2.015, 2.719)))
LR["room_note"]["C18"] = LR["room_note"]["C18"] + "（Rev E 前门改 1200 单扇，此洞边不动）"
LR["notes5"] += " Rev E：前门改 1200 单扇（洞 1403 不变：固定侧板 203｜门扇 1200，合页在侧板一侧）；⚠ 若向内开，门扇扫到 L 形沙发 G14（离墙约 190）—— 待业主定外开或挪沙发。"

# Rev F (owner 2026-10-08): C28 out from behind sofa G14 -> 3000 from the B-wall left corner (between sofa end ~2696 and G18 ~3335)
LR["rev"] = dict(rev="F")
LR["override"]["C28"] = ("B", 6.380 - 3.000, "从 L 形沙发后面挪出（业主 2026-10-08）：中心离左端墙角 3000，在沙发端头（约 2696）与书柜 G18（约 3335）之间，离地 450")
LR["room_note"].pop("C28", None)
LR["notes5"] += " Rev F：C28 挪到 B 墙离左端 3000（沙发与书柜 G18 之间），h450。"

# Rev G (owner 2026-10-08): (1) front door opening = 1200 overall, single leaf, no side panel; latch edge by C18 / S9 kept.
# (2) TV sockets C16 / C29 / C30 grouped round C29 (unchanged, 3410 from left), 100 clear between plates (146 wide -> 246 c/c).
# (3) garden-door unit widened to 2100, from the 295 pier right up to the D-wall corner (450 pier removed).
LR["rev"] = dict(rev="G")
LR["openings"] = [o for o in LR["openings"] if o[1] != _FD]
_FD = "前门 单扇（洞 1200）"
LR["openings"].insert(0, ("door", _FD, (-2.015, 1.519), (-3.215, 1.519), 0, 2051))
LR["op_design"].pop("前门 1200 单扇 + 固定侧板", None)
LR["op_design"][_FD] = dict(cuts=[], kinds=["solid"], swing=(0, "L"), labels=["前门扇|合页在左|向内开（待定）"])
LR["swings"][-1] = ((-2.015, 1.519), (-3.215, 1.519), (-2.015, 2.719))
for pid, s_mm in [("C16", 3164), ("C29", 3410), ("C30", 3656)]:
    LR["override"][pid] = ("F", 5.315 - s_mm / 1000, "电视插座三个一组，以 C29 为中，面板之间净距 100（中心距 246），离地 600（业主 2026-10-08）")
LR["openings"] = [o for o in LR["openings"] if o[1] != _C_UNIT]
_C_UNIT = "花园门组 2100（侧亮 + 法式双开门 + 侧亮）"
LR["openings"].insert(1, ("door", _C_UNIT, (-3.995, 7.899), (-1.895, 7.899), 0, 2012))
LR["op_design"] = {k: v for k, v in LR["op_design"].items() if not k.startswith("花园门组")}
LR["op_design"][_C_UNIT] = dict(cuts=[525, 1050, 1575], rails={0: [1100], 3: [1100]},
                                labels=["侧亮 固定", "法式门扇|外开", "法式门扇|外开", "侧亮 固定"])
LR["notes5"] += (" Rev G：前门洞改 1200 整樘单扇（无侧板，C18 / S9 一侧洞边不动，左侧墙段 147 → 350）；"
                 "电视插座 C16 / C29 / C30 以 C29 为中三个一组，面板净距 100；"
                 "花园门组改 2100×2012，从左端 295 墙段一直到 D 墙墙角（原 450 墙段取消，侧亮 / 门扇各 525，按草图暂分，门窗厂复核；门框贴 D 墙需留框边，过梁 2100 结构工程师确认）。")

# Rev B (楼下洗手间, owner 2026-10-08): door -> F27 686 x 1981, opening 756 — same opening as 副客厅 D wall (Rev D)
WC = ROOMS["GF_楼下洗手间"]
WC["rev"] = dict(rev="B")
WC["openings"] = [("door", "门 F27 686×1981（洞 756，开向副客厅）", (-1.775, 7.680), (-1.775, 6.924), 0, 2032) if o[0] == "door" else o for o in WC["openings"]]
WC["notes5"] = WC["notes5"].replace("门 620（洞 680）开向副客厅", "门 F27 686×1981（洞 756，Rev B）开向副客厅")

# ---------------- 中间书房 (CGI site F03 / P11; old data: 卧室 3; owner calls it 书房1) — first floor, model v44 ----------------
# faces / openings: evaluated FF_Wall_Shell + ray casts; door wall has a small 100 / 60 two-step jog at its south end (not drawn as faces)
ROOMS["FF_中间书房"] = dict(
    F="FF", cn="中间书房", en="Middle study", sheet0=4, fz=3.208, ceil=2500, skirt=144, cove=90, rev=dict(rev="A"),
    poly=[(-0.590, 5.524), (1.502, 5.524), (1.502, 5.624), (1.563, 5.624), (1.563, 5.684), (2.460, 5.684), (2.460, 7.929), (-0.590, 7.929)],
    faces=[
        ("A", "西墙", "房门墙 Entrance door wall", (1.502, 5.524), (-0.590, 5.524), ("墙角（南端墙面凸出 100 / 160 两级）", "墙角")),
        ("B", "北墙", "沙发墙 Sofa wall", (-0.590, 5.524), (-0.590, 7.929), ("墙角", "墙角")),
        ("C", "东墙", "后窗 / 空调墙 Rear window & A/C wall", (-0.590, 7.929), (2.460, 7.929), ("墙角", "墙角")),
        ("D", "南墙", "书桌墙 Desk wall", (2.460, 7.929), (2.460, 5.684), ("墙角", "墙角")),
    ],
    openings=[("window", "后窗 成品 1000×1600（窗台约 500）", (-0.391, 7.929), (0.628, 7.929), 501, 2100),
              ("door", "房门（洞 927）", (1.390, 5.524), (0.463, 5.524), 0, 2030)],
    swings=[((1.381, 5.524), (0.493, 5.524), (1.381, 6.412))],      # hinge on the south jamb, opens into the room (DoorLeaf.009)
    furniture=[("沙发 F09", [-0.544, 5.834, 3.298, 0.356, 7.734, 4.138]), ("升降书桌 F21a", [1.743, 6.173, 3.263, 2.446, 7.375, 3.974]),
               ("空调内机", [0.742, 7.74, 5.266, 1.558, 7.929, 5.545])],
    override={},
    room_note={"C12": "⚠ 中心离门洞边约 100，双联面板会贴近门套 —— 现场核对，必要时往北挪",
               "C24": "⚠ 面板下沿离窗洞顶约 47 —— 现场核对",
               "C13": "离东墙角约 100；沙发 F09 端头外约 100"},
    ceil_labels=((-0.50, 6.0), (2.30, 5.80)),
    notes5="5. 中间书房 = 原数据的「卧室 3」（CGI 网站 F03 / 全景 P11；业主叫「书房1」）。墙面、门窗洞、家具按模型 v44：后窗 1000×1600（窗台约 500），后墙窗南侧为平齐补墙；房门洞 927×2030，合页在南侧、向房间内开。门墙南端有 100 / 60 两级小凸出，不另出立面。天花按模型 2500（主卧已按业主改约 2700，本房是否同样待业主确认）。开关 S8 在门外走廊，不在本图。",
)


# Rev B (owner 2026-10-09): door = 762 in the old frame (same note as corridor F); C12 -> twin socket ~200 from the door opening edge;
# C13 300 from the east corner; C24 (A/C, h2190) moved off the window, 250 from its edge; desk-wall sockets C10 / C11 at h450.
MS = ROOMS["FF_中间书房"]
MS["rev"] = dict(rev="B")
MS["openings"] = [("door", "房门 762（按老门框，洞 927 暂定）", o[2], o[3], o[4], o[5]) if o[1].startswith("房门") else o for o in MS["openings"]]
MS["features"] = MS.get("features", []) + [("A", "注：房门按老门框装 762 门。|门洞 927 为暂定数字（按模型），|可能有误差，现场量老门框后确认。", 80, 1260, 2060, 2440, "note")]
MS["drop"] = {"C12"}
MS["extra_pts"] = [("A", "C12", "双联插座 Twin socket", 1039 + 200, 450, "业主 2026-10-09：改双联；中心离门洞边约 200，h450", "WX6", "socket", "double")]
MS["override"].update({
    "C13": ("B", 0.300, "中心离东墙角 300（业主 2026-10-09），h450"),
    "C24": ("C", 3.050 - (1.218 + 0.250), "空调插座：与窗错开，中心离窗洞边 250（业主 2026-10-09），h2190；在空调内机范围内，现场按内机接线位置核对"),
    "C10": ("D", 2.245 - 0.684, "书桌墙：由台面上方改到离地 450（书桌下方，业主 2026-10-09）", 450),
    "C11": ("D", 2.245 - 1.698, "书桌墙：由台面上方改到离地 450（书桌下方，业主 2026-10-09）", 450),
})
for _k in ("C12", "C24", "C13"): MS["room_note"].pop(_k, None)
MS["circ_set"] = {k: "WX6A" for k in ("C10", "C11", "C13", "C26")}
MS["extra_pts"] = [e[:6] + ("WX6A",) + e[7:] for e in MS["extra_pts"]]
MS["features"] += [("D", "注：本房间插座单独走一路插座线（新回路暂记 WX6A，|编号由电工定），不与其他房间共用；|空调插座 C24 仍为专用回路 WP3。", 80, 1500, 2060, 2440, "note")]
MS["rev"] = dict(rev="C")
MS["extra_pts"] = MS["extra_pts"] + [("A", "TH", "地暖温控面板 UFH thermostat", 1346, 1200, "S10 右侧同高，中心距 150（业主 2026-10-09）；有线温控需穿线到地暖分水器接线中心，无线温控也按此位置留底盒；型号由地暖供应商定", "待定")]
MS["notes5"] += " Rev C：S10 右侧加地暖温控面板 TH（同高 1200，中心距 150）。"
MS["notes5"] += " 本房间插座（C10 / C11 / C12 / C13 / C26）单独走一路插座线（暂记 WX6A，编号由电工定），不与 C15–C18 共用原 WX6；空调插座 C24 仍为专用 WP3。"
MS["notes5"] += " Rev B：房门按老门框装 762（洞 927 暂定）；C12 改双联、离门洞边约 200；C13 离东墙角 300；C24 与窗错开（离窗洞边 250）；书桌墙 C10 / C11 改离地 450。"

# ---------------- 后书房 (CGI site F04 / P12; old data: 卧室 4) + 后房窄卫浴 (F08) — LIVE Blender model (owner 2026-10-08: the model is
# the latest; the CGI site still shows the old desk layout). Rear floor is lower: FFL = structural 2.852, ceiling 5.708 -> 2856.
ROOMS["FF_后书房"] = dict(
    F="FF", cn="后书房", en="Rear study", sheet0=5, fz=2.852, ceil=2856, skirt=144, cove=90, rev=dict(rev="A"),
    poly=[(1.285, 8.104), (4.290, 8.104), (4.290, 8.960), (3.270, 8.960), (3.270, 11.569), (1.285, 11.569)],
    faces=[
        ("A", "西墙", "房门墙 Entrance door wall", (4.290, 8.104), (1.285, 8.104), ("墙角", "墙角")),
        ("B", "北墙", "窗墙 Window wall", (1.285, 8.104), (1.285, 11.569), ("墙角", "墙角")),
        ("C", "东墙", "后墙 Rear wall", (1.285, 11.569), (3.270, 11.569), ("墙角", "墙角")),
        ("D", "南墙", "卫浴门隔墙 En-suite partition", (3.270, 11.569), (3.270, 8.960), ("墙角", "墙端（阳角）")),
        ("E", "东墙", "衣柜侧墙 Wardrobe end wall", (3.270, 8.960), (4.290, 8.960), ("墙端（阳角）", "墙角")),
        ("F", "南墙", "衣柜后墙 Wardrobe back wall", (4.290, 8.960), (4.290, 8.104), ("墙角", "墙角")),
    ],
    openings=[("door", "房门 Rear215（门扇约 690）", (3.373, 8.104), (2.540, 8.104), 0, 2060),
              ("window", "窄高窗 476（窗台 1560，窗下补墙）", (1.285, 8.248), (1.285, 8.724), 1560, 2100),
              ("window", "窗（窗台约 800）", (1.285, 9.110), (1.285, 10.130), 800, 2100),
              ("door", "卫浴门（洞 690，开向书房）", (3.270, 9.800), (3.270, 9.110), 0, 2040)],
    swings=[((3.342, 8.104), (2.652, 8.104), (3.342, 8.794)), ((3.270, 9.800), (3.270, 9.160), (2.630, 9.800))],
    furniture=[("床（占位，未选定）", [1.29, 10.11, 2.852, 3.27, 11.51, 3.902]), ("衣柜 F24（折叠门）", [3.693, 8.12, 2.922, 4.28, 8.94, 4.952]),
               ("排水立管箱 S2 200×200（柜内）", [4.09, 8.2, 2.852, 4.29, 8.4, 4.052])],
    override={},
    extra_pts=[("D", "FS", "排风扇开关 Extract fan switch（卫浴）", 2119, 2250, "⚠ 模型 v44 有（NAB15，卫浴门上方书房一侧），点位数据里没有 —— 按模型画出，待业主确认；排风扇本体按产品定", "待定")],
    room_note={"C14": "空调插座；模型 v44 本房间没有空调内机，内机位置 / 是否保留待业主定",
               "C15": "⚠ 床（占位，床架高约 1050）贴北墙，插座在床侧后面 —— 床未选定，待业主定",
               "C16": "⚠ 在床头（占位）后面 —— 床未选定，待业主定；若作床头插座，高度按床头柜面 + 150"},
    ceil_labels=((1.36, 8.30), (3.05, 10.30)),
    notes5="5. 后书房 = 原数据的「卧室 4」（CGI 网站 F04 / 全景 P12）。按 Blender 当前模型画（业主 2026-10-08：模型是最新状态，网站相册是旧的书桌布置）：现放床（占位，未选定）；西南角衣柜 F24（折叠门），柜内有排水立管 S2 箱 200×200×1200（顶上 AAV 检修口）。后部地面比前部低：本图 FFL = 结构 2.852，天花 2856。北墙主窗（窗台约 800）+ 窄高窗（窗台 1560，窗下补墙）。房门 Rear215 外有台阶上前部平台。卫浴见 W2-06。",
)

ROOMS["FF_后房窄卫浴"] = dict(
    F="FF", cn="后房窄卫浴", en="Rear en-suite", sheet0=6, fz=2.852, ceil=2856, skirt=144, cove=90, rev=dict(rev="A"), plan_kind="带洁具",
    poly=[(3.380, 9.070), (4.290, 9.070), (4.290, 11.569), (3.380, 11.569)],
    faces=[("A", "西墙", "西端墙 West end wall", (4.290, 9.070), (3.380, 9.070), ("墙角", "墙角")),
           ("B", "北墙", "门墙 / 隔墙 Door wall（书房一侧是 D 墙）", (3.380, 9.070), (3.380, 11.569), ("墙角", "墙角")),
           ("C", "东墙", "淋浴端墙 Shower end wall", (3.380, 11.569), (4.290, 11.569), ("墙角", "墙角")),
           ("D", "南墙", "洁具墙（外墙）Fixture wall", (4.290, 11.569), (4.290, 9.070), ("墙角", "墙角"))],
    openings=[("door", "门（洞 690，开向书房）", (3.380, 9.110), (3.380, 9.800), 0, 2040)],
    swings=[],                       # the door swings into 后书房 (see W2-05-0)
    furniture=[("马桶 F25", [3.705, 9.27, 2.872, 4.29, 9.63, 3.632]), ("台盆 F26（挂墙）", [3.99, 9.91, 3.642, 4.29, 10.29, 3.822]),
               ("淋浴区 F28（淋浴盘 760×740）", [3.53, 10.77, 2.852, 4.29, 11.51, 4.854])],
    water=[("WC3", "马桶 WC（F25，南墙）", "冷水（软水）15；110 污水", (4.05, 9.45)),
           ("B3", "台盆 Basin（F26，南墙）", "冷 / 热（软水）15；32 废水", (4.14, 10.10)),
           ("SH3", "淋浴 Shower（F28，东端）", "冷 / 热（软水）15；40 废水", (3.95, 11.10))],
    override={}, room_note={},
    ceil_labels=((3.45, 9.20), (4.20, 9.20)),
    notes5="5. 后房窄卫浴（CGI 网站 F08）。按 Blender 当前模型：净 910×2499，天花 2856，完成地面比书房高约 8；无窗。马桶、台盆在南墙（外墙），淋浴区在东端（淋浴盘 760×740，模型里混水阀约 h1050、顶喷约 h1970，仅示意）。门洞 690 开向书房，开关 S14 和排风扇开关在书房 D 墙。给排水预留口：给排水施工图 Rev C 只定了洁具、管径和走向，没有定出口位置 / 高度 —— 按所选洁具安装说明现场定，本图不画。",
)


# ---------------- 二楼走廊 (CGI site F09a 楼梯与走廊 + F09b 电梯旁走廊; old data: 走廊 / 电梯 / 楼梯) — LIVE Blender model --------------
# One space at the front FFL 3.208: corridor + lift alcove (north end) + stair landing (south end). The stair opening and the steps down to
# 后书房 are inside the outline (so ceiling lights over them get dimensions) but their balustrade / lower walls are not elevations here.
ROOMS["FF_二楼走廊"] = dict(
    F="FF", cn="二楼走廊", en="First-floor corridor & landing", sheet0=7, fz=3.208, ceil=2500, skirt=144, cove=90, rev=dict(rev="A"), plan_k=25.0, ceil_fs=1.9,
    poly=[(-1.884, 4.474), (2.460, 4.474), (2.460, 4.574), (2.592, 4.574), (2.592, 4.474), (4.290, 4.474), (4.290, 7.966), (2.580, 7.966),
          (2.580, 5.494), (2.460, 5.494), (2.460, 5.564), (1.563, 5.564), (1.563, 5.404), (-0.650, 5.404), (-0.650, 5.524), (-0.710, 5.524),
          (-0.710, 6.279), (-1.884, 6.279)],
    faces=[
        ("A", "西墙", "主卧旧门封墙 Old door infill (master)", (4.290, 4.474), (2.592, 4.474), ("墙角", "墙垛（凸出 100）")),
        ("B", "西墙", "主卧门墙 Master bedroom door wall", (2.460, 4.474), (-1.884, 4.474), ("墙垛（凸出 100）", "墙角")),
        ("C", "北墙", "北端 · 次卧门 North end", (-1.884, 4.474), (-1.884, 6.279), ("墙角", "墙角")),
        ("D", "东墙", "电梯后墙 Wall behind lift", (-1.884, 6.279), (-0.710, 6.279), ("墙角", "墙角")),
        ("E", "南墙", "电梯侧墙 Lift side wall", (-0.710, 6.279), (-0.710, 5.524), ("墙角", "墙端（阳角）")),
        ("F", "东墙", "中间书房门墙 Middle-study door wall", (-0.650, 5.404), (1.563, 5.404), ("墙角", "墙角")),
        ("G", "东墙", "中间书房外墙 Middle-study wall", (1.563, 5.564), (2.460, 5.564), ("墙角", "墙端")),
        ("H", "南墙", "楼梯口墙 Stair-head wall", (2.580, 6.855), (2.580, 5.494), ("下行台阶起点", "墙端")),
        ("I", "南墙", "楼梯平台外墙 Landing outer wall", (4.290, 5.374), (4.290, 4.474), ("楼梯栏杆端", "墙角")),
    ],
    openings=[("door", "主卧门（洞 761）", (2.360, 4.474), (1.599, 4.474), 0, 2040),
              ("door", "次卧门 828（见次卧图）", (-1.884, 4.474), (-1.884, 5.302), 0, 2031),
              ("door", "中间书房门（洞 927）", (0.463, 5.404), (1.390, 5.404), 0, 2030)],
    swings=[],
    furniture=[("家用电梯 Duo Classic 轿厢升到二层时的位置", [-1.737, 5.388, 3.208, -0.813, 6.28, 5.33])],
    override={},
    room_note={"S8": "走廊北端，中间书房门左侧",
               "S11": "楼梯口；离下行台阶起点约 970",
               "C02": "楼梯平台外墙；离墙角约 325"},
    ceil_labels=((2.95, 5.62), (2.72, 5.62)),
    ceil_zones=[("天窗", (-1.555, 4.684, -0.975, 5.864)),
                ("楼梯洞口（下方楼梯）", (3.39, 5.374, 4.29, 7.966)),
                ("下行台阶 → 后书房", (2.58, 6.855, 3.39, 7.966))],
    notes5="5. 二楼走廊 = CGI 网站「楼梯与走廊」(F09a) +「电梯旁走廊」(F09b)，原数据「走廊 / 电梯 / 楼梯」。按 Blender 当前模型：走廊、电梯位（北端，Duo Classic 穿楼板，上方天窗）、楼梯平台（南端）作一个空间，FFL 3.208，天花 2500。楼梯洞口一侧为栏杆，不出立面；下行台阶到后书房（低平台 2.856）的墙面和开关 S12（楼梯顶）另见楼梯图。主卧门旁 100 墙垛、中间书房门墙 160 小错台、书房南墙端 70 小凸出只在平面表示。",
)


# Rev B (owner 2026-10-09): skylight part (corridor, north of the old partition nibs x 2.46–2.59) ceiling 2500, landing beyond it 2700;
# smoke alarm SD1 on the landing ceiling (blue mark); L15 moved south clear of the lift door; L02 a little south; L01 on the stair-turn
# landing (centre of the down-steps strip, on its old E-W line).
CR = ROOMS["FF_二楼走廊"]
CR["rev"] = dict(rev="B")
CR["ceil"] = 2700
CR["face_ceil"] = {k: 2500 for k in "BCDEFG"}
CR["ceil_split"] = (2.52, "天花 2500（走廊 / 天窗段）", (1.10, 4.62), "天花 2700（楼梯平台）", (2.75, 4.60))
CR["ceil_labels"] = ((3.05, 5.75), (2.72, 5.62))
CR["ceil_move"] = {"L15": (-0.404, 4.915), "L02": (2.000, 4.945), "L01": (3.760, 7.410)}
CR["ceil_items"] = [dict(id="SD1", name="烟雾报警器 Smoke alarm（楼梯平台天花；联网 / 电源按 BS 5839-6 由电工定）", p=(3.08, 5.06), cat="light", sym="smoke")]
CR["notes5"] = CR["notes5"].replace("天花 2500", "天花：走廊（天窗段）2500，过隔断后楼梯平台 2700") + " Rev B：天窗在电梯旁走廊天花（见天花图蓝框）；加烟雾报警器 SD1（楼梯平台）；L15 往南挪开电梯门口，L02 略往南，L01 挪到楼梯转角平台。"

# Rev C (owner 2026-10-09): skylight smaller (west part only, ~650 wide); L15 a further 300 south; RCP dims short + larger;
# C02 from I onto A, 600 from the I-wall corner; middle-study door = 762 in the old frame (note box, figure TBC);
# H runs on to the back-study door (y 7.966); S11 200 from H's G-side end; S8 200 from F's left corner; S12 350 from the back-study door.
CR["rev"] = dict(rev="C")
CR["ceil_zones"] = [("天窗（约 580×650，尺寸现场复核）", (-1.555, 4.684, -0.975, 5.334)) if z[0].startswith("天窗") else z for z in CR["ceil_zones"]]
CR["ceil_move"]["L15"] = (-0.104, 4.915)
CR["ceil_fs"] = 2.6; CR["ceil_short"] = True
CR["ceil_vdx"] = {"L15": 0, "L02": -7, "SD1": 7}
CR["ceil_split"] = (2.52, "天花 2500（走廊 / 天窗段）", (1.05, 5.50), "天花 2700（楼梯平台）", (2.80, 5.62))
CR["ceil_labels"] = ((4.20, 5.62), (2.72, 5.62))
CR["faces"] = [f if f[0] != "H" else ("H", "南墙", "楼梯口墙（延伸到后书房门口）Stair-head wall to back-study door", (2.580, 7.966), (2.580, 5.494), ("后书房门口（下行台阶尽头）", "墙端")) for f in CR["faces"]]
CR["face_ceil"]["H"] = 2700
CR["override"].update({
    "C02": ("A", 1.698 - 0.600, "从楼梯平台外墙 I 挪到 A 墙，中心离 I 墙墙角 600（业主 2026-10-09），h450"),
    "S11": ("H", 0.200, "楼梯口：中心离 H 墙端（靠 G 墙一侧）200（业主 2026-10-09），h1200"),
    "S8":  ("F", 2.213 - 0.200, "走廊北端：中心离 F 墙左端墙角 200（业主 2026-10-09），h1200"),
    "S12": ("H", 2.472 - 0.350, "后书房门旁：中心离后书房门口 350（业主 2026-10-09）；此段地面为下行台阶，h1200 起算面现场按台阶 / 平台定"),
})
CR["room_note"].pop("S11", None); CR["room_note"].pop("C02", None)
_MS = "中间书房门 762（按老门框，洞 927 暂定）"
CR["openings"] = [("door", _MS, o[2], o[3], o[4], o[5]) if o[1].startswith("中间书房门") else o for o in CR["openings"]]
CR["features"] = CR.get("features", []) + [("F", "注：中间书房门按老门框装 762 门。|门洞 927 为暂定数字（按模型），|可能有误差，现场量老门框后确认。", 1000, 2180, 2060, 2440, "note")]
CR["notes5"] += " Rev C：天窗缩小（约 580×650，现场复核）；L15 再往南 300；C02 挪到 A 墙离 I 墙角 600；H 墙延伸到后书房门口，S11 离 H 墙端 200、S12 离后书房门 350；S8 离 F 墙左角 200；中间书房门按老门框装 762（洞宽暂定）。"

# Rev D (owner 2026-10-09): H was drawn mirrored — seen from the landing (looking north) the G-side end is on the LEFT and the
# back-study door on the RIGHT: S11 left (200 from the G-side end), S12 right (350 from the back-study door). H and I on separate sheets.
# Stair light F06 = key K, 3-way: GF S6 + FF S11 (one of its two keys) + FF S12.
CR["rev"] = dict(rev="D")
CR["faces"] = [f if f[0] != "H" else ("H", "北墙", "楼梯口墙（延伸到后书房门口）Stair-head wall to back-study door", (2.580, 5.494), (2.580, 7.966), ("墙端（靠 G 墙）", "后书房门口（下行台阶尽头）")) for f in CR["faces"]]
_K3 = "K 键 = 楼梯吊灯 F06 三路控制：一层 S6 + 二层 S11（其中一键）+ 二层 S12"
CR["override"]["S11"] = ("H", 2.472 - 0.200, "楼梯口，两联：D 键 = 走廊灯（与 S8 双控），" + _K3 + "；中心离 H 墙左端（靠 G 墙）200，h1200")
CR["override"]["S12"] = ("H", 0.350, "后书房门旁，单联 K 键（" + _K3 + "）；中心离后书房门口 350；此段地面为下行台阶，h1200 起算面现场按台阶 / 平台定")
CR["own_sheet"] = ("H", "I")
CR["notes5"] += " Rev D：H 墙按站在楼梯平台看（朝北）重画：左端靠 G 墙、右端后书房门；S11 在左（离端 200）、S12 在右（离后书房门 350）。楼梯吊灯 K 键三路控制：一层 S6 + 二层 S11 + S12。H、I 分两张图。"

# Rev E (owner 2026-10-09): extra switch S15 on H, ~500 from the G-side end (approximate: where the hand falls on reaching the top of
# the stairs); if needed it may go directly under S11 instead.
CR["rev"] = dict(rev="E")
CR["extra_pts"] = CR.get("extra_pts", []) + [("H", "S15", "开关（新增；控制内容待业主定）", 500, 1200,
                  "大概位置：中心离 H 墙左端（靠 G 墙）约 500，上完楼梯顺手处；如有必要可改放在 S11 正下方", "待定")]
CR["features"] = CR.get("features", []) + [("H", "注：S15 为大概位置（离 G 墙一端约 500），|最好在上完楼梯后顺手的地方；|如有必要可改放在 S11 正下方。", 120, 1500, 1650, 2000, "note")]
CR["notes5"] += " Rev E：H 墙加开关 S15（离靠 G 墙一端约 500，h1200，大概位置；必要时放在 S11 正下方），控制内容待业主定。"

# Rev F (owner 2026-10-09): the new H-wall point is a TWIN SOCKET at h450 (not a switch) -> C27 (next free FF socket number)
CR["rev"] = dict(rev="F")
CR["extra_pts"] = [e for e in CR["extra_pts"] if e[1] != "S15"] + [("H", "C27", "双联插座 Twin socket（新增）", 500, 450,
                  "新增（业主 2026-10-09）：大概位置，中心离 H 墙左端（靠 G 墙）约 500，上完楼梯顺手处；如有必要可改放在 S11 正下方；h450", "待定", "socket", "double")]
CR["features"] = [f for f in CR["features"] if not f[1].startswith("注：S15")] + [("H", "注：C27 双联插座为大概位置（离 G 墙一端约 500，离地 450），|最好在上完楼梯后顺手的地方；|如有必要可改放在 S11 正下方。", 120, 1700, 1650, 2000, "note")]
CR["notes5"] = CR["notes5"].replace(" Rev E：H 墙加开关 S15（离靠 G 墙一端约 500，h1200，大概位置；必要时放在 S11 正下方），控制内容待业主定。", "") + " Rev F：H 墙新增双联插座 C27（离靠 G 墙一端约 500，h450，大概位置；必要时放在 S11 正下方）。"

# Rev G (owner 2026-10-09): ceiling split is at the lift-area / corridor step (x -0.68), NOT at the landing nibs: north part (skylight /
# lift area) 2500, the whole corridor + landing south of it 2700.  Skylight size not decided -> no figure on the drawing.
CR["rev"] = dict(rev="G")
CR["ceil_split"] = (-0.68, "天花 2500（天窗 / 电梯段）", (-0.86, 5.45), "天花 2700（走廊 + 楼梯平台）", (2.72, 4.56))
CR["face_ceil"] = {"C": 2500, "D": 2500, "E": 2500}
CR["features"] = CR.get("features", []) + [("B", "天花 2500 段（天窗 / 电梯段）", round((2.460 + 0.68) * 1000), 4344, 2500, 2700, "pre")]
CR["ceil_zones"] = [("天窗（尺寸待定）", z[1]) if z[0].startswith("天窗") else z for z in CR["ceil_zones"]]
CR["notes5"] = (CR["notes5"].replace("天窗缩小（约 580×650，现场复核）", "天窗缩小（尺寸待定）")
                .replace("天花：走廊（天窗段）2500，过隔断后楼梯平台 2700", "天花：北端天窗 / 电梯段 2500，其余走廊 + 楼梯平台 2700")
                + " Rev G：天花分界改在电梯段与走廊交界（窄口处）：北端天窗 / 电梯段 2500，往南走廊 + 楼梯平台 2700；天窗尺寸待定，图上只示意位置。")

# 后书房 Rev B (owner 2026-10-09): ceiling ~2600 (not 2856); L06 nearer the middle of the room (L-shape centroid line); S13 150 and
# C17 250 from the door opening edge; C14 (A/C) 150 from the north corner.
RS = ROOMS["FF_后书房"]
RS["rev"] = dict(rev="B")
RS["ceil"] = 2600
RS["ceil_move"] = {"L06": (2.400, 9.690)}
RS["override"].update({
    "S13": ("A", 3.005 - (1.750 + 0.150), "中心离房门洞边 150（业主 2026-10-09），h1200"),
    "C17": ("A", 3.005 - (1.750 + 0.250), "中心离房门洞边 250（业主 2026-10-09），h450"),
    "C14": ("A", 0.150, "空调插座：中心离北墙角 150（业主 2026-10-09）；天花降到约 2600 后原 h2540 会碰顶角线，暂改 h2300 —— 按内机位置现场定；内机位置 / 是否保留待业主定", 2300),
})
RS["room_note"].pop("C14", None)
RS["notes5"] = RS["notes5"].replace("2856", "约 2600") + " Rev B：天花约 2600（业主 2026-10-09：后部下两步台阶，台阶高度不计，按约 2600）；L06 挪到房间中间；S13 离门洞边 150、C17 离门洞边 250；C14 离北墙角 150。"

# 后书房 Rev C / 中间书房 Rev D (owner 2026-10-09): 后书房 door = 762 in the old opening (note as the others) + UFH thermostat beside S13;
# 中间书房 ceiling 2700 (same as the corridor).
RS["rev"] = dict(rev="C")
RS["openings"] = [("door", "房门 762（按老门洞，洞 833 暂定）", o[2], o[3], o[4], o[5]) if o[1].startswith("房门") else o for o in RS["openings"]]
RS["features"] = RS.get("features", []) + [("A", "注：房门按老门洞装 762 门。|门洞 833 为暂定数字（按模型），|可能有误差，现场量老门洞后确认。", 700, 1900, 2120, 2480, "note")]
RS["extra_pts"] = RS.get("extra_pts", []) + [("A", "TH", "地暖温控面板 UFH thermostat", 2050, 1200, "S13 右侧同高，中心距 150（业主 2026-10-09）；有线温控需穿线到地暖分水器接线中心，无线温控也按此位置留底盒；型号由地暖供应商定", "待定")]
RB = ROOMS["FF_后房窄卫浴"]
RB["rev"] = dict(rev="B"); RB["ceil"] = 2600
RB["features"] = [f[:5] + (2600,) + f[6:] if f[5] == 2856 else f for f in RB.get("features", [])]
RB["notes5"] = RB.get("notes5", "").replace("2856", "约 2600") + " Rev B：与后书房同为下两步台阶后的后部，天花约 2600（业主 2026-10-09；台阶高度不计）。"
RS["notes5"] += " Rev C：房门按老门洞装 762（洞 833 暂定）；S13 右侧加地暖温控面板 TH（h1200，中心距 150）。"
MS["rev"] = dict(rev="D")
MS["ceil"] = 2700
MS["openings"] = [("window", "后窗 成品 1000×1600（窗台约 880，待现场复核）", o[2], o[3], 880, 2480) if o[0] == "window" else o for o in MS["openings"]]
MS["notes5"] = MS["notes5"].replace("天花 2500", "天花 2700") + " Rev D：天花 2700（与二楼走廊同高，业主 2026-10-09）；后窗窗台超过 800（业主），暂按 880（同主卧 W5），洞顶 2480，现场复核。"

# 后书房 Rev D / 后房窄卫浴 Rev C (owner 2026-10-09): geometry from the OWNER'S PLAN (rooms 218 / 219), not model v44:
# door wall A and south wall (x 4.290) kept; room 3050 (2040 + 1010) x 3590 (alcove 1050 + 2540); bath 910 x 2440 behind a 100
# partition; window wall: pier 300 | window 370 | pier 290 | window 940 | 1690.  Bath fittings / water points shift 125 with the rear wall.
RS["rev"] = dict(rev="D"); RB["rev"] = dict(rev="C")
RS["poly"] = [(1.240, 8.104), (4.290, 8.104), (4.290, 9.154), (3.280, 9.154), (3.280, 11.694), (1.240, 11.694)]
_rf = {f[0]: f for f in RS["faces"]}
_rc = {"A": ((4.290, 8.104), (1.240, 8.104)), "B": ((1.240, 8.104), (1.240, 11.694)), "C": ((1.240, 11.694), (3.280, 11.694)),
       "D": ((3.280, 11.694), (3.280, 9.154)), "E": ((3.280, 9.154), (4.290, 9.154)), "F": ((4.290, 9.154), (4.290, 8.104))}
RS["faces"] = [(k_,) + _rf[k_][1:3] + _rc[k_] + (_rf[k_][5],) for k_ in "ABCDEF"]
RS["openings"] = [o for o in RS["openings"] if o[1].startswith("房门")] + [
    ("window", "窄高窗 370（窗台 1560，窗下补墙）", (1.240, 8.404), (1.240, 8.774), 1560, 2100),
    ("window", "窗 940（窗台约 800）", (1.240, 9.064), (1.240, 10.004), 800, 2100),
    ("door", "卫浴门（洞 690，开向书房）", (3.280, 9.954), (3.280, 9.264), 0, 2040)]
RS["swings"] = [RS["swings"][0], ((3.280, 9.954), (3.280, 9.264), (2.590, 9.954))]
RS["furniture"] = [(n_, [b_[0], b_[1] + .125, b_[2], b_[3], b_[4] + .125, b_[5]]) if n_.startswith("床") else (n_, b_) for n_, b_ in RS["furniture"]]
RS["override"]["S13"] = ("A", 3.050 - 1.900, RS["override"]["S13"][2])
RS["override"]["C17"] = ("A", 3.050 - 2.000, RS["override"]["C17"][2])
_c = Polygon(RS["poly"]).centroid
RS["ceil_move"] = {"L06": (round(_c.x, 3), round(_c.y, 3))}
RS["extra_pts"] = [e if e[1] != "FS" else (e[0], e[1], e[2], round((11.694 - 9.609) * 1000), e[4]) + tuple(e[5:]) for e in RS["extra_pts"]]
RB["poly"] = [(3.380, 9.254), (4.290, 9.254), (4.290, 11.694), (3.380, 11.694)]
_bc = {"A": ((4.290, 9.254), (3.380, 9.254)), "B": ((3.380, 9.254), (3.380, 11.694)), "C": ((3.380, 11.694), (4.290, 11.694)), "D": ((4.290, 11.694), (4.290, 9.254))}
RB["faces"] = [(f[0], f[1], f[2]) + _bc[f[0]] + (f[5],) for f in RB["faces"]]
RB["openings"] = [("door", "门（洞 690，开向书房）", (3.380, 9.264), (3.380, 9.954), 0, 2040)]
RB["furniture"] = [(n_, [b_[0], b_[1] + .125, b_[2], b_[3], b_[4] + .125, b_[5]]) for n_, b_ in RB["furniture"]]
RB["water"] = [w_[:3] + ((w_[3][0], w_[3][1] + .125),) for w_ in RB["water"]]
_bas = next(b_ for n_, b_ in RB["furniture"] if n_.startswith("台盆"))
RB["ceil_move"] = {"L08": (round((3.380 + 4.290) / 2, 3), round((_bas[1] + _bas[4]) / 2, 3))}
RB["ceil_labels"] = ((3.45, 9.38), (4.20, 9.38))
WALL_REBUILD["FF"] = [((1.10, 8.104, 4.45, 11.85), ["FF_后书房", "FF_后房窄卫浴"], 0.10)]
RS["notes5"] += " Rev D：墙体尺寸改按业主平面图（房间 218）：净宽 3050（2040 + 凹位 1010）、进深 3590（凹位 1050 + 2540）；窗墙：墙垛 300｜窄高窗 370｜290｜窗 940｜1690；与模型 v44 不同处以本图为准，现场复核。L06 在房间中间。"
RB["notes5"] = RB["notes5"].replace("净 910×2499", "净 910×2440（Rev C 按业主平面图）") + " Rev C：按业主平面图（房间 219）净 910×2440；洁具随后墙整体后移 125；L08 在台盆正上方、房间宽度正中。"

# 后书房 Rev E (owner 2026-10-09): multi-purpose room (bed or desk) -> C15 centred under the big window; C16 on D at the middle of the bed.
RS["rev"] = dict(rev="E")
_bed = next(b_ for n_, b_ in RS["furniture"] if n_.startswith("床"))
RS["override"]["C15"] = ("B", 3.590 - (9.534 - 8.104), "大窗正中下方（业主 2026-10-09：多功能房，不放床时窗下可放书桌），h450")
RS["override"]["C16"] = ("D", 2.540 - (11.694 - (_bed[1] + _bed[4]) / 2), "D 墙上床（占位）中段（业主 2026-10-09），h450；被床挡住时作床边插座", )
for _k in ("C15", "C16"): RS["room_note"].pop(_k, None)
RS["override"]["S14"] = ("E", 1.010 - 0.150, "卫浴灯开关：凹位端墙，中心离卫浴隔墙墙角 150（Rev E 按业主平面墙位后重新定位；原模型点位落到墙外），h1200")
RS["furniture"] = RS["furniture"] + [("空调内机（示意 800×300，型号待定）", [1.490, 8.104, 2.852 + 2.080, 2.290, 8.304, 2.852 + 2.380])]
RS["notes5"] += " Rev E：多功能房（放床或书桌）：C15 在大窗正中下方；C16 在 D 墙床中段。A 墙 C14 旁画空调内机示意（800×300，离地 2080–2380，型号 / 位置待定）。"

# 后书房 Rev F (owner 2026-10-09): A/C unit drawn like 中间书房's (816 x 279, size TBC); bath door hinge moved to the alcove end (still
# opens into the study) so the latch side is on the left (seen on D); S14 on D 100 left of the door, FS above it at h1800.
RS["rev"] = dict(rev="F")
RS["furniture"] = [f for f in RS["furniture"] if not f[0].startswith("空调内机")] + [("空调内机（同中间书房，尺寸暂定）", [1.984, 8.104, 2.852 + 2.058, 2.800, 8.293, 2.852 + 2.337])]
RS["furniture"] = [("空调内机（同中间书房，尺寸暂定）", [2.290 - 0.816, 8.104, 2.852 + 2.058, 2.290, 8.293, 2.852 + 2.337]) if f[0].startswith("空调内机") else f for f in RS["furniture"]]
RS["swings"] = [RS["swings"][0], ((3.280, 9.264), (3.280, 9.954), (2.590, 9.264))]
_ds = round((11.694 - 9.954) * 1000)                                   # door's left edge on D (mm from D's left end)
RS["override"]["S14"] = ("D", 2.540 - (_ds - 100) / 1000, "卫浴灯开关：D 墙卫浴门左边，中心离门洞边 100（业主 2026-10-09），h1200；门合页已换到右侧（凹位一端）")
RS["extra_pts"] = [e if e[1] != "FS" else (e[0], e[1], e[2], _ds - 100, 1800, "排风扇开关：与 S14 同一竖线，h1800（业主 2026-10-09）；排风扇本体按产品定") + tuple(e[6:]) for e in RS["extra_pts"]]
RS["ceil_move"] = {"L06": (round(_c.x - 0.150, 3), round(_c.y, 3))}   # owner: a little further north
RS["notes5"] = RS["notes5"].replace("A 墙 C14 旁画空调内机示意（800×300，离地 2080–2380，型号 / 位置待定）。", "") + " Rev F：C14 旁空调内机按中间书房同款示意（816×279，尺寸暂定）；卫浴门合页换到凹位一端（仍开向书房）；S14 在 D 墙门左边 100、h1200，FS 同位置 h1800。"

# ---------------- 主客厅 (CGI site G01 / P01; old data: 起居室) + 门厅 / 鞋帽间 / 楼梯 (G07a 玄关鞋帽间, G07b 入口走廊) — LIVE Blender model.
# Owner 2026-10-09: these are one space -> laid out as a suite (one plan, one ceiling, letters continue). Bay: 3 faces from ray casts.
ROOMS["GF_主客厅"] = dict(
    F="GF", cn="主客厅", en="Main living room", sheet0=3, fz=0.0, ceil=2600, skirt=144, cove=90, rev=dict(rev="A"),
    poly=[(-0.600, 0.069), (-0.085, 0.069), (-0.085, -0.046), (0.059, -0.046), (0.592, -0.441), (1.621, -0.441), (2.148, -0.046), (2.344, -0.046),
          (2.344, 0.069), (3.089, 0.069), (3.089, 4.234), (-0.655, 4.234), (-0.655, 0.844), (-0.600, 0.844)],
    faces=[  # A1..A9 = front wall + bay, left -> right as seen from inside; shown as ONE unfolded wall A (owner 2026-10-09)
        ("A1", "西墙", "前墙南段", (3.089, 0.069), (2.344, 0.069), ("墙角", "转角")),
        ("A2", "西墙", "凸窗口南侧回墙", (2.344, 0.069), (2.344, -0.046), ("转角", "转角")),
        ("A3", "西墙", "凸窗口南侧墙垛", (2.344, -0.046), (2.148, -0.046), ("转角", "转角")),
        ("A4", "西墙", "凸窗南斜面", (2.148, -0.046), (1.621, -0.441), ("转角", "转角")),
        ("A5", "西墙", "凸窗正面", (1.621, -0.441), (0.592, -0.441), ("转角", "转角")),
        ("A6", "西墙", "凸窗北斜面", (0.592, -0.441), (0.059, -0.046), ("转角", "转角")),
        ("A7", "西墙", "凸窗口北侧墙垛", (0.059, -0.046), (-0.085, -0.046), ("转角", "转角")),
        ("A8", "西墙", "凸窗口北侧回墙", (-0.085, -0.046), (-0.085, 0.069), ("转角", "转角")),
        ("A9", "西墙", "前墙北段", (-0.085, 0.069), (-0.600, 0.069), ("转角", "墙角")),
        ("B", "南墙", "电视墙 / 门厅门 TV wall", (3.089, 4.234), (3.089, 0.069), ("墙角", "墙角")),
        ("C", "东墙", "通餐厅拱门墙 Arch to dining", (-0.655, 4.234), (3.089, 4.234), ("墙角", "墙角")),
        ("D", "北墙", "沙发墙（装饰线板）Sofa wall", (-0.655, 0.844), (-0.655, 4.234), ("墙角（凸出 55）", "墙角")),
        ("E", "北墙", "北墙前段 North wall, front part", (-0.600, 0.069), (-0.600, 0.844), ("墙角", "墙角（凹进 55）")),
    ],
    unfold={"A": ("西墙", "前墙 + 凸窗（展开）Front wall & bay, unfolded", ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9"])},
    openings=[("window", "凸窗北扇（窗台约 660）", (0.508, -0.379), (0.112, -0.085), 660, 2260),
              ("window", "凸窗正扇（窗台约 660）", (1.592, -0.441), (0.665, -0.441), 660, 2260),
              ("window", "凸窗南扇（窗台约 660）", (2.133, -0.057), (1.734, -0.356), 660, 2260),
              ("door", "门（通门厅，框内 1000）", (3.089, 1.429), (3.089, 0.399), 0, 2030),
              ("door", "拱门 / 侧滑门洞（通餐厅）", (-0.372, 4.234), (2.178, 4.234), 0, 2040)],
    swings=[],
    furniture=[("沙发 G09", [-0.602, 1.238, 0.002, 0.906, 4.238, 0.898]), ("边柜 G12", [-0.6, 2.726, 0.002, -0.45, 4.226, 0.682]),
               ("柜 G02", [-0.555, 0.184, 0.002, -0.155, 0.984, 0.907]), ("凸窗茶台柜 G03", [0.342, 0.016, 0.002, 1.731, 0.934, 0.875]),
               ("电视柜 G21", [2.651, 1.764, 0.002, 3.001, 3.964, 0.452]), ("装饰线板 F34（墙面）", [-0.655, 1.124, 1.028, -0.621, 4.124, 2.378])],
    override={},
    room_note={"S1": "数据写「门厅 · 前门内侧」；按模型在主客厅前墙南段（凸窗南侧）",
               "C07": "数据里房间写「储物间」；按位置在主客厅前墙南段",
               "C17": "柜 G02 柜面（约 907）上方约 200",
               "S3": "拱门南侧，离拱门洞边约 180",
               "C04": "电视柜 G21 上方", "C31": "电视柜 G21 上方；电视后面", "C32": "电视柜 G21 上方；电视后面"},
    notes5="5. 主客厅 = 原数据的「起居室」（CGI 网站 G01 / 全景 P01）。按 Blender 当前模型：前部三面凸窗（窗台约 660、洞顶约 2260），沙发墙 V12 带装饰线板 F34，后墙拱门通餐厅（拱门旁 S4 / S5 / 壁灯 L01 在餐厅一侧，见餐厅图）。天花 2600，平顶无梁。前墙 + 三面凸窗展开成一张立面 A（虚线 = 转角，业主 2026-10-09）。",
)

ROOMS["GF_门厅楼梯"] = dict(
    F="GF", cn="门厅 · 鞋帽间 · 楼梯", en="Entrance hall, boot room & stairs", sheet0=3, fz=0.0, ceil=2600, skirt=144, cove=90, rev=dict(rev="A"),
    poly=[(3.215, 0.371), (4.290, 0.371), (4.290, 7.414), (3.424, 7.414), (3.424, 5.069), (3.215, 5.069)],
    faces=[
        ("F", "西墙", "前门墙 Front door wall", (4.290, 0.371), (3.215, 0.371), ("墙角", "墙角")),
        ("G", "北墙", "门厅北墙（通主客厅门）Hall north wall", (3.215, 0.371), (3.215, 4.300), ("墙角", "墙端（通餐厅）")),
        ("H", "南墙", "门厅 / 楼梯南墙（外墙）Hall & stair south wall", (4.290, 7.414), (4.290, 0.371), ("楼梯转角", "墙角")),
    ],
    openings=[("door", "前门（门扇 + 上亮到天花，框约 1030）", (4.276, 0.371), (3.249, 0.371), 0, 2600),
              ("door", "门（通主客厅，框内 1000）", (3.215, 0.399), (3.215, 1.429), 0, 2030)],
    swings=[((3.310, 0.371), (4.230, 0.371), (3.310, 1.291))],      # front door: hinge north (handle at x 4.12), opens into the hall
    furniture=[("内门 F26（框内约 760）", [3.32, 1.775, 0.002, 4.082, 1.893, 1.983]),
               ("内门北侧墙垛", [3.215, 1.775, 0.0, 3.321, 1.893, 2.0]), ("内门南侧墙垛", [4.081, 1.775, 0.0, 4.29, 1.893, 2.0]),
               ("挂衣板 + 镜 F33", [4.234, 1.984, 0.4, 4.29, 2.764, 1.8]), ("鞋柜 G13", [3.241, 2.828, 0.002, 4.239, 3.432, 2.014]),
               ("楼梯（直跑 + 顶部转角踏步，见楼梯图）", [3.322, 5.069, 0.0, 4.29, 7.414, 2.445])],
    override={},
    room_note={"S2": "数据写「门厅 · 前储物间旁」；按位置在门厅北墙，内门 F26 前",
               "C01": "数据里房间写「储物间」；按位置在鞋帽间北墙",
               "C03": "数据里房间写「储物间」；按位置在楼梯口南墙",
               "S6": "楼梯底，第一级踏步前约 500"},
    notes5="5. 门厅 · 鞋帽间 · 楼梯（CGI 网站 G07a「玄关鞋帽间」+ G07b「入口走廊」；原数据「门厅 / 储物间 / 楼梯」）。按 Blender 当前模型：前门（门扇 + 上亮到天花）→ 内门 F26（两侧墙垛）→ 鞋帽间（南墙挂衣板 + 镜 F33）→ 鞋柜 G13（模型里几乎占满通道宽度，请核对）→ 楼梯口（西侧敞开到餐厅）→ 楼梯（第一级 y 5.069 起，上方通二层，楼梯另见楼梯图）。H 墙只画到直跑段顶。",
)


# ---------------- 餐厅 (CGI site G02 / P02) — part of the 主客厅区 suite (owner 2026-10-09: 主客厅 + 餐厅 + 楼梯 + 玄关鞋帽间 = one area).
ROOMS["GF_餐厅"] = dict(
    F="GF", cn="餐厅", en="Dining", sheet0=3, fz=0.0, ceil=2600, skirt=144, cove=90, rev=dict(rev="A"),
    ceil_extra="（有低梁 V26，梁底约 2320）",
    poly=[(-0.655, 4.234), (2.224, 4.234), (2.224, 4.354), (3.215, 4.354), (3.215, 5.069), (3.322, 5.069), (3.322, 7.864), (1.155, 7.864),
          (1.155, 7.899), (-0.609, 7.899), (-0.609, 4.354), (-0.655, 4.354)],
    faces=[
        ("I", "西墙", "拱门旁墙段（楼梯口）Wall by the arch", (3.215, 4.354), (2.224, 4.354), ("墙端（楼梯口）", "墙端（拱门）")),
        ("J", "南墙", "楼梯侧板（楼梯下检修门）Stair side", (3.322, 7.864), (3.322, 5.069), ("墙角", "楼梯起步")),
        ("K", "东墙", "后墙 · 通厨房门 Rear wall, kitchen door", (1.155, 7.864), (3.322, 7.864), ("墙端（凹进 35）", "墙角")),
        ("L", "东墙", "后墙 · 法式门 Rear wall, French doors", (-0.609, 7.899), (1.155, 7.899), ("墙角", "墙端（凸出 35）")),
        ("M", "北墙", "吸音墙 / 暗门 Acoustic wall & hidden door", (-0.609, 4.354), (-0.609, 7.899), ("墙端（拱门旁）", "墙角")),
    ],
    openings=[("door", "通厨房门 KP762（框约 790）", (2.530, 7.864), (3.322, 7.864), 0, 2030),
              ("door", "法式门（通后花园，框约 1210）", (-0.380, 7.899), (0.830, 7.899), 0, 2240),
              ("door", "暗门 V15 762（通副客厅，洞 828，按副客厅 Rev C）", (-0.609, 4.354), (-0.609, 5.122), 0, 2032),
              ("door", "楼梯下检修门（内有配电箱）", (3.322, 7.379), (3.322, 6.769), 0, 1800)],
    swings=[],
    furniture=[("餐桌", [1.275, 6.239, 0.002, 2.075, 7.839, 0.762]), ("低梁 V26（梁底 2320）", [2.224, 4.354, 2.32, 2.465, 7.864, 2.62])],
    override={"C08": ("K", 1.484, "点位数据原点离墙面 350，按墙面定位（距左端 683）；在餐桌端头旁")},
    room_note={"C02": "拱门旁墙段，离拱门端约 110",
               "C15": "吸音墙上（V15 吸音墙面层，底盒需随面层加长）",
               "S7": "法式门框南侧（数据写「东侧」）"},
    notes5="5. 餐厅（CGI 网站 G02 / 全景 P02）。按 Blender 当前模型：西侧拱门通主客厅，北侧为吸音墙 V15（暗门通副客厅，尺寸按副客厅 Rev C），南侧为楼梯侧板（楼梯下检修门，内有配电箱），后墙法式门通后花园、通厨房门 KP762。天花 2600，有低梁 V26（梁底约 2320，宽约 240，东西向）。楼梯口一侧敞开到门厅。",
)


# ---------------- 厨房区 = 早餐区 (CGI G04; data: 厨房（吧台区）) + 厨房 (G05) + 洗衣房 (G06 杂物间) — LIVE Blender model, one suite (owner 2026-10-09)
ROOMS["GF_早餐区"] = dict(
    F="GF", cn="早餐区", en="Breakfast / bar area", sheet0=4, fz=0.0, ceil=2600, skirt=144, cove=90, rev=dict(rev="A"),
    poly=[(1.270, 8.164), (4.290, 8.164), (4.290, 11.824), (1.270, 11.824)],
    faces=[
        ("A", "西墙", "通餐厅门墙 Wall to dining", (4.290, 8.164), (1.270, 8.164), ("墙角", "墙角")),
        ("B", "北墙", "法式门墙（通后花园）French-door wall", (1.270, 8.164), (1.270, 11.824), ("墙角", "敞开（接厨房）")),
        ("C", "东墙", "墙垛（早餐区侧）Pier", (3.771, 11.824), (4.290, 11.824), ("墙端", "墙角")),
        ("D", "南墙", "半岛台墙 Peninsula wall", (4.290, 11.824), (4.290, 8.164), ("墙角（墙垛）", "墙角")),
    ],
    openings=[("door", "门 KP762（通餐厅）", (3.343, 8.164), (2.523, 8.164), 0, 2030),
              ("door", "法式门（通后花园，框 1641）", (1.270, 8.673), (1.270, 10.314), 0, 2032)],
    swings=[],
    furniture=[("排水立管箱 S2 200×200", [4.09, 8.2, 0.0, 4.29, 8.4, 2.6]), ("柜 G24", [1.378, 8.304, 0.054, 1.703, 8.756, 0.592]),
               ("挂墙柜 G23", [1.29, 8.163, 1.247, 1.732, 8.503, 1.968]),
               ("半岛台（水槽，台面 902）", [2.438, 10.211, 0.0, 4.281, 11.035, 0.902]), ("台面 + 洗碗机 Bosch", [3.67, 11.035, 0.0, 4.281, 11.824, 0.902]),
               ("吊柜", [3.905, 10.687, 1.356, 4.301, 11.824, 2.202])],
    override={},
    room_note={"S13": "厨房入口，离门洞北侧边约 130", "C23": "半岛台台面（902）上方约 200", "C09": "台面（902）上方约 200；洗碗机上方",
               "C27": "排水立管箱 S2 旁"},
    notes5="5. 早餐区 = CGI 网站 G04「早餐区」，原数据「厨房（吧台区）」。按 Blender 当前模型：前墙门 KP762 通餐厅，北墙法式门通后花园，南墙半岛台（水槽 + 洗碗机，台面约 902）+ 吊柜，西南角排水立管箱 S2。半岛台侧面插座 C26（h800）不在墙面上，见平面。与厨房之间敞开，只有南侧墙垛（约 520）和顶部下挂梁（梁底约 2040）。",
)

ROOMS["GF_厨房"] = dict(
    F="GF", cn="厨房", en="Kitchen", sheet0=4, fz=0.0, ceil=2600, skirt=144, cove=90, rev=dict(rev="A"),
    ceil_extra="（与早餐区交界有下挂梁，梁底约 2040）",
    poly=[(1.270, 11.824), (3.771, 11.824), (3.771, 12.104), (4.290, 12.104), (4.290, 14.714), (1.270, 14.714)],
    faces=[
        ("E", "北墙", "窗墙 Window wall", (1.270, 11.824), (1.270, 14.714), ("敞开（接早餐区）", "墙角")),
        ("F", "东墙", "通洗衣房门墙 Wall to utility", (1.270, 14.714), (4.290, 14.714), ("墙角", "墙角")),
        ("G", "南墙", "灶台墙 Cooker wall", (4.290, 14.714), (4.290, 12.104), ("墙角", "墙角（墙垛）")),
        ("H", "西墙", "墙垛（厨房侧）Pier", (4.290, 12.104), (3.771, 12.104), ("墙角", "墙端")),
    ],
    openings=[("window", "大窗（窗台约 1120）", (1.270, 12.640), (1.270, 14.110), 1120, 2040),
              ("door", "门（通洗衣房，开向洗衣房）", (1.270, 14.714), (2.240, 14.714), 0, 2040)],
    swings=[],
    furniture=[("台面 + 地柜（灶台 AEG、烤箱）", [3.655, 12.098, 0.0, 4.281, 14.106, 0.902]), ("烟机 G01", [3.905, 12.678, 1.622, 4.273, 13.577, 2.409]),
               ("吊柜", [3.905, 12.116, 1.356, 4.301, 12.634, 2.202]), ("吊柜", [3.905, 13.621, 1.356, 4.301, 13.989, 2.202]),
               ("转角吊柜", [3.626, 13.942, 1.411, 4.284, 14.639, 2.202]), ("转角台面 + 地柜", [2.994, 14.091, 0.0, 4.264, 14.713, 0.902]),
               ("吊柜", [3.141, 14.331, 1.356, 3.659, 14.728, 2.202]), ("冰箱 850", [2.245, 13.956, 0.0, 3.095, 14.713, 1.802])],
    override={},
    room_note={"C25": "冰箱后面（冰箱插座）；数据里房间写「洗衣房」，按位置在厨房一侧",
               "C10": "台面（902）上方约 200；数据里房间写「洗衣房」，按位置在厨房一侧",
               "C24": "台面（902）上方约 200；数据里房间写「洗衣房」，按位置在厨房一侧",
               "C14": "大窗北端下方（窗台约 1120）"},
    notes5="5. 厨房（CGI 网站 G05）。按 Blender 当前模型：北墙大窗（窗台约 1120，洞顶约 2040），南墙灶台（AEG 灶具 + 烤箱 + 烟机 G01）及吊柜，东北角冰箱 850，东墙门通洗衣房（门扇开向洗衣房）。与早餐区之间有下挂梁（梁底约 2040）。天花 2600。主灯 L27 灯具待选。",
)

ROOMS["GF_洗衣房"] = dict(
    F="GF", cn="洗衣房", en="Utility", sheet0=4, fz=0.0, ceil=2600, skirt=144, cove=90, rev=dict(rev="A"),
    poly=[(1.270, 14.834), (4.290, 14.834), (4.290, 16.034), (1.270, 16.034)],
    faces=[
        ("I", "西墙", "通厨房门墙 Wall to kitchen", (4.290, 14.834), (1.270, 14.834), ("墙角", "墙角")),
        ("J", "北墙", "小窗墙 Small-window wall", (1.270, 14.834), (1.270, 16.034), ("墙角", "墙角")),
        ("K", "东墙", "后门墙 Back-door wall", (1.270, 16.034), (4.290, 16.034), ("墙角", "墙角")),
        ("L", "南墙", "洗衣机墙 Washer wall", (4.290, 16.034), (4.290, 14.834), ("墙角", "墙角")),
    ],
    openings=[("door", "门（通厨房）", (2.240, 14.834), (1.270, 14.834), 0, 2040),
              ("window", "小窗（窗台约 1120）", (1.270, 15.363), (1.270, 15.840), 1120, 2040),
              ("door", "后门 单扇 890（外开）", (1.270, 16.034), (2.160, 16.034), 0, 2012),
              ("window", "后小窗（窗台约 1427）", (3.262, 16.034), (3.902, 16.034), 1427, 2052)],
    swings=[((1.270, 14.834), (1.990, 14.834), (1.270, 15.554))],
    furniture=[("洗衣机 / 烘干机 G04（台面 1002）", [3.527, 14.81, 0.0, 4.257, 16.034, 1.002])],
    override={},
    room_note={"C12": "洗衣机 / 烘干机台面（1002）上方", "S14": "门洞南侧，离洞边约 170"},
    notes5="5. 洗衣房 = CGI 网站 G06「杂物间」。按 Blender 当前模型：后门单扇 890（外开），后墙另有小窗（窗台约 1427），北墙小窗，南墙洗衣机 / 烘干机 G04。天花 2600。",
)


# ---------------- 门廊 (outside the front door; owner 2026-10-09: part of 主客厅区, it has the porch lantern L07 / G25) — LIVE Blender model
ROOMS["GF_门廊"] = dict(
    F="GF", cn="门廊", en="Front porch", sheet0=3, fz=0.0, ceil=2600, skirt=0, cove=0, rev=dict(rev="A"),
    poly=[(3.315, -0.046), (4.260, -0.046), (4.260, 0.311), (3.315, 0.311)],
    faces=[
        ("N", "北侧", "门廊北侧墙 Porch north side", (3.315, -0.046), (3.315, 0.311), ("拱口（壁柱）", "墙角")),
        ("O", "东墙", "前门（门廊一侧）Front door, outside", (3.315, 0.311), (4.260, 0.311), ("墙角", "墙角")),
        ("P", "南侧", "门廊南侧砖垛 Porch south pier", (4.260, 0.311), (4.260, -0.046), ("墙角", "拱口（壁柱）")),
    ],
    openings=[("door", "前门（门扇 + 上亮，见 F 墙）", (3.315, 0.311), (4.260, 0.311), 0, 2600)],
    swings=[],
    furniture=[("门廊吊灯 G25（L07）", [3.676, -0.01, 1.827, 3.899, 0.213, 2.6]), ("拱门 Archway（拱底约 2030）", [3.315, -0.082, 2.03, 4.26, 0.05, 2.602]),
               ("拱门壁柱（北）", [3.185, -0.068, 0.0, 3.325, -0.046, 1.9]), ("拱门壁柱（南）", [4.25, -0.068, 0.0, 4.39, -0.046, 1.9])],
    override={},
    room_note={},
    notes5="5. 门廊（前门外，业主 2026-10-09 并入主客厅区）。按 Blender 当前模型：前门外凹口约 945 宽 × 357 深，外口为拱门（两侧壁柱，拱底约 2030，拱心石），南侧砖垛；前门约 920 门扇，合页在北侧、向门厅内开（平面画开门弧线；开足时会挡住通主客厅的门，请核对），顶（门廊顶板）约 2600；地面为花砖。户外吊灯 G25 = L07，线盒在门廊顶板正中偏前（尺寸见天花图）；灯具需 IP44 以上，开关见 S1 键 3（数据：门廊壁灯 G25）。",
)


# ---------------- 前院 = 副客厅前门外凹位 (EV charger, outdoor socket, car-wash tap) + 前花园 / 车道 (plan only) — LIVE Blender model (owner 2026-10-09)
ROOMS["GF_前门凹位"] = dict(
    F="GF", cn="前门凹位", en="Recess outside the side-lounge front door", sheet0=5, fz=-0.048, ceil=2668, skirt=0, cove=0, rev=dict(rev="A"),
    ceil_extra="（二层楼板底，室外）",
    poly=[(-4.290, 0.959), (-1.665, 0.959), (-1.665, 1.289), (-4.290, 1.289)],
    faces=[
        ("A", "北侧", "凹位北侧墙（洗车龙头）North side", (-4.290, 0.959), (-4.290, 1.289), ("墙端（外）", "墙角")),
        ("B", "东墙", "副客厅前门外墙（充电桩）Wall with side-lounge door & EV charger", (-4.290, 1.289), (-1.665, 1.289), ("墙角", "墙端")),
        ("C", "西侧", "凹位前侧墙垛内侧 Inner face of front pier", (-3.815, 0.959), (-4.290, 0.959), ("墙端（外）", "墙角")),
    ],
    openings=[("door", "副客厅前门 双扇（见副客厅图）", (-3.215, 1.289), (-1.812, 1.289), 0, 2099)],
    swings=[],
    furniture=[],
    override={},
    extra_pts=[("B", "EV", "EV 充电桩 Charger（D07）", 909, 1050, "电源 WP5 专线，室内隔离开关 D08 在副客厅墙内（离地 1.2 m，不在本图）；充电桩型号 / 安装支架按产品；中心离地约 1.0 m（数据）", "WP5")],
    water_pts=[("A", "FT", "洗车龙头 Car-wash tap", 116, 420, "给排水施工图 Rev C：热水器下软水机前三通引出，穿新砌外墙出户；模型中心约离地 420")],
    room_note={"C34": "⚠ 点位数据在北侧墙、洗车龙头 FT 正上方约 180（插座与龙头同一竖线）；v44 点位审阅模型放在 C 墙（墙垛内侧，离墙端约 60）—— 待业主定"},
    notes5="5. 前门凹位（副客厅前门外，二层楼板下）。按 Blender 当前模型：凹位约 2625 × 330，地面约 -0.048（本图高度从此地面起算），顶为二层楼板底（约 2668）。B 墙：副客厅前门 + EV 充电桩（D07，专线 WP5）；A 墙：洗车龙头 FT；户外插座 C34 位置待定（见点位表）。户外插座 / 充电桩均为 IP 防护等级产品。",
)

ROOMS["GF_前花园"] = dict(
    F="GF", cn="前花园 · 车道", en="Front garden & driveway", sheet0=5, fz=0.0, ceil=0, skirt=0, cove=0, rev=dict(rev="A"),
    ceil_extra="（室外，无天花）",
    poly=[(-4.620, -4.160), (4.530, -4.160), (4.530, -0.046), (2.250, -0.046), (1.660, -0.560), (0.550, -0.560), (-0.040, -0.046), (-0.830, -0.046),
          (-0.830, 0.727), (-1.665, 0.727), (-1.665, 0.959), (-3.815, 0.959), (-3.815, 0.726), (-4.406, 0.726), (-4.406, 0.840), (-4.620, 0.840)],
    faces=[],
    openings=[], swings=[],
    furniture=[("前矮墙（北段）", [-0.6, -4.16, -0.5, 0.03, -3.96, 0.15]), ("前矮墙（南段）", [1.47, -4.16, -0.5, 4.16, -3.96, 0.15]),
               ("台阶墩（北）", [0.01, -4.22, -0.5, 0.33, -3.9, 0.3]), ("台阶墩（南）", [1.17, -4.22, -0.5, 1.49, -3.9, 0.3]),
               ("入口台阶", [0.33, -4.2, -0.5, 1.17, -3.73, -0.15]), ("回墙（车道 / 花园分隔）", [-0.83, -3.9, -0.5, -0.63, -1.4, 0.15]),
               ("回墙端墩", [-0.89, -1.4, -0.5, -0.57, -1.08, 0.3]), ("花坛（北）", [-0.63, -3.96, -0.2, 0.01, -3.4, -0.1]),
               ("花坛（南）", [1.49, -3.96, -0.2, 2.99, -3.4, -0.1]), ("北侧铁栏杆", [-4.63, -1.98, 0.05, -4.61, 0.52, 0.68]),
               ("北侧围墙墩（临街）", [-4.78, -4.22, -0.5, -4.46, -3.9, 0.05]), ("北侧围墙墩（中）", [-4.78, -2.3, -0.5, -4.46, -1.98, 0.55]),
               ("南侧铁栏杆", [4.37, -3.9, 0.1, 4.39, -0.09, 1.02])],
    override={}, room_note={},
    notes5="5. 前花园 · 车道（按 Blender 当前模型，只出平面）：北半为车道（斜坡，约 -0.05 → -0.55 到街面），南半为前花园（地面约 -0.15，两处花坛），临街前矮墙 + 入口台阶 + 两侧铁栏杆。点位数据里前花园本身没有灯 / 插座；门廊灯 L07 见主客厅区（W1-03），凹位的充电桩 / 户外插座 / 洗车龙头见本套 A–C 墙。房屋前沿轮廓（凸窗外侧）为示意。",
)


# ---------------- 后院 (rear patio; lawn and garden room further back have no points) — LIVE Blender model (owner 2026-10-09)
ROOMS["GF_后院"] = dict(
    F="GF", cn="后院", en="Rear garden / patio", sheet0=6, fz=-0.020, ceil=3600, skirt=0, cove=0, rev=dict(rev="A"),
    no_ceiling=True, top_label="立面画到", plan_k=16.666,
    poly=[(-4.520, 8.129), (1.040, 8.129), (1.040, 16.264), (4.530, 16.264), (4.530, 17.160), (-4.520, 17.160)],
    faces=[
        ("A", "西墙（外）", "房屋后墙外侧 House rear wall, outside", (1.040, 8.129), (-4.520, 8.129), ("墙角", "墙角（围栏）")),
        ("B", "南墙（外）", "厨房 / 早餐区外墙 Kitchen extension wall, outside", (1.040, 16.264), (1.040, 8.129), ("墙角", "墙角")),
        ("C", "西墙（外）", "洗衣房后墙外侧 Utility rear wall, outside", (4.530, 16.264), (1.040, 16.264), ("墙角（围墙）", "墙角")),
        ("D", "北侧", "北侧围栏（白卵石 + LED 灯带）North fence", (-4.520, 8.129), (-4.520, 17.160), ("墙角", "接草坪")),
    ],
    openings=[("door", "副客厅花园门（法式门 + 两侧侧窗，总宽约 2100，见副客厅图）", (-1.880, 8.129), (-3.980, 8.129), 0, 2052),
              ("window", "楼下洗手间小窗", (-0.975, 8.129), (-1.575, 8.129), 1452, 2012),
              ("door", "餐厅法式门", (0.830, 8.129), (-0.380, 8.129), 0, 2240),
              ("door", "早餐区法式门", (1.040, 10.314), (1.040, 8.673), 0, 2032),
              ("window", "厨房大窗（外凸）", (1.040, 14.110), (1.040, 12.640), 1120, 2040),
              ("window", "洗衣房小窗", (1.040, 15.840), (1.040, 15.363), 1120, 2040),
              ("door", "洗衣房后门 890（外开）", (2.160, 16.264), (1.270, 16.264), 0, 2012),
              ("window", "洗衣房后小窗", (3.902, 16.264), (3.262, 16.264), 1427, 2052)],
    swings=[],
    furniture=[("S1 污水立管（上到屋面）", [-0.91, 8.129, -0.35, -0.8, 8.36, 3.6]), ("户外转角沙发", [-4.28, 10.39, -0.02, -1.74, 13.6, 0.93]),
               ("水景模块", [-4.52, 14.42, 0.0, -2.66, 17.16, 1.67]), ("检查井 MH（现有）", [-2.07, 9.38, -0.02, -1.47, 9.82, 0.01]),
               ("白卵石 + LED 灯带", [-4.52, 8.18, -0.03, -3.83, 14.3, 0.03]), ("后加建斜屋面（檐口约 2850）", [1.04, 11.81, 2.85, 1.12, 16.21, 3.44])],
    override={"L08": ("C", 1.770, "户外壁灯 G26_1，IP44 以上；数据原点离墙面 440，按墙面定位（距左端 1720）"),
              "C20": ("A", 0.271, "IP66；按模型在后墙北端（距右端墙角 271），盆栽棕榈后面 —— 现场核对")},
    extra_pts=[("D", "L40", "围栏地灯 Fence light（LED）", 1058, 0, "白卵石带内 LED 灯带接线点（数据 x -4.30）；防水接线盒 IP68，驱动 / 开关位置待定", "待定"),
               ("D", "L41", "围栏地灯 Fence light（LED）", 3068, 0, "同上", "待定"),
               ("D", "L42", "围栏地灯 Fence light（LED）", 4918, 0, "同上", "待定"),
               ("D", "L43", "围栏地灯 Fence light（LED）", 5968, 0, "同上；灯带止于 y 约 14.3（水景前）", "待定")],
    room_note={"L44": "⚠ 二层外墙泛光灯 G26_4（离地 3350）：点位数据在 x -0.805（S1 立管旁），模型 v44 里灯在约 x -1.35 —— 待业主定",
               "C21": "IP66；v44 点位审阅模型另有建议位（离南端约 700，靠近 L09）",
               "C20": "IP66；后墙北端，盆栽棕榈后面 —— 现场核对",
               "L09": "户外壁灯 G26_2，IP44 以上", "L10": "户外壁灯 G26_3，IP44 以上", "L08": "户外壁灯 G26_1，IP44 以上"},
    notes5="5. 后院（按 Blender 当前模型，只画后露台；草坪及花园小屋没有点位，不出图）。露台地面约 -0.02，本图高度从露台地面起算；立面画到 3600（不是天花）。A 墙为房屋后墙外侧（副客厅花园门、洗手间小窗、餐厅法式门、S1 污水立管），B 墙为厨房 / 早餐区加建外墙（法式门、厨房大窗、洗衣房小窗），C 墙为洗衣房后墙外侧（后门、后小窗），D 为北侧围栏（白卵石带内 LED 灯带）。户外插座 IP66，户外灯 IP44 以上，回路见照明 / 插座施工图。",
)


def revised_walls(R):
    if R is not BR and R is not BA:                   # other rooms: walls from the model section
        if R["F"] not in _PLN: _PLN[R["F"]] = so.Plan(R["F"])
        w = _PLN[R["F"]].walls
        for op, b in WALL_EDITS.get(R["F"], []):                         # owner-revised walls on top of the model section
            w = w.difference(box(*b)) if op == "sub" else w.union(box(*b))
        for clear, keys, t in WALL_REBUILD.get(R["F"], []):              # area redrawn from the owner's plan: clear the model walls,
            from shapely.ops import unary_union                           # rebuild them around the owner-dimensioned room polygons
            polys = [Polygon(ROOMS[k_]["poly"]) for k_ in keys]
            nw = unary_union([p_.buffer(t, join_style=2) for p_ in polys]).difference(unary_union(polys))
            for k_ in keys:
                for kind, nm, a, b, sill, head in ROOMS[k_]["openings"]:
                    if kind == "door": nw = nw.difference(LineString([a, b]).buffer(t + .03, cap_style=2))
            w = w.difference(box(*clear)).union(nw)
        return w
    from shapely.ops import unary_union
    polys = [Polygon(r["poly"]) for r in (BR,BA)]
    walls = unary_union([p.buffer(.100,join_style=2) for p in polys]).difference(unary_union(polys))
    for room in (BR,BA):
        for kind,name,a,b,sill,head in room["openings"]:
            if kind == "door": walls = walls.difference(LineString([a,b]).buffer(.13,cap_style=2))
    return walls

CIRC = {}          # socket id -> scheme-B circuit
LIGHT_KEYS = {}    # light id (L..) -> "S3 键 2 / S4 键 10"


def load_meta(F):
    import json
    P = json.load(open(os.path.join(so.TOOL, f"power_{F}.json"), encoding="utf-8"))
    for i, s in enumerate(P["sockets"], 1): CIRC[f"C{i:02d}"] = s["c"].get("B", s["c"].get("A"))
    J = so.load_tool(F)
    key2plate = {k: p["id"] for p in J["plates"] for k in p["keys"]}
    for i, l in enumerate(J["lights"], 1):
        for c in J["circuits"]:
            if l["id"] in c["lights"]:
                LIGHT_KEYS[f"L{i:02d}"] = (" / ".join(f"{key2plate.get(k, '?')} 键 {k}" for k in c["keys"]), c.get("wl", ""), cgi(c["name"]))
    SW_LIGHTS.clear()
    for c in J["circuits"]:
        for k in c["keys"]:
            SW_LIGHTS.setdefault(key2plate.get(k, "?"), []).append(f"键 {k} → {c['name']}")       # cgi() is applied once, in pt_note()
    for v in SW_LIGHTS.values():                       # 后院 Rev B (owner 2026-10-09): fence ground lights x4 -> one outdoor LED strip (tail L40)
        v[:] = [t.replace("围栏地灯 ×4", "围栏户外灯带（L40 出线；原地灯 ×4 取消）") for t in v]


SW_LIGHTS = {}
BG_MODE = False          # True: sheets for the FreeCAD underlay (fc_bridge.py)
_OLD2CGI = [("北卫生间", "次卧卫浴"), ("北卫", "次卧卫浴"), ("西卫生间", "主卫"), ("西卫", "主卫"), ("主卧", "§"), ("卧室2", "主卧"), ("卧室 2", "主卧"), ("§", "次卧"),
            # ground floor (CGI site): old 客厅 -> 副客厅, old 起居室 -> 主客厅; protect names that already contain 客厅
            ("主客厅", "‹1›"), ("副客厅", "‹2›"), ("客厅", "副客厅"), ("起居室", "主客厅"), ("‹1›", "主客厅"), ("‹2›", "副客厅"),
            ("卧室 3", "中间书房"), ("卧室3", "中间书房"), ("卧室 4", "后书房"), ("卧室4", "后书房")]


def cgi(s):
    """old data room names -> CGI-site names (owner 2026-10-08: 次卧 = front-left room with en-suite, 主卧 = old 卧室 2)"""
    for a, b in _OLD2CGI: s = s.replace(a, b)
    return s
PLATE = {"double": (0.146, 0.086), "single": (0.086, 0.086), "switch": (0.086, 0.086), "new": (0.086, 0.086), "water": (0.07, 0.07)}
SHORT = {"double": "双联插座 Twin socket", "single": "单联插座 Single socket", "high": "空调插座 A/C socket", "outdoor": "户外插座 IP66"}


# ---------------- geometry helpers ----------------
def face_frame(L, R):
    run = math.dist(L, R); u = ((R[0] - L[0]) / run, (R[1] - L[1]) / run)
    return run, u


def along(L, u, p): return (p[0] - L[0]) * u[0] + (p[1] - L[1]) * u[1]


def inward(L, R, poly):
    run, u = face_frame(L, R)
    for n in ((-u[1], u[0]), (u[1], -u[0])):
        m = ((L[0] + R[0]) / 2 + n[0] * 0.05, (L[1] + R[1]) / 2 + n[1] * 0.05)
        if poly.contains(Point(m)): return n
    raise ValueError("face not on room boundary")


def r10(v): return int(round(v / 10.0) * 10)


def room_points(R):
    PLN, rows = so.locate(R["F"])
    poly = Polygon(R["poly"])
    faces = {f[0]: f for f in R["faces"]}
    wall, ceil = {k: [] for k in faces}, []
    key = next(k for k, v in ROOMS.items() if v is R)
    fcp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_fc_points.json")
    fc = json.load(open(fcp, encoding="utf-8")).get(key, {}) if os.path.exists(fcp) else {}
    for r in rows:
        if r["cat"] not in ("socket", "switch", "light", "new"): continue
        if r["id"] in R.get("drop", ()): continue                  # replaced by R["extra_pts"]
        p = r["p"]
        if r["id"] in fc:                                 # adjusted in FreeCAD (fc_bridge.py): exact position on that face
            q = fc[r["id"]]
            wall[q["face"]].append(dict(r, _sl=q["s"] / 1000.0, h=q["h"], note=R["override"].get(r["id"], (0, 0, ""))[2] or R["room_note"].get(r["id"], ""))); continue
        if r["id"] in R["override"]:
            k, d, why = R["override"][r["id"]][:3]      # d = distance from the face's right end; optional 4th item = new height
            hh = R["override"][r["id"]][3] if len(R["override"][r["id"]]) > 3 else (1360 if r["id"] == "S3" and R["cn"] == "次卧" else r["h"])
            wall[k].append(dict(r, _d=d, note=why, h=hh, **({"why": ""} if len(R["override"][r["id"]]) > 3 else {}))); continue   # new height: old data note no longer true
        if r.get("mount", "wall") in ("ceiling",) or r.get("wall") == "天花":
            if r["id"] in R.get("ceil_move", {}): r = dict(r, p=R["ceil_move"][r["id"]]); p = r["p"]   # owner-moved light
            if r["id"] in R.get("ceil_name", {}): r = dict(r, name=R["ceil_name"][r["id"]])          # owner-changed fitting
            if poly.buffer(0.02).contains(Point(p)): ceil.append(r)
            continue
        if r.get("wall") in ("地面", "室外地面", "岛台", "—"): continue
        best = None
        for k, nm, desc, L, Rr, ends in R["faces"]:
            run, u = face_frame(L, Rr); n = inward(L, Rr, poly)
            s = along(L, u, p); off = (p[0] - L[0]) * n[0] + (p[1] - L[1]) * n[1]
            if -0.02 <= s <= run + 0.02 and -0.03 <= off <= 0.35 and (best is None or off < best[0]): best = (off, k, s)
        if best: wall[best[1]].append(dict(r, _s=best[2], note=R["room_note"].get(r["id"], "")))
    ceil += [dict(r) for r in R.get("ceil_items", [])]                  # owner-added ceiling items (e.g. extract fan)
    for pid, c_ in R.get("circ_set", {}).items(): CIRC[pid] = c_         # owner-changed circuit (e.g. room on its own socket circuit)
    for e in R.get("extra_pts", []):                                     # owner-placed points (exact), e.g. flex outlets
        k, pid, name, s_mm, h_mm, why, circ = e[:7]; cat, kind = (e[7], e[8]) if len(e) > 8 else ("new", "")   # optional cat / kind
        wall[k].append(dict(cat=cat, id=pid, name=name, display_name=name, _sl=s_mm / 1000.0, h=h_mm, p=(0, 0), note=why, circ=circ, kind=kind))
    for k, pid, name, s_mm, h_mm, why in R.get("water_pts", []):
        wall[k].append(dict(cat="water", id=pid, name=name, display_name=name, _sl=s_mm / 1000.0, h=h_mm, p=(0, 0), note=why, circ="冷 / 热"))
    if R["cn"] == "次卧":
        _dL, _dR = next((f[3], f[4]) for f in R["faces"] if f[0] == "D"); _drun = math.dist(_dL, _dR)
        for pid,name,s_mm in [("SM","智能马桶开关",154),("ST","电热毛巾架开关",284)]:   # Rev N: beside the door (hinge side), h 1800
            wall["D"].append(dict(cat="switch", id=pid, name=name, display_name=name, _d=_drun - s_mm / 1000, h=1800, p=(0,0), note="卫浴门左侧墙段（门洞到墙角 434），中心离地 1800；两开关中心距 130，ST 离门洞边 150；控制卫浴内智能马桶 / 电热毛巾架（不装排风扇）；双极 FCU（建议 SM 13A、ST 3A），型号由电工定", circ="待定"))
    for pts in wall.values():
        for q in pts:
            if q["id"] == "N-TR2" and not q.get("display_name"): q["why"] = "智能马桶及毛巾架出线面板位置保留 h300；毛巾架已移至马桶上方；控制开关 ST 位于卫生间门上方"
    for k, pts in wall.items():
        _, _, _, L, Rr, _ = faces[k]; run, u = face_frame(L, Rr)
        for q in pts:
            if q.get("_sl") is not None: q["_d"] = run - q["_sl"]       # FreeCAD position: exact, like owner-set points
            if q.get("_d") is not None: q["_s"] = run - q["_d"]; q["p"] = (L[0] + u[0] * q["_s"], L[1] + u[1] * q["_s"])
            q["sL"] = round(q["_s"] * 1000) if q.get("_d") is not None else r10(q["_s"] * 1000); q["sR"] = round(run * 1000) - q["sL"]     # wall length exact (model), point to 10 mm
    return wall, ceil


def openings_on(R, L, Rr):
    run, u = face_frame(L, Rr); ln = LineString([L, Rr]); out = []
    for kind, nm, a, b, sill, head in R["openings"]:
        if ln.distance(Point(a)) > 0.03 or ln.distance(Point(b)) > 0.03: continue
        s0, s1 = sorted((along(L, u, a), along(L, u, b)))
        out.append((kind, nm, max(0, s0), min(run, s1), sill, head))
    return out


def furniture_on(R, L, Rr, poly):
    run, u = face_frame(L, Rr); n = inward(L, Rr, poly); ln = LineString([L, Rr]); out = []
    for label, (x0, y0, z0, x1, y1, z1) in R["furniture"]:
        bx = box(x0, y0, x1, y1)
        if bx.distance(ln) > 0.15: continue
        c = bx.centroid.coords[0]
        if (c[0] - L[0]) * n[0] + (c[1] - L[1]) * n[1] < 0: continue
        xs = [along(L, u, q) for q in bx.exterior.coords]
        a, b = max(0, min(xs)), min(run, max(xs))
        if b - a > 0.05: out.append((label, a, b, (z1 - R["fz"]) * 1000, max(0.0, (z0 - R["fz"]) * 1000)))
    return out


# ---------------- unfolded walls (owner 2026-10-09: 主客厅 front wall + bay = one elevation) ----------------
# R["unfold"] = {"A": (compass, description, ["A1", "A2", ...])}: sub-faces in R["faces"] (left -> right as seen from inside) keep
# the geometry for assigning points / openings / furniture; plans, tables and elevations show them as ONE wall, unfolded.
def ugroup(R, k): return R.get("unfold", {}).get(k)


def _members(R, k):
    g = ugroup(R, k)
    return [next(f for f in R["faces"] if f[0] == m) for m in g[2]] if g else []


def dfaces(R):
    """faces as displayed: every unfold group becomes one synthetic face (L = first member's L, R = last member's R)"""
    grp = {m: g for g, (nm, desc, ms) in R.get("unfold", {}).items() for m in ms}
    out, seen = [], set()
    for f in R["faces"]:
        g = grp.get(f[0])
        if g is None: out.append(f); continue
        if g in seen: continue
        seen.add(g); fs = _members(R, g); nm, desc, _ = R["unfold"][g]
        out.append((g, nm, desc, fs[0][3], fs[-1][4], (fs[0][5][0], fs[-1][5][1])))
    return out


def flen(R, k):
    fs = _members(R, k) or [f for f in R["faces"] if f[0] == k]
    return sum(math.dist(f[3], f[4]) for f in fs)


def folds_of(R, k):
    cum, out = 0.0, []
    for f in _members(R, k)[:-1]:
        cum += math.dist(f[3], f[4]); out.append(cum)
    return out


def unfold_pts(R, wall, k):
    if not ugroup(R, k): return wall[k]
    out, cum = [], 0.0
    for f in _members(R, k):
        for q in wall[f[0]]:
            q2 = dict(q, _s=q["_s"] + cum); q2["sL"] = q["sL"] + round(cum * 1000); out.append(q2)
        cum += math.dist(f[3], f[4])
    for q in out: q["sR"] = round(cum * 1000) - q["sL"]
    return out


def ops_of(R, k):
    if not ugroup(R, k):
        f = next(f for f in R["faces"] if f[0] == k); return openings_on(R, f[3], f[4])
    out, cum = [], 0.0
    for f in _members(R, k):
        out += [(kind, nm, a + cum, b + cum, sill, head) for kind, nm, a, b, sill, head in openings_on(R, f[3], f[4])]
        cum += math.dist(f[3], f[4])
    return out


def furn_of(R, k, poly):
    if not ugroup(R, k):
        f = next(f for f in R["faces"] if f[0] == k); return furniture_on(R, f[3], f[4], poly)
    out, cum = [], 0.0
    for f in _members(R, k):
        out += [(label, a + cum, b + cum, top, bot) for label, a, b, top, bot in furniture_on(R, f[3], f[4], poly)]
        cum += math.dist(f[3], f[4])
    return out


# ---------------- drawing primitives (page mm) ----------------
def hdim(A, x1, x2, y, txt, ext=None, above=True, fs=1.9):
    """horizontal dimension with 45° ticks; ext = y the extension lines start from"""
    if x2 - x1 < 0.01: return
    A(f'<line x1="{x1:.2f}" y1="{y:.2f}" x2="{x2:.2f}" y2="{y:.2f}" class="dim"/>')
    for x in (x1, x2):
        A(f'<line x1="{x-0.8:.2f}" y1="{y+0.8:.2f}" x2="{x+0.8:.2f}" y2="{y-0.8:.2f}" class="dim" style="stroke-width:.3"/>')
        if ext is not None: A(f'<line x1="{x:.2f}" y1="{ext:.2f}" x2="{x:.2f}" y2="{y+1.2:.2f}" class="dim" style="stroke:#999"/>')
    w = len(str(txt)) * fs * 0.56
    tx = (x1 + x2) / 2
    if x2 - x1 < w + 1: tx = x2 + w / 2 + 1.2        # too small: text outside, right
    A(f'<text x="{tx:.2f}" y="{y-0.7 if above else y+fs+0.4:.2f}" font-size="{fs}" text-anchor="middle" class="dimt">{E(str(txt))}</text>')


def vdim(A, x, y1, y2, txt, fs=1.9, side=-1):
    """vertical dimension (y1 top, y2 bottom); text rotated, on the left (side -1) or right"""
    A(f'<line x1="{x:.2f}" y1="{y1:.2f}" x2="{x:.2f}" y2="{y2:.2f}" class="dim"/>')
    for y in (y1, y2):
        A(f'<line x1="{x-0.8:.2f}" y1="{y+0.8:.2f}" x2="{x+0.8:.2f}" y2="{y-0.8:.2f}" class="dim" style="stroke-width:.3"/>')
    ty = (y1 + y2) / 2; tx = x + side * 0.7
    A(f'<text x="{tx:.2f}" y="{ty:.2f}" font-size="{fs}" text-anchor="middle" class="dimt" transform="rotate(-90 {tx:.2f} {ty:.2f})">{E(str(txt))}</text>')


def plate(A, cx, cy, w, h, cat, kind=""):
    c = COL.get(cat, "#333")
    A(f'<rect x="{cx-w/2:.2f}" y="{cy-h/2:.2f}" width="{w:.2f}" height="{h:.2f}" fill="#fff" stroke="{c}" stroke-width=".35" rx=".3"/>')
    if cat == "socket":
        n = 2 if kind == "double" else 1
        for i in range(n):
            px = cx - w / 2 + w * (i + 0.5) / n
            A(f'<line x1="{px-0.9:.2f}" y1="{cy:.2f}" x2="{px+0.9:.2f}" y2="{cy:.2f}" stroke="{c}" stroke-width=".3"/><line x1="{px:.2f}" y1="{cy-0.9:.2f}" x2="{px:.2f}" y2="{cy-0.2:.2f}" stroke="{c}" stroke-width=".3"/>')
    elif cat == "switch":
        A(f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r=".7" fill="{c}"/>')
    elif cat == "water":
        A(f'<path d="M{cx:.2f} {cy-1.1:.2f} L{cx+1:.2f} {cy+0.8:.2f} L{cx-1:.2f} {cy+0.8:.2f} Z" fill="{c}" fill-opacity=".25" stroke="{c}" stroke-width=".3"/>')
    else:
        A(f'<path d="M{cx:.2f} {cy-1:.2f} L{cx+1:.2f} {cy:.2f} L{cx:.2f} {cy+1:.2f} L{cx-1:.2f} {cy:.2f} Z" fill="none" stroke="{c}" stroke-width=".3"/>')
    A(f'<line x1="{cx-w/2-1:.2f}" y1="{cy:.2f}" x2="{cx+w/2+1:.2f}" y2="{cy:.2f}" stroke="{c}" stroke-width=".1"/>'
      f'<line x1="{cx:.2f}" y1="{cy-h/2-1:.2f}" x2="{cx:.2f}" y2="{cy+h/2+1:.2f}" stroke="{c}" stroke-width=".1"/>')


def pt_cat(r):
    return "new" if r["cat"] == "new" else r["cat"]


def pt_name(r):
    if r.get('display_name'): return r['display_name']
    if r["cat"] == "socket": return SHORT.get(r.get("kind"), r["name"])
    if r["cat"] == "switch":
        g = r["name"].split(" ")[0]
        return f"{g} 联开关 {g}-gang switch"
    return cgi(r["name"])


def pt_note(r):
    bits = []
    if r["cat"] == "socket":
        w0 = r.get("why", "").split("；")[0].replace("床头柜面 480 + 150（略高于柜面）", "床头柜面 485 + 150 ≈ 630")
        if r.get("h") not in (None, 630): w0 = w0.replace("床头柜面 485 + 150 ≈ 630", f"高于床头柜面，h{r['h']}").replace("床头柜面 485 + 150 = 630", f"高于床头柜面，h{r['h']}")
        bits.append(w0)
    if r["cat"] == "switch": bits.append("；".join(SW_LIGHTS.get(r["id"], [])))
    if r["cat"] == "new": bits.append(r.get("why", "").replace("；两个 FCU 13A 装在卫生间门外 h 1100", "；FCU 现场定，不在本图"))
    if r.get("note"): bits.append(r["note"])
    return cgi("；".join(b for b in bits if b))


# ---------------- sheets ----------------
def elevation(s, R, k, ox, oy, K, wall_pts):
    """one wall elevation, top-left of the ceiling line at (ox, oy); K = page mm per metre. Returns bottom y used."""
    A = s.add
    if k in R.get("face_ceil", {}): R = dict(R, ceil=R["face_ceil"][k])   # room with two ceiling heights
    poly = Polygon(R["poly"])
    if ugroup(R, k):
        _fs = _members(R, k); nm, desc = R["unfold"][k][0], R["unfold"][k][1]
        L, Rr, ends = _fs[0][3], _fs[-1][4], (_fs[0][5][0], _fs[-1][5][1]); run = flen(R, k)
    else:
        _, nm, desc, L, Rr, ends = next(f for f in R["faces"] if f[0] == k)
        run, u = face_frame(L, Rr)
    W, H = run * K, R["ceil"] / 1000 * K
    base = oy + H
    X = lambda sm: ox + sm * K
    Z = lambda zmm: base - zmm / 1000 * K
    A(f'<text x="{ox:.2f}" y="{oy-9:.2f}" font-size="3.4" class="ttl">立面 {k} · {nm}</text>'
      f'<text x="{ox:.2f}" y="{oy-5:.2f}" font-size="2.2" fill="#555">{E(desc)} · 比例 1:{int(1000/K)} · 站在房间里面对此墙</text>')
    # wall field, cut return walls at the ends, floor / ceiling
    A(f'<rect x="{ox:.2f}" y="{oy:.2f}" width="{W:.2f}" height="{H:.2f}" fill="#fcfcfc" stroke="none"/>')
    for x, e in ((ox, ends[0]), (ox + W, ends[1])):
        if e == "墙角": A(f'<rect x="{x-(2.4 if x == ox else 0):.2f}" y="{oy:.2f}" width="2.4" height="{H:.2f}" class="cut"/>')
        A(f'<line x1="{x:.2f}" y1="{oy:.2f}" x2="{x:.2f}" y2="{base:.2f}" class="wl"/>')
    A(f'<line x1="{ox-6:.2f}" y1="{base:.2f}" x2="{ox+W+6:.2f}" y2="{base:.2f}" class="fl"/>'
      f'<line x1="{ox-3:.2f}" y1="{oy:.2f}" x2="{ox+W+3:.2f}" y2="{oy:.2f}" class="wl"/>')
    A(f'<rect x="{ox-6:.2f}" y="{base:.2f}" width="{W+12:.2f}" height="1.6" fill="url(#hatch)"/>')
    A(f'<line x1="{ox:.2f}" y1="{Z(R["skirt"]):.2f}" x2="{ox+W:.2f}" y2="{Z(R["skirt"]):.2f}" class="thin"/>'
      f'<line x1="{ox:.2f}" y1="{Z(R["ceil"]-R["cove"]):.2f}" x2="{ox+W:.2f}" y2="{Z(R["ceil"]-R["cove"]):.2f}" class="thin"/>')
    # level marks on the left
    A(f'<text x="{ox-7:.2f}" y="{base+0.8:.2f}" font-size="1.9" text-anchor="end" fill="#b00020">±0 FFL</text>'
      f'<text x="{ox-7:.2f}" y="{oy+0.8:.2f}" font-size="1.9" text-anchor="end" fill="#555">{R.get("top_label", "天花")} {R["ceil"]}</text>')
    vdim(A, ox - 4.5, oy, base, R["ceil"], side=-1)
    # openings
    ops = ops_of(R, k)
    for kind, onm, a, b, sill, head in ops:
        cls = "win" if kind == "window" else "door"
        A(f'<rect x="{X(a):.2f}" y="{Z(head):.2f}" width="{(b-a)*K:.2f}" height="{(head-sill)/1000*K:.2f}" class="{cls}"/>')
        if kind == "window":
            A(f'<path d="M{X(a):.2f} {Z(head):.2f} L{X((a+b)/2):.2f} {Z(sill):.2f} L{X(b):.2f} {Z(head):.2f}" class="thin" style="stroke:#7a9cb8"/>')
        A(f'<text x="{X((a+b)/2):.2f}" y="{Z(head)+3:.2f}" font-size="1.9" text-anchor="middle" fill="#456">{E(onm)}</text>'
          f'<text x="{X((a+b)/2):.2f}" y="{Z(head)+5.4:.2f}" font-size="1.7" text-anchor="middle" fill="#456">洞 {round((b-a)*1000)} × {head-sill}</text>')
        if onm == "房门 762（门扇）":
            # Diagram shows combined lining / fitting allowance, not a selected frame profile.
            ia, ib = a + .033, b - .033
            A(f'<rect x="{X(a):.2f}" y="{Z(head):.2f}" width="{(b-a)*K:.2f}" height="{head/1000*K:.2f}" fill="#d9d1c4" stroke="#8d6e3f" stroke-width=".3"/>')
            A(f'<rect x="{X(ia):.2f}" y="{Z(1991):.2f}" width="{(ib-ia)*K:.2f}" height="{1981/1000*K:.2f}" class="door"/>')
            for dy, txt in [(10, "门扇 762 × 1981 × 35"), (15, "暂定门洞 828 × 2031"), (20, "两侧合计 66（框及缝）"), (25, "洞高从完成地面 FFL 起算"), (30, "门框及安装缝按成品复核")]:
                A(f'<text x="{X((a+b)/2):.2f}" y="{Z(head)+dy:.2f}" font-size="1.8" text-anchor="middle" fill="#456">{txt}</text>')
            hdim(A, X(ia), X(ib), Z(900), "762 门扇", ext=Z(820))
            hdim(A, X(a), X(b), Z(600), "828 含框预留", ext=Z(520))
        pd = R.get("op_design", {}).get(onm)
        if pd:                                           # owner-sketched panel layout: frame, glazed leaves, rails, labels, panel chain
            cuts = [0] + list(pd["cuts"]) + [round((b - a) * 1000)]
            for i, (c0, c1) in enumerate(zip(cuts, cuts[1:])):
                g0, g1 = a + c0 / 1000 + .035, a + c1 / 1000 - .035
                pk = pd.get("kinds", ["glass"] * len(cuts))[i]
                A(f'<rect x="{X(g0):.2f}" y="{Z(head-160):.2f}" width="{(g1-g0)*K:.2f}" height="{(head-230)/1000*K:.2f}" class="{"win" if pk == "glass" else "door"}"/>')
                if pd.get("swing", (None,))[0] == i:     # opening triangle: apex at the hinge side
                    hx, fx = (g0, g1) if pd["swing"][1] == "L" else (g1, g0)
                    A(f'<path d="M{X(fx):.2f} {Z(head-160):.2f} L{X(hx):.2f} {Z((head-90)/2):.2f} L{X(fx):.2f} {Z(70):.2f}" class="thin" style="stroke:#8d6e3f"/>')
                for z in pd.get("rails", {}).get(i, []):
                    A(f'<line x1="{X(g0):.2f}" y1="{Z(z):.2f}" x2="{X(g1):.2f}" y2="{Z(z):.2f}" stroke="#8d6e3f" stroke-width=".9"/>')
                for j, t in enumerate(pd["labels"][i].split("|")):
                    A(f'<text x="{X((g0+g1)/2):.2f}" y="{Z(head)+12+j*2.4:.2f}" font-size="1.6" text-anchor="middle" fill="#456">{E(t)}</text>')
                hdim(A, X(a + c0 / 1000), X(a + c1 / 1000), Z(300), str(c1 - c0), fs=1.7)
            for i, zs in list(pd.get("rails", {}).items())[:1]:
                vdim(A, X(a + cuts[i] / 1000) + 2.2, Z(zs[0]), base, zs[0], fs=1.6, side=1)
        if kind == "window": vdim(A, X(b) - 2.2, Z(sill), base, sill, fs=1.7)
        vdim(A, X(b) - (5 if kind == "window" else 2.2), Z(head), base, head, fs=1.7)
    # built features from the plumbing drawings (pre-wall, niches, wall drain, access panel): s / z in mm on this face
    feat_m = list(folds_of(R, k))
    for fk, label, s0, s1, z0, z1, style in R.get("features", []):
        if fk != k: continue
        if style == "note":                                              # owner note box: dashed frame, lines split by "|"
            A(f'<rect x="{X(s0/1000):.2f}" y="{Z(z1):.2f}" width="{(s1-s0)/1000*K:.2f}" height="{(z1-z0)/1000*K:.2f}" fill="#fff8e1" stroke="#c62828" stroke-width=".3" stroke-dasharray="1.2 .6"/>')
            for j, t in enumerate(label.split("|")):
                A(f'<text x="{X(s0/1000)+1.5:.2f}" y="{Z(z1)+3+j*2.6:.2f}" font-size="1.8" fill="#b71c1c">{E(t)}</text>')
            continue
        st = {"pre": 'fill="#f2efe8" stroke="#8a7a5c" stroke-width=".25"', "niche": 'fill="#fff" stroke="#00897b" stroke-width=".35"',
              "drain": 'fill="#00897b" fill-opacity=".35" stroke="#00897b" stroke-width=".3"', "panel": 'fill="none" stroke="#00897b" stroke-width=".3" stroke-dasharray="1 .6"'}[style]
        A(f'<rect x="{X(s0/1000):.2f}" y="{Z(z1):.2f}" width="{(s1-s0)/1000*K:.2f}" height="{(z1-z0)/1000*K:.2f}" {st}/>')
        ty = Z(z1) + 2.6 if style in ("pre",) else (Z(z0) + 3.2 if style in ("drain", "panel") else Z(z1) - 1)
        if style == "pre": ty = Z(z1) + 2.6
        A(f'<text x="{X((s0+s1)/2000):.2f}" y="{ty:.2f}" font-size="1.7" text-anchor="middle" fill="#00695c">{E(label)}' + (f'（{z0}–{z1}）' if style in ("niche", "panel") else "") + '</text>')
        if style in ("niche", "drain", "panel"): feat_m += [s0 / 1000, s1 / 1000]
        if style == "niche": vdim(A, X(s1/1000) + 1.2, Z(z1), Z(z0), z1 - z0, fs=1.6, side=1)
    # furniture (dashed)
    for fx in folds_of(R, k):                                            # unfolded wall: corner lines
        A(f'<line x1="{X(fx):.2f}" y1="{oy:.2f}" x2="{X(fx):.2f}" y2="{base:.2f}" stroke="#555" stroke-width=".25" stroke-dasharray="2 1"/>')
    for label, a, b, top, bot in furn_of(R, k, poly):
        A(f'<rect x="{X(a):.2f}" y="{Z(top):.2f}" width="{(b-a)*K:.2f}" height="{(top-bot)/1000*K:.2f}" class="furn"/>'
          f'<text x="{X((a+b)/2):.2f}" y="{Z(top)-1:.2f}" font-size="1.7" text-anchor="middle" class="ft">{E(label)} · 顶 {int(round(top))}</text>')
    if R["cn"] == "次卧" and k == "H":
        cx = X(1.704)
        A(f'<line x1="{cx:.2f}" y1="{Z(1420):.2f}" x2="{cx:.2f}" y2="{Z(1100):.2f}" stroke="#999" stroke-width=".15" stroke-dasharray="1 .6"/>')
        vdim(A, cx+10, Z(1360), Z(1210), "150", fs=2.2, side=1)
        for height in (1360, 1210):
            A(f'<line x1="{cx+3:.2f}" y1="{Z(height):.2f}" x2="{cx+12:.2f}" y2="{Z(height):.2f}" class="thin"/>')
        A(f'<text x="{cx+16:.2f}" y="{Z(1285):.2f}" font-size="2.1" fill="#444">开关中心高于床头板 150</text>')
    if R["cn"] == "次卧完整卫浴" and k == "C":
        mid = 1.568
        cx = X(mid)
        A(f'<line x1="{cx:.2f}" y1="{Z(2000):.2f}" x2="{cx:.2f}" y2="{Z(850):.2f}" stroke="#999" stroke-width=".15" stroke-dasharray="1 .6"/>')
        vdim(A, X(mid-.250)-4, Z(1300), base, "1300 底边", fs=2.0)
        vdim(A, X(mid+.250)+3, Z(1943), Z(1300), "643", fs=2.0, side=1)
        hdim(A, X(mid-.250), X(mid+.250), Z(1943)-6, "500", ext=Z(1943), fs=2.0)
        A(f'<text x="{cx:.2f}" y="{Z(1100):.2f}" font-size="2.0" text-anchor="middle" fill="#555">毛巾架与马桶中心对齐</text>')
    # points (BG_MODE: FreeCAD underlay — the editable plates, labels and the chain are drawn live in FreeCAD instead)
    R.setdefault("_layout", {})[k] = dict(sheet=s.number, ox=ox, base=base, K=K)
    pts = [] if BG_MODE else sorted(wall_pts, key=lambda r: r["_s"])
    boxes = []
    for r in pts:
        w, h = PLATE.get(r.get("kind") if r["cat"] == "socket" else r["cat"], (0.086, 0.086))
        cx, cy = X(r["_s"]), Z(r["h"])
        plate(A, cx, cy, w * K, h * K, pt_cat(r), r.get("kind", ""))
        boxes.append((cx - w * K / 2, cx + w * K / 2))
    labels = []
    rects = []
    used_vx = []
    for r in pts:
        w, h = PLATE.get(r.get("kind") if r["cat"] == "socket" else r["cat"], (0.086, 0.086)); cx, cy = X(r["_s"]), Z(r["h"])
        rects.append((cx - w * K / 2, cx + w * K / 2, cy - h * K / 2, cy + h * K / 2))
    for i, r in enumerate(pts):
        w, h = PLATE.get(r.get("kind") if r["cat"] == "socket" else r["cat"], (0.086, 0.086))
        cx, cy = X(r["_s"]), Z(r["h"]); c = COL.get(pt_cat(r))
        # height dimension beside the plate (right side unless another plate is there)
        dx = w * K / 2 + 1.8
        side = 1
        if any(b[0] < cx + dx + 1 < b[1] + 2.5 for j, b in enumerate(boxes) if j != i): side = -1
        if any(abs(cx + side * dx - u_) < 1.5 for u_ in used_vx): side = -side          # stacked plates: other side
        vx = cx + side * dx
        if any(abs(vx - u_) < 1.5 for u_ in used_vx): vx += side * 3.5                  # still taken: step outwards
        used_vx.append(vx)
        vdim(A, vx, cy, base, r["h"], fs=1.8, side=side)
        A(f'<line x1="{min(vx, cx):.2f}" y1="{cy:.2f}" x2="{max(vx, cx):.2f}" y2="{cy:.2f}" class="dim" style="stroke:#999"/>')
        txt = f'{r["id"]} · h {r["h"]}'; tw = len(txt) * 1.25
        ly0 = ly = cy - h * K / 2 - 1.4
        hit = lambda yy: any(abs(cx - q[0]) < (tw + q[2]) / 2 + 0.8 and abs(yy - q[1]) < 2.6 for q in labels) or             any(cx - tw / 2 < b[1] and cx + tw / 2 > b[0] and yy - 2 < b[3] and yy + 0.6 > b[2] for b in rects)
        while hit(ly): ly -= 2.8
        labels.append((cx, ly, tw))
        if ly < ly0 - 0.1: A(f'<line x1="{cx:.2f}" y1="{ly+0.6:.2f}" x2="{cx:.2f}" y2="{ly0+0.6:.2f}" stroke="{c}" stroke-width=".12"/>')
        A(f'<text x="{cx:.2f}" y="{ly:.2f}" font-size="2.2" text-anchor="middle" fill="{c}" font-weight="bold">{E(txt)}</text>')
    # chain under the floor line: wall ends + opening edges + point centres, rounded cumulatively so the parts add up
    ops_m = [v for o in ops for v in (o[2], o[3])] + feat_m
    marks = sorted({0.0, run, *ops_m, *[r["_s"] for r in pts]})
    y1 = base + 6
    pt_s = {r["_s"] for r in pts if r.get("_d") is None}       # owner-dimensioned points (override) stay exact
    cum = [r10(m * 1000) if m in pt_s and m not in ops_m else round(m * 1000) for m in marks]   # openings / ends exact mm, points 10 mm
    for (a, b), (ca, cb) in zip(zip(marks, marks[1:]), zip(cum, cum[1:])):
        if cb - ca > 0 and not BG_MODE: hdim(A, X(a), X(b), y1, cb - ca, ext=base + 1.8)
    A(f'<text x="{ox-7:.2f}" y="{y1+0.6:.2f}" font-size="1.7" text-anchor="end" fill="#555">定位</text>')
    y2 = y1 + 6
    hdim(A, X(0), X(run), y2, f"{round(run*1000)}（净长 clear）", ext=base + 1.8)
    y3 = y2
    A(f'<text x="{ox:.2f}" y="{y3+4.5:.2f}" font-size="1.9" fill="#444">← 左端 L：{E(ends[0])}</text>'
      f'<text x="{ox+W:.2f}" y="{y3+4.5:.2f}" font-size="1.9" text-anchor="end" fill="#444">右端 R：{E(ends[1])} →</text>')
    return y3 + 6


def point_rows(R, k, pts):
    out = []
    for r in sorted(pts, key=lambda r: r["_s"]):
        circ = CIRC.get(r["id"], "") if r["cat"] == "socket" else ("WL4" if r["cat"] == "switch" else r.get("circ", ""))
        if r.get("display_name"): circ = r["circ"]
        out.append([f"{k}-{r['id']}", pt_name(r), circ, r["sL"], r["sR"], r["h"], pt_note(r)])
    return out


COLS = [("面-编号", 13), ("名称 Item", 40), ("回路", 11), ("距左端 L", 16), ("距右端 R", 16), ("离地 h", 13), ("备注 Notes（高度 = 底盒中心离本房间完成地面）", 175)]
NOTES = ["说明 Notes",
         "1. 尺寸单位 mm。水平尺寸量到底盒中心，从完成墙面（抹灰 / 石膏板后）起量；左 / 右端 = 站在房间里面对这面墙的左 / 右手边。",
         "2. 高度 h = 底盒中心离本房间完成地面（二层前部 FFL = 结构 3.208）。开关 1200；普通插座 450（英国规格）；床头插座 = 柜面 + 150。",
         "3. 底稿：Blender 模型 v44（西卫方案 B）的墙面、门窗洞、天花、家具；点位：点位定位尺寸图 Rev A。专用电器开关 / FCU 不在本图（业主现场定，计划集中在楼梯下）。",
         "4. 墙体以现场完成面为准，与本图相差 > 50 mm 时先停工联系业主。点位离墙角 / 门框 < 150 时现场先核。"]


def sheet(R, number, title, scale):
    s = Sheet(f"{(R['suite_cn'] + ' · ') if R.get('suite_cn') else ''}{R['cn']} {title}", number, R["F"], ((0, 1), (0, 1)), scale_note=scale, discipline="墙面立面 / 点位 Wall elevations", **dict(REV, **R.get("rev", {})))
    s.defs.append('<pattern id="hatch" width="1.6" height="1.6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="1.6" stroke="#666" stroke-width=".25"/></pattern>')
    return s


def elev_sheet(R, ks, number, wall):
    lens = [flen(R, k) for k in ks]
    K = 50.0 if sum(lens) * 50 + 30 * len(ks) < 380 and 42 + R["ceil"] / 1000 * 50 < 190 else 40.0   # tall (outdoor) walls: 1:25
    s = sheet(R, number, "立面 " + " / ".join(ks) + " Wall elevation", f"1:{int(1000/K)}")
    x = 30.0; bottom = 0
    for k, ln in zip(ks, lens):
        bottom = max(bottom, elevation(s, R, k, x, 42, K, unfold_pts(R, wall, k)))
        x += ln * K + 34
    rows = [row for k in ks for row in point_rows(R, k, unfold_pts(R, wall, k))]
    for k in ks:
        if not unfold_pts(R, wall, k): rows.append([k, "本面墙无点位 No points", "", "", "", "", "只画门窗洞 / 家具，供核对尺寸"])
    ty = max(bottom + 8, 196)
    table(s, 14, ty, COLS, rows, fs=2.0, title="点位表 Point schedule（本图）")
    keyplan(s, R, hi=ks)
    s.add(f'<text x="14" y="{ty-6.5:.1f}" font-size="2.1" fill="#444">尺寸 mm · 水平尺寸量到底盒中心（完成墙面起量）· h = 底盒中心离本房间完成地面 · 左 / 右 = 面对此墙 · 全部说明见 {R["_index_sheet"]}</text>')
    s.frame()
    return s


_PLN = {}


def keyplan(s, R, hi=(), ceiling=False, x0=300.0, y0=197.0, bw=110.0, bh=55.0):
    """small plan of the space in the empty corner above the notes; hi = wall letters to highlight (red).
    A suite (R["_suite"] = member rooms) is drawn whole; only R's own faces can be highlighted."""
    A = s.add
    members = R.get("_suite") or [R]
    from shapely.ops import unary_union
    allpoly = unary_union([Polygon(M["poly"]) for M in members]); bx0, by0, bx1, by1 = allpoly.bounds
    m = 0.35; k = min((bw - 6) / (by1 - by0 + 2 * m), (bh - 12) / (bx1 - bx0 + 2 * m))
    ox = x0 + (bw - (by1 - by0 + 2 * m) * k) / 2 - (by0 - m) * k; oy = y0 + 8 - (bx0 - m) * k
    P = lambda x, y: (ox + y * k, oy + x * k)
    title = R.get("suite_cn") or R["cn"]
    A(f'<rect x="{x0}" y="{y0}" width="{bw}" height="{bh}" fill="#fff" stroke="#999" stroke-width=".25"/>'
      f'<text x="{x0+2}" y="{y0+4.2}" font-size="2.4" font-weight="bold">位置示意 Key plan · {E(title)}</text>'
      f'<text x="{x0+bw-2}" y="{y0+4.2}" font-size="1.8" text-anchor="end" fill="#666">北 ↑　前门 ← → 后院</text>')
    if R["F"] not in _PLN: _PLN[R["F"]] = so.Plan(R["F"])
    g = revised_walls(R).intersection(box(bx0 - m, by0 - m, bx1 + m, by1 + m))
    for G in getattr(g, "geoms", [g]):
        if G.is_empty or G.geom_type != "Polygon": continue
        d = "".join("M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in (P(*c) for c in ring.coords)) + " Z " for ring in [G.exterior] + list(G.interiors))
        A(f'<path d="{d}" fill="#d6d6d6" stroke="#888" stroke-width=".12" style="fill-rule:evenodd"/>')
    for M in members:
        mine = M is R or len(members) == 1
        fill = ("#ffe0cc" if ceiling else "#fffdf6") if (mine or ceiling) else "#f4f4f4"
        A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in (P(*c) for c in M["poly"])) + f' Z" fill="{fill}" stroke="#333" stroke-width=".25"/>')
        for label, (fx0, fy0, fz0, fx1, fy1, fz1) in M["furniture"]:
            (a, b), (c, d) = P(fx0, fy0), P(fx1, fy1)
            A(f'<rect x="{min(a,c):.2f}" y="{min(b,d):.2f}" width="{abs(c-a):.2f}" height="{abs(d-b):.2f}" fill="#efe9dc" stroke="#b5a88c" stroke-width=".12"/>')
        for kind, nm, a, b, sill, head in M["openings"]:
            (ax, ay), (bx_, by_) = P(*a), P(*b)
            A(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx_:.2f}" y2="{by_:.2f}" stroke="{"#4f7ea8" if kind == "window" else fill}" stroke-width="1"/>')
        if len(members) > 1 and not ceiling:
            c = Polygon(M["poly"]).representative_point().coords[0]; q = P(*c)
            A(f'<text x="{q[0]:.2f}" y="{q[1]+0.7:.2f}" font-size="1.8" text-anchor="middle" fill="#999">{E(M["cn"])}</text>')
    poly = Polygon(R["poly"]); rb = poly.bounds
    placed = []                                              # page positions of letters already drawn (avoid overlaps)
    base_off = min(0.75, 0.3 * min(rb[2] - rb[0], rb[3] - rb[1]))          # small rooms: keep the letters near their wall
    for f in sorted(dfaces(R), key=lambda f: f[0] not in hi):            # highlighted letters first
        kk, nm, desc, L, Rr, ends = f; on = kk in hi
        n = inward(L, Rr, poly); run_, u = face_frame(L, Rr)
        if on:
            for (sa, sb) in ([(m[3], m[4]) for m in _members(R, kk)] or [(L, Rr)]):
                (lx, ly), (rx, ry) = P(*sa), P(*sb)
                A(f'<line x1="{lx:.2f}" y1="{ly:.2f}" x2="{rx:.2f}" y2="{ry:.2f}" stroke="#d32f2f" stroke-width="1.3" stroke-linecap="round"/>')
            best, fallback = None, None
            for t_along in (0.5, 0.3, 0.7, 0.18, 0.82):
                for off in (base_off, base_off * 0.6, base_off * 1.35, base_off * 0.4):
                    mid = (L[0] + u[0] * run_ * t_along, L[1] + u[1] * run_ * t_along)
                    qq = (mid[0] + n[0] * off, mid[1] + n[1] * off)
                    q = P(*qq)
                    if not poly.buffer(0.05).contains(Point(qq)): continue
                    gap = min([math.dist(q, o) for o in placed] or [99])
                    if gap > 8.0: best = (q, mid); break
                    if fallback is None or gap > fallback[0]: fallback = (gap, q, mid)   # otherwise: the spot farthest from the others
                if best: break
            if best is None and fallback: best = fallback[1:]
            q, mid = best or (P(L[0] + u[0] * run_ / 2 + n[0] * base_off, L[1] + u[1] * run_ / 2 + n[1] * base_off), (L[0] + u[0] * run_ / 2, L[1] + u[1] * run_ / 2))
            placed.append(q)
            tq = P(mid[0] + n[0] * 0.15, mid[1] + n[1] * 0.15)
            A(f'<line x1="{q[0]:.2f}" y1="{q[1]:.2f}" x2="{tq[0]:.2f}" y2="{tq[1]:.2f}" stroke="#d32f2f" stroke-width=".35" marker-end="url(#kar)"/>'
              f'<circle cx="{q[0]:.2f}" cy="{q[1]:.2f}" r="2.1" fill="#d32f2f"/><text x="{q[0]:.2f}" y="{q[1]+0.95:.2f}" font-size="2.6" text-anchor="middle" fill="#fff" font-weight="bold">{kk}</text>')
        elif not ceiling:
            mid = ((L[0] + Rr[0]) / 2, (L[1] + Rr[1]) / 2)
            q = P(mid[0] + n[0] * 0.3, mid[1] + n[1] * 0.3)
            if any(math.dist(q, o) < 4.0 for o in placed): continue
            placed.append(q)
            A(f'<text x="{q[0]:.2f}" y="{q[1]+0.7:.2f}" font-size="1.9" text-anchor="middle" fill="#aaa">{kk}</text>')
    if ceiling:
        for M in members:
            _, lights = room_points(M)
            for light in lights:
                lx, ly = P(*light["p"])
                actual = M["cn"] == "次卧" and light["id"] == "L03"
                radius = .250 * k if actual else 1.2
                dash = "" if actual else ' stroke-dasharray=".6 .4"'
                A(f'<circle cx="{lx:.2f}" cy="{ly:.2f}" r="{radius:.2f}" fill="#ff8a00" fill-opacity=".18" stroke="#e65100" stroke-width=".4"{dash}/>')
                A(f'<path d="M{lx-1.2:.2f} {ly:.2f} H{lx+1.2:.2f} M{lx:.2f} {ly-1.2:.2f} V{ly+1.2:.2f}" stroke="#c33" stroke-width=".3"/>')
                label = light["id"] + (" / F19" if actual else "")
                A(f'<text x="{lx+radius+1:.2f}" y="{ly-1:.2f}" font-size="2.2" fill="#c43b00" font-weight="bold" style="paint-order:stroke;stroke:white;stroke-width:.7">{label}</text>')
        A(f'<text x="{x0+2}" y="{y0+bh-1.8}" font-size="1.8" fill="#555">' + ("橙色为灯位投影；F19 圆圈按 Ø500；待选灯仅示中心" if R["cn"] == "次卧" else "橙色为灯位投影（只示中心）") + '</text>')
    s.defs.append('<marker id="kar" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto"><path d="M0 0 L4 2 L0 4 Z" fill="#d32f2f"/></marker>')


def plan_k(poly):
    bx0, by0, bx1, by1 = poly.bounds
    return 50.0 if (by1 - by0) * 50 < 280 and (bx1 - bx0) * 50 < 140 else 40.0


def plan_xy(s, K, x0, y0):
    return lambda x, y: (x0 + y * K, y0 + x * K)


def index_sheet(R, number, wall, ceil):
    poly = Polygon(R["poly"]); bx0, by0, bx1, by1 = poly.bounds
    K = R.get("plan_k") or plan_k(poly)
    s = sheet(R, number, f"平面布置（{R.get('plan_kind', '带家具')}）+ 墙面索引 Furnished plan & key", f"1:{int(1000/K)}")
    A = s.add
    P = plan_xy(s, K, 30 - by0 * K, 46 - bx0 * K)
    PLN = so.Plan(R["F"])
    clip = box(bx0 - 0.45, by0 - 0.45, bx1 + 0.45, by1 + 0.45)
    def path(g, cls):
        geoms = getattr(g, "geoms", [g])
        for G in geoms:
            if G.is_empty or G.geom_type != "Polygon": continue
            d = ""
            for ring in [G.exterior] + list(G.interiors):
                d += "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in (P(*c) for c in ring.coords)) + " Z "
            A(f'<path d="{d}" class="{cls}" style="fill-rule:evenodd"/>')
    path(revised_walls(R).intersection(clip), "b-wall")
    pts = [P(*c) for c in R["poly"]]
    A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + ' Z" fill="#fffdf6" stroke="#222" stroke-width=".45"/>')
    if R["cn"] == "次卧完整卫浴":
        ax, ay = P(-2.621, 6.338)
        bx, by = P(-.711, 7.928)
        hdim(A, ax, bx, by+7, "1590 净尺寸", ext=by, fs=2.5)
        vdim(A, ax-7, ay, by, "1910 净尺寸", fs=2.5)
    # openings on the room faces
    for kind, nm, a, b, sill, head in R["openings"]:
        (ax, ay), (bx, by) = P(*a), P(*b)
        A(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" stroke="{"#4f7ea8" if kind == "window" else "#fffdf6"}" stroke-width="{2.2 if kind == "window" else 1.2}"/>')
        mx, my = (ax + bx) / 2, (ay + by) / 2
        A(f'<text x="{mx:.2f}" y="{my + (4 if kind == "window" else 0):.2f}" font-size="1.8" text-anchor="middle" fill="#456">{E(nm.split(" ")[0])}</text>' if kind == "window" else "")
    for h, c, o in R["swings"]:
        (hx, hy), (cx, cy), (oxx, oyy) = P(*h), P(*c), P(*o); rr = math.dist((hx, hy), (cx, cy))
        A(f'<path d="M{oxx:.2f} {oyy:.2f} L{hx:.2f} {hy:.2f} M{cx:.2f} {cy:.2f} A{rr:.2f} {rr:.2f} 0 0 {1 if (cx-hx)*(oyy-hy)-(cy-hy)*(oxx-hx) > 0 else 0} {oxx:.2f} {oyy:.2f}" fill="none" stroke="#8d6e3f" stroke-width=".25"/>')
    for label, (x0, y0, z0, x1, y1, z1) in R["furniture"]:
        if label.startswith("电热毛巾架") and R is BA:
            (a,b),(c,d)=P(x0,y0),P(x1,y1)
            A(f'<rect x="{a:.2f}" y="{b:.2f}" width="{c-a:.2f}" height="{d-b:.2f}" fill="#efe9dc" stroke="#8a7a5c" stroke-width=".3"/>')
            tx,ty=c+10,(b+d)/2
            A(f'<line x1="{c:.2f}" y1="{ty:.2f}" x2="{tx-1:.2f}" y2="{ty:.2f}" stroke="#777" stroke-width=".2"/><text x="{tx:.2f}" y="{ty:.2f}" font-size="2.1">F31 毛巾架（马桶上方）</text><text x="{tx:.2f}" y="{ty+3:.2f}" font-size="2.0">底边 1300 / 顶边 1943</text>')
            continue
        (a, b), (c, d) = P(x0, y0), P(x1, y1)
        A(f'<rect x="{min(a,c):.2f}" y="{min(b,d):.2f}" width="{abs(c-a):.2f}" height="{abs(d-b):.2f}" fill="#efe9dc" stroke="#8a7a5c" stroke-width=".3"/>'
          f'<text x="{(a+c)/2:.2f}" y="{(b+d)/2-0.4:.2f}" font-size="1.9" text-anchor="middle" fill="#5d4e33">{E(label.split("（")[0])}</text>'
          f'<text x="{(a+c)/2:.2f}" y="{(b+d)/2+2.2:.2f}" font-size="1.6" text-anchor="middle" fill="#7d6e53">{r10((y1-y0)*1000)}×{r10((x1-x0)*1000)} h{r10((z1-R["fz"])*1000)}</text>')
    # wall letters: circle + arrow pointing at the face
    for k, nm, desc, L, Rr, ends in dfaces(R):
        n = inward(L, Rr, poly); m = ((L[0] + Rr[0]) / 2, (L[1] + Rr[1]) / 2)
        q = (m[0] + n[0] * 0.42, m[1] + n[1] * 0.42); (qx, qy), (tx, ty) = P(*q), P(m[0] + n[0] * 0.12, m[1] + n[1] * 0.12)
        A(f'<line x1="{qx:.2f}" y1="{qy:.2f}" x2="{tx:.2f}" y2="{ty:.2f}" stroke="#c62828" stroke-width=".4" marker-end="url(#ar)"/>'
          f'<circle cx="{qx:.2f}" cy="{qy:.2f}" r="2.6" fill="#fff" stroke="#c62828" stroke-width=".4"/><text x="{qx:.2f}" y="{qy+1.1:.2f}" font-size="3" text-anchor="middle" fill="#c62828" font-weight="bold">{k}</text>')
    s.defs.append('<marker id="ar" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto"><path d="M0 0 L4 2 L0 4 Z" fill="#c62828"/></marker>')
    # points
    for k, rs in wall.items():
        _, _, _, L, Rr, _ = next(f for f in R["faces"] if f[0] == k); run, u = face_frame(L, Rr); n = inward(L, Rr, poly)
        for r in rs:
            p = (L[0] + u[0] * r["_s"] + n[0] * 0.07, L[1] + u[1] * r["_s"] + n[1] * 0.07); px, py = P(*p)
            A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1" fill="{COL[pt_cat(r)]}"/>')
            lp = P(p[0] + n[0] * 0.22, p[1] + n[1] * 0.22)
            A(f'<text x="{lp[0]:.2f}" y="{lp[1]+0.7:.2f}" font-size="1.9" text-anchor="middle" fill="{COL[pt_cat(r)]}" font-weight="bold">{E(r["id"])}</text>')
    for r in ceil:
        px, py = P(*r["p"])
        A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.6" fill="#fff" stroke="{COL["light"]}" stroke-width=".35" stroke-dasharray=".8 .5"/>'
          f'<text x="{px+2.4:.2f}" y="{py+0.7:.2f}" font-size="1.8" fill="{COL["light"]}">{E(r["id"])}（天花）</text>')
    # orientation
    A('<g transform="translate(372,95)"><line x1="-12" y1="0" x2="12" y2="0" stroke="#222" stroke-width=".3" marker-end="url(#ar)"/>'
      '<text x="-13" y="1" font-size="2" text-anchor="end">西 Front</text><text x="14" y="1" font-size="2">东 Rear</text>'
      '<line x1="0" y1="8" x2="0" y2="-8" stroke="#222" stroke-width=".3" marker-end="url(#ar)"/><text x="0" y="-10" font-size="2" text-anchor="middle">北 North</text></g>')
    # index table
    rows = []
    sheets = {k: num for num, ks in R["_sheetmap"] for k in ks}
    for k, nm, desc, L, Rr, ends in dfaces(R):
        ids = " ".join(r["id"] for r in sorted(unfold_pts(R, wall, k), key=lambda r: r["_s"])) or "—"
        ops = " ".join(o[1].split(" ")[0] for o in ops_of(R, k)) or "—"
        rows.append([k, f"{nm} · {desc}", round(flen(R, k) * 1000), f"{ends[0]} → {ends[1]}", ops, ids, sheets.get(k, "")])
    if not R.get("no_ceiling"):
        rows.append(["天花", "Ceiling（反射平面）", "", f"高 {R['ceil']}，顶角线 {R['cove']}", "", " ".join(r["id"] for r in ceil), R["_ceil_sheet"]])
    table(s, 14, 218, [("面", 9), ("墙 Wall", 62), ("净长", 12), ("左端 → 右端", 40), ("门窗", 20), ("点位", 30), ("立面图号", 34)], rows, fs=2.0,
          title="墙面索引 Wall index（字母 = 立面编号，红箭头指向被看的墙）")
    y = 40; lx = 346
    A(f'<text x="{lx}" y="{y}" font-size="2.6" font-weight="bold">图例 Legend</text>')
    for i, (cat, t) in enumerate([("socket", "插座 Socket"), ("switch", "开关 Switch"), ("light", "天花灯（见天花图）")]):
        yy = y + 5 + i * 4.6
        A(f'<circle cx="{lx+2:.2f}" cy="{yy-0.8:.2f}" r="{1.6 if cat == "light" else 1}" fill="{"#fff" if cat == "light" else COL[cat]}" stroke="{COL[cat]}" stroke-width=".35"/>')
        A(f'<text x="{lx+6}" y="{yy:.1f}" font-size="2.1">{E(t)}</text>')
    A(f'<rect x="{lx}" y="{y+17.5:.1f}" width="5" height="3" fill="#efe9dc" stroke="#8a7a5c" stroke-width=".3"/><text x="{lx+6}" y="{y+19.9:.1f}" font-size="2.1">家具（模型 v44，宽×深 h 高）</text>'
      f'<circle cx="{lx+2.5}" cy="{y+26:.1f}" r="2" fill="#fff" stroke="#c62828" stroke-width=".35"/><text x="{lx+2.5}" y="{y+26.8:.1f}" font-size="2.2" text-anchor="middle" fill="#c62828">A</text>'
      f'<text x="{lx+6}" y="{y+26.8:.1f}" font-size="2.1">立面编号 → 被看的墙</text>')
    if R.get("water"):          # fixtures + their pipes from the plumbing set Rev C (outlet positions / heights not fixed there)
        for code, nm, pipes, p in R["water"]:
            px, py = P(*p)
            A(f'<path d="M{px:.2f} {py-2:.2f} L{px+1.8:.2f} {py+1.2:.2f} L{px-1.8:.2f} {py+1.2:.2f} Z" fill="#fff" stroke="{COL["water"]}" stroke-width=".35"/>'
              f'<text x="{px+2.6:.2f}" y="{py+0.8:.2f}" font-size="2" fill="{COL["water"]}" font-weight="bold">{code}</text>')
        yb = 218 + 3.6 * (len(R["faces"]) + 2) + 10
        table(s, 14, yb, [("编号", 12), ("洁具 Fixture", 60), ("给排水（给排水施工图 Rev C）", 90), ("出口位置 / 高度", 45)],
              [[c, n, pp, "按洁具安装说明现场定"] for c, n, pp, _ in R["water"]], fs=2.0, title="给排水点 Plumbing points（只标洁具，出口未定）")
    floor_txt = None if R["F"] == "FF" and abs(R["fz"] - 3.208) < 1e-6 else ("（一层 FFL = 0）" if R["F"] == "GF" else f"（本房间 FFL = 结构 {R['fz']:.3f}，二层后部）")
    notes = NOTES if floor_txt is None else [n.replace("（二层前部 FFL = 结构 3.208）", floor_txt) for n in NOTES]
    s.frame(notes + [R.get("notes5", "")])
    return s


def ceiling_sheet(R, number, ceil):
    poly = Polygon(R["poly"]); bx0, by0, bx1, by1 = poly.bounds
    K = R.get("plan_k") or plan_k(poly)
    s = sheet(R, number, "天花 Reflected ceiling plan", f"1:{int(1000/K)}")
    A = s.add
    P = plan_xy(s, K, 30 - by0 * K, 46 - bx0 * K)
    pts = [P(*c) for c in R["poly"]]
    A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + ' Z" fill="#fff" stroke="#222" stroke-width=".6"/>')
    inner = poly.buffer(-R["cove"] / 1000, join_style=2)
    A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in (P(*c) for c in inner.exterior.coords)) + ' Z" class="thin" style="stroke-dasharray:1 .6"/>')
    (cx_, cy_), (tx_, ty_) = R.get("ceil_labels", ((-4.0, 1.2), (-1.3, 1.6)))
    A(f'<text x="{P(cx_, cy_)[0]:.2f}" y="{P(cx_ - 0.08, cy_)[1]:.2f}" font-size="1.8" fill="#888">顶角线 Coving 90×60（虚线内）</text>')
    if R.get("ceil_split"):                                              # two ceiling heights: dashed split line + a label each side
        xs, lab_a, pa, lab_b, pb = R["ceil_split"]
        seg = LineString([(xs, by0 - 1), (xs, by1 + 1)]).intersection(poly)
        for g_ in getattr(seg, "geoms", [seg]):
            (ax, ay), (bx, by) = P(*g_.coords[0]), P(*g_.coords[-1])
            A(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" stroke="#6a1b9a" stroke-width=".5" stroke-dasharray="2 1"/>')
        for lab, pp in ((lab_a, pa), (lab_b, pb)):
            A(f'<text x="{P(*pp)[0]:.2f}" y="{P(*pp)[1]:.2f}" font-size="2.4" fill="#6a1b9a" font-weight="bold">{E(lab)}</text>')
    else:
        A(f'<text x="{P(tx_, ty_)[0]:.2f}" y="{P(tx_, ty_)[1]:.2f}" font-size="2.4" fill="#999">天花高 {R["ceil"]}（平顶，无梁）</text>')
    for label, (x0, y0, x1, y1) in R.get("ceil_zones", []):          # e.g. lift through the slab
        (ax, ay), (bx, by) = P(x0, y0), P(x1, y1)
        if "天窗" in label:                                               # skylight: glazed look, label inside
            A(f'<rect x="{min(ax, bx):.2f}" y="{min(ay, by):.2f}" width="{abs(bx-ax):.2f}" height="{abs(by-ay):.2f}" fill="#e3f0fa" stroke="#4f7ea8" stroke-width=".5"/>'
              f'<path d="M{min(ax,bx):.2f} {min(ay,by):.2f} L{max(ax,bx):.2f} {max(ay,by):.2f} M{max(ax,bx):.2f} {min(ay,by):.2f} L{min(ax,bx):.2f} {max(ay,by):.2f}" stroke="#4f7ea8" stroke-width=".2"/>'
              f'<text x="{(ax+bx)/2:.2f}" y="{(ay+by)/2+1:.2f}" font-size="2.6" text-anchor="middle" fill="#1f4e79" font-weight="bold" style="paint-order:stroke;stroke:#e3f0fa;stroke-width:1.2">{E(label)}</text>')
            continue
        A(f'<rect x="{min(ax, bx):.2f}" y="{min(ay, by):.2f}" width="{abs(bx-ax):.2f}" height="{abs(by-ay):.2f}" fill="#f3f3f3" stroke="#666" stroke-width=".3" stroke-dasharray="1.2 .7"/>'
          f'<text x="{(ax+bx)/2:.2f}" y="{max(ay, by)+3.2:.2f}" font-size="1.9" text-anchor="middle" fill="#555">{E(label)}</text>')
    rows = []
    for r in ceil:
        p = r["p"]; px, py = P(*p)
        if r.get("sym") == "smoke":                                      # smoke alarm (ceiling)
            A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3" fill="#fff" stroke="#c62828" stroke-width=".5"/><circle cx="{px:.2f}" cy="{py:.2f}" r="1.6" fill="none" stroke="#c62828" stroke-width=".3"/>'
              f'<text x="{px+4:.2f}" y="{py-3:.2f}" font-size="2.4" fill="#c62828" font-weight="bold">{E(r["id"])}</text>')
        else:
          A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3" fill="#fff" stroke="{COL["light"]}" stroke-width=".4"/>'
          f'<path d="M{px-2.1:.2f} {py-2.1:.2f} L{px+2.1:.2f} {py+2.1:.2f} M{px+2.1:.2f} {py-2.1:.2f} L{px-2.1:.2f} {py+2.1:.2f}" stroke="{COL["light"]}" stroke-width=".35"/>'
          f'<text x="{px+4:.2f}" y="{py-3:.2f}" font-size="2.4" fill="{COL["light"]}" font-weight="bold">{E(r["id"])}</text>')
        if R["cn"] == "次卧":
            if r["id"] == "L03":
                rad = .250 * K
                A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{rad:.2f}" fill="none" stroke="#e65100" stroke-width=".4"/>')
                A(f'<text x="{px+rad+3:.2f}" y="{py-6:.2f}" font-size="2.5" fill="#e65100">F19 吸顶灯 Ø500</text>')
                hdim(A, px-rad, px+rad, py+rad+10, "Ø500 灯体", ext=py+rad, fs=2.3)
            elif r["id"] == "L12":
                A(f'<text x="{px+5:.2f}" y="{py+6:.2f}" font-size="2.3" fill="#e65100">灯具待选；灯体尺寸待定</text>')
        # chains to the walls in both directions (inside the room polygon)
        res = {}
        for name, (dx, dy) in (("北 N", (-1, 0)), ("南 S", (1, 0)), ("西 W", (0, -1)), ("东 E", (0, 1))):
            ray = LineString([p, (p[0] + dx * 12, p[1] + dy * 12)]).intersection(poly.exterior)
            cand = [g for g in getattr(ray, "geoms", [ray]) if not g.is_empty]
            d = min(Point(p).distance(g) for g in cand)
            res[name] = d
        (nx, ny), (sx, sy) = P(p[0] - res["北 N"], p[1]), P(p[0] + res["南 S"], p[1])
        (wx, wy), (ex, ey) = P(p[0], p[1] - res["西 W"]), P(p[0], p[1] + res["东 E"])
        def dist_label(direction):
            mm = r10(res[direction] * 1000)
            return f"{direction[0]} {mm}" if R.get("ceil_short") else f"中心距{direction[0]}墙 {mm}"
        vdx = R.get("ceil_vdx", {}).get(r["id"], 0)                    # page-mm side shift: keep N-S chains of lights in one line apart
        vdim(A, px + vdx, ny, py, dist_label("北 N"), fs=R.get("ceil_fs", 2.7))
        vdim(A, px + vdx, py, sy, dist_label("南 S"), fs=R.get("ceil_fs", 2.7))
        dim_y = py + (25 if r["id"] == "L03" else -16) if R["cn"] == "次卧" else py      # Codex Rev K: keep the two E-W chains apart
        hdim(A, wx, px, dim_y, dist_label("西 W"), ext=py, fs=R.get("ceil_fs", 2.7))
        hdim(A, px, ex, dim_y, dist_label("东 E"), ext=py, fs=R.get("ceil_fs", 2.7))
        A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r=".8" fill="#e65100"/>')
        if R["cn"] == "次卧" and r["id"] == "L03":
            A(f'<text x="{px+16:.2f}" y="{py+18:.2f}" font-size="2.3" fill="#555">灯边距墙：北 {r10(res["北 N"]*1000)-250} / 南 {r10(res["南 S"]*1000)-250}</text>')
            A(f'<text x="{px+16:.2f}" y="{py+22:.2f}" font-size="2.3" fill="#555">西 {r10(res["西 W"]*1000)-250} / 东 {r10(res["东 E"]*1000)-250}（按 Ø500）</text>')
        keys = LIGHT_KEYS.get(r["id"], ("", "", ""))
        rows.append([r["id"], r["name"] + (f"（{keys[2]}）" if keys[2] else ""), keys[1], f'北 {r10(res["北 N"]*1000)} / 南 {r10(res["南 S"]*1000)}',
                     f'西 {r10(res["西 W"]*1000)} / 东 {r10(res["东 E"]*1000)}', keys[0], "天花线盒中心；吸顶 / 吊灯按灯具定" if "待选" not in r["name"] else "只定线盒位置，灯具待选"])
    table(s, 14, 218, [("编号", 11), ("灯 Light", 50), ("回路", 10), ("南北向 mm", 26), ("东西向 mm", 26), ("开关 Switch", 30)], [r[:6] for r in rows], fs=2.0,
          title="天花点位 Ceiling points（尺寸到完成墙面）")
    A(f'<text x="14" y="{252 if len(rows) <= 8 else 218 + 3.5 * (len(rows) + 2) + 3:.1f}" font-size="2.1" fill="#444">反射天花平面：方向与平面图相同（从上往下看）。尺寸量到灯位（线盒）中心，墙面为完成面（不含顶角线）。</text>')
    if R["cn"] == "次卧":
        A('<text x="14" y="258" font-size="2.3" fill="#444">灯具尺寸：L03 / F19 吸顶灯 Ø500（产品清单 D50）；L12 灯具待选，外形 / 安装尺寸待定。定位尺寸均到灯中心。</text>')
    keyplan(s, R, ceiling=True)
    s.frame()
    return s


def build_room(key):
    R = ROOMS[key]
    load_meta(R["F"])
    wall, ceil = room_points(R)
    floor = "2" if R["F"] == "FF" else "1"
    n0 = R["sheet0"]
    num = lambda i: f"W{floor}-{n0:02d}-{i}"
    R["_ceil_sheet"] = num(1); R["_index_sheet"] = num(0)
    groups, cur, wsum = [], [], 0.0
    for f in dfaces(R):
        # owner 2026-10-08: every wall gets an elevation (walls without points show their doors / windows for checking)
        w = flen(R, f[0]) * 50 + 40
        if cur and (wsum + w > 370 or f[0] in R.get("own_sheet", ()) or cur[-1] in R.get("own_sheet", ())): groups.append(cur); cur, wsum = [], 0.0
        cur.append(f[0]); wsum += w
    if cur: groups.append(cur)
    first = 1 if R.get("no_ceiling") else 2                                 # outdoor spaces: no ceiling sheet
    R["_sheetmap"] = [(num(i + first), tuple(ks)) for i, ks in enumerate(groups)]
    out = [index_sheet(R, num(0), wall, ceil)] + ([] if R.get("no_ceiling") else [ceiling_sheet(R, num(1), ceil)])
    for number, ks in R["_sheetmap"]: out.append(elev_sheet(R, ks, number, wall))
    return out


# ---------------- suites: several rooms laid out as ONE space (owner 2026-10-08: 主卧 + 主卫 + 衣帽间) ----------------
def suite_frame(Rs, wmax=150.0, hmax=165.0, x0=22.0, y0=40.0):
    from shapely.ops import unary_union
    allp = unary_union([Polygon(R["poly"]) for R in Rs]); bx0, by0, bx1, by1 = allp.bounds
    K = next(k for k in (50.0, 40.0, 1000 / 30.0, 25.0, 20.0, 1000 / 60.0) if (by1 - by0) * k <= wmax and (bx1 - bx0) * k <= hmax)
    return K, (lambda x, y: (x0 + (y - by0) * K, y0 + (x - bx0) * K)), allp


def suite_index_sheet(Rs, number, data, title):
    R0 = Rs[0]
    K, P, allp = suite_frame(Rs)
    s = sheet(dict(R0, cn=title, suite_cn=""), number, "平面布置（带家具 / 洁具）+ 墙面索引 Furnished plan & key", f"1:{round(1000/K)}")
    A = s.add
    bx0, by0, bx1, by1 = allp.bounds
    g = revised_walls(R0).intersection(box(bx0 - .4, by0 - .4, bx1 + .4, by1 + .4))
    for G in getattr(g, "geoms", [g]):
        if G.is_empty or G.geom_type != "Polygon": continue
        d = "".join("M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in (P(*c) for c in ring.coords)) + " Z " for ring in [G.exterior] + list(G.interiors))
        A(f'<path d="{d}" class="b-wall" style="fill-rule:evenodd"/>')
    s.defs.append('<marker id="ar" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto"><path d="M0 0 L4 2 L0 4 Z" fill="#c62828"/></marker>')
    rows = []
    for R in Rs:
        wall, ceil = data[R["cn"]]; poly = Polygon(R["poly"])
        A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in (P(*c) for c in R["poly"])) + ' Z" fill="#fffdf6" stroke="#222" stroke-width=".4"/>')
        c = poly.representative_point().coords[0]
        for kind, nm, a, b, sill, head in R["openings"]:
            (ax, ay), (bx, by) = P(*a), P(*b)
            A(f'<line x1="{ax:.2f}" y1="{ay:.2f}" x2="{bx:.2f}" y2="{by:.2f}" stroke="{"#4f7ea8" if kind == "window" else "#fffdf6"}" stroke-width="{2.0 if kind == "window" else 1.4}"/>')
        for h, cc, o in R["swings"]:
            (hx, hy), (cx, cy), (oxx, oyy) = P(*h), P(*cc), P(*o); rr = math.dist((hx, hy), (cx, cy))
            sweep = 1 if (cx - hx) * (oyy - hy) - (cy - hy) * (oxx - hx) > 0 else 0
            A(f'<path d="M{oxx:.2f} {oyy:.2f} L{hx:.2f} {hy:.2f} M{cx:.2f} {cy:.2f} A{rr:.2f} {rr:.2f} 0 0 {sweep} {oxx:.2f} {oyy:.2f}" fill="none" stroke="#8d6e3f" stroke-width=".25"/>')
        for label, (x0, y0, z0, x1, y1, z1) in R["furniture"]:
            (a, b), (cx, cy) = P(x0, y0), P(x1, y1)
            A(f'<rect x="{min(a,cx):.2f}" y="{min(b,cy):.2f}" width="{abs(cx-a):.2f}" height="{abs(cy-b):.2f}" fill="#efe9dc" stroke="#8a7a5c" stroke-width=".25"/>'
              f'<text x="{(a+cx)/2:.2f}" y="{(b+cy)/2-0.2:.2f}" font-size="1.5" text-anchor="middle" fill="#5d4e33">{E(label.split("（")[0])}</text>'
              f'<text x="{(a+cx)/2:.2f}" y="{(b+cy)/2+1.8:.2f}" font-size="1.3" text-anchor="middle" fill="#7d6e53">{r10((y1-y0)*1000)}×{r10((x1-x0)*1000)} h{r10((z1-R["fz"])*1000)}</text>')
        q = P(*c)
        A(f'<text x="{q[0]:.2f}" y="{q[1]+1:.2f}" font-size="3.4" text-anchor="middle" fill="#bbb" font-weight="bold">{E(R["cn"])}</text>')
        rb = poly.bounds; off = min(0.42, 0.22 * min(rb[2] - rb[0], rb[3] - rb[1]))
        for k, nm, desc, L, Rr, ends in dfaces(R):
            n = inward(L, Rr, poly); mid = ((L[0] + Rr[0]) / 2, (L[1] + Rr[1]) / 2)
            (qx, qy), (tx, ty) = P(mid[0] + n[0] * off, mid[1] + n[1] * off), P(mid[0] + n[0] * 0.08, mid[1] + n[1] * 0.08)
            A(f'<line x1="{qx:.2f}" y1="{qy:.2f}" x2="{tx:.2f}" y2="{ty:.2f}" stroke="#c62828" stroke-width=".35" marker-end="url(#ar)"/>'
              f'<circle cx="{qx:.2f}" cy="{qy:.2f}" r="2.1" fill="#fff" stroke="#c62828" stroke-width=".35"/><text x="{qx:.2f}" y="{qy+0.9:.2f}" font-size="2.5" text-anchor="middle" fill="#c62828" font-weight="bold">{k}</text>')
        for k, rs in wall.items():
            _, _, _, L, Rr, _ = next(f for f in R["faces"] if f[0] == k); run, u = face_frame(L, Rr); n = inward(L, Rr, poly)
            for r in rs:
                pp = (L[0] + u[0] * r["_s"] + n[0] * 0.05, L[1] + u[1] * r["_s"] + n[1] * 0.05); px, py = P(*pp)
                A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r=".8" fill="{COL[pt_cat(r)]}"/>')
                lp = P(pp[0] + n[0] * 0.16, pp[1] + n[1] * 0.16)
                A(f'<text x="{lp[0]:.2f}" y="{lp[1]+0.6:.2f}" font-size="1.6" text-anchor="middle" fill="{COL[pt_cat(r)]}" font-weight="bold">{E(r["id"])}</text>')
        for r in ceil:
            px, py = P(*r["p"])
            A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.3" fill="#fff" stroke="{COL["light"]}" stroke-width=".3" stroke-dasharray=".7 .4"/>'
              f'<text x="{px+2:.2f}" y="{py+0.6:.2f}" font-size="1.5" fill="{COL["light"]}">{E(r["id"])}</text>')
        sheets = {k: num for num, ks in R["_sheetmap"] for k in ks}
        for k, nm, desc, L, Rr, ends in dfaces(R):
            ids = " ".join(r["id"] for r in sorted(unfold_pts(R, wall, k), key=lambda r: r["_s"])) or "—"
            rows.append([k, R["cn"], f"{nm} · {desc.split(' ')[0]}", round(flen(R, k) * 1000), ids, sheets.get(k, "")])
    rows.append(["天花", "全部", "Ceiling（反射平面）高 " + " / ".join(sorted({str(R["ceil"]) for R in Rs})), "", " ".join(r["id"] for R in Rs for r in data[R["cn"]][1]), R0["_ceil_sheet"]])
    table(s, 186, 34, [("面", 9), ("空间", 20), ("墙 Wall", 70), ("净长", 12), ("点位", 50), ("立面图号", 22)], rows, fs=1.9,
          title="墙面索引 Wall index（字母 = 立面编号，红箭头指向被看的墙）")
    y = 150; lx = 186
    A(f'<text x="{lx}" y="{y}" font-size="2.4" font-weight="bold">图例 Legend</text>')
    for i, (cat, t_) in enumerate([("socket", "插座"), ("switch", "开关"), ("new", "出线面板（新增）"), ("light", "天花灯（见天花图）")]):
        xx = lx + i * 34
        A(f'<circle cx="{xx+2:.2f}" cy="{y+4.2:.2f}" r="{1.3 if cat == "light" else .9}" fill="{"#fff" if cat == "light" else COL[cat]}" stroke="{COL[cat]}" stroke-width=".3"/>'
          f'<text x="{xx+5}" y="{y+5:.1f}" font-size="2">{E(t_)}</text>')
    A('<g transform="translate(372,180)"><line x1="-10" y1="0" x2="10" y2="0" stroke="#222" stroke-width=".3" marker-end="url(#ar)"/>'
      '<text x="-11" y="1" font-size="2" text-anchor="end">西 Front</text><text x="12" y="1" font-size="2">东 Rear</text>'
      '<line x1="0" y1="7" x2="0" y2="-7" stroke="#222" stroke-width=".3" marker-end="url(#ar)"/><text x="0" y="-9" font-size="2" text-anchor="middle">北 North</text></g>')
    base = NOTES if Rs[0]["F"] == "FF" else [n.replace("（二层前部 FFL = 结构 3.208）", "（一层 FFL = 0）") for n in NOTES]
    notes = base + [f"{5 + i}." + R.get("notes5", "").split(".", 1)[-1] for i, R in enumerate(Rs) if R.get("notes5")]
    s.frame(notes)
    return s


def _ceil_rooms(A, Rs, P, data, rows=None, clip=None, fs=1.9, label=True):
    """reflected ceiling of the rooms Rs with page mapping P; rows: table rows to fill; clip: (x0, y0, x1, y1) window (enlarged detail)"""
    cb = box(*clip) if clip else None
    for R in Rs:
        poly = Polygon(R["poly"]); _, ceil = data[R["cn"]]
        shown = poly.intersection(cb) if cb is not None else poly
        if shown.is_empty: continue
        for g_ in getattr(shown, "geoms", [shown]):
            if g_.geom_type != "Polygon": continue
            A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in (P(*c) for c in g_.exterior.coords)) + ' Z" fill="#fff" stroke="#222" stroke-width=".5"/>')
        inner = poly.buffer(-R["cove"] / 1000, join_style=2)
        if cb is not None: inner = inner.intersection(cb)
        for g_ in getattr(inner, "geoms", [inner]):
            if g_.geom_type == "Polygon":
                A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in (P(*c) for c in g_.exterior.coords)) + ' Z" class="thin" style="stroke-dasharray:1 .6"/>')
        if label and cb is None:
            rb = poly.bounds; q = P(rb[2] - 0.17, rb[1] + 0.15)              # bottom-left corner inside the room: clear of the light dims
            A(f'<text x="{q[0]:.2f}" y="{q[1]:.2f}" font-size="2.4" fill="#aaa" font-weight="bold">{E(R["cn"])} · 天花 {R["ceil"]}</text>')
        obst = [poly.exterior]
        for lab, (x0, y0, x1, y1), door in R.get("ceil_walls", []):        # partitions inside the space: drawn bold, dims stop at them
            bx_ = box(x0, y0, x1, y1); obst.append(bx_.exterior)
            (ax, ay), (bx, by) = P(x0, y0), P(x1, y1)
            st = 'fill="#fff" stroke="#c62828" stroke-width=".35" stroke-dasharray="1 .5"' if door else 'fill="#9e9e9e" stroke="#222" stroke-width=".4"'
            A(f'<rect x="{min(ax,bx):.2f}" y="{min(ay,by):.2f}" width="{abs(bx-ax):.2f}" height="{abs(by-ay):.2f}" {st}/>')
            if lab and cb is not None:                                       # label along the partition (vertical on the page)
                tx_, ty_ = (ax + bx) / 2 + 0.8, (ay + by) / 2
                A(f'<text x="{tx_:.2f}" y="{ty_:.2f}" font-size="{fs:.1f}" text-anchor="middle" fill="#c62828" font-weight="bold" transform="rotate(-90 {tx_:.2f} {ty_:.2f})" style="paint-order:stroke;stroke:#fff;stroke-width:.8">{E(lab)}</text>')
        from shapely.ops import unary_union
        obst = unary_union(obst)
        for r in ceil:
            p = r["p"]
            if cb is not None and not cb.contains(Point(p)): continue
            px, py = P(*p)
            A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="2.4" fill="#fff" stroke="{COL["light"]}" stroke-width=".4"/>'
              f'<path d="M{px-1.7:.2f} {py-1.7:.2f} L{px+1.7:.2f} {py+1.7:.2f} M{px+1.7:.2f} {py-1.7:.2f} L{px-1.7:.2f} {py+1.7:.2f}" stroke="{COL["light"]}" stroke-width=".35"/>'
              f'<text x="{px+3:.2f}" y="{py-2.6:.2f}" font-size="{fs+0.3:.1f}" fill="{COL["light"]}" font-weight="bold">{E(r["id"])}</text>')
            res = {}
            for name, (dx, dy) in (("北 N", (-1, 0)), ("南 S", (1, 0)), ("西 W", (0, -1)), ("东 E", (0, 1))):
                ray = LineString([p, (p[0] + dx * 12, p[1] + dy * 12)]).intersection(obst)
                res[name] = min(Point(p).distance(g_) for g_ in getattr(ray, "geoms", [ray]) if not g_.is_empty)
            ends = {"北 N": (p[0] - res["北 N"], p[1]), "南 S": (p[0] + res["南 S"], p[1]), "西 W": (p[0], p[1] - res["西 W"]), "东 E": (p[0], p[1] + res["东 E"])}
            ok = lambda k_: cb is None or cb.buffer(0.02).contains(Point(ends[k_]))
            if ok("北 N"): vdim(A, px, P(*ends["北 N"])[1], py, r10(res["北 N"] * 1000), fs=fs)
            if ok("南 S"): vdim(A, px, py, P(*ends["南 S"])[1], r10(res["南 S"] * 1000), fs=fs)
            if ok("西 W"): hdim(A, P(*ends["西 W"])[0], px, py, r10(res["西 W"] * 1000), fs=fs)
            if ok("东 E"): hdim(A, px, P(*ends["东 E"])[0], py, r10(res["东 E"] * 1000), fs=fs)
            if rows is not None:
                keys = LIGHT_KEYS.get(r["id"], ("", "", ""))
                rows.append([r["id"], R["cn"], r["name"] + (f"（{keys[2]}）" if keys[2] and r["id"] not in R.get("ceil_name", {}) else ""), keys[1], f'北 {r10(res["北 N"]*1000)} / 南 {r10(res["南 S"]*1000)}',
                             f'西 {r10(res["西 W"]*1000)} / 东 {r10(res["东 E"]*1000)}', keys[0]])


def suite_ceiling_sheet(Rs, number, data, title):
    R0 = Rs[0]
    K, P, allp = suite_frame(Rs)
    s = sheet(dict(R0, cn=title, suite_cn=""), number, "天花 Reflected ceiling plan", f"1:{round(1000/K)}")
    A = s.add
    rows = []
    _ceil_rooms(A, Rs, P, data, rows)
    for lab, clip, K2, (gx, gy), *more in R0.get("ceil_detail", []):   # enlarged detail of a tight spot (e.g. the entrance)
        x0, y0, x1, y1 = clip
        P2 = lambda x, y, _x0=x0, _y0=y0: (gx + (y - _y0) * K2, gy + 6 + (x - _x0) * K2)
        A(f'<text x="{gx:.1f}" y="{gy+2:.1f}" font-size="2.8" font-weight="bold">{E(lab)}</text>')
        w2 = revised_walls(R0).intersection(box(*clip))
        for g_ in getattr(w2, "geoms", [w2]):
            if g_.geom_type == "Polygon":
                A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in (P2(*c) for c in g_.exterior.coords)) + ' Z" fill="#d6d6d6" stroke="#888" stroke-width=".15"/>')
        _ceil_rooms(A, Rs, P2, data, None, clip=clip, fs=2.3)
        for t_, (lx, ly) in (more[0] if more else []):
            q_ = P2(lx, ly); A(f'<text x="{q_[0]:.2f}" y="{q_[1]:.2f}" font-size="2.6" fill="#999" font-weight="bold">{E(t_)}</text>')
    table(s, 186, 34, [("编号", 10), ("空间", 16), ("灯 Light", 58), ("回路", 10), ("南北向 mm", 26), ("东西向 mm", 26), ("开关", 32)], rows, fs=1.9,
          title="天花点位 Ceiling points（尺寸到本空间完成墙面，量到灯位中心）")
    keyplan(s, dict(R0, suite_cn=title), ceiling=True)                 # small key plan bottom-right, as on the other sheets
    A(f'<text x="186" y="{100 if len(rows) <= 14 else 34 + 3.9 * (len(rows) + 2) + 6:.0f}" font-size="2.1" fill="#444">反射天花平面：方向与平面图相同（从上往下看）；天花 {E("，".join(R["cn"] + " " + str(R["ceil"]) + R.get("ceil_extra", "") for R in Rs))}，{"其余" if any(R.get("ceil_extra") for R in Rs) else ""}平顶无梁；虚线 = 顶角线 90。</text>')
    s.frame()
    return s


def build_suite(keys, n0, title):
    Rs = [ROOMS[k] for k in keys]
    load_meta(Rs[0]["F"])
    floor = "2" if Rs[0]["F"] == "FF" else "1"
    num = lambda i: f"W{floor}-{n0:02d}-{i}"
    data = {}
    for R in Rs:
        R["_suite"] = Rs; R["suite_cn"] = title
        data[R["cn"]] = room_points(R)
        R["_index_sheet"], R["_ceil_sheet"] = num(0), num(1)
    i = 2
    for R in Rs:
        groups, cur, wsum = [], [], 0.0
        for f in dfaces(R):
            w = flen(R, f[0]) * 50 + 40
            if cur and wsum + w > 370: groups.append(cur); cur, wsum = [], 0.0
            cur.append(f[0]); wsum += w
        if cur: groups.append(cur)
        R["_sheetmap"] = [(num(i + j), tuple(ks)) for j, ks in enumerate(groups)]; i += len(groups)
    out = [suite_index_sheet(Rs, num(0), data, title), suite_ceiling_sheet(Rs, num(1), data, title)]
    for R in Rs:
        for number, ks in R["_sheetmap"]: out.append(elev_sheet(R, ks, number, data[R["cn"]][0]))
    return out


# 主客厅区 Rev E (owner 2026-10-09): entrance is tight at 1:60 -> mark the partitions clearly on the ceiling plan (front door line, inner
# door F26 partition with its 762 door; dims stop at them) and add an enlarged 1:25 detail of porch + vestibule on the ceiling sheet.
for _k in ("GF_主客厅", "GF_门厅楼梯", "GF_餐厅", "GF_门廊"): ROOMS[_k]["rev"] = dict(rev="E")
ROOMS["GF_门厅楼梯"]["ceil_walls"] = [("", (3.215, 1.775, 3.321, 1.893), False), ("", (4.081, 1.775, 4.290, 1.893), False),
                                      ("内门隔断 · 内门 F26（门 762）", (3.321, 1.775, 4.081, 1.893), True),
                                      ("前门（门扇 + 上亮）", (3.249, 0.311, 4.276, 0.371), True)]
ROOMS["GF_主客厅"]["ceil_detail"] = [("门口放大 Entrance detail 1:25（门廊 → 前门 → 门厅 → 内门隔断 → 鞋帽间）", (3.05, -0.20, 4.45, 3.10), 40.0, (25.0, 150.0),
                                    [("门廊", (4.20, -0.02)), ("门厅", (4.18, 0.55)), ("鞋帽间", (4.18, 2.05))])]
ROOMS["GF_门厅楼梯"]["notes5"] += " Rev E：天花图上标明前门线和内门 F26 隔断（红虚线 = 门洞），灯位尺寸量到隔断；天花图左下另附门口放大 1:25。"

# 主客厅区 Rev F (owner 2026-10-09): 3x3 GU10 grid in 主客厅 150 further south; C07 / C33 same height (h1110, above cabinet G02) and
# symmetric about the bay (257 from each bay return); S1 (4-gang) to B, centred on the pier right of the hall door; TV wall: new cabinet
# G21 2400 x 350 x 450 -> 4 twin sockets in a tight block (100 clear between plates) on the cabinet centre: 2 at h1100, 2 at h350.
LV = ROOMS["GF_主客厅"]
for _k in ("GF_主客厅", "GF_门厅楼梯", "GF_餐厅", "GF_门廊"): ROOMS[_k]["rev"] = dict(rev="F")
LV["ceil_move"] = {k_: (x_ + 0.150, y_) for k_, (x_, y_) in {
    "L03": (1.164, 2.069), "L11": (2.219, 3.287), "L12": (2.219, 2.057), "L13": (2.219, 0.821), "L14": (1.196, 0.834),
    "L15": (0.102, 2.070), "L16": (0.102, 3.300), "L17": (1.176, 3.301), "L18": (0.102, 0.834)}.items()}
LV["furniture"] = [("电视柜 G21（2400×350×450，柜脚离地 160）", [2.651, 1.664, 0.002, 3.001, 4.064, 0.452]) if f[0].startswith("电视柜") else f for f in LV["furniture"]]
_tv = 4.234 - 2.864                                                    # cabinet centre on B (from B's left end)
LV["override"].update({
    "C07": ("A1", 0.745 - 0.488, "与 C33 同高对称（各离凸窗回墙 257，业主 2026-10-09），h1110", 1110),
    "C33": ("A9", 0.515 - 0.257, "与 C07 同高对称（各离凸窗回墙 257），h1110，在柜 G02 台面上方", 1110),
    "S1":  ("B", 0.165, "4 联开关：B 墙门洞右侧 330 宽墙垛正中（业主 2026-10-09），h1200"),
    "C04": ("B", 4.165 - (_tv - 0.123), "电视墙插座组（4 个双联，面板净距 100）：左上，h1100（业主 2026-10-09）", 1100),
    "C31": ("B", 4.165 - (_tv + 0.123), "电视墙插座组：右上，h1100", 1100),
    "C32": ("B", 4.165 - (_tv - 0.123), "电视墙插座组：左下，h350（在电视柜后面，柜高 450）", 350),
})
LV["extra_pts"] = LV.get("extra_pts", []) + [("B", "C35", "双联插座 Twin socket（新增）", round((_tv + 0.123) * 1000), 350, "电视墙插座组：右下，h350（在电视柜后面）；新增（业主 2026-10-09）", "WX1", "socket", "double")]
LV["notes5"] += " Rev F：3×3 筒灯阵列整体往南 150；C07 / C33 同高 1110、对称；S1 挪到 B 墙门洞右侧墙垛正中；电视柜按 2400×350×450，电视墙 4 个双联插座成组（净距 100）：上两个 h1100、下两个 h350（C35 新增）。"

# 主客厅区 Rev G (owner 2026-10-09):
# 主客厅: D + E are ONE plane (no 55 step) -> one face D; sofa back shelf assumed 2 x 1500 platforms -> C17 / C05 each centred on one;
#         A: C07 / C33 at h450.
# 餐厅: I runs on across the arch (reverse of 主客厅 C) -> S4 / S5 / C02 200 from the arch edge, wall light L01 higher (h2100);
#       J: under-stair door count / size TBC + a second small door; rear wall K + L are ONE plane (no 35 step) -> one face K, the old M
#       becomes L; S7 150 from the French door; C15 800 from hidden door V15.  门厅: S6 placed by the stair foot + note box.
for _k in ("GF_主客厅", "GF_门厅楼梯", "GF_餐厅", "GF_门廊"): ROOMS[_k]["rev"] = dict(rev="G")
LV["poly"] = [(-0.655, 0.069), (-0.085, 0.069), (-0.085, -0.046), (0.059, -0.046), (0.592, -0.441), (1.621, -0.441), (2.148, -0.046),
              (2.344, -0.046), (2.344, 0.069), (3.089, 0.069), (3.089, 4.234), (-0.655, 4.234)]
LV["faces"] = [(f[0], f[1], f[2], f[3], (-0.655, 0.069), f[5]) if f[0] == "A9" else f for f in LV["faces"] if f[0] != "E"]
LV["faces"] = [("D", "北墙", "沙发墙（装饰线板，与原前段同一平面）Sofa wall", (-0.655, 0.069), (-0.655, 4.234), ("墙角", "墙角")) if f[0] == "D" else f for f in LV["faces"]]
WALL_EDITS.setdefault("GF", []).extend([("sub", (-0.655, 0.069, -0.600, 0.844)), ("add", (-0.609, 7.864, 1.155, 7.899))])
LV["furniture"] = LV["furniture"] + [("沙发背架（预估，平台 1）1500", [-0.655, 1.234, 0.002, -0.455, 2.734, 0.900]),
                                     ("沙发背架（预估，平台 2）1500", [-0.655, 2.734, 0.002, -0.455, 4.234, 0.900])]
LV["override"].update({
    "C07": ("A1", 0.745 - 0.488, "与 C33 同高对称（各离凸窗回墙 257），h450（业主 2026-10-09）", 450),
    "C33": ("A9", 0.570 - 0.257, "与 C07 同高对称（各离凸窗回墙 257），h450（业主 2026-10-09；在柜 G02 后面）", 450),
    "C17": ("D", 4.165 - (1.984 - 0.069), "沙发背架平台 1（预估 1500）正中，h450（业主 2026-10-09）", 450),
    "C05": ("D", 4.165 - (3.484 - 0.069), "沙发背架平台 2（预估 1500）正中，h450（业主 2026-10-09）", 450),
})
DN = ROOMS["GF_餐厅"]
DN["poly"] = [(-0.655, 4.234), (2.224, 4.234), (2.224, 4.354), (3.215, 4.354), (3.215, 5.069), (3.322, 5.069), (3.322, 7.864),
              (-0.609, 7.864), (-0.609, 4.354), (-0.655, 4.354)]
_df = {f[0]: f for f in DN["faces"]}
DN["faces"] = [("I", "西墙", "拱门墙（含拱门，主客厅 C 墙背面）Arch wall", (3.215, 4.354), (-0.609, 4.354), ("墙端（楼梯口）", "墙角")),
               _df["J"],
               ("K", "东墙", "后墙 · 法式门 + 通厨房门（同一平面）Rear wall", (-0.609, 7.864), (3.322, 7.864), ("墙角", "墙角")),
               ("L", "北墙", "吸音墙 / 暗门 Acoustic wall & hidden door", (-0.609, 4.354), (-0.609, 7.864), ("墙端（拱门旁）", "墙角"))]
DN["openings"] = [("door", o[1], (-0.38, 7.864), (0.83, 7.864), o[4], o[5]) if o[1].startswith("法式门") else
                  (("door", "楼梯下检修门（内有配电箱）· 门洞数量 / 尺寸待定", o[2], o[3], o[4], o[5]) if o[1].startswith("楼梯下检修门") else o)
                  for o in DN["openings"]]
DN["openings"] += [("door", "楼梯下小门（新增，尺寸待定）", (3.322, 6.719), (3.322, 6.269), 0, 900),
                   ("door", "拱门（通主客厅）", (2.178, 4.354), (-0.372, 4.354), 0, 2040)]
DN["features"] = DN.get("features", []) + [
    ("J", "注：楼梯下门洞数量 / 尺寸待定；|现画检修门（配电箱）+ 旁边小门各一，|按楼梯下净高现场定。", 150, 1500, 1500, 1900, "note")]
_arch = 3.215 - 2.178                                                    # arch edge on I, from I's left end
DN["override"].update({
    "S4":  ("I", 3.824 - (_arch - 0.200), "中心离拱门边 200（业主 2026-10-09），h1200"),
    "S5":  ("I", 3.824 - (_arch - 0.200), "S4 正上方，中心离拱门边 200，h1330"),
    "C02": ("I", 3.824 - (_arch - 0.200), "中心离拱门边 200（业主 2026-10-09），h450"),
    "L01": ("I", 3.824 - 0.4865, "壁灯：位置不变，加高到 h2100（业主 2026-10-09；原 1930）", 2100),
    "S7":  ("K", 3.931 - (0.83 + 0.150 + 0.609), "中心离法式门洞边 150（业主 2026-10-09），h1200"),
    "C15": ("L", 3.510 - (0.768 + 0.800), "中心离暗门 V15 洞边 800（业主 2026-10-09），h450"),
})
DN["drop"] = set(DN.get("drop", set())) | {"C05", "S3"}          # 主客厅 points near the arch: keep them out of the 餐厅 I wall
DN["notes5"] += (" Rev G：I 墙画到拱门（含拱门），S4 / S5 / C02 离拱门边 200，壁灯 L01 加高到 2100；后墙 K（原 K + L，同一平面不错落）；"
                 "原 M 改为 L；S7 离法式门 150；C15 离暗门 800；J 楼梯下门洞数量待定，旁加小门。")
HS = ROOMS["GF_门厅楼梯"]
HS["override"]["S6"] = ("H", 7.043 - (7.414 - (5.069 - 0.300)), "楼梯三控开关（K 键）：楼梯第一级前约 300（业主 2026-10-09：按楼梯位置定），h1200")
HS["features"] = HS.get("features", []) + [("H", "注：S6 按楼梯位置定 —— 第一级踏步前约 300，|上楼前顺手；楼梯起步位置以楼梯图 / 现场为准。", 2050, 3600, 1550, 1900, "note")]
LV["notes5"] += " Rev G：D 墙与原 E 段同一平面（不错落），合为 D；沙发背架预估 2 × 1500 平台，C17 / C05 各在一个平台正中（h450）；A 墙 C07 / C33 改 h450。"

# ---------------- 前门凹位 Rev B (owner 2026-10-09): EV charger reserved on the north side wall A, not beside the door on B
FR = ROOMS["GF_前门凹位"]
FR["rev"] = dict(rev="B")
FR["faces"] = [("A", "北侧", "凹位北侧墙（洗车龙头 + 充电桩预留）North side", *FR["faces"][0][3:]),
               ("B", "东墙", "副客厅前门外墙 Wall with side-lounge door", *FR["faces"][1][3:]), FR["faces"][2]]
FR["extra_pts"] = [("A", "EV", "EV 充电桩预留 Charger（D07）", 165, 1050, "预留位（业主 2026-10-09）：由 B 墙门边挪到北侧墙正中（墙宽 330），中心离地约 1050；电源 WP5 专线；室内隔离开关 D08 原定在副客厅墙内 —— 跟着挪位后请电工核对穿线路径；充电桩型号 / 安装支架按产品", "WP5")]
FR["notes5"] = FR["notes5"].replace("B 墙：副客厅前门 + EV 充电桩（D07，专线 WP5）；A 墙：洗车龙头 FT；",
                                    "B 墙：副客厅前门；A 墙：洗车龙头 FT + EV 充电桩预留（D07，专线 WP5，Rev B 由 B 墙挪来，业主 2026-10-09）；")

# ---------------- 后院 Rev B (owner 2026-10-09): B-wall lights up to h2000; L10 centred between the laundry window and the kitchen window
BK = ROOMS["GF_早餐区"]
BK["rev"] = dict(rev="B")
BK["room_note"]["C06"] = "⚠ 位置 / 高度待定：按热水器（西北角柜 G23 / G24）实际安装位置相应调整高度和左右位置（业主 2026-10-09），图上为暂定位"
BK["override"]["S12"] = ("B", (11.824 - 8.164) - (10.314 - 8.164 + 0.150), "中心离法式门洞边 150（业主 2026-10-09；原 50），h1200")
BK["features"] = BK.get("features", []) + [("A", "注：C06 为暂定位 ——|按热水器实际安装位置，|相应调整高度和左右位置。", 1880, 3000, 650, 1050, "note")]
BK["notes5"] += " Rev B：S12 离法式门洞边 150；C06 按热水器位置调整（待定）。"

# ---------------- 厨房区 Rev B (owner 2026-10-09): kitchen units per the Wren order (Charter Pack S8097782/1, 16 Aug 2026) and
# sockets set out from those units.  Wren plan, mapped to the model: cooker wall run 12.104-14.714 (2610 = 1948 units + 92 void
# + 570 corner) matches the model exactly; Wall C units run from the pier (y 11.824): filler 36, dishwasher 600, corner 893;
# peninsula worktop A 1821 x 824 next to worktop C (909); wall A: fridge 850 at 875 from the window wall, corner units 1018.
# Heights: worktop 900, wall units 1409-2129 (pelmet to 1354), hood housing 1554-2129.
KT = ROOMS["GF_厨房"]
KT["rev"] = BK["rev"] = dict(rev="B")
_WREN = "按 Wren 橱柜图（S8097782/1）"
BK["furniture"] = [f for f in BK["furniture"] if not f[0].startswith(("半岛台", "台面 + 洗碗机", "吊柜"))] + [
    ("台面 C + 洗碗机 Bosch（离墙垛 36–636）", [3.688, 10.915, 0.0, 4.290, 11.824, 0.900]),
    ("半岛台 A 1821×824（水槽）", [2.469, 10.091, 0.0, 4.290, 10.915, 0.900]),
    ("吊柜（Wren 21 / 22 / 23）", [3.960, 10.550, 1.409, 4.290, 11.824, 2.129])]
KT["furniture"] = [
    ("台面 B 2008 + 地柜（灶 860 中心离墙垛 1048）", [3.688, 12.104, 0.0, 4.290, 14.112, 0.900]),
    ("烤箱 AEG 600", [3.720, 12.852, 0.150, 4.290, 13.452, 0.800]),
    ("烟机柜 1000（Wren 18）", [3.960, 12.652, 1.554, 4.290, 13.652, 2.129]),
    ("吊柜", [3.960, 13.652, 1.409, 4.290, 14.112, 2.129]), ("吊柜", [3.960, 12.104, 1.409, 4.290, 12.652, 2.129]),
    ("转角台面 D 1270 + 地柜", [3.020, 14.112, 0.0, 4.290, 14.714, 0.900]),
    ("转角吊柜（Wren 14 / 24 / 25）", [3.020, 14.384, 1.409, 4.290, 14.714, 2.129]),
    ("冰箱 850（美式，高 1800）", [2.145, 14.014, 0.0, 2.995, 14.714, 1.800])]
# D (breakfast south wall, s from the pier): C09 centred on worktop C, C23 centred on the peninsula where it meets the wall
BK["override"]["C09"] = ("D", 3.660 - 0.455, "台面 C（909）正中，h1100；下面是洗碗机；" + _WREN)
BK["override"]["C23"] = ("D", 3.660 - 1.321, "半岛台 A 靠墙一端正中（824 宽），h1100；" + _WREN)
BK["extra_pts"] = BK.get("extra_pts", []) + [
    ("D", "FD", "洗碗机开关 FCU（带开关熔断接线盒 13A）", 750, 1100, "控制洗碗机插座 C38；台面上方，在 C09 与半岛台之间；" + _WREN, "WX3"),
    ("D", "C38", "洗碗机插座 Single socket（在角柜内）", 1080, 300, "在洗碗机旁转角柜（Wren 7）后面，由 FD 控制；洗碗机 Bosch 集成 600 位于离墙垛 36–636；" + _WREN, "WX3", "socket", "single")]
# F (kitchen east wall, s from the window wall): fridge 875-1725, corner units 1760-2778, worktop D 1750-3020
KT["override"]["C25"] = ("F", 3.020 - 1.300, "冰箱插座：冰箱（850，离窗墙 875–1725）后面正中，h450；" + _WREN)
KT["override"]["C24"] = ("F", 3.020 - 1.950, "转角台面 D 上，离冰箱边约 225，h1100；" + _WREN)
KT["override"]["C10"] = ("F", 3.020 - 2.550, "转角台面 D 上，h1100（转角里面 242 为空腔，不放插座）；" + _WREN)
# G (cooker wall, s from the F corner): units 2 662-1262, oven 1262-1862, unit 3 1862-2562; hob 860 centred on the oven (1132-1992)
KT["extra_pts"] = KT.get("extra_pts", []) + [
    ("G", "C36", "双联插座 Twin socket", 800, 1100, "台面 B 上，灶左边，离灶边 332（≥ 300）；" + _WREN, "WX3", "socket", "double"),
    ("G", "C37", "双联插座 Twin socket", 2350, 1100, "台面 B 上，灶右边，离灶边 358（≥ 300），离墙垛 260；" + _WREN, "WX3", "socket", "double"),
    ("G", "C39", "烤箱 / 灶点火 插座（双联，在抽屉柜后）", 2212, 300, "在烤箱旁 700 抽屉柜（Wren 3）后面；烤箱 AEG BPX535061M、灶 AEG HKB95820NB 点火电源，由 H 墙 FO 控制；烤箱按说明书确认 13A 插头或接独立 cooker 回路（电工定）", "待定", "socket", "double"),
    ("G", "C40", "烟机插座 Single socket（在烟机柜内）", 1562, 1900, "烟机柜（Wren 18，1000 宽，1554–2129）内，烟机为内循环；由 H 墙 FO 控制；" + _WREN, "待定", "socket", "single")]
KT["extra_pts"] += [("H", "FO", "电器开关 FCU ×3（烤箱 / 灶点火 / 烟机）", 260, 1100, "墙垛正面（台面 B 尽端上方），离灶边约 620；三个带开关熔断接线盒分别控制 C39（两路）、C40；" + _WREN, "待定")]
KT["notes5"] += (" Rev B：橱柜按 Wren 橱柜图（S8097782/1，2026-08-16）重画（台面 900，吊柜底 1354，烟机柜 1000 中心对烤箱 / 灶）；"
                 "插座按橱柜尺寸重新定位：灶两边新增台面插座 C36 / C37（离灶边 ≥ 300），烤箱 / 灶点火插座 C39、烟机插座 C40，开关 FO 在墙垛；"
                 "C24 / C10 移到转角台面 D 上，C25 在冰箱后正中。")
BK["notes5"] += " Rev B（续）：半岛台 / 台面 / 吊柜按 Wren 橱柜图；C09 在台面 C 正中，C23 在半岛台靠墙一端正中；新增洗碗机开关 FD + 洗碗机插座 C38（角柜内）。"

# Rev B, owner round 2 (2026-10-09): worktop sockets 300 above the quartz (centre h1200); FD hidden in the D wall unit (ask the
# electrician whether all appliance FCUs can go under the stairs instead); C38 at h450; S13 150 from the door; L38 room centre.
_UP = "台面上方 300（中心 h1200，业主 2026-10-09）"
for _R, _k in ((BK, "C09"), (BK, "C23"), (KT, "C24"), (KT, "C10")):
    _o = _R["override"][_k]; _R["override"][_k] = (_o[0], _o[1], _o[2].replace("h1100", _UP), 1200)
_FCU_UNDER_STAIRS = "⚠ 能否把所有电器开关 FCU（FD / FO）都集中放到楼梯下（配电箱处）—— 请电工评估"
BK["extra_pts"] = [e for e in BK["extra_pts"] if e[1] not in ("FD", "C38")] + [
    ("D", "FD", "洗碗机开关 FCU（藏在吊柜内）", 750, 1700, "暂藏在 D 面吊柜（Wren 22）里面，开柜门可操作；控制洗碗机插座 C38；" + _FCU_UNDER_STAIRS, "WX3"),
    ("D", "C38", "洗碗机插座 Single socket（在角柜内）", 1080, 450, "在洗碗机旁转角柜（Wren 7）后面，h450（业主 2026-10-09）；由 FD 控制；洗碗机 Bosch 集成 600 位于离墙垛 36–636；" + _WREN, "WX3", "socket", "single")]
KT["extra_pts"] = [(e[:4] + (1200, e[5].replace("台面 B 上", "台面 B 上，" + _UP))) + e[6:] if e[1] in ("C36", "C37") else
                   (e[:5] + (e[5] + "；" + _FCU_UNDER_STAIRS,) + e[6:] if e[1] == "FO" else e) for e in KT["extra_pts"]]
KT["extra_pts"] = [("G", "C39", "灶台 / 烤箱供电插座（双联，在烤箱 / 灶背后）", 1562, 300,
                    "用途：给灶 AEG HKB95820NB（点火）+ 烤箱 AEG BPX535061M 供电；放在烤箱 / 灶正后方（烤箱中心，离墙垛 1048），位置可按电器说明书 / 现场调整（业主 2026-10-09）；由 H 墙 FO 控制；烤箱按说明书确认 13A 插头或接独立 cooker 回路（电工定）",
                    "待定", "socket", "double") if e[1] == "C39" else e for e in KT["extra_pts"]]
KT["features"] = KT.get("features", []) + [("G", "注：C39 = 灶台 + 烤箱供电，|在它们背后；位置可调整。", 1990, 2600, 450, 750, "note"),
                                           ("H", "注：FO 能否|放到楼梯下|（配电箱处）？|请电工评估。", 15, 505, 200, 700, "note")]
KT["extra_pts"] = [e[:2] + ("电器开关 FCU×3（烤箱 / 灶 / 烟机）",) + e[3:] if e[1] == "FO" else e for e in KT["extra_pts"]]
BK["features"] = BK.get("features", []) + [("D", "注：FD 暂藏在吊柜里；|能否把所有电器开关（FD / FO）|集中放到楼梯下 —— 请电工评估。", 1350, 2700, 1650, 2050, "note")]
BK["override"]["S13"] = ("A", 3.020 - (4.290 - 2.523 + 0.150), "中心离门 KP762 洞边 150（业主 2026-10-09；原 133），h1200")
UT = ROOMS["GF_洗衣房"]
UT["rev"] = dict(rev="B")
UT["ceil_move"] = {"L38": ((1.270 + 4.290) / 2, (14.834 + 16.034) / 2)}       # owner 2026-10-09: room centre
UT["notes5"] += " Rev B：筒灯 L38 移到房间正中（业主 2026-10-09）。"
_o = KT["override"]["C25"]
KT["override"]["C25"] = (_o[0], _o[1], "⚠ 冰箱专用：单独一路线（专线，不与其他插座共用；业主 2026-10-09）；" + _o[2])
KT["circ_set"] = dict(KT.get("circ_set", {}), C25="冰箱专线")
KT["features"] = KT.get("features", []) + [("F", "注：C25 = 冰箱专用插座，|单独一路线（专线）。", 1000, 1700, 650, 900, "note")]
KT["notes5"] += " C25 为冰箱专用插座，单独走一路线（专线）。"
KT["ceil_move"] = {"L27": (2.629, 13.152)}                       # owner 2026-10-09: on the hob / hood centreline (Wren), N-S unchanged
KT["notes5"] += " 主灯 L27 东西向挪到灶 / 烟机中线上（离西 1328），南北不变。"
UT["override"]["C12"] =("L", 1.200 - 0.640, "用途：洗衣机 + 烘干机供电；降低到机器背后 h450（业主 2026-10-09；原台面上方 h1200）；位置按给排水管道（进水阀 / 排水口）需求现场调整", 450)
UT["features"] = UT.get("features", []) + [("L", "注：C12 = 洗衣机 + 烘干机供电，|在机器背后；按管道需求调整位置。", 40, 1160, 1300, 1650, "note")]
UT["notes5"] += " C12（洗衣机 / 烘干机供电）降低到机器背后 h450，位置按管道需求调整。"
KT["notes5"] += " 台面插座统一为台面上方 300（中心 h1200）；FD 暂藏吊柜内，FCU 能否集中到楼梯下待电工评估。"
BK["notes5"] += " S13 离门洞边 150；C09 / C23 台面上方 300（h1200）；C38 改 h450。"

RY = ROOMS["GF_后院"]
RY["rev"] = dict(rev="B")
_ry_run = 16.264 - 8.129                                          # B wall run (left end = 16.264 end)
_ry_mid = ((16.264 - 15.363) + (16.264 - 14.110)) / 2              # centre of the wall piece between 洗衣房小窗 and 厨房大窗, from the left end
RY["override"]["L10"] = ("B", _ry_run - _ry_mid, "户外壁灯 G26_3，IP44 以上；在洗衣房小窗与厨房大窗之间墙段正中（两边各约 627），h2000（业主 2026-10-09；原贴厨房大窗边、h1800）", 2000)
RY["override"]["L09"] = ("B", _ry_run - 4.850, "户外壁灯 G26_2，IP44 以上；位置不变，h2000（业主 2026-10-09，与 L10 同高；原 1800）", 2000)
RY["extra_pts"] = [e for e in RY["extra_pts"] if e[1] not in ("L40", "L41", "L42", "L43")] + [   # owner 2026-10-09: no spotlights, one tail for an outdoor LED strip
    ("D", "L40", "户外灯带出线 LED strip cable tail", 500, 450, "只留线（业主 2026-10-09）：围栏改做户外 LED 灯条，不做地灯 / spotlight（原 L40–L43 四个点取消）；在围栏北端（离左端墙角约 500，离地约 450）留防水接线盒 IP68 + 出线，灯条沿白卵石带走；驱动 / 开关位置待定", "待定")]
RY["notes5"] += (" Rev B：B 墙两个户外壁灯 L09 / L10 改 h2000（约与窗顶 2040 齐）；L10 挪到洗衣房小窗与厨房大窗之间墙段正中；"
                 "D 围栏不做地灯，原 L40–L43 改为一个户外灯带出线 L40（离左端约 500，h450）。")

RY = ROOMS["GF_后院"]
# 后院 Rev C (owner 2026-10-09): outdoor pedestal basin on C (model v44 RearWall_PedestalBasin, centre x 3.582; plumbing.py "OUT":
# cold only 15 hard water via DCV + indoor isolating valve, frost-protected; waste 32 through the rear wall into the utility).
_C_RUN = 4.530 - 1.040
_ob = round((4.530 - 3.582) * 1000)                                           # basin centre from C's left end (948)
RY["rev"] = dict(rev="C")
RY["furniture"] = RY["furniture"] + [("户外立柱台盆（盆宽 500，盆面约 850，模型 v44）", [3.332, 16.264, -0.02, 3.832, 16.664, 0.852])]
RY["extra_pts"] = RY["extra_pts"] + [
    ("C", "OW", "户外台盆冷水 Cold supply 15", _ob + 100, 600, "户外台盆（立柱盆）冷水：15 硬水，室内设隔离阀 + 防回流 DCV，室外段防冻保温；按给排水图 OUT；出水位按台盆 / 龙头产品现场定", "冷水 15", "water", ""),
    ("C", "OD", "户外台盆排水 Waste 32", _ob - 40, 350, "排水 32：穿后墙接洗衣房地坪下管（给排水图）；高度按立柱盆存水弯现场定", "排水 32", "water", "")]
RY["features"] = RY.get("features", []) + [("C", "注：户外台盆（按 Blender 模型 v44）——|只有冷水；给水 / 排水位置按产品和管道现场调整；|冬天防冻（室内隔离阀可关断放空）。", 1500, 3200, 2900, 3350, "note")]
RY["extra_pts"] += [("C", "C41", "户外插座 IP66（专线）", 1720, 600,
                      "业主 2026-10-09：C 墙新增户外插座，单独一条线从配电箱出（专线，RCD 保护）；在壁灯 L08 正下方，离台盆边约 520（与水保持距离），h600，防水盖朝下", "专线", "socket", "double")]
RY["features"] += [("C", "注：C41 户外插座 —— 单独一条线|从配电箱出（专线 + RCD），IP66。", 1500, 3200, 2450, 2750, "note")]
RY["notes5"] += " C 墙新增户外插座 C41（IP66，h600，L08 正下方），专线从配电箱单独出。"
RY["notes5"] += f" Rev C：C 墙加户外立柱台盆（模型 v44，中心离 C 墙左端 {_ob}，盆面约 850）：冷水 15（室内隔离阀 + DCV，防冻）+ 排水 32 穿墙进洗衣房（业主 2026-10-09）。"


# ---------------- 主卧套间 Rev M (owner 2026-10-09): TH under S5 on the bedroom B wall; C06 onto H1 (vanity side, beside F25), h450;
# SM / ST / SF out of the en-suite onto the bedroom B wall right of the F25 opening, low (h450 band)
_MB, _BT = ROOMS["FF_主卧"], ROOMS["FF_主卫"]
for _k in ("FF_主卧", "FF_主卫", "FF_衣帽间"): ROOMS[_k]["rev"] = dict(rev="M")
_MB["extra_pts"] = [e for e in _MB.get("extra_pts", []) if e[1] != "TH"] + [
    ("B", "TH", "地暖温控面板 UFH thermostat", 3870, 1050, "S5 正下方，中心距 150（业主 2026-10-09 挪到 B 墙）；有线温控需穿线到地暖分水器接线中心，无线温控也按此位置留底盒；型号由地暖供应商定", "待定")]
_sw = {e[1]: e for e in _BT.get("extra_pts", []) if e[1] in ("SM", "ST", "SF")}
_BT["extra_pts"] = [e for e in _BT.get("extra_pts", []) if e[1] not in ("SM", "ST", "SF")]
_MB["extra_pts"] += [("B", k, _sw[k][2], s_, 450, f"本房间 B 墙，主卫入口 F25 洞口右边，一排三个（中心距 130，离地 450；业主 2026-10-09 从主卫 G 墙挪出）；"
                      + ("供主卫 N-WC1 出线面板" if k == "SM" else "供主卫 N-TR1 出线面板" if k == "ST" else "主卫排风扇；风扇位置 / 型号现场定"), _sw[k][6])
                     for k, s_ in (("SM", 1170), ("ST", 1300), ("SF", 1430))]
_BT["features"] = [f for f in _BT.get("features", []) if not f[1].startswith("注：SM / ST / SF")]
_H1 = 1.348 - 0.209
_BT["override"]["C06"] = ("H1", _H1 - 0.985, "⚠ 业主 2026-10-09：挪到 H1 墙（盥洗室侧，F25 洞口与墙角之间 307 宽墙段正中），h450；卫生间内插座按 BS 7671 请电工判定（可能需改剃须插座）", 450)
_MB["features"] = _MB.get("features", []) + [("B", "注：SM / ST / SF = 主卫智能马桶盖、|电热毛巾架、排风扇开关（FCU），|放在主卧这一侧，离地 450。", 1100, 2600, 1500, 1900, "note")]
_MB["notes5"] += " Rev M：地暖温控 TH 挪到 B 墙 S5 正下方（h1050）；SM / ST / SF 从主卫挪到主卧 B 墙 F25 洞口右边，离地 450。"
_BT["notes5"] += " Rev M：C06 挪到 H1 墙（F25 洞口旁），h450；SM / ST / SF 挪到主卧 B 墙。"

# ---------------- 后书房 Rev G (owner 2026-10-09): C16 off the D partition onto the rear wall C, about 450 from the D corner
_RS = ROOMS["FF_后书房"]
_RS["rev"] = dict(rev="G")
_RS["override"]["C16"] = ("C", 0.450, "业主 2026-10-09：从 D 墙挪到 C 墙（后墙），中心离 D 墙角约 450，h450；床（占位）贴 C 墙时在床侧，床定了再核", 450)
_RS["notes5"] += " Rev G：C16 从 D 墙挪到 C 墙（离 D 墙角约 450，h450）。"

# ---------------- 主客厅区 Rev H / 副客厅 Rev H (owner 2026-10-10): UFH thermostat TH under the room's switch, same as 主卧
# (centre 150 below, h1050): 主客厅 C wall under S3 (s3010), 副客厅 F wall under S8 (s2140). Other GF zones (P-09) not added.
_TH_NOTE = "正下方，中心距 150（业主 2026-10-10，同卧室 2 做法）；有线温控需穿线到地暖分水器接线中心，无线温控也按此位置留底盒；型号由地暖供应商定"
for _k in ("GF_主客厅", "GF_门厅楼梯", "GF_餐厅", "GF_门廊"): ROOMS[_k]["rev"] = dict(rev="H", date="2026-10-10")
ROOMS["GF_主客厅"]["extra_pts"] = ROOMS["GF_主客厅"].get("extra_pts", []) + [("C", "TH", "地暖温控面板 UFH thermostat", 3010, 1050, "S3 " + _TH_NOTE, "待定")]
ROOMS["GF_主客厅"]["notes5"] += " Rev H：S3 正下方加地暖温控面板 TH（中心距 150，h1050）。"
LR["rev"] = dict(rev="H", date="2026-10-10")
LR["extra_pts"] = LR.get("extra_pts", []) + [("F", "TH", "地暖温控面板 UFH thermostat", 2140, 1050, "S8 " + _TH_NOTE, "待定")]
LR["notes5"] += " Rev H：S8 正下方加地暖温控面板 TH（中心距 150，h1050）。"


# ---------------- v47 (2026-10-14): model v47 = owner keyplan screenshot, owner-adjusted in Blender (log: output/product_components_20260927/
# _claude_edits_v47_20261014.md).  厨房区 Rev C / 后院 Rev D / 主客厅区 Rev I.
#   * 早餐区: French door moved 91 (frame 8.764-10.405, 600 from the A wall); fridge 850 x 600 in the old boiler corner (A wall), C25 behind it;
#     boiler G23 / softener G24 moved out to the laundry; FD (dishwasher FCU) -> under the stairs
#   * 厨房: door to the laundry -> plain opening 760 (x 2.070-2.830); fridge moved out; FO (oven / hob / hood FCUs) -> under the stairs
#   * 洗衣房: rear door 880 moved to x 2.650-3.530 (old door walled up, rear window gone); washer + dryer cabinet at the west end (C12 behind it);
#     boiler on the rear wall, hot-water cylinder (no longer combi), softener; 4 single white fused switches FU1-FU4 under the boiler;
#     all laundry plates white
#   * 后院: rear door + French door moved; L08 left of the new door; outdoor basin under it (owner); C41 outdoor socket cancelled (owner deleted it)
#   * 餐厅 J (stair side, hall face of the winder closure): 4 single brass fused switches FD / FO1-FO3 (owner: every other FCU under the stairs)
_V47 = "（模型 v47，业主 2026-10-14）"
_FCU_STAIR = "楼梯下柜内（配电箱旁）单联 fused switch，业主 2026-10-14 集中"
BK, KT, UT, RY, DN = ROOMS["GF_早餐区"], ROOMS["GF_厨房"], ROOMS["GF_洗衣房"], ROOMS["GF_后院"], ROOMS["GF_餐厅"]
for _R in (BK, KT, UT): _R["rev"] = dict(rev="C", date="2026-10-14")
BK["openings"] = [("door", "法式门（通后花园，框 1641；v47 挪 91，门框离 A 墙 600）", (1.270, 8.764), (1.270, 10.405), 0, 2032) if o[1].startswith("法式门") else o
                  for o in BK["openings"]]
BK["furniture"] = [f for f in BK["furniture"] if not f[0].startswith(("柜 G24", "挂墙柜 G23"))] + [
    ("冰箱 850×600（原热水器位置）", [1.399, 8.172, 0.0, 2.249, 8.772, 1.802])]
BK["override"]["S12"] = ("B", 11.824 - (10.405 + 0.150), "中心离法式门洞边 150（法式门 v47 挪 91 后跟着挪），h1200")
BK["room_note"]["C25"] = "冰箱专用插座（单独一路线 = 专线），冰箱背后，h450" + _V47
BK["room_note"].pop("C06", None)
BK["drop"] = set(BK.get("drop", set())) | {"C06"}       # C06 (by the old boiler) -> the 4 laundry fused switches FU1-FU4 (owner, model v47)
BK["circ_set"] = dict(BK.get("circ_set", {}), C25="冰箱专线")
BK["extra_pts"] = [(e[:5] + (e[5].replace("由 FD 控制", "由楼梯下 FD 控制"),) + e[6:]) for e in BK["extra_pts"] if e[1] != "FD"]
BK["extra_pts"] = [(e[:2] + ("洗碗机插座 Twin socket（在角柜内，双位，白色）",) + e[3:8] + ("double",)) if e[1] == "C38" else e for e in BK["extra_pts"]]
BK["features"] = [f for f in BK.get("features", []) if not f[1].startswith(("注：FD", "注：C06"))]
BK["notes5"] += " Rev C" + _V47 + "：法式门挪 91（门框离 A 墙 600），原热水器位置放冰箱 850×600，冰箱插座 C25（专线）在冰箱背后；S12 跟法式门；洗碗机开关 FD 挪到楼梯下；原热水器旁插座 C06 取消（改为洗衣房 4 个 fused switch）。"

KT["openings"] = [("door", "无门洞口 760（通洗衣房）", (2.070, 14.714), (2.830, 14.714), 0, 2032) if o[1].startswith("门（通洗衣房") else o for o in KT["openings"]]
KT["furniture"] = [f for f in KT["furniture"] if not f[0].startswith("冰箱")]
KT["override"].pop("C25", None); KT["room_note"].pop("C25", None)
KT["extra_pts"] = [(e[:5] + (e[5].replace("由 H 墙 FO 控制", "由楼梯下 FO 控制"),) + e[6:]) for e in KT["extra_pts"] if e[1] != "FO"]
KT["features"] = [f for f in KT.get("features", []) if not f[1].startswith(("注：C25", "注：FO"))]
KT["extra_pts"] = [(e[:2] + (e[2] + "（柜内，白色）",) + e[3:]) if e[1] in ("C39", "C40") else e for e in KT["extra_pts"]]
KT["extra_pts"] += [("F", "C42", "双位插座 Twin socket（antique brass）", 400, 450,
                     "新增（业主 2026-10-14）：厨房一侧，通洗衣房洞口左边墙段（窗墙角到洞口 800）正中，h450" + _V47, "WX3", "socket", "double")]
KT["notes5"] += " Rev C" + _V47 + "：通洗衣房的门改为无门洞口 760（x 2.070–2.830）；冰箱挪到早餐区（C25 跟着走）；洞口左边新增双位插座 C42（antique brass，h450）；C39 在烤箱后柜内、白色；电器开关 FO（烤箱 / 灶 / 烟机）挪到楼梯下。"

UT["openings"] = [("door", "无门洞口 760（通厨房）", (2.830, 14.834), (2.070, 14.834), 0, 2032),
                  ("window", "小窗（窗台约 1120）", (1.270, 15.363), (1.270, 15.840), 1120, 2040),
                  ("door", "后门 单扇 880（外开；v47 挪位）", (2.650, 16.034), (3.530, 16.034), 0, 2012)]
UT["swings"] = []
UT["furniture"] = [("洗衣机 + 烘干机柜（机上盆）G04", [1.303, 14.808, 0.0, 2.033, 16.034, 1.002]),
                   ("锅炉 G23（挂墙）", [3.650, 15.655, 1.388, 4.095, 16.034, 2.109]),
                   ("软水机 G24", [3.701, 15.664, 0.054, 4.153, 15.989, 0.591]),
                   ("热水缸 Ø500（型号待定）", [3.780, 14.872, 0.002, 4.280, 15.372, 1.502])]
UT["override"].pop("C12", None)
UT["features"] = [f for f in UT.get("features", []) if not f[1].startswith("注：C12")]
UT["room_note"].update({"S14": "通厨房洞口南侧，离洞边约 130" + _V47, "S15": "后门锁侧，离门洞边约 140" + _V47,
                        "C12": "洗衣机 / 烘干机柜背后，h450；机器电源经 FU1 / FU2 fused switch" + _V47,
                        "C13": "隔墙洗衣房一侧，h450" + _V47})
_K0 = 1.270                                                             # K (rear wall) left end x
UT["extra_pts"] = UT.get("extra_pts", []) + [
    ("K", f"FU{i}", f"Fused switch FCU · {lab}（白色）", round((x - _K0) * 1000), 1200,
     f"锅炉下方一排 4 个单联 fused switch（中心距 96），白色；{lab}" + _V47, "待定")
    for i, (lab, x) in enumerate((("洗衣机", 3.803), ("烘干机", 3.899), ("锅炉", 3.995), ("地暖电子控制", 4.091)), 1)]
UT["extra_pts"] += [("K", "C43", "双位插座 Twin socket（白色）", round((3.947 - _K0) * 1000), 850,
                     "新增（业主 2026-10-15）：锅炉 / 热水器处，FU1–FU4 正下方居中，h850（在软水机上方）；给软水机及热水器附属设备供电", "待定", "socket", "double")]
UT["notes5"] += (" Rev C" + _V47 + "：后门 880 挪到后墙 x 2.65–3.53（原门洞补墙、后小窗取消）；通厨房改无门洞口 760；洗衣机 + 烘干机柜挪到西头（C12 在机器背后），"
                 "锅炉挂后墙（不再 combi，加热水缸），软水机在锅炉下；锅炉下 4 个单联 fused switch FU1–FU4（洗衣机 / 烘干机 / 锅炉 / 地暖电子控制），下面一个白色双位插座 C43（h850，软水机用）；洗衣房开关插座全部白色。")

RY["rev"] = dict(rev="D", date="2026-10-14")
RY["openings"] = [("door", "早餐区法式门（v47 挪 91）", (1.040, 10.405), (1.040, 8.764), 0, 2032) if o[1] == "早餐区法式门" else
                  ("door", "洗衣房后门 880（外开；v47 挪位）", (3.530, 16.264), (2.650, 16.264), 0, 2012) if o[1].startswith("洗衣房后门") else o
                  for o in RY["openings"] if o[1] != "洗衣房后小窗"]
RY["override"]["L08"] = ("C", 1.845 - 1.040, "户外壁灯 G26_1，IP44 以上；挪到洗衣房后门左边（中心 x 1.845）" + _V47)
_ob = round((4.530 - 1.836) * 1000)                                       # basin centre from C's left end
RY["furniture"] = [f for f in RY["furniture"] if not f[0].startswith("户外立柱台盆")] + [
    ("户外立柱台盆（盆宽 500，盆面约 850，后门左边）", [1.587, 16.264, -0.02, 2.085, 16.664, 0.852])]
RY["extra_pts"] = [e for e in RY["extra_pts"] if e[1] not in ("C41", "OW", "OD")] + [
    ("C", "OW", "户外台盆冷水 Cold supply 15", _ob + 100, 600, "户外台盆（立柱盆，挪到后门左边、壁灯 L08 下）冷水：15 硬水，室内设隔离阀 + 防回流 DCV，室外段防冻保温；出水位按台盆 / 龙头产品现场定" + _V47, "冷水 15", "water", ""),
    ("C", "OD", "户外台盆排水 Waste 32", _ob - 40, 350, "排水 32：穿后墙接洗衣房地坪下管（给排水图）；高度按立柱盆存水弯现场定" + _V47, "排水 32", "water", "")]
RY["features"] = [f for f in RY.get("features", []) if not f[1].startswith("注：C41")]
RY["notes5"] += " Rev D" + _V47 + "：洗衣房后门挪到 x 2.65–3.53（后小窗取消），早餐区法式门挪 91；壁灯 L08 挪到后门左边，户外台盆挪到 L08 下；户外插座 C41 取消。"

for _k in ("GF_主客厅", "GF_门厅楼梯", "GF_餐厅", "GF_门廊"): ROOMS[_k]["rev"] = dict(rev="I", date="2026-10-14")
DN["faces"] = [("J", "南墙", "楼梯侧板（楼梯下检修门 + 电器开关）Stair side", (3.322, 8.040), (3.322, 5.069), ("墙端（厨房门框）", "楼梯起步")) if f[0] == "J" else f
               for f in DN["faces"]]
DN["extra_pts"] = DN.get("extra_pts", []) + [
    ("J", pid, f"Fused switch FCU · {lab}（柜内，白色）", round((8.040 - y) * 1000), 1200, f"{_FCU_STAIR}；装在楼梯下柜子里面（本面板背面，检修门旁），白色；{lab}；一排 4 个（中心距 96）", "待定")
    for pid, lab, y in (("FD", "洗碗机", 7.576), ("FO1", "烤箱", 7.672), ("FO2", "灶（点火）", 7.768), ("FO3", "烟机", 7.864))]
DN["features"] = DN.get("features", []) + [("J", "注：FD / FO1–FO3 装在楼梯下柜子里面|（本面板背面，开检修门可操作），白色。", 120, 1400, 2030, 2330, "note")]
DN["notes5"] += " Rev I（2026-10-14）：楼梯下柜子里面（J 面板背面，检修门旁）加 4 个白色单联 fused switch：FD 洗碗机、FO1 烤箱、FO2 灶、FO3 烟机（原在早餐区 / 厨房墙上，业主要求集中到楼梯下）；C02 改双位插座。"

# ---------------- 二楼走廊 Rev H (owner 2026-10-15): stair pendant F06 3-way — the intermediate moves from S11 to S12, so S11 is a plain
# 2-gang 2-way plate (NAB42) and S12 a 1-gang intermediate (NAB13); strappers GF S6 -> FF S12 (intermediate) -> FF S11
CR = ROOMS["FF_二楼走廊"]
CR["rev"] = dict(rev="H", date="2026-10-15")
_K3 = "K 键 = 楼梯吊灯 F06 三控：一层 S6（双控）+ 二层 S12（中途）+ 二层 S11（双控）"
CR["override"]["S11"] = CR["override"]["S11"][:2] + ("楼梯口，两联双控（BG NAB42，一块面板）：D 键 = 走廊灯（与 S8 双控），" + _K3 + "；中心离 H 墙左端（靠 G 墙）200，h1200",)
CR["override"]["S12"] = CR["override"]["S12"][:2] + ("后书房门旁，单联中途开关（BG NAB13）K 键（" + _K3 + "）；中心离后书房门口 350；此段地面为下行台阶，h1200 起算面现场按台阶 / 平台定",)
CR["notes5"] += " Rev H（2026-10-15）：楼梯吊灯三控的中途开关由 S11 改到 S12 —— S11 = 两联双控 NAB42，S12 = 单联中途 NAB13；联络线 一层 S6 → 二层 S12 → 二层 S11。"

SETS = {  # set name -> (rooms, output name)
    "后院": (["GF_后院"], "27PR_墙面立面_后院_RevD_后门挪位_台盆"),
    "前院": (["GF_前门凹位", "GF_前花园"], "27PR_墙面立面_前院_RevB_充电桩挪北侧", ("前院", 5)),
    "厨房": (["GF_早餐区", "GF_厨房", "GF_洗衣房"], "27PR_墙面立面_厨房区_RevC_洗衣房后门_冰箱_FCU", ("厨房区", 4)),
    "主客厅": (["GF_主客厅", "GF_门厅楼梯", "GF_餐厅", "GF_门廊"], "27PR_墙面立面_主客厅区_RevI_楼梯下FCU", ("主客厅区", 3)),
    "二楼走廊": (["FF_二楼走廊"], "27PR_墙面立面_二楼走廊_RevH_S12中途开关"),
    "走廊": (["FF_二楼走廊"], "27PR_墙面立面_二楼走廊_RevH_S12中途开关"),
    "后书房": (["FF_后书房", "FF_后房窄卫浴"], "27PR_墙面立面_后书房_RevG_C16挪后墙"),
    "中间书房": (["FF_中间书房"], "27PR_墙面立面_中间书房_RevD_天花2700"),
    "书房1": (["FF_中间书房"], "27PR_墙面立面_中间书房_RevD_天花2700"),
    "次卧": (["FF_次卧", "FF_次卧卫浴"], "27PR_墙面立面_次卧_RevP_毛巾架出线_床头650"),
    "主卧": (["FF_主卧", "FF_主卫", "FF_衣帽间"], "27PR_墙面立面_主卧套间_RevM_温控开关挪位", ("主卧套间", 3)),
    "副客厅": (["GF_副客厅", "GF_楼下洗手间"], "27PR_墙面立面_副客厅_RevH_加地暖温控"),
}

if __name__ == "__main__":
    from build_drawings import build
    want = sys.argv[1] if len(sys.argv) > 1 else list(SETS)[-1]
    keys, name, *suite = SETS[want]

    class M:
        CSS = CSS
        sheets = staticmethod(lambda: build_suite(keys, suite[0][1], suite[0][0]) if suite else [s for k in keys for s in build_room(k)])
    build(name, M)
