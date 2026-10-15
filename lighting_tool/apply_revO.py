"""Rev O (2026-10-15): stair pendant F06 (FF key 7 / 17, 3-way with GF S6) — the intermediate switch moves from S11 to S12.

  * FF S12 (single, back-study door) becomes the intermediate (BG NAB13); FF S11 is then a plain 2-gang 2-way plate (NAB42)
    instead of NAB12 + NAB13 side by side (owner 2026-10-15). Strappers: GF S6 (2-way) -> FF S12 (intermediate) -> FF S11 (2-way).
  * GF laundry rear door hinge flipped to the east side (opens out; S15 on the lock side), door leaves re-read from walls_GF.svg;
  * FF 后书房 bath door hinge at the alcove end (y 9.264), opens out into the study (owner 2026-10-15), S14 on the lock side.
Positions, keys and circuits unchanged.

    python products/lighting_tool/apply_revO.py
Reads ref_RevN/lighting_<F>.json (frozen on first run), writes lighting_<F>.json, rebuilds lighting_data.js.
"""
import json, os, re, shutil

HERE = os.path.dirname(os.path.abspath(__file__))


def b2t(F, x, y):
    M = json.load(open(os.path.join(HERE, f"b2t_{F}.json")))
    return round(x * M[0][0] + y * M[1][0] + M[2][0]), round(x * M[0][1] + y * M[1][1] + M[2][1])


REF = os.path.join(HERE, "ref_RevN")
if not os.path.isdir(REF):   # first run: freeze the current Rev N data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev O · 2026-10-15（楼梯吊灯中途开关由二层 S11 改到 S12：S11 = 双联双控，S12 = 单联中途；洗衣房后门合页改东侧）"
REV_CN = "Rev O 2026-10-15"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
P = {p["id"]: p for p in D["FF"]["plates"]}
P["S11"]["middle_keys"] = []
P["S12"]["middle_keys"] = ["7"]
P["S12"]["panel"] = "单联中途开关 7"
# laundry rear door hinge flipped to the east (model v47, matches the owner keyplan; S15 is then on the lock side):
# GF door leaves rebuilt from the re-patched walls_GF.svg (run trade_drawings/patch_walls_v46.py first)
svg = open(os.path.join(HERE, "walls_GF.svg"), encoding="utf-8").read()
body = re.search(r'<g class="door"[^>]*>(.*?)</g>', svg, re.S).group(1)
doors = []
for name, d in re.findall(r'<path data-name="([^"]*)" d="([^"]+)"/>', body):
    ring = re.split(r"(?=M)", d.strip())[1] if d.strip().startswith("M") else d    # first ring only
    nums = [float(v) for v in re.sub("[MLZ]", " ", ring).split()]
    pts = [[round(nums[i]), round(nums[i + 1])] for i in range(0, len(nums) - 1, 2)]
    if len(pts) >= 3: doors.append(dict(name=name, pts=pts))
D["GF"]["doors"] = doors
# 后书房 bath door: hinge at the alcove end (y 9.264), leaf opens into the study — same box as patch_walls_v46.DOOR_BOX
for dr in D["FF"]["doors"]:
    if dr["name"] == "墙_V39_DoorLeaf_Bath":
        dr["pts"] = [list(b2t("FF", x, y)) for x, y in ((2.590, 9.264), (3.280, 9.264), (3.280, 9.304), (2.590, 9.304))]
D["GF"]["meta"]["cn_notes"].append("21. Rev O（2026-10-15）：洗衣房后门合页改到东侧（外开），S15 在锁侧。")
D["FF"]["meta"]["cn_notes"].append("18. Rev O（2026-10-15）：后书房卫浴门合页改到凹位一端（y 9.264），朝外开向书房，S14 在锁侧。")
D["FF"]["meta"]["cn_notes"].append("17. Rev O（2026-10-15）：楼梯吊灯 F06 三控的中途开关由 S11 改到 S12（S12 = BG NAB13 单联中途；S11 = NAB42 双联双控，一块面板）。联络线：一层 S6 → 二层 S12（中途）→ 二层 S11。")
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
D["GF"]["wl_other"] = json.loads(json.dumps(D["FF"]["wl"])); D["FF"]["wl_other"] = json.loads(json.dumps(D["GF"]["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev O written")
