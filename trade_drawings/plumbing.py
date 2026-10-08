# -*- coding: utf-8 -*-
"""27PR 给排水施工图 (water supply + drainage) — design data and A3 sheets.

All coordinates are Blender metres (GF floor z = 0, FF floor ≈ 2.85 rear / 3.21 front), fixtures from 27PR_CGI_v40 (see
_blender_fixtures_v40.txt), re-checked against v42 on 2026-10-08 (west-bath false walls / niches / pipes, S2 boxes). Site facts from the user (2026-10-07): mains stopcock under the stairs at the front entrance,
combi boiler (Vaillant ecoTEC plus, G23) with the central softener (G24) right below it, RO purifier under the kitchen sink,
no existing soil stack to reuse (stacks are designed here). Everything marked 现场确认 must be checked on site.
"""
import html, math, os, re
VARIANT = os.environ.get("WB_VARIANT", "B")   # 西卫马桶走法：B（2026-10-08 定为正式）假墙内走到北墙角再沿北墙下往后；A 落进本格搁栅直着往后（已弃用）
from plan_base import Sheet as _Sheet, BASE_CSS, MM, wrap


def Sheet(*a, **k):
    k.setdefault("rev", "C"); k.setdefault("date", "2026-10-08")
    return _Sheet(*a, **k)

# ---------------- design data ----------------
STYLE = {   # kind: (colour, width mm, dash, label)
    "mdpe":  ("#1b3a8a", 0.9, "3 1.2", "进户自来水 MDPE 25（埋深 ≥ 750）Incoming main"),
    "hard":  ("#1b3a8a", 0.7, "", "冷水（硬水，未软化）Mains cold, hard"),
    "soft":  ("#2aa7d6", 0.7, "", "冷水（软化后）Softened cold"),
    "hot":   ("#d62828", 0.7, "", "热水（combi 锅炉出）Hot (from combi)"),
    "pure":  ("#7b3fb5", 0.6, "1.2 0.8", "净化饮用水 Purified drinking"),
    "waste": ("#c77d1a", 0.8, "", "废水 Waste（32 / 40 / 50 mm PVC-U，坡度 ≥ 1:40）"),
    "soil":  ("#6b3e1e", 1.3, "", "污水 Soil（110 mm PVC-U，坡度 1:40）"),
    "ug":    ("#6b3e1e", 1.0, "2.5 1.2", "地下排水 Below ground（110 mm，坡度 ≥ 1:40）"),
    "yard":  ("#1b3a8a", 0.8, "1.6 0.8", "花园给水 MDPE 20 硬水（埋深 ≥ 750）Garden supply"),
    "sw":    ("#2e7d32", 1.0, "2.5 1.2", "地表水 Surface water（110 mm PVC-U，≥ 1:80）→ 渗水井，不接污水"),
}

SHORT = {"mdpe": "进户", "hard": "冷水（硬）", "soft": "冷水（软）", "hot": "热水", "pure": "净水", "waste": "废水", "soil": "污水", "ug": "地下排水",
         "yard": "花园给水", "sw": "地表水"}

EQUIP = [   # id, floor, x, y, w, d (m), text
    ("SC", "GF", 4.00, 3.00, 0.18, 0.18, "总阀 Stopcock + 泄水阀 + DCV（楼梯下）"),
    ("SOFT", "GF", 1.54, 8.53, 0.32, 0.46, "G24 中央软水机 Softener（锅炉正下方，带三阀旁通）"),
    ("BLR", "GF", 1.51, 8.33, 0.44, 0.34, "G23 Vaillant combi 锅炉（挂墙 1.25–1.97 m）"),
    ("RO", "GF", 2.95, 10.62, 0.30, 0.30, "RO 净水器 + 压力桶（厨房水槽柜内，接软水）"),
    ("R1", "GF", 1.40, 8.20, 0.15, 0.15, "R1 立管井（冷 / 热 22 上二层）"),
    ("R1", "FF", 1.37, 8.19, 0.15, 0.15, "R1 立管井（自一层锅炉）箱封 150×150"),
]

FIX = {     # id: floor, x, y, name, supplies, drain (kind, size)
    "G20":  ("GF", -1.27, 7.62, "一层卫生间马桶 WC", "S", ("soil", 110)),
    "G19":  ("GF", -1.27, 6.67, "一层卫生间台盆 Basin", "SH", ("waste", 32)),
    "SINK": ("GF", 3.04, 10.73, "厨房岛台水槽 Kitchen sink", "SHP", ("waste", 40)),
    "DW":   ("GF", 3.97, 11.62, "洗碗机 Dishwasher", "S", ("waste", 40)),
    "LDY":  ("GF", 3.90, 15.44, "洗衣柜（洗衣机 + 干衣机 + 上盆）Laundry", "SH", ("waste", 40)),
    "OUT":  ("GF", 3.58, 16.45, "户外水斗 Outdoor sink", "C", ("waste", 32)),
    "CAR":  ("GF", -4.27, 1.07, "洗车龙头 Outside tap（副客厅前门西侧凹角，户外插座正下方，离地约 380）", "C", ("车道", 0)),
    "F13":  ("FF", 0.79, 1.93, "西卫智能马桶 WC（需 13A 插座，坐原楼板，不抬高）", "S", ("soil", 110)),
    "F14":  ("FF", -0.15, 1.95, "西卫淋浴（墙排地漏在假墙内，淋浴盘坐原楼板，不抬高）Shower", "SH", ("waste", 40)),
    "F12":  ("FF", -0.32, 0.72, "盥洗室台盆柜 Vanity", "SH", ("waste", 40)),
    "F16":  ("FF", -1.05, 7.60, "北卫智能马桶 WC（后墙东角）", "S", ("soil", 110)),
    "F18":  ("FF", -1.14, 6.84, "北卫淋浴 800×900（前面东角）Shower", "SH", ("waste", 40)),
    "F17":  ("FF", -2.02, 6.64, "北卫台盆（前墙，门旁）Vanity", "SH", ("waste", 40)),
    "F25":  ("FF", 4.05, 9.45, "后卫马桶 WC", "S", ("soil", 110)),
    "F26":  ("FF", 4.14, 10.10, "后卫台盆 Basin", "SH", ("waste", 32)),
    "F28":  ("FF", 3.95, 11.10, "后卫淋浴 Shower", "SH", ("waste", 40)),
}

CODE = {"G20": "WC-G", "G19": "B-G", "SINK": "KS", "DW": "DW", "LDY": "LD", "OUT": "OB", "CAR": "FT", "F13": "WC1", "F14": "SH1", "F12": "B1", "F16": "WC2", "F18": "SH2", "F17": "B2", "F25": "WC3", "F26": "B3", "F28": "SH3"}

STACKS = [  # id, x, y, serves
    ("S1", -0.85, 8.26, "后墙外 · 北卫 + 西卫 + 盥洗室（二层 110 转角双支管：北卫直穿后墙接正口、西卫沿墙接侧口）"),
    ("S2", 4.20, 8.30, "室内暗装：二层卧室 4 墙角箱封 200×200（高 1200，顶部 AAV）→ 一层厨房楼梯后墙角箱封 200×200 → 直下地坪下 · 后卫"),
]
CHAMBERS = [("MH", -1.77, 9.60, "现有检查井 MH：全屋汇入（量管底标高）"), ("IC1", -1.10, 8.55, "检查井 IC1（S1 + IC4 汇入）"), ("IC4", 0.62, 8.45, "检查井 IC4（汇合）"), ("IC2", 0.70, 11.00, "检查井 IC2（侧通道）")]
GULLIES = [("G2", 0.40, 10.73, "回水井 G2（厨房）")]

# pipes: floor, kind, size, points, label (shown at the longest segment)
PIPES = [
    # ---- GF supply ----
    ("GF", "mdpe", 25, [(4.00, -0.60), (4.00, 3.00)], "自前院进户 MDPE 25（现场确认位置）"),
    ("GF", "hard", 22, [(4.00, 3.00), (4.00, 8.30)], "22 主管（楼板 / 地坪内）"),
    ("GF", "hard", 15, [(4.00, 4.90), (-4.20, 4.90), (-4.20, 1.07)], "15 硬水 → 洗车龙头 FT（主管三通，经餐厅 / 客厅地坪内暗装到副客厅前门西侧凹角，户外插座正下方出墙，室内隔离阀 + 泄水阀）"),
    ("GF", "hard", 15, [(4.00, 8.30), (4.00, 16.15), (3.58, 16.15), (3.58, 16.40)], "15 硬水 → 户外水斗（DCV + 室内隔离阀，防冻保温）"),
    ("GF", "hard", 15, [(3.80, 16.15), (3.80, 16.40)], "15 硬水 → 水池补水（洗衣房内三通 + 隔离阀 + 泄水阀，穿后墙套管）"),
    ("GF", "yard", 20, [(3.80, 16.40), (3.80, 16.95), (3.20, 16.95)], "20 MDPE 埋地 → 后花园水池补水井 TU + 花园龙头（见 P-07）"),
    ("GF", "hard", 22, [(4.00, 8.30), (1.85, 8.30), (1.70, 8.45)], "22 → 软水机（三阀旁通）"),
    ("GF", "soft", 15, [(2.90, 10.78), (2.95, 10.68)], "15 软水 → RO 净水器（水槽柜内冷水三通）"),
    ("GF", "pure", 10, [(2.95, 10.62), (3.05, 10.48)], "饮用水龙头"),
    ("GF", "soft", 22, [(1.54, 8.53), (1.54, 8.30)], "22 软水 → 锅炉冷水进"),
    ("GF", "soft", 15, [(1.45, 8.40), (1.45, 7.80), (-0.95, 7.80), (-0.95, 7.62), (-1.10, 7.62)], "15 软水 → 一层卫生间"),
    ("GF", "soft", 15, [(-0.95, 7.62), (-0.95, 6.67), (-1.10, 6.67)], ""),
    ("GF", "hot", 15, [(1.35, 8.33), (1.35, 7.86), (-1.03, 7.86), (-1.03, 6.72), (-1.10, 6.72)], "15 热水 → 一层台盆"),
    ("GF", "soft", 22, [(1.70, 8.62), (1.70, 10.78), (2.90, 10.78)], "22 软水 → 岛台水槽（地坪内预埋，套管）"),
    ("GF", "soft", 15, [(2.30, 10.78), (2.30, 11.62), (3.75, 11.62)], "15 → 洗碗机"),
    ("GF", "soft", 15, [(3.30, 11.62), (3.30, 15.30), (3.62, 15.30)], "15 软水 → 洗衣柜"),
    ("GF", "hot", 22, [(1.80, 8.40), (1.80, 10.68), (2.90, 10.68)], "22 热水 → 岛台水槽"),
    ("GF", "hot", 15, [(2.45, 10.68), (2.45, 10.68), (3.40, 10.68), (3.40, 15.22), (3.62, 15.22)], "15 热水 → 洗衣柜上盆"),
    # ---- FF supply (R1 riser from the boiler) ----
    ("FF", "soft", 22, [(1.37, 8.23), (3.45, 8.23), (3.45, 9.20), (4.15, 9.20), (4.15, 11.00)], "22 → 后卫（马桶 / 台盆 / 淋浴）"),
    ("FF", "hot", 22, [(1.42, 8.29), (3.50, 8.29), (3.50, 9.26), (4.10, 9.26), (4.10, 11.05)], "22 热"),
    ("FF", "soft", 22, [(1.32, 8.15), (1.32, 7.75), (-0.75, 7.75), (-1.60, 7.75), (-2.45, 7.75), (-2.45, 6.70), (-2.10, 6.70)], "22 → 北卫（沿后墙、西墙到前墙台盆）"),
    ("FF", "soft", 15, [(-0.75, 7.75), (-0.75, 7.60)], "15 马桶"),
    ("FF", "soft", 15, [(-0.75, 7.75), (-0.75, 6.90), (-1.00, 6.90)], "15 淋浴冷"),
    ("FF", "hot", 22, [(1.27, 8.15), (1.27, 7.70), (-0.85, 7.70), (-2.40, 7.70), (-2.40, 6.75), (-2.10, 6.75)], "22 热"),
    ("FF", "hot", 15, [(-0.85, 7.70), (-0.85, 6.95), (-1.00, 6.95)], "15 淋浴热"),
    ("FF", "soft", 22, [(-0.20, 7.75), (-0.20, 2.42), (-0.45, 2.42), (-0.45, 0.72)], "22 → 西卫 / 盥洗室（北卫主管上三通 → 和西卫马桶管同一格搁栅（北墙下那一格）往前，不另开地板 → 西卫假墙内：竖上到恒温淋浴阀，西到盥洗室台盆）"),
    ("FF", "soft", 15, [(-0.20, 2.42), (0.88, 2.42), (0.88, 2.30)], "15 → 西卫马桶（假墙内往东，马桶段角阀）"),
    ("FF", "hot", 22, [(-0.12, 7.70), (-0.12, 2.40), (-0.51, 2.40), (-0.51, 0.72)], "22 热（同一格搁栅，和冷水并行，保温）"),
    # ---- GF drainage ----
    ("GF", "soil", 110, [(-1.27, 7.82), (-1.27, 8.40), (-1.10, 8.55)], "110 一层马桶 + 台盆 → 穿后墙 → IC1（和 S1 汇合后一起去 MH）"),
    ("GF", "waste", 32, [(-1.27, 6.67), (-1.00, 6.67), (-1.00, 7.82), (-1.20, 7.82)], "32 台盆（接马桶支管 strap-on boss）"),
    ("GF", "waste", 40, [(3.04, 10.73), (1.15, 10.73), (0.40, 10.73)], "40 岛台水槽 → G2（地坪内预埋，≥1:40）"),
    ("GF", "waste", 40, [(3.97, 11.62), (3.04, 11.62), (3.04, 10.80)], "40 洗碗机"),
    ("GF", "waste", 40, [(3.90, 15.44), (3.85, 15.55)], "40 洗衣机 + 上盆（存水弯）→ 地坪下 50 废水管"),
    ("GF", "waste", 32, [(3.58, 16.45), (3.58, 16.10), (3.85, 15.70)], "32 户外水斗 → 穿后墙 → 接洗衣房地坪下管"),
    ("GF", "waste", 50, [(3.85, 15.80), (0.70, 11.00)], "50 废水（洗衣机 + 台盆 + 户外水斗）斜穿厨房地坪下 → 穿西墙 → IC2（约 5.7 m，≥ 1:40，起点留清扫口）"),
    ("GF", "ug", 110, [(0.40, 10.73), (0.70, 11.00)], ""),
    ("GF", "ug", 110, [(4.20, 8.30), (1.00, 8.30), (0.62, 8.45)], "110 S2 到地坪下 → 大半径弯头 → 地坪下往西 → 穿西墙基础 → IC4"),
    ("GF", "ug", 110, [(0.70, 11.00), (0.62, 8.45)], "110 IC2 → IC4"),
    ("GF", "ug", 110, [(0.62, 8.45), (-1.10, 8.55)], "110 IC4 → IC1"),
    ("GF", "ug", 110, [(-0.85, 8.26), (-1.10, 8.55)], ""),
    ("GF", "ug", 110, [(-1.10, 8.55), (-1.77, 9.60)], "110 IC1 → MH"),
    # ---- FF drainage ----
    ("FF", "soil", 110, [(4.05, 9.45), (4.20, 9.45), (4.20, 8.30)], "110 后卫马桶 → 沿东墙往南约 1.2 m → S2（靠楼梯墙角往下）"),
    ("FF", "waste", 40, [(4.14, 10.10), (4.10, 10.06)], "40 后卫台盆 → 落进楼板 → 接淋浴废水"),
    ("FF", "waste", 40, [(3.95, 11.10), (4.10, 11.10), (4.10, 8.36), (4.15, 8.33)], "40 淋浴 + 台盆 → S2（与马桶管并行）"),
    ("FF", "soil", 110, [(-0.95, 7.60), (-0.95, 8.20), (-0.88, 8.26)], "110 北卫马桶（后墙东角）→ 直穿后墙 → S1"),
    ("FF", "waste", 40, [(-1.14, 6.84), (-1.14, 7.90), (-0.90, 7.95), (-0.88, 8.20)], "40 淋浴 → 楼板内往后 → S1 boss"),
    ("FF", "waste", 40, [(-2.02, 6.64), (-2.02, 6.47), (-1.25, 6.47), (-1.25, 6.95), (-1.16, 7.00)], "40 台盆 → 落进楼板 → 接淋浴废水"),
    (("FF", "soil", 110, [(0.79, 2.18), (0.79, 2.45), (0.75, 2.62), (0.75, 7.80), (-0.70, 7.85), (-0.70, 8.16), (-0.76, 8.29)], "110 西卫马桶 → 马桶段假墙内下到楼板（完成面下约 150）→ 落进本格搁栅直着往后 1:40 → 后墙内侧借梁位横走到 S1 旁 → 出墙进 S1（墙外无横管；起点 AAV 在假墙内）")
     if VARIANT == "A" else
     ("FF", "soil", 110, [(0.78, 2.20), (0.78, 2.45), (-0.31, 2.45), (-0.31, 2.62), (-0.31, 8.30), (-0.73, 8.30)], "110 西卫马桶 → 假墙内（地面以上）沿后墙 1:40 到北墙角（约 1.1 m，起点 AAV 在马桶段检修口内）→ 下到楼板，落进北墙下那一格搁栅 → 直着往后约 5.7 m（1:40）→ 穿后墙 → S1 侧口")),
    ("FF", "waste", 40, [(-0.15, 2.44), (-0.15, 2.48), (0.70, 2.46), (0.79, 2.45)] if VARIANT == "A" else [(-0.15, 2.38), (-0.25, 2.43), (-0.31, 2.45)], "40 淋浴墙排地漏 → 淋浴段假墙（100 厚）内、地面以上 → 马桶落管侧口 boss（不进地面、不抬地面）" if VARIANT == "A" else "40 淋浴墙排地漏 → 淋浴段假墙内、地面以上 → 北墙角 110 落管侧口 boss（不进地面、不抬地面）"),
    (("FF", "waste", 40, [(-0.32, 0.72), (-0.32, 2.40), (0.70, 2.42)], "40 盥洗室台盆 → 垂直落进楼板 → 楼板内往后 → 接马桶落管侧口（楼板内，在 110 弯头上方）")
     if VARIANT == "A" else
     ("FF", "waste", 40, [(-0.32, 0.72), (-0.40, 0.72), (-0.40, 2.80), (-0.33, 2.90)], "40 盥洗室台盆 → 垂直落进楼板 → 北墙下同一格搁栅里往后 → 侧面接西卫马桶管（楼板内）")),
]

# ---- rear-garden pond (Blender Pond_* / Rockery_*, v40): coping outer x -4.675..-2.765, y 14.745..17.155; water x -4.45..-2.99,
#      y 14.97..16.93; rockery + waterfall at the house end (y 14.2-15.4); patio ends at y 17.16, lawn beyond ----
POND_OUT = [(-4.675, 14.745), (-2.765, 14.745), (-2.765, 17.155), (-4.675, 17.155)]
POND_IN = [(-4.45, 14.97), (-2.99, 14.97), (-2.99, 16.93), (-4.45, 16.93)]
ROCKERY = [(-4.48, 14.5), (-4.33, 14.21), (-4.12, 14.19), (-3.46, 14.29), (-3.19, 14.44), (-3.12, 14.7), (-3.04, 15.08),
           (-3.09, 15.22), (-4.29, 15.38), (-4.45, 15.17)]
CHANNEL = (-2.62, 14.60, 17.05)          # x, y0, y1 — 100 mm linear channel drain just east of the coping
GARDEN_PTS = [  # id, x, y, w, d (m), text, cls
    ("TU", -2.38, 16.75, 0.30, 0.30, "补水井 TU（浮球阀，AB 型空气隔断）+ 花园龙头 GT", "eq"),
    ("CP", -2.62, 17.45, 0.45, 0.45, "沉泥井 CP（450，带沉泥槽）", "ic"),
    ("SA", -2.62, 23.10, 1.20, 1.20, "渗水井 SA（模块式蓄水箱约 1 m³，距房屋 ≥ 5 m）", "ic"),
]
GARDEN_PIPES = [
    ("hard", 15, [(3.80, 16.15), (3.80, 16.40)], "15 硬水：洗衣房内户外水斗支管三通 → 隔离阀 + 泄水阀 → 穿后墙套管"),
    ("yard", 20, [(3.80, 16.40), (3.80, 16.95), (-2.38, 16.95), (-2.38, 16.85)], "20 MDPE 硬水，埋深 ≥ 750，沿露台后边往西约 6.2 m → TU"),
    ("waste", 50, [(-2.99, 16.55), (-2.62, 16.55)], "50 溢流（设计水位，带防鱼格栅）→ 地沟"),
    ("sw", 110, [(-2.62, 17.05), (-2.62, 17.45)], "110 地沟出口 → CP"),
    ("sw", 110, [(-2.62, 17.45), (-2.62, 22.50)], "110 地表水 CP → SA（约 5 m，≥ 1:80）"),
]
NOTES_GARDEN = [
    "说明 Notes",
    "1. 水池补水 / 花园龙头用硬水（不过软水机）：在洗衣房内从户外水斗支管三通分出，室内装隔离阀 + 泄水阀，穿后墙套管后改 20 mm MDPE，沿露台后边埋深 ≥ 750 走到水池东侧补水井 TU。",
    "2. 水池属 Water Regs 第 5 类液体：补水必须有 AB 型空气隔断——浮球阀装在池边补水井内，出水口高于溢流水位 ≥ 20 mm；不得把浮球阀 / 软管泡在池水里直接补水。花园龙头 GT 装 DCV、可单独关断，冬季排空。",
    "3. 地沟 CH：100 mm 宽线性排水沟（ACO 或不锈钢缝隙沟），沿水池东侧压顶外约 2.5 m，沟底坡向北端出口；露台铺装向地沟找坡约 1:60。",
    "4. 水池溢流：池壁在设计水位处预埋 50 mm 溢流管（带格栅），接入地沟；放空水池用水泵接软管排入地沟。",
    "5. 地沟出口 → 沉泥井 CP → 110 mm 地表水管 ≥ 1:80 → 草坪下渗水井 SA（距房屋 ≥ 5 m，施工前做渗透测试 BRE 365，按结果定容积）。地表水不接污水井 MH。",
    "6. 水泵 / 过滤器 / 瀑布泵电源：户外 IP66 插座，30 mA RCD，埋地用 SWA 电缆（电气另出）。",
]

NOTES_SUPPLY = [
    "说明 Notes",
    "[GF]1. 进户：楼梯下总阀（stopcock）后依次装 泄水阀、双止回阀 DCV；总阀后 22 mm 主管经楼板 / 地坪内到厨房。",
    "[GF]2. 软水机 G24 装在 combi 锅炉 G23 正下方，进出口带三阀旁通；户外用水全部用硬水、不过软水机：户外水斗、后花园水池补水 + 花园龙头（见 P-07）、副客厅前门旁洗车龙头 FT。厨房 RO 净水器接软水（软水进 RO 可保护膜，出水已去掉钠）。",
    "3. 软化后冷水供：锅炉冷水进、全屋马桶 / 台盆 / 淋浴 / 洗碗机 / 洗衣机。热水全部来自 combi 锅炉，无热水缸。",
    "4. 二层冷 / 热水经 R1 立管（卧室 4 西南角箱封 150×150）上楼，楼板内敷设；穿搁栅按 Building Regs 规定打孔，不得开深槽。",
    "5. 管材：铜管或 PEX（WRAS 认证），主管 22 mm、支管 15 mm；热水管及外墙 / 楼板内冷水管全部保温。",
    "6. 每个用水点装检修隔离阀（service valve）；淋浴用恒温混水阀；户外龙头装 DCV、室内可关断，冬季可排空。",
    "[GF]7. 岛台水槽在地面中间：冷 / 热 / 净水管和排水管须在地坪浇筑前预埋（带套管），位置以厨房深化图为准（现场确认）。",
    "[FF]8. 西卫（主卧卫生间）地面不抬高：冷 / 热水在北卫主管上三通，和西卫马桶管同一格搁栅（北墙下那一格）往前进西卫后墙假墙（只开这一格地板），在淋浴段假墙内竖上到明装恒温淋浴阀（离地约 1050），马桶给水在马桶段假墙内；不得为走管抬高地面。详见 P-08。",
]
NOTES_DRAIN = [
    "说明 Notes",
    "1. 新设 2 根 110 污水立管：S1 后墙外（伸顶通气；二层用 110 转角双支管（92.5°）：北卫马桶直穿后墙接正口、西卫接侧口，boss 口接北卫 40 废水）；S2 室内暗装（二层卧室 4 墙角箱封 → 一层厨房楼梯后墙角箱封 → 地坪下，顶部 AAV）。前面的 S3 已取消。",
    "[FF]2. 西卫马桶管（方案 A）：搁栅前后方向（业主确认）。马桶 110 出水口进马桶段假墙，在假墙内下到楼板（完成面下约 150），落进马桶下那一格搁栅直着往后，到后墙内侧借梁的位置横走到 S1 旁再出墙进 S1，墙外不走横管；全长约 7.6 m，坡度 1:40，起点 AAV 在假墙内。楼板约 590 深（二层前部完成面 3.208，一层天花顶 2.62），到后墙时管底仍高出一层天花约 190 mm，楼板里放得下。" if VARIANT == "A" else
    "[FF]2. 西卫马桶管（方案 B，2026-10-08 定为正式，取代方案 A）：马桶 110 后出水进后墙假墙，在假墙内、地面以上沿墙按 1:40 走到北墙角（约 1.1 m，起点 AAV 在马桶段检修口内），在北墙角下到楼板，落进北墙下那一格搁栅，在搁栅之间直着往后约 5.7 m（1:40），穿后墙进 S1 侧口；墙外不走长横管。后墙假墙尽量薄，能借后面原墙的位置就借，尽量保留卫生间内空（厚度由施工方现场定，本图只标点位和走向）。盥洗室台盆 40 在同一格搁栅里侧接马桶管；淋浴墙排地漏在假墙内接北墙角落管侧口。到后墙时管底仍高出一层天花约 180 mm。",

    "[FF]3. ★ 西卫（主卧卫生间）地面一律不抬高：淋浴盘、马桶都直接坐在原楼板完成面上，不做台阶、不垫高。后墙做假墙（尽量薄，能借后面原墙的位置就借，尽量保留卫生间内空）：马桶段 1100 高，顶面做置物平台（内放 110 横管起点 + AAV，留检修口）；淋浴段做到天花，内走 110 横管，墙面做两个壁龛（宽 300，离地 850–1750，深 80，中间一块隔板），中间装明装恒温淋浴。淋浴墙排地漏装在假墙内，40 废水在假墙内、地面以上接北墙角 110 落管侧口。所有排水管只走假墙内或楼板内，不得为排水抬高地面。详见 P-08。",
    "4. S2 箱封：一层厨房楼梯后墙角、二层卧室 4 墙角各一个 200 × 200 箱封（二层高 1200，顶部 AAV，带检修门）；一层箱封到天花，底部留检修口。",
    "5. 台盆 32 mm（≤ 1.7 m，否则 40）；淋浴 / 洗碗机 / 洗衣 40；废水单独接立管（strap-on boss），一层台盆接马桶支管。",
    "6. 存水弯水封 ≥ 75 mm；转弯处留清扫口。地下排水 110 PVC-U ≥ 1:40，碎石垫层；IC1 / IC2 / IC4 为 450 塑料检查井，只在检查井处转向。",
    "[GF]7. 一层卫生间马桶 / 台盆先进 IC1，和 S1 汇合后一根管去后院 MH；全屋污水 / 废水都进后院 MH（前院不用检查井）。最远点洗衣房 → MH 约 11 m，MH 管底须比洗衣房起点深 ≥ 0.28 m（施工前量）。本图不含雨水。",
]


# ---------------- drawing ----------------
CSS = BASE_CSS + """
.lbl{fill:#222}.lblb{fill:#fff;opacity:.85}.fix{fill:#fff;stroke:#333;stroke-width:.2}.eq{fill:#fff6d8;stroke:#7a5b00;stroke-width:.3}
.stk{fill:#6b3e1e}.stkr{fill:#fff;stroke:#6b3e1e;stroke-width:.5}.ic{fill:#fff;stroke:#6b3e1e;stroke-width:.4}.gl{fill:#fff;stroke:#c77d1a;stroke-width:.35}
.valve{fill:#fff;stroke:#111;stroke-width:.25}
"""


def bounds(F):
    return ((-4.6, 4.6), (-1.0, 17.2)) if F == "GF" else ((-4.6, 4.6), (-0.6, 12.2))


def pipe(s, kind, pts, size, tag=None, flip=False):
    col, w, dash, _ = STYLE[kind]
    d = "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in (s.P(*p) for p in pts))
    s.add(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{w}" stroke-dasharray="{dash}" stroke-linejoin="round"/>')
    segs = list(zip(pts, pts[1:]))
    a, b = max(segs, key=lambda e: math.dist(*e))
    mx, my = s.P((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    horiz = abs(a[1] - b[1]) > abs(a[0] - b[0])
    other = (kind == "waste") != flip               # waste labels on the other side of the line
    al = 7.0 if kind == "hot" else 0.0              # hot runs beside the cold one: shift its label along the line instead
    dx, dy = ((al, 2.9) if other else (al, -1.6)) if horiz else ((-1.6, al) if other else (1.6, al))
    if size and math.dist(a, b) >= 0.45:
        s.add(f'<text x="{mx+dx:.2f}" y="{my+dy:.2f}" font-size="1.8" fill="{col}" text-anchor="{"middle" if horiz else ("end" if other else "start")}">Ø{size}</text>')
    if tag:
        t2 = other or kind == "hot"
        tx, ty = ((mx + 5 + al, my) if t2 else (mx - 5, my)) if horiz else ((mx, my + 4 + al) if t2 else (mx, my - 4))
        s.add(f'<circle cx="{tx:.2f}" cy="{ty:.2f}" r="1.7" fill="#fff" stroke="{col}" stroke-width=".3"/><text x="{tx:.2f}" y="{ty+0.7:.2f}" font-size="1.9" text-anchor="middle" fill="{col}" font-weight="bold">{tag}</text>')


def legend(s, kinds, x=300, y=36):
    s.add(f'<rect x="{x-3}" y="{y-5}" width="112" height="{6+5*len(kinds)+24}" fill="#fff" stroke="#999" stroke-width=".2"/>')
    s.add(f'<text x="{x}" y="{y}" font-size="2.6" font-weight="bold">图例 Legend</text>')
    for i, k in enumerate(kinds):
        col, w, dash, txt = STYLE[k]; yy = y + 5 + i * 5
        s.add(f'<line x1="{x}" y1="{yy}" x2="{x+12}" y2="{yy}" stroke="{col}" stroke-width="{w}" stroke-dasharray="{dash}"/><text x="{x+15}" y="{yy+0.8}" font-size="2.2">{html.escape(txt)}</text>')
    yy = y + 5 + len(kinds) * 5
    s.add(f'<rect x="{x}" y="{yy-1.6}" width="3" height="3" class="fix"/><text x="{x+15}" y="{yy+0.8}" font-size="2.2">用水点 Fixture（S 软冷 / H 热 / C 冷 / P 净水）</text>')
    s.add(f'<path d="M{x} {yy+3.4} l3 2 v-2 l-3 2 z" class="valve"/><text x="{x+15}" y="{yy+5.6}" font-size="2.2">阀门 Valve（总阀 / 隔离阀）</text>')
    s.add(f'<circle cx="{x+1.5}" cy="{yy+10}" r="1.6" class="stk"/><text x="{x+15}" y="{yy+10.8}" font-size="2.2">污水立管 Soil stack 110（伸顶通气）</text>')
    s.add(f'<rect x="{x}" y="{yy+13.4}" width="3.2" height="3.2" class="ic"/><text x="{x+15}" y="{yy+15.8}" font-size="2.2">检查井 IC / 回水井 Gully</text>')


EQ_OFF = {"BLR": (0, -5.2), "SOFT": (6.2, 0), "R1": (-3.8, 0)}


def fixtures(s, F, equip=True):
    for fid, (fl, x, y, name, sup, (dk, ds)) in FIX.items():
        if fl != F: continue
        px, py = s.P(x, y)
        s.add(f'<rect x="{px-1.6:.2f}" y="{py-1.6:.2f}" width="3.2" height="3.2" class="fix"/>'
              f'<text x="{px:.2f}" y="{py+4.4:.2f}" font-size="2" text-anchor="middle" font-weight="bold" class="lbl">{CODE[fid]}</text>')
    for eid, fl, x, y, w, d, txt in EQUIP:
        if fl != F or not equip: continue
        px, py = s.P(x, y)
        s.add(f'<rect x="{px-d*MM/2:.2f}" y="{py-w*MM/2:.2f}" width="{d*MM:.2f}" height="{w*MM:.2f}" class="eq"/>'
              f'<text x="{px+EQ_OFF.get(eid, (0, 0))[0]:.2f}" y="{py+0.8+EQ_OFF.get(eid, (0, 0))[1]:.2f}" font-size="1.8" text-anchor="middle" font-weight="bold">{eid}</text>')


def setting_out(F):
    """items with distances from the east wall inner face (x = 4.29) and the front wall inner face (y = 0.20), mm"""
    rows = []
    for eid, fl, x, y, w, d, txt in EQUIP:
        if fl == F: rows.append([eid, txt.split("（")[0], round((4.29 - x) * 1000), round((y - 0.20) * 1000)])
    for sid, x, y, txt in STACKS:
        rows.append([sid, "污水立管 110 Soil stack", round((4.29 - x) * 1000), round((y - 0.20) * 1000)])
    if F == "GF":
        for cid, x, y, txt in CHAMBERS + GULLIES:
            rows.append([cid, txt, round((4.29 - x) * 1000), round((y - 0.20) * 1000)])
    return rows


def valves(s, F):
    V = {"GF": [(4.00, 3.25), (4.00, 8.05), (1.85, 8.30), (3.58, 16.25), (3.80, 16.28), (-4.20, 2.00), (1.54, 8.40)], "FF": []}
    for x, y in V[F]:
        px, py = s.P(x, y)
        s.add(f'<path d="M{px-1.5:.2f} {py-1:.2f} L{px+1.5:.2f} {py+1:.2f} L{px+1.5:.2f} {py-1:.2f} L{px-1.5:.2f} {py+1:.2f} Z" class="valve"/>')


S2_BOX = (4.09, 4.29, 8.20, 8.40)          # 200 × 200 box-in round S2 (both floors, model v42)
# 西卫后墙假墙 (model v42, FF front floor 3.208): shower part 100 thick to the ceiling, WC part 160 thick × 1100 with a shelf top
# 方案 B: the 110 runs inside the shower part too, so the whole false wall is as thin as the 110 allows — drawn 160 (max), face y = 2.37
WB_FACE = 2.37 if VARIANT == "B" else 2.43  # bathroom face of the shower-part false wall
WB_SHOWER_WALL = (-0.61, 0.50, WB_FACE, 2.53)
WB_WC_WALL = (0.50, 1.07, 2.37, 2.53)
WB_NICHES = [(-0.52, -0.22), (0.08, 0.38)]  # x ranges, 80 deep, 850–1750 above floor, shelf at 1288–1312
NICHE_Y = (WB_FACE, WB_FACE + 0.08)
WB_DROP = (-0.31, 2.45)                     # 方案 B: 110 drops into the joist bay under the north wall here
WB_DRAIN = (-0.45, 0.15)                    # wall-drain grate (x), 600 wide at the foot of the shower wall
WB_AAV = (0.79, 2.45)


def rect(s, x0, x1, y0, y1, style):
    s.poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], closed=True, style=style)


def leader(s, pts, txt=None, size=1.9, anchor="start", col="#b00020"):
    """leader from a plan point to page-mm text position: pts = [(x, y) Blender, (px, py) page...]"""
    a = s.P(*pts[0]); rest = pts[1:]
    s.add(f'<circle cx="{a[0]:.2f}" cy="{a[1]:.2f}" r=".45" fill="{col}"/><path d="M{a[0]:.2f} {a[1]:.2f} ' + " ".join(f"L{x:.2f} {y:.2f}" for x, y in rest)
          + f'" fill="none" stroke="{col}" stroke-width=".22"/>')
    if txt:
        x, y = rest[-1]
        s.add(f'<text x="{x + (0.8 if anchor == "start" else -0.8):.2f}" y="{y + 0.7:.2f}" font-size="{size}" fill="{col}" text-anchor="{anchor}">{html.escape(txt)}</text>')


def west_bath_plan(s):
    """P-04: the west-bath false walls / niches / wall drain drawn to scale + the 'no raised floor' callout"""
    rect(s, *WB_SHOWER_WALL, "fill:#f3e3c3;stroke:#a07a3a;stroke-width:.25")
    rect(s, *WB_WC_WALL, "fill:#e9d2a6;stroke:#a07a3a;stroke-width:.25")
    for x0, x1 in WB_NICHES:
        rect(s, x0, x1, *NICHE_Y, "fill:#fff;stroke:#a07a3a;stroke-width:.18;stroke-dasharray:.6 .4")
    s.poly([(WB_DRAIN[0], WB_FACE - 0.01), (WB_DRAIN[1], WB_FACE - 0.01)], style="stroke:#c77d1a;stroke-width:.7;fill:none")
    px, py = s.P(*WB_AAV)
    s.add(f'<circle cx="{px:.2f}" cy="{py:.2f}" r=".9" fill="#fff" stroke="#6b3e1e" stroke-width=".3"/>')
    # callout box in the (empty) master bedroom, leaders to the false walls
    bx, by, bw = 20.0, 70.0, 74.0
    lines = ["西卫（主卧卫生间）：地面不抬高 —— 详见 P-08",
             "• 淋浴盘、马桶直接坐原楼板完成面，不做台阶 / 不垫高",
             "• 马桶后：假墙 160 厚 × 1100 高，顶面置物平台；",
             "　 内放 110 落管 + AAV，留检修口",
             "• 淋浴后：假墙 100 厚到天花，两个壁龛 300 宽，",
             "　 离地 850–1750，深 80，中间隔板；中间明装恒温淋浴",
             "• 墙排地漏在假墙内；排水只走假墙内 / 楼板内"] if VARIANT == "A" else \
            ["西卫（主卧卫生间）：地面不抬高 —— 详见 P-08",
             "• 淋浴盘、马桶直接坐原楼板完成面，不做台阶 / 不垫高",
             "• 后墙假墙尽量薄，能借原墙就借：马桶段 1100 高，平台",
             "　 （AAV + 检修口）；淋浴段到天花，两个壁龛 300 宽，",
             "　 离地 850–1750，深 80，中间隔板；中间明装恒温淋浴",
             "• 110 马桶管（方案 B）：假墙内、地面以上 1:40 走到",
             "　 北墙角，下到楼板，沿北墙下那一格搁栅往后进 S1",
             "• 墙排地漏在假墙内，接北墙角落管；排水只走假墙 / 楼板内"]
    h = 3.0 * len(lines) + 2.5
    s.add(f'<rect x="{bx}" y="{by}" width="{bw}" height="{h:.1f}" fill="#fff" stroke="#b00020" stroke-width=".35"/>')
    for i, t in enumerate(lines):
        s.add(f'<text x="{bx+1.5}" y="{by+3.6+i*3.0:.1f}" font-size="{2.1 if i == 0 else 1.85}" fill="{"#b00020" if i == 0 else "#222"}"{BOLD_ if i == 0 else ""}>{html.escape(t)}</text>')
    for x, y in ((0.78, 2.45), WB_DROP if VARIANT == "B" else (-0.07, 2.48)):
        a = s.P(x, y)
        s.add(f'<path d="M{bx+bw:.2f} {by+h/2:.2f} L{a[0]:.2f} {a[1]:.2f}" stroke="#b00020" stroke-width=".22" fill="none"/><circle cx="{a[0]:.2f}" cy="{a[1]:.2f}" r=".45" fill="#b00020"/>')


def drainage_marks(s, F):
    for sid, x, y, txt in STACKS:
        px, py = s.P(x, y)
        s.add(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="2.2" class="stk"/><text x="{px:.2f}" y="{py+0.8:.2f}" font-size="2" fill="#fff" text-anchor="middle" font-weight="bold">{sid}</text>')
        if sid == "S2":
            rect(s, *S2_BOX, "fill:none;stroke:#111;stroke-width:.35;stroke-dasharray:.8 .4")
    if F != "GF":
        west_bath_plan(s)
        a = s.P(-0.85, 8.26); s.add(f'<text x="{a[0]+3:.2f}" y="{a[1]-3:.2f}" font-size="2.0" class="lbl">S1 110（后墙外）：北卫 + 西卫 / 盥洗室 → IC1 → MH</text>')
        leader(s, [(4.29, 8.40), (s.P(4.29, 8.40)[0] + 6, s.P(4.29, 8.40)[1] + 6)], "S2 箱封 200×200（高 1200，顶部 AAV + 检修门）", 1.9, col="#6b3e1e")
        return
    leader(s, [(4.29, 8.40), (s.P(4.29, 8.40)[0] + 5, s.P(4.29, 8.40)[1] + 5)], "S2 箱封 200×200（厨房楼梯后墙角，到天花，底部检修口）", 1.9, col="#6b3e1e")
    for cid, x, y, txt in CHAMBERS:
        px, py = s.P(x, y)
        s.add(f'<rect x="{px-2.2:.2f}" y="{py-2.2:.2f}" width="4.4" height="4.4" class="ic"/><text x="{px+3:.2f}" y="{py+3.8:.2f}" font-size="2.1" class="lbl">{html.escape(txt)}</text>')
    for gid, x, y, txt in GULLIES:
        px, py = s.P(x, y)
        s.add(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="1.8" class="gl"/><text x="{px+2.6:.2f}" y="{py-2.2:.2f}" font-size="2.1" class="lbl">{html.escape(txt)}</text>')



def floor_notes(notes, F):
    """drop the items tagged for the other floor ([GF] / [FF]) and renumber 1, 2, 3 …"""
    out, n = [], 0
    for t in notes:
        m = re.match(r"\[(GF|FF)\]", t)
        if m and m.group(1) != F: continue
        t = t[m.end():] if m else t
        if re.match(r"\d+\. ", t):
            n += 1; t = re.sub(r"^\d+\. ", f"{n}. ", t)
        out.append(t)
    return out


def plan_sheet(F, which, number):
    from plan_base import table
    fl = "一层 GF" if F == "GF" else "二层 FF"
    title = f"{fl} {'给水平面图 Water supply' if which == 'supply' else '排水平面图 Drainage'}"
    s = Sheet(title, number, F, bounds(F), discipline="给排水 Plumbing & drainage")
    s.base_plan(F)
    kinds = ["mdpe", "hard", "yard", "soft", "hot", "pure"] if which == "supply" else ["soil", "waste", "ug"]
    runs = []
    for fl_, kind, size, pts, label in PIPES:
        if fl_ == F and kind in kinds:
            tag = None
            if label:
                runs.append([len(runs) + 1, SHORT[kind], f"Ø{size}", label]); tag = len(runs)
            pipe(s, kind, pts, size, tag, flip=label.startswith("110 后卫马桶"))
    fixtures(s, F, which == "supply")
    if which == "supply": valves(s, F)
    else: drainage_marks(s, F)
    legend(s, [k for k in kinds if F == "GF" or k not in ("mdpe", "pure", "ug", "yard")], x=168, y=219)
    table(s, 14, 214, [("No.", 7), ("介质", 15), ("管径", 9), ("走向 / 说明 Route", 117)], runs, fs=1.85, title="管段表 Pipe schedule（图中圆圈编号）")
    fx = [[CODE[k], v[3], v[4] if which == "supply" else (f"{v[5][0]} Ø{v[5][1]}" if v[5][1] else "车道排水")] for k, v in FIX.items() if v[0] == F]
    y = table(s, 300, 32, [("编号", 10), ("用水点 Fixture", 70), ("给水" if which == "supply" else "排水", 18)], fx, fs=1.85,
              title="用水点 Fixtures（S 软冷 H 热 C 冷 P 净水）" if which == "supply" else "用水点 Fixtures")
    table(s, 300, y + 6, [("项", 10), ("名称", 58), ("距东墙 E", 15), ("距前墙 F", 15)], setting_out(F), fs=1.85,
          title="定位 Setting out（mm，自东墙内皮 / 前墙内皮）")
    s.frame(floor_notes(NOTES_SUPPLY if which == "supply" else NOTES_DRAIN, F))
    return s


def schematic_sheet():
    """P-05: water supply schematic + drainage stack diagram (not to scale)."""
    s = Sheet("给水系统图 + 排水系统图 Schematics（示意，不按比例）", "P-05", "", ((0, 1), (0, 1)), scale_note="NTS", discipline="给排水 Plumbing & drainage")
    A = s.add
    def box(x, y, w, h, t, cls="eq", fs=2.4):
        A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}" rx="1"/><text x="{x+w/2}" y="{y+h/2+0.9}" font-size="{fs}" text-anchor="middle">{html.escape(t)}</text>')
    def ln(pts, kind, label=""):
        col, w, dash, _ = STYLE[kind]
        A('<path d="M' + " L".join(f"{a} {b}" for a, b in pts) + f'" fill="none" stroke="{col}" stroke-width="{w}" stroke-dasharray="{dash}"/>')
        if label:
            (a, b), (c, d) = pts[-2], pts[-1]
            A(f'<text x="{c-1.5}" y="{d-1}" font-size="2.1" fill="{col}" text-anchor="end">{html.escape(label)}</text>')
    A('<text x="16" y="30" font-size="3.4" font-weight="bold">① 给水系统图 Water supply schematic</text>')
    box(16, 40, 34, 9, "自来水进户 MDPE 25", "fix"); ln([(50, 44.5), (66, 44.5)], "mdpe")
    box(66, 38, 40, 13, "楼梯下：总阀 + 泄水阀 + DCV"); ln([(106, 44.5), (122, 44.5)], "hard", "22")
    A('<circle cx="124" cy="44.5" r="1.4" fill="#1b3a8a"/>')
    ln([(124, 44.5), (124, 66), (140, 66)], "hard", "15 硬水"); box(140, 60, 44, 12, "户外水斗（DCV、防冻）", "fix")
    ln([(114, 44.5), (114, 100), (140, 100)], "hard", "15 硬水"); box(140, 94, 60, 12, "门口洗车龙头 FT（充电桩旁，DCV、防冻）", "fix", 2.2)
    ln([(124, 66), (124, 84), (140, 84)], "yard", "20 MDPE"); box(140, 78, 60, 12, "后花园水池补水 TU + 花园龙头（AB 空气隔断）", "fix", 2.2)
    ln([(124, 44.5), (140, 44.5)], "hard", "22")
    ln([(140, 44.5), (160, 44.5)], "hard", "22"); box(160, 38, 44, 13, "G24 软水机（三阀旁通）")
    ln([(204, 44.5), (220, 44.5)], "soft", "22 软水"); A('<circle cx="222" cy="44.5" r="1.4" fill="#2aa7d6"/>')
    ln([(222, 44.5), (222, 58), (236, 58)], "soft", "22"); box(236, 52, 40, 13, "G23 Vaillant combi 锅炉")
    ln([(276, 58.5), (290, 58.5)], "hot", "22 热")
    rows = [("一层卫生间 马桶 / 台盆", "S H"), ("岛台水槽（冷 / 热）+ RO 净水器 → 饮用龙头", "S H"), ("洗碗机", "S"), ("洗衣柜", "S H"),
            ("R1 ↑ 二层 后卫 马桶 / 台盆 / 淋浴", "S H"), ("R1 ↑ 二层 北卫 马桶 / 台盆 / 淋浴", "S H"), ("R1 ↑ 二层 西卫 / 盥洗室", "S H")]
    for i, (t, k) in enumerate(rows):
        y = 74 + i * 9
        ln([(222, 44.5 if i == 0 else 74 + (i - 1) * 9), (222, y), (300, y)], "soft")
        if "H" in k: ln([(292, 58.5 if i == 0 else 76 + (i - 1) * 9), (292, y + 2), (300, y + 2)], "hot")
        box(300, y - 3, 92, 7, t + "（" + k + "）", "fix", 2.2)
    A('<text x="16" y="150" font-size="3.4" font-weight="bold">② 排水系统图 Drainage (stacks)</text>')
    for i, (sid, serves, items) in enumerate((("S1", "后墙外 · 伸顶通气", ["二层 北卫：马桶 110（直穿后墙）/ 淋浴 40 / 台盆 40", "二层 西卫：马桶 110 + 淋浴 40（双支管右口）", "二层 盥洗室：台盆柜 40（经西卫支管）"]),
                                              ("S2", "室内暗装 · 200×200 箱封 · 顶部 AAV，不伸顶", ["二层 后卫：马桶 110 / 淋浴 + 台盆 40"]))):
        x = 40 + i * 120
        A(f'<line x1="{x}" y1="160" x2="{x}" y2="246" stroke="#6b3e1e" stroke-width="2"/><text x="{x}" y="157" font-size="2.6" text-anchor="middle" font-weight="bold">{sid} 110（{serves}）</text>')
        A(f'<line x1="{x-60}" y1="200" x2="{x+60}" y2="200" stroke="#bbb" stroke-width=".3" stroke-dasharray="2 1"/><text x="{x+58}" y="198.5" font-size="2" text-anchor="end" fill="#888">二层楼板 FF</text>')
        for j, t in enumerate(items):
            A(f'<line x1="{x}" y1="{182+j*6}" x2="{x+12}" y2="{182+j*6}" stroke="#6b3e1e" stroke-width="1"/><text x="{x+14}" y="{183+j*6}" font-size="2.2">{html.escape(t)}</text>')
        ic = {"S1": "IC1 → MH（一层马桶 / 台盆也先进 IC1）", "S2": "地坪下管 → IC4 → IC1 → MH（IC2 收 G2 厨房 + 洗衣房 / 户外水斗 50 废水）"}[sid]
        A(f'<rect x="{x-4}" y="246" width="8" height="6" class="ic"/><text x="{x}" y="258" font-size="2.2" text-anchor="middle">{html.escape(ic)}</text>')
    A('<text x="16" y="268" font-size="2.3" fill="#333">排水坡度：马桶支管 1:40；废水 ≥ 1:40（≤ 1:110 不允许）；地下 110 ≥ 1:40。所有立管底部用大弯头（大半径 bend），首个接口距弯头底 ≥ 450 mm。</text>')
    s.frame()
    return s


def detail_sheet():
    """P-06: boiler + softener valve set, and the purifier under the kitchen sink (elevations, NTS)."""
    s = Sheet("设备详图 Details：锅炉 + 软水机 · 厨房水槽下净水器（示意）", "P-06", "", ((0, 1), (0, 1)), scale_note="NTS", discipline="给排水 Plumbing & drainage")
    A = s.add
    def box(x, y, w, h, t, cls="eq", fs=2.4):
        A(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}" rx="1"/><text x="{x+w/2}" y="{y+h/2+0.9}" font-size="{fs}" text-anchor="middle">{html.escape(t)}</text>')
    def ln(pts, kind):
        col, w, dash, _ = STYLE[kind]
        A('<path d="M' + " L".join(f"{a} {b}" for a, b in pts) + f'" fill="none" stroke="{col}" stroke-width="{w}" stroke-dasharray="{dash}"/>')
    def v(x, y):
        A(f'<path d="M{x-1.6} {y-1.1} L{x+1.6} {y+1.1} L{x+1.6} {y-1.1} L{x-1.6} {y+1.1} Z" class="valve"/>')
    # ① boiler + softener elevation (floor at y=240, 1 mm = 10 mm real)
    A('<text x="16" y="30" font-size="3.4" font-weight="bold">① 锅炉 G23 + 软水机 G24 立面（厨房后墙，示意 1:10）</text>')
    A('<line x1="20" y1="240" x2="190" y2="240" stroke="#333" stroke-width=".6"/><text x="22" y="244" font-size="2.2">完成地面 FFL</text>')
    box(80, 43, 44, 72, "G23 Vaillant combi 440×720", "eq", 2.6)
    A('<text x="126" y="121" font-size="2">底部离地约 1250（与现场核对检修空间）</text>')
    box(86, 186, 32, 54, "G24 软水机 320×535", "eq", 2.4)
    ln([(30, 225), (70, 225), (70, 200), (86, 200)], "hard"); v(60, 225); A('<text x="30" y="222" font-size="2.1" fill="#1b3a8a">22 硬水进（来自总阀）</text>')
    ln([(70, 200), (70, 175), (140, 175), (140, 200), (118, 200)], "hard"); v(105, 175); A('<text x="96" y="172" font-size="2.1">旁通阀 Bypass（平时关）</text>')
    v(78, 200); v(128, 200)
    ln([(140, 175), (140, 160), (110, 160), (110, 115)], "soft"); A('<text x="142" y="157" font-size="2.1" fill="#2aa7d6">22 软水 → 锅炉冷水进 + 全屋冷水（用户分支）</text>')
    ln([(140, 160), (175, 160)], "soft")
    ln([(94, 115), (94, 135), (175, 135)], "hot"); A('<text x="150" y="132" font-size="2.1" fill="#d62828">22 热水出 → 全屋</text>')
    ln([(70, 225), (40, 225), (40, 70), (30, 70)], "hard"); A('<text x="22" y="66" font-size="2.1" fill="#1b3a8a">15 硬水 → 户外水斗 / 水池补水（在软水机前分出）</text>')
    A('<path d="M118 232 L150 232 L150 240" fill="none" stroke="#c77d1a" stroke-width=".6" stroke-dasharray="1 1"/><text x="152" y="236" font-size="2.1" fill="#c77d1a">再生排水 + 溢流 → 废水（空气隔断 Type A/AA）</text>')
    A('<text x="20" y="252" font-size="2.2">要点：软水机前装 DCV；三阀旁通便于检修；锅炉冷水进前加隔离阀；锅炉安全阀 / 冷凝水管按 Vaillant 说明书接入废水（冷凝水 22 mm，坡度 ≥ 2.5°）。</text>')
    # ② purifier under the sink
    A('<text x="216" y="30" font-size="3.4" font-weight="bold">② 厨房岛台水槽下 RO 净水器（示意）</text>')
    A('<rect x="220" y="60" width="160" height="6" fill="#ddd" stroke="#888" stroke-width=".3"/><text x="300" y="58" font-size="2.2" text-anchor="middle">台面 Worktop ≈ 900</text>')
    A('<rect x="230" y="66" width="140" height="174" fill="none" stroke="#888" stroke-width=".3" stroke-dasharray="2 1"/><text x="300" y="246" font-size="2.2" text-anchor="middle">水槽柜（≥ 600 宽，内部净高 ≥ 700，现场确认）</text>')
    box(290, 66, 50, 18, "水槽 Sink", "fix")
    A('<line x1="262" y1="60" x2="262" y2="44" stroke="#555" stroke-width=".8"/><text x="262" y="41" font-size="2.1" text-anchor="middle">混水龙头（软冷 + 热）</text>')
    A('<line x1="352" y1="60" x2="352" y2="44" stroke="#7b3fb5" stroke-width=".8"/><text x="352" y="41" font-size="2.1" text-anchor="middle" fill="#7b3fb5">饮用水龙头</text>')
    box(236, 150, 36, 70, "RO 主机", "eq"); box(280, 170, 28, 50, "压力桶", "eq")
    ln([(226, 230), (226, 200), (236, 200)], "soft"); v(229, 214); A('<text x="210" y="236" font-size="2.1" fill="#2aa7d6">15 软水（水槽冷水三通）</text>')
    ln([(272, 160), (352, 160), (352, 66)], "pure"); ln([(272, 195), (280, 195)], "pure")
    ln([(244, 240), (244, 236)], "soft"); ln([(256, 240), (256, 236)], "hot")
    A('<path d="M262 150 L262 110 L300 110 L300 84" fill="none" stroke="#c77d1a" stroke-width=".6"/><text x="304" y="110" font-size="2.1" fill="#c77d1a">RO 浓水 → 排水卡箍（drain saddle）</text>')
    A('<path d="M300 84 L300 128 L330 128 L330 240" fill="none" stroke="#c77d1a" stroke-width=".8"/><text x="333" y="200" font-size="2.1" fill="#c77d1a">40 废水（地坪预埋 → G2）</text>')
    A('<text x="216" y="251" font-size="2.2">要点：净水器、压力桶留检修空间；13A 插座（若带增压泵）装在柜内高处；洗碗机排水接水槽存水弯侧口。</text>')
    s.frame()
    return s


def west_bath_sheet():
    """P-08: west bath (master en-suite) rear false wall — elevation, enlarged plan and section through the WC, 1:20.
    Geometry from model v42 (FF front finished floor 3.208, ceiling 5.70, GF ceiling top 2.62)."""
    from plan_base import walls
    s = Sheet("西卫后墙详图 West bath：地面不抬高 · 平台 · 壁龛 · 110 走北墙", "P-08", "", ((0, 1), (0, 1)), scale_note="1:20",
              discipline="给排水 Plumbing & drainage")
    A = s.add
    K = 50.0                                   # 1:20 -> 50 page mm per metre
    FFL, CEIL = 3.208, 5.70
    RED, BR, OR, NI = "#b00020", "#6b3e1e", "#c77d1a", "#7a5b00"
    WALL = "fill:#cfcfcf;stroke:#555;stroke-width:.25"
    FW_S = "fill:#f3e3c3;stroke:#a07a3a;stroke-width:.3"      # shower false wall
    FW_W = "fill:#e9d2a6;stroke:#a07a3a;stroke-width:.3"      # WC false wall
    SHELF = "fill:#b08850;stroke:#6d5022;stroke-width:.25"
    s.defs.append('<pattern id="slab" width="2" height="2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                  '<line x1="0" y1="0" x2="0" y2="2" stroke="#999" stroke-width=".25"/></pattern>')

    def R(x0, y0, x1, y1, st):
        A(f'<rect x="{min(x0,x1):.2f}" y="{min(y0,y1):.2f}" width="{abs(x1-x0):.2f}" height="{abs(y1-y0):.2f}" style="{st}"/>')

    def T(x, y, t, fs=2.1, anchor="start", col="#222", bold=False):
        A(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{fs}" text-anchor="{anchor}" fill="{col}"{BOLD_ if bold else ""}>{html.escape(t)}</text>')

    def L(pts, st):
        A('<path d="M' + " L".join(f"{a:.2f} {b:.2f}" for a, b in pts) + f'" style="fill:none;{st}"/>')

    def tick(x, y):
        L([(x - .8, y + .8), (x + .8, y - .8)], "stroke:#333;stroke-width:.3")

    def dim_h(x0, x1, y, t):
        L([(x0, y), (x1, y)], "stroke:#333;stroke-width:.18")
        for x in (x0, x1): L([(x, y - 1.2), (x, y + 1.2)], "stroke:#333;stroke-width:.18"); tick(x, y)
        T((x0 + x1) / 2, y - 0.8, t, 1.9, "middle")

    def dim_v(x, y0, y1, t, side=1):
        L([(x, y0), (x, y1)], "stroke:#333;stroke-width:.18")
        for y in (y0, y1): L([(x - 1.2, y), (x + 1.2, y)], "stroke:#333;stroke-width:.18"); tick(x, y)
        if t: T(x + 1.0 * side, (y0 + y1) / 2 + 0.7, t, 1.9, "start" if side > 0 else "end")

    def lab(px, py, tx, ty, t, col="#222"):
        L([(px, py), (tx - 0.5, ty)], f"stroke:{col};stroke-width:.2"); A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r=".4" fill="{col}"/>')
        T(tx, ty + 0.7, t, 1.85, "start", col)

    # ---------- ① elevation of the rear wall, seen from inside the bathroom (x to the right) ----------
    ex, ey = 48.0, 165.0
    X = lambda x: ex + (x + 0.61) * K
    Z = lambda z: ey - (z - FFL) * K
    EL = X(1.18) + 17                          # label column right of the elevation
    T(16, 30, "① 后墙立面 Elevation（站在卫生间里面朝后墙看）1:20", 3.2, bold=True)
    R(X(-0.72), Z(CEIL), X(-0.61), ey, WALL); R(X(1.07), Z(CEIL), X(1.18), ey, WALL)
    R(X(-0.61), Z(CEIL), X(0.50), ey, FW_S)
    R(X(0.50), Z(FFL + 1.10), X(1.07), ey, FW_W)
    R(X(0.50), Z(CEIL), X(1.07), Z(FFL + 1.12), "fill:#f7f7f7;stroke:#999;stroke-width:.2")
    R(X(0.50), Z(FFL + 1.12), X(1.07), Z(FFL + 1.10), SHELF)
    T(X(0.785), Z(FFL + 1.80), "原墙面", 1.9, "middle", "#888")
    for x0, x1 in WB_NICHES:
        R(X(x0), Z(FFL + 1.75), X(x1), Z(FFL + 0.85), "fill:#fff;stroke:#a07a3a;stroke-width:.35")
        R(X(x0), Z(FFL + 1.312), X(x1), Z(FFL + 1.288), "fill:#a07a3a")
    R(X(-0.27), Z(FFL + 1.08), X(0.13), Z(FFL + 1.02), "fill:#bbb;stroke:#333;stroke-width:.25")
    L([(X(-0.07), Z(FFL + 1.08)), (X(-0.07), Z(FFL + 2.02))], "stroke:#333;stroke-width:.6")
    A(f'<ellipse cx="{X(-0.07):.2f}" cy="{Z(FFL+1.975):.2f}" rx="{0.125*K:.2f}" ry="1.0" fill="#ddd" stroke="#333" stroke-width=".25"/>')
    R(X(-0.03), Z(FFL + 1.55), X(0.0), Z(FFL + 1.35), "fill:#888")
    R(X(WB_DRAIN[0]), Z(FFL + 0.06), X(WB_DRAIN[1]), Z(FFL + 0.005), "fill:#fff;stroke:" + OR + ";stroke-width:.4")
    dx = WB_DROP[0]                              # 方案 B: 110 runs along the wall (1:40) to the north corner and drops there
    L([(X(-0.15), Z(FFL + 0.03)), (X(-0.15), Z(FFL + 0.06)), (X(dx), Z(FFL + 0.06))], f"stroke:{OR};stroke-width:.6;stroke-dasharray:1.2 .6")
    L([(X(0.79), Z(FFL + 0.96)), (X(0.79), Z(FFL + 0.18)), (X(dx), Z(FFL + 0.153)), (X(dx), Z(FFL - 0.15))], f"stroke:{BR};stroke-width:1.4;stroke-dasharray:2 .8;stroke-linejoin:round")
    R(X(0.73), Z(FFL + 1.075), X(0.85), Z(FFL + 0.965), "fill:#fff;stroke:" + BR + ";stroke-width:.3")
    T(X(0.79), Z(FFL + 1.005), "AAV", 1.4, "middle", BR)
    R(X(0.64), Z(FFL + 1.09), X(0.94), Z(FFL + 0.79), "fill:none;stroke:#333;stroke-width:.25;stroke-dasharray:1 .5")
    L([(X(0.585), ey), (X(0.585), Z(FFL + 0.40)), (X(0.995), Z(FFL + 0.40)), (X(0.995), ey)], "stroke:#777;stroke-width:.25;stroke-dasharray:1 .6")
    T(X(0.79), Z(FFL + 0.30), "马桶（在前）", 1.7, "middle", "#777")
    R(X(-0.72), ey, X(1.18), ey + 7, "fill:url(#slab);stroke:#555;stroke-width:.25")
    L([(X(-0.85), ey), (X(1.30), ey)], f"stroke:{RED};stroke-width:.7")
    L([(X(-0.85), Z(CEIL)), (X(1.30), Z(CEIL))], "stroke:#555;stroke-width:.35")
    T(X(1.30), Z(CEIL) - 1, "天花（离地约 2490）", 1.9, "end")
    T(X(-0.72), ey + 11, "FFL ±0 = 原楼板完成面：淋浴盘、马桶都直接坐在上面", 2.1, "start", RED, True)
    T(X(-0.72), ey + 14.5, "地面不抬高、不做台阶、不垫高", 2.1, "start", RED, True)
    dim_h(X(-0.61), X(0.50), Z(CEIL) - 6, "淋浴段假墙 1110（尽量薄，到天花）")
    dim_h(X(0.50), X(1.07), Z(CEIL) - 6, "马桶段 570")
    dim_h(X(-0.52), X(-0.22), Z(FFL + 1.75) - 2.5, "300"); dim_h(X(0.08), X(0.38), Z(FFL + 1.75) - 2.5, "300")
    dim_v(X(-0.72) - 5, Z(FFL + 0.85), ey, "850", -1); dim_v(X(-0.72) - 5, Z(FFL + 1.75), Z(FFL + 0.85), "900", -1)
    dim_v(X(-0.72) - 13, Z(FFL + 1.75), ey, "1750", -1); dim_v(X(-0.72) - 13, Z(CEIL), Z(FFL + 1.75), "≈740", -1)
    dim_v(X(1.18) + 4, Z(FFL + 1.10), ey, "1100")
    lab(X(-0.37), Z(FFL + 1.62), EL, Z(FFL + 2.36), "壁龛 1：宽 300 × 高 900 × 深 80，离地 850–1750", NI)
    lab(X(0.30), Z(FFL + 1.62), EL, Z(FFL + 2.22), "壁龛 2：同尺寸；两个都有中间隔板（离地约 1300）", NI)
    lab(X(0.05), Z(FFL + 1.975), EL, Z(FFL + 2.08), "顶喷 Ø250，离地约 1975；滑杆 + 手持")
    lab(X(1.0), Z(FFL + 1.11), EL, Z(FFL + 1.58), "置物平台面 1100（深 180，挑出假墙 20）")
    lab(X(0.13), Z(FFL + 1.05), EL, Z(FFL + 1.42), "明装恒温淋浴杆阀，中心离地约 1050")
    lab(X(0.94), Z(FFL + 0.85), EL, Z(FFL + 0.98), "检修口 300×300（正对 AAV）")
    lab(X(0.30), Z(FFL + 0.175), EL, Z(FFL + 0.56), "110 横管：假墙内、地面以上沿墙 1:40 走到北墙角（约 1.1 m）", BR)
    lab(X(-0.24), Z(FFL + 0.06), EL, Z(FFL + 0.42), "40 废水：假墙内、地面以上接北墙角落管侧口", OR)
    lab(X(0.12), Z(FFL + 0.03), EL, Z(FFL + 0.26), "墙排地漏 600 宽（装在淋浴段假墙底部）", OR)
    lab(X(dx), Z(FFL - 0.10), EL, Z(FFL + 0.06), "110 落管：北墙角下到楼板，落进北墙下那一格搁栅 → 往后进 S1", BR)

    # ---------- ③ section A-A through the WC (x = 0.79), y horizontal ----------
    sx, sy = 232.0, 150.0
    Y2 = lambda y: sx + (y - 1.50) * K
    Z2 = lambda z: sy - (z - FFL) * K
    yR, zT = 3.30, 5.10                         # cut limits (break lines)
    SC = Y2(yR) + 13                           # label column
    T(220, 30, "③ 剖面 A-A Section（经过北墙角落管，x 同②中 A-A）1:20", 3.2, bold=True)
    R(Y2(1.50), Z2(2.62), Y2(yR), Z2(2.588), "fill:#ddd;stroke:#555;stroke-width:.2")
    R(Y2(1.50), Z2(FFL), Y2(yR), Z2(3.18), "fill:#c9b28a;stroke:#6d5022;stroke-width:.2")
    R(Y2(1.50), Z2(3.18), Y2(yR), Z2(2.62), "fill:#fbf6ea;stroke:#b9a27a;stroke-width:.2;stroke-dasharray:1.5 .8")
    T(Y2(1.95), Z2(2.80), "搁栅之间（北墙下那一格），搁栅不切、不开槽", 1.7, "middle", NI)
    R(Y2(2.53), Z2(zT), Y2(2.65), Z2(FFL), WALL)
    R(Y2(2.37), Z2(zT), Y2(2.53), Z2(FFL), FW_S)
    R(Y2(2.37), Z2(FFL + 1.75), Y2(2.45), Z2(FFL + 0.85), "fill:#fff;stroke:#a07a3a;stroke-width:.3")
    R(Y2(2.37), Z2(FFL + 1.312), Y2(2.45), Z2(FFL + 1.288), "fill:#a07a3a")
    R(Y2(1.50), Z2(FFL + 0.045), Y2(2.37), Z2(FFL), "fill:#e8f1f8;stroke:#2a7ab8;stroke-width:.25")
    T(Y2(1.90), Z2(FFL + 0.10), "淋浴盘（坐原楼板）", 1.7, "middle", "#2a7ab8")
    R(Y2(2.37), Z2(FFL + 0.06), Y2(2.42), Z2(FFL + 0.005), "fill:#fff;stroke:" + OR + ";stroke-width:.35")
    L([(Y2(2.42), Z2(FFL + 0.04)), (Y2(2.395), Z2(FFL + 0.04))], f"stroke:{OR};stroke-width:.5")
    zb = 2.998 - (yR - 2.62) / 40
    A(f'<circle cx="{Y2(2.45):.2f}" cy="{Z2(FFL + 0.153):.2f}" r="{0.055*K:.2f}" fill="#8a5a33" stroke="{BR}" stroke-width=".3" opacity=".85"/>')
    L([(Y2(2.45), Z2(FFL + 0.153)), (Y2(2.45), Z2(3.058)), (Y2(2.62), Z2(2.998)), (Y2(yR), Z2(zb))], f"stroke:{BR};stroke-width:{0.11*K:.2f};stroke-linejoin:round;opacity:.85")
    A(f'<circle cx="{Y2(2.45):.2f}" cy="{Z2(FFL + 0.04):.2f}" r="{0.02*K:.2f}" fill="#fff" stroke="{OR}" stroke-width=".4"/>')
    L([(Y2(yR), Z2(2.55)), (Y2(yR) - 1.5, Z2(2.75)), (Y2(yR) + 1.5, Z2(2.95)), (Y2(yR), Z2(3.30))], "stroke:#333;stroke-width:.25")
    L([(Y2(2.45), Z2(zT)), (Y2(2.55), Z2(zT) - 1.2), (Y2(2.63), Z2(zT) + 1.2), (Y2(2.72), Z2(zT))], "stroke:#333;stroke-width:.25")
    L([(Y2(1.40), Z2(FFL)), (Y2(yR) + 4, Z2(FFL))], f"stroke:{RED};stroke-width:.7")
    T(Y2(1.40), Z2(FFL) - 1.2, "FFL ±0 原楼板，不抬高", 2.0, "start", RED, True)
    dim_v(Y2(1.50) - 4, Z2(FFL), Z2(2.62), "楼板约 590", -1)
    dim_v(Y2(2.65) + 3, Z2(FFL + 0.153), Z2(FFL), "≈150")
    dim_v(Y2(2.65) + 3, Z2(FFL + 1.75), Z2(FFL + 0.85), "壁龛 850–1750")
    zbw = 2.998 - (8.30 - 2.62) / 40 - 0.055     # pipe invert-bottom at the rear wall
    T(Y2(1.50), Z2(2.588) + 4, "一层天花 GF ceiling（顶面 2.620）", 1.8)
    lab(Y2(2.41), Z2(FFL + 1.50), SC, Z2(4.62), "假墙尽量薄，能借原墙就借（厚度现场定）；壁龛深 80", NI)
    lab(Y2(2.47), Z2(FFL + 0.17), SC, Z2(3.85), "110 横管（自马桶，沿墙 1:40）到此转弯下落", BR)
    lab(Y2(2.40), Z2(FFL + 0.04), SC, Z2(3.55), "墙排地漏 → 40 侧接落管（地面以上）", OR)
    lab(Y2(3.0), Z2(2.998 - 0.38 / 40), SC, Z2(3.05), "110 · 1:40 → 北墙下那一格往后约 5.7 m → 穿后墙 → S1", BR)
    T(SC, Z2(4.30), "AAV 在马桶端（横管起点）检修口内，见①", 1.85, col=BR)
    T(SC, Z2(2.80), f"到后墙处管底离一层天花约 {round((zbw - 2.62) * 1000, -1):.0f} mm", 1.85, col=BR)

    # ---------- ② enlarged plan (same x as the elevation, back wall at the top) ----------
    py0 = 212.0                                  # page y of y = 2.53
    Y = lambda y: py0 + (2.53 - y) * K
    T(16, 188, "② 平面放大 Plan 1:20（上方 = 后墙）", 3.0, bold=True)
    s.defs.append(f'<clipPath id="wbp"><rect x="{X(-0.85):.2f}" y="{Y(2.70):.2f}" width="{(1.32+0.85)*K:.2f}" height="{(2.70-1.40)*K:.2f}"/></clipPath>')
    w, _ = walls("FF")
    A('<g clip-path="url(#wbp)">')
    for k in ("door", "wall"):
        for name, pts, closed in w.get(k, []):
            L([(X(x), Y(y)) for x, y in pts] + ([(X(pts[0][0]), Y(pts[0][1]))] if closed else []),
              "fill:#cfcfcf;stroke:#555;stroke-width:.25;fill-rule:evenodd" if k == "wall" else "fill:#eee;stroke:#999;stroke-width:.2")
    A('</g>')
    R(X(-0.61), Y(2.53), X(0.50), Y(WB_FACE), FW_S); R(X(0.50), Y(2.53), X(1.07), Y(2.37), FW_W)
    for x0, x1 in WB_NICHES: R(X(x0), Y(NICHE_Y[1]), X(x1), Y(NICHE_Y[0]), "fill:#fff;stroke:#a07a3a;stroke-width:.3;stroke-dasharray:.8 .4")
    R(X(-0.55), Y(WB_FACE - 0.01), X(0.25), Y(1.42), "fill:none;stroke:#2a7ab8;stroke-width:.3;stroke-dasharray:1.5 .8")
    T(X(-0.15), Y(1.80), "淋浴区", 1.9, "middle", "#2a7ab8"); T(X(-0.15), Y(1.72), "（淋浴盘坐原楼板）", 1.7, "middle", "#2a7ab8")
    R(X(WB_DRAIN[0]), Y(WB_FACE), X(WB_DRAIN[1]), Y(WB_FACE - 0.02), f"fill:{OR}")
    A(f'<rect x="{X(0.585):.2f}" y="{Y(2.33):.2f}" width="{0.41*K:.2f}" height="{0.20*K:.2f}" fill="#fff" stroke="#333" stroke-width=".25"/>'
      f'<ellipse cx="{X(0.79):.2f}" cy="{Y(1.90):.2f}" rx="{0.19*K:.2f}" ry="{0.24*K:.2f}" fill="#fff" stroke="#333" stroke-width=".25"/>')
    T(X(0.79), Y(1.86), "马桶 WC1", 1.7, "middle")
    L([(X(0.79), Y(2.18)), (X(0.79), Y(2.45)), (X(WB_DROP[0]), Y(2.45))], f"stroke:{BR};stroke-width:1.2;stroke-dasharray:2 .8;stroke-linejoin:round")
    A(f'<circle cx="{X(0.79):.2f}" cy="{Y(2.45):.2f}" r="{0.03*K:.2f}" fill="#fff" stroke="{BR}" stroke-width=".4"/>')
    A(f'<circle cx="{X(WB_DROP[0]):.2f}" cy="{Y(2.45):.2f}" r="{0.055*K:.2f}" fill="#fff" stroke="{BR}" stroke-width=".5"/>')
    L([(X(WB_DROP[0]), Y(2.45) - 2.8), (X(WB_DROP[0]), Y(2.70))], f"stroke:{BR};stroke-width:1.2;stroke-dasharray:2 .8")
    L([(X(-0.15), Y(2.38)), (X(-0.25), Y(2.43)), (X(WB_DROP[0]), Y(2.45))], f"stroke:{OR};stroke-width:.6;stroke-dasharray:1.2 .6")
    ax = X(WB_DROP[0])
    L([(ax, Y(2.68)), (ax, Y(1.45))], "stroke:#000;stroke-width:.3;stroke-dasharray:4 1 1 1")
    T(ax + 2, Y(2.66), "A", 2.4, "middle", "#000", True); T(ax + 2, Y(1.47), "A", 2.4, "middle", "#000", True)
    lab(X(0.23), Y(2.41), X(0.23) + 3, Y(2.82), "壁龛 300 × 深 80（淋浴段到天花）", NI)
    lab(X(0.79) + 2.8, Y(2.45), X(0.79) + 6, Y(2.92), "AAV + 检修口（马桶段假墙高 1100）", BR)
    lab(X(WB_DROP[0]) - 2.8, Y(2.45), X(-0.85), Y(2.78), "110 下落点（北墙角）→ 楼板内往后 → S1", BR)
    lab(X(0.40), Y(2.45), X(0.40) + 3, Y(2.20) + 1, "110 横管 1:40", BR)
    T(X(-0.85), Y(1.40) + 5, "FFL ±0 不抬高：整个卫生间地面保持原楼板标高，门口无台阶", 2.0, "start", RED, True)

    # ---------- ④ requirements + legend ----------
    nx, ny, nw = 166.0, 196.0, 242.0
    req = ["施工要求 Requirements（防止擅自抬高地面）",
           "1. 西卫（主卧卫生间）地面一律不抬高：保持原楼板完成面，淋浴盘、马桶直接坐在原楼板上；不做台阶、不垫高、不加找坡层。任何抬高地面的做法须业主书面同意。",
           "2. 后墙假墙尽量薄，能借后面原墙的位置就借，尽量保留卫生间内空；厚度由施工方现场定，本图只标点位和走向（图中厚度仅示意）。马桶段 1100 高（宽约 570），顶面做置物平台（深 180）；内放 110 横管起点 + AAV（AAV 顶离地约 1075，低于平台面），正对 AAV 留 300 × 300 检修口。",
           "3. 淋浴段假墙与马桶段同厚、做到天花（宽约 1110），110 横管从里面穿过；墙面做两个壁龛：宽 300 × 高 900（离地 850–1750）× 深 80，中间一块隔板（离地约 1300），壁龛底面向外找坡 ≥ 2%。",
           "4. 两个壁龛中间装明装恒温淋浴：杆阀中心离地约 1050，顶喷 Ø250 离地约 1975，带滑杆手持；冷热水在淋浴段假墙内竖上。",
           "5. 淋浴用墙排地漏（600 宽）装在淋浴段假墙底部；40 废水在假墙内、地面以上接北墙角 110 落管侧口（boss）。选定地漏型号后核对：地漏本体须在 110 横管下方（横管管底离地约 100）。",
           "6. 110 马桶管（方案 B）：马桶后出水进假墙，在假墙内、地面以上沿后墙按 1:40 走到北墙角（约 1.1 m），在北墙角下到楼板，落进北墙下那一格搁栅，在搁栅之间按 1:40 直着往后约 5.7 m，穿后墙进 S1；不得切断搁栅或开深槽。盥洗室台盆 40 在同一格搁栅内侧接。",
           "7. 淋浴区整面墙（含壁龛内）做防水层（tanking）；假墙用防潮板 + 金属龙骨或等效做法，接缝加防水带。",
           "8. 尺寸以本图和模型 v42 为准。现场与图不符时先停工、拍照联系业主，不得自行改成抬高地面的做法。"]
    lines = [(i, l) for i, n in enumerate(req) for l in (wrap(n, 108) if i else [n])]
    lh = 3.15
    h = lh * len(lines) + 3.5
    A(f'<rect x="{nx-2}" y="{ny-4.2}" width="{nw}" height="{h:.1f}" fill="#fff" stroke="{RED}" stroke-width=".5"/>')
    for j, (i, l) in enumerate(lines):
        T(nx, ny + j * lh, l, 2.4 if i == 0 else 2.05, "start", RED if i == 0 else "#222", i == 0)
    ly = ny + h + 2
    items = [("r", FW_S, "淋浴段假墙（尽量薄）到天花"), ("r", FW_W, "马桶段假墙 高 1100"), ("r", WALL, "原墙（剖切）"),
             ("r", "fill:url(#slab);stroke:#555;stroke-width:.25", "原楼板（不动）"),
             ("l", f"stroke:{BR};stroke-width:1.2", "110 污水"), ("l", f"stroke:{OR};stroke-width:.6;stroke-dasharray:1.2 .6", "40 废水"),
             ("l", f"stroke:{RED};stroke-width:.7", "FFL ±0（不抬高）")]
    for k, (t, st, txt) in enumerate(items):
        cx, cy = nx + (k % 4) * 33, ly + (k // 4) * 4.6
        if t == "r": R(cx, cy - 2.2, cx + 6, cy + 0.6, st)
        else: L([(cx, cy - 0.8), (cx + 6, cy - 0.8)], st)
        T(cx + 7.5, cy, txt, 1.9)
    s.frame()
    return s


BOLD_ = ' font-weight="bold"'


def cover_sheet():
    s = Sheet("给排水施工图 目录 + 设计说明 Index & design notes", "P-00", "", ((0, 1), (0, 1)), scale_note="—", discipline="给排水 Plumbing & drainage")
    A = s.add
    A('<text x="16" y="34" font-size="3.4" font-weight="bold">图纸目录 Drawing list</text>')
    for i, t in enumerate(["P-00 目录 + 设计说明", "P-01 一层给水平面图", "P-02 二层给水平面图", "P-03 一层排水平面图（含地下排水）",
                           "P-04 二层排水平面图（西卫马桶管：方案 B 走北墙）", "P-05 给水系统图 + 排水系统图", "P-06 设备详图：锅炉 + 软水机、水槽下净水器", "P-07 后花园水池：补水 + 地沟 + 渗水井",
                           "P-08 西卫后墙详图：地面不抬高 · 马桶平台 · 淋浴壁龛 · 110 走北墙（方案 B）"]):
        A(f'<text x="20" y="{40+i*4.6}" font-size="2.5">{html.escape(t)}</text>')
    A('<text x="16" y="86" font-size="3.4" font-weight="bold">设计依据与条件 Basis</text>')
    basis = ["• UK Water Supply (Water Fittings) Regulations 1999、WRAS 认证产品；Building Regulations Part G（卫生与热水）、Part H（排水）、Part L（保温）。",
             "• 现场条件（业主 2026-10-07 确认）：进户总阀在楼梯下 / 前门进门处；锅炉为 Vaillant ecoTEC plus 即热式 combi，不设热水缸；",
             "  中央软水机放在锅炉正下方；厨房水槽下放 RO 净水器；原有污水立管不可利用，本图重新设计 2 根立管（S1、S2）。",
             "• 户型与用水点：Blender 模型 v42（2026-10-08，含门洞改动、西卫假墙 / 壁龛、S2 箱封）与 PPT v10 第 4 / 8 页给排水点位。",
             "• 坐标 / 尺寸为设计意图，管位以现场放线为准；凡标「现场确认」处须施工前核实（搁栅方向与高度、现有排水去向、规划）。"]
    for i, t in enumerate(basis):
        A(f'<text x="20" y="{94+i*5}" font-size="2.4">{html.escape(t)}</text>')
    A('<text x="16" y="128" font-size="3.4" font-weight="bold">管材与规格 Materials</text>')
    rows = [("进户", "MDPE 25 mm（蓝），埋深 ≥ 750 mm，进屋处带套管"), ("冷 / 热给水", "铜管 Table X 或 PEX（WRAS），主管 22 mm，支管 15 mm；热水管、外墙及楼板内冷水管保温 ≥ 13 mm"),
            ("阀门", "总阀 + 泄水阀 + DCV；软水机三阀旁通；每用水点 service valve；淋浴恒温阀；户外龙头 DCV + 防冻"),
            ("污水", "PVC-U 110 mm 立管 / 马桶支管，1:40；立管伸顶通气，带检修口"), ("废水", "PVC-U 32 mm（台盆）/ 40 mm（淋浴、洗碗机、洗衣、水槽），≥ 1:40，存水弯水封 ≥ 75 mm"),
            ("地下", "PVC-U 110 mm，坡度 ≥ 1:40，碎石垫层；450 mm 塑料检查井 IC1、IC2、IC4，接入后院现有 MH；回水井 G2（厨房）；洗衣房 / 户外水斗为废水，经厨房地坪下 50 mm 废水管斜穿到 IC2")]
    for i, (k, v) in enumerate(rows):
        A(f'<text x="20" y="{136+i*5.4}" font-size="2.4" font-weight="bold">{html.escape(k)}</text><text x="50" y="{136+i*5.4}" font-size="2.4">{html.escape(v)}</text>')
    A('<text x="16" y="176" font-size="3.4" font-weight="bold">用水点清单 Fixture schedule</text>')
    for i, (fid, (fl, x, y, name, sup, (dk, ds))) in enumerate(FIX.items()):
        col, row = i // 8, i % 8
        A(f'<text x="{20+col*150}" y="{184+row*5}" font-size="2.3">{"一层" if fl=="GF" else "二层"} · {html.escape(name)} · 给水 {sup} · 排水 {str(ds) + " mm" if ds else "车道地面"}</text>')
    A('<text x="16" y="232" font-size="3.4" font-weight="bold">施工前须确认 Site checks</text>')
    checks = ["① 进户管实际位置、水压与流量（combi 需 ≥ 1.5 bar / 15 L/min）；② 二层搁栅方向（业主已确认前后方向）与间距：西卫马桶管在假墙内走到北墙角，落进北墙下那一格，按 1:40 往后约 5.7 m；",
              "③ 后院 MH 的管底标高与管径；④ 西卫地面不抬高（见 P-08），假墙尺寸以 P-08 为准；⑤ 岛台位置定版后再预埋地坪管线；⑥ S2 两处 200×200 箱封位置。"]
    for i, t in enumerate(checks):
        A(f'<text x="20" y="{240+i*5}" font-size="2.4">{html.escape(t)}</text>')
    A('<text x="16" y="260" font-size="3.0" font-weight="bold" fill="#b00020">修订 Revisions</text>')
    A('<text x="20" y="266" font-size="2.4" fill="#b00020">Rev C · 2026-10-08：西卫马桶管改用方案 B（假墙内走到北墙角，沿北墙下那一格搁栅往后进 S1），取代方案 A；后墙假墙尽量薄，能借后面原墙的位置就借，尽量保留卫生间内空；西卫冷热水改为和马桶管同一格搁栅走；P-02 / P-04 / P-08 / 说明同步更新，单张 P-04B 作废。</text>')
    s.frame()
    return s


def garden_sheet():
    """P-07: rear-garden pond — hard-water top-up with an air gap, channel drain, overflow, catch pit and soakaway (1:50)."""
    from plan_base import table
    s = Sheet("后花园水池 补水 + 地沟 Garden pond: feed & channel drain", "P-07", "GF", ((-4.8, 4.6), (7.6, 25.6)),
              discipline="给排水 Plumbing & drainage")
    s.defs.append('<clipPath id="pc"><rect x="11" y="11" width="398" height="197"/></clipPath>')
    s.base_plan("GF")
    A = s.add
    A(f'<path d="M{s.P(-4.55, 8.13)[0]:.1f} {s.P(-4.55, 8.13)[1]:.1f} H{s.P(0, 26)[0]:.1f}" stroke="#7a5b00" stroke-width=".5" stroke-dasharray="3 1"/>')
    s.text(-4.40, 11.5, "西侧围栏 Fence（WPC / 铁丝网）", 2.1, "lbl")
    s.poly([(-4.52, 17.16), (4.53, 17.16)], style="stroke:#888;stroke-width:.3;stroke-dasharray:1.5 1;fill:none")
    s.text(1.5, 13.0, "露台 Patio（铺装向地沟找坡 1:60）", 2.4, "room"); s.text(1.5, 21.0, "草坪 Lawn", 3.0, "room")
    s.poly(POND_OUT, closed=True, style="fill:#d9d4c7;stroke:#555;stroke-width:.3")
    s.poly(POND_IN, closed=True, style="fill:#bfe0f2;stroke:#3b7fa8;stroke-width:.3")
    s.text(-3.72, 16.25, "水池 Pond", 3.0, "lbl", style="font-weight:bold"); s.text(-3.38, 16.25, "池水约 1.5 × 2.0 m，深约 0.8 m", 1.9, "lbl")
    s.poly(ROCKERY, closed=True, style="fill:#c9c2b3;stroke:#7a7466;stroke-width:.25")
    s.text(-3.80, 14.75, "假山 + 瀑布 Rockery", 2.0, "lbl")
    x, y0, y1 = CHANNEL
    (ax, ay), (bx, by) = s.P(x - 0.05, y0), s.P(x + 0.05, y1)
    A(f'<rect x="{ax:.2f}" y="{ay:.2f}" width="{bx-ax:.2f}" height="{by-ay:.2f}" fill="#fff" stroke="#2e7d32" stroke-width=".4"/>')
    for i in range(int((bx - ax) / 1.2)):
        A(f'<line x1="{ax+0.6+i*1.2:.2f}" y1="{ay:.2f}" x2="{ax+0.6+i*1.2:.2f}" y2="{by:.2f}" stroke="#2e7d32" stroke-width=".15"/>')
    s.text(x + 0.30, y0 - 0.15, "地沟 CH 100 宽，长约 2.5 m，坡向北端出口 →", 2.1, "lbl", anchor="end", style="fill:#2e7d32")
    runs = []
    for kind, size, pts, label in GARDEN_PIPES:
        runs.append([len(runs) + 1, SHORT[kind], f"Ø{size}", label]); pipe(s, kind, pts, size, len(runs))
    for gid, gx, gy, w, d, txt, cls in GARDEN_PTS:
        px, py = s.P(gx, gy)
        if gid == "SA": A(f'<circle cx="{px:.2f}" cy="{py:.2f}" r="{w*MM/2:.2f}" fill="#eef7ee" stroke="#2e7d32" stroke-width=".4" stroke-dasharray="2 1"/>')
        else: A(f'<rect x="{px-d*MM/2:.2f}" y="{py-w*MM/2:.2f}" width="{d*MM:.2f}" height="{w*MM:.2f}" class="{cls}"/>')
        A(f'<text x="{px:.2f}" y="{py+0.8:.2f}" font-size="2" text-anchor="middle" font-weight="bold">{gid}</text>')
        A(f'<text x="{px+(w*MM/2+1.5 if gid != "TU" else 0):.2f}" y="{py+(3.6 if gid != "TU" else 6.0):.2f}" font-size="2.1" class="lbl" text-anchor="{"start" if gid != "TU" else "middle"}">{html.escape(txt)}</text>')
    fixtures(s, "GF", False)
    for vx, vy in ((3.80, 16.28),):
        px, py = s.P(vx, vy)
        A(f'<path d="M{px-1.5:.2f} {py-1:.2f} L{px+1.5:.2f} {py+1:.2f} L{px+1.5:.2f} {py-1:.2f} L{px-1.5:.2f} {py+1:.2f} Z" class="valve"/>')
    s.text(2.2, 22.6, "SA 距洗衣房后墙约 6.7 m（≥ 5 m）、距围栏 ≥ 1.5 m", 2.0, "lbl", style="fill:#2e7d32")
    s.parts = ['<g clip-path="url(#pc)">'] + s.parts + ['</g>']
    table(s, 14, 216, [("No.", 7), ("介质", 15), ("管径", 9), ("走向 / 说明 Route", 117)], runs, fs=1.85, title="管段表 Pipe schedule（图中圆圈编号）")
    # section through pond edge → channel → catch pit (NTS)
    A('<text x="14" y="252" font-size="2.6" font-weight="bold">剖面 Section A：池边 → 地沟 → 沉泥井（示意）</text>')
    A('<path d="M18 262 H40 V285 H18" fill="#bfe0f2" stroke="#3b7fa8" stroke-width=".3"/><rect x="40" y="258" width="5" height="27" fill="#d9d4c7" stroke="#555" stroke-width=".3"/>')
    A('<line x1="18" y1="264" x2="40" y2="264" stroke="#3b7fa8" stroke-width=".3" stroke-dasharray="1 .6"/><text x="19" y="263" font-size="1.8">设计水位 WL</text>')
    A('<line x1="40" y1="264" x2="58" y2="264" stroke="#c77d1a" stroke-width=".8"/><text x="46" y="262" font-size="1.8" fill="#c77d1a">50 溢流</text>')
    A('<path d="M56 258 V270 H64 V258" fill="none" stroke="#2e7d32" stroke-width=".5"/><line x1="55" y1="258" x2="65" y2="258" stroke="#2e7d32" stroke-width=".6" stroke-dasharray=".6 .4"/><text x="60" y="274" font-size="1.8" text-anchor="middle" fill="#2e7d32">地沟 CH</text>')
    A('<line x1="45" y1="258" x2="110" y2="258" stroke="#888" stroke-width=".4"/><text x="80" y="256.5" font-size="1.8">露台铺装 → 坡向地沟 1:60</text>')
    A('<path d="M64 268 H84" stroke="#2e7d32" stroke-width=".8" fill="none"/><rect x="84" y="262" width="10" height="20" fill="#fff" stroke="#2e7d32" stroke-width=".4"/><text x="89" y="285" font-size="1.8" text-anchor="middle">CP</text>')
    A('<path d="M94 270 H120" stroke="#2e7d32" stroke-width=".8" stroke-dasharray="2.5 1.2" fill="none"/><text x="122" y="271" font-size="1.8" fill="#2e7d32">→ SA 渗水井</text>')
    A('<rect x="122" y="250" width="9" height="9" class="eq"/><text x="126.5" y="248" font-size="1.8" text-anchor="middle">TU</text><line x1="126.5" y1="259" x2="126.5" y2="262" stroke="#1b3a8a" stroke-width=".5"/>'
      '<text x="133" y="253" font-size="1.8">浮球阀出水口高于溢流位 ≥ 20</text><text x="133" y="256" font-size="1.8">（AB 空气隔断）</text>')
    legend(s, ["hard", "yard", "waste", "sw"], x=168, y=219)
    s.frame(NOTES_GARDEN)
    return s


def sheets():
    return [cover_sheet(), plan_sheet("GF", "supply", "P-01"), plan_sheet("FF", "supply", "P-02"),
            plan_sheet("GF", "drain", "P-03"), plan_sheet("FF", "drain", "P-04"), schematic_sheet(), detail_sheet(), garden_sheet(), west_bath_sheet()]
