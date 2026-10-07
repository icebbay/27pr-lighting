"""方案 B（2026-10-07 用户手绘）：西卫马桶 110 在假墙内走到北墙角，再沿北墙下那一格搁栅往后到 S1 — 单张 P-04B。
    WB_VARIANT=B python make_variant_b.py   (sets the variant itself)"""
import os, sys
os.environ["WB_VARIANT"] = "B"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plumbing
from build_drawings import build


class One:
    CSS = plumbing.CSS
    @staticmethod
    def sheets():
        s = plumbing.plan_sheet("FF", "drain", "P-04B")
        return [s]


build("27PR_给排水_P-04B_方案B_西卫走北墙", One)
