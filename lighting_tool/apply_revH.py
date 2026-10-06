"""Rev H (2026-10-06) applied to the Rev G data — user's PPT v7 (后房间改卧室 4 + 东侧套卫; 一层 key 28):

  一层  新户外壁灯 G26_4（卫生间后墙、小窗东侧，与 G26_2 同款）= 回路 v，键 28；S7 / S11 / S12 由双联改三联，
        三处控制（S11、S12 两路开关，S7 中途开关），接户外 WL3。S7 在模型里往西挪 0.25 m。
  二层  书房 → 卧室 4（双人床）；后卫生间改到东侧 0.91 × 2.44 m（淋浴 / 台盆 / 马桶 由北往南），门开在竖隔墙南段。
        F23 移到卧室中部，后卫筒灯移进新卫生间；S14（卫生间灯）移到隔墙卧室侧、卫生间门南边。
        墙体 / 门 / 房间名来自 PPT v8（= v6 + 同样的改墙），walls_FF.svg 由 export_lighting_json.py 重新导出。

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\apply_revH.py
Reads ref_RevG/lighting_<F>.json (frozen on first run) + the v8 FF export, writes lighting_<F>.json, rebuilds lighting_data.js.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevG")
if not os.path.isdir(REF):   # first run: freeze the current Rev G data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
EXPORT_FF = os.path.join(HERE, "ref_RevH_export_FF.json")   # export_lighting_json.py run on PPT v8 (rooms / doors / light symbols)
VERSION = "Rev H · 2026-10-06（二层后房间改卧室 4 + 东侧套卫；一层新增户外壁灯 G26_4 三控）"
REV_CN = "Rev H 2026-10-06"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
gf, ff = D["GF"], D["FF"]
ex = json.load(open(EXPORT_FF, encoding="utf-8"))
U = gf["units"]["emu_per_px"]

# Blender (m) -> tool frame: b2t_GF.json fitted on 27 GF downlights, b2t_FF.json on the new FF partition corners (error < 6 mm)
def b2t(M, x, y):
    return round(x * M[0][0] + y * M[1][0] + M[2][0]), round(x * M[0][1] + y * M[1][1] + M[2][1])


def plate(d, pid):
    return next(p for p in d["plates"] if p["id"] == pid)


def circ(d, cid):
    return next(c for c in d["circuits"] if c["id"] == cid)


# ---------------- 一层：G26_4 + key 28 ----------------
M = json.load(open(os.path.join(HERE, "b2t_GF.json")))
x, y = b2t(M, -0.805, 8.161)
# sheet 3 (厨房 · 洗衣房 · 后花园): its view covers this wall, like the other garden lights (zone member box would say 1)
gf["lights"].append(dict(id="壁灯 G26_4", kind="壁灯", x=x, y=y, sheet=3, outdoor=True))
for pid, panel in (("S7", "三联中途开关"), ("S11", "三联开关 3"), ("S12", "三联开关 4")):
    p = plate(gf, pid)
    p["panel"], p["gangs"], p["keys"] = panel, 3, p["keys"] + ["28"]
    if pid == "S7": p["middle_keys"] = p["middle_keys"] + ["28"]
s7 = plate(gf, "S7")
dx, dy = [a - b for a, b in zip(b2t(M, 0.712, 7.899), b2t(M, 0.958, 7.899))]
s7["x"] += dx; s7["y"] += dy
gf["circuits"].append(dict(id="L22", letter="v", name="后花园壁灯 G26_4（卫生间后墙，三控：S11、S12、S7）", keys=["28"],
                           lights=["壁灯 G26_4"], wl="WL3", assumed="与 p、q 同一组开关：S11、S12 为两路开关，S7 为中途开关（三控）"))
gf["wl"]["WL3"]["circ"].append("L22")
gf["wl"]["WL3"]["name"] = "户外照明（后花园壁灯 ×4 / 围栏地灯）"

# ---------------- 二层：卧室 4 + 东侧套卫 ----------------
MF = json.load(open(os.path.join(HERE, "b2t_FF.json")))
ff["rooms"] = ex["rooms"]
ff["doors"] = ex["doors"]
exl = {l["id"]: l for l in ex["lights"]}
for l in ff["lights"]:
    if l["id"] in ("主灯 F23", "射灯 GU10_FF_卧室4_1"):
        l["x"], l["y"] = exl[l["id"]]["x"], exl[l["id"]]["y"]
p = plate(ff, "S13"); p["location"] = "卧室 4 门旁"
p = plate(ff, "S14"); p["location"] = "卧室 4 内 · 卫生间门南侧（隔墙短墙）"
p["x"], p["y"] = b2t(MF, 3.27, 9.04)
circ(ff, "L12")["name"] = "卧室 4 主灯 F23"
circ(ff, "L13")["name"] = "后卫生间筒灯（套卫）"
ff["zones"]["2"]["name"] = "走廊 · 北卫 · 卧室3 · 楼梯 · 卧室 4 · 后卫"
for d in D.values():
    for w, v in list(d["wl"].items()) + list(d["wl_other"].items()):
        v["name"] = v["name"].replace("书房 / 后卫", "卧室 4 / 后卫")
    for w, v in d["wl"].items():
        v["n"] = sum(len(x["lights"]) for x in d["circuits"] if x["wl"] == w)

gn, fn = gf["meta"]["cn_notes"], ff["meta"]["cn_notes"]
gn.append("14. Rev H：新增后花园壁灯 G26_4（卫生间后墙、小窗东侧，IP65，与 G26_2 同款），回路 v、键 28；S7、S11、S12 改三联，"
          "v 与 p、q 一样三处控制（S11、S12 两路，S7 中途），接户外 WL3。")
fn.append("11. Rev H：后房间由书房改为卧室 4，后卫生间改为东侧套内卫生间（0.91 × 2.44 m，淋浴 / 台盆 / 马桶由北往南）；"
          "F23 移到卧室中部，后卫筒灯移入新卫生间，S14 移到卧室内卫生间门南侧。卫生间排气扇仍接卫生间灯回路（不设 FI）。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
    d["meta"]["basis"] = d["meta"]["basis"].split("；")[0] + "；PPT v7（用户 2026-10-06 标注）；Blender v39"
gf["wl_other"] = json.loads(json.dumps(ff["wl"])); ff["wl_other"] = json.loads(json.dumps(gf["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev H written:", {F: {w: v["n"] for w, v in d["wl"].items()} for F, d in D.items()},
      "G26_4", gf["lights"][-1], "S14", plate(ff, "S14"))
