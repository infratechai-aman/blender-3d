"""
AMALTASPUR - Phase 1 blockout builder.

Run (rebuilds MASTER_WORLD.blend from scratch; the previous file is archived first):
  blender -b --factory-startup --python build_blockout.py

Idempotent: every run starts from an empty scene, so rerunning never duplicates assets.
"""
import csv
import datetime
import json
import math
import os
import random
import shutil
import sys

import bpy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

import numpy as np  # noqa: E402

import config_layout as C  # noqa: E402
from bld_meshes import OBJECT_PREFIX, MeshBuilder, build_plot_mesh  # noqa: E402
from geo import OBB, Path2D, river_distance, river_path, terrain_height  # noqa: E402
from layout_solver import LayoutSolver  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
MASTER_DIR = os.path.join(ROOT, "00_MASTER")
BLEND_PATH = os.path.join(MASTER_DIR, "MASTER_WORLD.blend")
LOG = []


def log(msg):
    LOG.append(msg)
    print("[village] " + msg)


# ============================================================================
# Scene setup
# ============================================================================
COLLECTIONS = [
    "ENV_TERRAIN", "ENV_WATER", "ENV_ROADS", "ENV_FIELDS", "ENV_VEGETATION", "ENV_BACKDROP",
    "BLD_HOUSES", "BLD_SHOPS", "BLD_UTILITY", "BLD_LANDMARKS", "PRP_ASSETS",
    "INT_INTERIORS", "CHR_HUMANS", "CHR_ANIMALS", "VEH_TRANSPORT", "FX_ENVIRONMENT",
    "LIGHTING_CAMERAS", "REVIEW_LABELS", "PROTO_LIBRARY",
]
COLL = {}


def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "AMALTASPUR_MASTER"
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    sc.render.engine = "BLENDER_EEVEE"
    for attr, val in (("taa_render_samples", 48), ("use_shadows", True), ("use_raytracing", True),
                      ("shadow_ray_count", 2), ("shadow_step_count", 8)):
        try:
            setattr(sc.eevee, attr, val)
        except Exception:
            pass
    for vt in ("AgX", "Filmic", "Standard"):
        try:
            sc.view_settings.view_transform = vt
            break
        except Exception:
            continue
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    root = sc.collection
    for name in COLLECTIONS:
        c = bpy.data.collections.new(name)
        root.children.link(c)
        COLL[name] = c
    vl = bpy.context.view_layer
    vl.layer_collection.children["PROTO_LIBRARY"].exclude = True
    COLL["REVIEW_LABELS"].hide_render = True
    log("Scene: metric 1 BU = 1 m, EEVEE review renders, view transform %s" % sc.view_settings.view_transform)


# ============================================================================
# Materials
# ============================================================================
def hex_lin(h):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def _nt(mat):
    if mat.node_tree is None:
        try:
            mat.use_nodes = True
        except Exception:
            pass
    return mat.node_tree


def principled(mat):
    return next(n for n in _nt(mat).nodes if n.type == "BSDF_PRINCIPLED")


ROUGH = {"water": 0.06, "shutter_metal": 0.45, "roof_tin": 0.5, "road_tar": 0.85, "saffron": 0.6}


def make_materials():
    M = {}
    for key, hx in C.PALETTE.items():
        name = "MAT_BLK_" + "".join(p.capitalize() for p in key.split("_"))
        m = bpy.data.materials.new(name)
        b = principled(m)
        col = hex_lin(hx)
        b.inputs["Base Color"].default_value = (*col, 1.0)
        b.inputs["Roughness"].default_value = ROUGH.get(key, 0.82)
        if key in ("shutter_metal", "roof_tin"):
            b.inputs["Metallic"].default_value = 0.6
        if key == "label_text":
            b.inputs["Emission Color"].default_value = (1, 1, 1, 1)
            b.inputs["Emission Strength"].default_value = 4.0
        m.diffuse_color = (*col, 1.0)
        M[key] = m
    M["terrain"] = terrain_material()
    return M


def terrain_material():
    m = bpy.data.materials.new("MAT_BLK_Terrain_GrassRock")
    nt = _nt(m)
    nodes, links = nt.nodes, nt.links
    for n in list(nodes):
        nodes.remove(n)
    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (900, 0)
    grass = nodes.new("ShaderNodeBsdfPrincipled")
    grass.location = (300, 200)
    grass.inputs["Roughness"].default_value = 0.9
    rock = nodes.new("ShaderNodeBsdfPrincipled")
    rock.location = (300, -300)
    rock.inputs["Base Color"].default_value = (*hex_lin(C.PALETTE["rock"]), 1)
    rock.inputs["Roughness"].default_value = 0.85
    mix = nodes.new("ShaderNodeMixShader")
    mix.location = (650, 0)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-300, 300)
    noise.inputs["Scale"].default_value = 0.02
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (0, 300)
    ramp.color_ramp.elements[0].color = (*hex_lin(C.PALETTE["grass_lush"]), 1)
    ramp.color_ramp.elements[1].color = (*hex_lin(C.PALETTE["grass_dry"]), 1)
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], grass.inputs["Base Color"])
    geo = nodes.new("ShaderNodeNewGeometry")
    geo.location = (-500, -200)
    sep_n = nodes.new("ShaderNodeSeparateXYZ")
    sep_n.location = (-300, -100)
    sep_p = nodes.new("ShaderNodeSeparateXYZ")
    sep_p.location = (-300, -300)
    links.new(geo.outputs["Normal"], sep_n.inputs[0])
    links.new(geo.outputs["Position"], sep_p.inputs[0])
    mr_n = nodes.new("ShaderNodeMapRange")
    mr_n.location = (-100, -100)
    mr_n.inputs["From Min"].default_value = 0.80
    mr_n.inputs["From Max"].default_value = 0.93
    mr_n.inputs["To Min"].default_value = 1.0
    mr_n.inputs["To Max"].default_value = 0.0
    links.new(sep_n.outputs["Z"], mr_n.inputs["Value"])
    mr_h = nodes.new("ShaderNodeMapRange")
    mr_h.location = (-100, -300)
    mr_h.inputs["From Min"].default_value = 25.0
    mr_h.inputs["From Max"].default_value = 90.0
    mr_h.inputs["To Min"].default_value = 0.0
    mr_h.inputs["To Max"].default_value = 0.75
    links.new(sep_p.outputs["Z"], mr_h.inputs["Value"])
    mx = nodes.new("ShaderNodeMath")
    mx.operation = "MAXIMUM"
    mx.location = (100, -200)
    links.new(mr_n.outputs["Result"], mx.inputs[0])
    links.new(mr_h.outputs["Result"], mx.inputs[1])
    links.new(mx.outputs["Value"], mix.inputs[0])
    links.new(grass.outputs["BSDF"], mix.inputs[1])
    links.new(rock.outputs["BSDF"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])
    m.diffuse_color = (*hex_lin(C.PALETTE["grass_lush"]), 1)
    return m


def link(obj, coll):
    COLL[coll].objects.link(obj)
    return obj


def mesh_object(name, verts, faces, mat, coll, smooth=False, mat_idx=None, mats=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    if mats:
        for m in mats:
            me.materials.append(m)
    else:
        me.materials.append(mat)
    if mat_idx is not None:
        me.polygons.foreach_set("material_index", mat_idx)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    return link(bpy.data.objects.new(name, me), coll)


def grid_faces(nx, ny, offset=0):
    idx = np.arange(nx * ny).reshape(ny, nx) + offset
    a = idx[:-1, :-1].ravel()
    b = idx[:-1, 1:].ravel()
    c = idx[1:, 1:].ravel()
    d = idx[1:, :-1].ravel()
    return np.stack([a, b, c, d], 1).tolist()


# ============================================================================
# Environment
# ============================================================================
def build_terrain(M):
    xs = np.arange(C.TERRAIN_X[0], C.TERRAIN_X[1] + 0.1, C.TERRAIN_CELL)
    ys = np.arange(C.TERRAIN_Y[0], C.TERRAIN_Y[1] + 0.1, C.TERRAIN_CELL)
    X, Y = np.meshgrid(xs, ys)
    Z = terrain_height(X, Y)
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1).tolist()
    obj = mesh_object("OBJ_Terrain_Master", verts, grid_faces(len(xs), len(ys)), M["terrain"], "ENV_TERRAIN", smooth=True)
    log("Terrain: %d x %d m, %d verts, height %.1f..%.1f m" % (
        xs[-1] - xs[0], ys[-1] - ys[0], len(verts), Z.min(), Z.max()))
    return obj


def build_backdrop(M):
    """Low-res outer terrain ring out to the horizon: continues the master terrain and
    raises a ring of hills (tallest in the north).  Inside the master terrain rectangle it
    drops below ground so it never shows through."""
    step = 50.0
    xs = np.arange(-3500.0, 3500.1, step)
    ys = np.arange(-3500.0, 3500.1, step)
    X, Y = np.meshgrid(xs, ys)
    x0, x1 = C.TERRAIN_X
    y0, y1 = C.TERRAIN_Y
    dx = np.maximum(np.maximum(x0 - X, X - x1), 0.0)
    dy = np.maximum(np.maximum(y0 - Y, Y - y1), 0.0)
    dout = np.hypot(dx, dy)
    base = terrain_height(X, Y)
    north = np.clip((Y + 500.0) / 2000.0, 0.0, 1.0)
    ridge = (0.55 + 0.30 * np.sin(X * 0.0021 + 0.8) + 0.15 * np.sin(X * 0.0067 + Y * 0.0031)
             + 0.10 * np.sin(X * 0.017 + Y * 0.011))
    rise = np.clip(dout / 1300.0, 0.0, 1.0) ** 1.4
    Z = base + rise * (70.0 + 260.0 * north) * ridge
    inside = (X > x0) & (X < x1) & (Y > y0) & (Y < y1)
    edge = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1) & ~inside
    Z[inside] = -9.0
    Z[edge] = base[edge] - 0.6
    verts = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1).tolist()
    mesh_object("OBJ_Backdrop_OuterTerrain", verts, grid_faces(len(xs), len(ys)), M["terrain"], "ENV_BACKDROP", smooth=True)


def ribbon(path, half_w, z_fn, step=2.0, t0=0.0, t1=None):
    t1 = path.length if t1 is None else t1
    ts = np.arange(t0, t1 + 1e-6, step)
    if ts[-1] < t1:
        ts = np.append(ts, t1)
    verts, faces = [], []
    for i, t in enumerate(ts):
        p = path.point(t)
        n = path.normal(t)
        for s in (1, -1):
            q = p + n * half_w * s
            verts.append((q[0], q[1], 0.0))
    V = np.array(verts)
    V[:, 2] = z_fn(V[:, 0], V[:, 1], np.repeat(ts, 2))
    for i in range(len(ts) - 1):
        a = 2 * i
        faces.append((a, a + 2, a + 3, a + 1))
    return V.tolist(), faces


def build_water(M):
    rp = Path2D(C.RIVER_CTRL, 30.0, step=4.0)
    verts, faces = ribbon(rp, 21.0, lambda x, y, t: np.full_like(x, C.WATER_Z), step=4.0)
    mesh_object("OBJ_River_Water", verts, faces, M["water"], "ENV_WATER")
    log("River: %.0f m long, water level %.1f m" % (rp.length, C.WATER_Z))


def bridge_profile(paths):
    """Return (t_centre, deck_z, half_span) where R04 crosses the river."""
    p = paths["R04"]
    d = river_distance(p.pts[:, 0], p.pts[:, 1])
    i = int(np.argmin(d))
    return float(p.ts[i]), 1.6, 24.0


def build_roads(M, paths):
    tc, deck, half = bridge_profile(paths)
    for rid, spec in C.ROADS.items():
        path = paths[rid]
        off = C.ROAD_Z_OFFSET[spec["kind"]]

        def zf(x, y, t, off=off, rid=rid):
            z = terrain_height(x, y) + off
            if rid == "R04":
                ramp = deck - np.maximum(np.abs(t - tc) - half, 0.0) * (deck / 14.0)
                z = np.maximum(z, ramp + off)
            return z

        verts, faces = ribbon(path, spec["width"] / 2.0, zf, step=2.0)
        mat = M[{"paved": "road_tar", "dirt_main": "road_dirt_main", "dirt": "road_dirt", "stone": "road_stone"}[spec["kind"]]]
        mesh_object("OBJ_Road_%s_%s" % (rid, spec["name"]), verts, faces, mat, "ENV_ROADS")
    # chowk plaza
    n = 48
    verts = [(0.0, 0.0, 0.0)] + [(C.CHOWK_RADIUS * math.cos(2 * math.pi * i / n),
                                  C.CHOWK_RADIUS * math.sin(2 * math.pi * i / n), 0.0) for i in range(n)]
    V = np.array(verts)
    V[:, 2] = terrain_height(V[:, 0], V[:, 1]) + 0.18
    faces = [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)]
    mesh_object("OBJ_Chowk_Plaza", V.tolist(), faces, M["chowk_stone"], "ENV_ROADS")
    log("Roads: %d ribbons, total %.0f m" % (len(paths), sum(p.length for p in paths.values())))


def place_obj(mb, name, coll, loc, rot=0.0):
    obj = bpy.data.objects.new(name, mb.to_mesh(name))
    obj.location = loc
    obj.rotation_euler = (0.0, 0.0, rot)
    return link(obj, coll)


def build_bridge_and_ghat(M, paths):
    p = paths["R04"]
    tc, deck, half = bridge_profile(paths)
    c = p.point(tc)
    tang = p.tangent(tc)
    ang = math.atan2(tang[1], tang[0])
    mb = MeshBuilder()
    L, W = half * 2 + 4, 8.0
    mb.box(-L / 2, L / 2, -W / 2, W / 2, deck - 0.9, deck + 0.05, M["plinth_stone"])
    for y0, y1 in ((W / 2 - 0.35, W / 2), (-W / 2, -W / 2 + 0.35)):
        mb.box(-L / 2, L / 2, y0, y1, deck, deck + 1.0, M["plinth_stone"])
    for x in (-12.0, 0.0, 12.0):
        mb.box(x - 1.2, x + 1.2, -W / 2, W / 2, C.RIVER_BED_Z - 0.5, deck - 0.9, M["plinth_stone"])
        mb.frustum(x, -W / 2, C.RIVER_BED_Z - 0.5, deck - 0.9, 1.3, 1.3, 3, M["plinth_stone"], rot=-math.pi / 2)
        mb.frustum(x, W / 2, C.RIVER_BED_Z - 0.5, deck - 0.9, 1.3, 1.3, 3, M["plinth_stone"], rot=math.pi / 2)
    place_obj(mb, "OBJ_Landmark_Bridge_001", "BLD_LANDMARKS", (c[0], c[1], 0.0), ang)

    # Ghat: stone steps from the temple path down to the water
    rv = river_path()
    target = np.array([128.0, 50.0])
    ti, _ = rv.nearest_t(target)
    q = rv.point(ti)
    dirv = target - q
    dirv /= np.linalg.norm(dirv)
    base = q + dirv * 9.0
    gang = math.atan2(dirv[1], dirv[0]) - math.pi / 2       # local +Y points up the bank
    top_z = float(terrain_height(*(q + dirv * 26.0))) + 0.1
    mb = MeshBuilder()
    steps = 14
    for i in range(steps):
        y0 = i * 1.2
        z1 = C.WATER_Z - 0.6 + (top_z - C.WATER_Z + 0.6) * (i + 1) / steps
        mb.box(-11, 11, y0, 17.0, C.RIVER_BED_Z - 0.5, z1, M["road_stone"])
    for s in (-1, 1):
        mb.box(s * 11 - 0.6, s * 11 + 0.6, 0.0, 17.0, C.RIVER_BED_Z - 0.5, top_z + 0.9, M["plinth_stone"])
    mb.frustum(9.5, 15.0, top_z, top_z + 3.2, 1.0, 1.0, 4, M["temple_white"], rot=math.pi / 4)
    mb.frustum(9.5, 15.0, top_z + 3.2, top_z + 4.6, 1.4, 0.0, 8, M["temple_white"])
    place_obj(mb, "OBJ_Landmark_Ghat_001", "BLD_LANDMARKS", (base[0], base[1], 0.0), gang)
    log("Bridge at R04 t=%.0f m (deck %.1f m); ghat %d steps" % (tc, deck, steps))


def build_gate(M, paths):
    p = paths[C.GATE_ROAD]
    t, _ = p.nearest_t(C.GATE_POINT)
    c = p.point(t)
    tang = p.tangent(t)
    ang = math.atan2(tang[1], tang[0]) - math.pi / 2
    z = float(terrain_height(c[0], c[1]))
    mb = MeshBuilder()
    hw = p.width / 2.0 + 1.6
    for s in (-1, 1):
        x = s * hw
        mb.box(x - 0.9, x + 0.9, -0.9, 0.9, -1.0, 6.2, M["wall_sandstone"])
        mb.frustum(x, 0.0, 6.2, 7.6, 1.0, 0.0, 4, M["roof_terracotta"], rot=math.pi / 4)
    mb.box(-hw, hw, -0.7, 0.7, 5.0, 6.0, M["wall_sandstone"])
    mb.box(-3.6, 3.6, -0.75, -0.65, 5.15, 5.85, M["saffron"])        # name board
    mb.box(-1.6, 1.6, -1.6, 1.6, 6.0, 6.25, M["plinth_stone"])
    for dx in (-1.3, 1.3):
        for dy in (-1.3, 1.3):
            mb.box(dx - 0.12, dx + 0.12, dy - 0.12, dy + 0.12, 6.25, 7.6, M["wall_sandstone"])
    mb.frustum(0.0, 0.0, 7.6, 9.4, 2.0, 0.0, 8, M["wall_sandstone"])
    place_obj(mb, "OBJ_Landmark_Gate_001", "BLD_LANDMARKS", (c[0], c[1], z), ang)
    log("Entrance gate on %s at t=%.0f m" % (C.GATE_ROAD, t))


def build_chowk_features(M):
    z = float(terrain_height(0.0, 0.0)) + 0.18
    mb = MeshBuilder()
    mb.frustum(0, 0, -0.5, 0.75, 7.5, 7.5, 32, M["plinth_stone"])               # chabutra
    mb.frustum(0, 0, 0.75, 7.5, 2.4, 1.5, 12, M["bark"])                       # trunk
    for (x, y, r) in ((5.0, 3.0, 1.0), (-4.5, 4.0, 0.9), (2.0, -5.0, 0.8), (-3.0, -4.0, 0.7)):
        mb.frustum(x, y, 0.75, 8.5, 0.35 * r, 0.3 * r, 6, M["bark"])           # aerial roots
    rng = random.Random(7)
    for i in range(9):
        a = 2 * math.pi * i / 9
        rr = rng.uniform(5, 10)
        mb.ellipsoid(rr * math.cos(a), rr * math.sin(a), rng.uniform(10, 12.5),
                     rng.uniform(7, 9), rng.uniform(7, 9), rng.uniform(3.5, 4.5), M["foliage_banyan"])
    mb.ellipsoid(0, 0, 13.5, 11, 11, 4.5, M["foliage_banyan"])
    place_obj(mb, "OBJ_Landmark_Banyan_Chowk", "ENV_VEGETATION", (0.0, 0.0, z))
    # well
    mb = MeshBuilder()
    mb.frustum(0, 0, -0.5, 0.95, 1.5, 1.5, 20, M["plinth_stone"])
    mb.frustum(0, 0, 0.9, 0.97, 1.15, 1.15, 20, M["water"])
    for s in (-1, 1):
        mb.box(s * 1.3 - 0.12, s * 1.3 + 0.12, -0.12, 0.12, 0.95, 2.8, M["wood_dark"])
    mb.box(-1.45, 1.45, -0.1, 0.1, 2.6, 2.8, M["wood_dark"])
    place_obj(mb, "OBJ_Prop_Well_Chowk", "PRP_ASSETS", (15.0, -11.0, float(terrain_height(15, -11)) + 0.18))
    # small shrine
    mb = MeshBuilder()
    mb.box(-1.4, 1.4, -1.4, 1.4, -0.4, 0.5, M["plinth_stone"])
    mb.box(-1.0, 1.0, -1.0, 1.0, 0.5, 2.6, M["temple_white"])
    mb.frustum(0, 0, 2.6, 4.6, 1.2, 0.0, 4, M["temple_white"], rot=math.pi / 4)
    mb.box(-0.5, 0.5, -1.06, -0.98, 0.6, 1.9, M["saffron"])
    place_obj(mb, "OBJ_Landmark_Shrine_Chowk", "BLD_LANDMARKS", (-15.0, 13.5, float(terrain_height(-15, 13.5)) + 0.18),
              math.atan2(-13.5, 15.0) + math.pi / 2)


# ============================================================================
# Buildings
# ============================================================================
def build_plots(M, plots):
    counters = {}
    for p in plots:
        prefix, coll = OBJECT_PREFIX[p["family"]]
        counters[prefix] = counters.get(prefix, 0) + 1
        name = "%s_%03d" % (prefix, counters[prefix])
        p["object"] = name
        p["collection"] = coll
        mb = build_plot_mesh(p, M)
        obj = place_obj(mb, name, coll, (p["x"], p["y"], p["z"]), p["rot"])
        obj["plot_id"] = "P%02d" % p["num"]
        obj["family"] = p["family"]
        obj["neighbourhood"] = p["hood"]
        obj["status"] = "blockout"
    log("Buildings: %d plots built" % len(plots))


# ============================================================================
# Fields and vegetation
# ============================================================================
def build_fields(M, paths, plots):
    rng = random.Random(11)
    names = [c[0] for c in C.CROPS]
    weights = [c[1] for c in C.CROPS]
    mats = [M["crop_" + n] for n in names]
    verts, faces, midx = [], [], []
    road_pts = [(p.pts, p.width / 2.0) for p in paths.values()]
    cells = []
    for z in C.FIELD_ZONES:
        cw, ch = z["cell"]
        x = z["x"][0]
        while x + cw <= z["x"][1]:
            y = z["y"][0]
            while y + ch <= z["y"][1]:
                cells.append((x + C.FIELD_GAP / 2, x + cw - C.FIELD_GAP / 2, y + C.FIELD_GAP / 2, y + ch - C.FIELD_GAP / 2))
                y += ch
            x += cw
    kept = 0
    for (x0, x1, y0, y1) in cells:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        box = OBB(cx, cy, (x1 - x0) / 2, (y1 - y0) / 2, 0.0)
        if any(box.dist_points(pts).min() < hw + 3.0 for pts, hw in road_pts):
            continue
        if any(box.overlaps(pl["obb"], 10.0) for pl in plots):
            continue
        if box.dist_points(river_path().pts).min() < 26.0:
            continue
        if math.hypot(cx, cy) < 135:
            continue
        gx = np.linspace(x0, x1, 7)
        gy = np.linspace(y0, y1, 7)
        GX, GY = np.meshgrid(gx, gy)
        GZ = terrain_height(GX, GY)
        if GZ.max() - GZ.min() > 4.0 or GZ.max() > 20:
            continue
        o = len(verts)
        verts.extend(np.stack([GX.ravel(), GY.ravel(), GZ.ravel() + 0.06], 1).tolist())
        fs = grid_faces(7, 7, o)
        faces.extend(fs)
        midx.extend([rng.choices(range(len(names)), weights)[0]] * len(fs))
        kept += 1
    # one crop per field (not per face)
    fid = 0
    per = 36
    for i in range(0, len(midx), per):
        crop = midx[i]
        midx[i:i + per] = [crop] * per
        fid += 1
    mesh_object("OBJ_Fields_Blockout", verts, faces, None, "ENV_FIELDS", mat_idx=midx, mats=mats)
    log("Fields: %d patches from %d candidate cells" % (kept, len(cells)))
    return kept


def tree_protos(M):
    protos = {}

    def proto(name, build):
        coll = bpy.data.collections.new("PROTO_" + name)
        COLL["PROTO_LIBRARY"].children.link(coll)
        mb = MeshBuilder()
        build(mb)
        obj = bpy.data.objects.new("OBJ_Tree_%s_Proto" % name, mb.to_mesh("ME_Tree_%s" % name))
        coll.objects.link(obj)
        protos[name] = coll

    proto("Mango", lambda mb: (mb.frustum(0, 0, -0.3, 3.0, 0.35, 0.25, 8, M["bark"]),
                               mb.ellipsoid(0, 0, 5.2, 4.2, 4.2, 3.3, M["foliage_mango"]),
                               mb.ellipsoid(1.5, 0.8, 6.6, 2.6, 2.6, 2.0, M["foliage_mango"])))
    proto("Neem", lambda mb: (mb.frustum(0, 0, -0.3, 4.2, 0.3, 0.2, 8, M["bark"]),
                              mb.ellipsoid(0, 0, 6.6, 3.4, 3.4, 2.6, M["foliage_neem"]),
                              mb.ellipsoid(-1.6, 0.6, 5.4, 2.3, 2.3, 1.8, M["foliage_neem"]),
                              mb.ellipsoid(1.4, -0.9, 7.6, 2.0, 2.0, 1.6, M["foliage_neem"])))
    proto("Palm", lambda mb: (mb.frustum(0, 0, -0.3, 10.5, 0.28, 0.18, 8, M["bark"]),
                              mb.ellipsoid(0, 0, 10.8, 3.6, 3.6, 1.0, M["foliage_palm"]),
                              mb.frustum(0, 0, 10.0, 11.4, 2.8, 0.2, 10, M["foliage_palm"])))
    proto("Amaltas", lambda mb: (mb.frustum(0, 0, -0.3, 3.0, 0.25, 0.18, 8, M["bark"]),
                                 mb.ellipsoid(0, 0, 5.0, 3.2, 3.2, 2.5, M["foliage_neem"]),
                                 mb.ellipsoid(0.4, 0.3, 5.6, 3.0, 3.0, 2.1, M["foliage_amaltas"])))
    return protos


def scatter_trees(M, paths, plots):
    protos = tree_protos(M)
    rng = random.Random(23)
    road_pts = np.concatenate([p.pts for p in paths.values()])
    road_hw = np.concatenate([np.full(len(p.pts), p.width / 2.0) for p in paths.values()])
    placed = []
    grid = {}
    tries = 0
    obbs = [pl["obb"] for pl in plots]

    def near_existing(x, y):
        gx, gy = int(x // C.TREE_MIN_SPACING), int(y // C.TREE_MIN_SPACING)
        for i in range(gx - 1, gx + 2):
            for j in range(gy - 1, gy + 2):
                for (px, py) in grid.get((i, j), []):
                    if (px - x) ** 2 + (py - y) ** 2 < C.TREE_MIN_SPACING ** 2:
                        return True
        return False

    cam_lines = [(np.array(c["pos"][:2], float), np.array(c["target"][:2], float))
                 for c in C.CAMERAS.values() if c.get("ground")]

    def blocks_camera(x, y):
        """Keep review-camera sightlines clear (no tree within 22 m of a ground camera,
        or within 7 m of its first 90 m of view line)."""
        p = np.array([x, y])
        for a, b in cam_lines:
            if np.linalg.norm(p - a) < 22.0:
                return True
            ab = b - a
            L = np.linalg.norm(ab)
            u = ab / L
            s = float((p - a) @ u)
            if 0 < s < min(L, 90.0) and abs(float(np.cross(u, p - a))) < 7.0:
                return True
        return False

    N = 30000
    CX = np.array([rng.uniform(-480, 480) for _ in range(N)])
    CY = np.array([rng.uniform(-480, 340) for _ in range(N)])
    CRD = river_distance(CX, CY)
    CZ = terrain_height(CX, CY)
    while len(placed) < C.TREE_COUNT_TARGET and tries < N:
        x, y, rd, z = float(CX[tries]), float(CY[tries]), float(CRD[tries]), float(CZ[tries])
        tries += 1
        r = math.hypot(x, y)
        # acceptance weight: dense along river banks and village fringe, sparse in the open fields
        w = 0.12
        if 24 < rd < 60:
            w = 0.9
        elif r < 230:
            w = 0.55
        if rng.random() > w:
            continue
        if rd < 22 or r < C.CHOWK_RADIUS + 6:
            continue
        d = np.hypot(road_pts[:, 0] - x, road_pts[:, 1] - y) - road_hw
        if d.min() < 3.0:
            continue
        if any(o.dist_points([(x, y)])[0] < 3.5 for o in obbs):
            continue
        if near_existing(x, y):
            continue
        if blocks_camera(x, y):
            continue
        if z > 35:
            continue
        if rd < 60:
            kind = rng.choices(["Palm", "Neem", "Mango"], [0.45, 0.3, 0.25])[0]
        elif r < 230:
            kind = rng.choices(["Mango", "Neem", "Amaltas", "Palm"], [0.35, 0.33, 0.2, 0.12])[0]
        else:
            kind = rng.choices(["Mango", "Neem", "Palm"], [0.45, 0.4, 0.15])[0]
        e = bpy.data.objects.new("INST_Tree_%s_%03d" % (kind, len(placed) + 1), None)
        e.instance_type = "COLLECTION"
        e.instance_collection = protos[kind]
        e.location = (x, y, z)
        e.rotation_euler = (0, 0, rng.uniform(0, 2 * math.pi))
        s = rng.uniform(0.75, 1.3)
        e.scale = (s, s, s * rng.uniform(0.9, 1.1))
        link(e, "ENV_VEGETATION")
        placed.append((x, y))
        grid.setdefault((int(x // C.TREE_MIN_SPACING), int(y // C.TREE_MIN_SPACING)), []).append((x, y))
    # peepal tree inside the temple compound (hero tree for the temple)
    tp = next(p for p in plots if p["family"] == "temple")
    lx, ly = -7.5, -6.5
    o = tp["obb"]
    wx, wy = o.c + lx * o.u + ly * o.v
    mb = MeshBuilder()
    mb.frustum(0, 0, 0.0, 5.0, 0.9, 0.6, 10, M["bark"])
    mb.ellipsoid(0, 0, 8.5, 6.5, 6.5, 4.0, M["foliage_banyan"])
    mb.ellipsoid(2.0, 1.0, 10.5, 4.0, 4.0, 2.8, M["foliage_neem"])
    place_obj(mb, "OBJ_Landmark_Peepal_Temple", "ENV_VEGETATION", (wx, wy, tp["z"] + 0.75))
    log("Vegetation: %d tree instances (4 prototypes) + banyan + peepal" % len(placed))
    return len(placed)


# ============================================================================
# World, lighting, cameras, labels
# ============================================================================
def build_world():
    w = bpy.data.worlds.new("WLD_Day_Clear")
    bpy.context.scene.world = w
    nt = _nt(w)
    nodes, links = nt.nodes, nt.links
    for n in list(nodes):
        nodes.remove(n)
    out = nodes.new("ShaderNodeOutputWorld")
    bg = nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    tc = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    ramp = nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position = 0.0
    els[0].color = (*hex_lin("#F2DCB8"), 1)
    els[1].position = 0.45
    els[1].color = (*hex_lin("#5E93CC"), 1)
    mid = els.new(0.12)
    mid.color = (*hex_lin("#B9D2E6"), 1)
    links.new(tc.outputs["Generated"], sep.inputs[0])
    links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bg.inputs["Color"])
    links.new(bg.outputs["Background"], out.inputs["Surface"])

    sun_d = bpy.data.lights.new("LGT_Sun_Afternoon", "SUN")
    sun_d.energy = 4.2
    sun_d.color = (1.0, 0.9, 0.76)
    sun_d.angle = math.radians(1.2)
    sun = bpy.data.objects.new("LGT_Sun_Afternoon", sun_d)
    sun.rotation_euler = (math.radians(56), 0.0, math.radians(-40))
    link(sun, "LIGHTING_CAMERAS")


def look_rot(pos, target):
    from mathutils import Vector
    d = Vector(target) - Vector(pos)
    return d.to_track_quat("-Z", "Y").to_euler()


def build_cameras():
    for name, cfg in C.CAMERAS.items():
        cam = bpy.data.cameras.new(name)
        cam.clip_start = 0.1
        cam.clip_end = 8000
        x, y, z = cfg["pos"]
        tx, ty, tz = cfg["target"]
        if cfg.get("ground"):
            z += float(terrain_height(x, y))
            tz += float(terrain_height(tx, ty))
        if cfg.get("ortho"):
            cam.type = "ORTHO"
            cam.ortho_scale = cfg["ortho_scale"]
        else:
            cam.lens = cfg["lens"]
        obj = bpy.data.objects.new(name, cam)
        obj.location = (x, y, z)
        if cfg.get("ortho"):
            obj.rotation_euler = (0, 0, 0)
        else:
            obj.rotation_euler = look_rot((x, y, z), (tx, ty, tz))
        link(obj, "LIGHTING_CAMERAS")
    bpy.context.scene.camera = bpy.data.objects["CAM_Aerial_Establishing_001"]


def build_labels(M, plots):
    for p in plots:
        cu = bpy.data.curves.new("TXT_Plot_%02d" % p["num"], "FONT")
        cu.body = str(p["num"])
        cu.size = 4.2
        cu.align_x = "CENTER"
        cu.align_y = "CENTER"
        cu.materials.append(M["label_text"])
        t = bpy.data.objects.new("LBL_Plot_%02d" % p["num"], cu)
        t.location = (p["x"], p["y"], 120.0)
        link(t, "REVIEW_LABELS")
        mb = MeshBuilder()
        r = 3.2 if p["num"] < 10 else 3.7
        mb.frustum(0, 0, 0, 0.2, r, r, 24, M["label_plate"])
        place_obj(mb, "LBL_Plate_%02d" % p["num"], "REVIEW_LABELS", (p["x"], p["y"], 119.5))


# ============================================================================
# Records
# ============================================================================
def write_records(plots, paths, stats):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with open(os.path.join(MASTER_DIR, "PLOT_SCHEDULE.csv"), "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["plot_id", "family", "label", "neighbourhood", "road", "x_m", "y_m", "base_z_m",
                     "frontage_m", "depth_m", "rotation_deg", "wall_colour", "blender_object", "collection", "status"])
        for p in plots:
            wr.writerow(["P%02d" % p["num"], p["family"], p["label"], p["hood"], p["road"],
                         round(p["x"], 1), round(p["y"], 1), round(p["z"], 2), round(p["w"], 1), round(p["d"], 1),
                         round(math.degrees(p["rot"]) % 360, 1), p["wall"], p["object"], p["collection"],
                         "layout approved G1 (2026-11-12)"])
    reg = os.path.join(MASTER_DIR, "ASSET_REGISTRY.csv")
    with open(reg, "w", newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["asset_id", "name", "category", "file", "collection", "version", "dimensions_m",
                     "materials", "intended_use", "camera_distance", "rig_status", "approval", "notes"])
        blend = "00_MASTER/MASTER_WORLD.blend"
        rows = [
            ("ENV-0001", "OBJ_Terrain_Master", "environment", "ENV_TERRAIN",
             "%dx%d" % (C.TERRAIN_X[1] - C.TERRAIN_X[0], C.TERRAIN_Y[1] - C.TERRAIN_Y[0]), "MAT_BLK_Terrain_GrassRock",
             "master ground", "all", "analytic height fn in geo.py"),
            ("ENV-0002", "OBJ_River_Water", "environment", "ENV_WATER", "~30 wide", "MAT_BLK_Water", "river", "all", ""),
            ("ENV-0003", "OBJ_Road_* (%d)" % len(paths), "environment", "ENV_ROADS", "-", "MAT_BLK_Road*", "roads", "all", ""),
            ("ENV-0004", "OBJ_Chowk_Plaza", "environment", "ENV_ROADS", "r=%d" % C.CHOWK_RADIUS, "MAT_BLK_ChowkStone",
             "main square", "all", ""),
            ("ENV-0005", "OBJ_Fields_Blockout", "environment", "ENV_FIELDS", "%d patches" % stats["fields"],
             "MAT_BLK_Crop*", "farmland", "wide", ""),
            ("ENV-0006", "INST_Tree_* (%d)" % stats["trees"], "vegetation", "ENV_VEGETATION", "-", "MAT_BLK_Foliage*",
             "trees (instances)", "wide/medium", "4 prototype collections in PROTO_LIBRARY"),
            ("ENV-0007", "OBJ_Landmark_Banyan_Chowk", "vegetation", "ENV_VEGETATION", "~24 wide", "MAT_BLK_FoliageBanyan",
             "hero tree", "all", "needs hero sculpt in Phase 1b"),
            ("ENV-0008", "OBJ_Backdrop_OuterTerrain", "environment", "ENV_BACKDROP", "7000x7000", "terrain",
             "horizon hills ring", "far", "50 m grid, drops under the master terrain"),
            ("LMK-0001", "OBJ_Landmark_Gate_001", "landmark", "BLD_LANDMARKS", "~12 wide", "sandstone", "entrance", "all", ""),
            ("LMK-0002", "OBJ_Landmark_Bridge_001", "landmark", "BLD_LANDMARKS", "52x8", "stone", "river crossing", "all", ""),
            ("LMK-0003", "OBJ_Landmark_Ghat_001", "landmark", "BLD_LANDMARKS", "22x17", "stone", "river steps", "all", ""),
            ("LMK-0004", "OBJ_Landmark_Shrine_Chowk", "landmark", "BLD_LANDMARKS", "2.8x2.8", "temple white", "chowk shrine", "medium", ""),
            ("PRP-0001", "OBJ_Prop_Well_Chowk", "prop", "PRP_ASSETS", "r=1.5", "stone", "chowk well", "medium", ""),
        ]
        for r in rows:
            wr.writerow([r[0], r[1], r[2], blend, r[3], C.BLOCKOUT_VERSION, r[4], r[5], r[6], r[7], "n/a",
                         "G1 approved 2026-11-12", r[8]])
        for p in plots:
            wr.writerow(["BLD-%04d" % p["num"], p["object"], p["family"], blend, p["collection"], C.BLOCKOUT_VERSION,
                         "%.1fx%.1f" % (p["w"], p["d"]), "MAT_BLK_*", "plot P%02d (%s)" % (p["num"], p["hood"]),
                         "wide/medium", "n/a", "G1 approved 2026-11-12", "blockout volume only"])
    with open(os.path.join(MASTER_DIR, "layout_plots.json"), "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in p.items() if k != "obb"} for p in plots], f, indent=1)
    with open(os.path.join(MASTER_DIR, "build_log.txt"), "w", encoding="utf-8") as f:
        f.write("Build %s  (%s)\n" % (ts, C.BLOCKOUT_VERSION))
        f.write("\n".join(LOG))


# ============================================================================
def main():
    setup_scene()
    M = make_materials()
    solver = LayoutSolver()
    plots = solver.solve()
    for line in solver.log:
        log("layout: " + line)
    log("Plot mix: %s" % solver.summary())
    paths = solver.paths
    build_terrain(M)
    build_backdrop(M)
    build_water(M)
    build_roads(M, paths)
    build_bridge_and_ghat(M, paths)
    build_gate(M, paths)
    build_chowk_features(M)
    build_plots(M, plots)
    stats = {"fields": build_fields(M, paths, plots), "trees": scatter_trees(M, paths, plots)}
    build_world()
    build_cameras()
    build_labels(M, plots)

    if os.path.exists(BLEND_PATH):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(ROOT, "99_ARCHIVE", "MASTER_WORLD_%s.blend" % stamp)
        shutil.copy2(BLEND_PATH, dst)
        log("Checkpoint: previous master archived to %s" % os.path.basename(dst))
    write_records(plots, paths, stats)
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)
    log("Saved %s" % BLEND_PATH)
    with open(os.path.join(MASTER_DIR, "build_log.txt"), "a", encoding="utf-8") as f:
        f.write("\n" + LOG[-1] + "\n")


if __name__ == "__main__":
    main()
