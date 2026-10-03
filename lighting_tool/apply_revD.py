"""Rev D (2026-10-03, user decisions) applied to the Rev C data:
  1. GF S7 controls the garden lights p + q (not l): S7 becomes a 2-gang intermediate plate, so p and q are
     three-way (S11 + S12 two-way, S7 intermediate). l goes back to two-way (S8 + S9).
  2. GF S6 (楼梯底) key 30 switches the FF stair pendant F06: F06 is shown as a ghost on the GF plan (special_keys.30.ghost).
  (Web tool only: plate boxes stay next to their dots — S2 was drawn far away beside MK.)

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\apply_revD.py
Reads ref_RevC/lighting_<F>.json, writes lighting_<F>.json, then rebuilds lighting_data.js.
"""
import json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevC")
if not os.path.isdir(REF):   # first run: freeze the current Rev C data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev D · 2026-10-03（S7 改控后花园 p、q 三控）"
REV_CN = "Rev D 2026-10-03"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
gf = D["GF"]
C = {c["letter"]: c for c in gf["circuits"]}
S = {p["id"]: p for p in gf["plates"]}

# 1. S7: 28 (l, intermediate) -> 26 + 27 (p, q, both intermediate)
s7 = S["S7"]
s7.update(panel="双联中途开关", gangs=2, keys=["26", "27"], middle_keys=["26", "27"])
C["l"]["keys"].remove("28")
C["l"].pop("assumed", None)
C["p"]["name"] = "后花园壁灯 G26_2、G26_3（三控：S11、S12、S7）"
C["q"]["name"] = "围栏地灯 ×4（户外，三控：S11、S12、S7）"
C["p"]["assumed"] = "S11、S12 为两路开关，S7 为中途开关（三控）"

# 2. GF S6 key 30 switches the FF stair pendant F06: show F06 as a ghost on the GF plan at the same place.
#    FF -> GF: scale = ratio of emu_per_m, offset from the lift guide (same object in both wall SVGs).
def centre(svg, name):
    d = re.search(rf'data-name="{re.escape(name)}" d="([^"]+)"', open(os.path.join(HERE, svg), encoding="utf-8").read()).group(1)
    v = list(map(float, re.sub("[MLZ]", " ", d).split())); xs, ys = v[0::2], v[1::2]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
s = gf["units"]["emu_per_m"] / D["FF"]["units"]["emu_per_m"]
(gx, gy), (fx, fy) = centre("walls_GF.svg", "墙_Lift_Guide_Duo_1"), centre("walls_FF.svg", "墙_Lift_Guide_Duo_1")
sk = gf["special_keys"]["30"]
f06 = next(l for l in D["FF"]["lights"] if l["id"] == "主灯 F06")
sk["ghost"] = dict(light=f06["id"], kind=f06["kind"], x=round(gx + s * (f06["x"] - fx)), y=round(gy + s * (f06["y"] - fy)),
                   label="二层楼梯吊灯 F06（在楼上，S6 控）")

m = gf["meta"]
m["keyplan_note"] = "4. 按常理补全：p、q 回路 S7 为中途开关三控（S11、S12 两路）；38 控洗衣房筒灯；围栏地灯 4 盏；前储物间加门控开关。"
notes = m["cn_notes"]
i9 = next(i for i, t in enumerate(notes) if t.startswith("9. "))
notes[i9] = "9. 按常理补全（Rev B）：38 号键控洗衣房筒灯；围栏地灯 4 盏；前储物间门控开关。"
notes.append("11. Rev D：S7 改为双联中途开关，控后花园壁灯 p、围栏地灯 q（与 S11、S12 三控）；G15 区筒灯 l 改为 S8、S9 双控。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
gf["wl_other"] = json.loads(json.dumps(D["FF"]["wl"])); D["FF"]["wl_other"] = json.loads(json.dumps(gf["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev D written")
