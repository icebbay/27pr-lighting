"""Rev M (2026-10-14): owner's switching changes, ground floor only.

  * 后花园 p / q / v: S11 is now the only plate that switches all three; S12 keeps only p, S7 keeps only v.
      p (壁灯 G26_2/3, key 26)  = 双控 S11 + S12
      v (投光灯 G26_4, key 28)  = 双控 S11 + S7
      q (围栏 LED 灯带, key 27) = 单控 S11
    S12 / S7 become single-gang two-way switches; no intermediate switch left (S7 was the 三联中途开关).
  * S3 (主客厅侧 · 拱门南侧, keys 23-25) cancelled: it was on the back of the arch and of little use.
    g / h / i are switched from S5 only (单控).
  * S9 no longer switches k (G16 吊灯, key 15): S9 becomes 三联 (j l m), k is switched from S8 only (单控).
Positions, lights and first floor unchanged.

    python products/lighting_tool/apply_revM.py
Reads ref_RevL/lighting_<F>.json (frozen on first run), writes lighting_<F>.json, rebuilds lighting_data.js.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevL")
if not os.path.isdir(REF):   # first run: freeze the current Rev L data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev M · 2026-10-14（后花园开关改：S11 控 p q v、S12 只控 p、S7 只控 v；取消 S3；S9 取消 k）"
REV_CN = "Rev M 2026-10-14"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
GF = D["GF"]
P = {p["id"]: p for p in GF["plates"]}
C = {c["letter"]: c for c in GF["circuits"]}

# ---- 后花园: S11 = p q v, S12 = p, S7 = v ----
P["S12"].update(panel="单联开关 S12", gangs=1, keys=["26"], middle_keys=[])
P["S7"].update(panel="单联开关 S7", gangs=1, keys=["28"], middle_keys=[])
P["S11"]["middle_keys"] = []
C["p"]["name"] = "后花园壁灯 G26_2、G26_3（双控：S11、S12）"
C["p"]["assumed"] = "S11、S12 为两路开关（双控）；业主 2026-10-14：S12 只控 p"
C["q"]["name"] = "围栏户外 LED 灯带（L40 出线；户外，单控：S11）"
C["v"]["name"] = "后花园投光灯 SOLLA 三头 150W（离地约 3.5 m，双控：S11、S7）"
C["v"]["assumed"] = "S11、S7 为两路开关（双控）；业主 2026-10-14：S7 只控 v"

# ---- S3 cancelled: g h i only on S5 ----
GF["plates"] = [p for p in GF["plates"] if p["id"] != "S3"]
for L in "ghi":
    C[L]["keys"] = [k for k in C[L]["keys"] if k not in ("23", "24", "25")]

# ---- S9 no longer switches k ----
P["S9"].update(panel="三联开关 2", gangs=3, keys=["14", "16", "17"])
C["k"]["keys"] = [k for k in C["k"]["keys"] if k != "15"]

GF["meta"]["cn_notes"].append("19. Rev M（2026-10-14）：后花园 S11 一处控 p、q、v；S12 只控 p（与 S11 双控），S7 只控 v（与 S11 双控），q 由 S11 单控，不再有中途开关。取消 S3（拱门背面，用处不大），g、h、i 改由 S5 单控。S9 取消 k 键（改三联），k（G16 吊灯）由 S8 单控。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
D["GF"]["wl_other"] = json.loads(json.dumps(D["FF"]["wl"])); D["FF"]["wl_other"] = json.loads(json.dumps(D["GF"]["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev M written")
