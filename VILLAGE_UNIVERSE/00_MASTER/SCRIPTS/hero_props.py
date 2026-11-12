"""
HERO PROPS + TABELA + DRESSED STREET (Amaltaspur)

  blender -b --factory-startup --python hero_props.py -- [--render] [--quick] [--only CAM]

Output: 06_PROPS/LIB_Village_Props.blend
  AST_StreetLight_Pole_A, AST_LampPost_Lantern_A, AST_WallLantern_A,
  AST_Planter_Tulsi_A, AST_Planter_Marigold_A, AST_Planter_MoneyPlant_A,
  AST_Bougainvillea_Wall_A, AST_Banana_Plant_A, AST_Hibiscus_Bush_A,
  AST_HandPump_A, AST_Haystack_A, AST_WaterDrum_Bucket_A, AST_BoundaryWall_A, AST_Tabela_A
  STAGE: a dressed village street (hero house + trees linked from their libraries) for day and dusk reviews.
Every asset origin = ground contact point; fronts face -Y.
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

import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "06_PROPS", "LIB_Village_Props.blend")
HOUSE_BLEND = os.path.join(ROOT, "02_ARCHITECTURE", "HOUSES_MEDIUM", "HERO_House_Common_A.blend")
TREES_BLEND = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Trees.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "PH1B_PROPS_STREET_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UP = np.array([0.0, 0.0, 1.0])
LIB = None
SRC = None
LAMP_LIGHTS = []


def nrm(v):
    return v / (np.linalg.norm(v) + 1e-9)


def rand_unit(rng):
    while True:
        v = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)])
        n = np.linalg.norm(v)
        if 0.1 < n <= 1.0:
            return v / n


def asset(name):
    c = bpy.data.collections.new(name)
    LIB.children.link(c)
    return c


def put(hb, name, coll, recalc=True, smooth=False, loc=(0, 0, 0)):
    me = hb.to_mesh("ME_" + name, recalc=recalc)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me)
    o.location = loc
    coll.objects.link(o)
    return o


def lamp_light(coll, name, loc, energy_dusk=60.0, radius=0.08):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = 0.0
    ld.color = (1.0, 0.78, 0.5)
    ld.shadow_soft_size = radius
    ld["energy_dusk"] = energy_dusk
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    coll.objects.link(o)
    LAMP_LIGHTS.append(ld)
    return o


# ---------------------------------------------------------------- leaf sources
def blade(hb, mat, L, Wd, curve=0.2, fold=0.2, prof=0.7, x0=0.0, y0=0.0, rotz=0.0):
    st = 6
    v, f = [], []
    for i in range(st + 1):
        t = i / st
        w = Wd * (math.sin(math.pi * t) ** prof)
        z = -curve * L * t * t
        for sx in (-1, 0, 1):
            x, y = sx * w, t * L
            c, s = math.cos(rotz), math.sin(rotz)
            v.append((x0 + x * c - y * s, y0 + x * s + y * c, z + (fold * w if sx else 0.0)))
    for i in range(st):
        for j in range(2):
            a = i * 3 + j
            f.append((a, a + 1, a + 4, a + 3))
    hb.add(v, f, mat)


def src_obj(name, hb):
    o = bpy.data.objects.new("SRC_" + name, hb.to_mesh("ME_SRC_" + name, recalc=False))
    SRC.objects.link(o)
    return o


def bloom(hb, mat, r, petals=5, cup=0.35):
    for k in range(petals):
        blade(hb, mat, r, r * 0.45, curve=-cup, fold=0.1, prof=0.6, rotz=2 * math.pi * k / petals)


def scatter_volume(rng, n, center, radii, normal_bias=0.3, shell=(0.55, 1.0), lower_cut=-0.6, size=(0.8, 1.2)):
    P, R, S = [], [], []
    c = np.asarray(center, float)
    rx, ry, rz = radii
    while len(P) < n:
        u = rand_unit(rng)
        if u[2] < lower_cut:
            continue
        k = shell[0] + (shell[1] - shell[0]) * rng.random() ** 0.5
        p = c + np.array([u[0] * rx, u[1] * ry, u[2] * rz]) * k
        z = nrm(u + np.array([0, 0, normal_bias]))
        t = nrm(np.cross(z, rand_unit(rng)))
        x = np.cross(t, z)
        e = Matrix(((x[0], t[0], z[0]), (x[1], t[1], z[1]), (x[2], t[2], z[2]))).to_euler()
        P.append(p)
        R.append((e.x, e.y, e.z))
        S.append(rng.uniform(*size))
    return P, R, S


# ============================================================================
def materials():
    return {
        "iron": H.mat_simple("MAT_Metal_CastIron_Black", "#1F1F1F", 0.42, 0.65),
        "galv": H.mat_simple("MAT_Metal_Galvanised", "#8D9396", 0.38, 0.75, noise=0.08),
        "glass": H.mat_glass(),
        "glow": H.mat_glow(),
        "concrete": H.mat_simple("MAT_Concrete_Weathered", "#A39C90", 0.85, noise=0.18),
        "terracotta": H.mat_simple("MAT_Clay_Pot_Terracotta", "#A45A3C", 0.6, noise=0.14),
        "pot_white": H.mat_plaster("MAT_Pot_Limewashed", "#E9DFCB", band="#B5492C", band_top=0.12),
        "soil": H.mat_mud("MAT_Soil_Dark", "#4A3A2C"),
        "leaf_tulsi": H.mat_leaf("MAT_Leaf_Tulsi", ("#3E6A2A", "#527F33", "#6B4E5E")),
        "leaf_dark": H.mat_leaf("MAT_Leaf_Shrub_Dark", ("#2D5523", "#3F6A2C", "#557F37")),
        "leaf_money": H.mat_leaf("MAT_Leaf_MoneyPlant", ("#4F8A2E", "#77A83E", "#B9C65A")),
        "leaf_bougain": H.mat_leaf("MAT_Leaf_Bougainvillea", ("#3B6A2A", "#4D7C31", "#628E3C")),
        "leaf_banana": H.mat_leaf("MAT_Leaf_Banana", ("#5C9433", "#73A83D", "#8DBA4A"), transl=0.3, rough=0.4),
        "leaf_banana_dry": H.mat_simple("MAT_Leaf_Banana_Dry", "#9A8250", 0.8, noise=0.2),
        "bract": H.mat_leaf("MAT_Flower_Bougainvillea", ("#B7286F", "#D63C8E", "#E86AAE"), transl=0.35),
        "marigold": H.mat_leaf("MAT_Flower_Marigold", ("#E36D12", "#F28C1C", "#F6B42C"), transl=0.25),
        "hibiscus": H.mat_leaf("MAT_Flower_Hibiscus", ("#B5182A", "#CF2334", "#E04A3A"), transl=0.3),
        "stem": H.mat_wood("MAT_Wood_Stem_Green", "#4B5A2A", "#6A7A3A", 0.8),
        "bark": H.mat_wood("MAT_Bark_Woody_Stem", "#4A3829", "#6A543F", 0.9),
        "banana_stem": H.mat_simple("MAT_Banana_PseudoStem", "#7E8F4A", 0.6, noise=0.25),
        "wood": H.mat_wood(),
        "wood_dark": H.mat_wood("MAT_Wood_Dark_Aged", "#3E2A1C", "#5A3E29"),
        "bamboo": H.mat_simple("MAT_Bamboo_Pole", "#B59A62", 0.6, noise=0.2),
        "mud": H.mat_mud(),
        "mud_floor": H.mat_mud("MAT_Mud_Floor_Tabela", "#8E6E4E"),
        "plaster": H.mat_plaster("MAT_Wall_Boundary_Lime", "#E6DBC4", band="#9A4A34", band_top=0.45),
        "straw": H.mat_straw(),
        "hay": H.mat_straw("MAT_Hay_Fodder", "#B89A55", "#D9C07A"),
        "dung": H.mat_simple("MAT_DungCake", "#5E4632", 0.95, noise=0.3),
        "rope": H.mat_rope(),
        "pump": H.mat_simple("MAT_Metal_Pump_Painted", "#3D5A6B", 0.5, 0.35, noise=0.1),
        "drum": H.mat_simple("MAT_Plastic_Drum_Blue", "#2F6FB5", 0.4),
        "steel": H.mat_simple("MAT_Metal_Steel_Bucket", "#B9BEC2", 0.25, 0.9),
        "water": H.mat_simple("MAT_Water_Still", "#3C6E68", 0.05),
        "stone": H.mat_stone_blocks(),
        "coping": H.mat_simple("MAT_Stone_Coping_Smooth", "#A39A8C", 0.7, noise=0.12),
        "red_cloth": H.mat_simple("MAT_Cloth_Red", "#A8302A", 0.8, noise=0.15),
    }


# ============================================================================
def street_light(M):
    c = asset("AST_StreetLight_Pole_A")
    hb = HB()
    hb.box(-0.3, 0.3, -0.3, 0.3, -0.4, 0.45, M["concrete"])
    hb.frustum(0, 0, 0.45, 6.6, 0.09, 0.055, 8, M["galv"])
    hb.box(-0.09, 0.09, -0.19, -0.07, 2.6, 3.0, M["galv"])                       # junction box
    pts = [np.array([0.0, 0.0, 6.4]) + np.array([0, -1.5 * math.sin(a), 0.55 * (1 - math.cos(a)) + 0.0])
           for a in np.linspace(0, math.pi / 2.2, 8)]
    for a, b in zip(pts[:-1], pts[1:]):
        hb.rod(M["galv"], a, b, 0.035, 8)
    tip = pts[-1]
    hb.ellipsoid(tip[0], tip[1] - 0.15, tip[2] - 0.02, 0.17, 0.32, 0.08, M["galv"], 12, 6)
    hb.ellipsoid(tip[0], tip[1] - 0.15, tip[2] - 0.07, 0.13, 0.25, 0.025, M["glow"], 12, 4)
    for i in range(5):                                                             # cable coil
        a = i * 1.2
        hb.rod(M["iron"], (0.1 * math.cos(a), 0.1 * math.sin(a), 3.0 + i * 0.05),
               (0.1 * math.cos(a + 1.2), 0.1 * math.sin(a + 1.2), 3.05 + i * 0.05), 0.01, 4)
    put(hb, "GEO_StreetLight_Pole_A", c)
    lamp_light(c, "LGT_StreetLight_A", (tip[0], tip[1] - 0.15, tip[2] - 0.2), 120.0, 0.12)


def lamp_post(M):
    c = asset("AST_LampPost_Lantern_A")
    hb = HB()
    hb.box(-0.32, 0.32, -0.32, 0.32, -0.3, 0.35, M["coping"])
    prof = [(0.17, 0.35), (0.17, 0.45), (0.11, 0.5), (0.08, 0.65), (0.06, 0.9), (0.055, 2.2), (0.08, 2.25),
            (0.08, 2.32), (0.05, 2.4), (0.05, 2.62), (0.11, 2.66), (0.11, 2.7)]
    hb.lathe(M["iron"], prof, 16)
    # lantern
    z0, z1 = 2.7, 3.25
    hb.box(-0.16, 0.16, -0.16, 0.16, z0, z0 + 0.04, M["iron"])
    for dx in (-0.15, 0.15):
        for dy in (-0.15, 0.15):
            hb.box(dx - 0.012, dx + 0.012, dy - 0.012, dy + 0.012, z0, z1, M["iron"])
    for (x0, x1, y0, y1) in ((-0.14, 0.14, -0.15, -0.14), (-0.14, 0.14, 0.14, 0.15), (-0.15, -0.14, -0.14, 0.14), (0.14, 0.15, -0.14, 0.14)):
        hb.box(x0, x1, y0, y1, z0 + 0.04, z1 - 0.02, M["glass"])
    hb.ellipsoid(0, 0, (z0 + z1) / 2, 0.06, 0.06, 0.09, M["glow"], 10, 6)
    hb.frustum(0, 0, z1, z1 + 0.06, 0.2, 0.2, 4, M["iron"], rot=math.pi / 4)
    hb.frustum(0, 0, z1 + 0.06, z1 + 0.3, 0.22, 0.03, 4, M["iron"], rot=math.pi / 4)
    hb.lathe(M["iron"], [(0.0, 0.0), (0.03, 0.02), (0.04, 0.07), (0.01, 0.14), (0.0, 0.16)], 8, 0, 0, z1 + 0.28)
    put(hb, "GEO_LampPost_Lantern_A", c)
    lamp_light(c, "LGT_LampPost_A", (0, 0, (z0 + z1) / 2), 45.0, 0.05)


def wall_lantern(M):
    """Origin = wall surface point; lantern hangs out toward -Y."""
    c = asset("AST_WallLantern_A")
    hb = HB()
    hb.box(-0.08, 0.08, -0.03, 0.0, -0.2, 0.2, M["iron"])
    hb.rod(M["iron"], (0, -0.02, 0.1), (0, -0.42, 0.1), 0.014, 6)
    hb.rod(M["iron"], (0, -0.02, -0.15), (0, -0.3, 0.1), 0.01, 6)
    hb.rod(M["iron"], (0, -0.4, 0.1), (0, -0.4, -0.02), 0.006, 4)
    z0, z1 = -0.36, -0.04
    cy = -0.4
    for dx in (-0.08, 0.08):
        for dy in (-0.08, 0.08):
            hb.box(dx - 0.008, dx + 0.008, cy + dy - 0.008, cy + dy + 0.008, z0, z1, M["iron"])
    hb.box(-0.075, 0.075, cy - 0.075, cy + 0.075, z0 + 0.02, z1 - 0.02, M["glass"])
    hb.ellipsoid(0, cy, (z0 + z1) / 2, 0.035, 0.035, 0.055, M["glow"], 8, 5)
    hb.box(-0.09, 0.09, cy - 0.09, cy + 0.09, z0 - 0.02, z0, M["iron"])
    hb.frustum(0, cy, z1, z1 + 0.12, 0.12, 0.02, 4, M["iron"], rot=math.pi / 4)
    put(hb, "GEO_WallLantern_A", c)
    lamp_light(c, "LGT_WallLantern_A", (0, cy, (z0 + z1) / 2), 18.0, 0.03)


# ---------------------------------------------------------------- planters
POT_A = [(0.0, 0.0), (0.12, 0.0), (0.15, 0.04), (0.2, 0.25), (0.22, 0.34), (0.24, 0.36), (0.235, 0.4), (0.2, 0.4)]
POT_B = [(0.0, 0.0), (0.1, 0.0), (0.2, 0.08), (0.25, 0.2), (0.22, 0.32), (0.15, 0.38), (0.17, 0.42), (0.15, 0.43)]


def planter(M, name, pot, pot_mat, leaf_src, leaf_mat, n_leaf, bush, flowers=None, trailing=False, seed=1):
    c = asset(name)
    hb = HB()
    hb.lathe(pot_mat, pot, 24)
    top = pot[-1][1]
    rtop = max(r for r, _ in pot) * 0.92
    hb.frustum(0, 0, top - 0.06, top - 0.03, rtop, rtop, 20, M["soil"])
    rng = random.Random(seed)
    for _ in range(9):                                                             # stems
        a = rng.uniform(0, 6.28)
        r = rng.uniform(0, rtop * 0.5)
        hb.rod(M["stem"], (r * math.cos(a), r * math.sin(a), top - 0.05),
               (r * math.cos(a) * 1.6 + rng.uniform(-0.05, 0.05), r * math.sin(a) * 1.6, top + bush[2] * rng.uniform(0.9, 1.6)),
               0.008, 4)
    put(hb, "GEO_%s_Pot" % name[4:], c, recalc=False, smooth=True)
    ctr = (0, 0, top + bush[2] * 0.9)
    P, R, S = scatter_volume(rng, n_leaf, ctr, bush, lower_cut=-0.75)
    if trailing:                                                                   # vines spilling over the rim
        for k in range(7):
            a = 2 * math.pi * k / 7 + rng.uniform(-0.2, 0.2)
            for s in np.linspace(0, 1, 14):
                p = np.array([(rtop + 0.03 + 0.1 * s) * math.cos(a), (rtop + 0.03 + 0.1 * s) * math.sin(a), top - s * 0.55])
                P.append(p + rand_unit(rng) * 0.02)
                e = Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(rng.uniform(1.1, 1.6), 3, "Y")
                ee = e.to_euler()
                R.append((ee.x, ee.y, ee.z))
                S.append(rng.uniform(0.8, 1.1))
    H.points_object("FOL_%s_Leaves" % name[4:], P, R, S, c, H.instancer("GN_%s_Leaves" % name[4:], leaf_src))
    if flowers:
        fsrc, nf = flowers
        P, R, S = scatter_volume(rng, nf, ctr, tuple(b * 1.02 for b in bush), normal_bias=1.0, shell=(0.85, 1.05),
                                 lower_cut=-0.2)
        H.points_object("FLW_%s" % name[4:], P, R, S, c, H.instancer("GN_%s_Flowers" % name[4:], fsrc))


def bougainvillea(M, srcs):
    """Spills over a 1.6 m boundary wall: origin = wall base centre, street side = -Y, 3.6 m wide."""
    c = asset("AST_Bougainvillea_Wall_A")
    rng = random.Random(8)
    hb = HB()
    for k in range(5):                                                             # woody trunks behind the wall
        x = rng.uniform(-1.2, 1.2)
        pts = [np.array([x, 0.45, 0.0]), np.array([x * 1.2, 0.4, 1.0]), np.array([x * 1.4, 0.2, 1.7]),
               np.array([x * 1.6 + rng.uniform(-0.3, 0.3), -0.25, 1.9]), np.array([x * 1.8, -0.45, 1.4])]
        for a, b in zip(pts[:-1], pts[1:]):
            hb.rod(M["bark"], a, b, 0.035, 6)
    put(hb, "GEO_Bougainvillea_Stems", c)
    P, R, S = [], [], []
    PF, RF, SF = [], [], []
    for blob in range(14):
        cx = rng.uniform(-1.7, 1.7)
        ctr = np.array([cx, rng.uniform(-0.35, 0.25), rng.uniform(1.55, 2.3)])
        rad = (rng.uniform(0.45, 0.75), rng.uniform(0.35, 0.5), rng.uniform(0.3, 0.45))
        p, r, s = scatter_volume(rng, 380, ctr, rad, lower_cut=-0.9)
        P += p; R += r; S += s
        p, r, s = scatter_volume(rng, 260, ctr, tuple(x * 1.05 for x in rad), normal_bias=0.6, shell=(0.75, 1.05),
                                 lower_cut=-0.95)
        PF += p; RF += r; SF += s
    for drape in range(9):                                                         # cascades down the street face
        cx = rng.uniform(-1.6, 1.6)
        for s_ in np.linspace(0, 1, 6):
            ctr = np.array([cx + rng.uniform(-0.1, 0.1), -0.32 - 0.1 * s_, 1.55 - s_ * 1.0])
            p, r, s = scatter_volume(rng, 45, ctr, (0.22, 0.12, 0.18), lower_cut=-1.0)
            P += p; R += r; S += s
            p, r, s = scatter_volume(rng, 35, ctr, (0.24, 0.14, 0.2), normal_bias=0.2, lower_cut=-1.0)
            PF += p; RF += r; SF += s
    H.points_object("FOL_Bougainvillea_Leaves", P, R, S, c, H.instancer("GN_Bougainvillea_Leaves", srcs["leaf_small"]))
    H.points_object("FLW_Bougainvillea_Bracts", PF, RF, SF, c, H.instancer("GN_Bougainvillea_Bracts", srcs["bract"]))
    print("[props] bougainvillea: %d leaves, %d bracts" % (len(P), len(PF)))


def banana(M):
    c = asset("AST_Banana_Plant_A")
    rng = random.Random(4)
    hb = HB()
    hb.frustum(0, 0, -0.1, 2.1, 0.14, 0.09, 12, M["banana_stem"])
    for k in range(3):                                                             # suckers
        a = rng.uniform(0, 6.28)
        hb.frustum(0.45 * math.cos(a), 0.45 * math.sin(a), -0.1, rng.uniform(0.5, 1.0), 0.06, 0.04, 8, M["banana_stem"])
    put(hb, "GEO_Banana_Stem", c, smooth=True)
    hb = HB()
    for k in range(9):
        az = 2 * math.pi * k / 9 * 1.05 + rng.uniform(-0.2, 0.2)
        dry = k in (2, 6)
        el = math.radians(rng.uniform(-35, -15) if dry else rng.uniform(10, 55))
        L = rng.uniform(1.6, 2.2)
        Wd = 0.27
        base = np.array([0.0, 0.0, 2.0 + rng.uniform(-0.1, 0.15)])
        d0 = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        side = nrm(np.cross(d0, UP))
        mat = M["leaf_banana_dry"] if dry else M["leaf_banana"]
        hb.rod(M["banana_stem"], base, base + d0 * 0.45, 0.025, 6)
        st = 14
        v, f = [], []
        for i in range(st + 1):
            s = i / st
            p = base + d0 * (0.45 + s * L) + np.array([0, 0, -0.55 * (s * L) ** 2 / L])
            w = Wd * (math.sin(math.pi * min(1.0, s * 1.1)) ** 0.5) * (1.0 if rng.random() > 0.15 else 0.7)
            droop = 0.12 * w / Wd
            v += [tuple(p - side * w + np.array([0, 0, -droop])), tuple(p + np.array([0, 0, 0.02])),
                  tuple(p + side * w + np.array([0, 0, -droop]))]
        for i in range(st):
            for j in range(2):
                a = i * 3 + j
                f.append((a, a + 1, a + 4, a + 3))
        hb.add(v, f, mat)
    put(hb, "FOL_Banana_Leaves", c, recalc=False, smooth=True)


def hibiscus(M, srcs):
    c = asset("AST_Hibiscus_Bush_A")
    rng = random.Random(6)
    hb = HB()
    for _ in range(6):
        a = rng.uniform(0, 6.28)
        hb.rod(M["bark"], (0, 0, 0), (0.4 * math.cos(a), 0.4 * math.sin(a), rng.uniform(0.6, 1.1)), 0.025, 5)
    put(hb, "GEO_Hibiscus_Stems", c)
    P, R, S = [], [], []
    for ctr, rad in (((0, 0, 0.95), (0.7, 0.65, 0.55)), ((0.35, 0.2, 1.3), (0.4, 0.4, 0.35)), ((-0.3, -0.15, 1.25), (0.4, 0.4, 0.35))):
        p, r, s = scatter_volume(rng, 1100, ctr, rad)
        P += p; R += r; S += s
    H.points_object("FOL_Hibiscus_Leaves", P, R, S, c, H.instancer("GN_Hibiscus_Leaves", srcs["leaf_oval"]))
    P, R, S = scatter_volume(rng, 45, (0, 0, 1.0), (0.75, 0.7, 0.62), normal_bias=0.5, shell=(0.92, 1.03))
    H.points_object("FLW_Hibiscus", P, R, S, c, H.instancer("GN_Hibiscus_Flowers", srcs["hibiscus"]))


def hand_pump(M):
    c = asset("AST_HandPump_A")
    hb = HB()
    hb.box(-0.85, 0.85, -0.85, 0.85, -0.2, 0.18, M["concrete"])
    hb.box(-0.85, 0.85, -0.85, -0.7, 0.18, 0.3, M["concrete"])
    hb.box(-0.85, -0.7, -0.7, 0.85, 0.18, 0.3, M["concrete"])
    hb.box(0.7, 0.85, -0.7, 0.85, 0.18, 0.3, M["concrete"])
    hb.box(-0.85, 0.85, 0.7, 0.85, 0.18, 0.3, M["concrete"])
    hb.box(-0.12, 0.12, -1.6, -0.85, -0.05, 0.05, M["concrete"])                    # drain channel
    hb.box(-0.62, 0.62, -0.62, 0.62, 0.18, 0.2, M["water"])
    hb.frustum(0, 0.25, 0.2, 0.32, 0.17, 0.17, 12, M["pump"])
    hb.frustum(0, 0.25, 0.32, 1.05, 0.085, 0.085, 14, M["pump"])
    hb.frustum(0, 0.25, 1.05, 1.32, 0.13, 0.13, 14, M["pump"])
    hb.frustum(0, 0.25, 1.32, 1.36, 0.15, 0.15, 14, M["pump"])
    hb.rod(M["pump"], (0, 0.18, 0.78), (0, -0.25, 0.7), 0.035, 10)                  # spout
    hb.rod(M["pump"], (0, 0.25, 1.3), (0, 1.25, 1.62), 0.025, 8)                    # handle
    hb.rod(M["iron"], (0, 1.1, 1.57), (0, 1.32, 1.65), 0.03, 8)
    hb.box(-0.05, 0.05, 0.3, 0.4, 1.28, 1.42, M["pump"])
    put(hb, "GEO_HandPump_A", c)


def haystack(M):
    c = asset("AST_Haystack_A")
    hb = HB()
    hb.lathe(M["hay"], [(0.0, -0.05), (1.4, -0.05), (1.55, 0.6), (1.45, 1.3), (1.1, 2.0), (0.6, 2.6), (0.15, 2.95),
                        (0.0, 3.0)], 28)
    hb.frustum(0, 0, 2.7, 3.6, 0.05, 0.035, 6, M["bamboo"])
    put(hb, "GEO_Haystack_A", c, recalc=False, smooth=True)


def drum_bucket(M):
    c = asset("AST_WaterDrum_Bucket_A")
    hb = HB()
    hb.lathe(M["drum"], [(0.0, 0.0), (0.27, 0.0), (0.29, 0.05), (0.29, 0.3), (0.3, 0.33), (0.29, 0.36), (0.29, 0.62),
                         (0.3, 0.65), (0.29, 0.68), (0.29, 0.86), (0.25, 0.9), (0.0, 0.9)], 24)
    hb.lathe(M["steel"], [(0.0, 0.0), (0.12, 0.0), (0.16, 0.3), (0.165, 0.31), (0.15, 0.31)], 20, 0.55, -0.1, 0)
    hb.rod(M["steel"], (0.40, -0.1, 0.31), (0.55, -0.1, 0.45), 0.006, 4)
    hb.rod(M["steel"], (0.55, -0.1, 0.45), (0.70, -0.1, 0.31), 0.006, 4)
    put(hb, "GEO_WaterDrum_Bucket_A", c, recalc=False, smooth=True)


def boundary_wall(M):
    """6 m lime-plastered boundary wall with a tiled coping; origin = base centre, street side -Y."""
    c = asset("AST_BoundaryWall_A")
    hb = HB()
    hb.box(-3.0, 3.0, -0.12, 0.12, -0.3, 1.6, M["plaster"])
    hb.box(-3.08, 3.08, -0.2, 0.2, 1.6, 1.68, M["coping"])
    for x in (-3.0, 0.0, 3.0):
        hb.box(x - 0.2, x + 0.2, -0.2, 0.2, -0.3, 1.85, M["plaster"])
        hb.frustum(x, 0, 1.85, 2.05, 0.25, 0.05, 4, M["coping"], rot=math.pi / 4)
    put(hb, "GEO_BoundaryWall_A", c)


# ---------------------------------------------------------------- tabela
def thatch(hb, mat, origin, A, La, D, Ld, N, rng, course=0.34, overlap=0.22, thick=0.26, dx=0.06):
    """Layered thatch: each course is a thick bundle row with a ragged, uneven lower edge and lumpy top."""
    xs = np.arange(0.0, La + 1e-6, dx)
    n = len(xs)
    s0 = 0.0
    sl = hb._slot(mat)
    while s0 < Ld - 1e-3:
        s1 = min(s0 + course + overlap, Ld)
        rag = np.array([rng.uniform(0.0, 0.2) for _ in xs])
        rag = np.convolve(rag, np.ones(3) / 3, mode="same")
        lump = np.array([rng.uniform(-0.025, 0.025) for _ in xs])
        wave = 0.03 * np.sin(xs * 9.0 + rng.uniform(0, 6.28))
        rows = []
        for s, off in ((s0 - rag, 0.05 - thick), (s0 - rag * 0.7, 0.05 + lump + wave), (s0 + (s1 - s0) * 0.5, 0.025 + lump * 0.5),
                       (np.full(n, s1), 0.0)):
            s = np.broadcast_to(s, (n,))
            off = np.broadcast_to(off, (n,))
            rows.append(origin + np.outer(xs, A) + np.outer(s, D) + np.outer(off, N))
        base = len(hb.v)
        for r in rows:
            hb.v.extend(map(tuple, r.tolist()))
        for k in range(len(rows) - 1):
            for i in range(n - 1):
                a = base + k * n + i
                hb.f.append((a, a + 1, a + n + 1, a + n))
                hb.mi.append(sl)
        s0 += course


def tabela(M):
    """Cattle shed 9 x 6 m.  Open front (-Y), mud back + side walls, lean-to thatch, trough, pegs,
    fodder, dung-cake wall + bitaura stack, chaff cutter.  No animals (Phase 6)."""
    c = asset("AST_Tabela_A")
    rng = random.Random(21)
    hb = HB()
    W, D = 9.0, 6.0
    hb.box(-W / 2 - 0.3, W / 2 + 0.3, -D / 2 - 0.3, D / 2 + 0.3, -0.4, 0.22, M["mud_floor"])
    hb.box(-W / 2, W / 2, D / 2 - 0.35, D / 2, 0.22, 2.25, M["mud"])                # back wall
    for sx in (-1, 1):                                                              # side walls, stepped down
        x0, x1 = (-W / 2, -W / 2 + 0.35) if sx < 0 else (W / 2 - 0.35, W / 2)
        hb.box(x0, x1, -0.2, D / 2 - 0.35, 0.22, 1.5, M["mud"])
    posts = [-4.3, -1.45, 1.45, 4.3]
    for x in posts:                                                                  # forked log posts
        lean = rng.uniform(-0.04, 0.04)
        top = np.array([x + lean, -D / 2 + 0.25, 2.35])
        hb.rod(M["wood"], (x, -D / 2 + 0.25, 0.0), top, 0.11, 9)
        for s in (-1, 1):
            hb.rod(M["wood"], top, top + np.array([s * 0.18, 0, 0.28]), 0.055, 6)
    hb.rod(M["wood"], (-W / 2 - 0.4, -D / 2 + 0.25, 2.5), (W / 2 + 0.4, -D / 2 + 0.25, 2.5), 0.1, 9)     # front beam
    hb.rod(M["wood"], (-W / 2 - 0.4, D / 2 - 0.15, 2.32), (W / 2 + 0.4, D / 2 - 0.15, 2.32), 0.09, 9)    # wall plate
    z_back, z_front = 3.45, 2.55
    y_back, y_front = D / 2 + 0.5, -D / 2 - 0.65
    k = (z_back - z_front) / (y_back - y_front)
    for x in np.arange(-W / 2 - 0.3, W / 2 + 0.31, 0.6):                            # bamboo rafters
        hb.rod(M["bamboo"], (x, y_front + 0.1, z_front - 0.1), (x, y_back - 0.05, z_back - 0.1), 0.035, 6)
    # trough (naad) along the back wall
    hb.box(-3.4, 3.4, D / 2 - 1.15, D / 2 - 0.35, 0.22, 0.75, M["concrete"])
    hb.box(-3.25, 3.25, D / 2 - 1.02, D / 2 - 0.48, 0.5, 0.76, M["hay"])
    for x in (-2.4, -0.8, 0.8, 2.4):                                                # khoonte + rope loops
        hb.frustum(x, D / 2 - 1.7, 0.1, 0.62, 0.06, 0.045, 7, M["wood_dark"])
        for i in range(8):
            a0, a1 = 2 * math.pi * i / 8, 2 * math.pi * (i + 1) / 8
            hb.rod(M["rope"], (x + 0.09 * math.cos(a0), D / 2 - 1.7 + 0.09 * math.sin(a0), 0.5),
                   (x + 0.09 * math.cos(a1), D / 2 - 1.7 + 0.09 * math.sin(a1), 0.5), 0.012, 4)
    put(hb, "GEO_Tabela_Structure", c)
    # thatch roof (slope along Y so the straw streaks run downhill)
    hb = HB()
    Dv = np.array([0.0, y_back - y_front, z_back - z_front])
    Ld = float(np.linalg.norm(Dv))
    Dv = Dv / Ld
    Nv = np.array([0.0, -Dv[2], Dv[1]])
    thatch(hb, M["straw"], np.array([-W / 2 - 0.55, y_front, z_front]), np.array([1.0, 0, 0]), W + 1.1, Dv, Ld, Nv, rng)
    # ragged straw fringe along the front eave
    fr = random.Random(5)
    for x in np.arange(-W / 2 - 0.5, W / 2 + 0.5, 0.05):
        L = fr.uniform(0.12, 0.3)
        p = np.array([x, y_front + 0.02, z_front + 0.02])
        hb.add([tuple(p), tuple(p + np.array([0.035, 0, 0])), tuple(p + np.array([0.015, -0.08 * L, -L]))], [(0, 1, 2), (2, 1, 0)], M["straw"])
    put(hb, "GEO_Tabela_Thatch", c, recalc=False)
    # fodder pile, hay bundles, dung cakes (uple) on the outside wall + bitaura stack, chaff cutter
    soft = HB()
    soft.ellipsoid(W / 2 + 1.6, 0.6, 0.35, 1.3, 1.0, 0.85, M["hay"], 24, 14)
    put(soft, "PRP_Tabela_FodderPile", c, smooth=True)
    hb = HB()
    for i in range(5):
        x = -W / 2 + 0.8 + i * 0.5
        hb.frustum(x, -1.0, 0.22, 1.0 + 0.05 * (i % 2), 0.2, 0.17, 10, M["hay"])
        hb.frustum(x, -1.0, 0.55, 0.62, 0.205, 0.205, 10, M["rope"])
    for i in range(4):
        for j in range(6):
            y = -0.05 + j * 0.42 + (0.2 if i % 2 else 0)
            if y > D / 2 - 0.5:
                continue
            z = 0.5 + i * 0.3
            hb.frustum(-W / 2 - 0.02, y, z, z + 0.001, 0.13, 0.13, 10, M["dung"])
            hb.ellipsoid(-W / 2 - 0.035, y, z, 0.03, 0.13, 0.12, M["dung"], 10, 5)
    bx, by = -W / 2 - 1.8, 1.4                                                      # bitaura
    hb.lathe(M["mud"], [(0.0, -0.05), (1.0, -0.05), (1.05, 0.5), (0.85, 1.3), (0.45, 2.0), (0.1, 2.35), (0.0, 2.4)], 24, bx, by, 0)
    for i in range(40):
        a = rng.uniform(0, 6.28)
        zz = rng.uniform(0.2, 1.9)
        rr = 1.05 - zz * 0.43
        hb.ellipsoid(bx + rr * math.cos(a), by + rr * math.sin(a), zz, 0.12, 0.12, 0.04, M["dung"], 8, 4)
    cx, cy = W / 2 + 0.9, -D / 2 - 1.2                                              # chaff cutter
    for dx in (-0.35, 0.35):
        for dy in (-0.25, 0.25):
            hb.rod(M["wood_dark"], (cx + dx, cy + dy, 0.0), (cx + dx * 0.8, cy + dy * 0.8, 0.85), 0.04, 6)
    hb.box(cx - 0.35, cx + 0.35, cy - 0.28, cy + 0.28, 0.82, 0.98, M["wood_dark"])
    hb.box(cx - 0.9, cx + 0.3, cy - 0.12, cy + 0.12, 0.98, 1.2, M["wood_dark"])
    wr, wc = 0.55, np.array([cx + 0.42, cy, 1.1])
    for i in range(24):
        a0, a1 = 2 * math.pi * i / 24, 2 * math.pi * (i + 1) / 24
        hb.rod(M["iron"], wc + np.array([0, wr * math.cos(a0), wr * math.sin(a0)]),
               wc + np.array([0, wr * math.cos(a1), wr * math.sin(a1)]), 0.03, 6)
    for i in range(6):
        a = 2 * math.pi * i / 6
        hb.rod(M["iron"], wc, wc + np.array([0, wr * math.cos(a), wr * math.sin(a)]), 0.015, 5)
    hb.rod(M["wood_dark"], wc + np.array([0, wr * 0.8, 0]), wc + np.array([0.25, wr * 0.8, 0]), 0.03, 6)
    hb.rod(M["rope"], (-1.45, -D / 2 + 0.25, 2.4), (-1.45, -D / 2 + 0.25, 1.9), 0.01, 4)  # hanging lantern hook
    put(hb, "PRP_Tabela_Details", c)
    print("[props] tabela built")


# ============================================================================
def leaf_sources(M):
    s = {}
    hb = HB(); blade(hb, M["leaf_tulsi"], 0.05, 0.016, 0.3, 0.3); s["tulsi"] = src_obj("Leaf_Tulsi", hb)
    hb = HB(); blade(hb, M["leaf_dark"], 0.07, 0.02); s["marigold_leaf"] = src_obj("Leaf_Marigold", hb)
    hb = HB(); blade(hb, M["leaf_money"], 0.09, 0.04, 0.15, 0.15, 0.55); s["money"] = src_obj("Leaf_Money", hb)
    hb = HB(); blade(hb, M["leaf_bougain"], 0.06, 0.022); s["leaf_small"] = src_obj("Leaf_Bougainvillea", hb)
    hb = HB(); bloom(hb, M["bract"], 0.035, 3, 0.4); s["bract"] = src_obj("Bract_Bougainvillea", hb)
    hb = HB()                                       # marigold: ruffled pompom of small petals, not a ball
    hb.ellipsoid(0, 0, 0.005, 0.014, 0.014, 0.012, M["marigold"], 8, 5)
    for layer, (r, n, cup, z) in enumerate(((0.032, 13, 0.15, 0.0), (0.026, 11, 0.5, 0.008), (0.019, 9, 0.9, 0.015))):
        sub = HB()
        bloom(sub, M["marigold"], r, n, cup)
        hb.merge(sub, Matrix.Translation((0, 0, z)) @ Matrix.Rotation(layer * 0.4, 4, "Z"))
    s["marigold"] = src_obj("Flower_Marigold", hb)
    hb = HB(); blade(hb, M["leaf_dark"], 0.1, 0.04, 0.15, 0.15, 0.6); s["leaf_oval"] = src_obj("Leaf_Oval", hb)
    hb = HB(); bloom(hb, M["hibiscus"], 0.07, 5, 0.5); s["hibiscus"] = src_obj("Flower_Hibiscus", hb)
    return s


# ============================================================================
def build_stage(M):
    stage = bpy.data.collections.new("STAGE")
    bpy.context.scene.collection.children.link(stage)

    def inst(coll, name, loc, rz=0.0, s=1.0):
        e = bpy.data.objects.new(name, None)
        e.instance_type = "COLLECTION"
        e.instance_collection = coll
        e.location = loc
        e.rotation_euler = (0, 0, rz)
        e.scale = (s, s, s)
        stage.objects.link(e)
        return e

    lib = {c.name: c for c in bpy.data.collections}
    # ground: dirt street with ruts + yards
    road = H.NT(bpy.data.materials.new("MAT_Road_Dirt_Ruts"))
    mroad = bpy.data.materials["MAT_Road_Dirt_Ruts"]
    tc = road.n("ShaderNodeTexCoord")
    sxyz = road.n("ShaderNodeSeparateXYZ", Vector=tc.outputs["Object"])
    n = road.noise(tc.outputs["Object"], 2.5, 6.0, 0.6)
    col = road.ramp(n.outputs["Fac"], [(0.3, H.hex_lin("#9C8160")), (0.7, H.hex_lin("#B89C76"))])
    rut = road.math("ADD", road.math("MULTIPLY", road.math("COMPARE", sxyz.outputs["Y"], -12.6, 0.28), 1.0),
                    road.math("COMPARE", sxyz.outputs["Y"], -9.6, 0.28))
    col = road.mix(road.math("MULTIPLY", rut, 0.55), col, H.hex_lin("#6E583F"))
    fine = road.noise(tc.outputs["Object"], 14.0, 8.0, 0.7)
    road.finish(col, 0.95, road.bump(road.math("ADD", fine.outputs["Fac"], road.math("MULTIPLY", rut, -0.4)), 0.5, 0.03))
    hb = HB()
    hb.add([(-60, -14.5, 0.0), (60, -14.5, 0.0), (60, -7.8, 0.0), (-60, -7.8, 0.0)], [(0, 1, 2, 3)], mroad)
    gm = H.mat_ground()
    hb.add([(-200, -200, -0.02), (200, -200, -0.02), (200, 200, -0.02), (-200, 200, -0.02)], [(0, 1, 2, 3)], gm)
    put(hb, "STG_Ground_Street", stage, recalc=False)

    # linked hero house x2 + trees
    if os.path.exists(HOUSE_BLEND):
        with bpy.data.libraries.load(HOUSE_BLEND, link=True) as (src, dst):
            dst.collections = [c for c in src.collections if c == "AST_House_Common_A"]
        house = dst.collections[0]
        inst(house, "STG_House_A", (0, 0, 0))
        inst(house, "STG_House_B", (22.5, 0.6, 0), rz=0.03)
        inst(house, "STG_House_C", (6.0, -23.2, 0), rz=math.pi)            # across the street, facing it
    if os.path.exists(TREES_BLEND):
        want = ["VEG_Tree_Neem_A", "VEG_Tree_Mango_A", "VEG_Tree_Amaltas_A", "VEG_Tree_Palm_A", "VEG_Tree_Peepal_A_LOD1"]
        with bpy.data.libraries.load(TREES_BLEND, link=True) as (src, dst):
            dst.collections = [c for c in src.collections if c in want]
        T = {c.name: c for c in dst.collections}
        inst(T["VEG_Tree_Neem_A"], "STG_Tree_Neem", (-8.0, 7.0, 0), 0.6)
        inst(T["VEG_Tree_Amaltas_A"], "STG_Tree_Amaltas", (11.5, -4.0, 0), 1.2, 0.85)
        inst(T["VEG_Tree_Mango_A"], "STG_Tree_Mango", (34.0, 8.0, 0), 2.0)
        inst(T["VEG_Tree_Palm_A"], "STG_Tree_Palm", (-30.0, -2.0, 0), 0.3)
        inst(T["VEG_Tree_Peepal_A_LOD1"], "STG_Tree_Peepal", (10.0, -25.0, 0), 0.9)

    inst(lib["AST_Tabela_A"], "STG_Tabela", (-17.5, 1.0, 0), 0.0)
    inst(lib["AST_BoundaryWall_A"], "STG_Wall_1", (11.2, -7.0, 0))
    inst(lib["AST_BoundaryWall_A"], "STG_Wall_2", (33.2, -6.6, 0))
    inst(lib["AST_BoundaryWall_A"], "STG_Wall_3", (-6.0, -15.6, 0), math.pi)
    inst(lib["AST_BoundaryWall_A"], "STG_Wall_4", (18.0, -15.6, 0), math.pi)
    inst(lib["AST_Bougainvillea_Wall_A"], "STG_Bougainvillea_2", (18.5, -15.6, 0), math.pi, 0.9)
    inst(lib["AST_Bougainvillea_Wall_A"], "STG_Bougainvillea", (11.0, -7.0, 0))
    inst(lib["AST_StreetLight_Pole_A"], "STG_StreetLight_1", (4.0, -15.3, 0), math.pi)
    inst(lib["AST_StreetLight_Pole_A"], "STG_StreetLight_2", (-26.0, -15.3, 0), math.pi)
    inst(lib["AST_LampPost_Lantern_A"], "STG_LampPost_1", (-5.6, -7.4, 0))
    inst(lib["AST_LampPost_Lantern_A"], "STG_LampPost_2", (16.0, -7.4, 0))
    inst(lib["AST_WallLantern_A"], "STG_WallLantern_House", (-1.0, -1.95, 2.55))
    inst(lib["AST_HandPump_A"], "STG_HandPump", (-9.2, -9.2, 0), 0.4)
    inst(lib["AST_Haystack_A"], "STG_Haystack", (-24.5, 6.0, 0))
    inst(lib["AST_WaterDrum_Bucket_A"], "STG_Drum", (-6.4, -2.2, 0.5))
    inst(lib["AST_Banana_Plant_A"], "STG_Banana_1", (-6.8, 2.0, 0), 0.4)
    inst(lib["AST_Banana_Plant_A"], "STG_Banana_2", (29.0, -3.0, 0), 2.1, 0.9)
    inst(lib["AST_Hibiscus_Bush_A"], "STG_Hibiscus", (6.6, -6.2, 0), 0.0, 0.9)
    inst(lib["AST_Planter_Tulsi_A"], "STG_Pot_1", (-2.0, -4.2, 0.53), 0.0)
    inst(lib["AST_Planter_Marigold_A"], "STG_Pot_2", (-3.6, -4.3, 0.53), 1.0)
    inst(lib["AST_Planter_MoneyPlant_A"], "STG_Pot_3", (3.9, -4.3, 0.53), 2.0)
    inst(lib["AST_Planter_Marigold_A"], "STG_Pot_4", (1.6, -4.4, 0.53), 0.5, 0.9)
    inst(lib["AST_Planter_Marigold_A"], "STG_Pot_5", (20.0, -4.4, 0.53), 0.3)
    inst(lib["AST_Planter_Tulsi_A"], "STG_Pot_6", (25.4, -4.3, 0.53), 0.3)

    sc = bpy.context.scene
    w = bpy.data.worlds.new("WLD_Review")
    sc.world = w
    t = H.NT(w)
    tc = t.n("ShaderNodeTexCoord")
    z = t.n("ShaderNodeSeparateXYZ", Vector=tc.outputs["Generated"]).outputs["Z"]
    ramp = t.ramp(z, [(0.0, H.hex_lin("#F2DCB8")), (0.12, H.hex_lin("#B9D2E6")), (0.45, H.hex_lin("#5E93CC"))])
    bg = t.n("ShaderNodeBackground", Color=ramp, Strength=1.0)
    t.link(bg.outputs[0], t.n("ShaderNodeOutputWorld").inputs["Surface"])
    sd = bpy.data.lights.new("LGT_Sun", "SUN")
    sun = bpy.data.objects.new("LGT_Sun", sd)
    stage.objects.link(sun)
    cams = {
        "CAM_Street_Day":      ((-24.0, -12.2, 1.65), (20.0, -5.5, 2.6), 26, None),
        "CAM_Street_Dusk":     ((-24.0, -12.2, 1.65), (20.0, -5.5, 2.6), 26, None),
        "CAM_Tabela":          ((-9.0, -10.5, 1.7), (-17.5, 1.0, 1.6), 28, None),
        "CAM_Bougainvillea":   ((7.0, -12.5, 1.6), (11.0, -7.0, 1.6), 35, 6.6),
        "CAM_Veranda_Props":   ((-3.0, -9.0, 1.4), (-1.5, -3.8, 1.0), 32, 5.3),
    }
    for name, (pos, tgt, lens, focus) in cams.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 3000
        if focus:
            cd.dof.use_dof = True
            cd.dof.focus_distance = focus
            cd.dof.aperture_fstop = 3.5
        co = bpy.data.objects.new(name, cd)
        co.location = pos
        co.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        stage.objects.link(co)
    return cams, sun, sd, ramp, bg


def set_light(mode, sun, sd, ramp_out, bg):
    els = ramp_out.node.color_ramp.elements
    if mode == "dusk":
        sd.energy, sd.color, sd.angle = 2.2, (1.0, 0.55, 0.28), math.radians(3)
        sun.rotation_euler = (math.radians(84), 0.0, math.radians(-115))
        els[0].color = H.hex_lin("#F0A060")
        els[1].color = H.hex_lin("#8F7FA8")
        els[2].color = H.hex_lin("#2E3F6E")
        bg.inputs["Strength"].default_value = 0.6
        glow = 45.0
    else:
        sd.energy, sd.color, sd.angle = 4.5, (1.0, 0.9, 0.77), math.radians(1.5)
        sun.rotation_euler = (math.radians(52), 0.0, math.radians(-38))
        els[0].color = H.hex_lin("#F2DCB8")
        els[1].color = H.hex_lin("#B9D2E6")
        els[2].color = H.hex_lin("#5E93CC")
        bg.inputs["Strength"].default_value = 1.0
        glow = 0.0
    m = bpy.data.materials["MAT_Lamp_Glow"]
    for nd in m.node_tree.nodes:
        if nd.type == "BSDF_PRINCIPLED":
            H.NT.inp(nd, "Emission Strength").default_value = glow
    for ld in LAMP_LIGHTS:
        ld.energy = ld["energy_dusk"] * 3.0 if mode == "dusk" else 0.0


def main():
    global LIB, SRC
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "LIB_Village_Props"
    sc.unit_settings.system = "METRIC"
    LIB = bpy.data.collections.new("LIB_PROPS")
    sc.collection.children.link(LIB)
    SRC = bpy.data.collections.new("SRC_PROPS")
    sc.collection.children.link(SRC)
    bpy.context.view_layer.layer_collection.children["SRC_PROPS"].exclude = True
    M = materials()
    S = leaf_sources(M)
    street_light(M)
    lamp_post(M)
    wall_lantern(M)
    planter(M, "AST_Planter_Tulsi_A", POT_A, M["pot_white"], S["tulsi"], M["leaf_tulsi"], 900, (0.2, 0.2, 0.22), seed=1)
    planter(M, "AST_Planter_Marigold_A", POT_B, M["terracotta"], S["marigold_leaf"], M["leaf_dark"], 700,
            (0.26, 0.26, 0.2), flowers=(S["marigold"], 42), seed=2)
    planter(M, "AST_Planter_MoneyPlant_A", POT_A, M["terracotta"], S["money"], M["leaf_money"], 260,
            (0.22, 0.22, 0.16), trailing=True, seed=3)
    bougainvillea(M, S)
    banana(M)
    hibiscus(M, S)
    hand_pump(M)
    haystack(M)
    drum_bucket(M)
    boundary_wall(M)
    tabela(M)
    for ch in LIB.children:
        bpy.context.view_layer.layer_collection.children["LIB_PROPS"].children[ch.name].exclude = True
    cams, sun, sd, ramp, bg = build_stage(M)
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception as ex:
        print("[props] GPU setup failed:", ex)
    quick = "--quick" in ARGS
    sc.cycles.samples = 64 if quick else 256
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = (1280, 720) if quick else (1920, 1080)
    set_light("day", sun, sd, ramp, bg)
    sc.camera = bpy.data.objects["CAM_Street_Day"]
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_Village_Props_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[props] saved", OUT_BLEND)
    if "--render" in ARGS:
        os.makedirs(OUT_REVIEW, exist_ok=True)
        only = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None
        for c in cams:
            if only and c != only:
                continue
            set_light("dusk" if "Dusk" in c else "day", sun, sd, ramp, bg)
            sc.camera = bpy.data.objects[c]
            sc.render.filepath = os.path.join(OUT_REVIEW, c + ".png")
            bpy.ops.render.render(write_still=True)
            print("[props] rendered", c)


main()
