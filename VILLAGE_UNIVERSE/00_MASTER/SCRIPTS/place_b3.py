"""
BATCH 3 placement - environmental storytelling across the village (idempotent: rebuilds PRP_B3_STORYTELLING).

  patch the saved master:  blender -b MASTER_WORLD.blend --python place_b3.py
  from build_master_v2:    place_b3.place(scene, paths, plots, link_fn)

Every area gets a purpose: electric line along the roads (poles + sagging wires, transformer at the market),
open drains along the lanes, public taps at lane mouths, benches + bins + direction board at the chowk,
handcarts, bicycles and buntings on the market street, a bus stop + milestone at the village gate, charpais in
front of homes, the overhead water tank and a mobile tower on the outskirts.
"""
import datetime
import math
import os
import random
import shutil
import sys

import bpy
from mathutils import Matrix, Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import config_layout as C  # noqa: E402
import geo  # noqa: E402
import hero_lib as H  # noqa: E402
from geo import terrain_height  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
LIB = os.path.join(ROOT, "06_PROPS", "LIB_Props_B3.blend")
NAMES = ["AST_UtilityPole_A", "AST_TransformerPole_A", "AST_PublicTap_A", "AST_Charpai_A", "AST_Bicycle_A", "AST_Thela_A",
         "AST_Dustbin_A", "AST_BusStop_A", "AST_WaterTower_A", "AST_MobileTower_A", "AST_Milestone_A", "AST_DirectionBoard_A",
         "AST_StoneBench_A"]


def _link():
    with bpy.data.libraries.load(LIB, link=True) as (src, dst):
        dst.collections = [n for n in src.collections if n in NAMES]
    return {c.name: c for c in dst.collections if c}


def _clear_ok(P, paths, plots, road_extra, plot_margin, river_min=24.0):
    P = np.asarray(P, float).reshape(-1, 2)
    ok = np.ones(len(P), bool)
    for p in paths.values():
        ok &= geo.dist_to_polyline(P, p.pts) > p.width / 2.0 + road_extra
    for pl in plots:
        ok &= pl["obb"].dist_points(P) > plot_margin
    ok &= geo.river_distance(P[:, 0], P[:, 1]) > river_min
    return ok


def place(scene, paths, plots, assets=None, seed=8):
    rng = random.Random(seed)
    assets = assets or _link()
    coll = bpy.data.collections.get("PRP_B3_STORYTELLING")
    if coll is None:
        coll = bpy.data.collections.new("PRP_B3_STORYTELLING")
        scene.collection.children.link(coll)
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    n = {}

    def add(key, x, y, rz=0.0, s=1.0, dz=0.0):
        if key not in assets:
            return None
        e = bpy.data.objects.new("B3_%s_%03d" % (key[4:], n.get(key, 0) + 1), None)
        e.instance_type = "COLLECTION"
        e.instance_collection = assets[key]
        e.location = (x, y, float(terrain_height(x, y)) + dz)
        e.rotation_euler = (0, 0, rz)
        e.scale = (s, s, s)
        coll.objects.link(e)
        n[key] = n.get(key, 0) + 1
        return e

    mat_conc = bpy.data.materials.get("MAT_Concrete_Weathered") or H.mat_simple("MAT_Concrete_Weathered", "#A39C90", 0.85, noise=0.18)
    mat_wire = H.mat_simple("MAT_Wire_Black", "#121212", 0.5)
    mat_sludge = H.mat_simple("MAT_Drain_Sludge", "#2E3A2C", 0.15, noise=0.3)
    # ---- electric line: poles every ~38 m on one side of the main roads, wires sagging between them
    wire = HB()
    for rid, t0, t1, side in (("R01", 0, 660, -1), ("R02", 12, 330, 1), ("R04", 8, 85, -1), ("R04", 165, 420, -1),
                              ("R05", 10, 300, 1), ("L01", 8, 130, -1), ("L02", 8, 110, 1), ("L03", 8, 125, 1), ("L04", 8, 90, -1)):
        p = paths.get(rid)
        if p is None:
            continue
        prev = None
        for t in np.arange(t0, min(t1, p.length), 38.0 if rid.startswith("R") else 30.0):
            q = p.point(t) + p.normal(t) * side * (p.width / 2 + 1.6)
            if not _clear_ok([q], paths, plots, 1.0, 0.8, 22.0)[0]:
                prev = None
                continue
            tg = p.tangent(t)
            rz = math.atan2(tg[1], tg[0])
            key = "AST_TransformerPole_A" if (rid == "R02" and abs(t - 88) < 19) else "AST_UtilityPole_A"
            e = add(key, q[0], q[1], rz)
            if e is None:
                continue
            wp = [e.matrix_world @ Vector(w) for w in assets[key].get("wire_points", [])]
            bpy.context.view_layer.update()
            wp = [Matrix.Translation(e.location) @ Matrix.Rotation(rz, 4, "Z") @ Vector(w) for w in assets[key].get("wire_points", [])]
            if prev is not None and len(prev) == len(wp):
                for a, b in zip(prev, wp):
                    a, b = np.array(a[:]), np.array(b[:])
                    L = float(np.linalg.norm(b - a))
                    sag = 0.012 * L + 0.25
                    pts = [a + (b - a) * k / 10 - np.array([0, 0, sag * 4 * (k / 10) * (1 - k / 10)]) for k in range(11)]
                    for u, v in zip(pts[:-1], pts[1:]):
                        wire.rod(mat_wire, u, v, 0.007, 4)
            prev = wp
    wo = bpy.data.objects.new("B3_GEO_PowerLines", wire.to_mesh("ME_B3_PowerLines", recalc=False))
    wo.visible_shadow = True
    coll.objects.link(wo)
    # ---- open drains (nali) along the lanes and the market street, both sides
    dr = HB()
    for rid in ("L01", "L02", "L03", "L04", "L05", "R02"):
        p = paths.get(rid)
        if p is None:
            continue
        for side in (-1, 1):
            V, F, VW, FW = [], [], [], []
            ts = np.arange(2.0, p.length - 2.0, 1.0)
            for k, t in enumerate(ts):
                c = p.point(t) + p.normal(t) * side * (p.width / 2 + 0.3)
                nv = p.normal(t) * side
                z = float(terrain_height(c[0], c[1]))
                for off, dz in ((-0.24, 0.06), (-0.14, 0.06), (-0.14, -0.22), (0.14, -0.22), (0.14, 0.06), (0.24, 0.06)):
                    q = c + nv * off
                    V.append((q[0], q[1], z + dz))
                if k:
                    o = (k - 1) * 6
                    for j in range(5):
                        F.append((o + j, o + j + 1, o + j + 7, o + j + 6))
            if F:
                dr.add(V, F, mat_conc)
                # sludge strip at the bottom
                W = []
                for k, t in enumerate(ts):
                    c = p.point(t) + p.normal(t) * side * (p.width / 2 + 0.3)
                    nv = p.normal(t) * side
                    z = float(terrain_height(c[0], c[1])) - 0.17
                    W += [tuple((c - nv * 0.13).tolist() + [z]), tuple((c + nv * 0.13).tolist() + [z])]
                dr.add(W, [(2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2) for k in range(len(ts) - 1)], mat_sludge)
    coll.objects.link(bpy.data.objects.new("B3_GEO_Drains", dr.to_mesh("ME_B3_Drains", recalc=False)))
    # ---- public taps at lane mouths, benches / bins / board at the chowk
    for rid in ("L01", "L02", "L03", "L04", "L05"):
        p = paths.get(rid)
        if p is None:
            continue
        q = p.point(5.0) + p.normal(5.0) * (p.width / 2 + 1.6)
        if _clear_ok([q], paths, plots, 0.9, 0.6, 22.0)[0]:
            add("AST_PublicTap_A", q[0], q[1], rng.uniform(0, 6.28))
    for k in range(8):
        a = 2 * math.pi * (k + 0.25) / 8
        q = np.array([math.cos(a), math.sin(a)]) * (C.CHOWK_RADIUS - 3.0)
        if _clear_ok([q], paths, {}, 0.6, 0.0, 0.0)[0]:
            add("AST_StoneBench_A", q[0], q[1], a + math.pi / 2, dz=0.18)
    for k in range(4):
        a = 2 * math.pi * (k + 0.6) / 4
        q = np.array([math.cos(a), math.sin(a)]) * (C.CHOWK_RADIUS + 2.0)
        if _clear_ok([q], paths, plots, 0.4, 0.5, 0.0)[0]:
            add("AST_Dustbin_A", q[0], q[1], 0.0)
    p = paths["R03"]
    q = p.point(6.0) + p.normal(6.0) * (p.width / 2 + 1.2)
    add("AST_DirectionBoard_A", q[0], q[1], math.atan2(p.tangent(6.0)[1], p.tangent(6.0)[0]) + math.pi / 2)
    # ---- market street: handcarts, bicycles, buntings
    p = paths["R02"]
    for t in (35.0, 78.0, 140.0):
        side = 1 if t != 78.0 else -1
        q = p.point(t) + p.normal(t) * side * (p.width / 2 - 0.9)
        add("AST_Thela_A", q[0], q[1], math.atan2(p.tangent(t)[1], p.tangent(t)[0]))
    bunt = HB()
    flag_mats = [H.mat_simple("MAT_Bunting_%d" % k, c, 0.7) for k, c in enumerate(("#E8402A", "#F2B82A", "#2E8B4A", "#2F6FB5", "#E86AA0"))]
    for t in np.arange(20.0, min(190.0, p.length), 16.0):
        a = p.point(t) + p.normal(t) * (p.width / 2 + 0.6)
        b = p.point(t + 3.0) - p.normal(t + 3.0) * (p.width / 2 + 0.6)
        za = float(terrain_height(a[0], a[1])) + 5.2
        zb = float(terrain_height(b[0], b[1])) + 5.2
        A, Bv = np.array([a[0], a[1], za]), np.array([b[0], b[1], zb])
        L = float(np.linalg.norm(Bv - A))
        prevp = A
        for k in range(1, 21):
            f = k / 20
            q = A + (Bv - A) * f - np.array([0, 0, 0.6 * 4 * f * (1 - f)])
            bunt.rod(mat_wire, prevp, q, 0.004, 3)
            if k % 1 == 0 and k < 20:
                d = (q - prevp) / (np.linalg.norm(q - prevp) + 1e-9)
                bunt.add([tuple(prevp), tuple(q), tuple((prevp + q) / 2 - np.array([0, 0, 0.32]))], [(0, 1, 2), (2, 1, 0)],
                         flag_mats[(k + int(t)) % len(flag_mats)])
            prevp = q
    coll.objects.link(bpy.data.objects.new("B3_GEO_Buntings", bunt.to_mesh("ME_B3_Buntings", recalc=False)))
    # ---- homes and shops: charpais, bicycles
    for pl in plots:
        fam = pl["family"]
        c, s_ = math.cos(pl["rot"]), math.sin(pl["rot"])

        def local(lx, ly):
            return pl["x"] + lx * c - ly * s_, pl["y"] + lx * s_ + ly * c
        if fam in ("house_common", "house_small", "house_middle") and rng.random() < 0.55:
            x, y = local(pl["w"] / 2 + 1.4, -pl["d"] / 2 - 0.4)
            if _clear_ok([(x, y)], paths, [q for q in plots if q is not pl], 0.6, 0.6, 22.0)[0]:
                add("AST_Charpai_A", x, y, pl["rot"] + rng.uniform(-0.4, 0.4))
        if fam in ("shop", "shop_2storey", "house_middle") and rng.random() < 0.5:
            x, y = local(rng.uniform(-1.5, 1.5), -pl["d"] / 2 - 1.1)
            add("AST_Bicycle_A", x, y, pl["rot"] + rng.uniform(-0.2, 0.2))
    # ---- village gate: bus stop + milestone;  outskirts: water tower, mobile tower
    p = paths["R01"]
    for t, key, side in ((600.0, "AST_BusStop_A", 1), (520.0, "AST_Milestone_A", -1)):
        q = p.point(t) + p.normal(t) * side * (p.width / 2 + (2.8 if key.endswith("BusStop_A") else 1.0))
        tg = p.tangent(t)
        add(key, q[0], q[1], math.atan2(tg[1], tg[0]) + (math.pi if side > 0 else 0.0) + math.pi / 2 * 0)
    for key, cand in (("AST_WaterTower_A", [(-70, 140), (-95, 120), (-40, 175), (60, 150)]),
                      ("AST_MobileTower_A", [(-210, -135), (-250, 60), (300, 120), (-180, 260)])):
        for (x, y) in cand:
            if _clear_ok([(x, y)], paths, plots, 8.0, 8.0, 40.0)[0]:
                add(key, x, y, rng.uniform(0, 6.28))
                break
    print("[b3] placed: " + ", ".join("%s %d" % (k[4:], v) for k, v in sorted(n.items())))
    return coll


if __name__ == "__main__":
    from layout_solver import LayoutSolver
    path = bpy.data.filepath
    shutil.copy2(path, os.path.join(ROOT, "99_ARCHIVE", "MASTER_WORLD_preB3_%s.blend" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    solver = LayoutSolver()
    plots = solver.solve()
    place(bpy.context.scene, solver.paths, plots)
    bpy.ops.wm.save_mainfile()
    print("[b3] saved", path)
