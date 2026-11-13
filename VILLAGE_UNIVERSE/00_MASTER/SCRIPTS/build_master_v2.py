"""
AMALTASPUR - MASTER WORLD v2 (Phase 1b integration).

  blender -b --factory-startup --python build_master_v2.py

Rebuilds MASTER_WORLD.blend from the approved layout (config_layout.py) and swaps in the approved hero
libraries (all LINKED, so updating a library updates the village):
  house_common plots -> HERO_House_Common_A        cattle_shed plots -> AST_Tabela_A
  trees -> LIB_Trees (LOD1 scatter, hero banyan at the chowk, hero peepal at the temple)
  river -> closed water body + AST_Bridge_Stone_A + AST_Ghat_A      north -> mountains + waterfall
  props -> street lights, lantern posts, hand pumps, planters, bougainvillea, banana, hibiscus, haystacks
Other building families keep their blockout massing but get production materials (hero passes pending).
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

import build_blockout as B  # noqa: E402
import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402
import config_layout as C  # noqa: E402
import geo  # noqa: E402
import master_materials as MM  # noqa: E402
from bld_meshes import OBJECT_PREFIX, MeshBuilder, build_plot_mesh  # noqa: E402
from geo import OBB, Path2D, river_distance, river_path, terrain_height  # noqa: E402
from layout_solver import LayoutSolver  # noqa: E402

ROOT = B.ROOT
LIBS = {
    "house": os.path.join(ROOT, "02_ARCHITECTURE", "HOUSES_MEDIUM", "HERO_House_Common_A.blend"),
    "trees": os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Trees.blend"),
    "river": os.path.join(ROOT, "01_ENVIRONMENT", "WATER", "LIB_River_Bridge_Ghat.blend"),
    "props": os.path.join(ROOT, "06_PROPS", "LIB_Village_Props.blend"),
    "mtn": os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Mountains_Waterfall.blend"),
    "farm": os.path.join(ROOT, "06_PROPS", "LIB_Farm_Props.blend"),
    "banyan": os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Hero_Banyan.blend"),
}
BRIDGE_RAMP = 36.0          # bridge asset half-length incl. ramps (m)
GHAT_LOCAL_Y = 38.0         # ghat centre in the river-kit's local frame
LOG = B.LOG
log = B.log


def link_collections(path, names):
    with bpy.data.libraries.load(path, link=True) as (src, dst):
        dst.collections = [c for c in src.collections if c in names]
    got = {c.name: c for c in dst.collections if c}
    missing = [n for n in names if n not in got]
    if missing:
        log("WARNING missing in %s: %s" % (os.path.basename(path), missing))
    return got


def inst(coll, name, loc, rz=0.0, s=1.0, target="PRP_ASSETS"):
    e = bpy.data.objects.new(name, None)
    e.instance_type = "COLLECTION"
    e.instance_collection = coll
    e.location = tuple(float(v) for v in loc)
    e.rotation_euler = (0.0, 0.0, float(rz))
    e.scale = (s, s, s)
    B.COLL[target].objects.link(e)
    return e


def plot_xf(p, lx, ly):
    c, s = math.cos(p["rot"]), math.sin(p["rot"])
    return np.array([p["x"] + lx * c - ly * s, p["y"] + lx * s + ly * c])


# ============================================================================
def ghat_frame():
    rv = river_path()
    target = np.array([128.0, 50.0])
    ti, _ = rv.nearest_t(target)
    q = rv.point(ti)
    u = (target - q) / np.linalg.norm(target - q)          # river -> bank
    a = math.atan2(-u[1], -u[0])                            # local +X points bank -> river
    R = np.array([[math.cos(a), -math.sin(a)], [math.sin(a), math.cos(a)]])
    loc = q - R @ np.array([0.0, GHAT_LOCAL_Y])
    return loc, a, R


def ghat_cut_fn():
    loc, a, R = ghat_frame()
    Rt = R.T

    def cut(x, y, h):
        P = np.stack([x - loc[0], y - loc[1]], 1) @ Rt.T
        lx, ly = P[:, 0], P[:, 1]
        inside = (ly > GHAT_LOCAL_Y - 11.8) & (ly < GHAT_LOCAL_Y + 11.8) & (lx > -28.5) & (lx < -8.0)
        step_z = 0.55 - (lx + 28.0) / 16.5 * (0.55 - (C.WATER_Z - 0.9)) - 0.35
        return np.where(inside, np.minimum(h, step_z), h)
    return cut


# ============================================================================
def build_water(M):
    """Closed river body (top at water level, bottom below the bed) so volume absorption gives depth colour."""
    rp = Path2D(C.RIVER_CTRL, 30.0, step=4.0)
    ts = rp.ts
    hw = 21.0
    top, bot = [], []
    for t in ts:
        p, n = rp.point(t), rp.normal(t)
        for s in (1, -1):
            q = p + n * hw * s
            top.append((q[0], q[1], C.WATER_Z))
            bot.append((q[0], q[1], C.RIVER_BED_Z - 0.8))
    v = top + bot
    N = len(top)
    f = []
    for i in range(len(ts) - 1):
        a = 2 * i
        f.append((a, a + 2, a + 3, a + 1))                       # top
        f.append((N + a, N + a + 1, N + a + 3, N + a + 2))       # bottom
        f.append((a, N + a, N + a + 2, a + 2))                   # side +
        f.append((a + 1, a + 3, N + a + 3, N + a + 1))           # side -
    f.append((0, 1, N + 1, N))
    e = 2 * (len(ts) - 1)
    f.append((e, N + e, N + e + 1, e + 1))
    B.mesh_object("OBJ_River_Water_Body", v, f, M["water"], "ENV_WATER")
    log("River: closed water body %.0f m" % rp.length)


def build_roads(M, paths, skip):
    kinds = {"paved": "road_paved", "dirt_main": "road_dirt_main", "dirt": "road_lane", "stone": "road_stone"}
    for rid, spec in C.ROADS.items():
        path = paths[rid]
        off = C.ROAD_Z_OFFSET[spec["kind"]]
        segs = [(0.0, path.length)]
        if rid in skip:
            a, b = skip[rid]
            segs = [(0.0, max(0.0, a)), (min(path.length, b), path.length)]
        for k, (t0, t1) in enumerate(segs):
            if t1 - t0 < 2.0:
                continue
            ts = np.arange(t0, t1 + 1e-6, 2.0)
            if ts[-1] < t1:
                ts = np.append(ts, t1)
            V, F, UV = [], [], []
            hw = spec["width"] / 2.0
            for t in ts:
                p, n = path.point(t), path.normal(t)
                for s in (1, -1):
                    q = p + n * hw * s
                    V.append([q[0], q[1], 0.0])
            Va = np.array(V)
            Va[:, 2] = terrain_height(Va[:, 0], Va[:, 1]) + off
            for i in range(len(ts) - 1):
                a = 2 * i
                F.append((a, a + 2, a + 3, a + 1))
            name = "OBJ_Road_%s_%s%s" % (rid, spec["name"], "" if k == 0 else "_B")
            obj = B.mesh_object(name, Va.tolist(), F, M[kinds[spec["kind"]]], "ENV_ROADS")
            me = obj.data
            uvl = me.uv_layers.new(name="UVMap")
            for poly in me.polygons:
                for li in poly.loop_indices:
                    vi = me.loops[li].vertex_index
                    uvl.data[li].uv = (0.0 if vi % 2 == 0 else 1.0, float(ts[vi // 2]) / (2 * hw))
    n = 48
    verts = [(0.0, 0.0, 0.0)] + [(C.CHOWK_RADIUS * math.cos(2 * math.pi * i / n),
                                  C.CHOWK_RADIUS * math.sin(2 * math.pi * i / n), 0.0) for i in range(n)]
    V = np.array(verts)
    V[:, 2] = terrain_height(V[:, 0], V[:, 1]) + 0.18
    B.mesh_object("OBJ_Chowk_Plaza", V.tolist(), [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)], M["chowk_stone"], "ENV_ROADS")
    kerb = H.mat_simple("MAT_Stone_Kerb", "#9A9182", 0.8, noise=0.15)
    hb = HB()
    nk = 120
    for i in range(nk):                                   # dressed-stone kerb so the plaza edge reads as built
        a0, a1 = 2 * math.pi * i / nk, 2 * math.pi * (i + 0.94) / nk
        am = (a0 + a1) / 2
        c = np.array([math.cos(am), math.sin(am)]) * (C.CHOWK_RADIUS + 0.1)
        zc = float(terrain_height(c[0], c[1]))
        L = (a1 - a0) * C.CHOWK_RADIUS
        hb.obox(kerb, (c[0], c[1], zc + 0.06), (-math.sin(am), math.cos(am), 0), (math.cos(am), math.sin(am), 0),
                L / 2, 0.22, 0.25)
    B.place_obj(hb, "OBJ_Chowk_Kerb", "ENV_ROADS", (0, 0, 0))
    log("Roads: UV-mapped ribbons; R04 cut for the bridge between t=%.0f..%.0f" % skip.get("R04", (0, 0)))


def bridge_offset(empty, c, along, normal):
    """Measure (on the evaluated, bent instance) how far the bridge ends sit sideways from the road line."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    offs = []
    for di in dg.object_instances:
        if not di.is_instance or di.parent is None or di.parent.original.name != empty.name:
            continue
        ob = di.object
        if ob.type != "MESH":
            continue
        me = ob.to_mesh()
        mw = np.array(di.matrix_world)
        co = np.array([v.co[:] for v in me.vertices])
        ob.to_mesh_clear()
        co = (np.c_[co, np.ones(len(co))] @ mw.T)[:, :2] - c
        a = co @ along
        ends = co[np.abs(a) > np.abs(a).max() - 2.0]
        offs.append(float((ends @ normal).mean()))
    return float(np.mean(offs)) if offs else 0.0


def place_river_kit(M, paths):
    kit = link_collections(LIBS["river"], ["AST_Bridge_Stone_A", "AST_Ghat_A"])
    skip = {}
    if "AST_Bridge_Stone_A" in kit:
        tc, _, _ = B.bridge_profile(paths)
        p = paths["R04"]
        c = p.point(tc)
        tg = p.tangent(tc)
        ang = math.atan2(tg[1], tg[0])
        n = np.array([-math.sin(ang), math.cos(ang)])
        e = inst(kit["AST_Bridge_Stone_A"], "INST_Landmark_Bridge_Stone_A", (c[0], c[1], 0.0), ang, target="BLD_LANDMARKS")
        off = bridge_offset(e, c, np.array([math.cos(ang), math.sin(ang)]), n)
        e.location = (c[0] - n[0] * off, c[1] - n[1] * off, 0.0)
        skip["R04"] = (tc - BRIDGE_RAMP + 0.5, tc + BRIDGE_RAMP - 0.5)
        log("Bridge v002 placed on R04 t=%.0f, end-offset correction %.2f m" % (tc, off))
    if "AST_Ghat_A" in kit:
        loc, a, R = ghat_frame()
        inst(kit["AST_Ghat_A"], "INST_Landmark_Ghat_A", (loc[0], loc[1], 0.0), a, target="BLD_LANDMARKS")
        log("Ghat placed below the temple")
    return skip


# ============================================================================
HERO_FAMILIES = {"house_small": ["AST_House_Small_Kaccha_A"], "house_middle": ["AST_House_Middle_A"], "house_rich": ["AST_Haveli_A"],
                 "shop": ["AST_Shop_Kirana_A", "AST_Shop_Chai_A", "AST_Shop_Cloth_A"], "shop_2storey": ["AST_Shop2_Hardware_A"],
                 "temple": ["AST_Temple_Shiv_A"], "school": ["AST_School_A"], "panchayat": ["AST_Panchayat_A"]}
HERO_ASSETS = {}


def link_b2():
    """Batch 2 hero building library (+ kaccha house) -> HERO_ASSETS."""
    for lib, names in ((os.path.join(ROOT, "02_ARCHITECTURE", "LIB_Buildings_B2.blend"), sorted({a for v in HERO_FAMILIES.values() for a in v} - {"AST_House_Small_Kaccha_A"})),
                       (os.path.join(ROOT, "02_ARCHITECTURE", "HOUSES_SMALL", "HERO_House_Small_Kaccha_A.blend"), ["AST_House_Small_Kaccha_A"])):
        if os.path.exists(lib):
            HERO_ASSETS.update(link_collections(lib, names))


def build_plots(M, plots, house, tabela):
    counters = {}
    nhero = ntab = 0
    for p in plots:
        prefix, coll = OBJECT_PREFIX[p["family"]]
        counters[prefix] = counters.get(prefix, 0) + 1
        name = "%s_%03d" % (prefix, counters[prefix])
        p["object"], p["collection"] = name, coll
        if p["family"] == "house_common" and house is not None:
            o = inst(house, name, (p["x"], p["y"], p["z"]), p["rot"], target=coll)
            nhero += 1
        elif p["family"] in HERO_FAMILIES and HERO_ASSETS:
            choices = [HERO_ASSETS[a] for a in HERO_FAMILIES[p["family"]] if a in HERO_ASSETS]
            if choices:
                o = inst(choices[p["num"] % len(choices)], name, (p["x"], p["y"], p["z"]), p["rot"], target=coll)
            else:
                mb = build_plot_mesh(p, M)
                o = B.place_obj(mb, name, coll, (p["x"], p["y"], p["z"]), p["rot"])
        elif p["family"] == "cattle_shed" and tabela is not None:
            o = inst(tabela, name, (p["x"], p["y"], p["z"] - 0.2), p["rot"], target=coll)
            ntab += 1
        else:
            mb = build_plot_mesh(p, M)
            o = B.place_obj(mb, name, coll, (p["x"], p["y"], p["z"]), p["rot"])
        o["plot_id"] = "P%02d" % p["num"]
        o["family"] = p["family"]
        o["status"] = "hero" if o.instance_type == "COLLECTION" else "blockout massing + production materials"
    log("Buildings: %d plots (%d hero houses, %d tabelas, rest production-material massing)" % (len(plots), nhero, ntab))


def chowk_and_temple_trees(trees, plots):
    for o in list(bpy.data.objects):
        if o.name in ("OBJ_Landmark_Banyan_Chowk", "OBJ_Landmark_Peepal_Temple"):
            bpy.data.objects.remove(o, do_unlink=True)
    z = float(terrain_height(0.0, 0.0)) + 0.18
    mb = MeshBuilder()
    stone = bpy.data.materials.get("MAT_Stone_Plinth_Blocks")
    mb.frustum(0, 0, -0.5, 0.75, 7.5, 7.5, 40, stone)
    mb.frustum(0, 0, 0.75, 0.85, 7.7, 7.7, 40, bpy.data.materials.get("MAT_Concrete_Weathered"))
    B.place_obj(mb, "OBJ_Landmark_Chabutra_Chowk", "BLD_LANDMARKS", (0, 0, z))
    hero = link_collections(LIBS["banyan"], ["VEG_Tree_Banyan_Chowk_Hero"]).get("VEG_Tree_Banyan_Chowk_Hero")
    if hero is not None:                       # B2: the village's signature banyan (30 m canopy, lanterns, shrine)
        inst(hero, "INST_Hero_Banyan_Chowk", (0, 0, z + 0.85), 0.4, 1.0, target="ENV_VEGETATION")
    elif "VEG_Tree_Banyan_A" in trees:
        inst(trees["VEG_Tree_Banyan_A"], "INST_Hero_Banyan_Chowk", (0, 0, z + 0.7), 0.4, 0.72, target="ENV_VEGETATION")
    tp = next(p for p in plots if p["family"] == "temple")
    o = tp["obb"]
    wx, wy = o.c + (-7.5) * o.u + (-6.5) * o.v
    if "VEG_Tree_Peepal_A" in trees:
        inst(trees["VEG_Tree_Peepal_A"], "INST_Hero_Peepal_Temple", (wx, wy, tp["z"] + 0.75), 1.0, 0.8, target="ENV_VEGETATION")


# ============================================================================
def clear_of(pt, paths, plots, margin=0.8, road_extra=0.4):
    for p in paths.values():
        if np.min(np.hypot(p.pts[:, 0] - pt[0], p.pts[:, 1] - pt[1])) < p.width / 2.0 + road_extra:
            return False
    for pl in plots:
        if pl["obb"].dist_points([pt])[0] < margin:
            return False
    if float(river_distance(pt[0], pt[1])) < 24.0:
        return False
    return math.hypot(*pt) > C.CHOWK_RADIUS - 1.0 or True


def place_props(props, paths, plots):
    rng = random.Random(77)
    n = {}

    def add(key, nm, pt, rz, s=1.0, z_off=0.0):
        z = float(terrain_height(pt[0], pt[1])) + z_off
        inst(props[key], "INST_%s_%03d" % (nm, n.get(nm, 0) + 1), (pt[0], pt[1], z), rz, s)
        n[nm] = n.get(nm, 0) + 1

    # street lights along the main roads, alternating sides, arm over the road
    for rid, t0, t1, step in (("R01", 525, 660, 30), ("R02", 8, 200, 30), ("R04", 8, 95, 28), ("R05", 10, 140, 34)):
        p = paths[rid]
        side = 1
        for t in np.arange(t0, min(t1, p.length), step):
            nv = p.normal(t) * side
            pt = p.point(t) + nv * (p.width / 2 + 1.0)
            if clear_of(pt, {k: v for k, v in paths.items()}, plots, 0.6, 0.6):
                d = -nv
                add("AST_StreetLight_Pole_A", "StreetLight", pt, math.atan2(d[0], -d[1]))
            side = -side
    # lantern posts ringing the chowk, along the temple road and at the ghat
    for k in range(8):
        a = 2 * math.pi * (k + 0.5) / 8
        pt = np.array([math.cos(a), math.sin(a)]) * (C.CHOWK_RADIUS - 1.5)
        if all(np.min(np.hypot(pp.pts[:, 0] - pt[0], pp.pts[:, 1] - pt[1])) > pp.width / 2 + 0.8 for pp in paths.values()):
            add("AST_LampPost_Lantern_A", "LampPost", pt, 0.0, z_off=0.18)
    p = paths["R03"]
    for t in np.arange(10, p.length, 18):
        for side in (1, -1):
            pt = p.point(t) + p.normal(t) * side * (p.width / 2 + 0.8)
            if clear_of(pt, paths, plots, 0.5, 0.5):
                add("AST_LampPost_Lantern_A", "LampPost", pt, 0.0)
    # hand pumps near lane mouths
    for rid in ("L01", "L02", "L03", "L04"):
        p = paths[rid]
        for t in (7.0, 12.0, 17.0):
            pt = p.point(t) + p.normal(t) * (p.width / 2 + 2.2)
            if clear_of(pt, paths, plots, 1.5, 1.5):
                add("AST_HandPump_A", "HandPump", pt, rng.uniform(0, 6.28))
                break
    # domestic dressing around hero houses and tabelas
    for pl in plots:
        w, d, rot = pl["w"], pl["d"], pl["rot"]
        if pl["family"] == "house_common":
            for (key, nm, lx, ly, z_off, s) in (
                    ("AST_Planter_Marigold_A", "Planter", -3.0, -3.95, 0.53, 1.0),
                    ("AST_Planter_Marigold_A", "Planter", 2.8, -3.95, 0.53, 0.9),
                    ("AST_Planter_MoneyPlant_A", "Planter", 4.4, -2.4, 0.53, 1.0),
                    ("AST_WallLantern_A", "WallLantern", -1.0, -1.95, 2.55, 1.0)):
                pt = plot_xf(pl, lx, ly)
                inst(props[key], "INST_%s_%03d" % (nm, n.get(nm, 0) + 1), (pt[0], pt[1], pl["z"] + z_off), rot, s)
                n[nm] = n.get(nm, 0) + 1
            for (key, nm, lx, ly) in (("AST_Banana_Plant_A", "Banana", -w / 2 - 1.6, 1.5),
                                      ("AST_Hibiscus_Bush_A", "Hibiscus", w / 2 + 1.3, -d / 2 - 0.8),
                                      ("AST_Bougainvillea_Wall_A", "Bougainvillea", -w / 2 - 0.6, -d / 2 - 1.2)):
                if rng.random() < 0.7:
                    pt = plot_xf(pl, lx, ly)
                    if clear_of(pt, paths, [q for q in plots if q is not pl], 0.8, 0.8) and pl["obb"].dist_points([pt])[0] > 0.3:
                        add(key, nm, pt, rot + rng.uniform(-0.3, 0.3), rng.uniform(0.85, 1.1))
        elif pl["family"] == "cattle_shed":
            pt = plot_xf(pl, pl["w"] / 2 + 3.2, 0.5)
            if clear_of(pt, paths, [q for q in plots if q is not pl], 1.0, 1.5):
                add("AST_Haystack_A", "Haystack", pt, rng.uniform(0, 6.28), 0.9)
        elif pl["family"] in ("house_small", "house_middle") and rng.random() < 0.6:
            pt = plot_xf(pl, rng.choice((-1, 1)) * (pl["w"] / 2 + 1.4), rng.uniform(-1, 1.5))
            if clear_of(pt, paths, [q for q in plots if q is not pl], 0.8, 0.8):
                add(rng.choice(["AST_Banana_Plant_A", "AST_Hibiscus_Bush_A"]), "YardPlant", pt, rng.uniform(0, 6.28))
            pt = plot_xf(pl, rng.uniform(-1.0, 1.0), -pl["d"] / 2 - 1.0)
            if clear_of(pt, paths, [q for q in plots if q is not pl], 0.3, 0.6):
                add("AST_WaterDrum_Bucket_A", "Drum", pt, rng.uniform(0, 6.28))
    # haystacks at the farm edges
    k = 0
    while k < 14:
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(150, 260)
        pt = np.array([math.cos(a) * r, math.sin(a) * r * 0.9])
        if float(terrain_height(pt[0], pt[1])) > 6 or not clear_of(pt, paths, plots, 4, 3):
            continue
        add("AST_Haystack_A", "Haystack", pt, rng.uniform(0, 6.28), rng.uniform(0.8, 1.2))
        k += 1
    log("Props: " + ", ".join("%s %d" % kv for kv in sorted(n.items())))


def massif_heightfield(m):
    """Raycast the linked massif mesh into a 10 m height grid (library-local) for geo.MASSIF terrain shaping."""
    from mathutils.bvhtree import BVHTree
    ob = next(o for o in m["AST_Mountain_Massif_A"].all_objects if o.name.startswith("GEO_Mountain_Massif"))
    me = ob.data
    verts = [ob.matrix_world @ v.co for v in me.vertices]
    bvh = BVHTree.FromPolygons(verts, [tuple(p.vertices) for p in me.polygons])
    xs = np.arange(-460.0, 460.1, 10.0)
    ys = np.arange(-120.0, 520.1, 10.0)
    Hh = np.full((len(ys), len(xs)), np.nan)
    for j, y in enumerate(ys):
        for i, x in enumerate(xs):
            rx, ry = min(max(x, -459.0), 459.0), min(max(y, -119.0), 519.0)    # edge samples just inside the mesh
            hit = bvh.ray_cast(Vector((rx, ry, 2000.0)), Vector((0, 0, -1)))
            if hit[0] is not None:
                Hh[j, i] = hit[0].z
    for _ in range(4):                       # fill any remaining misses from valid neighbours (edges must not read 0)
        nan = np.isnan(Hh)
        if not nan.any():
            break
        P = np.pad(Hh, 1, constant_values=np.nan)
        nb = np.stack([P[:-2, 1:-1], P[2:, 1:-1], P[1:-1, :-2], P[1:-1, 2:]])
        with np.errstate(all="ignore"):
            fill = np.nanmax(nb, axis=0)
        Hh[nan] = fill[nan]
    return xs, ys, np.nan_to_num(Hh)


def link_mountains():
    m = link_collections(LIBS["mtn"], ["AST_Mountain_Massif_A", "AST_Waterfall_A"])
    if "AST_Mountain_Massif_A" in m:
        xs, ys, Hh = massif_heightfield(m)
        ox, oy = C.MOUNTAIN_ORIGIN
        geo.MASSIF = dict(ox=ox, oy=oy, z0=C.MOUNTAIN_Z0, xs=xs, ys=ys, H=Hh)
        log("Massif heightfield %dx%d, peak %.0f m (library-local)" % (len(xs), len(ys), np.nanmax(Hh)))
    return m


def place_mountains(m, trees):
    """Waterfall: instanced as is.  Massif: its rock meshes go into a local collection (still linked data) and
    its ~2,200 tree empties are re-created locally on the baked tree meshes, same transforms."""
    if not m:
        return
    ox, oy = C.MOUNTAIN_ORIGIN
    if "AST_Waterfall_A" in m:
        inst(m["AST_Waterfall_A"], "INST_AST_Waterfall_A", (ox, oy, C.MOUNTAIN_Z0), 0.0, target="ENV_BACKDROP")
    src = m.get("AST_Mountain_Massif_A")
    if src is None:
        return
    rock = bpy.data.collections.new("AST_Mountain_Massif_A_Rock")
    B.COLL["PROTO_LIBRARY"].children.link(rock)
    off = Matrix.Translation((ox, oy, C.MOUNTAIN_Z0))
    nt = 0
    for o in src.all_objects:
        if o.type == "MESH":
            rock.objects.link(o)
        elif o.instance_type == "COLLECTION" and o.instance_collection is not None:
            key = o.instance_collection.name
            coll = trees.get(key, o.instance_collection)
            e = bpy.data.objects.new("INST_MtnTree_%04d" % nt, None)
            e.instance_type = "COLLECTION"
            e.instance_collection = coll
            e.matrix_world = off @ o.matrix_world
            B.COLL["ENV_BACKDROP"].objects.link(e)
            nt += 1
    inst(rock, "INST_AST_Mountain_Massif_A", (ox, oy, C.MOUNTAIN_Z0), 0.0, target="ENV_BACKDROP")
    log("Mountains + waterfall placed at (%.0f, %.0f, %.1f); %d massif trees on baked meshes" % (ox, oy, C.MOUNTAIN_Z0, nt))


EXTRA_CAMS = {
    "CAM_Village_Hero":      ((330.0, -250.0, 92.0), (10.0, 60.0, 12.0), 30, False),
    "CAM_Aerial_Massif":     ((560.0, -560.0, 260.0), (90.0, 330.0, 30.0), 28, False),
    "CAM_North_Valley":      ((92.0, 345.0, 2.2), (150.0, 900.0, 75.0), 24, True),
    "CAM_Bridge_Ground":     ((176.0, -78.0, 2.2), (140.0, -28.0, 3.0), 26, True),
    "CAM_Chowk_Close":       ((-16.0, -24.0, 1.7), (6.0, 6.0, 4.5), 24, True),
    "CAM_House_Lane":        ((-6.0, 64.0, 1.7), (-80.0, 74.0, 2.5), 28, True),
    "CAM_Approach_Avenue":   ((-27.0, -470.0, 1.8), (-20.0, -300.0, 4.0), 30, True),
}


def ground_sightlines():
    out = []
    for name, (pos, tgt, lens, ground) in EXTRA_CAMS.items():
        if ground:
            out.append((np.array(pos[:2], float), np.array(tgt[:2], float)))
    for c in C.CAMERAS.values():
        if c.get("ground"):
            out.append((np.array(c["pos"][:2], float), np.array(c["target"][:2], float)))
    return out


def blocks_view(P, lines, near=16.0, corridor=5.0, reach=80.0):
    """Vectorised: True where a point would block a ground review camera (close to it or in its view line)."""
    P = np.asarray(P, float).reshape(-1, 2)
    bad = np.zeros(len(P), bool)
    for a, b in lines:
        ab = b - a
        u = ab / np.linalg.norm(ab)
        d = P - a
        s_ = d @ u
        lat = np.abs(d[:, 0] * u[1] - d[:, 1] * u[0])
        bad |= np.hypot(d[:, 0], d[:, 1]) < near
        bad |= (s_ > 0) & (s_ < min(np.linalg.norm(ab), reach)) & (lat < corridor)
    return bad


def extra_cameras():
    cams = EXTRA_CAMS
    for name, (pos, tgt, lens, ground) in cams.items():
        x, y, z = pos
        tx, ty, tz = tgt
        if ground:
            z += float(terrain_height(x, y))
            tz += float(terrain_height(tx, ty))
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 9000
        o = bpy.data.objects.new(name, cd)
        o.location = (x, y, z)
        o.rotation_euler = (Vector((tx, ty, tz)) - Vector((x, y, z))).to_track_quat("-Z", "Y").to_euler()
        B.COLL["LIGHTING_CAMERAS"].objects.link(o)
    for o in B.COLL["LIGHTING_CAMERAS"].objects:
        if o.type == "CAMERA":
            o.data.clip_end = 9000


# ============================================================================
# Fields v2: bunds, orchards and tubewell yards
# ============================================================================
def build_fields_v2(M, paths, plots):
    rng = random.Random(11)
    names = [c[0] for c in C.CROPS]
    weights = [c[1] for c in C.CROPS]
    mats = [M["crop_" + n] for n in names]
    road_pts = [(p.pts, p.width / 2.0) for p in paths.values()]
    g = C.FIELD_GAP / 2
    cells = []
    for zi, z in enumerate(C.FIELD_ZONES):
        cw, ch = z["cell"]
        i, x = 0, z["x"][0]
        while x + cw <= z["x"][1]:
            j, y = 0, z["y"][0]
            while y + ch <= z["y"][1]:
                cells.append(dict(key=(zi, i, j), x0=x + g, x1=x + cw - g, y0=y + g, y1=y + ch - g))
                y += ch
                j += 1
            x += cw
            i += 1
    kept = []
    for c in cells:
        x0, x1, y0, y1 = c["x0"], c["x1"], c["y0"], c["y1"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        box = OBB(cx, cy, (x1 - x0) / 2, (y1 - y0) / 2, 0.0)
        if any(box.dist_points(pts).min() < hw + 3.0 for pts, hw in road_pts):
            continue
        if any(box.overlaps(pl["obb"], 10.0) for pl in plots):
            continue
        if box.dist_points(river_path().pts).min() < 26.0 or math.hypot(cx, cy) < 135:
            continue
        if any(o["x"][0] - 4 < cx < o["x"][1] + 4 and o["y"][0] - 4 < cy < o["y"][1] + 4 for o in C.ORCHARDS):
            continue
        GX, GY = np.meshgrid(np.linspace(x0, x1, 7), np.linspace(y0, y1, 7))
        GZ = terrain_height(GX, GY)
        if GZ.max() - GZ.min() > 4.0 or GZ.max() > 20:
            continue
        c.update(cx=cx, cy=cy, GX=GX, GY=GY, GZ=GZ, crop=names[rng.choices(range(len(names)), weights)[0]])
        kept.append(c)
    yards = []                                     # tubewell yards replace the nearest field cell to each target
    for tx, ty in C.TUBEWELL_TARGETS:
        yards.append(min((c for c in kept if c not in yards), key=lambda c: math.hypot(c["cx"] - tx, c["cy"] - ty)))
    fields = [c for c in kept if c not in yards]
    verts, faces, midx = [], [], []
    for c in fields:
        o = len(verts)
        verts.extend(np.stack([c["GX"].ravel(), c["GY"].ravel(), c["GZ"].ravel() + 0.06], 1).tolist())
        fs = B.grid_faces(7, 7, o)
        faces.extend(fs)
        midx.extend([names.index(c["crop"])] * len(fs))
    B.mesh_object("OBJ_Fields_Crops", verts, faces, None, "ENV_FIELDS", mat_idx=midx, mats=mats)
    # bunds (mend): one ridge per shared grid line, drawn once; open edges of a block always closed
    keys = {c["key"] for c in kept}
    segs = []
    for c in kept:
        zi, i, j = c["key"]
        X0, X1, Y0, Y1 = c["x0"] - g, c["x1"] + g, c["y0"] - g, c["y1"] + g
        segs.append(((X0, Y0), (X0, Y1)))
        segs.append(((X0, Y0), (X1, Y0)))
        if (zi, i + 1, j) not in keys:
            segs.append(((X1, Y0), (X1, Y1)))
        if (zi, i, j + 1) not in keys:
            segs.append(((X0, Y1), (X1, Y1)))
    V, F, bund_pts = [], [], []
    for (a, b) in segs:
        a, b = np.array(a, float), np.array(b, float)
        L = float(np.linalg.norm(b - a))
        n = max(2, int(L / 3.0) + 1)
        u = (b - a) / L
        nv = np.array([-u[1], u[0]])
        o = len(V)
        for k in range(n):
            p = a + (b - a) * k / (n - 1)
            w = 0.55 + 0.08 * math.sin(p[0] * 0.7 + p[1] * 1.3)
            for off, dz in ((-w, -0.04), (-w * 0.35, 0.2), (w * 0.35, 0.22), (w, -0.04)):
                q = p + nv * off
                V.append([q[0], q[1], dz])
            bund_pts.append(p)
        for k in range(n - 1):
            for e in range(3):
                i0 = o + k * 4 + e
                F.append((i0, i0 + 1, i0 + 5, i0 + 4))
    Va = np.array(V)
    Va[:, 2] += terrain_height(Va[:, 0], Va[:, 1])
    B.mesh_object("OBJ_Field_Bunds", Va.tolist(), F, H.mat_ground("MAT_Ground_Bund_Grass"), "ENV_FIELDS", smooth=True)
    km = sum(float(np.linalg.norm(np.subtract(b, a))) for a, b in segs) / 1000.0
    log("Fields v2: %d crop fields, %d tubewell yards, %d bund segments (%.1f km)" % (len(fields), len(yards), len(segs), km))
    return fields, yards, np.array(bund_pts)


# ============================================================================
# Vegetation + ground cover
# ============================================================================
class Placer:
    """Spacing grid shared by every added tree so nothing intersects the base scatter."""

    def __init__(self, spacing):
        self.s = spacing
        self.grid = {}

    def add(self, x, y, r):
        self.grid.setdefault((int(x // self.s), int(y // self.s)), []).append((x, y, r))

    def free(self, x, y, r):
        gx, gy = int(x // self.s), int(y // self.s)
        for i in range(gx - 2, gx + 3):
            for j in range(gy - 2, gy + 3):
                for (px, py, pr) in self.grid.get((i, j), []):
                    if (px - x) ** 2 + (py - y) ** 2 < (0.5 * (r + pr)) ** 2:
                        return False
        return True


def clear_mask(P, paths, plots, road_extra=2.5, plot_margin=2.5, river_min=24.0, fields=None, field_grow=0.0):
    """Vectorised clearance test against roads, plots, river, chowk and (optionally) crop fields."""
    P = np.asarray(P, float).reshape(-1, 2)
    ok = np.ones(len(P), bool)
    for p in paths.values():
        ok &= geo.dist_to_polyline(P, p.pts) > p.width / 2.0 + road_extra
    for pl in plots:
        ok &= pl["obb"].dist_points(P) > plot_margin
    ok &= river_distance(P[:, 0], P[:, 1]) > river_min
    ok &= np.hypot(P[:, 0], P[:, 1]) > C.CHOWK_RADIUS + 2.0
    if fields:
        for c in fields:
            ok &= ~((P[:, 0] > c["x0"] - field_grow) & (P[:, 0] < c["x1"] + field_grow) &
                    (P[:, 1] > c["y0"] - field_grow) & (P[:, 1] < c["y1"] + field_grow))
    return ok


def massif_rock_mask(P):
    """True where the massif's rock stands above the valley floor (nothing is planted there)."""
    P = np.asarray(P, float).reshape(-1, 2)
    if geo.MASSIF is None:
        return np.zeros(len(P), bool)
    Mf = geo.MASSIF
    lx, ly = P[:, 0] - Mf["ox"], P[:, 1] - Mf["oy"]
    inside = (np.abs(lx) < geo.MASSIF_X_HALF) & (ly > geo.MASSIF_Y[0]) & (ly < geo.MASSIF_Y[1])
    Hc = geo._massif_lookup(np.clip(lx, -459, 459), np.clip(ly, -119, 519))
    return inside & (Hc > 4.0)


def dress_trees(trees, paths, plots, fields, yards, bund_pts):
    rng = random.Random(404)
    lines = ground_sightlines()
    pl = Placer(6.0)
    for o in B.COLL["ENV_VEGETATION"].objects:
        pl.add(o.location.x, o.location.y, 7.0)
    T = {"Mango": trees["VEG_Tree_Mango_A_LOD1"], "Neem": trees["VEG_Tree_Neem_A_LOD1"],
         "Palm": trees["VEG_Tree_Palm_A_LOD1"], "Amaltas": trees["VEG_Tree_Amaltas_A_LOD1"],
         "Peepal": trees.get("VEG_Tree_Peepal_A_LOD1", trees["VEG_Tree_Neem_A_LOD1"])}
    n = {}

    def try_put(kind, x, y, r=7.0, s=(0.8, 1.2), fields_ok=False):
        P = np.array([[x, y]])
        if blocks_view(P, lines)[0] or massif_rock_mask(P)[0]:
            return False
        if not clear_mask(P, paths, plots, 3.2, 3.5, 23.0, None if fields_ok else fields, 0.6)[0]:
            return False
        if float(terrain_height(x, y)) > 40 or not pl.free(x, y, r):
            return False
        n[kind] = n.get(kind, 0) + 1
        e = inst(T[kind], "INST_Tree2_%s_%04d" % (kind, n[kind]), (x, y, float(terrain_height(x, y))),
                 rng.uniform(0, 2 * math.pi), 1.0, target="ENV_VEGETATION")
        sc = rng.uniform(*s)
        e.scale = (sc, sc, sc * rng.uniform(0.92, 1.08))
        pl.add(x, y, r)
        return True

    # 1) avenue trees along the arterial roads outside the village core
    for rid, t0, t1, step, mix in (("R01", 0, 515, 15, ("Neem", "Mango", "Neem", "Peepal")),
                                   ("R04", 175, 9999, 16, ("Neem", "Mango", "Palm")),
                                   ("R02", 215, 9999, 17, ("Mango", "Neem", "Neem")),
                                   ("R05", 160, 9999, 15, ("Neem", "Palm", "Mango"))):
        p = paths[rid]
        for t in np.arange(t0, min(t1, p.length), step):
            for side in (1, -1):
                if rng.random() < 0.18:
                    continue
                tt = t + rng.uniform(-2.5, 2.5)
                q = p.point(tt) + p.normal(tt) * side * (p.width / 2 + rng.uniform(4.2, 5.5))
                try_put(rng.choice(mix), q[0], q[1], 6.5, (0.85, 1.25), fields_ok=True)
    na = sum(n.values())
    # 2) orchards: jittered grid
    for o in C.ORCHARDS:
        sp = o["spacing"]
        for x in np.arange(o["x"][0], o["x"][1], sp):
            for y in np.arange(o["y"][0], o["y"][1], sp):
                if rng.random() < 0.06:
                    continue
                try_put(o["kind"], x + rng.uniform(-0.8, 0.8), y + rng.uniform(-0.8, 0.8), sp * 0.8, (0.7, 0.95), True)
    nb = sum(n.values()) - na
    # 3) bund trees: lone palms / neem / peepal on field edges
    k = 0
    for i in rng.sample(range(len(bund_pts)), min(len(bund_pts), 1200)):
        if k >= 170:
            break
        x, y = bund_pts[i]
        if try_put(rng.choices(["Palm", "Neem", "Peepal", "Mango"], [0.4, 0.3, 0.1, 0.2])[0], x, y, 9.0, (0.8, 1.2), True):
            k += 1
    # 4) north valley + mountain foot: clumps, palms near the river
    for _ in range(95):
        cx, cy = rng.uniform(-560, 760), rng.uniform(340, 860)
        for _ in range(rng.randint(3, 11)):
            a, r = rng.uniform(0, 6.28), rng.uniform(0, 28)
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            near_river = float(river_distance(x, y)) < 70
            kind = "Palm" if near_river and rng.random() < 0.5 else rng.choice(["Neem", "Mango", "Neem", "Peepal"])
            try_put(kind, x, y, 6.5, (0.75, 1.25), True)
    # 5) tubewell yards: a shade tree each
    for c in yards:
        try_put("Neem", c["x1"] - 3.0, c["y1"] - 3.0, 4.0, (0.9, 1.1), True)
    rm = 0                                         # base-scatter trees that block the new review cameras
    for o in list(B.COLL["ENV_VEGETATION"].objects):
        if o.name.startswith("INST_Tree_") and blocks_view([(o.location.x, o.location.y)], lines)[0]:
            bpy.data.objects.remove(o, do_unlink=True)
            rm += 1
    log("Vegetation v2: +%d trees (%d avenue, %d orchard, rest bund/valley/yard); %d base trees cleared from views; %s" % (
        sum(n.values()), na, nb, rm, ", ".join("%s %d" % kv for kv in sorted(n.items()))))


def coll_instancer(name, coll):
    """GN group: instance a (linked) collection on points with 'rot' (euler) and 'scl' attributes."""
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    iop = N.new("GeometryNodeInstanceOnPoints")
    ci = N.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = coll
    ci.transform_space = "ORIGINAL"
    nr = N.new("GeometryNodeInputNamedAttribute")
    nr.data_type = "FLOAT_VECTOR"
    nr.inputs["Name"].default_value = "rot"
    ns = N.new("GeometryNodeInputNamedAttribute")
    ns.data_type = "FLOAT"
    ns.inputs["Name"].default_value = "scl"
    L.new(gi.outputs[0], iop.inputs["Points"])
    L.new(ci.outputs[0], iop.inputs["Instance"])
    ro = nr.outputs["Attribute"]
    try:
        e2r = N.new("FunctionNodeEulerToRotation")
        L.new(ro, e2r.inputs[0])
        ro = e2r.outputs[0]
    except Exception:
        pass
    L.new(ro, iop.inputs["Rotation"])
    L.new(ns.outputs["Attribute"], iop.inputs["Scale"])
    L.new(iop.outputs["Instances"], go.inputs[0])
    return ng


def realize_collection(coll, name):
    """Local baked copy of a linked asset collection: all (nested) instances realized into one mesh."""
    tmp_me = bpy.data.meshes.new("TMP_" + name)
    tmp = bpy.data.objects.new("TMP_" + name, tmp_me)
    bpy.context.scene.collection.objects.link(tmp)
    ng = bpy.data.node_groups.new("TMP_GN_" + name, "GeometryNodeTree")
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
    bpy.data.meshes.remove(tmp_me)
    bpy.data.node_groups.remove(ng)
    c = bpy.data.collections.new(name)
    B.COLL["PROTO_LIBRARY"].children.link(c)
    c.objects.link(bpy.data.objects.new(name, me))
    log("Baked %s: %d polys, %d materials" % (name, len(me.polygons), len(me.materials)))
    return c


def scatter_cover(name, coll, P, rng, smin, smax, tilt=0.08):
    P = np.asarray(P, float).reshape(-1, 2)
    if len(P) == 0:
        return
    pts = np.c_[P, terrain_height(P[:, 0], P[:, 1]) - 0.03]
    R = [(rng.uniform(-tilt, tilt), rng.uniform(-tilt, tilt), rng.uniform(0, 6.28)) for _ in range(len(P))]
    S = [rng.uniform(smin, smax) for _ in range(len(P))]
    H.points_object(name, pts, R, S, B.COLL["ENV_VEGETATION"], coll_instancer("GN_" + name, coll))


def road_distance(P, paths):
    return np.min([geo.dist_to_polyline(P, p.pts) - p.width / 2 for p in paths.values()], axis=0)


def dress_ground_cover(farm, paths, plots, fields, bund_pts):
    rng = random.Random(505)
    nrng = np.random.default_rng(505)
    lines = ground_sightlines()
    out = {}

    def cand(n, x0, x1, y0, y1):
        return np.c_[nrng.uniform(x0, x1, n), nrng.uniform(y0, y1, n)]

    # shrubs: road verges, compound edges, the valley and the mountain foot
    P = cand(26000, -600, 760, -620, 880)
    ok = clear_mask(P, paths, plots, 1.6, 1.4, 24.0, fields, 0.4) & ~massif_rock_mask(P)
    ok &= ~blocks_view(P, lines, 7.0, 1.5, 40.0)
    P = P[ok]
    droad = road_distance(P, paths)
    dplot = np.min([pl["obb"].dist_points(P) for pl in plots], axis=0)
    w = 0.03 + 0.5 * np.exp(-np.maximum(droad - 2, 0) / 6) + 0.45 * np.exp(-np.maximum(dplot - 2, 0) / 5)
    w += 0.25 * (P[:, 1] > 700)
    P = P[nrng.random(len(P)) < w]
    kinds = nrng.choice(3, len(P), p=[0.4, 0.35, 0.25])
    north = P[:, 1] > 650
    kinds[north] = nrng.choice([1, 2], int(north.sum()), p=[0.4, 0.6])
    for k, nm in enumerate(("AST_Shrub_Lantana_A", "AST_Shrub_Dense_A", "AST_Shrub_Dry_A")):
        sel = P[kinds == k]
        scatter_cover("ENV_Shrubs_%s" % nm[10:-2], farm[nm], sel, rng, 0.7, 1.35)
        out[nm[10:-2]] = len(sel)
    # grass tufts: everywhere open, thicker along roads, bunds and the village fringe
    P = cand(240000, -620, 780, -640, 900)
    P = P[clear_mask(P, paths, plots, 0.35, 0.6, 21.5, fields, -0.2) & ~massif_rock_mask(P)]
    r = np.hypot(P[:, 0] / 1.2, P[:, 1])
    w = 0.12 + 0.55 * np.exp(-np.maximum(road_distance(P, paths), 0) / 5) + 0.35 * (r < 260)
    P = P[nrng.random(len(P)) < w]
    if len(bund_pts):
        B2 = bund_pts[nrng.random(len(bund_pts)) < 0.85]
        P = np.r_[P, B2 + nrng.normal(0, 0.35, B2.shape)]
    dry = nrng.random(len(P)) < 0.35
    scatter_cover("ENV_GrassTufts_Green", farm["AST_GrassTuft_A"], P[~dry], rng, 0.7, 1.6, tilt=0.15)
    scatter_cover("ENV_GrassTufts_Dry", farm["AST_GrassTuft_Dry_A"], P[dry], rng, 0.7, 1.5, tilt=0.15)
    out["GrassTufts"] = len(P)
    # kans grass along the river banks
    rp = river_path()
    Q = []
    for t in np.arange(0, rp.length, 3.0):
        for side in (1, -1):
            if rng.random() < 0.55:
                continue
            Q.append(rp.point(t) + rp.normal(t) * side * rng.uniform(17.5, 34.0))
    Q = np.array(Q)
    okq = (terrain_height(Q[:, 0], Q[:, 1]) > C.WATER_Z + 0.25) & clear_mask(Q, paths, plots, 1.0, 2.0, 0.0)
    okq &= ~massif_rock_mask(Q) & ~blocks_view(Q, lines, 6.0, 1.2, 25.0)
    Q = Q[okq]
    scatter_cover("ENV_Kans_Riverbank", farm["AST_GrassClump_Tall_A"], Q, rng, 0.75, 1.25, tilt=0.12)
    out["Kans"] = len(Q)
    log("Ground cover: " + ", ".join("%s %d" % kv for kv in sorted(out.items())))


def dress_farms(farm, props, paths, plots, fields, yards):
    rng = random.Random(606)
    lines = ground_sightlines()
    n = {}

    def add(coll, nm, x, y, rz, s=1.0, z_off=0.0):
        n[nm] = n.get(nm, 0) + 1
        return inst(coll, "INST_%s_%03d" % (nm, n[nm]), (x, y, float(terrain_height(x, y)) + z_off), rz, s)

    for c in yards:                                # pump house in the yard, haystacks along its back edge
        add(farm["AST_Tubewell_A"], "Tubewell", c["cx"], c["cy"], rng.choice([0.0, math.pi / 2, math.pi, -math.pi / 2]))
        for k in range(2):
            add(props["AST_Haystack_A"], "Haystack", c["x0"] + 3.5 + k * 3.6, c["y1"] - 3.5, rng.uniform(0, 6.28),
                rng.uniform(0.75, 0.95))
    crop_fields = [c for c in fields if c["crop"] != "fallow"]
    hero = min(crop_fields, key=lambda c: math.hypot(c["cx"] - C.FARM_HERO[0], c["cy"] - C.FARM_HERO[1]))
    for c in [hero] + rng.sample([c for c in crop_fields if c is not hero], 7):
        x = c["cx"] + rng.uniform(-0.2, 0.2) * (c["x1"] - c["x0"])
        y = c["cy"] + rng.uniform(-0.2, 0.2) * (c["y1"] - c["y0"])
        if c is hero:
            x, y = c["cx"], c["cy"]
        add(farm["AST_Machaan_A"], "Machaan", x, y, rng.uniform(0, 6.28), 1.0, 0.06)
    for c in rng.sample(crop_fields, 14):
        add(farm["AST_Scarecrow_A"], "Scarecrow", rng.uniform(c["x0"] + 3, c["x1"] - 3), rng.uniform(c["y0"] + 3, c["y1"] - 3),
            rng.uniform(-0.6, 0.6), rng.uniform(0.95, 1.05), 0.06)
    hx, hy = hero["cx"], hero["cy"]
    add(farm["AST_Scarecrow_A"], "Scarecrow", hx - 9.0, hy - 6.0, -0.5, 1.0, 0.06)
    EXTRA_CAMS["CAM_Farm_Machaan"] = ((hx - 22.0, hy - 27.0, 1.7), (hx - 1.0, hy + 2.0, 3.0), 30, True)
    corners = [c for c in fields if math.hypot(c["cx"], c["cy"]) < 330]
    for c in rng.sample(corners, min(10, len(corners))):           # haystack clusters at field corners
        for k in range(rng.randint(1, 3)):
            px, py = c["x0"] - 0.2 + rng.uniform(-2.5, 2.5) - k * 3.2, c["y0"] - 0.2 + rng.uniform(-2.5, 2.5)
            P = np.array([[px, py]])
            if clear_mask(P, paths, plots, 2.0, 2.5, 26.0)[0] and not blocks_view(P, lines)[0]:
                add(props["AST_Haystack_A"], "Haystack", px, py, rng.uniform(0, 6.28), rng.uniform(0.7, 1.1))
    log("Farm detail: hero field (%.0f, %.0f) %s; %s" % (hx, hy, hero["crop"], ", ".join("%s %d" % kv for kv in sorted(n.items()))))


# ============================================================================
def main():
    geo.EXTRA_CUTS[:] = [ghat_cut_fn()]
    B.setup_scene()
    mtn = link_mountains()                       # before any terrain sampling: sets geo.MASSIF
    M = B.make_materials()
    M = MM.upgrade_palette(M)
    solver = LayoutSolver()
    plots = solver.solve()
    paths = solver.paths
    log("Plot mix: %s" % solver.summary())

    B.build_terrain(M)
    B.build_backdrop(M)
    build_water(M)
    skip = place_river_kit(M, paths)
    build_roads(M, paths, skip)
    B.build_gate(M, paths)
    B.build_chowk_features(M)

    house = link_collections(LIBS["house"], ["AST_House_Common_A"]).get("AST_House_Common_A")
    props = link_collections(LIBS["props"], [
        "AST_StreetLight_Pole_A", "AST_LampPost_Lantern_A", "AST_WallLantern_A", "AST_Planter_Tulsi_A",
        "AST_Planter_Marigold_A", "AST_Planter_MoneyPlant_A", "AST_Bougainvillea_Wall_A", "AST_Banana_Plant_A",
        "AST_Hibiscus_Bush_A", "AST_HandPump_A", "AST_Haystack_A", "AST_WaterDrum_Bucket_A", "AST_Tabela_A"])
    trees = link_collections(LIBS["trees"], [
        "VEG_Tree_Mango_A_LOD1", "VEG_Tree_Neem_A_LOD1", "VEG_Tree_Palm_A_LOD1", "VEG_Tree_Amaltas_A_LOD1",
        "VEG_Tree_Peepal_A_LOD1", "VEG_Tree_Banyan_A", "VEG_Tree_Peepal_A"])
    farm = link_collections(LIBS["farm"], [
        "AST_Machaan_A", "AST_Tubewell_A", "AST_Scarecrow_A", "AST_Shrub_Lantana_A", "AST_Shrub_Dense_A",
        "AST_Shrub_Dry_A", "AST_GrassTuft_A", "AST_GrassTuft_Dry_A", "AST_GrassClump_Tall_A"])
    # Bake leaf instances into one shared mesh per tree/shrub type: ~12M nested leaf instances otherwise
    # exceed 8 GB RAM / 4 GB VRAM.  The libraries stay untouched; only the master uses the baked copies.
    for k in ("VEG_Tree_Mango_A_LOD1", "VEG_Tree_Neem_A_LOD1", "VEG_Tree_Palm_A_LOD1", "VEG_Tree_Amaltas_A_LOD1",
              "VEG_Tree_Peepal_A_LOD1"):
        if k in trees and C.BAKE_FOLIAGE:
            trees[k] = realize_collection(trees[k], k + "_BAKED")
    for k in ("AST_Shrub_Lantana_A", "AST_Shrub_Dense_A", "AST_Shrub_Dry_A"):
        if k in farm and C.BAKE_FOLIAGE:
            farm[k] = realize_collection(farm[k], k + "_BAKED")
    link_b2()
    build_plots(M, plots, house, props.get("AST_Tabela_A"))
    fields, yards, bund_pts = build_fields_v2(M, paths, plots)
    stats = {"fields": len(fields)}
    dress_farms(farm, props, paths, plots, fields, yards)          # also registers CAM_Farm_Machaan
    B.tree_protos = lambda _M: {"Mango": trees["VEG_Tree_Mango_A_LOD1"], "Neem": trees["VEG_Tree_Neem_A_LOD1"],
                                "Palm": trees["VEG_Tree_Palm_A_LOD1"], "Amaltas": trees["VEG_Tree_Amaltas_A_LOD1"]}
    stats["trees"] = B.scatter_trees(M, paths, plots)
    chowk_and_temple_trees(trees, plots)
    place_props(props, paths, plots)
    dress_trees(trees, paths, plots, fields, yards, bund_pts)
    dress_ground_cover(farm, paths, plots, fields, bund_pts)
    place_mountains(mtn, trees)
    B.build_world()
    import lighting_atmosphere as LA                  # Batch 1: cinematic sky, sun, haze, grade (replaces the flat world)
    import place_b3                                   # Batch 3: storytelling props
    place_b3.place(bpy.context.scene, paths, plots)
    import patch_b456                                 # Batches 4 + 6: new species, sugarcane, hedges, footpaths, pebbles, far ridges
    rng456 = random.Random(456)
    G456 = patch_b456.Ground()
    patch_b456.vegetation(bpy.context.scene, G456, paths, plots, rng456)
    patch_b456.ground_detail(bpy.context.scene, G456, paths, plots, rng456)
    LA.apply(bpy.context.scene, os.environ.get("AMALTASPUR_LIGHT", "morning"))
    B.build_cameras()
    extra_cameras()
    B.build_labels(M, plots)

    if os.path.exists(B.BLEND_PATH):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(ROOT, "99_ARCHIVE", "MASTER_WORLD_%s.blend" % stamp)
        shutil.copy2(B.BLEND_PATH, dst)
        log("Checkpoint: previous master archived to %s" % os.path.basename(dst))
    reg = os.path.join(B.MASTER_DIR, "ASSET_REGISTRY.csv")
    keep = []
    if os.path.exists(reg):                      # preserve hero/library rows across the rebuild
        with open(reg, encoding="utf-8-sig") as f:
            keep = [ln for ln in f.read().splitlines()
                    if ln.split(",")[0].startswith(("HERO-", "VEG-", "ENV-01", "ENV-02", "PRP-01", "PRP-02", "BLD-T"))]
    B.write_records(plots, paths, stats)
    with open(reg, "a", encoding="utf-8") as f:
        for ln in keep:
            f.write(ln + "\n")
    bpy.ops.wm.save_as_mainfile(filepath=B.BLEND_PATH, compress=True)
    log("Saved %s (v2 integrated)" % B.BLEND_PATH)


main()
