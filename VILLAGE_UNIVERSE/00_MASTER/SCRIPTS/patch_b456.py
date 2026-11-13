"""
Batches 4-6 applied to the saved MASTER_WORLD (checkpoint first; idempotent - rebuilds its own collections).

  blender -b MASTER_WORLD.blend --python patch_b456.py

B5  refresh master-local materials in place (terrain, roads, crops, bunds, water, palette) from the upgraded
    hero_lib / master_materials functions
B4  ENV_B4_VEGETATION: bamboo along the river + village edge, eucalyptus rows on the approach road and far field
    edges, babool on dry outskirts / north valley, gulmohar at school / panchayat / temple road / chowk, ashoka
    at the temple and school, ber shrubs on bunds and yards, sugarcane on selected fields, hedges on lane edges
B6  ENV_B6_GROUND: footpaths (pagdandi) from homes out to the fields, pebble/stone scatter, a far ridge ring
    for layered distant hills.  Heights come from raycasting the built terrain mesh.
"""
import datetime
import math
import os
import random
import shutil
import sys

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import config_layout as C  # noqa: E402
import geo  # noqa: E402
import hero_lib as H  # noqa: E402
import master_materials as MM  # noqa: E402
from hero_lib import HB  # noqa: E402
from layout_solver import LayoutSolver  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
LIB_B4 = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Trees_B4.blend")
B4_NAMES = ["VEG_Bamboo_Clump_A", "VEG_Eucalyptus_A", "VEG_Babool_A", "VEG_Gulmohar_A", "VEG_Ashoka_A", "VEG_Ber_Shrub_A",
            "AST_Sugarcane_Patch_A", "AST_Hedge_Row_A"]


class Ground:
    def __init__(self):
        dg = bpy.context.evaluated_depsgraph_get()
        self.t = BVHTree.FromObject(bpy.data.objects["OBJ_Terrain_Master"], dg)

    def h(self, x, y):
        hit = self.t.ray_cast(Vector((x, y, 2000.0)), Vector((0, 0, -1)))
        return hit[0].z if hit[0] is not None else float(geo.terrain_height(x, y))


def fresh_coll(scene, name):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        scene.collection.children.link(c)
    for o in list(c.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    return c


def bake(coll, name):
    """Realize the leaf instances of a library collection into one shared local mesh (memory-safe)."""
    old = bpy.data.collections.get(name)
    if old is not None:
        return old
    me0 = bpy.data.meshes.new("TMP")
    tmp = bpy.data.objects.new("TMP_" + name, me0)
    bpy.context.scene.collection.objects.link(tmp)
    ng = bpy.data.node_groups.new("TMP_GN", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    go = ng.nodes.new("NodeGroupOutput")
    ng.nodes.new("NodeGroupInput")
    ci = ng.nodes.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = coll
    ci.transform_space = "ORIGINAL"
    ri = ng.nodes.new("GeometryNodeRealizeInstances")
    ng.links.new(ci.outputs[0], ri.inputs[0])
    ng.links.new(ri.outputs[0], go.inputs[0])
    tmp.modifiers.new("Bake", "NODES").node_group = ng
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    me.name = "ME_" + name
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(me0)
    bpy.data.node_groups.remove(ng)
    c = bpy.data.collections.new(name)
    proto = bpy.data.collections.get("PROTO_LIBRARY")
    (proto or bpy.context.scene.collection).children.link(c)
    c.objects.link(bpy.data.objects.new(name, me))
    return c


def clear_ok(P, paths, plots, road_extra, plot_margin, river_min):
    P = np.asarray(P, float).reshape(-1, 2)
    ok = np.ones(len(P), bool)
    for p in paths.values():
        ok &= geo.dist_to_polyline(P, p.pts) > p.width / 2.0 + road_extra
    for pl in plots:
        ok &= pl["obb"].dist_points(P) > plot_margin
    ok &= geo.river_distance(P[:, 0], P[:, 1]) > river_min
    return ok


# ------------------------------------------------------------------------------------------------ B5
def refresh_materials():
    M = MM.upgrade_palette({})                     # rebuilds every palette / terrain / road / crop material in place
    H.mat_ground("MAT_Ground_Bund_Grass")
    H.mat_stone_blocks()
    print("[b5] master materials refreshed:", len(M))


# ------------------------------------------------------------------------------------------------ B4
def vegetation(scene, G, paths, plots, rng):
    with bpy.data.libraries.load(LIB_B4, link=True) as (src, dst):
        dst.collections = [n for n in src.collections if n in B4_NAMES]
    lib = {c.name: c for c in dst.collections if c}
    baked = {k: bake(v, k + "_BAKED") for k, v in lib.items()}
    coll = fresh_coll(scene, "ENV_B4_VEGETATION")
    taken = [(o.matrix_world.translation.x, o.matrix_world.translation.y) for o in scene.objects
             if o.instance_type == "COLLECTION" and o.instance_collection and o.instance_collection.name.startswith(("VEG_", "AST_Sugar"))]
    grid = {}
    for (x, y) in taken:
        grid.setdefault((int(x // 6), int(y // 6)), []).append((x, y))
    n = {}

    def free(x, y, r):
        for i in range(int(x // 6) - 2, int(x // 6) + 3):
            for j in range(int(y // 6) - 2, int(y // 6) + 3):
                for (px, py) in grid.get((i, j), []):
                    if (px - x) ** 2 + (py - y) ** 2 < r * r:
                        return False
        return True

    def put(key, x, y, s=1.0, r=5.0, check=True, rz=None, road_extra=2.5, plot_margin=2.5, river_min=22.0):
        if check and (not free(x, y, r) or not clear_ok([(x, y)], paths, plots, road_extra, plot_margin, river_min)[0]):
            return False
        e = bpy.data.objects.new("B4_%s_%03d" % (key.split("_")[1], n.get(key, 0) + 1), None)
        e.instance_type = "COLLECTION"
        e.instance_collection = baked[key]
        e.location = (x, y, G.h(x, y))
        e.rotation_euler = (0, 0, rng.uniform(0, 6.28) if rz is None else rz)
        sc = s * rng.uniform(0.85, 1.15)
        e.scale = (sc, sc, sc * rng.uniform(0.92, 1.1))
        coll.objects.link(e)
        grid.setdefault((int(x // 6), int(y // 6)), []).append((x, y))
        n[key] = n.get(key, 0) + 1
        return True

    rp = geo.river_path()
    for t in np.arange(0, rp.length, 9.0):                                    # bamboo along the banks
        q = rp.point(t)
        if not (-450 < q[1] < 700) or rng.random() < 0.45:
            continue
        side = rng.choice((-1, 1))
        p = q + rp.normal(t) * side * rng.uniform(26, 40)
        put("VEG_Bamboo_Clump_A", p[0], p[1], rng.uniform(0.8, 1.1), 7.0)
    for _ in range(40):                                                       # bamboo + ber at the village edge
        a, r = rng.uniform(0, 6.28), rng.uniform(150, 230)
        put(rng.choice(["VEG_Bamboo_Clump_A", "VEG_Ber_Shrub_A", "VEG_Ber_Shrub_A"]), r * math.cos(a), r * math.sin(a) * 0.9, 1.0, 5.0)
    p = paths["R01"]
    for t in np.arange(0, 500, 11.0):                                         # eucalyptus rows on the approach road
        for side in (-1, 1):
            q = p.point(t) + p.normal(t) * side * (p.width / 2 + 9.0 + rng.uniform(-0.6, 0.6))
            put("VEG_Eucalyptus_A", q[0], q[1], rng.uniform(0.85, 1.15), 4.0, road_extra=6.0)
    for _ in range(140):                                                      # babool on dry outskirts + north valley
        x, y = rng.uniform(-620, 760), rng.uniform(-640, 860)
        if math.hypot(x / 1.2, y) < 360:
            continue
        put("VEG_Babool_A", x, y, rng.uniform(0.8, 1.25), 9.0)
    for (fam, keys, dist) in (("school", ["VEG_Gulmohar_A", "VEG_Ashoka_A"], 24.0), ("panchayat", ["VEG_Gulmohar_A"], 12.0),
                              ("temple", ["VEG_Ashoka_A", "VEG_Gulmohar_A"], 15.0)):
        for pl in [q for q in plots if q["family"] == fam]:
            c, s_ = math.cos(pl["rot"]), math.sin(pl["rot"])
            for k in range(6):
                lx = rng.uniform(-pl["w"] / 2 - 4, pl["w"] / 2 + 4)
                ly = -pl["d"] / 2 - rng.uniform(3.0, 7.0)
                x, y = pl["x"] + lx * c - ly * s_, pl["y"] + lx * s_ + ly * c
                put(rng.choice(keys), x, y, 1.0, 7.0, plot_margin=1.5)
    p = paths["R03"]
    for t in np.arange(8, p.length, 14.0):                                    # gulmohar along the temple road
        side = 1 if int(t) % 2 else -1
        q = p.point(t) + p.normal(t) * side * (p.width / 2 + 3.0)
        put("VEG_Gulmohar_A", q[0], q[1], 0.9, 8.0, road_extra=1.5, plot_margin=1.5)
    for k in range(5):                                                        # gulmohar at the chowk edge
        a = 2 * math.pi * (k + 0.1) / 5
        put("VEG_Gulmohar_A", (C.CHOWK_RADIUS + 9) * math.cos(a), (C.CHOWK_RADIUS + 9) * math.sin(a), 0.85, 8.0, road_extra=2.0, plot_margin=2.0)
    for rid in ("L01", "L02", "L03", "L04", "R05"):                          # hedges on lane edges
        p = paths[rid]
        for t in np.arange(10, min(p.length, 150), 4.6):
            if rng.random() < 0.55:
                continue
            side = rng.choice((-1, 1))
            q = p.point(t) + p.normal(t) * side * (p.width / 2 + 1.4)
            tg = p.tangent(t)
            put("AST_Hedge_Row_A", q[0], q[1], 1.0, 1.5, rz=math.atan2(tg[1], tg[0]), road_extra=0.9, plot_margin=1.2)
    # sugarcane: replace the crop look on a few field cells by tiling patches over them
    cells = [((-300, -260), (-90, -40)), ((240, 290), (-260, -200)), ((-420, -380), (60, 110)), ((40, 80), (-420, -380)),
             ((260, 300), (40, 90)), ((-230, -190), (-300, -260))]
    for (xa, xb), (ya, yb) in cells:
        for x in np.arange(xa + 4, xb - 3, 8.0):
            for y in np.arange(ya + 4, yb - 3, 8.0):
                put("AST_Sugarcane_Patch_A", x, y, 1.0, 0.1, rz=0.0, road_extra=4.5, plot_margin=4.0, river_min=26.0)
    print("[b4] placed: " + ", ".join("%s %d" % (k.split("_")[1], v) for k, v in sorted(n.items())))


# ------------------------------------------------------------------------------------------------ B6
def ground_detail(scene, G, paths, plots, rng):
    coll = fresh_coll(scene, "ENV_B6_GROUND")
    path_mat = bpy.data.materials.get("MAT_Road_Dirt_Lane") or MM.road_dirt("MAT_Road_Dirt_Lane", "#B49A76", grass_mid=True)
    hb = HB()
    homes = [p for p in plots if p["family"] in ("house_small", "house_common", "house_middle", "cattle_shed")]
    k = 0
    for pl in rng.sample(homes, min(18, len(homes))):
        c, s_ = math.cos(pl["rot"]), math.sin(pl["rot"])
        back = np.array([pl["x"] - (-s_) * (pl["d"] / 2 + 1.5), pl["y"] - c * (pl["d"] / 2 + 1.5)])
        out = back - np.array([pl["x"], pl["y"]])
        out /= np.linalg.norm(out) + 1e-9
        L = rng.uniform(30, 70)
        side = np.array([-out[1], out[0]])
        ctrl = [back, back + out * L * 0.35 + side * rng.uniform(-6, 6), back + out * L * 0.7 + side * rng.uniform(-8, 8), back + out * L]
        P = geo.catmull_rom([tuple(q) for q in ctrl], 12)
        ok = clear_ok(P, paths, [q for q in plots if q is not pl], -0.5, 0.3, 24.0)
        if ok.mean() < 0.85:
            continue
        V, F = [], []
        for i, q in enumerate(P):
            tg = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
            tg /= np.linalg.norm(tg) + 1e-9
            nv = np.array([-tg[1], tg[0]])
            w = 0.45 + 0.1 * math.sin(i * 0.7)
            for sgn in (-1, 1):
                p2 = q + nv * w * sgn
                V.append((p2[0], p2[1], G.h(p2[0], p2[1]) + 0.04))
            if i:
                a = 2 * (i - 1)
                F.append((a, a + 1, a + 3, a + 2))
        hb.add(V, F, path_mat)
        k += 1
    po = bpy.data.objects.new("B6_GEO_Footpaths", hb.to_mesh("ME_B6_Footpaths", recalc=False))
    coll.objects.link(po)
    # pebbles / small stones: one rock mesh instanced by GN points near paths, yards and the river edge
    rock = HB()
    stone = H.mat_simple("MAT_Stone_Pebble", "#8A8174", 0.85, noise=0.3)
    rock.ellipsoid(0, 0, 0.03, 0.09, 0.07, 0.05, stone, 7, 4)
    rme = rock.to_mesh("ME_B6_Pebble", recalc=False)
    src = bpy.data.objects.new("SRC_B6_Pebble", rme)
    srcc = bpy.data.collections.get("PROTO_LIBRARY") or scene.collection
    srcc.objects.link(src)
    nrng = np.random.default_rng(6)
    Pc = np.c_[nrng.uniform(-420, 420, 60000), nrng.uniform(-420, 420, 60000)]
    ok = clear_ok(Pc, paths, plots, 0.2, 0.3, 19.0)
    Pc = Pc[ok]
    Pc = Pc[nrng.random(len(Pc)) < 0.12]
    pts = [(x, y, G.h(x, y) - 0.02) for x, y in Pc]
    R = [(nrng.uniform(-0.3, 0.3), nrng.uniform(-0.3, 0.3), nrng.uniform(0, 6.28)) for _ in pts]
    S = [float(nrng.uniform(0.5, 2.6) ** 1.3) for _ in pts]
    po2 = H.points_object("B6_GEO_Pebbles", pts, R, S, coll, H.instancer("GN_B6_Pebbles", src))
    po2.visible_shadow = False                      # tiny + many: shadows would blow EEVEE's shadow map on 8 GB
    # far ridge ring: layered silhouettes far behind the backdrop (mist turns them blue)
    fr = HB()
    far = H.mat_simple("MAT_Far_Hills", "#5E7356", 0.95, noise=0.2)
    nu, nv = 180, 4
    V = []
    for j in range(nv):
        r = 6200.0 + j * 700.0
        for i in range(nu):
            a = 2 * math.pi * i / nu
            north = 0.6 + 0.4 * max(math.sin(a), 0.0)
            hgt = (260 + 220 * math.sin(a * 3.0 + j) + 120 * math.sin(a * 11.0 + 2 * j)) * north * (1.0 if 0 < j < nv - 1 else 0.0) - 60
            V.append((r * math.cos(a), r * math.sin(a), hgt))
    F = [(j * nu + i, j * nu + (i + 1) % nu, (j + 1) * nu + (i + 1) % nu, (j + 1) * nu + i) for j in range(nv - 1) for i in range(nu)]
    fr.add(V, F, far)
    coll.objects.link(bpy.data.objects.new("B6_GEO_FarRidges", fr.to_mesh("ME_B6_FarRidges", recalc=False)))
    print("[b6] footpaths %d, pebbles %d, far ridges ring" % (k, len(pts)))


if __name__ == "__main__":
    path = bpy.data.filepath
    shutil.copy2(path, os.path.join(ROOT, "99_ARCHIVE", "MASTER_WORLD_preB456_%s.blend" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    solver = LayoutSolver()
    plots = solver.solve()
    rng = random.Random(456)
    G = Ground()
    refresh_materials()
    vegetation(bpy.context.scene, G, solver.paths, plots, rng)
    ground_detail(bpy.context.scene, G, solver.paths, plots, rng)
    bpy.ops.wm.save_mainfile()
    print("[b456] saved", path)
