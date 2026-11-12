"""
HERO ASSET: Common tiled house, variant A  (quality benchmark for the architecture library)

  blender -b --factory-startup --python hero_house_common.py -- [--render] [--quick] [--only CAM]

Builds 02_ARCHITECTURE/HOUSES_MEDIUM/HERO_House_Common_A.blend
Asset origin = centre of footprint at ground level, front door faces -Y (same convention as plots).
Footprint 10.0 x 8.5 m (matches the house_common family in config_layout.py).
"""
import math
import os
import random
import shutil
import sys
import datetime

import bpy
from mathutils import Matrix, Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
ASSET = "House_Common_A"
VERSION = "v001"
OUT_BLEND = os.path.join(ROOT, "02_ARCHITECTURE", "HOUSES_MEDIUM", "HERO_%s.blend" % ASSET)
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "G3_HERO_%s_%s" % (ASSET.upper(), VERSION))
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

# ---------------------------------------------------------------- dimensions
W, D = 10.0, 8.5            # footprint
VD = 2.3                    # veranda depth
PH = 0.5                    # plinth top
WH = 3.2                    # wall height
WT = PH + WH                # wall top 3.7
T = 0.35                    # wall thickness
YF = -D / 2                 # veranda front -4.25
YB = YF + VD                # front wall outer face -1.95
YK = D / 2                  # back wall outer face 4.25
PITCH = math.radians(30)
TAN = math.tan(PITCH)
RIDGE_Y = (YB + YK) / 2
GX = W / 2 + 0.45           # gable overhang
POSTS = [-4.85, -1.7, 1.85, 4.85]
POST_Y = -4.05
BEAM_TOP = 2.95

COLL = {}


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    COLL[name] = c
    return c


def obj_from(hb, name, collname, recalc=True, parent=None):
    me = hb.to_mesh("ME_" + name, recalc=recalc)
    o = bpy.data.objects.new(name, me)
    COLL[collname].objects.link(o)
    if parent:
        o.parent = parent
    return o


def materials():
    M = {
        "plaster": H.mat_plaster("MAT_Wall_LimePlaster_White_IndigoBand", "#EDE3CF", band="#4A6A9A", band_top=PH + 0.65),
        "plaster_plain": H.mat_plaster("MAT_Wall_LimePlaster_White", "#EDE3CF"),
        "tile": H.mat_tile(),
        "wood": H.mat_wood(),
        "wood_dark": H.mat_wood("MAT_Wood_Dark_Aged", "#3E2A1C", "#5A3E29"),
        "paint": H.mat_painted("MAT_Wood_Painted_Teal", "#2F7A72"),
        "stone": H.mat_stone_blocks(),
        "coping": H.mat_simple("MAT_Stone_Coping_Smooth", "#A39A8C", 0.7, noise=0.12),
        "kota": H.mat_kota(),
        "cement": H.mat_simple("MAT_Floor_Cement_Plain", "#9C968B", 0.6, noise=0.1),
        "mud": H.mat_mud(),
        "lipai": H.mat_mud("MAT_Mud_Lipai_Yard", "#B39270", 0.97),
        "tin": H.mat_tin(),
        "iron": H.mat_simple("MAT_Metal_Iron_Painted_Black", "#262626", 0.5, 0.6),
        "concrete": H.mat_simple("MAT_Concrete_Weathered", "#B3AC9F", 0.85, noise=0.15),
        "clay": H.mat_simple("MAT_Clay_Pot_Terracotta", "#A45A3C", 0.55, noise=0.12),
        "rope": H.mat_rope(),
        "leaf": H.mat_leaf("MAT_Foliage_Tulsi", ("#3E6A2A", "#527F33", "#6B4E5E")),
        "mango_leaf": H.mat_simple("MAT_Foliage_MangoLeaf_Toran", "#3F6E2C", 0.6, noise=0.15),
        "chaura": H.mat_plaster("MAT_Plaster_Tulsi_Chaura", "#F1E6D2", band="#C2552E", band_top=0.35),
        "meter": H.mat_simple("MAT_Plastic_MeterBox_Grey", "#9EA3A2", 0.45),
        "bulb": H.mat_simple("MAT_Bulb_Warm", "#FFF1D6", 0.2, emission=H.hex_lin("#FFD9A0"), estr=0.0),
        "plate": H.mat_simple("MAT_Nameplate_Black", "#1D1D1D", 0.35),
        "dark": H.mat_simple("MAT_Void_Dark", "#0E0C0A", 0.9),
        "cut": H.mat_simple("MAT_Cutter_Hidden", "#FF00FF", 1.0),
        "ground": H.mat_ground(),
        "tree": H.mat_simple("MAT_Foliage_Stage_Tree", "#4A7234", 0.8, noise=0.2),
        "bark": H.mat_wood("MAT_Bark_Stage", "#4A3829", "#5E4A38", 0.9),
    }
    return M


# ============================================================================
# Openings (doors / windows) built in a canonical frame:
#   outer wall face at y = 0, wall runs inward to y = T, opening centred on x = 0.
# ============================================================================
def opening(M, kind, w, z0, z1, rng, chhajja=False):
    p, cut = HB(), HB()
    cut.box(-w / 2, w / 2, -0.3, T + 0.3, z0, z1, M["cut"])
    fr = 0.09
    paint = M["paint"]
    p.box(-w / 2, -w / 2 + fr, 0.04, 0.22, z0, z1, paint)
    p.box(w / 2 - fr, w / 2, 0.04, 0.22, z0, z1, paint)
    p.box(-w / 2, w / 2, 0.04, 0.22, z1 - fr, z1, paint)
    p.box(-w / 2 - 0.22, w / 2 + 0.22, -0.035, 0.1, z1, z1 + 0.17, M["wood_dark"])      # lintel
    if kind == "window":
        p.box(-w / 2, w / 2, 0.04, 0.22, z0, z0 + fr, paint)
        p.box(-w / 2 - 0.1, w / 2 + 0.1, -0.09, 0.12, z0 - 0.07, z0, M["coping"])      # sill
        n = max(3, int(round((w - 2 * fr) / 0.15)))
        for i in range(n):
            x = -w / 2 + fr + (i + 1) * (w - 2 * fr) / (n + 1)
            p.rod(M["iron"], (x, 0.13, z0 + fr), (x, 0.13, z1 - fr), 0.011, 6)
        zm = (z0 + z1) / 2
        p.box(-w / 2 + fr, w / 2 - fr, 0.115, 0.145, zm - 0.015, zm + 0.015, M["iron"])
        p.box(-w / 2 + fr, w / 2 - fr, 0.30, 0.32, z0, z1, M["dark"])                   # inner curtain/shadow
        lw = w / 2
        for sx in (-1, 1):
            th = math.radians(rng.uniform(128, 160))
            dv = np.array([-sx * math.cos(th), -math.sin(th), 0.0])
            hinge = np.array([sx * w / 2, -0.035, 0.0])
            c = hinge + dv * (lw / 2)
            c[2] = (z0 + z1) / 2
            U = dv
            V = np.array([0.0, 0.0, 1.0])
            Wn = np.cross(U, V)
            hh = (z1 - z0) / 2 - 0.02
            p.obox(paint, c, U, V, lw / 2, hh, 0.018)
            for sz in (-1, 1):
                for sw in (-1, 1):
                    p.obox(paint, c + V * sz * hh * 0.48 + Wn * sw * 0.022, U, V, lw * 0.33, hh * 0.36, 0.006)
    else:  # door
        p.box(-w / 2 - 0.08, w / 2 + 0.08, -0.06, T, z0 - 0.02, z0 + 0.09, M["coping"])  # threshold
        lw = (w - 2 * fr) / 2
        zt = z1 - fr
        for sx in (-1, 1):
            xa, xb = sorted((0.0, sx * lw))
            p.box(xa + 0.004, xb - 0.004, 0.10, 0.16, z0 + 0.09, zt, paint)
            ph = (zt - z0 - 0.09)
            for k in range(3):
                za = z0 + 0.09 + ph * (0.06 + k * 0.32)
                p.box(xa + 0.07, xb - 0.07, 0.085, 0.10, za, za + ph * 0.26, paint)
            for k in range(4):
                for j in (0.25, 0.75):
                    xx = xa + (xb - xa) * j
                    zz = z0 + 0.09 + ph * (0.04 + k * 0.32) if k < 3 else zt - 0.06
                    p.rod(M["iron"], (xx, 0.10, zz), (xx, 0.075, zz), 0.017, 6)
            hx = sx * 0.07
            p.rod(M["iron"], (hx, 0.10, z0 + 1.05), (hx, 0.06, z0 + 1.05), 0.012, 6)
            p.rod(M["iron"], (hx, 0.06, z0 + 1.05), (hx, 0.06, z0 + 0.93), 0.008, 6)
        p.box(-w / 2 + fr, w / 2 - fr, 0.30, 0.32, z0, zt, M["dark"])
    if chhajja:
        p.box(-w / 2 - 0.3, w / 2 + 0.3, -0.5, 0.0, z1 + 0.2, z1 + 0.28, M["concrete"])
    return p, cut


def place(n_out, px, py):
    a = {(0, -1): 0.0, (0, 1): math.pi, (-1, 0): -math.pi / 2, (1, 0): math.pi / 2}[n_out]
    return Matrix.Translation(Vector((px, py, 0.0))) @ Matrix.Rotation(a, 4, "Z")


OPENINGS = [
    # kind,     wall normal, x,      y,     width, z0,        z1,        chhajja
    ("door",   (0, -1),  0.6,    YB,    1.2,  PH,        PH + 2.25, False),
    ("window", (0, -1), -3.25,   YB,    1.0,  1.35,      2.6,       False),
    ("window", (0, -1),  3.35,   YB,    1.0,  1.35,      2.6,       False),
    ("door",   (0, 1),  -2.2,    YK,    0.9,  PH,        PH + 2.05, True),
    ("window", (0, 1),   2.4,    YK,    0.9,  1.45,      2.55,      True),
    ("window", (-1, 0), -W / 2,  1.2,   0.9,  1.4,       2.55,      True),
    ("window", (1, 0),   W / 2, -0.75,  0.8,  1.45,      2.5,       True),
]


# ============================================================================
def build_house(M, root):
    rng = random.Random(41)

    # ---------------- plinth, steps, floors
    hb = HB()
    hb.box(-W / 2 - 0.25, W / 2 + 0.25, YF - 0.25, YK + 0.25, -0.6, PH - 0.08, M["stone"])
    hb.box(-W / 2 - 0.32, W / 2 + 0.32, YF - 0.32, YK + 0.32, PH - 0.08, PH, M["coping"])
    for i, (ya, za) in enumerate(((0.38, 0.33), (0.76, 0.16))):
        hb.box(-0.25, 1.45, YF - 0.32 - ya, YF - 0.32 - ya + 0.38, -0.3, za, M["coping" if i == 0 else "stone"])
    hb.box(-2.75, -1.65, YK + 0.32, YK + 0.7, -0.3, 0.25, M["stone"])            # back step
    hb.box(-W / 2 - 0.2, W / 2 + 0.2, YF - 0.2, YB, PH, PH + 0.03, M["kota"])      # veranda floor
    hb.box(-W / 2 + T, W / 2 - T, YB + T, YK - T, PH, PH + 0.03, M["cement"])      # interior floor
    obj_from(hb, "GEO_%s_Plinth_Floors" % ASSET, "AST", parent=root)

    # ---------------- walls (hollow shell) + openings
    hb = HB()
    hb.box(-W / 2, W / 2, YB, YK, PH, WT, M["plaster"])
    hb.box_inv(-W / 2 + T, W / 2 - T, YB + T, YK - T, PH + 0.02, WT - 0.12, M["plaster_plain"])
    walls = obj_from(hb, "GEO_%s_Walls" % ASSET, "AST", parent=root)
    parts, cutters = HB(), HB()
    for kind, n_out, x, y, w, z0, z1, ch in OPENINGS:
        p, c = opening(M, kind, w, z0, z1, rng, ch)
        Mx = place(n_out, x, y)
        parts.merge(p, Mx)
        cutters.merge(c, Mx)
    obj_from(parts, "GEO_%s_Doors_Windows" % ASSET, "AST", parent=root)
    cut = obj_from(cutters, "CUT_%s_Openings" % ASSET, "AST_CUTTERS", parent=root)
    cut.hide_render = True
    cut.display_type = "WIRE"
    bev = walls.modifiers.new("Bevel_Soft", "BEVEL")
    bev.width = 0.025
    bev.segments = 2
    bev.limit_method = "ANGLE"
    bo = walls.modifiers.new("Openings", "BOOLEAN")
    bo.operation = "DIFFERENCE"
    bo.object = cut
    try:
        bo.solver = "EXACT"
    except Exception:
        pass

    # ---------------- gable walls
    zr = WT + (RIDGE_Y - YB) * TAN
    hb = HB()
    for xo, xi in ((-W / 2, -W / 2 + T), (W / 2, W / 2 - T)):
        v = []
        for xx in (xo, xi):
            v += [(xx, YB, WT), (xx, YK, WT), (xx, RIDGE_Y, zr)]
        hb.add(v, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], M["plaster_plain"])
        s = 1 if xo > 0 else -1
        hb.box(xo - 0.02 if s > 0 else xo - 0.03, xo + 0.03 if s > 0 else xo + 0.02, RIDGE_Y - 0.35, RIDGE_Y + 0.35,
               WT + 0.75, WT + 1.15, M["dark"])                                       # vent
        hb.box(xo - 0.035 if s > 0 else xo - 0.045, xo + 0.045 if s > 0 else xo + 0.035, RIDGE_Y - 0.42,
               RIDGE_Y + 0.42, WT + 0.68, WT + 0.75, M["wood_dark"])
    # mortar flashing where the veranda roof meets the front wall
    hb.box(-W / 2, W / 2, YB - 0.09, YB, 3.5, 3.64, M["plaster_plain"])
    obj_from(hb, "GEO_%s_Gables" % ASSET, "AST", parent=root)

    # ---------------- veranda timber
    hb = HB()
    for x in POSTS:
        hb.box(x - 0.17, x + 0.17, POST_Y - 0.17, POST_Y + 0.17, PH + 0.03, PH + 0.28, M["coping"])
        hb.box(x - 0.1, x + 0.1, POST_Y - 0.1, POST_Y + 0.1, PH + 0.28, 2.6, M["wood"])
        hb.box(x - 0.13, x + 0.13, POST_Y - 0.13, POST_Y + 0.13, PH + 0.28, PH + 0.38, M["wood_dark"])
        hb.box(x - 0.24, x + 0.24, POST_Y - 0.15, POST_Y + 0.15, 2.6, 2.72, M["wood_dark"])
        for s in (-1, 1):
            if abs(x + s * 0.5) < W / 2 + 0.05:
                hb.beam(M["wood"], (x + s * 0.09, POST_Y, 2.2), (x + s * 0.5, POST_Y, 2.71), (0, 1, 0), 0.08, 0.08)
    hb.box(-W / 2 - 0.15, W / 2 + 0.15, POST_Y - 0.12, POST_Y + 0.12, 2.72, BEAM_TOP, M["wood"])

    # veranda roof plane: through (POST_Y, 3.09) and (YB, 3.55)
    k = (3.55 - 3.09) / (YB - POST_Y)
    ye = YF - 0.5
    ze = 3.09 - (POST_Y - ye) * k
    Dv = np.array([0.0, 1.0, k]) / math.hypot(1.0, k)
    Nv = np.array([0.0, -Dv[2], Dv[1]])
    Lv = math.hypot(YB - ye, 3.55 - ze)

    def vplane(y, off):
        return np.array([0.0, y, ze + (y - ye) * k]) - Nv * off

    for x in np.arange(-W / 2 - 0.1, W / 2 + 0.11, 0.55):
        a = vplane(ye + 0.02, 0.085)
        b = vplane(YB - 0.01, 0.085)
        a[0] = b[0] = x
        hb.beam(M["wood"], a, b, Nv, 0.07, 0.11)
    c = vplane((ye + YB) / 2, 0.018)
    hb.obox(M["wood"], c, (1, 0, 0), Dv, W / 2 + 0.3, Lv / 2, 0.012)                 # plank deck
    f0 = vplane(ye, 0.06)
    hb.beam(M["wood_dark"], (-W / 2 - 0.32, f0[1] - 0.02, f0[2]), (W / 2 + 0.32, f0[1] - 0.02, f0[2]), (0, 0, 1), 0.04, 0.2)
    for xe in (-W / 2 - 0.32, W / 2 + 0.32):                                       # veranda barge boards
        a = vplane(ye - 0.02, 0.05)
        b = vplane(YB - 0.02, 0.05)
        a[0] = b[0] = xe
        hb.beam(M["wood_dark"], a, b, Nv, 0.05, 0.22)

    # main roof: deck, rafter tails, purlins, barge + fascia boards
    zb_e = WT + 0.06 - 0.5 * TAN
    yb_e = YK + 0.5
    Df = np.array([0.0, math.cos(PITCH), math.sin(PITCH)])
    Nf = np.array([0.0, -math.sin(PITCH), math.cos(PITCH)])
    Dk = np.array([0.0, -math.cos(PITCH), math.sin(PITCH)])
    Nk = np.array([0.0, math.sin(PITCH), math.cos(PITCH)])
    of = np.array([0.0, YB - 0.22, WT + 0.06 - 0.22 * TAN])   # front eave laps over the veranda roof
    ok = np.array([0.0, yb_e, zb_e])
    Lf = (RIDGE_Y - of[1]) / math.cos(PITCH)
    Lk = (ok[1] - RIDGE_Y) / math.cos(PITCH)
    zr_top = of[2] + Lf * math.sin(PITCH)
    for o, Dd, Nn, L in ((of, Df, Nf, Lf), (ok, Dk, Nk, Lk)):
        hb.obox(M["wood"], o + Dd * L / 2 - Nn * 0.018, (1, 0, 0), Dd, GX, L / 2, 0.012)
        for s in (0.25, 0.55, 0.85):
            p = o + Dd * L * s - Nn * 0.09
            hb.beam(M["wood_dark"], (-GX + 0.02, p[1], p[2]), (GX - 0.02, p[1], p[2]), Nn, 0.1, 0.12)
        for xe in (-GX - 0.02, GX + 0.02):
            a = o - Nn * 0.05
            b = o + Dd * (L + 0.06) - Nn * 0.05
            a[0] = b[0] = xe
            hb.beam(M["wood_dark"], a, b, Nn, 0.05, 0.24)
        if o is ok:                                   # fascia only on the back eave (front laps the veranda)
            a = o - Nn * 0.07 - Dd * 0.02
            hb.beam(M["wood_dark"], (-GX - 0.04, a[1], a[2]), (GX + 0.04, a[1], a[2]), Nn, 0.04, 0.2)
    for x in np.arange(-W / 2 + 0.1, W / 2, 0.6):
        a = ok + Dk * 0.0 - Nk * 0.085
        b = ok + Dk * 0.8 - Nk * 0.085
        a[0] = b[0] = x
        hb.beam(M["wood"], a + Dk * 0.02, b, Nk, 0.07, 0.11)
    obj_from(hb, "GEO_%s_Timber" % ASSET, "AST", parent=root)

    # ---------------- roof tiles (open surfaces: keep authored normals)
    hb = HB()
    tr = random.Random(5)
    common = dict(course=0.30, overlap=0.10, period=0.25, amp=0.055, lip=0.035, step_lift=0.035, dx=0.035, rng=tr)
    hb.corrugated(M["tile"], of + np.array([-GX, 0, 0]), (1, 0, 0), 2 * GX, Df, Lf + 0.02, Nf, **common)
    hb.corrugated(M["tile"], ok + np.array([-GX, 0, 0]), (1, 0, 0), 2 * GX, Dk, Lk + 0.02, Nk, **common)
    hb.corrugated(M["tile"], np.array([-W / 2 - 0.3, ye, ze]), (1, 0, 0), W + 0.6, Dv, Lv, Nv, **common)
    hb.ridge_caps(M["tile"], -GX - 0.05, GX + 0.05, RIDGE_Y, zr_top + 0.035, 0.15, rng=tr)
    obj_from(hb, "GEO_%s_Roof_Tiles" % ASSET, "AST", recalc=False, parent=root)

    # ---------------- kitchen annex (mud, tin roof)
    hb = HB()
    ax0, ax1, ay0, ay1 = W / 2 - 0.02, W / 2 + 2.6, 0.55, YK
    hb.box(ax0, ax1 + 0.15, ay0 - 0.15, ay1 + 0.15, -0.4, 0.3, M["mud"])
    hb.box(ax0, ax1, ay0, ay1, 0.3, 2.65, M["mud"])
    # sloped wall top so the tin roof sits on the walls (no gap under the roof)
    rz0, rz1 = 3.08, 2.62                     # roof underside at x = ax0 - 0.02 and x = ax1 + 0.4

    def zroof(x):
        return rz0 + (x - (ax0 - 0.02)) * (rz1 - rz0) / ((ax1 + 0.4) - (ax0 - 0.02)) - 0.04

    hb.add([(ax0, ay0, 2.64), (ax1, ay0, 2.64), (ax1, ay1, 2.64), (ax0, ay1, 2.64),
            (ax0, ay0, zroof(ax0)), (ax1, ay0, zroof(ax1)), (ax1, ay1, zroof(ax1)), (ax0, ay1, zroof(ax0))],
           [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], M["mud"])
    hb.box(ax0 + 0.9, ax0 + 1.72, ay0 - 0.06, ay0 + 0.02, 0.32, 2.1, M["wood_dark"])
    hb.box(ax0 + 0.85, ax0 + 1.77, ay0 - 0.08, ay0 + 0.02, 2.1, 2.2, M["wood_dark"])
    for i in range(5):
        x = ax0 + 0.93 + i * 0.16
        hb.box(x, x + 0.14, ay0 - 0.08, ay0 - 0.05, 0.34, 2.08, M["wood"])
    hb.box(ax1 - 0.02, ax1 + 0.02, 2.0, 2.55, 1.5, 1.9, M["dark"])
    hb.box(ax1 - 0.04, ax1 + 0.04, 1.97, 2.58, 1.45, 1.5, M["wood_dark"])
    hb.rod(M["tin"], (ax1 - 0.6, 3.6, 2.4), (ax1 - 0.6, 3.6, 3.85), 0.085, 10)
    hb.frustum(ax1 - 0.6, 3.6, 3.85, 4.1, 0.2, 0.0, 10, M["tin"])
    hb.beam(M["wood"], (ax1 + 0.25, ay0 - 0.3, 2.55), (ax1 + 0.25, ay1 + 0.35, 2.55), (0, 0, 1), 0.1, 0.12)
    # firewood stack
    lr = random.Random(9)
    for row in range(4):
        for i in range(6 - row):
            r = lr.uniform(0.055, 0.085)
            x = ax1 + 0.45 + i * 0.17 + row * 0.085
            z = 0.07 + row * 0.14
            hb.rod(M["bark"], (x, 1.3 + lr.uniform(-0.1, 0.1), z), (x, 2.9 + lr.uniform(-0.1, 0.1), z), r, 7)
    obj_from(hb, "GEO_%s_Annex_Kitchen" % ASSET, "AST", parent=root)
    hb = HB()
    te = np.array([ax1 + 0.4, ay0 - 0.35, 2.62])
    tt = np.array([ax0 - 0.02, ay0 - 0.35, 3.08])
    Dt = (tt - te) / np.linalg.norm(tt - te)
    Nt = np.array([-Dt[2], 0.0, Dt[0]])
    if Nt[2] < 0:
        Nt = -Nt
    hb.corrugated(M["tin"], te, (0, 1, 0), (ay1 + 0.35) - (ay0 - 0.35), Dt, float(np.linalg.norm(tt - te)), Nt,
                  course=10.0, overlap=0.0, period=0.076, amp=0.022, profile="sin", lip=0.012, step_lift=0.012,
                  dx=0.0095, rng=None)
    obj_from(hb, "GEO_%s_Annex_TinRoof" % ASSET, "AST", recalc=False, parent=root)

    # ---------------- lived-in details
    hb = HB()
    # charpai leaning on the front wall
    ch = HB()
    for xx in (0.05, 1.85):
        for yy in (-0.38, 0.38):
            ch.frustum(xx, yy, 0.0, 0.44, 0.045, 0.04, 8, M["wood"])
    for yy in (-0.4, 0.4):
        ch.box(0.0, 1.9, yy - 0.03, yy + 0.03, 0.36, 0.44, M["wood"])
    for xx in (0.02, 1.88):
        ch.box(xx - 0.03, xx + 0.03, -0.4, 0.4, 0.36, 0.44, M["wood"])
    ch.box(0.06, 1.84, -0.37, 0.37, 0.395, 0.405, M["rope"])
    Mc = (Matrix.Translation(Vector((4.4, YB - 0.46, PH + 0.03))) @ Matrix.Rotation(math.radians(-12), 4, "X")
          @ Matrix.Rotation(math.radians(90), 4, "Z") @ Matrix.Rotation(math.radians(-90), 4, "Y"))
    hb.merge(ch, Mc)
    # hanging bulb, meter box, wire, nameplate
    hb.rod(M["iron"], (0.6, POST_Y, 2.72), (0.6, POST_Y, 2.5), 0.006, 6)
    hb.frustum(0.6, POST_Y, 2.42, 2.5, 0.025, 0.025, 10, M["iron"])
    hb.ellipsoid(0.6, POST_Y, 2.37, 0.045, 0.045, 0.06, M["bulb"], 12, 8)
    hb.box(1.55, 1.85, YB - 0.12, YB, 2.0, 2.4, M["meter"])
    hb.rod(M["iron"], (1.7, YB - 0.06, 2.4), (1.7, YB - 0.06, 3.45), 0.007, 6)
    hb.box(-0.6, -0.18, YB - 0.025, YB, 1.85, 2.08, M["plate"])
    # mango-leaf toran above the door
    tz = PH + 2.25 + 0.2
    hb.rod(M["rope"], (-0.15, YB - 0.05, tz), (1.35, YB - 0.05, tz), 0.006, 5)
    for i in range(11):
        x = -0.1 + i * 0.14
        hb.ellipsoid(x, YB - 0.06, tz - 0.09, 0.028, 0.008, 0.08, M["mango_leaf"], 6, 4)
    # tulsi chaura in the front yard
    cx, cy = -2.7, YF - 2.6
    hb.box(cx - 0.42, cx + 0.42, cy - 0.42, cy + 0.42, -0.1, 0.12, M["chaura"])
    hb.box(cx - 0.32, cx + 0.32, cy - 0.32, cy + 0.32, 0.12, 0.85, M["chaura"])
    hb.box(cx - 0.38, cx + 0.38, cy - 0.38, cy + 0.38, 0.85, 0.93, M["chaura"])
    hb.box(cx - 0.11, cx + 0.11, cy - 0.33, cy - 0.31, 0.35, 0.6, M["dark"])            # diya niche
    hb.box(cx - 0.26, cx + 0.26, cy - 0.26, cy + 0.26, 0.9, 0.95, M["mud"])
    pr = random.Random(3)
    for i in range(9):
        a = pr.uniform(0, 2 * math.pi)
        r = pr.uniform(0.0, 0.14)
        hb.rod(M["wood_dark"], (cx, cy, 0.94), (cx + r * math.cos(a), cy + r * math.sin(a), 1.25 + pr.uniform(0, 0.15)),
               0.008, 5)
    obj_from(hb, "PRP_%s_Details" % ASSET, "AST", parent=root)
    # tulsi foliage: real leaf instances (v002, replaces the blob placeholder)
    src_c = coll("SRC_HOUSE_LEAVES")
    bpy.context.view_layer.layer_collection.children["SRC_HOUSE_LEAVES"].exclude = True
    lb = HB()
    lb.add([(0, 0, 0), (0.013, 0.022, 0.005), (0, 0.055, 0), (-0.013, 0.022, 0.005)], [(0, 1, 2, 3)], M["leaf"])
    leaf_o = bpy.data.objects.new("SRC_Leaf_Tulsi_House", lb.to_mesh("ME_SRC_Leaf_Tulsi_House", recalc=False))
    src_c.objects.link(leaf_o)
    P, R, S = [], [], []
    while len(P) < 1400:
        u = np.array([pr.uniform(-1, 1), pr.uniform(-1, 1), pr.uniform(-1, 1)])
        if not 0.2 < np.linalg.norm(u) <= 1.0 or u[2] < -0.7:
            continue
        P.append((cx + u[0] * 0.24, cy + u[1] * 0.24, 1.3 + u[2] * 0.26))
        R.append((pr.uniform(-1.2, 1.2), pr.uniform(-1.2, 1.2), pr.uniform(0, 6.28)))
        S.append(pr.uniform(0.8, 1.3))
    lo = H.points_object("FOL_%s_Tulsi" % ASSET, P, R, S, COLL["AST"], H.instancer("GN_House_Tulsi", leaf_o))
    lo.parent = root

    # clay matkas on the veranda (open-top lathe meshes)
    hb = HB()
    prof = [(0.0, 0.0), (0.1, 0.005), (0.19, 0.06), (0.235, 0.17), (0.225, 0.29), (0.16, 0.38), (0.095, 0.425),
            (0.09, 0.45), (0.11, 0.475), (0.105, 0.485)]
    for (x, y, s) in ((-4.45, YB - 0.45, 1.0), (-3.95, YB - 0.4, 0.82), (-4.2, YB - 0.95, 0.7)):
        hb.lathe(M["clay"], [(r * s, z * s) for r, z in prof], 24, x, y, PH + 0.03)
    mk = obj_from(hb, "PRP_%s_Matkas" % ASSET, "AST", recalc=False, parent=root)
    mk.data.polygons.foreach_set("use_smooth", [True] * len(mk.data.polygons))

    # mud-plastered front yard (lipai)
    hb = HB()
    n = 40
    v = [(0.4, YF - 2.6, 0.012)]
    for i in range(n):
        a = 2 * math.pi * i / n
        r = 4.4 + 0.45 * math.sin(a * 3 + 0.5) + 0.25 * math.sin(a * 7 + 1.3)
        v.append((0.4 + r * math.cos(a) * 1.25, YF - 2.6 + r * math.sin(a) * 0.62, 0.012))
    hb.add(v, [(0, 1 + i, 1 + (i + 1) % n) for i in range(n)], M["lipai"])
    obj_from(hb, "GEO_%s_Yard_Lipai" % ASSET, "AST", recalc=False, parent=root)


# ============================================================================
def build_stage(M):
    hb = HB()
    hb.add([(-400, -400, 0), (400, -400, 0), (400, 400, 0), (-400, 400, 0)], [(0, 1, 2, 3)], M["ground"])
    obj_from(hb, "STG_Ground", "STAGE", recalc=False)
    hb = HB()
    tr = random.Random(12)
    for (x, y, s) in ((-11, 9, 1.2), (12, 11, 1.0), (-16, -2, 0.9), (17, -6, 1.1), (3, 17, 1.3), (-7, 19, 1.0)):
        hb.frustum(x, y, 0, 3.2 * s, 0.32 * s, 0.24 * s, 10, M["bark"])
        for _ in range(4):
            hb.ellipsoid(x + tr.uniform(-1.6, 1.6) * s, y + tr.uniform(-1.6, 1.6) * s, (5.2 + tr.uniform(-0.6, 1.2)) * s,
                         tr.uniform(2.2, 3.2) * s, tr.uniform(2.2, 3.2) * s, tr.uniform(1.8, 2.4) * s, M["tree"], 16, 10)
    obj_from(hb, "STG_Trees_Context", "STAGE")

    w = bpy.data.worlds.new("WLD_Day_Clear")
    bpy.context.scene.world = w
    t = H.NT(w)
    tc = t.n("ShaderNodeTexCoord")
    z = t.n("ShaderNodeSeparateXYZ", Vector=tc.outputs["Generated"]).outputs["Z"]
    col = t.ramp(z, [(0.0, H.hex_lin("#F2DCB8")), (0.12, H.hex_lin("#B9D2E6")), (0.45, H.hex_lin("#5E93CC"))])
    bg = t.n("ShaderNodeBackground", Color=col, Strength=1.0)
    o = t.n("ShaderNodeOutputWorld")
    t.link(bg.outputs[0], o.inputs["Surface"])

    sd = bpy.data.lights.new("LGT_Sun_Afternoon", "SUN")
    sd.energy = 4.5
    sd.color = (1.0, 0.9, 0.77)
    sd.angle = math.radians(1.5)
    sun = bpy.data.objects.new("LGT_Sun_Afternoon", sd)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(-38))
    COLL["STAGE"].objects.link(sun)

    cams = {
        "CAM_Hero_Front34":   ((-10.5, -15.0, 1.7), (0.6, -0.6, 2.3), 32, None),
        "CAM_Hero_Front":     ((0.6, -19.0, 1.65), (0.6, 0.0, 2.6), 38, None),
        "CAM_Hero_SideRight": ((16.0, -4.0, 1.9), (3.0, 1.0, 2.4), 32, None),
        "CAM_Hero_Back34":    ((10.0, 15.5, 2.2), (0.0, 1.0, 2.5), 32, None),
        "CAM_Hero_Aerial34":  ((-13.0, -14.0, 11.0), (0.5, 0.5, 2.6), 35, None),
        "CAM_Hero_Close_Door": ((-0.9, -7.6, 1.55), (0.45, YB, 1.75), 45, 6.0),
        "CAM_Hero_Close_Eave": ((-6.7, -6.4, 1.45), (-4.6, -3.9, 2.95), 30, 3.4),
    }
    for name, (pos, tgt, lens, focus) in cams.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 2000
        if focus:
            cd.dof.use_dof = True
            cd.dof.focus_distance = focus
            cd.dof.aperture_fstop = 4.0
        co = bpy.data.objects.new(name, cd)
        co.location = pos
        co.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        COLL["STAGE"].objects.link(co)
    bpy.context.scene.camera = bpy.data.objects["CAM_Hero_Front34"]
    return list(cams)


def setup_render(quick):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception as e:
        print("[hero] GPU setup failed, using CPU:", e)
    sc.cycles.samples = 64 if quick else 256
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPTIX"
    except Exception:
        pass
    sc.cycles.max_bounces = 6
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = (1280, 720) if quick else (1920, 1080)
    sc.render.image_settings.file_format = "PNG"


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "HERO_" + ASSET
    sc.unit_settings.system = "METRIC"
    coll("AST")
    COLL["AST"].name = "AST_" + ASSET
    coll("AST_CUTTERS", COLL["AST"])
    coll("STAGE")
    M = materials()
    root = bpy.data.objects.new("ASSET_" + ASSET, None)
    root.empty_display_type = "ARROWS"
    root["asset_family"] = "house_common"
    root["footprint_m"] = "%.1f x %.1f" % (W, D)
    root["version"] = VERSION
    root["status"] = "hero benchmark - awaiting approval"
    COLL["AST"].objects.link(root)
    build_house(M, root)
    cams = build_stage(M)
    setup_render("--quick" in ARGS)
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "HERO_%s_%s.blend" % (ASSET, stamp)))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    nv = sum(len(o.data.vertices) for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("GEO", "PRP")))
    print("[hero] saved %s  (%d asset verts before modifiers)" % (OUT_BLEND, nv))
    if "--render" in ARGS:
        os.makedirs(OUT_REVIEW, exist_ok=True)
        only = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None
        for c in cams:
            if only and c != only:
                continue
            sc.camera = bpy.data.objects[c]
            sc.render.filepath = os.path.join(OUT_REVIEW, c + ".png")
            bpy.ops.render.render(write_still=True)
            print("[hero] rendered", c)


main()
