# -*- coding: utf-8 -*-
"""Export the FINAL point positions from the wall-elevation sets (wall_elev.py = owner-approved, 2026-10-09).

    python points_final.py   -> _points_final.json  (one row per point: room, face, elevation sheet, L / R distance,
                                height, circuit, note, plan position) + a coverage report against the old point data

The 点位定位尺寸图 Rev B (setting_out_sheets.py) reads this file, so the point plan always follows the elevations.
"""
import json, math, os, sys
from shapely.geometry import LineString, Point, Polygon

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def load_wall_elev():
    src = open(os.path.join(HERE, "wall_elev.py"), encoding="utf-8").read().split('if __name__ == "__main__":')[0]
    ns = {"__name__": "wall_elev_export", "__file__": os.path.join(HERE, "wall_elev.py")}
    exec(compile(src, "wall_elev.py", "exec"), ns)
    return ns


def ceil_dists(R, p):
    """same as the elevation ceiling sheets (wall_elev._ceil_rooms): rays stop at the room outline AND at partitions (ceil_walls)"""
    from shapely.geometry import box
    from shapely.ops import unary_union
    obst = unary_union([Polygon(R["poly"]).exterior] + [box(*b).exterior for _, b, _ in R.get("ceil_walls", [])])
    res = {}
    for name, (dx, dy) in (("N", (-1, 0)), ("S", (1, 0)), ("W", (0, -1)), ("E", (0, 1))):
        ray = LineString([p, (p[0] + dx * 12, p[1] + dy * 12)]).intersection(obst)
        cand = [g for g in getattr(ray, "geoms", [ray]) if not g.is_empty]
        res[name] = int(round(min(Point(p).distance(g) for g in cand) * 1000 / 10.0) * 10) if cand else None
    return res


def export():
    W = load_wall_elev()
    ROOMS, SETS = W["ROOMS"], W["SETS"]
    seen_out, sets = set(), []
    for nm, v in SETS.items():
        keys, out, *suite = v
        if out in seen_out: continue
        seen_out.add(out); sets.append((keys, out, suite))
    rows, ceil_rows, dup, areas = [], [], [], []
    have = set()
    for keys, out, suite in sets:
        if suite: W["build_suite"](keys, suite[0][1], suite[0][0])
        else:
            for k in keys: W["build_room"](k)
        for k in keys:
            R = ROOMS[k]
            W["load_meta"](R["F"])
            wall, ceil = W["room_points"](R)
            smap = {f: num for num, ks in R.get("_sheetmap", []) for f in ks}
            poly_ = Polygon(R["poly"])
            members = {f[0]: (W["_members"](R, f[0]) or [f]) for f in W["dfaces"](R)}

            def normal_at(k, p):
                fs = members[k]; best = min(fs, key=lambda m: LineString([m[3], m[4]]).distance(Point(p)))
                n = W["inward"](best[3], best[4], poly_); return [round(n[0], 4), round(n[1], 4)]
            for f in W["dfaces"](R):
                for q in W["unfold_pts"](R, wall, f[0]):
                    key = (R["F"], R["cn"], q["id"])
                    if key in have: dup.append((R["F"], q["id"], R["cn"])); continue
                    have.add(key)
                    circ = W["CIRC"].get(q["id"], "") if q["cat"] == "socket" else ("WL4" if q["cat"] == "switch" else q.get("circ", ""))
                    if q.get("display_name"): circ = q.get("circ", "")
                    rows.append(dict(F=R["F"], set=out, room=R["cn"], suite=R.get("suite_cn", ""), face=f[0], face_nm=f[1], ends=list(f[5]),
                                     sheet=smap.get(f[0], ""), id=q["id"], cat=q["cat"], kind=q.get("kind", ""), name=W["pt_name"](q),
                                     circ=circ, sL=q["sL"], sR=q["sR"], h=q["h"], note=W["pt_note"](q),
                                     p=[round(q["p"][0], 4), round(q["p"][1], 4)], fz=R["fz"], z=round(R["fz"] + q["h"] / 1000, 4),
                                     n_in=normal_at(f[0], q["p"])))
            nums = [n for n, _ in R.get("_sheetmap", [])] + [R.get("_ceil_sheet", ""), R.get("_index_sheet", "")]
            areas.append(dict(F=R["F"], set=out, room=R["cn"], poly=[list(c) for c in R["poly"]], prefix=next(n for n in nums if n)[:5]))
            for r in ceil:
                key = (R["F"], R["cn"], r["id"])
                if key in have: dup.append((R["F"], r["id"], R["cn"])); continue
                have.add(key)
                keys_ = W["LIGHT_KEYS"].get(r["id"], ("", "", ""))
                ceil_rows.append(dict(F=R["F"], set=out, room=R["cn"], suite=R.get("suite_cn", ""), sheet=R.get("_ceil_sheet", ""), id=r["id"],
                                      cat="smoke" if r.get("sym") == "smoke" else "light", name=r["name"], circ=keys_[1], switch=keys_[0],
                                      h=R["ceil"], d=ceil_dists(R, r["p"]), p=[round(r["p"][0], 4), round(r["p"][1], 4)],
                                      fz=R["fz"], z=round(R["fz"] + R["ceil"] / 1000, 4)))
    # coverage against the old point data (setting_out.locate)
    so = W["so"]
    old = {F: {r["id"]: r for r in so.locate(F)[1]} for F in ("GF", "FF")}
    ids = {(k[0], k[2]) for k in have}
    missing = [(F, i, r.get("room"), r.get("cat")) for F in old for i, r in old[F].items() if (F, i) not in ids and r.get("cat") not in ("water",)]
    # points that are not on a wall or ceiling (e.g. the peninsula-side socket C26): keep them from the point data, plan position only
    other = [dict(F=F, room=r.get("room", ""), id=i, cat=r["cat"], name=r.get("name", ""), h=r.get("h"), where=r.get("wall", ""),
                  note=r.get("why", ""), p=[round(r["p"][0], 4), round(r["p"][1], 4)])
             for F in old for i, r in old[F].items() if (F, i) not in ids and r.get("wall") in ("岛台", "地面", "室外地面")]
    REMOVED = {"L41": "围栏地灯取消，改户外灯带出线 L40（后院 Rev B）", "L42": "同 L41", "L43": "同 L41",
               "L10": "衣帽间两个筒灯合为一个吸顶灯 L14（主卧套间 Rev D）"}
    missing = [m + (REMOVED.get(m[1], "⚠ 未处理"),) for m in missing]
    other = [o for o in other if o["id"] not in REMOVED]
    missing = [m[:4] + ("取消：原热水器旁插座，改为洗衣房锅炉下 4 个单联 fused switch FU1–FU4（模型 v47，业主 2026-10-14）",) if m[0] == "GF" and m[1] == "C06" else m for m in missing]
    missing = [m if m[1] != "C26" else m[:4] + ("半岛台柜内插座（与 C23 同一线，h800，白色；业主 2026-10-14），只在平面（不在墙面）",) for m in missing]
    json.dump(dict(wall=rows, ceiling=ceil_rows, other=other, areas=areas, duplicates=dup, missing=missing), open(os.path.join(HERE, "_points_final.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    return rows, ceil_rows, dup, missing


if __name__ == "__main__":
    rows, ceil_rows, dup, missing = export()
    print(f"wall points {len(rows)}, ceiling {len(ceil_rows)}, duplicates {len(dup)}, old points not in any elevation {len(missing)}")
    for d in dup: print("  dup", d)
    for m in missing: print("  missing", m)
