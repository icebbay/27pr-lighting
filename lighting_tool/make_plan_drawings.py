"""Lighting drawings for each plan (A / B) — same lamps, switches and keys, lighting circuits regrouped per power_plans.json.

For every plan: write out/lighting_<plan>_<F>.json (lighting_<F>.json with wl / circuit wl / notes replaced), run the English and
GB drawing scripts into drawings/27PR_<floor>照明施工图_RevG-<plan>_<style>.pptx, and export slide PNGs with PowerPoint.

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\make_plan_drawings.py
"""
import copy, glob, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.dirname(HERE)
OUT, DWG = os.path.join(HERE, "out"), os.path.join(HERE, "drawings")
FCN = {"GF": "一层", "FF": "二层"}
SCRIPTS = (("make_lighting_drawings.py", "英式"), ("make_lighting_drawings_cn.py", "国标"))
LJ = {F: json.load(open(os.path.join(HERE, f"lighting_{F}.json"), encoding="utf-8")) for F in ("GF", "FF")}
PLANS = json.load(open(os.path.join(HERE, "power_plans.json"), encoding="utf-8"))
os.makedirs(OUT, exist_ok=True)


def regroup(pid, pl):
    D = {F: copy.deepcopy(LJ[F]) for F in LJ}
    for F, d in D.items():
        groups = [w for w in pl["lighting"] if w["floor"] == F]
        d["wl"] = {w["id"]: dict(name=w["name"], br=w["br"], circ=list(w["circ"])) for w in groups}
        for w in groups:
            for c in d["circuits"]:
                if c["id"] in w["circ"]: c["wl"] = w["id"]
        for w, v in d["wl"].items():
            v["n"] = sum(len(c["lights"]) for c in d["circuits"] if c["wl"] == w)
        r = d["meta"]["rev_cn"].split(" ")          # "Rev G 2026-10-03" -> "Rev G-A 2026-10-03"
        d["meta"]["rev_cn"] = f"{r[0]} {r[1]}-{pid} {r[-1]}"
        d["meta"]["version"] = f"{r[0]} {r[1]}-{pid} · {pl['name']}（照明 {len(pl['lighting'])} 路）"
        n = d["meta"]["cn_notes"]
        n[:] = [t for t in n if not t.startswith(("12. ", "13. "))]   # GF revision notes about the old 4-way lighting decision
        n.append(f"{'12' if F == 'GF' else '11'}. 本套图：{pl['name']}，全屋照明 {len(pl['lighting'])} 路"
                 f"（{' / '.join(w['id'] + ' ' + w['name'].split('（')[0].replace('+ 卫生间排气扇', '').strip() for w in pl['lighting'])}）。"
                 "两个方案的灯、开关和联动完全相同，只是照明回路分组不同；插座与专线见网页「配电箱」页。")
        i = next(k for k, t in enumerate(n) if t.startswith("2. "))
        lst = "、".join(f"{w} {v['name'].split('（')[0].replace('+ 卫生间排气扇', '').strip()}（{v['br'].split(' ')[0]}）" for w, v in d["wl"].items())
        n[i] = (f"2. {FCN[F]}照明由照明配电箱 AL1{'（暂定楼梯下，现场定）' if F == 'GF' else '沿楼梯井引上'}引出 {len(d['wl'])} 个回路：{lst}，"
                f"均为 30 mA RCBO。本图为{pl['name']}；楼梯壁灯在一层、楼梯吊灯在二层，任一路跳闸楼梯仍有照明。")
    for F, d in D.items():
        d["wl_other"] = copy.deepcopy(D["FF" if F == "GF" else "GF"]["wl"])
    return D


made = []
for pid, pl in PLANS.items():
    for F, d in regroup(pid, pl).items():
        jp = os.path.join(OUT, f"lighting_{pid}_{F}.json")
        json.dump(d, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        for script, style in SCRIPTS:
            dst = os.path.join(DWG, f"27PR_{FCN[F]}照明施工图_RevG-{pid}_{style}.pptx")
            env = dict(os.environ, FLOOR=F, LIGHTING_JSON=jp, DST_OVERRIDE=dst, PYTHONIOENCODING="utf-8")
            r = subprocess.run([sys.executable, os.path.join(PROD, script)], cwd=PROD, env=env, capture_output=True, text=True, encoding="utf-8")
            assert r.returncode == 0 and os.path.exists(dst), r.stdout[-1500:] + r.stderr[-1500:]
            made.append(dst); print("saved", os.path.basename(dst))

PS = r"""
$pp = New-Object -ComObject PowerPoint.Application
foreach ($src in @({files})) {{
  $dst = Join-Path '{png}' ([IO.Path]::GetFileNameWithoutExtension($src)); New-Item -ItemType Directory -Force $dst | Out-Null
  Remove-Item "$dst\*.png" -ErrorAction SilentlyContinue
  $pres = $pp.Presentations.Open($src, $true, $false, $false); $i = 0
  foreach ($s in $pres.Slides) {{ $i++; $s.Export(($dst + '\slide' + $i.ToString('00') + '.png'), 'PNG', 1600, 900) }}
  $pres.Close(); Write-Output ([IO.Path]::GetFileName($src) + ': ' + $i)
}}
if ($pp.Presentations.Count -eq 0) {{ $pp.Quit() }}
"""
files = ",".join("'" + f.replace("'", "''") + "'" for f in made)
r = subprocess.run(["powershell", "-NoProfile", "-Command", PS.format(files=files, png=os.path.join(DWG, "png"))], capture_output=True, text=True)
print(r.stdout.strip() or r.stderr[-2000:])
counts = {os.path.basename(d): len(glob.glob(os.path.join(d, "*.png"))) for d in glob.glob(os.path.join(DWG, "png", "*RevG-*"))}
json.dump(counts, open(os.path.join(DWG, "png", "counts.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(counts)
