"""Rev J (2026-10-07) applied to the Rev I data — switch positions agreed with the user during the walkthrough review:

  一层  S7（后花园三控中途开关）挪到法式门框东侧（Blender 0.958, 7.899）。
  二层  S3（主卧灯单联）挪到主卧门旁、S4 西侧（Blender -1.62, 4.354）。
Same positions as trade_drawings/electrical.py OVERRIDE.

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\apply_revJ.py
Reads ref_RevI/lighting_<F>.json (frozen on first run), writes lighting_<F>.json, rebuilds lighting_data.js.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevI")
if not os.path.isdir(REF):   # first run: freeze the current Rev I data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev J · 2026-10-07（一层 S7 挪到法式门框东侧；二层 S3 挪到主卧门旁）"
REV_CN = "Rev J 2026-10-07"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}


def b2t(F, x, y):
    M = json.load(open(os.path.join(HERE, f"b2t_{F}.json")))
    return round(x * M[0][0] + y * M[1][0] + M[2][0]), round(x * M[0][1] + y * M[1][1] + M[2][1])


MOVE = {("GF", "S7"): (0.958, 7.899, "法式门框东侧（后花园门旁）"), ("FF", "S3"): (-1.62, 4.354, "主卧门旁（S4 西侧）")}
for (F, pid), (x, y, loc) in MOVE.items():
    p = next(q for q in D[F]["plates"] if q["id"] == pid)
    p["x"], p["y"] = b2t(F, x, y); p["location"] = loc
D["GF"]["meta"]["cn_notes"].append("16. Rev J：S7 挪到法式门框东侧（后花园门旁），按键不变。")
D["FF"]["meta"]["cn_notes"].append("13. Rev J：主卧灯开关 S3 挪到主卧门旁、S4 西侧，按键不变。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
D["GF"]["wl_other"] = json.loads(json.dumps(D["FF"]["wl"])); D["FF"]["wl_other"] = json.loads(json.dumps(D["GF"]["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev J written:", {k: D[k[0]]["plates"][[q["id"] for q in D[k[0]]["plates"]].index(k[1])]["location"] for k in MOVE})
