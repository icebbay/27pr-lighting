"""Build the trade drawing sets as A3 PDFs (+ PNG previews).

    python products/trade_drawings/build_drawings.py [plumbing] [electrical]
Writes products/trade_drawings/out/27PR_<set>.pdf and out/png/<sheet>.png (Chromium via Playwright).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out"); PNG = os.path.join(OUT, "png")
os.makedirs(PNG, exist_ok=True)


def build(name, mod):
    sheets = mod.sheets()
    pages = []
    for s in sheets:
        svg = s.svg(mod.CSS)
        open(os.path.join(OUT, f"{s.number}.svg"), "w", encoding="utf-8").write(svg)
        pages.append((s.number, svg))
    doc = ('<!doctype html><html><head><meta charset="utf-8"><style>@page{size:420mm 297mm;margin:0}body{margin:0}'
           '.pg{width:420mm;height:297mm;page-break-after:always;overflow:hidden}.pg svg{display:block}</style></head><body>'
           + "".join(f'<div class="pg">{svg}</div>' for _, svg in pages) + '</body></html>')
    hp = os.path.join(OUT, f"{name}.html"); open(hp, "w", encoding="utf-8").write(doc)
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto("file:///" + hp.replace("\\", "/")); pg.wait_for_timeout(300)
        pg.pdf(path=os.path.join(OUT, f"{name}.pdf"), width="420mm", height="297mm", print_background=True)
        v = b.new_page(viewport={"width": 1588, "height": 1123}, device_scale_factor=2)
        for num, svg in pages:
            px = svg.replace('width="420mm" height="297mm"', 'width="1588" height="1123"')
            v.set_content('<html><body style="margin:0;background:#fff">' + px + '</body></html>')
            v.screenshot(path=os.path.join(PNG, f"{num}.png"))
        b.close()
    print(name, len(pages), "sheets ->", os.path.join(OUT, f"{name}.pdf"))


if __name__ == "__main__":
    want = sys.argv[1:] or ["plumbing", "electrical", "power"]
    if "plumbing" in want:
        import plumbing; build("27PR_给排水施工图_RevB", plumbing)
    if "electrical" in want and os.path.exists(os.path.join(HERE, "electrical.py")):
        import electrical; build("27PR_照明布线施工图_RevB", electrical)
    if "power" in want:
        import power_sheets; build("27PR_插座动力施工图_RevB", power_sheets)
