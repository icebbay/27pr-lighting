"""卧室 2 进门从北墙东端挪到西端（2026-10-06，用户新平面图）—— PPT 墙体层修改，供 v9（用户标点）和工具源 PPT 共用.

Old opening x 2.754–3.78 (hinge east, x 3.771) on the north wall y 4.354–4.474. New opening = what the user drew on v9 slide 6:
wall ends 1.678, west jamb 1.678–1.71, east jamb 2.408–2.439 (hinge), clear ~0.70 m, leaf drawn open into the bedroom; old opening filled.
"""
import copy
from lxml import etree
from ppt_ff_transform import b2s

A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
ns = {'a': A}
WY0, WY1 = 4.354, 4.474
NEW_W, NEW_E = 1.678, 2.408         # west wall end (= west jamb outer face), hinge / east jamb inner face (user, v9 slide 6)
OLD_W, OLD_E = 2.754, 3.771
LEAF = NEW_E - NEW_W - 0.032       # clear width


def _dx(m):
    return b2s(m, 0)[0] - b2s(0, 0)[0]


def _poly(el, pts, name, nid):
    S = [b2s(x, y) for x, y in pts]
    xs = [p[0] for p in S]; ys = [p[1] for p in S]
    ox, oy = int(min(xs)), int(min(ys))
    w, h = max(1, int(max(xs)) - ox), max(1, int(max(ys)) - oy)
    c = el.find('.//{*}cNvPr'); c.set('name', '墙_' + name); c.set('id', str(nid))
    x = el.find('.//a:xfrm', ns)
    for k in ('rot', 'flipH', 'flipV'):
        x.attrib.pop(k, None)
    x.find('a:off', ns).set('x', str(ox)); x.find('a:off', ns).set('y', str(oy))
    x.find('a:ext', ns).set('cx', str(w)); x.find('a:ext', ns).set('cy', str(h))
    pl = el.find('.//a:pathLst', ns)
    for ch in list(pl): pl.remove(ch)
    path = etree.SubElement(pl, f'{{{A}}}path', w=str(w), h=str(h))
    for i, (sx, sy) in enumerate(S):
        m = etree.SubElement(path, f'{{{A}}}' + ('moveTo' if i == 0 else 'lnTo'))
        etree.SubElement(m, f'{{{A}}}pt', x=str(int(sx) - ox), y=str(int(sy) - oy))
    etree.SubElement(path, f'{{{A}}}close')


def edit_wall_group(g, nid):
    by = {}
    for sh in g.shapes:
        by.setdefault(sh.name, []).append(sh)
    # 1. FF_Wall_Shell subpath that ends at the old west jamb: cut it back to the new west jamb
    done = False
    for sh in by['墙_FF_Wall_Shell']:
        e = sh._element
        off = e.find('.//a:xfrm/a:off', ns); ext = e.find('.//a:xfrm/a:ext', ns)
        ox, oy, cx, cy = int(off.get('x')), int(off.get('y')), int(ext.get('cx')), int(ext.get('cy'))
        for path in e.findall('.//a:path', ns):
            w, h = int(path.get('w') or cx), int(path.get('h') or cy)
            to_s = lambda pt: (ox + int(pt.get('x')) * cx / w, oy + int(pt.get('y')) * cy / h)
            to_p = lambda X, Y: (str(round((X - ox) * w / cx)), str(round((Y - oy) * h / cy)))
            cmds = [c for c in path if etree.QName(c).localname in ('moveTo', 'lnTo')]
            from ppt_ff_transform import s2b
            for c in cmds:
                pt = c.find('a:pt', ns); bx, by_ = s2b(*to_s(pt))
                if abs(by_ - WY0) < 0.01 or abs(by_ - WY1) < 0.01:
                    if 2.4 < bx < 2.8:          # points 2.52 / 2.754 on both faces -> new west end
                        X, Y = b2s(NEW_W, WY0 if abs(by_ - WY0) < 0.01 else WY1)
                        pt.set('x', to_p(X, Y)[0]); pt.set('y', to_p(X, Y)[1]); done = True
    assert done, "north wall points not found"
    # 2. new wall piece east of the new door, filling the old opening
    tmpl = by['墙_V39_Partition_Bed_Bath_W'][0]._element if '墙_V39_Partition_Bed_Bath_W' in by else by['墙_V35_Partition_Study_Bath'][0]._element
    e = copy.deepcopy(tmpl); _poly(e, [(NEW_E + 0.041, WY0), (3.78, WY0), (3.78, WY1), (NEW_E + 0.041, WY1)], 'V40_Wall_Bed2_North_East', nid); tmpl.addnext(e)
    # 3. jambs follow the opening, leaf redrawn 0.73 m open into the bedroom
    j_w, j_e = by['墙_FrameJamb.048'][0], by['墙_FrameJamb.049'][0]
    j_w.left = int(j_w.left + _dx(NEW_W - OLD_W)); j_e.left = int(j_e.left + _dx(NEW_E - OLD_E))
    leaf = by['墙_DoorLeaf.014'][0]._element
    e = copy.deepcopy(by['墙_V39_DoorLeaf_Bath'][0]._element if '墙_V39_DoorLeaf_Bath' in by else leaf)
    _poly(e, [(NEW_E - 0.04, WY0 - LEAF), (NEW_E, WY0 - LEAF), (NEW_E, WY0), (NEW_E - 0.04, WY0)], 'V40_DoorLeaf_Bed2', nid + 1)
    leaf.addnext(e); g._element.remove(leaf)
    return nid + 2
