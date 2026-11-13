"""
HERO FARM PROPS + GROUND COVER (Amaltaspur)

  blender -b --factory-startup --python hero_farm.py -- [--render] [--quick] [--only CAM]

Output: 06_PROPS/LIB_Farm_Props.blend
  AST_Machaan_A            raised bamboo crop-watch platform with a thatch hood and ladder
  AST_Tubewell_A           brick pump room, tin roof, delivery pipe gushing into a hauz + irrigation channel, LT pole
  AST_Scarecrow_A          pot-head scarecrow (bijookha) in an old kurta with straw cuffs
  AST_Shrub_Lantana_A      1.1 m flowering hedge shrub        (field edges, road verges)
  AST_Shrub_Dense_A        1.6 m dark evergreen bush (karonda) (bunds, compound edges)
  AST_Shrub_Dry_A          1.0 m sparse grey-green scrub (ber/aak) (dry ground, mountain foot)
  AST_GrassTuft_A          0.3-0.45 m green tuft               (mass scatter)
  AST_GrassTuft_Dry_A      0.3-0.5 m straw tuft                (mass scatter)
  AST_GrassClump_Tall_A    kans grass with cream plumes, 1-1.9 m (river banks, bunds)
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
import master_materials as MM  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "06_PROPS", "LIB_Farm_Props.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "PH1C_FARM_PROPS_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UP = np.array([0.0, 0.0, 1.0])
LIB = None
SRC = None


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


def bloom(hb, mat, r, petals=5, cup=0.35):
    for k in range(petals):
        blade(hb, mat, r, r * 0.45, curve=-cup, fold=0.1, prof=0.6, rotz=2 * math.pi * k / petals)


def src_obj(name, hb):
    o = bpy.data.objects.new("SRC_" + name, hb.to_mesh("ME_SRC_" + name, recalc=False))
    SRC.objects.link(o)
    return o


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


def blade_clump(hb, mat, n, hmin, hmax, rng, spread=0.12, lean=(0.15, 0.55), width=1.0):
    tips = []
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        ln = rng.uniform(*lean)
        h = rng.uniform(hmin, hmax)
        w = (0.012 + 0.01 * h) * width
        d = np.array([math.cos(a), math.sin(a), 0.0])
        side = np.array([-d[1], d[0], 0.0])
        base = d * rng.uniform(0, spread)
        pts = [base + d * ln * h * (t * t) + np.array([0, 0, h * t]) for t in (0, 0.35, 0.7, 1.0)]
        v = []
        for j, p in enumerate(pts):
            ww = w * (1 - j / 3.0) + 0.001
            v += [tuple(p - side * ww), tuple(p + side * ww)]
        hb.add(v, [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6)], mat)
        tips.append((pts[-1], nrm(pts[-1] - pts[-2])))
    return tips


def thatch(hb, mat, origin, A, La, D, Ld, N, rng, course=0.3, overlap=0.2, thick=0.2, dx=0.06):
    """Layered thatch courses with a ragged lower edge (same construction as the approved tabela)."""
    xs = np.arange(0.0, La + 1e-6, dx)
    n = len(xs)
    s0 = 0.0
    sl = hb._slot(mat)
    while s0 < Ld - 1e-3:
        s1 = min(s0 + course + overlap, Ld)
        rag = np.array([rng.uniform(0.0, 0.18) for _ in xs])
        rag = np.convolve(rag, np.ones(3) / 3, mode="same")
        lump = np.array([rng.uniform(-0.02, 0.02) for _ in xs])
        rows = []
        for s, off in ((s0 - rag, 0.05 - thick), (s0 - rag * 0.7, 0.05 + lump), (s0 + (s1 - s0) * 0.5, 0.025 + lump * 0.5),
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


# ============================================================================
def materials():
    return {
        "wood": H.mat_wood(),
        "wood_dark": H.mat_wood("MAT_Wood_Dark_Aged", "#3E2A1C", "#5A3E29"),
        "bamboo": H.mat_simple("MAT_Bamboo_Pole", "#B59A62", 0.6, noise=0.2),
        "bamboo_old": H.mat_simple("MAT_Bamboo_Pole_Weathered", "#8F7E5E", 0.75, noise=0.25),
        "straw": H.mat_straw(),
        "rope": H.mat_rope(),
        "brick": H.mat_stone_blocks("MAT_Brick_Exposed_Red", "#94492F", "#AD5C3C", "#B9AC96", 3.4, 0.5, 0.25, 0.9),
        "concrete": H.mat_simple("MAT_Concrete_Weathered", "#A39C90", 0.85, noise=0.18),
        "tin": H.mat_tin(),
        "door": H.mat_painted("MAT_Metal_Door_Green", "#3E6B4E", "#5A5248", 0.7),
        "galv": H.mat_simple("MAT_Metal_Galvanised", "#8D9396", 0.38, 0.75, noise=0.08),
        "iron": H.mat_simple("MAT_Metal_CastIron_Black", "#1F1F1F", 0.42, 0.65),
        "water": H.mat_simple("MAT_Water_Still", "#3C6E68", 0.05),
        "gush": H.mat_simple("MAT_Water_Gush_Foam", "#D7E6E4", 0.15),
        "terracotta": H.mat_simple("MAT_Clay_Pot_Terracotta", "#A45A3C", 0.6, noise=0.14),
        "pot_white": H.mat_plaster("MAT_Pot_Limewashed", "#E9DFCB", band="#B5492C", band_top=0.12),
        "black": H.mat_simple("MAT_Paint_Black", "#141210", 0.5),
        "kurta": H.mat_simple("MAT_Cloth_Kurta_Faded", "#C7B48C", 0.85, noise=0.2),
        "red_cloth": H.mat_simple("MAT_Cloth_Red", "#A8302A", 0.8, noise=0.15),
        "saffron": H.mat_simple("MAT_Cloth_Saffron", "#E3722A", 0.7, noise=0.1),
        "bark": H.mat_wood("MAT_Bark_Woody_Stem", "#4A3829", "#6A543F", 0.9),
        "leaf_lantana": H.mat_leaf("MAT_Leaf_Lantana", ("#2F5A24", "#41702D", "#5A8436")),
        "leaf_dense": H.mat_leaf("MAT_Leaf_Karonda", ("#23461C", "#2F5824", "#3E6A2C"), rough=0.4),
        "leaf_dry": H.mat_leaf("MAT_Leaf_Scrub_GreyGreen", ("#6E7A4E", "#87916A", "#9C9E78")),
        "flower_lantana": H.mat_leaf("MAT_Flower_Lantana", ("#E2552B", "#F0A030", "#E8649A"), transl=0.3),
        "grass": H.mat_simple("MAT_Foliage_GrassTuft", "#7C9444", 0.6, noise=0.3),
        "grass_dry": H.mat_simple("MAT_Foliage_GrassTuft_Dry", "#B49A5E", 0.7, noise=0.3),
        "kans": H.mat_simple("MAT_Foliage_Kans_Blade", "#8C9A55", 0.6, noise=0.25),
        "plume": H.mat_leaf("MAT_Foliage_Kans_Plume", ("#E6DCC4", "#F1EBDB", "#D9CDB0"), transl=0.45, rough=0.7),
    }


# ============================================================================
def machaan(M):
    """2.2 x 2.2 m crop-watch platform at 2.45 m, thatch hood, bamboo ladder on the -Y side."""
    c = asset("AST_Machaan_A")
    rng = random.Random(31)
    hb = HB()
    Z = 2.45
    legs = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            b = np.array([sx * 1.08, sy * 1.08, -0.35])
            t = np.array([sx * 0.98 + rng.uniform(-0.03, 0.03), sy * 0.98, Z + 1.55])
            hb.rod(M["wood"], b, t, 0.075, 9)
            legs.append((b, t))
    for (i, j) in ((0, 1), (2, 3), (0, 2), (1, 3)):                                  # X-braces
        (b0, t0), (b1, t1) = legs[i], legs[j]
        for f0, f1 in ((0.2, 0.8), (0.8, 0.2)):
            p0 = b0 + (t0 - b0) * f0 * 0.62
            p1 = b1 + (t1 - b1) * f1 * 0.62
            hb.rod(M["bamboo_old"], p0, p1, 0.035, 6)
    for y in (-1.0, 1.0):                                                            # platform bearers
        hb.rod(M["bamboo"], (-1.25, y, Z - 0.05), (1.25, y, Z - 0.05), 0.06, 8)
    for x in np.arange(-1.12, 1.13, 0.105):                                          # slats
        hb.rod(M["bamboo"], (x + rng.uniform(-0.01, 0.01), -1.18, Z + 0.03), (x, 1.18, Z + 0.03 + rng.uniform(-0.02, 0.02)), 0.045, 6)
    for (a, b) in (((-1.0, -1.0), (-1.0, 1.0)), ((1.0, -1.0), (1.0, 1.0)), ((-1.0, 1.0), (1.0, 1.0))):   # railing
        for z in (Z + 0.45, Z + 0.85):
            hb.rod(M["bamboo_old"], (a[0], a[1], z), (b[0], b[1], z), 0.03, 6)
    for k in range(9):                                                               # rope lashings at the joints
        x, y = (-1, 1, -1, 1, -1, 1, 0, -1, 1)[k], (-1, -1, 1, 1, 0, 0, 1, -1, 1)[k]
        hb.frustum(x * 1.0, y * 1.0, Z - 0.12, Z + 0.05, 0.085, 0.085, 8, M["rope"])
    # ladder
    for x in (-0.24, 0.24):
        hb.rod(M["bamboo"], (x, -2.05, -0.1), (x * 0.9, -1.12, Z + 0.4), 0.04, 6)
    for k in range(1, 9):
        f = k / 9.0
        y = -2.05 + (0.93) * f
        z = -0.1 + (Z + 0.5) * f
        hb.rod(M["bamboo_old"], (-0.26, y, z), (0.26, y, z), 0.025, 5)
    # props on the platform: matka, folded red cloth, rattle stick
    hb.lathe(M["terracotta"], [(0.0, 0.0), (0.12, 0.0), (0.2, 0.12), (0.19, 0.25), (0.09, 0.34), (0.08, 0.38), (0.1, 0.4)], 18,
             0.65, 0.6, Z + 0.07)
    hb.box(-0.8, -0.2, 0.3, 0.75, Z + 0.07, Z + 0.15, M["red_cloth"])
    hb.rod(M["bamboo_old"], (0.2, -0.7, Z + 0.1), (0.9, 0.4, Z + 0.95), 0.02, 5)
    put(hb, "GEO_Machaan_Structure", c)
    # thatch hood: gable along X
    hb = HB()
    ridge_z, eave_z = Z + 2.35, Z + 1.45
    for sy in (-1, 1):
        y_eave = sy * 1.45
        Dv = np.array([0.0, -y_eave, ridge_z - eave_z])
        Ld = float(np.linalg.norm(Dv))
        Dv /= Ld
        A = np.array([1.0, 0.0, 0.0])
        Nv = nrm(np.cross(A, Dv)) * (1 if sy > 0 else -1)
        if Nv[2] < 0:
            Nv = -Nv
        thatch(hb, M["straw"], np.array([-1.45, y_eave, eave_z]), A, 2.9, Dv, Ld, Nv, rng)
    hb.rod(M["bamboo"], (-1.5, 0.0, ridge_z + 0.02), (1.5, 0.0, ridge_z + 0.02), 0.05, 6)
    for x in np.arange(-1.45, 1.46, 0.04):                                           # ragged eave fringe
        for sy in (-1, 1):
            L = rng.uniform(0.08, 0.24)
            p = np.array([x, sy * 1.47, eave_z - 0.03])
            hb.add([tuple(p), tuple(p + np.array([0.03, 0, 0])), tuple(p + np.array([0.012, sy * 0.05 * L, -L]))],
                   [(0, 1, 2), (2, 1, 0)], M["straw"])
    put(hb, "GEO_Machaan_Thatch", c, recalc=False)
    print("[farm] machaan")


def tubewell(M):
    """Pump room 2.6 x 2.2 m (centre at y=+1.2), door on -Y, hauz in front, channel running to -Y."""
    c = asset("AST_Tubewell_A")
    rng = random.Random(41)
    hb = HB()
    hb.box(-1.6, 1.6, -0.1, 2.6, -0.3, 0.15, M["concrete"])                          # plinth
    x0, x1, y0, y1, h = -1.3, 1.3, 0.1, 2.3, 2.35
    t = 0.23
    hb.box(x0 + t, x1 - t, y0, y0 + t, 0.15, h, M["brick"])                         # walls butt, never overlap
    hb.box(x0 + t, x1 - t, y1 - t, y1, 0.15, h + 0.25, M["brick"])
    hb.box(x0, x0 + t, y0, y1, 0.15, h + 0.25, M["brick"])
    hb.box(x1 - t, x1, y0, y1, 0.15, h + 0.25, M["brick"])
    hb.box(-0.48, 0.08, y0 - 0.03, y0 - 0.005, 0.18, 1.95, M["door"])                 # door leaf
    hb.box(-0.52, 0.12, y0 - 0.05, y0 - 0.005, 1.95, 2.02, M["concrete"])                    # lintel
    hb.box(0.55, 0.95, y0 - 0.02, y0 - 0.005, 1.45, 1.75, M["iron"])                  # vent grille
    for k in range(5):
        hb.box(0.56, 0.94, y0 - 0.05, y0 - 0.02, 1.47 + k * 0.06, 1.49 + k * 0.06, M["galv"])
    hb.slope_slab(x0 - 0.3, x1 + 0.3, y0 - 0.35, y1 + 0.3, h + 0.05, h + 0.32, 0.03, M["tin"])   # tin roof
    for k in range(4):                                                               # stones holding the sheets down
        hb.ellipsoid(rng.uniform(-1.2, 1.2), rng.uniform(0.3, 2.1), h + 0.32, 0.14, 0.12, 0.08, M["concrete"], 8, 5)
    # starter box + cable on the side wall
    hb.box(x1 + 0.005, x1 + 0.12, 1.0, 1.4, 1.2, 1.6, M["galv"])
    hb.rod(M["black"], (x1 + 0.06, 1.2, 1.6), (x1 + 0.06, 1.2, h + 0.1), 0.012, 5)
    # delivery pipe through the front wall, elbow down into the hauz
    hb.rod(M["galv"], (0.7, y0 + 0.3, 0.75), (0.7, -0.75, 0.75), 0.085, 12)
    hb.frustum(0.7, -0.75, 0.62, 0.88, 0.1, 0.1, 12, M["galv"], 0)
    # hauz (cistern)
    cx0, cx1, cy0, cy1, ch = -0.6, 1.9, -2.4, -0.2, 0.62
    hb.box(cx0, cx1, cy0, cy1, -0.2, 0.05, M["concrete"])
    hb.box(cx0 + 0.15, cx1 - 0.15, cy0, cy0 + 0.15, 0.05, ch, M["concrete"])
    hb.box(cx0 + 0.15, cx1 - 0.15, cy1 - 0.15, cy1, 0.05, ch, M["concrete"])
    hb.box(cx0, cx0 + 0.15, cy0, cy1, 0.05, ch, M["concrete"])
    hb.box(cx1 - 0.15, cx1, cy0, cy1, 0.05, ch, M["concrete"])
    hb.box(cx0 + 0.15, cx1 - 0.15, cy0 + 0.15, cy1 - 0.15, 0.05, ch - 0.1, M["water"])
    # outlet notch + channel
    hb.box(0.4, 0.9, cy0 - 5.6, cy0 - 0.01, -0.25, 0.0, M["concrete"])
    hb.box(0.4, 0.5, cy0 - 5.6, cy0 - 0.01, 0.0, 0.18, M["concrete"])
    hb.box(0.8, 0.9, cy0 - 5.6, cy0 - 0.01, 0.0, 0.18, M["concrete"])
    hb.box(0.5, 0.8, cy0 - 5.6, cy0 - 0.01, 0.0, 0.1, M["water"])
    put(hb, "GEO_Tubewell_Structure", c)
    # water gush: thick tapered stream falling from the pipe mouth with a foam boil
    hb = HB()
    for i in range(10):
        a = 2 * math.pi * i / 10
        p0 = np.array([0.7 + 0.05 * math.cos(a), -0.86 + 0.05 * math.sin(a), 0.68])
        p1 = np.array([0.7 + 0.11 * math.cos(a), -1.05 + 0.1 * math.sin(a), ch - 0.08])
        hb.rod(M["gush"], p0, p1, 0.03, 5)
    hb.ellipsoid(0.7, -1.1, ch - 0.1, 0.38, 0.32, 0.06, M["gush"], 14, 5)
    put(hb, "GEO_Tubewell_WaterGush", c, smooth=True)
    # LT pole with a service wire to the roof
    hb = HB()
    px, py = 2.8, 2.9
    hb.frustum(px, py, -0.5, 7.2, 0.12, 0.08, 10, M["concrete"])
    hb.box(px - 0.7, px + 0.7, py - 0.05, py + 0.05, 6.8, 6.9, M["galv"])
    for dx in (-0.6, 0.0, 0.6):
        hb.frustum(px + dx, py, 6.9, 7.02, 0.04, 0.03, 8, M["concrete"])
    pts = [np.array([px, py, 6.95])]
    end = np.array([x1 + 0.06, 1.2, h + 0.1])
    for k in range(1, 11):
        f = k / 10.0
        p = pts[0] + (end - pts[0]) * f
        p[2] -= 0.35 * math.sin(math.pi * f)
        hb.rod(M["black"], pts[-1], p, 0.008, 4)
        pts.append(p)
    put(hb, "GEO_Tubewell_Pole", c)
    print("[farm] tubewell")


def scarecrow(M):
    c = asset("AST_Scarecrow_A")
    rng = random.Random(51)
    hb = HB()
    hb.rod(M["wood"], (0, 0, -0.4), (0.03, 0.0, 2.05), 0.045, 8)
    hb.rod(M["wood"], (-0.75, 0.0, 1.52), (0.75, 0.02, 1.56), 0.035, 7)
    hb.rod(M["rope"], (-0.06, 0, 1.5), (0.06, 0, 1.6), 0.05, 6)
    put(hb, "GEO_Scarecrow_Frame", c)
    hb = HB()                                                                        # pot head
    hb.lathe(M["pot_white"], [(0.0, 1.72), (0.13, 1.74), (0.2, 1.84), (0.21, 1.95), (0.17, 2.06), (0.1, 2.12),
                              (0.09, 2.15), (0.0, 2.15)], 20)
    for sx in (-1, 1):
        hb.ellipsoid(sx * 0.07, -0.19, 1.98, 0.03, 0.012, 0.03, M["black"], 8, 4)
    hb.beam(M["black"], (-0.08, -0.205, 1.88), (0.08, -0.205, 1.885), (0, 0, 1), 0.01, 0.015)
    hb.beam(M["black"], (-0.1, -0.205, 1.93), (0.0, -0.21, 1.915), (0, 0, 1), 0.01, 0.02)
    hb.beam(M["black"], (0.0, -0.21, 1.915), (0.1, -0.205, 1.93), (0, 0, 1), 0.01, 0.02)
    hb.ellipsoid(0.0, 0.0, 2.16, 0.2, 0.2, 0.08, M["saffron"], 14, 6)              # pagdi
    hb.rod(M["saffron"], (0.15, 0.08, 2.15), (0.22, 0.2, 1.75), 0.03, 5)            # loose tail
    put(hb, "GEO_Scarecrow_Head", c, smooth=True)
    hb = HB()                                                                        # kurta
    prof = [(0.0, 0.78), (0.24, 0.78), (0.23, 1.0), (0.2, 1.3), (0.22, 1.5), (0.12, 1.66), (0.0, 1.68)]
    tmp = HB()
    tmp.lathe(M["kurta"], prof, 16)
    hb.merge(tmp, Matrix.Diagonal((1.2, 0.6, 1.0, 1.0)))
    for sx in (-1, 1):
        tmp = HB()
        tmp.frustum(0, 0, 0, 0.58, 0.1, 0.08, 10, M["kurta"])
        q = Vector((0, 0, 1)).rotation_difference(Vector((sx, 0, 0.04)))
        hb.merge(tmp, Matrix.Translation((sx * 0.14, 0, 1.54)) @ q.to_matrix().to_4x4())
    for i in range(26):                                                              # ragged hem
        a = 2 * math.pi * i / 26
        p = np.array([0.28 * math.cos(a), 0.15 * math.sin(a), 0.8])
        q = p + np.array([0.0, 0.0, -rng.uniform(0.05, 0.16)])
        side = np.array([-math.sin(a), math.cos(a), 0]) * 0.045
        hb.add([tuple(p - side), tuple(p + side), tuple(q)], [(0, 1, 2), (2, 1, 0)], M["kurta"])
    put(hb, "GEO_Scarecrow_Kurta", c, recalc=False, smooth=True)
    hb = HB()                                                                        # straw at cuffs + neck
    for (o, d) in (((-0.72, 0, 1.55), (-1, 0, 0)), ((0.72, 0, 1.57), (1, 0, 0)), ((0, 0, 1.66), (0, 0, 1))):
        tmp = HB()
        blade_clump(tmp, M["straw"], 26, 0.12, 0.26, rng, 0.04, (0.3, 0.9), 0.6)
        q = Vector((0, 0, 1)).rotation_difference(Vector(d))
        hb.merge(tmp, Matrix.Translation(o) @ q.to_matrix().to_4x4())
    put(hb, "GEO_Scarecrow_Straw", c, recalc=False)
    print("[farm] scarecrow")


# ---------------------------------------------------------------- shrubs + grass
def leaf_sources(M):
    s = {}
    hb = HB(); blade(hb, M["leaf_lantana"], 0.06, 0.025, 0.2, 0.2, 0.6); s["lantana"] = src_obj("Leaf_Lantana", hb)
    hb = HB(); blade(hb, M["leaf_dense"], 0.07, 0.03, 0.15, 0.15, 0.6); s["dense"] = src_obj("Leaf_Karonda", hb)
    hb = HB(); blade(hb, M["leaf_dry"], 0.05, 0.022, 0.25, 0.2, 0.6); s["dry"] = src_obj("Leaf_Scrub", hb)
    hb = HB()
    for k in range(7):
        a = 2 * math.pi * k / 7
        sub = HB()
        bloom(sub, M["flower_lantana"], 0.008, 4, 0.4)
        hb.merge(sub, Matrix.Translation((0.012 * math.cos(a), 0.012 * math.sin(a), 0.002)))
    s["lantana_fl"] = src_obj("Flower_Lantana_Cluster", hb)
    return s


def shrub(M, name, leaf_src, blobs, n_per, stems, flowers=None, seed=1, lower_cut=-0.5):
    c = asset(name)
    rng = random.Random(seed)
    hb = HB()
    for _ in range(stems):
        a = rng.uniform(0, 6.28)
        top = max(b[0][2] for b in blobs) * rng.uniform(0.6, 0.95)
        r = rng.uniform(0.15, 0.5) * max(b[1][0] for b in blobs)
        mid = np.array([r * 0.4 * math.cos(a), r * 0.4 * math.sin(a), top * 0.45])
        hb.rod(M["bark"], (0, 0, -0.05), mid, 0.028, 5)
        hb.rod(M["bark"], mid, (r * math.cos(a), r * math.sin(a), top), 0.016, 5)
    put(hb, "GEO_%s_Stems" % name[4:], c)
    P, R, S = [], [], []
    for ctr, rad in blobs:
        p, r, s = scatter_volume(rng, n_per, ctr, rad, lower_cut=lower_cut)
        P += p; R += r; S += s
    H.points_object("FOL_%s_Leaves" % name[4:], P, R, S, c, H.instancer("GN_%s_Leaves" % name[4:], leaf_src))
    if flowers:
        fsrc, nf = flowers
        P, R, S = [], [], []
        for ctr, rad in blobs:
            p, r, s = scatter_volume(rng, nf, ctr, tuple(x * 1.02 for x in rad), normal_bias=1.0, shell=(0.88, 1.04),
                                     lower_cut=-0.3)
            P += p; R += r; S += s
        H.points_object("FLW_%s" % name[4:], P, R, S, c, H.instancer("GN_%s_Flowers" % name[4:], fsrc))


def grass_assets(M):
    c = asset("AST_GrassTuft_A")
    hb = HB()
    blade_clump(hb, M["grass"], 30, 0.16, 0.45, random.Random(2), 0.12)
    put(hb, "GEO_GrassTuft_A", c, recalc=False)
    c = asset("AST_GrassTuft_Dry_A")
    hb = HB()
    blade_clump(hb, M["grass_dry"], 28, 0.18, 0.5, random.Random(3), 0.12, (0.25, 0.7))
    put(hb, "GEO_GrassTuft_Dry_A", c, recalc=False)
    c = asset("AST_GrassClump_Tall_A")
    rng = random.Random(4)
    hb = HB()
    tips = blade_clump(hb, M["kans"], 70, 0.9, 1.7, rng, 0.25, (0.1, 0.45), 0.8)
    put(hb, "GEO_GrassClump_Tall_Blades", c, recalc=False)
    hb = HB()
    for k in range(16):                                                              # plumes on bare stalks
        a = rng.uniform(0, 6.28)
        lean = rng.uniform(0.05, 0.3)
        base = np.array([0.1 * math.cos(a), 0.1 * math.sin(a), 0.0])
        top = base + np.array([lean * math.cos(a), lean * math.sin(a), rng.uniform(1.5, 1.95)])
        hb.rod(M["kans"], base, top, 0.006, 4)
        d = nrm(top - base + np.array([0.15 * math.cos(a), 0.15 * math.sin(a), 0]))
        for j in range(14):
            f = j / 14.0
            p = top + d * (0.04 + 0.35 * f)
            side = nrm(np.cross(d, rand_unit(rng)))
            L = 0.12 * (1.0 - 0.6 * f)
            q = p + nrm(d * 0.7 + side) * L + np.array([0, 0, -0.03])
            w = side * 0.0 + nrm(np.cross(q - p, UP)) * 0.012
            hb.add([tuple(p - w), tuple(p + w), tuple(q + w * 0.5), tuple(q - w * 0.5)], [(0, 1, 2, 3)], M["plume"])
    put(hb, "GEO_GrassClump_Tall_Plumes", c, recalc=False)
    print("[farm] grass assets")


# ============================================================================
def build_stage(M):
    stage = bpy.data.collections.new("STAGE")
    bpy.context.scene.collection.children.link(stage)
    lib = {c.name: c for c in bpy.data.collections}

    def inst(coll, name, loc, rz=0.0, s=1.0):
        e = bpy.data.objects.new(name, None)
        e.instance_type = "COLLECTION"
        e.instance_collection = lib[coll]
        e.location = loc
        e.rotation_euler = (0, 0, rz)
        e.scale = (s, s, s)
        stage.objects.link(e)
        return e

    ground = H.mat_ground()
    wheat = MM.crop("MAT_Crop_Wheat", "wheat")
    mustard = MM.crop("MAT_Crop_Mustard", "mustard")
    hb = HB()
    hb.add([(-80, -60, 0), (80, -60, 0), (80, 80, 0), (-80, 80, 0)], [(0, 1, 2, 3)], ground)
    hb.add([(-30, 4, 0.04), (6, 4, 0.04), (6, 40, 0.04), (-30, 40, 0.04)], [(0, 1, 2, 3)], wheat)
    hb.add([(8, 4, 0.04), (40, 4, 0.04), (40, 40, 0.04), (8, 40, 0.04)], [(0, 1, 2, 3)], mustard)
    put(hb, "STG_Ground", stage)
    hb = HB()                                                                        # bunds
    for (x0, x1, y0, y1) in ((-31, 7, 2.6, 3.6), (7, 41, 2.6, 3.6), (6.1, 7.9, 3, 41)):
        hb.box(x0, x1, y0, y1, -0.05, 0.25, ground)
    put(hb, "STG_Bunds", stage)
    inst("AST_Machaan_A", "STG_Machaan", (-12, 20, 0.04), 0.3)
    inst("AST_Scarecrow_A", "STG_Scarecrow", (22, 16, 0.04), -0.4)
    inst("AST_Scarecrow_A", "STG_Scarecrow2", (-4, 30, 0.04), 0.5, 0.95)
    inst("AST_Tubewell_A", "STG_Tubewell", (4.0, -6.0, 0.0), 0.0)
    for k, (x, y) in enumerate([(-6, -2), (-3, -1.5), (14, -1), (18, -2), (24, -1.2), (-20, -2.4)]):
        inst(["AST_Shrub_Lantana_A", "AST_Shrub_Dense_A", "AST_Shrub_Dry_A"][k % 3], "STG_Shrub_%d" % k, (x, y, 0), k * 1.3)
    rng = random.Random(9)
    for k in range(260):
        x, y = rng.uniform(-30, 40), rng.uniform(-22, 2.2)
        inst(rng.choice(["AST_GrassTuft_A", "AST_GrassTuft_A", "AST_GrassTuft_Dry_A"]), "STG_Tuft_%03d" % k, (x, y, 0),
             rng.uniform(0, 6.28), rng.uniform(0.7, 1.4))
    for k in range(12):
        inst("AST_GrassClump_Tall_A", "STG_Kans_%d" % k, (rng.uniform(-30, -10), rng.uniform(-14, -6), 0), rng.uniform(0, 6.28),
             rng.uniform(0.8, 1.2))
    cams = {}
    for name, pos, tgt, lens in (("CAM_Farm_Wide", (2, -26, 2.2), (2, 14, 2.5), 26),
                                 ("CAM_Machaan_Scarecrow", (8, -2, 1.7), (-6, 22, 3.0), 32),
                                 ("CAM_Tubewell_Close", (-1.5, -13.5, 1.6), (4.5, -6.5, 1.0), 30),
                                 ("CAM_Shrubs_Grass", (-2, -14, 1.2), (-12, -3, 0.6), 30)):
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        o = bpy.data.objects.new(name, cd)
        o.location = pos
        o.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        stage.objects.link(o)
        cams[name] = o
    w = bpy.data.worlds.new("WLD_Stage")                                            # same sky as MASTER_WORLD
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, H.hex_lin("#F2DCB8")
    els[1].position, els[1].color = 0.45, H.hex_lin("#5E93CC")
    els.new(0.12).color = H.hex_lin("#B9D2E6")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    sd = bpy.data.lights.new("LGT_Sun", "SUN")
    sd.energy = 4.2
    sd.color = (1.0, 0.92, 0.8)
    sd.angle = math.radians(1.0)
    sun = bpy.data.objects.new("LGT_Sun", sd)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(-40))
    stage.objects.link(sun)
    return cams


def main():
    global LIB, SRC
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "LIB_Farm_Props"
    sc.unit_settings.system = "METRIC"
    LIB = bpy.data.collections.new("LIB_FARM")
    sc.collection.children.link(LIB)
    SRC = bpy.data.collections.new("SRC_FARM")
    sc.collection.children.link(SRC)
    bpy.context.view_layer.layer_collection.children["SRC_FARM"].exclude = True
    M = materials()
    S = leaf_sources(M)
    machaan(M)
    tubewell(M)
    scarecrow(M)
    shrub(M, "AST_Shrub_Lantana_A", S["lantana"],
          [((0, 0, 0.62), (0.75, 0.65, 0.48)), ((0.45, 0.2, 0.8), (0.42, 0.4, 0.34)), ((-0.4, -0.15, 0.75), (0.45, 0.42, 0.34))],
          1300, 7, flowers=(S["lantana_fl"], 55), seed=11)
    shrub(M, "AST_Shrub_Dense_A", S["dense"],
          [((0, 0, 0.85), (0.95, 0.9, 0.75)), ((0.3, 0.25, 1.35), (0.6, 0.55, 0.45)), ((-0.45, -0.2, 1.15), (0.55, 0.5, 0.45))],
          1700, 8, seed=12, lower_cut=-0.7)
    shrub(M, "AST_Shrub_Dry_A", S["dry"],
          [((0, 0, 0.6), (0.6, 0.55, 0.42)), ((0.35, -0.1, 0.85), (0.3, 0.3, 0.25)), ((-0.3, 0.25, 0.8), (0.3, 0.3, 0.25))],
          420, 12, seed=13)
    grass_assets(M)
    for ch in LIB.children:
        bpy.context.view_layer.layer_collection.children["LIB_FARM"].children[ch.name].exclude = True
    cams = build_stage(M)
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "CUDA"
        sc.cycles.device = "GPU"
    except Exception as ex:
        print("[farm] GPU setup failed:", ex)
    quick = "--quick" in ARGS
    sc.cycles.samples = 48 if quick else 160
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = (1280, 720) if quick else (1920, 1080)
    sc.camera = cams["CAM_Farm_Wide"]
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_Farm_Props_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[farm] saved", OUT_BLEND)
    if "--render" in ARGS:
        os.makedirs(OUT_REVIEW, exist_ok=True)
        only = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None
        for name, cam in cams.items():
            if only and name not in only.split(","):
                continue
            sc.camera = cam
            sc.render.filepath = os.path.join(OUT_REVIEW, name + ".png")
            bpy.ops.render.render(write_still=True)
            print("[farm] rendered", name)


main()
