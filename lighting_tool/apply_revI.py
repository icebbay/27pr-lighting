"""Rev I (2026-10-06) applied to the Rev H data — user's PPT v9 (卧室 2 进门从北墙东端挪到西端):

  二层  卧室 2 门洞 x 1.68–2.44（净宽约 0.70 m，合页在东），原门洞补墙；墙体 / 门来自 PPT v10（make_ppt_v10_bed2_door.py），
        walls_FF.svg 由 export_lighting_json.py 重新导出。门旁双联开关 S7 挪到新门西边短墙（锁侧）；S6 / S7 的位置说明原来写反了，一并改正；
        用户删掉靠门的筒灯 GU10_FF_卧室2_1，另一盏 GU10_FF_卧室2_2 往房间中间挪；回路 j 变成 1 盏。

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\apply_revI.py
Reads ref_RevH/lighting_<F>.json (frozen on first run) + ref_RevI_export_FF.json, writes lighting_<F>.json, rebuilds lighting_data.js.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevH")
if not os.path.isdir(REF):   # first run: freeze the current Rev H data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev I · 2026-10-06（卧室 2 进门挪到北墙西端；二层后房间改卧室 4 + 套卫；一层户外壁灯 G26_4 三控）"
REV_CN = "Rev I 2026-10-06"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
gf, ff = D["GF"], D["FF"]
ex = json.load(open(os.path.join(HERE, "ref_RevI_export_FF.json"), encoding="utf-8"))
MF = json.load(open(os.path.join(HERE, "b2t_FF.json")))


def b2t(M, x, y):
    return round(x * M[0][0] + y * M[1][0] + M[2][0]), round(x * M[0][1] + y * M[1][1] + M[2][1])


ff["rooms"], ff["doors"] = ex["rooms"], ex["doors"]
GONE = "射灯 GU10_FF_卧室2_1"
ff["lights"] = [l for l in ff["lights"] if l["id"] != GONE]
exl = {l["id"]: l for l in ex["lights"]}
for l in ff["lights"]:
    if l["id"] == "射灯 GU10_FF_卧室2_2":
        l["x"], l["y"] = exl[l["id"]]["x"], exl[l["id"]]["y"]
for c in ff["circuits"]:
    if GONE in c["lights"]:
        c["lights"] = [x for x in c["lights"] if x != GONE]
        c["name"] = "卧室2 筒灯"
# the plate at the old door is S7 (its label "床头侧" was swapped with S6 since Rev B); S6 sits on the east wall by the bed head
pl = {p["id"]: p for p in ff["plates"]}
pl["S7"]["x"], pl["S7"]["y"] = b2t(MF, 1.47, 4.354)
pl["S7"]["location"] = "卧室2 门旁（新门西侧短墙，锁侧）"
pl["S6"]["location"] = "卧室2 床头侧（东墙）"
s6 = pl["S7"]
for w, v in ff["wl"].items():
    v["n"] = sum(len(x["lights"]) for x in ff["circuits"] if x["wl"] == w)

ff["meta"]["cn_notes"].append("12. Rev I：卧室 2 进门由北墙东端挪到西端（净宽约 0.70 m，合页在东、向内开），门旁开关 S7 随门挪到锁侧短墙（S6 在床头东墙）；"
                              "取消门旁筒灯 1 盏，回路 j 剩 1 盏筒灯。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
    d["meta"]["basis"] = d["meta"]["basis"].split("；")[0] + "；PPT v7 / v9（用户 2026-10-06 标注）；Blender v40"
gf["wl_other"] = json.loads(json.dumps(ff["wl"])); ff["wl_other"] = json.loads(json.dumps(gf["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev I written:", {F: {w: v["n"] for w, v in d["wl"].items()} for F, d in D.items()}, "S7", s6["x"], s6["y"])
