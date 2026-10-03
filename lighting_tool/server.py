"""Local server for the lighting workflow tool: serves index.html and runs the existing PPT scripts.

    3D_gen_bench\\_tools_venv\\Scripts\\python.exe products\\lighting_tool\\server.py      -> http://127.0.0.1:8765/

index.html also works without this server (open the file directly): everything except 生成 PPT / 预览 works offline.
POST /api/build  {floors: {GF: json, FF: json}, tag}  -> writes out/lighting_<F>.json, runs make_lighting_drawings(.py/_cn.py)
POST /api/render {file}                               -> slide PNGs via PowerPoint (COM), for previewing the output
"""
import json, os, subprocess, sys, time, glob, urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

HERE = os.path.dirname(os.path.abspath(__file__))
PROD = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
FCN = {"GF": "一层", "FF": "二层"}
SCRIPTS = {"en": ("make_lighting_drawings.py", "英式"), "cn": ("make_lighting_drawings_cn.py", "国标")}


def build(req):
    os.makedirs(OUT, exist_ok=True)
    tag = "".join(c for c in req.get("tag", "工具") if c not in '\\/:*?"<>|') or "工具"
    res = []
    for F, data in req["floors"].items():
        jp = os.path.join(OUT, f"lighting_{F}.json")
        json.dump(data, open(jp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        for st in req.get("styles", ["en", "cn"]):
            script, name = SCRIPTS[st]
            dst = os.path.join(OUT, f"27PR_{FCN[F]}照明施工图_{tag}_{name}.pptx")
            env = dict(os.environ, FLOOR=F, LIGHTING_JSON=jp, DST_OVERRIDE=dst, PYTHONIOENCODING="utf-8")
            t = time.time()
            r = subprocess.run([sys.executable, os.path.join(PROD, script)], cwd=PROD, env=env, capture_output=True, text=True, encoding="utf-8")
            res.append(dict(floor=F, style=st, ok=r.returncode == 0 and os.path.exists(dst), file=os.path.relpath(dst, HERE).replace("\\", "/"),
                            seconds=round(time.time() - t, 1), log=(r.stdout + r.stderr)[-3000:]))
    return dict(ok=all(r["ok"] for r in res), results=res, json_dir="out/")


PS = r"""
$ErrorActionPreference = 'Stop'
$pp = New-Object -ComObject PowerPoint.Application
$pres = $pp.Presentations.Open('{src}', $true, $false, $false)
$i = 0
foreach ($s in $pres.Slides) {{ $i++; $s.Export(('{dst}\slide' + $i.ToString('00') + '.png'), 'PNG', 1600, 900) }}
$pres.Close()
if ($pp.Presentations.Count -eq 0) {{ $pp.Quit() }}
"""


def render(req):
    src = os.path.normpath(os.path.join(HERE, req["file"]))
    assert src.startswith(OUT) and src.endswith(".pptx"), "only files in out/"
    dst = os.path.join(OUT, "png", os.path.splitext(os.path.basename(src))[0])
    os.makedirs(dst, exist_ok=True)
    for f in glob.glob(os.path.join(dst, "*.png")): os.remove(f)
    r = subprocess.run(["powershell", "-NoProfile", "-Command", PS.format(src=src, dst=dst)], capture_output=True, text=True)
    pngs = sorted(glob.glob(os.path.join(dst, "*.png")))
    return dict(ok=bool(pngs), pngs=[os.path.relpath(p, HERE).replace("\\", "/") for p in pngs], log=r.stderr[-2000:])


class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=HERE, **k)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self):
        if self.path == "/api/ping":
            return self.reply(dict(ok=True, python=sys.executable))
        return super().do_GET()

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n).decode("utf-8"))
        try:
            out = {"/api/build": build, "/api/render": render}[urllib.parse.urlparse(self.path).path](req)
        except Exception as e:
            out = dict(ok=False, error=repr(e))
        self.reply(out)

    def reply(self, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(200); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print(f"27PR lighting tool: http://127.0.0.1:{port}/")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
