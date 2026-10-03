"""Rev G (2026-10-03, professional 18-way plan) applied to the Rev F data — lighting goes to 4 breakers:
    WL1 一层前区  门廊 / 门厅 / 起居室 / G07 餐厅 / 楼梯                (unchanged)
    WL2 一层后区  G15 区 / 卫生间 / 厨房 / 吧台区 / 洗衣房            (old WL2 + WL6)
    WL3 户外      后花园壁灯 / 围栏地灯                              (unchanged)
    WL4 二层      全部二层                                            (old WL4 + WL5 + WL7)
  Why: BS 7671 314.1 — no single lighting circuit for a whole house (GF has two; the stair has its wall light on WL1
  and its pendant on WL4). LED load is small (GF indoor ~680 W, FF ~320 W, estimated from the bought products).

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\apply_revG.py
Reads ref_RevF/lighting_<F>.json, writes lighting_<F>.json, then rebuilds lighting_data.js.
"""
import json, os, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "ref_RevF")
if not os.path.isdir(REF):   # first run: freeze the current Rev F data as the reference
    os.makedirs(REF)
    for F in ("GF", "FF"): shutil.copy(os.path.join(HERE, f"lighting_{F}.json"), REF)
VERSION = "Rev G · 2026-10-03（照明 4 路：一层前区 / 一层后区 / 二层 / 户外）"
REV_CN = "Rev G 2026-10-03"
D = {F: json.load(open(os.path.join(REF, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
gf, ff = D["GF"], D["FF"]

for c in gf["circuits"]:
    if c["wl"] == "WL6": c["wl"] = "WL2"
for c in ff["circuits"]: c["wl"] = "WL4"
br = gf["wl"]["WL1"]["br"]
gf["wl"] = {
    "WL1": dict(gf["wl"]["WL1"], name="一层前区照明（门廊 / 门厅 / 起居室 / G07 餐厅 / 楼梯）"),
    "WL2": dict(name="一层后区照明（G15 区 / 卫生间 / 厨房 / 吧台区 / 洗衣房）+ 卫生间排气扇", br=br,
                circ=gf["wl"]["WL2"]["circ"] + gf["wl"]["WL6"]["circ"]),
    "WL3": gf["wl"]["WL3"],
}
ff["wl"] = {"WL4": dict(name="二层照明（主卧 / 北卫 / 衣帽间 / 盥洗室 / 西卫 / 卧室2 / 走廊 / 卧室3 / 楼梯 / 书房 / 后卫）+ 卫生间排气扇",
                        br=br, circ=[c["id"] for c in ff["circuits"]])}
for d in D.values():
    for w, v in d["wl"].items():
        v["n"] = sum(len(x["lights"]) for x in d["circuits"] if x["wl"] == w)

gn, fn = gf["meta"]["cn_notes"], ff["meta"]["cn_notes"]
idx = lambda L, n: next(i for i, t in enumerate(L) if t.startswith(f"{n}. "))
gn[idx(gn, 2)] = ("2. 一层照明由照明配电箱 AL1（暂定楼梯下，现场定）引出 3 个回路：WL1 前区（含门廊壁灯）、WL2 后区（G15 区、卫生间、厨房、洗衣房，含排气扇）、"
                  "WL3 后花园户外，均为 30 mA RCBO。楼梯壁灯在 WL1、楼梯吊灯在二层 WL4：任一路跳闸楼梯仍有照明。")
gn[idx(gn, 12)] = "12. Rev E：一层照明曾按区域分 4 路；Rev G 起按全屋 18 路方案，厨房并回一层后区 WL2。"
gn.append("13. Rev G：全屋照明 4 路（一层前区 / 一层后区 / 二层 / 户外）。按已购灯具估算一层室内约 680 W、二层约 320 W，LED 负载远小于 6–10 A 照明回路；"
          "GU10 筒灯必须选 LED（≤ 7 W），不得换卤素灯。")
fn[idx(fn, 2)] = "2. 二层照明由一层 AL1 引出 1 个回路 WL4，沿楼梯井引上，含卫生间排气扇，30 mA RCBO。楼梯吊灯在 WL4、楼梯壁灯在一层 WL1。"
fn[idx(fn, 10)] = "10. Rev F：二层照明曾按区域分 3 路；Rev G 起按全屋 18 路方案合为 1 路 WL4（约 320 W）。"
for d in D.values():
    d["meta"]["version"] = VERSION; d["meta"]["rev_cn"] = REV_CN
gf["wl_other"] = json.loads(json.dumps(ff["wl"])); ff["wl_other"] = json.loads(json.dumps(gf["wl"]))

for F, d in D.items():
    json.dump(d, open(os.path.join(HERE, f"lighting_{F}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
exec(open(os.path.join(HERE, "build_data_js.py"), encoding="utf-8").read())
print("Rev G written:", {F: {w: v["n"] for w, v in d["wl"].items()} for F, d in D.items()})
