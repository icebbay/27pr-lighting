import json
from pptx.util import Inches
fit=json.load(open(r"D:\Codex project\output\product_components_20260927\cgi_v19\elec\fit.json",encoding='utf8'))
AX0,AY0,AX1,AY1=480,262,872,765
SW=Inches(13.333);TOP,BOT=Inches(0.95),Inches(7.2);LEFT_X=Inches(0.35);GAP=Inches(0.35);LEGEND_W=Inches(3.35)
k=min((BOT-TOP)/(AY1-AY0),(SW-2*LEFT_X-GAP-LEGEND_W)/(2*(AX1-AX0)))
f=fit['FF']
def b2s(x,y): return (LEFT_X+((x-f['bx'])/f['a']-AX0)*k, TOP+((f['by']-y)/f['a']-AY0)*k)
def s2b(sx,sy): return (((sx-LEFT_X)/k+AX0)*f['a']+f['bx'], f['by']-((sy-TOP)/k+AY0)*f['a'])

# ground floor
GAX0,GAY0,GAX1,GAY1=425,118,712,770
gk=min((BOT-TOP)/(GAY1-GAY0),(SW-2*LEFT_X-GAP-LEGEND_W)/(2*(GAX1-GAX0)))
gf=fit['GF']
def gb2s(x,y): return (LEFT_X+((x-gf['bx'])/gf['a']-GAX0)*gk, TOP+((gf['by']-y)/gf['a']-GAY0)*gk)
def gs2b(sx,sy): return (((sx-LEFT_X)/gk+GAX0)*gf['a']+gf['bx'], gf['by']-((sy-TOP)/gk+GAY0)*gf['a'])
