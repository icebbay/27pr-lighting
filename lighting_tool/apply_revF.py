"""Rev F (2026-10-03, user decision) applied to the Rev E data:
  FF lighting split into 3 areas, one breaker each (was 2: WL4 west incl. master bedroom, WL5 east incl. north bath):
    WL7 主卧区  主卧 a、b + 北卫 c          (new; S3, S4, S9)
    WL4 西区    衣帽间 / 盥洗室 / 西卫 / 卧室2  (S1, S2, S5, S6, S7)
    WL5 东区    走廊 / 卧室3 / 楼梯 / 书房 / 后卫 (S8, S10–S14; stair F06 stays on WL5)

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\apply_revF.py
Reads ref_RevE/lighting_<F>.json, writes lighting_<F>.json, then rebuilds lighting_data.js.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevE")
if not os.path.isdir(REF):   # first run: freeze the current Rev E data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev F · 2026-10-03（二层照明按区域分 3 路：主卧区 / 西区 / 东区）"
REV_CN = "Rev F 2026-10-03"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
ff = D["FF"]
C = {c["letter"]: c for c in ff["circuits"]}

area = {"WL7": "abc", "WL4": "fghij", "WL5": "deklm"}
for w, lets in area.items():
    for x in lets: C[x]["wl"] = w
br = ff["wl"]["WL4"]["br"]
ff["wl"] = {
    "WL4": dict(name="二层西区照明（衣帽间 / 盥洗室 / 西卫 / 卧室2）+ 卫生间排气扇", br=br, circ=[C[x]["id"] for x in area["WL4"]]),
    "WL5": dict(name="二层东区照明（走廊 / 卧室3 / 楼梯 / 书房 / 后卫）+ 卫生间排气扇", br=br, circ=[C[x]["id"] for x in area["WL5"]]),
    "WL7": dict(name="二层主卧区照明（主卧 / 北卫）+ 卫生间排气扇", br=br, circ=[C[x]["id"] for x in area["WL7"]]),
}
for w, v in ff["wl"].items():
    v["n"] = sum(len(x["lights"]) for x in ff["circuits"] if x["wl"] == w)

notes = ff["meta"]["cn_notes"]
i2 = next(i for i, t in enumerate(notes) if t.startswith("2. "))
notes[i2] = ("2. 二层照明由一层 AL1 按区域引出 3 个回路，沿楼梯井引上：WL7 主卧区（主卧、北卫）、WL4 西区（衣帽间、盥洗室、西卫、卧室2）、"
             "WL5 东区（走廊、卧室3、楼梯、书房、后卫），各含所在卫生间排气扇，均带 30 mA 漏电保护。")
notes.append("10. Rev F：二层照明按区域分 3 路（主卧区 / 西区 / 东区），主卧和北卫从 WL4、WL5 拆出为 WL7，每区一个断路器。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
D["GF"]["wl_other"] = json.loads(json.dumps(ff["wl"])); ff["wl_other"] = json.loads(json.dumps(D["GF"]["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev F written")
