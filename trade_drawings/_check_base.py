import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from plan_base import *
from playwright.sync_api import sync_playwright
for F in ("GF", "FF"):
    w, rooms = walls(F)
    xs = [p[0] for k in w for _, pts, _ in w[k] for p in pts]; ys = [p[1] for k in w for _, pts, _ in w[k] for p in pts]
    print(F, "x", round(min(xs), 2), round(max(xs), 2), "y", round(min(ys), 2), round(max(ys), 2), [r[0] for r in rooms])
    s = Sheet(f"{F} base", "X", F, ((min(xs), max(xs)), (min(ys), max(ys))), discipline="test")
    s.base_plan(F); s.frame()
    open(f"_base_{F}.svg", "w", encoding="utf-8").write(s.svg(BASE_CSS))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1680, "height": 1188})
    for F in ("GF", "FF"):
        pg.goto("file:///" + os.path.abspath(f"_base_{F}.svg").replace("\\", "/")); pg.screenshot(path=f"_base_{F}.png")
    b.close()
