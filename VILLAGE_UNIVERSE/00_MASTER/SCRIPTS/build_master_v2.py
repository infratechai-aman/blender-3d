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
    if "VEG_Tree_Banyan_A" in trees:
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


def place_mountains():
    m = link_collections(LIBS["mtn"], ["AST_Mountain_Massif_A", "AST_Waterfall_A"])
    if not m:
        return
    ox, oy = 150.0, 1180.0
    xs = np.linspace(ox - 300, ox + 300, 25)
    zs = terrain_height(xs, np.full_like(xs, 1060.0))
    z0 = float(np.percentile(zs, 40)) - 12.0
    for name, c in m.items():
        inst(c, "INST_" + name, (ox, oy, z0), 0.0, target="ENV_BACKDROP")
    log("Mountains + waterfall placed at (%.0f, %.0f, %.1f)" % (ox, oy, z0))


def extra_cameras():
    cams = {
        "CAM_Village_Hero":      ((330.0, -250.0, 92.0), (10.0, 60.0, 12.0), 30, False),
        "CAM_Bridge_Ground":     ((176.0, -78.0, 2.2), (140.0, -28.0, 3.0), 26, True),
        "CAM_Chowk_Close":       ((-16.0, -24.0, 1.7), (6.0, 6.0, 4.5), 24, True),
        "CAM_House_Lane":        ((-6.0, 64.0, 1.7), (-80.0, 74.0, 2.5), 28, True),
    }
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
def main():
    geo.EXTRA_CUTS[:] = [ghat_cut_fn()]
    B.setup_scene()
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
        "VEG_Tree_Banyan_A", "VEG_Tree_Peepal_A"])
    build_plots(M, plots, house, props.get("AST_Tabela_A"))
    stats = {"fields": B.build_fields(M, paths, plots)}
    B.tree_protos = lambda _M: {"Mango": trees["VEG_Tree_Mango_A_LOD1"], "Neem": trees["VEG_Tree_Neem_A_LOD1"],
                                "Palm": trees["VEG_Tree_Palm_A_LOD1"], "Amaltas": trees["VEG_Tree_Amaltas_A_LOD1"]}
    stats["trees"] = B.scatter_trees(M, paths, plots)
    chowk_and_temple_trees(trees, plots)
    place_props(props, paths, plots)
    place_mountains()
    B.build_world()
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
                    if ln.split(",")[0].startswith(("HERO-", "VEG-", "ENV-01", "ENV-02", "PRP-01", "BLD-T"))]
    B.write_records(plots, paths, stats)
    with open(reg, "a", encoding="utf-8") as f:
        for ln in keep:
            f.write(ln + "\n")
    bpy.ops.wm.save_as_mainfile(filepath=B.BLEND_PATH, compress=True)
    log("Saved %s (v2 integrated)" % B.BLEND_PATH)


main()
