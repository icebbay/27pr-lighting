"""Rev L (2026-10-13): the lighting tool brought up to the finished wall elevations + point plan Rev B and model v46.

  * every switch plate and every ceiling light that the elevations set out is moved to its position in
    trade_drawings/_points_final.json (exported from wall_elev.py, 2026-10-10);
  * 二层 S1 / S2 (主卫 entry pier / 一门两用 partition end) follow the owner's 2026-10-11 v46 edits instead (newer than the elevations);
  * 衣帽间: two GU10 -> ONE 吸顶灯 (L14, elevations 主卧套间 Rev D);
  * 后院 fence: 4 ground lights -> one LED-strip cable tail L40 (elevations 后院 Rev C, owner 2026-10-09);
  * the GF ghost of the FF stair pendant F06 follows F06 to the stair-turn landing;
  * walls: trade_drawings/patch_walls_v46.py (model v46 section) — run it before this script.
Keys, circuits and switching are unchanged.

    python products/lighting_tool/apply_revL.py
Reads ref_RevK/lighting_<F>.json (frozen on first run), writes lighting_<F>.json, rebuilds lighting_data.js.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevK")
if not os.path.isdir(REF):   # first run: freeze the current Rev K data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev L · 2026-10-13（开关、灯位按立面图 / 点位图 Rev B；墙按模型 v46 业主平面）"
REV_CN = "Rev L 2026-10-13"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
PF = json.load(open(os.path.join(HERE, "..", "trade_drawings", "_points_final.json"), encoding="utf-8"))


def b2t(F, x, y):
    M = json.load(open(os.path.join(HERE, f"b2t_{F}.json")))
    return round(x * M[0][0] + y * M[1][0] + M[2][0]), round(x * M[0][1] + y * M[1][1] + M[2][1])


# ---- switch plates -> elevation positions (Blender x, y) ----
SW = {(p["F"], p["id"]): p["p"] for p in PF["wall"] if p.get("cat") == "switch" and "p" in p}
SW[("FF", "S1")] = [1.230, 0.278]     # v46 2026-10-11: new 主卫 entry pier 0.150-0.406, centre
SW[("FF", "S2")] = [0.200, 1.150]     # v46 2026-10-11: partition face 1.150, 150 back from its end
LOC = {("GF", "S1"): "主客厅 · 门洞右侧墙垛正中",
       ("GF", "S3"): "主客厅侧 · 拱门南侧",
       ("GF", "S4"): "餐厅 · 拱门旁（与 S5 上下叠放，S4 在下）",
       ("GF", "S5"): "餐厅 · 拱门旁（叠在 S4 正上方，h1330）",
       ("GF", "S6"): "楼梯第一级前约 300",
       ("GF", "S11"): "G15 区 · 花园门组左侧 295 墙段正中",
       ("GF", "S12"): "厨房吧台区 · 法式门旁",
       ("GF", "S13"): "厨房入口（KP762 门旁）",
       ("FF", "S1"): "盥洗室入口墙垛正中（一门两用旁）",
       ("FF", "S2"): "西卫生间隔墙端头旁",
       ("FF", "S3"): "主卧床头板正中上方（h1360，与门口 S4 双控）",
       ("FF", "S4"): "主卧门旁 · F 墙转角（离墙端 150）",
       ("FF", "S5"): "衣帽间洞口旁 400 墙段正中",
       ("FF", "S6"): "卧室2 床头（C04 正上方，h850）",
       ("FF", "S9"): "北卫生间门外（离门洞 150）",
       ("FF", "S12"): "楼梯顶 · 卧室 4 门旁（离门口 350）",
       ("FF", "S14"): "卧室 4 内 · 卫生间门左边（离门洞 100）"}
moved = []
for F, d in D.items():
    for p in d["plates"]:
        xy = SW.get((F, p["id"]))
        if not xy: continue
        nx, ny = b2t(F, *xy)
        if abs(nx - p["x"]) + abs(ny - p["y"]) > 20000: moved.append(f"{F} {p['id']}")
        p["x"], p["y"] = nx, ny
        if (F, p["id"]) in LOC: p["location"] = LOC[(F, p["id"])]

# ---- ceiling lights -> elevation positions (tool id -> Blender x, y) ----
CE = {(p["F"], p["id"], p["room"]): p["p"] for p in PF["ceiling"]}
LIGHT = {"GF": {"射灯 GU10_GF_起居室_%d" % i: ("L%d" % (10 + i), "主客厅") for i in range(1, 8)},
         "FF": {}}
LIGHT["GF"].update({"射灯 GU10_GF_电梯井_1": ("L18", "主客厅"), "主灯 G06": ("L03", "主客厅"),
                    "主灯位待选 主灯待选_厨房": ("L27", "厨房"), "射灯 GU10_GF_洗衣房_1": ("L38", "洗衣房")})
LIGHT["FF"].update({"主灯 F06": ("L01", "二楼走廊"), "主灯 F11": ("L02", "二楼走廊"), "主灯 F11#2": ("L15", "二楼走廊"),
                    "主灯 F19": ("L03", "次卧"), "主灯位待选 主灯待选_主卧": ("L12", "次卧"),
                    "主灯 F20": ("L04", "主卧"), "主灯 F23": ("L06", "后书房"),
                    "射灯 GU10_FF_卫生间_1": ("L07", "次卧完整卫浴"), "射灯 GU10_FF_卧室4_1": ("L08", "后房窄卫浴"),
                    "射灯 GU10_FF_主卫_1": ("L13", "主卫"), "射灯 GU10_FF_衣帽间_1#2": ("L14", "衣帽间")})
for F, m in LIGHT.items():
    for L in D[F]["lights"]:
        if L["id"] in m:
            lid, room = m[L["id"]]
            L["x"], L["y"] = b2t(F, *CE[(F, lid, room)]); moved.append(f"{F} {L['id']}")

# 衣帽间: two GU10 -> one ceiling light (keep the circuit / key, rename the fitting)
FF = D["FF"]
FF["lights"] = [L for L in FF["lights"] if L["id"] != "射灯 GU10_FF_衣帽间_1"]
for L in FF["lights"]:
    if L["id"] == "射灯 GU10_FF_衣帽间_1#2": L["id"], L["kind"] = "吸顶灯 衣帽间", "主灯"
for c in FF["circuits"]:
    if "射灯 GU10_FF_衣帽间_1#2" in c["lights"]:
        c["lights"] = ["吸顶灯 衣帽间"]; c["name"] = "衣帽间吸顶灯"

# 后院 fence: 4 ground lights cancelled -> one IP68 cable tail L40 for an outdoor LED strip (owner 2026-10-09; same key 27, 3-way)
GF = D["GF"]
L40 = next(p["p"] for p in PF["wall"] if p["F"] == "GF" and p["id"] == "L40")
GF["lights"] = [L for L in GF["lights"] if not L["id"].startswith("地灯 GroundLED")]
x, y = b2t("GF", *L40)
GF["lights"].append(dict(id="灯带出线 L40", kind="地灯", x=x, y=y, sheet=1, outdoor=True))
for c in GF["circuits"]:
    if any(l.startswith("地灯 GroundLED") for l in c["lights"]):
        c["lights"] = ["灯带出线 L40"]; c["name"] = "围栏户外 LED 灯带（L40 出线；户外，三控：S11、S12、S7）"
        c["assumed"] = "原围栏地灯 ×4 取消，改围栏 LED 灯条；只在围栏北端留 IP68 接线盒 + 出线（业主 2026-10-09），驱动位置待定"

# GF ghost of the FF stair pendant follows F06
g = D["GF"]["special_keys"]["30"]["ghost"]
g["x"], g["y"] = b2t("GF", *CE[("FF", "L01", "二楼走廊")])

D["GF"]["meta"]["cn_notes"].append("18. Rev L（2026-10-13）：开关、灯位按墙面立面图 / 点位定位图 Rev B 定位；墙体按模型 v46（业主平面 keyplan3d）更新：主客厅宽 3.689、厨房 / 洗衣房洞口 2.12（左边加 300 墙垛）；围栏地灯 ×4 取消，改 LED 灯带（L40 出线）。按键与回路不变。")
D["FF"]["meta"]["cn_notes"].append("16. Rev L（2026-10-13）：开关、灯位按墙面立面图 / 点位定位图 Rev B；楼梯吊灯 F06 在转角平台；衣帽间改一个吸顶灯；墙体按模型 v46：卧室2 门 860、卧室2 方正 3.060 × 4.204、盥洗室 1.00 / 西卫 1.20 / 衣帽间 1.805。按键与回路不变。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
D["GF"]["wl_other"] = json.loads(json.dumps(D["FF"]["wl"])); D["FF"]["wl_other"] = json.loads(json.dumps(D["GF"]["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev L written; moved:", ", ".join(moved))
