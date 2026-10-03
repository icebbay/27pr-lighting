"""Feed lighting_<FLOOR>.json (from the web tool) into make_lighting_drawings.py / make_lighting_drawings_cn.py.

The scripts call apply_en(globals()) / apply_cn(globals()) when the LIGHTING_JSON environment variable points at a JSON file.
Every data table the scripts draw from is replaced; geometry of the walls still comes from the user's PPT (unchanged).
"""
import json, os


def load():
    return json.load(open(os.environ["LIGHTING_JSON"], encoding="utf-8"))


def apply_en(G):
    d = load()
    assert d["floor"] == G["FLOOR"], f"JSON is {d['floor']}, FLOOR is {G['FLOOR']}"
    G["LP"] = {l["id"]: (l["x"], l["y"]) for l in d["lights"]}
    G["LSHEET"] = {l["id"]: l["sheet"] for l in d["lights"]}
    G["PLATES"] = [(p["id"], p["panel"], p["location"], p["sheet"]) for p in d["plates"]]
    G["PANEL"] = {p["panel"]: (p["gangs"], list(p["keys"])) for p in d["plates"]}
    G["MOUNT"] = {p["panel"]: (p["x"], p["y"]) for p in d["plates"]}
    G["MOUNT"].update({f["panel"]: (f["x"], f["y"]) for f in d["fcus"]})
    k2p = {}
    for pn, (g, ks) in G["PANEL"].items():
        for k in ks:
            k2p.setdefault(k, []).append(pn)
    G["KEY2PANEL"] = k2p
    C = d["circuits"]
    G["CIRC"] = [(c["id"], c["name"], list(c["keys"]), list(c["lights"])) for c in C]
    G["CL"] = {c["id"]: c["letter"] for c in C}
    G["DESC"] = {c["id"]: c["name"] for c in C}
    G["TBC"] = {c["id"]: c["tbc"] for c in C if c.get("tbc")}
    G["ASSUMED"] = {c["id"]: c["assumed"] for c in C if c.get("assumed")}
    G["REMOTE"] = {c["id"]: list(c["remote"]) for c in C if c.get("remote")}
    G["KEY_CIRC"] = {k: c["id"] for c in C for k in c["keys"]}
    G["FCUS"] = [(f["id"], f["panel"], f["key"]) for f in d["fcus"]]
    G["PID"] = {pn: sid for sid, pn, _, _ in G["PLATES"]}
    G["PSHEET"] = {pn: sh for _, pn, _, sh in G["PLATES"]}
    G["ZONES"] = {int(z): dict(name=v["name"], view=tuple(v["view"]), member=tuple(v["member"])) for z, v in d["zones"].items()}
    sk = d.get("special_keys", {})
    G["EXTRA_KEYS"] = {k: v["text"] for k, v in sk.items()}
    G["EXTRA_TAG"] = {k: v.get("tag", "?") for k, v in sk.items()}
    G["RISER"] = {k: v["riser"] for k, v in sk.items() if v.get("riser")}
    G["GHOSTS"] = [(k, v["ghost"]) for k, v in sk.items() if v.get("ghost")]
    G["MIDDLE_KEYS"] = {(p["id"], k) for p in d["plates"] for k in p.get("middle_keys", [])}
    G["MIDDLE"] = {s for s, _ in G["MIDDLE_KEYS"]}
    G["DOORSW"] = [dict(x) for x in d.get("door_switches", [])]
    m = d["meta"]
    for k, g in (("version", "VERSION"), ("basis", "BASIS"), ("keyplan_note", "KEYPLAN_NOTE"), ("plate_note5", "PLATE_NOTE5"), ("fcu_row", "FCU_ROW")):
        if k in m: G[g] = m[k]
    if m.get("rev_cn"): G["REV_CN"] = m["rev_cn"]
    if os.environ.get("DST_OVERRIDE"): G["DST"] = os.environ["DST_OVERRIDE"]
    G["LIGHTING_DATA"] = d


def apply_cn(G):
    d = G.get("LIGHTING_DATA") or load()
    wl = {w: dict(v) for w, v in d["wl"].items()}
    other = {w: dict(v) for w, v in d.get("wl_other", {}).items()}
    G["WL"] = wl
    if d["floor"] == "GF":
        G["WL_GF_DEF"] = wl
        if other: G["WL_FF"] = other
    else:
        G["WL_FF"] = wl
        if other: G["WL_GF_DEF"] = other
    b = d["board"]
    G["AL1"] = (b["x"], b["y"]); G["BOARD_LABEL"] = b["label"]
    if d["meta"].get("cn_notes"): G["CN_NOTES"] = list(d["meta"]["cn_notes"])
