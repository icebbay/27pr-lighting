"""Rev E (2026-10-03, user decision) applied to the Rev D data:
  GF lighting split into 4 areas, one breaker each (was 3; WL2 covered G15 + bathroom + kitchen + laundry):
    WL1 前厅  门廊 / 门厅 / 起居室 / G07 餐厅 / 楼梯   (unchanged)
    WL2 侧厅  G15 区 / 卫生间（含排气扇）
    WL6 厨房  厨房 / 吧台区 / 洗衣房                  (new; WL4/WL5 are the FF circuits)
    WL3 户外  后花园壁灯 / 围栏地灯                    (unchanged)
  (Web tool: only the stretch of feed from AL1 to the switches that are on is animated, not the whole WL.)

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\apply_revE.py
Reads ref_RevD/lighting_<F>.json, writes lighting_<F>.json, then rebuilds lighting_data.js.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevD")
if not os.path.isdir(REF):   # first run: freeze the current Rev D data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev E · 2026-10-03（一层照明按区域分 4 路：前厅 / 侧厅 / 厨房 / 户外）"
REV_CN = "Rev E 2026-10-03"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
gf = D["GF"]
C = {c["letter"]: c for c in gf["circuits"]}

kitchen = [C[x]["id"] for x in ("r", "s", "t")]
for x in ("r", "s", "t"): C[x]["wl"] = "WL6"
wl = gf["wl"]
wl["WL1"]["name"] = "一层前厅照明（门廊 / 门厅 / 起居室 / G07 餐厅 / 楼梯）"
wl["WL2"]["name"] = "一层侧厅照明（G15 区 / 卫生间）+ 卫生间排气扇"
wl["WL2"]["circ"] = [c for c in wl["WL2"]["circ"] if c not in kitchen]
new = dict(name="一层厨房照明（厨房 / 吧台区 / 洗衣房）", br=wl["WL2"]["br"], circ=kitchen)
gf["wl"] = {"WL1": wl["WL1"], "WL2": wl["WL2"], "WL6": new, "WL3": wl["WL3"]}
for w, v in gf["wl"].items():
    v["n"] = sum(len(x["lights"]) for x in gf["circuits"] if x["wl"] == w)

notes = gf["meta"]["cn_notes"]
i2 = next(i for i, t in enumerate(notes) if t.startswith("2. "))
notes[i2] = ("2. 一层照明由照明配电箱 AL1（暂定楼梯下，现场定）按区域引出 4 个回路：WL1 前厅（含门廊壁灯）、WL2 侧厅（G15 区、卫生间，含排气扇）、"
             "WL6 厨房（含吧台区、洗衣房）、WL3 后花园户外，均带 30 mA 漏电保护。")
notes.append("12. Rev E：一层照明按区域分 4 路（前厅 / 侧厅 / 厨房 / 户外），厨房、吧台区、洗衣房从 WL2 拆出为 WL6，每区一个断路器。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
gf["wl_other"] = json.loads(json.dumps(D["FF"]["wl"])); D["FF"]["wl_other"] = json.loads(json.dumps(gf["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev E written")
