"""Rev K (2026-10-08) applied to the Rev J data — two FF switch positions corrected by the user on the setting-out draft:

  二层  S3（主卧主灯 F19 键 2，与 S4 双控）挪回主卧南墙（与衣帽间之间那面墙），主卧一侧、C19 西侧约 250（Blender -0.80, 3.37）。
  二层  S7（卧室 2 灯 键 14/15）留在门西侧短墙，但改到卧室 2 一侧（原来画在走廊一侧）（Blender 1.47, 4.25）。

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\apply_revK.py
Reads ref_RevJ/lighting_<F>.json (frozen on first run), writes lighting_<F>.json, rebuilds lighting_data.js.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevJ")
if not os.path.isdir(REF):   # first run: freeze the current Rev J data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev K · 2026-10-08（二层 S3 挪回主卧南墙 C19 旁；S7 改到卧室 2 一侧）"
REV_CN = "Rev K 2026-10-08"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}


def b2t(F, x, y):
    M = json.load(open(os.path.join(HERE, f"b2t_{F}.json")))
    return round(x * M[0][0] + y * M[1][0] + M[2][0]), round(x * M[0][1] + y * M[1][1] + M[2][1])


MOVE = {("FF", "S3"): (-0.80, 3.37, "主卧南墙（衣帽间那面墙）主卧一侧，C19 西侧"),
        ("FF", "S7"): (1.47, 4.25, "卧室2 门旁（门西侧短墙，卧室2 一侧，锁侧）")}
for (F, pid), (x, y, loc) in MOVE.items():
    p = next(q for q in D[F]["plates"] if q["id"] == pid)
    p["x"], p["y"] = b2t(F, x, y); p["location"] = loc
D["FF"]["meta"]["cn_notes"].append("14. Rev K：主卧灯开关 S3 挪回主卧南墙（C19 西侧）；卧室 2 门旁开关 S7 改装在短墙的卧室 2 一侧。按键不变。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
D["GF"]["wl_other"] = json.loads(json.dumps(D["FF"]["wl"])); D["FF"]["wl_other"] = json.loads(json.dumps(D["GF"]["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev K written:", {k: D[k[0]]["plates"][[q["id"] for q in D[k[0]]["plates"]].index(k[1])]["location"] for k in MOVE})
