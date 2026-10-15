"""Rev N (2026-10-14): ground floor follows model v47 (owner keyplan screenshot, owner-adjusted in Blender).

  * walls: trade_drawings/patch_walls_v46.py now reads _v47_section.json (run it before this script):
    laundry rear door moved to x 2.650-3.530, laundry -> kitchen = plain opening 2.070-2.830, 300 kitchen pier removed,
    breakfast French door moved 91 (frame 8.764-10.405, 600 from the dining-side wall for the fridge);
  * S12 moves with the French door (+91, distance to the frame unchanged); S14 next to the new opening (model v47, x 2.957,
    ~130 from the opening edge); S15 on the lock side of the moved rear door (x 2.513); garden wall light G26_1 (key 40) moved left of the new rear door (x 1.845);
  * GF door leaves (used for the hinge / lock-side checks) rebuilt from walls_GF.svg, which also brings in doors the
    v46 patch had added (KP762, ...).
Keys, circuits and switching are unchanged (Rev M).

    python products/lighting_tool/apply_revN.py
Reads ref_RevM/lighting_<F>.json (frozen on first run), writes lighting_<F>.json, rebuilds lighting_data.js.
"""
import json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevM")
if not os.path.isdir(REF):   # first run: freeze the current Rev M data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev N · 2026-10-14（一层按模型 v47：洗衣房后门挪位、洗衣房 / 厨房无门洞口、去 300 墙垛、早餐区法式门挪 91；S12 / S14 / G26_1 跟着挪）"
REV_CN = "Rev N 2026-10-14"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
GF = D["GF"]


def b2t(F, x, y):
    M = json.load(open(os.path.join(HERE, f"b2t_{F}.json")))
    return round(x * M[0][0] + y * M[1][0] + M[2][0]), round(x * M[0][1] + y * M[1][1] + M[2][1])


P = {p["id"]: p for p in GF["plates"]}
P["S12"]["x"], P["S12"]["y"] = b2t("GF", 1.270, 10.555)
P["S14"]["x"], P["S14"]["y"] = b2t("GF", 2.957, 14.834)
P["S14"]["location"] = "洗衣房 · 通厨房洞口南侧（离洞边约 130）"
P["S15"]["x"], P["S15"]["y"] = b2t("GF", 2.513, 16.034)
P["S15"]["location"] = "洗衣房后门锁侧（离门洞边约 140）"
for L in GF["lights"]:
    if L["id"] == "壁灯 G26_1":
        L["x"], L["y"] = b2t("GF", 1.845, 16.706)          # data origin 440 off the wall face, as before

# door leaves from the patched wall drawing
svg = open(os.path.join(HERE, "walls_GF.svg"), encoding="utf-8").read()
body = re.search(r'<g class="door"[^>]*>(.*?)</g>', svg, re.S).group(1)
doors = []
for name, d in re.findall(r'<path data-name="([^"]*)" d="([^"]+)"/>', body):
    ring = re.split(r"(?=M)", d.strip())[1] if d.strip().startswith("M") else d    # first ring only
    nums = [float(v) for v in re.sub("[MLZ]", " ", ring).split()]
    pts = [[round(nums[i]), round(nums[i + 1])] for i in range(0, len(nums) - 1, 2)]
    if len(pts) >= 3: doors.append(dict(name=name, pts=pts))
GF["doors"] = doors

GF["meta"]["cn_notes"].append("20. Rev N（2026-10-14）：按模型 v47 —— 洗衣房后门挪到后墙中间偏东（x 2.65–3.53，原门洞补墙、后小窗取消），洗衣房与厨房之间改无门洞口 760，去掉厨房 / 早餐区之间 300 墙垛，早餐区法式门挪 91（门框离墙 600，放冰箱）；S12 跟法式门、S14 在洞口旁、壁灯 G26_1 挪到后门左边。回路与开关控制不变。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
D["GF"]["wl_other"] = json.loads(json.dumps(D["FF"]["wl"])); D["FF"]["wl_other"] = json.loads(json.dumps(D["GF"]["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev N written; GF doors", len(doors))
