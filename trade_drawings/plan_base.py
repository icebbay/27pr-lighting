"""Shared base for the trade drawings (electrician / plumber): walls, doors, windows, stairs and room names of each floor in
Blender metres, and an A3 SVG sheet with title block, north arrow and scale bar.

Source: products/lighting_tool/walls_<F>.svg + lighting_<F>.json (slide EMU), converted with b2t_<F>.json (Blender m -> tool,
fitted on 27 GF downlights / the FF partition corners, error < 6 mm).  Sheet orientation: front of the house on the left, rear
garden on the right (page x = Blender y), west side up (page y = Blender x) — same as the lighting drawings.
"""
import json, os, re, html
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(os.path.dirname(HERE), "lighting_tool")
SCALE = 50                       # 1:50
MM = 1000.0 / SCALE              # page mm per metre
BOLD = ' font-weight="bold"'
A3 = (420.0, 297.0)
FL = {"GF": 0.0, "FF": 2.852}    # finished floor levels (front FF slab 3.208)


def load_tool(F):
    return json.load(open(os.path.join(TOOL, f"lighting_{F}.json"), encoding="utf-8"))


class Frame:
    """tool slide-EMU <-> Blender metres for one floor"""
    def __init__(self, F):
        A = np.array(json.load(open(os.path.join(TOOL, f"b2t_{F}.json"))))
        self.A = A
        self.M2 = np.array([[A[0][0], A[1][0]], [A[0][1], A[1][1]]]); self.t = np.array([A[2][0], A[2][1]])
        self.inv = np.linalg.inv(self.M2)

    def t2b(self, x, y):
        v = self.inv @ (np.array([x, y], float) - self.t); return float(v[0]), float(v[1])

    def b2t(self, x, y):
        v = self.M2 @ np.array([x, y], float) + self.t; return float(v[0]), float(v[1])


def walls(F):
    """{'wall'|'door'|'window'|'stair': [[(x,y),...], closed]}, rooms [(name,x,y)] in Blender metres"""
    fr = Frame(F)
    svg = open(os.path.join(TOOL, f"walls_{F}.svg"), encoding="utf-8").read()
    out = {}
    for g in re.finditer(r'<g class="(\w+)"[^>]*>(.*?)</g>', svg, re.S):
        k = g.group(1)
        if k == "rooms": continue
        for name, d in re.findall(r'data-name="([^"]*)" d="([^"]+)"', g.group(2)):
            for sub in re.split(r'(?=M)', d):
                nums = [float(v) for v in re.sub('[MLZ]', ' ', sub).split()]
                if len(nums) < 4: continue
                pts = [fr.t2b(nums[i], nums[i + 1]) for i in range(0, len(nums) - 1, 2)]
                out.setdefault(k, []).append((name, pts, sub.strip().endswith('Z')))
    rooms = []
    for x, y, t in re.findall(r'translate\(([\d.]+) ([\d.]+)\) scale\(1000\)">([^<]+)<', svg):
        bx, by = fr.t2b(float(x), float(y)); rooms.append((t, bx, by))
    return out, rooms


class Sheet:
    """A3 landscape SVG in mm. plan(x, y) maps Blender metres onto the sheet."""
    def __init__(self, title, number, floor, bounds, scale_note="1:50", discipline="", rev="B", date="2026-10-08"):
        self.parts = []; self.defs = []
        self.title, self.number, self.floor, self.rev, self.date, self.discipline = title, number, floor, rev, date, discipline
        (x0, x1), (y0, y1) = bounds            # Blender x range (page vertical), y range (page horizontal)
        self.ox = 14 - y0 * MM; self.oy = 22 - x0 * MM
        self.scale_note = scale_note

    def P(self, x, y):
        return (self.ox + y * MM, self.oy + x * MM)

    def add(self, s):
        self.parts.append(s)

    def poly(self, pts, cls="", closed=False, style=""):
        d = "M" + " L".join(f"{a:.2f} {b:.2f}" for a, b in (self.P(*p) for p in pts)) + (" Z" if closed else "")
        self.add(f'<path d="{d}" class="{cls}" style="{style}"/>')

    def text(self, x, y, s, size=2.5, cls="", anchor="middle", style="", page=False):
        px, py = (x, y) if page else self.P(x, y)
        self.add(f'<text x="{px:.2f}" y="{py:.2f}" font-size="{size}" text-anchor="{anchor}" class="{cls}" style="{style}">{html.escape(s)}</text>')

    def base_plan(self, F, dim=True):
        w, rooms = walls(F)
        for k in ("stair", "window", "door", "wall"):
            for name, pts, closed in w.get(k, []):
                self.poly(pts, "b-" + k, closed)
        for t, x, y in rooms:
            self.text(x, y, t, 3.0, "room")

    def frame(self, notes=None):
        W, H = A3
        tb = [(W - 120, H - 42), (W - 10, H - 10)]
        s = [f'<rect x="10" y="10" width="{W-20}" height="{H-20}" class="border"/>',
             f'<rect x="{tb[0][0]}" y="{tb[0][1]}" width="110" height="32" class="tb"/>']
        rows = [("项目 Project", "27PR 住宅改造 · 27 Penrith Road"), ("图名 Title", self.title), ("图号 Sheet", f"{self.number}   比例 {self.scale_note} @A3"),
                ("专业 Discipline", self.discipline), ("版次 Rev", f"{self.rev} · {self.date} · 施工图（待持证电工 / 水工复核）")]
        for i, (k, v) in enumerate(rows):
            y = tb[0][1] + 5.6 + i * 6.2
            s.append(f'<text x="{tb[0][0]+2}" y="{y}" font-size="2.2" class="tbk">{k}</text><text x="{tb[0][0]+27}" y="{y}" font-size="2.6" class="tbv">{html.escape(v)}</text>')
            if i: s.append(f'<line x1="{tb[0][0]}" y1="{y-4.2}" x2="{W-10}" y2="{y-4.2}" class="tbl"/>')
        s.append(f'<text x="16" y="18" font-size="5" class="h1">{html.escape(self.title)}</text>')
        plan = self.scale_note == '1:50'
        # north / orientation arrow: front of house left, garden right
        if plan: s.append('<g transform="translate(398,19)"><circle r="6" class="na"/><path d="M0,-5 L1.9,1.7 L0,0.5 L-1.9,1.7 Z" class="naf" transform="rotate(90)"/>'
                 '<text x="-8" y="1" font-size="2.2" text-anchor="end">→ 后花园 Rear</text></g>')
        # scale bar 0-2 m
        x0, y0 = 200, 18
        for i in range(4 if plan else 0):
            s.append(f'<rect x="{x0+i*MM*0.5:.1f}" y="{y0}" width="{MM*0.5:.1f}" height="1.6" class="{"sbk" if i%2==0 else "sbw"}"/>')
        if plan: s.append(f'<text x="{x0}" y="{y0-1.2}" font-size="2.2">0</text><text x="{x0+MM*2:.1f}" y="{y0-1.2}" font-size="2.2" text-anchor="middle">2 m</text>')
        if notes:
            lines = [l for n in notes for l in wrap(n, 52)]
            yy = H - 46 - 3.1 * len(lines)
            s.append(f'<rect x="{W-122}" y="{yy-4}" width="112" height="{3.1*len(lines)+2}" fill="#fff" opacity=".92"/>')
            for i, n in enumerate(lines):
                s.append(f'<text x="{W-120}" y="{yy + i*3.1:.1f}" font-size="2.1" class="note"{BOLD if i == 0 else ""}>{html.escape(n)}</text>')
        self.parts = s + self.parts

    def svg(self, css):
        W, H = A3
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" font-family="Microsoft YaHei, Arial, sans-serif">'
                f'<style>{css}</style><defs>{"".join(self.defs)}</defs>' + "".join(self.parts) + '</svg>')


def wrap(text, n):
    """wrap mixed CJK / latin text to about n CJK-width characters per line"""
    out, cur, w = [], "", 0.0
    for ch in text:
        cw = 1.0 if ord(ch) > 0x2E80 else 0.55
        if w + cw > n and ch != " ":
            out.append(cur); cur, w = ("   " if text[:2].rstrip()[-1:].isdigit() or text.startswith(("•", "①")) else ""), 0.0
        cur += ch; w += cw
    if cur.strip(): out.append(cur)
    return out


def table(sheet, x, y, cols, rows, fs=2.1, head=True, title=None):
    """cols: [(header, width_mm)], rows: [[cell,...]]; returns bottom y"""
    A = sheet.add; rh = fs * 1.75
    if title:
        A(f'<text x="{x}" y="{y-1.5}" font-size="{fs+0.5}" font-weight="bold">{html.escape(title)}</text>')
    W = sum(w for _, w in cols)
    lines = [[h for h, _ in cols]] + rows if head else rows
    yy = y
    for i, r in enumerate(lines):
        # long cells wrap inside their column (row grows)
        cells = [wrap(str(c), max(2.0, (w - 1.6) / fs)) or [""] for (h, w), c in zip(cols, r)]
        n = max(len(c) for c in cells); hh = rh + (n - 1) * fs * 1.2
        if i == 0 and head: A(f'<rect x="{x}" y="{yy}" width="{W}" height="{rh}" fill="#eee"/>')
        cx = x
        for (h, w), cl in zip(cols, cells):
            for k, t in enumerate(cl):
                A(f'<text x="{cx+0.8:.1f}" y="{yy+rh*0.72+k*fs*1.2:.1f}" font-size="{fs}"{BOLD if i == 0 and head else ""}>{html.escape(t.strip() if k else t)}</text>')
            cx += w
        yy += hh
        A(f'<line x1="{x}" y1="{yy:.1f}" x2="{x+W}" y2="{yy:.1f}" stroke="#bbb" stroke-width=".12"/>')
    A(f'<rect x="{x}" y="{y}" width="{W}" height="{yy-y:.1f}" fill="none" stroke="#666" stroke-width=".2"/>')
    return yy


BASE_CSS = """
.border{fill:none;stroke:#222;stroke-width:.5}.tb{fill:#fff;stroke:#222;stroke-width:.35}.tbl{stroke:#888;stroke-width:.15}
.tbk{fill:#666}.tbv{fill:#111}.h1{font-weight:bold;fill:#111}.note{fill:#333}.na{fill:none;stroke:#222;stroke-width:.3}.naf{fill:#222}
.sbk{fill:#222}.sbw{fill:#fff;stroke:#222;stroke-width:.2}
.b-wall{fill:#cfcfcf;stroke:#555;stroke-width:.18;fill-rule:evenodd}.b-door{fill:#eee;stroke:#999;stroke-width:.12}
.b-window{fill:#e6f0f8;stroke:#7a9cb8;stroke-width:.12}.b-stair{fill:none;stroke:#aaa;stroke-width:.12}
.room{fill:#9a9a9a}
"""
