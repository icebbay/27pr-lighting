"""Rev C (2026-10-03, user decisions) applied to the Rev B data:
  1. GF circuit c (门廊壁灯 G25) moves from WL3 (户外) to WL1 (前区): no WL3 run across the house to the front door,
     and plate S1 is fed from one WL only.
  2. No fan isolator switches (FI): GF S11, FF S3, FF S16 removed; fans run off the bathroom light circuit (with overrun).
     Remaining plates renumbered without gaps (GF S12–S16 -> S11–S15; FF S4–S15 -> S3–S14), text references updated.

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\apply_revC.py
Reads ref_RevB/lighting_<F>.json, writes lighting_<F>.json, then rebuilds lighting_data.js.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "Rev C · 2026-10-03（门廊灯改 WL1；取消排气扇隔离开关）"
REV_CN = "Rev C 2026-10-03"
D = {F: json.load(open(os.path.join(HERE, "ref_RevB", f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}


def renumber(d):
    """drop FI plates, renumber S1.. in the existing order; returns old -> new id map"""
    gone = [p for p in d["plates"] if p["gangs"] == 0]
    for p in gone:
        for k in p["keys"]:
            d["special_keys"].pop(k, None)
    d["plates"] = [p for p in d["plates"] if p["gangs"] != 0]
    m = {}
    for i, p in enumerate(d["plates"], 1):
        m[p["id"]] = f"S{i}"; p["id"] = m[p["id"]]
    return [p["panel"] for p in gone], m


def retext(s, m):
    """replace S-numbers in a text (longest first, via placeholders so S12->S11 and S13->S12 do not collide)"""
    for old in sorted(m, key=lambda x: -int(x[1:])):
        s = re.sub(rf"\bS{old[1:]}\b(?!\d)", f"§{m[old][1:]}§", s)
    return re.sub(r"§(\d+)§", r"S\1", s)


maps = {}
for F, d in D.items():
    gone, maps[F] = renumber(d)
    print(F, "removed", gone, "renumber", {a: b for a, b in maps[F].items() if a != b})

gf, ff = D["GF"], D["FF"]
# FF stair circuit k: "（三控：一层 S6 + 二层 S12、S13）" -> FF numbers change, GF S6 stays
for c in ff["circuits"]:
    c["name"] = re.sub(r"二层 (S\d+)、(S\d+)", lambda mo: f"二层 {retext(mo.group(1), maps['FF'])}、{retext(mo.group(2), maps['FF'])}", c["name"])
    for r in c.get("remote_links", []):
        r["plate"] = maps[r["floor"]].get(r["plate"], r["plate"])
    if c.get("remote_links"):
        c["remote"] = [("一层" if r["floor"] == "GF" else "二层") + " " + r["plate"] for r in c["remote_links"]]
for k, sk in gf["special_keys"].items():
    sk["text"] = re.sub(r"二层 (S\d+)、(S\d+)", lambda mo: f"二层 {retext(mo.group(1), maps['FF'])}、{retext(mo.group(2), maps['FF'])}", sk["text"])
for c in gf["circuits"]:
    if c.get("assumed"): c["assumed"] = retext(c["assumed"], maps["GF"])
for ds in gf["door_switches"]:
    for f in ("parallel", "schedule"): ds[f] = retext(ds[f], maps["GF"])

# meta / notes
gf["meta"]["keyplan_note"] = retext(gf["meta"]["keyplan_note"], maps["GF"])
gf["meta"]["plate_note5"] = retext(gf["meta"]["plate_note5"], maps["GF"])
ff["meta"]["keyplan_note"] = "4. 楼梯吊灯 F06 三控：一层 S6（楼梯底）、二层 S12（楼梯顶）为两路开关，S11 键 2 为中途开关。"
ff["meta"]["plate_note5"] = "5. S2 原图标为“6+”，按常理作为西卫生间筒灯的独立单联开关，装在门外。"
gf_notes, ff_notes = gf["meta"]["cn_notes"], ff["meta"]["cn_notes"]
idx = lambda L, n: next(i for i, t in enumerate(L) if t.startswith(f"{n}. "))
gf_notes[idx(gf_notes, 2)] = "2. 一层照明由照明配电箱 AL1（暂定楼梯下，现场定）引出 3 个回路：WL1 前区（含门廊壁灯）、WL2 后区（含卫生间排气扇）、WL3 后花园户外，均带 30 mA 漏电保护。"
gf_notes[idx(gf_notes, 9)] = retext(gf_notes[idx(gf_notes, 9)], maps["GF"])
gf_notes.append("10. Rev C：门廊壁灯 c 改由 WL1 供电；卫生间排气扇不设单独隔离开关，接卫生间灯回路（随灯开、延时关），开关编号重排。")
ff_notes[idx(ff_notes, 6)] = "6. 楼梯吊灯 F06 三控：一层 S6（楼梯底）、二层 S12（楼梯顶）为两路开关，二层 S11 第 2 键为中途开关。"
ff_notes[idx(ff_notes, 8)] = "8. 卫生间排气扇不设单独隔离开关，接所在卫生间灯回路（随灯开、带延时关）。Rev C 起开关编号重排。"
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN; d["meta"]["fan_isolator"] = False

# 1. c -> WL1
c = next(x for x in gf["circuits"] if x["letter"] == "c")
c["wl"] = "WL1"
gf["wl"]["WL3"]["circ"].remove(c["id"]); gf["wl"]["WL1"]["circ"].insert(gf["wl"]["WL1"]["circ"].index("L2") + 1, c["id"])
gf["wl"]["WL1"]["name"] = "一层前区照明（门廊 / 门厅 / 起居室 / G07 区 / 楼梯）"
gf["wl"]["WL3"]["name"] = "户外照明（后花园壁灯 / 围栏地灯）"
ff["wl"]["WL4"]["name"] = ff["wl"]["WL4"]["name"].replace("+ 排气扇", "+ 卫生间排气扇")
ff["wl"]["WL5"]["name"] = ff["wl"]["WL5"]["name"].replace("+ 排气扇", "+ 卫生间排气扇")
for F, d in D.items():
    for w, v in d["wl"].items():
        v["n"] = sum(len(x["lights"]) for x in d["circuits"] if x["wl"] == w)
gf["wl_other"] = json.loads(json.dumps(ff["wl"])); ff["wl_other"] = json.loads(json.dumps(gf["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev C written")
