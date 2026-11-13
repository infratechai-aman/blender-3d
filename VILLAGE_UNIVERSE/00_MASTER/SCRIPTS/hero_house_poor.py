"""
HERO ASSET (Batch 2): poor family's kaccha house, variant A  - HERO_House_Small_Kaccha_A

  blender -b --factory-startup --python hero_house_poor.py -- [--render] [--quick] [--only CAM_A,CAM_B]

Output: 02_ARCHITECTURE/HOUSES_SMALL/HERO_House_Small_Kaccha_A.blend  (collection AST_House_Small_Kaccha_A)
Fits the house_small plot (6.5 x 5.5 m); origin = footprint centre at ground, door faces -Y.
  shell     hand-plastered mud walls (lipai band, mandana dots round the door), gable ends, thatched roof with a
            blue tarp patch held by rope and stones, bamboo ridge
  front     beaten-earth aangan, clay chulha with soot, tulsi in a mud planter, charpai leaning on the wall,
            clothesline with washing, matkas, bucket, dung-cake stack, stick fence
  interior  (one room, door ajar) mud floor, charpai with rolled bedding, tin trunk, wall niche (aala) with pots,
            steel utensil shelf, hanging hurricane lantern, calendar on the wall
"""
import datetime
import math
import os
import random
import shutil
import sys

import bpy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import char_lib as CL  # noqa: E402
import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "02_ARCHITECTURE", "HOUSES_SMALL", "HERO_House_Small_Kaccha_A.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "B2_HOUSE_SMALL_KACCHA_A_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

W, D = 5.6, 4.6          # wall outer footprint
T = 0.38                 # wall thickness
PH = 0.32                # plinth top
EH = 2.55                # eave wall top
RH = 3.65                # gable apex
COLL = None


def materials():
    return {
        "mud": H.mat_mud("MAT_Mud_Plaster_Kaccha", "#B08560"),
        "lipai": mat_lipai("MAT_Mud_Lipai_Dung"),
        "floor": H.mat_mud("MAT_Mud_Floor_Beaten", "#8E6E4E"),
        "straw": H.mat_straw("MAT_Thatch_Straw_Old", "#8C7448", "#B59A63"),
        "wood": H.mat_wood("MAT_Wood_Weathered_Grey", "#5E5246", "#80725F"),
        "wood_dark": H.mat_wood("MAT_Wood_Dark_Aged", "#3E2A1C", "#5A3E29"),
        "bamboo": H.mat_simple("MAT_Bamboo_Pole_Weathered", "#8F7E5E", 0.75, noise=0.25),
        "rope": H.mat_rope(),
        "tarp": H.mat_simple("MAT_Plastic_Tarp_Blue", "#2D5E9A", 0.55, noise=0.18),
        "stone": H.mat_simple("MAT_Stone_Rubble", "#7D7468", 0.85, noise=0.25),
        "white": H.mat_simple("MAT_Paint_Lime_Mandana", "#EFE7D6", 0.8),
        "soot": H.mat_simple("MAT_Soot_Black", "#1E1A17", 0.9, noise=0.2),
        "terracotta": H.mat_simple("MAT_Clay_Pot_Terracotta", "#A45A3C", 0.6, noise=0.14),
        "steel": H.mat_simple("MAT_Metal_Steel_Utensil", "#B9BEC2", 0.25, 0.9),
        "tin": H.mat_simple("MAT_Metal_Trunk_Green", "#3F6B4E", 0.45, 0.4, noise=0.2),
        "cloth1": H.mat_simple("MAT_Cloth_Washing_Pink", "#C74E78", 0.85, noise=0.15),
        "cloth2": H.mat_simple("MAT_Cloth_Washing_Yellow", "#D9A425", 0.85, noise=0.15),
        "cloth3": H.mat_simple("MAT_Cloth_Washing_Blue", "#3E6FA8", 0.85, noise=0.15),
        "quilt": H.mat_simple("MAT_Cloth_Quilt_Patch", "#8E3D3A", 0.9, noise=0.35),
        "leaf": H.mat_simple("MAT_Leaf_Tulsi_Simple", "#3E6A2A", 0.6, noise=0.25),
        "dung": H.mat_simple("MAT_DungCake", "#5E4632", 0.95, noise=0.3),
        "paper": H.mat_simple("MAT_Calendar_Print", "#D8433A", 0.6, noise=0.4),
        "glass": H.mat_simple("MAT_Glass_Lantern", "#E8E2CF", 0.1),
    }


def mat_lipai(name):
    """Cow-dung + mud wash: darker, hand-swirled (wave rings), drier patches."""
    m, t = H._mat(name, "#6B5139")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    wave = t.n("ShaderNodeTexWave", Vector=obj, Scale=3.0, Distortion=6.0, Detail=3.0)
    wave.wave_type = "RINGS"
    n = t.noise(obj, 4.0, 6.0, 0.6)
    col = t.ramp(t.math("ADD", t.math("MULTIPLY", wave.outputs["Fac"], 0.5), t.math("MULTIPLY", n.outputs["Fac"], 0.5)),
                 [(0.3, H.hex_lin("#55402D")), (0.6, H.hex_lin("#6E543B")), (0.85, H.hex_lin("#8A6E50"))])
    t.finish(col, 0.95, t.bump(wave.outputs["Fac"], 0.3, 0.01))
    return m


def put(hb, name, recalc=True, smooth=False):
    me = hb.to_mesh("ME_" + name, recalc=recalc)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    return o


def thatch(hb, mat, origin, A, La, D_, Ld, N, rng, course=0.3, overlap=0.2, thick=0.22, dx=0.07):
    xs = np.arange(0.0, La + 1e-6, dx)
    n = len(xs)
    s0 = 0.0
    sl = hb._slot(mat)
    while s0 < Ld - 1e-3:
        s1 = min(s0 + course + overlap, Ld)
        rag = np.convolve(np.array([rng.uniform(0.0, 0.2) for _ in xs]), np.ones(3) / 3, mode="same")
        lump = np.array([rng.uniform(-0.025, 0.025) for _ in xs])
        sag = 0.05 * np.sin(np.pi * xs / La)
        rows = []
        for s, off in ((s0 - rag, 0.05 - thick - sag), (s0 - rag * 0.7, 0.05 + lump - sag), (s0 + (s1 - s0) * 0.5, 0.025 + lump * 0.5 - sag),
                       (np.full(n, s1), -sag)):
            s = np.broadcast_to(s, (n,))
            off = np.broadcast_to(off, (n,))
            rows.append(origin + np.outer(xs, A) + np.outer(s, D_) + np.outer(off, N))
        base = len(hb.v)
        for r in rows:
            hb.v.extend(map(tuple, r.tolist()))
        for k in range(len(rows) - 1):
            for i in range(n - 1):
                a = base + k * n + i
                hb.f.append((a, a + 1, a + n + 1, a + n))
                hb.mi.append(sl)
        s0 += course


def wall_with_openings(hb, mat, x0, x1, y0, y1, z0, z1, holes, axis="x"):
    """Axis-aligned wall slab with rectangular holes [(a0, a1, h0, h1)] along its length (axis x or y)."""
    a_lo, a_hi = (x0, x1) if axis == "x" else (y0, y1)
    cuts = sorted(holes)
    pos = a_lo
    for (h0, h1, v0, v1) in cuts:
        if h0 > pos:
            seg(hb, mat, axis, pos, h0, x0, x1, y0, y1, z0, z1)
        seg(hb, mat, axis, h0, h1, x0, x1, y0, y1, z0, v0)
        seg(hb, mat, axis, h0, h1, x0, x1, y0, y1, v1, z1)
        pos = h1
    if pos < a_hi:
        seg(hb, mat, axis, pos, a_hi, x0, x1, y0, y1, z0, z1)


def seg(hb, mat, axis, a0, a1, x0, x1, y0, y1, z0, z1):
    if z1 - z0 < 1e-3 or a1 - a0 < 1e-3:
        return
    if axis == "x":
        hb.box(a0, a1, y0, y1, z0, z1, mat)
    else:
        hb.box(x0, x1, a0, a1, z0, z1, mat)


def gable(hb, mat, x0, x1, rng):
    """Triangular mud gable on a side wall, slightly irregular top edge."""
    V = [(x0, -D / 2, EH), (x0, D / 2, EH), (x0, 0.0, RH), (x1, -D / 2, EH), (x1, D / 2, EH), (x1, 0.0, RH)]
    F = [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)]
    hb.add(V, F, mat)


def build_shell(M, rng):
    hb = HB()
    hb.box(-W / 2 - 0.35, W / 2 + 0.35, -D / 2 - 0.35, D / 2 + 0.35, -0.25, PH, M["floor"])            # plinth
    # walls: lower lipai band + upper mud plaster as separate slabs so the two finishes read
    door = (-0.45, 0.45, PH, PH + 1.85)
    win_f = (1.35, 1.95, PH + 0.95, PH + 1.6)
    win_b = (-1.6, -1.05, PH + 1.0, PH + 1.55)
    for (zz0, zz1, mat) in ((PH, PH + 0.55, M["lipai"]), (PH + 0.55, EH, M["mud"])):
        hf = [(h0, h1, max(v0, zz0), min(v1, zz1)) for (h0, h1, v0, v1) in (door, win_f) if v1 > zz0 and v0 < zz1]
        wall_with_openings(hb, mat, -W / 2, W / 2, -D / 2, -D / 2 + T, zz0, zz1, hf, "x")
        hb_ = [(h0, h1, max(v0, zz0), min(v1, zz1)) for (h0, h1, v0, v1) in (win_b,) if v1 > zz0 and v0 < zz1]
        wall_with_openings(hb, mat, -W / 2, W / 2, D / 2 - T, D / 2, zz0, zz1, hb_, "x")
        hb.box(-W / 2, -W / 2 + T, -D / 2 + T, D / 2 - T, zz0, zz1, mat)
        hb.box(W / 2 - T, W / 2, -D / 2 + T, D / 2 - T, zz0, zz1, mat)
    gable(hb, M["mud"], -W / 2, -W / 2 + T, rng)
    gable(hb, M["mud"], W / 2 - T, W / 2, rng)
    hb.box(-W / 2 + T, W / 2 - T, -D / 2 + T, D / 2 - T, PH - 0.01, PH + 0.005, M["floor"])            # inner floor
    o = put(hb, "GEO_HouseKaccha_Walls")
    b = o.modifiers.new("Soften", "BEVEL")
    b.width = 0.06
    b.segments = 3
    b.limit_method = "ANGLE"
    # mandana: white dot border round the door and a row along the plinth
    hb = HB()
    for k in range(26):
        t = k / 25
        if t < 0.35:
            x, z = -0.62, PH + 0.1 + t / 0.35 * 1.95
        elif t < 0.65:
            x, z = -0.62 + (t - 0.35) / 0.3 * 1.24, PH + 2.08
        else:
            x, z = 0.62, PH + 2.05 - (t - 0.65) / 0.35 * 1.95
        hb.ellipsoid(x, -D / 2 - 0.006, z, 0.028, 0.006, 0.028, M["white"], 8, 4)
    for k in range(40):
        hb.ellipsoid(-W / 2 + 0.2 + k * (W - 0.4) / 39, -D / 2 - 0.36, PH - 0.05, 0.025, 0.012, 0.02, M["white"], 6, 3)
    put(hb, "GEO_HouseKaccha_Mandana", recalc=False)
    # door (plank, ajar) + frame + latch chain; window frames with bamboo bars
    hb = HB()
    hb.box(-0.52, -0.45, -D / 2 - 0.02, -D / 2 + T, PH, PH + 1.92, M["wood_dark"])
    hb.box(0.45, 0.52, -D / 2 - 0.02, -D / 2 + T, PH, PH + 1.92, M["wood_dark"])
    hb.box(-0.6, 0.6, -D / 2 - 0.03, -D / 2 + T, PH + 1.85, PH + 1.98, M["wood_dark"])
    put(hb, "GEO_HouseKaccha_DoorFrame")
    hb = HB()
    for k in range(5):
        hb.box(0.0 + k * 0.17, 0.165 + k * 0.17, -0.03, 0.03, 0.0, 1.82 - 0.02 * (k % 2), M["wood"])
    for z in (0.3, 1.45):
        hb.box(0.02, 0.83, -0.05, -0.03, z, z + 0.1, M["wood"])
    door = put(hb, "GEO_HouseKaccha_Door")
    door.location = (-0.45, -D / 2 + 0.05, PH + 0.02)
    door.rotation_euler = (0, 0, math.radians(68))
    hb = HB()
    for (h0, h1, v0, v1), y0 in ((win_f, -D / 2), (win_b, D / 2 - T)):
        hb.box(h0 - 0.06, h1 + 0.06, y0 - 0.02, y0 + T + 0.02, v0 - 0.06, v0, M["wood_dark"])
        hb.box(h0 - 0.06, h1 + 0.06, y0 - 0.02, y0 + T + 0.02, v1, v1 + 0.06, M["wood_dark"])
        for k in range(5):
            x = h0 + (h1 - h0) * (k + 0.5) / 5
            hb.rod(M["bamboo"], (x, y0 + T / 2, v0), (x, y0 + T / 2, v1), 0.014, 6)
    put(hb, "GEO_HouseKaccha_Windows")
    # roof: thatch gable (ridge along X), bamboo rafters + ridge, blue tarp patch, holding stones
    hb = HB()
    ov = 0.55
    for sy in (-1, 1):
        y_e = sy * (D / 2 + ov)
        z_e = EH - 0.12
        Dv = np.array([0.0, -y_e, RH + 0.1 - z_e])
        Ld = float(np.linalg.norm(Dv))
        Dv /= Ld
        A = np.array([1.0, 0.0, 0.0])
        Nv = np.cross(A, Dv) * (1 if sy < 0 else -1)
        if Nv[2] < 0:
            Nv = -Nv
        thatch(hb, M["straw"], np.array([-W / 2 - ov, y_e, z_e]), A, W + 2 * ov, Dv, Ld, Nv, rng)
    put(hb, "GEO_HouseKaccha_Thatch", recalc=False)
    hb = HB()
    hb.rod(M["bamboo"], (-W / 2 - ov - 0.1, 0.0, RH + 0.14), (W / 2 + ov + 0.1, 0.0, RH + 0.14), 0.06, 8)
    for x in np.arange(-W / 2 - ov + 0.1, W / 2 + ov, 0.55):
        for sy in (-1, 1):
            hb.rod(M["bamboo"], (x, 0.0, RH + 0.05), (x, sy * (D / 2 + ov - 0.05), EH - 0.1), 0.03, 6)
    for x in np.arange(-W / 2, W / 2 + 0.01, 0.7):                                          # ridge rope ties
        hb.rod(M["rope"], (x, -0.15, RH + 0.16), (x, 0.15, RH + 0.16), 0.012, 4)
    put(hb, "GEO_HouseKaccha_RoofFrame")
    # tarp: a draped quad grid on the back-left slope, tied with rope, weighed with stones
    hb = HB()
    nx, ny = 12, 8
    x0, x1 = -W / 2 - 0.2, -W / 2 + 2.4
    V = []
    for j in range(ny + 1):
        for i in range(nx + 1):
            u, v = i / nx, j / ny
            y = 0.15 + v * (D / 2 + ov - 0.3)
            z = RH + 0.12 - (y / (D / 2 + ov)) * (RH - EH + 0.05) + 0.04 + 0.05 * math.sin(u * 7 + v * 3) * (0.3 + v)
            V.append((x0 + u * (x1 - x0), y, z))
    F = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(ny) for i in range(nx)]
    hb.add(V, F, M["tarp"])
    tarp = put(hb, "GEO_HouseKaccha_Tarp", recalc=False)
    tarp.modifiers.new("Thick", "SOLIDIFY").thickness = 0.006
    hb = HB()
    for k in range(6):
        u, v = rng.uniform(0.05, 0.95), rng.uniform(0.3, 0.9)
        y = 0.15 + v * (D / 2 + ov - 0.3)
        z = RH + 0.12 - (y / (D / 2 + ov)) * (RH - EH + 0.05) + 0.1
        hb.ellipsoid(x0 + u * (x1 - x0), y, z, 0.13, 0.11, 0.08, M["stone"], 8, 5)
    put(hb, "GEO_HouseKaccha_RoofStones", smooth=True)


def charpai(hb, M, cx, cy, cz, rot_x=0.0, L=1.85, Wd=0.85, h=0.45):
    """Rope-strung cot; built flat then optionally tilted about X (leaning on a wall)."""
    sub = HB()
    for sx in (-1, 1):
        sub.box(-L / 2, L / 2, sx * Wd / 2 - 0.04, sx * Wd / 2 + 0.04, h - 0.08, h, M["wood"])
        sub.box(sx * L / 2 - 0.04, sx * L / 2 + 0.04, -Wd / 2, Wd / 2, h - 0.08, h, M["wood"])
        for sy in (-1, 1):
            sub.lathe(M["wood"], [(0.0, 0.0), (0.04, 0.0), (0.05, 0.15), (0.035, 0.3), (0.045, h), (0.0, h)], 10, sx * L / 2, sy * Wd / 2, 0)
    for k in range(13):
        x = -L / 2 + 0.06 + k * (L - 0.12) / 12
        sub.rod(M["rope"], (x, -Wd / 2, h - 0.04), (x + 0.06, Wd / 2, h - 0.04), 0.008, 4)
    for k in range(7):
        y = -Wd / 2 + 0.05 + k * (Wd - 0.1) / 6
        sub.rod(M["rope"], (-L / 2, y, h - 0.035), (L / 2, y + 0.04, h - 0.035), 0.008, 4)
    from mathutils import Matrix
    hb.merge(sub, Matrix.Translation((cx, cy, cz)) @ Matrix.Rotation(rot_x, 4, "X"))


def build_yard_and_interior(M, rng):
    hb = HB()
    # aangan: beaten-earth patch in front
    hb.box(-W / 2 - 0.2, W / 2 + 0.2, -D / 2 - 2.6, -D / 2 - 0.36, -0.06, 0.03, M["lipai"])
    # chulha (U-shaped clay stove) with soot + a blackened pot
    cx, cy = -2.0, -D / 2 - 1.5
    hb.box(cx - 0.32, cx + 0.32, cy - 0.06, cy + 0.06, 0.0, 0.3, M["mud"])
    for sx in (-1, 1):
        hb.box(cx + sx * 0.26 - 0.06, cx + sx * 0.26 + 0.06, cy - 0.3, cy + 0.06, 0.0, 0.3, M["mud"])
    hb.box(cx - 0.2, cx + 0.2, cy - 0.28, cy - 0.02, 0.0, 0.02, M["soot"])
    hb.lathe(M["soot"], [(0.0, 0.0), (0.12, 0.02), (0.17, 0.1), (0.15, 0.2), (0.11, 0.24), (0.12, 0.26)], 16, cx, cy - 0.12, 0.3)
    # tulsi planter
    tx, ty = 2.3, -D / 2 - 1.2
    hb.box(tx - 0.3, tx + 0.3, ty - 0.3, ty + 0.3, 0.0, 0.75, M["mud"])
    hb.box(tx - 0.33, tx + 0.33, ty - 0.33, ty + 0.33, 0.75, 0.8, M["white"])
    for k in range(60):
        a, r = rng.uniform(0, 6.28), rng.uniform(0, 0.2)
        hb.ellipsoid(tx + r * math.cos(a), ty + r * math.sin(a), 0.85 + rng.uniform(0, 0.35), 0.035, 0.02, 0.012, M["leaf"], 6, 3)
    # matkas, bucket, dung-cake stack
    for k, (x, y, s) in enumerate(((-1.2, -D / 2 - 0.6, 1.0), (-0.95, -D / 2 - 0.62, 0.85), (1.1, -D / 2 - 0.55, 0.9))):
        hb.lathe(M["terracotta"], [(0.0, 0.0), (0.12 * s, 0.0), (0.2 * s, 0.12 * s), (0.19 * s, 0.26 * s), (0.08 * s, 0.36 * s),
                                   (0.07 * s, 0.4 * s), (0.09 * s, 0.42 * s)], 16, x, y, 0.03)
    hb.lathe(M["steel"], [(0.0, 0.0), (0.12, 0.0), (0.15, 0.28), (0.155, 0.29), (0.14, 0.29)], 16, 1.5, -D / 2 - 0.7, 0.03)
    for i in range(5):
        for j in range(4):
            hb.frustum(-W / 2 - 0.6 + j * 0.24 + (0.12 if i % 2 else 0), D / 2 - 0.4, 0.02 + i * 0.05, 0.05 + i * 0.05, 0.11, 0.11, 10, M["dung"])
    # stick fence along the aangan sides
    for side in (-1, 1):
        x = side * (W / 2 + 0.25)
        for k in range(10):
            y = -D / 2 - 0.3 - k * 0.24
            hb.rod(M["bamboo"], (x + rng.uniform(-0.03, 0.03), y, -0.05), (x + rng.uniform(-0.06, 0.06), y, rng.uniform(0.8, 1.05)), 0.018, 5)
        hb.rod(M["bamboo"], (x, -D / 2 - 0.3, 0.5), (x, -D / 2 - 2.5, 0.5), 0.014, 5)
        hb.rod(M["bamboo"], (x, -D / 2 - 0.3, 0.85), (x, -D / 2 - 2.5, 0.85), 0.014, 5)
    # clothesline: bamboo pole -> roof edge, three cloths
    pole = np.array([2.9, -D / 2 - 2.3, 0.0])
    hb.rod(M["bamboo"], pole, pole + np.array([0, 0, 2.2]), 0.035, 6)
    a, b = pole + np.array([0, 0, 2.1]), np.array([1.2, -D / 2 - 0.55, EH - 0.2])
    hb.rod(M["rope"], a, b, 0.006, 4)
    for k, mat in enumerate((M["cloth1"], M["cloth2"], M["cloth3"])):
        t = 0.2 + k * 0.25
        p = a + (b - a) * t - np.array([0, 0, 0.03 * math.sin(math.pi * t)])
        d = (b - a) / np.linalg.norm(b - a)
        side = d * 0.28
        hb.add([tuple(p - side), tuple(p + side), tuple(p + side * 0.95 - np.array([0, 0, 0.6 + 0.1 * k])),
                tuple(p - side * 1.05 - np.array([0, 0, 0.55 + 0.1 * k]))], [(0, 1, 2, 3)], mat)
    # charpai leaning against the front wall (right of the door)
    charpai(hb, M, 1.6, -D / 2 - 0.42, 0.95, rot_x=math.radians(-72))
    put(hb, "GEO_HouseKaccha_Yard")
    # ---- interior
    hb = HB()
    charpai(hb, M, -1.1, 0.9, PH, 0.0, L=1.8, Wd=0.8)
    hb.ellipsoid(-1.75, 0.9, PH + 0.55, 0.12, 0.34, 0.12, M["quilt"], 12, 6)                    # rolled bedding
    hb.box(1.2, 1.95, 1.1, 1.6, PH, PH + 0.42, M["tin"])                                        # tin trunk
    hb.box(1.18, 1.97, 1.08, 1.62, PH + 0.42, PH + 0.46, M["tin"])
    # wall niche (aala) on the back wall with two small pots
    hb.box(0.2, 0.75, D / 2 - T - 0.01, D / 2 - T + 0.0, PH + 1.15, PH + 1.6, M["soot"])
    for x in (0.33, 0.6):
        hb.lathe(M["terracotta"], [(0.0, 0.0), (0.05, 0.0), (0.08, 0.06), (0.04, 0.12), (0.045, 0.14)], 12, x, D / 2 - T - 0.08, PH + 1.15)
    # steel utensil shelf on the left wall
    hb.box(-W / 2 + T, -W / 2 + T + 0.25, -0.6, 0.6, PH + 1.3, PH + 1.34, M["wood"])
    for k in range(5):
        y = -0.5 + k * 0.25
        hb.lathe(M["steel"], [(0.0, 0.0), (0.08, 0.0), (0.1, 0.05), (0.1, 0.06)], 14, -W / 2 + T + 0.12, y, PH + 1.34)
        hb.frustum(-W / 2 + T + 0.03, y, PH + 1.45, PH + 1.65, 0.1, 0.1, 16, M["steel"])
    # hurricane lantern hanging from a roof rafter
    lx, ly, lz = 0.2, -0.3, 2.2
    hb.rod(M["rope"], (lx, ly, EH + 0.6), (lx, ly, lz + 0.22), 0.006, 4)
    hb.lathe(M["tin"], [(0.0, 0.0), (0.08, 0.0), (0.08, 0.05)], 12, lx, ly, lz - 0.12)
    hb.lathe(M["glass"], [(0.0, 0.0), (0.05, 0.0), (0.07, 0.08), (0.05, 0.16), (0.0, 0.16)], 12, lx, ly, lz - 0.07)
    hb.frustum(lx, ly, lz + 0.09, lz + 0.15, 0.08, 0.03, 12, M["tin"])
    # calendar on the wall
    hb.box(-0.3, 0.1, D / 2 - T - 0.012, D / 2 - T - 0.002, PH + 1.2, PH + 1.75, M["paper"])
    put(hb, "GEO_HouseKaccha_Interior")
    return (lx, ly, lz)


def main():
    global COLL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    lib = bpy.data.collections.new("LIB_HOUSES_SMALL")
    sc.collection.children.link(lib)
    COLL = bpy.data.collections.new("AST_House_Small_Kaccha_A")
    lib.children.link(COLL)
    rng = random.Random(7)
    M = materials()
    build_shell(M, rng)
    lamp = build_yard_and_interior(M, rng)
    COLL["night_lights"] = [list(lamp)]
    # stage: ground + master lighting look, cameras front / 3-4 / yard / interior
    import lighting_atmosphere as LA
    hb = HB()
    hb.add([(-40, -40, -0.02), (40, -40, -0.02), (40, 40, -0.02), (-40, 40, -0.02)], [(0, 1, 2, 3)], H.mat_ground())
    g = bpy.data.objects.new("STG_Ground", hb.to_mesh("ME_STG_Ground"))
    sc.collection.objects.link(g)
    e = bpy.data.objects.new("STG_House", None)
    e.instance_type = "COLLECTION"
    e.instance_collection = COLL
    sc.collection.objects.link(e)
    bpy.context.view_layer.layer_collection.children["LIB_HOUSES_SMALL"].exclude = True
    LA.apply(sc, "morning")
    from mathutils import Vector
    cams = {"CAM_Front": ((0.6, -13.0, 1.7), (0.0, 0.0, 1.7), 30), "CAM_ThreeQuarter": ((-8.5, -9.5, 3.2), (0.0, 0.0, 1.6), 28),
            "CAM_Yard": ((3.6, -6.6, 1.5), (-0.8, -3.0, 0.9), 28), "CAM_Interior": ((-0.2, -3.3, 1.5), (-0.4, 1.5, 1.0), 20),
            "CAM_Back34": ((7.5, 8.0, 3.5), (0.0, 0.0, 1.8), 28)}
    for name, (pos, tgt, lens) in cams.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        o = bpy.data.objects.new(name, cd)
        o.location = pos
        o.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(o)
    sc.camera = bpy.data.objects["CAM_ThreeQuarter"]
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "HERO_House_Small_Kaccha_A_%s.blend" %
                                             datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[house] saved", OUT_BLEND)
    if "--render" in ARGS:
        os.makedirs(OUT_REVIEW, exist_ok=True)
        sc.render.engine = "BLENDER_EEVEE"
        quick = "--quick" in ARGS
        sc.render.resolution_x, sc.render.resolution_y = (1280, 720) if quick else (1920, 1080)
        sc.eevee.taa_render_samples = 32 if quick else 64
        only = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
        for name in cams:
            if only and name not in only:
                continue
            sc.camera = bpy.data.objects[name]
            sc.render.filepath = os.path.join(OUT_REVIEW, name + ".png")
            bpy.ops.render.render(write_still=True)
            print("[house] rendered", name)


if __name__ == "__main__":
    main()
