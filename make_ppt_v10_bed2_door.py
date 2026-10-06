"""PPT v10（2026-10-06）：卧室 2 进门挪到北墙西端，按用户 v9 第 6 页.

1. 工具源 PPT：source_pptx/…_v10_照明控制图_专业版_卧室2进门.pptx = v8 + 改门（ppt_bed2_door.py，四页二层墙体组）
   + 用户在 v9 里动过的点（第 6 页 → v8 第 5 页，第 7 页 → 第 7 页；控制图第 6 页里的两盏筒灯同步）。
2. 用户工作 PPT：Downloads/…_v10_卧室2进门.pptx = 用户 v9，第 7 / 8 页的门洞统一成第 6 页的样子（用户只在第 6 页画准了）。
"""
import copy, os, shutil, sys
from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from ppt_bed2_door import edit_wall_group

DL = os.path.join(os.path.expanduser("~"), "Downloads")
V8 = os.path.join(HERE, "source_pptx", "Blender模型户型图_灯_插座_水路_可编辑_v8_照明控制图_专业版_卧室套卫.pptx")
USER = os.path.join(DL, "Blender模型户型图_灯_插座_水路_可编辑_v9_卧室2进门.pptx")
SRC_OUT = "Blender模型户型图_灯_插座_水路_可编辑_v10_照明控制图_专业版_卧室2进门.pptx"
USER_OUT = os.path.join(DL, "Blender模型户型图_灯_插座_水路_可编辑_v10_卧室2进门.pptx")
DOOR = ("墙_FrameJamb.048", "墙_FrameJamb.049", "墙_V40_DoorLeaf_Bed2", "墙_V40_Wall_Bed2_North_East")


def wall_group(shapes):
    for sh in shapes:
        if sh.shape_type == 6:
            if sh.name.startswith('墙体'): return sh
            g = wall_group(sh.shapes)
            if g is not None: return g


u = Presentation(USER)

# ---- 1. tool source ----
p = Presentation(V8)
nid = 300000
for si in (4, 5, 6, 7):
    nid = edit_wall_group(wall_group(p.slides[si].shapes), nid)
for us, vs, ids in ((6, 5, [272, 388, 392]), (7, 7, [335, 323])):
    U = {s.shape_id: s for s in u.slides[us - 1].shapes}; V = {s.shape_id: s for s in p.slides[vs - 1].shapes}
    for i in ids:
        assert V[i].name == U[i].name, (i, V[i].name, U[i].name)
        V[i].left, V[i].top = U[i].left, U[i].top
gone = [s for s in p.slides[4].shapes if s.name == "射灯 GU10_FF_卧室2_1"]
for s in gone: s._element.getparent().remove(s._element)
U6 = {s.name: s for s in u.slides[5].shapes}
plan = [x for x in p.slides[5].shapes if x.name == '二层平面（横向）'][0]
for sh in list(plan.shapes):
    if sh.name == "射灯 GU10_FF_卧室2_1": sh._element.getparent().remove(sh._element)
    elif sh.name == "射灯 GU10_FF_卧室2_2": sh.left, sh.top = U6[sh.name].left, U6[sh.name].top
dst = os.path.join(HERE, "source_pptx", SRC_OUT)
p.save(dst); shutil.copy(dst, os.path.join(DL, SRC_OUT)); print("saved", dst, "removed", len(gone))

# ---- 2. user's copy: slides 7 / 8 door = slide 6 door ----
g6 = wall_group(u.slides[5].shapes)
ref = {s.name: s._element for s in g6.shapes if s.name in DOOR}
patch = [s for s in u.slides[5].shapes if s.name == "墙_V40_Wall_Bed2_North_East"]   # user's top-level wall patch west of the door
for si in (6, 7):
    g = wall_group(u.slides[si].shapes)
    for s in list(g.shapes):
        if s.name in ref:
            s._element.addnext(copy.deepcopy(ref[s.name])); g._element.remove(s._element)
    for s in list(u.slides[si].shapes):
        if s.name == "墙_V40_Wall_Bed2_North_East": s._element.getparent().remove(s._element)
    for s in patch:
        u.slides[si].shapes._spTree.append(copy.deepcopy(s._element))
u.save(USER_OUT); print("saved", USER_OUT)
