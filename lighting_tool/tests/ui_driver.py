"""Small Playwright helper for testing index.html in the real browser (Chrome).
Used by the T1–T5 scripts; run with a Python that has playwright installed."""
import json, os
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(os.path.dirname(HERE), "screenshots")
URL = os.environ.get("TOOL_URL", "http://127.0.0.1:8765/")


class Tool:
    def __init__(self, w=1680, h=960):
        self.pw = sync_playwright().start()
        self.b = self.pw.chromium.launch(channel="chrome")
        self.pg = self.b.new_page(viewport={"width": w, "height": h})
        self.errors = []
        self.pg.on("console", lambda m: m.type == "error" and self.errors.append(m.text))
        self.pg.on("pageerror", lambda e: self.errors.append(str(e)))
        self.dialogs = []; self.accept_dialogs = True
        self.pg.on("dialog", lambda d: (self.dialogs.append(d.message), d.accept() if self.accept_dialogs else d.dismiss()))
        self.pg.goto(URL); self.pg.wait_for_function("window.APP && document.querySelector('.pane')")
        self.pg.wait_for_timeout(300)

    def js(self, code, arg=None):
        return self.pg.evaluate(code, arg)

    def shot(self, name):
        self.pg.wait_for_timeout(250)
        p = os.path.join(SHOTS, name + ".png"); self.pg.screenshot(path=p); return p

    def click(self, sel):
        self.pg.click(sel); self.pg.wait_for_timeout(120)

    def view(self, v): self.click(f'[data-view="{v}"]')
    def mode(self, m): self.click(f'[data-mode="{m}"]')
    def tab(self, t): self.click(f'[data-tab="{t}"]')

    def screen_of(self, F, x, y):
        """slide-EMU point on floor F -> page pixel."""
        return self.js("""([F,x,y]) => { const svg=[...document.querySelectorAll('svg.plan')].find(s=>s.classList.contains('p-'+F));
            const p=svg.createSVGPoint(); p.x=x; p.y=y; const q=p.matrixTransform(svg.getScreenCTM()); return [q.x,q.y]; }""", [F, x, y])

    def click_at(self, F, x, y, **kw):
        sx, sy = self.screen_of(F, x, y); self.pg.mouse.click(sx, sy, **kw); self.pg.wait_for_timeout(150)

    def press_key(self, F, plate, key):
        self.click(f'svg.p-{F} [data-k="key"][data-plate="{plate}"][data-key="{key}"]')

    def lamp(self, F, lid):
        self.click(f'svg.p-{F} [data-k="lamp"][data-id="{lid}"]')

    def zoom(self, F, x, y, w_m):
        self.js("([F,x,y,w]) => window.APP.zoom(F,x,y,w)", [F, x, y, w_m]); self.pg.wait_for_timeout(100)

    def issues(self):
        return self.js("() => window.APP.ISS().map(i => [i.sev, i.F, i.msg])")

    def close(self):
        self.b.close(); self.pw.stop()
