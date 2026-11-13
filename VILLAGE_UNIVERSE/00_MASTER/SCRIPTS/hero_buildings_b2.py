"""
BATCH 2 - building library: one hero design per family, each with a camera-ready interior.

  blender -b --factory-startup --python hero_buildings_b2.py -- [--only AST_A,AST_B]

Output: 02_ARCHITECTURE/LIB_Buildings_B2.blend
  AST_House_Middle_A      2-storey pucca house (14 x 14 plot): porch + balcony, boundary wall + iron gate, roof tank,
                          dish, clothesline.  Interior: living room, kitchen, upstairs bedroom.
  AST_Haveli_A            courtyard haveli (22 x 20): arched gate with carved doors, jharokhas, chhatris, two-storey
                          arcade round the aangan.  Interior: courtyard with tulsi, swing, diwan with masnads.
  AST_Shop_Kirana_A / AST_Shop_Chai_A / AST_Shop_Cloth_A   single shops (5 x 7) with shutters, awnings, signs, goods
  AST_Shop2_Hardware_A    2-storey shop (6 x 8): shop below, home above with balcony
  AST_Temple_Shiv_A       nagara shikhara temple on a jagati, pillared mandapa, nandi, bell, compound wall (24 x 24)
                          Interior: shivling, diyas, flowers.
  AST_School_A            U-shaped government primary school (40 x 34), verandahs, flag, gate board.
                          Interior: one full classroom (desks, blackboard, teacher table, fan).
  AST_Panchayat_A         Gram Panchayat Bhavan (18 x 11), arched verandah, board, notice board, flag.
                          Interior: meeting hall with table, chairs, durrie, cupboard.
Origins: footprint centre at ground, front faces -Y.  Night lights stored as collection["night_lights"].
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

import arch_kit as K  # noqa: E402
import char_lib as CL  # noqa: E402
import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "02_ARCHITECTURE", "LIB_Buildings_B2.blend")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LIB = None


def new_asset(name):
    c = bpy.data.collections.new(name)
    LIB.children.link(c)
    return c


# ============================================================================ middle-class house
def house_middle(M):
    c = new_asset("AST_House_Middle_A")
    rng = random.Random(3)
    lights = []
    hb = HB()
    PH, F1, F2 = 0.45, 3.6, 6.75
    x0, x1, y0, y1, T = -5.0, 5.0, -2.5, 6.5, 0.23
    hb.box(-7.0, 7.0, -7.0, 7.0, -0.2, 0.05, M["concrete"])                                 # plot paving / yard
    hb.box(x0 - 0.2, x1 + 0.2, y0 - 1.8, y1 + 0.2, 0.05, PH, M["stone"])                     # plinth + porch
    # ground floor walls
    K.wall_x(hb, M["plaster"], x0, x1, y0, y0 + T, PH, F1 - 0.15, [(-0.6, 0.6, PH, PH + 2.15), (-3.6, -2.4, PH + 0.9, PH + 2.1),
                                                                 (2.4, 3.6, PH + 0.9, PH + 2.1)])
    K.wall_x(hb, M["plaster"], x0, x1, y1 - T, y1, PH, F1 - 0.15, [(-1.0, 0.2, PH + 0.9, PH + 2.1), (2.4, 3.4, PH + 0.9, PH + 2.1)])
    K.wall_y(hb, M["plaster"], x0, x0 + T, y0 + T, y1 - T, PH, F1 - 0.15, [(1.5, 2.7, PH + 0.9, PH + 2.1)])
    K.wall_y(hb, M["plaster"], x1 - T, x1, y0 + T, y1 - T, PH, F1 - 0.15, [(1.5, 2.7, PH + 0.9, PH + 2.1)])
    K.wall_y(hb, M["plaster_in"], 0.9, 1.05, y0 + T, y1 - T, PH, F1 - 0.15, [(0.5, 1.5, PH, PH + 2.1)])   # partition
    hb.box(x0, x1, y0, y1, F1 - 0.15, F1, M["concrete"])                                      # first-floor slab
    hb.box(-3.6, 3.6, y0 - 1.6, y0, F1 - 0.15, F1, M["concrete"])                             # porch roof = balcony floor
    # first floor (set back slightly at the rear)
    K.wall_x(hb, M["plaster"], x0, x1, y0, y0 + T, F1, F2 - 0.15, [(-0.55, 0.55, F1, F1 + 2.1), (-3.6, -2.4, F1 + 0.9, F1 + 2.1),
                                                                 (2.4, 3.6, F1 + 0.9, F1 + 2.1)])
    K.wall_x(hb, M["plaster"], x0, x1, y1 - T, y1, F1, F2 - 0.15, [(-1.0, 0.2, F1 + 0.9, F1 + 2.1)])
    K.wall_y(hb, M["plaster"], x0, x0 + T, y0 + T, y1 - T, F1, F2 - 0.15, [(2.0, 3.2, F1 + 0.9, F1 + 2.1)])
    K.wall_y(hb, M["plaster"], x1 - T, x1, y0 + T, y1 - T, F1, F2 - 0.15, [(2.0, 3.2, F1 + 0.9, F1 + 2.1)])
    hb.box(x0 - 0.15, x1 + 0.15, y0 - 0.15, y1 + 0.15, F2 - 0.15, F2, M["concrete"])            # roof slab
    K.parapet(hb, M["plaster"], x0 - 0.15, x1 + 0.15, y0 - 0.15, y1 + 0.15, F2, 0.9, 0.15, M["concrete"])
    hb.box(x0 - 0.1, x1 + 0.1, y0 - 0.1, y0, F1 - 0.35, F1 - 0.15, M["white"])                # floor band
    K.put(hb, "GEO_HouseMiddle_Shell", c)
    hb = HB()
    for cx in (-3.4, 3.4):                                                                      # porch columns
        K.column(hb, M, cx, y0 - 1.45, PH, F1 - 0.15, 0.13, "square", M["white"])
    for k in range(3):
        hb.box(-1.0, 1.0, y0 - 1.8 - (3 - k) * 0.3, y0 - 1.8 - (2 - k) * 0.3, 0.05, 0.05 + (k + 1) * 0.135, M["stone"])
    K.railing(hb, M["grill"], (-3.55, y0 - 1.55), (3.55, y0 - 1.55), F1)
    K.railing(hb, M["grill"], (-3.55, y0 - 1.55), (-3.55, y0), F1)
    K.railing(hb, M["grill"], (3.55, y0 - 1.55), (3.55, y0), F1)
    K.door(hb, M, 0.0, y0, PH, 1.2, 2.15, T, -1, "teal", 0.35, carved=True)
    K.door(hb, M, 0.0, y0, F1, 1.1, 2.1, T, -1, "teal", 0.0)
    for fz in (PH, F1):
        for wx in (-3.0, 3.0):
            K.window(hb, M, wx, y0, fz + 0.9, 1.2, 1.2, T, -1, "teal")
        K.window(hb, M, -0.4, y1, fz + 0.9, 1.2, 1.2, T, 1, "teal")
        for sx, xw in ((-1, x0), (1, x1)):
            K.window(hb, M, 2.1 if fz == PH else 2.6, xw, fz + 0.9, 1.2, 1.2, T, sx, "teal", axis="y")
    K.put(hb, "GEO_HouseMiddle_Openings", c)
    # boundary wall + iron gate + yard dressing
    hb = HB()
    for (ax0, ax1, ay0, ay1) in ((-7.0, -1.4, -7.0, -6.8), (1.4, 7.0, -7.0, -6.8), (-7.0, -6.8, -6.8, 7.0), (6.8, 7.0, -6.8, 7.0),
                                 (-7.0, 7.0, 6.8, 7.0)):
        hb.box(ax0, ax1, ay0, ay1, 0.05, 1.3, M["plaster"])
        hb.box(ax0 - 0.03, ax1 + 0.03, ay0 - 0.03, ay1 + 0.03, 1.3, 1.36, M["concrete"])
    for gx in (-1.4, 1.4):
        hb.box(gx - 0.2, gx + 0.2, -7.1, -6.7, 0.05, 1.7, M["plaster"])
        hb.frustum(gx, -6.9, 1.7, 1.95, 0.22, 0.05, 4, M["concrete"], rot=math.pi / 4)
    for s in (-1, 1):                                                                          # half-open iron gate
        g = HB()
        g.box(0, 1.35, -0.025, 0.025, 0.1, 0.16, M["grill"])
        g.box(0, 1.35, -0.025, 0.025, 1.36, 1.42, M["grill"])
        for k in range(12):
            g.rod(M["grill"], (0.06 + k * 0.11, 0, 0.1), (0.06 + k * 0.11, 0, 1.55 if k % 3 == 0 else 1.42), 0.012, 5)
        from mathutils import Matrix
        hb.merge(g, Matrix.Translation((s * 1.2, -6.9, 0.0)) @ Matrix.Rotation(math.radians(-60 if s > 0 else 240), 4, "Z"))
    for k, (px, py) in enumerate(((-5.8, -5.8), (5.8, -5.8), (-2.2, y0 - 2.4))):
        hb.lathe(M["terracotta"], [(0.0, 0.0), (0.18, 0.0), (0.25, 0.35), (0.28, 0.4)], 16, px, py, 0.05)
        for j in range(40):
            hb.ellipsoid(px + rng.uniform(-0.2, 0.2), py + rng.uniform(-0.2, 0.2), 0.45 + rng.uniform(0, 0.4), 0.06, 0.04, 0.02, M["leaf"], 6, 3)
    K.water_tank(hb, M, 3.5, 5.0, F2)
    hb.rod(M["iron"], (-3.8, 5.6, F2), (-3.8, 5.6, F2 + 1.2), 0.02, 6)                           # dish antenna
    hb.lathe(M["steel"], [(0.0, 0.0), (0.28, 0.06), (0.35, 0.14)], 16, -3.8, 5.5, F2 + 1.0)
    for x in (-4.5, 1.5):                                                                       # rooftop clothesline
        hb.rod(M["iron"], (x, 1.0, F2), (x, 1.0, F2 + 1.6), 0.02, 5)
    hb.rod(M["iron"], (-4.5, 1.0, F2 + 1.5), (1.5, 1.0, F2 + 1.5), 0.006, 4)
    for k, mat in enumerate((M["cloth_red"], M["cloth_blue"], M["bedsheet"], M["cloth_green"])):
        x = -4.0 + k * 1.3
        hb.add([(x, 1.0, F2 + 1.5), (x + 0.9, 1.0, F2 + 1.5), (x + 0.88, 1.02, F2 + 0.75), (x + 0.02, 1.0, F2 + 0.8)], [(0, 1, 2, 3)], mat)
    hb.box(-6.4, -5.2, 3.0, 6.4, 0.05, 0.1, M["concrete"])                                     # parked-bike pad
    K.put(hb, "GEO_HouseMiddle_Yard", c)
    # interior
    hb = HB()
    K.durrie(hb, M, -4.2, -0.6, 0.0, 3.6, PH + 0.005)
    K.sofa(hb, M, -2.4, 5.6, PH, math.pi)
    K.tv_unit(hb, M, -2.4, -2.05, PH)
    K.table(hb, M, -2.4, 1.8, PH, 0.0, 1.0, 0.55, 0.42)
    K.ceiling_fan(hb, M, -2.4, 1.8, F1 - 0.15)
    K.kitchen(hb, M, 3.2, 6.0, PH, math.pi, 3.0)
    K.table(hb, M, 3.0, 2.2, PH, 0.0, 1.3, 0.8)
    for cx, cy, rz in ((2.5, 1.5, 0), (3.5, 1.5, 0), (2.5, 2.9, math.pi), (3.5, 2.9, math.pi)):
        K.chair(hb, M, cx, cy, PH, rz)
    K.bed(hb, M, -2.5, 4.4, F1, math.pi)
    K.almirah(hb, M, 3.8, 5.9, F1, math.pi)
    K.ceiling_fan(hb, M, -1.0, 2.5, F2 - 0.15)
    K.put(hb, "GEO_HouseMiddle_Interior", c)
    lights += [(-2.4, 1.8, F1 - 0.5, 40), (3.0, 3.0, F1 - 0.4, 40), (0.0, y0 - 1.0, F1 - 0.4, 35), (-1.0, 2.5, F2 - 0.5, 35),
               (0.0, y0 - 0.9, F2 - 0.3, 30), (1.4, -6.9, 1.9, 20)]
    c["night_lights"] = [list(map(float, l)) for l in lights]
    return c


# ============================================================================ haveli
def haveli(M):
    c = new_asset("AST_Haveli_A")
    lights = []
    rng = random.Random(9)
    PH, F1, F2 = 0.6, 4.4, 8.2
    X, Y, T = 10.0, 9.0, 0.45
    cx, cy = 4.6, 3.6                                                                          # courtyard half-size
    sand, carved = M["sandstone"], M["sand_smooth"]
    hb = HB()
    hb.box(-X - 0.4, X + 0.4, -Y - 0.4, Y + 0.4, -0.2, PH, M["stone"])
    for (zz0, zz1, fl) in ((PH, F1, 0), (F1 + 0.2, F2, 1)):
        holes_front = [(-1.6, 1.6, zz0, zz0 + (3.5 if fl == 0 else 0.0))] if fl == 0 else []
        for wx in (-7.5, -4.5, 4.5, 7.5):
            holes_front.append((wx - 0.55, wx + 0.55, zz0 + 1.0, zz0 + 2.6))
        K.wall_x(hb, sand, -X, X, -Y, -Y + T, zz0, zz1, holes_front)
        K.wall_x(hb, sand, -X, X, Y - T, Y, zz0, zz1, [(wx - 0.5, wx + 0.5, zz0 + 1.1, zz0 + 2.5) for wx in (-6, 0, 6)])
        K.wall_y(hb, sand, -X, -X + T, -Y + T, Y - T, zz0, zz1, [(wy - 0.5, wy + 0.5, zz0 + 1.1, zz0 + 2.5) for wy in (-4, 4)])
        K.wall_y(hb, sand, X - T, X, -Y + T, Y - T, zz0, zz1, [(wy - 0.5, wy + 0.5, zz0 + 1.1, zz0 + 2.5) for wy in (-4, 4)])
        hb.box(-X, X, -Y, Y, zz1 - 0.0, zz1 + 0.2, carved) if fl == 0 else None
    # floors round the courtyard (ring slabs) and roof
    for z in (F1, F2):
        hb.box(-X, X, -Y, -cy - 1.6, z, z + 0.2, carved)
        hb.box(-X, X, cy + 1.6, Y, z, z + 0.2, carved)
        hb.box(-X, -cx - 1.6, -cy - 1.6, cy + 1.6, z, z + 0.2, carved)
        hb.box(cx + 1.6, X, -cy - 1.6, cy + 1.6, z, z + 0.2, carved)
        hb.box(-cx - 1.6, cx + 1.6, -cy - 1.6, -cy, z, z + 0.2, carved)
        hb.box(-cx - 1.6, cx + 1.6, cy, cy + 1.6, z, z + 0.2, carved)
        hb.box(-cx - 1.6, -cx, -cy, cy, z, z + 0.2, carved)
        hb.box(cx, cx + 1.6, -cy, cy, z, z + 0.2, carved)
    # crenellated parapet with merlons
    K.parapet(hb, sand, -X, X, -Y, Y, F2 + 0.2, 0.7, 0.3, carved)
    for k in range(int(2 * X / 0.9)):
        x = -X + 0.3 + k * 0.9
        hb.box(x, x + 0.45, -Y, -Y + 0.3, F2 + 0.95, F2 + 1.25, carved)
        hb.box(x, x + 0.45, Y - 0.3, Y, F2 + 0.95, F2 + 1.25, carved)
    K.parapet(hb, carved, -cx, cx, -cy, cy, F2 + 0.2, 0.7, 0.2)
    hb.box(-cx, cx, -cy, cy, PH - 0.02, PH, M["kota"])                                         # courtyard floor
    hb.box(-X + T, X - T, -Y + T, Y - T, PH - 0.01, PH, M["kota"])
    K.put(hb, "GEO_Haveli_Shell", c)
    # arcade round the courtyard (both floors) + gallery railings
    hb = HB()
    for z0, z1 in ((PH, F1), (F1 + 0.2, F2)):
        xs = np.linspace(-cx, cx, 5)
        ys = np.linspace(-cy, cy, 4)
        for x in xs:
            for y in (-cy, cy):
                K.column(hb, M, x, y, z0, z1 - 0.7, 0.17, "round", carved)
        for y in ys[1:-1]:
            for x in (-cx, cx):
                K.column(hb, M, x, y, z0, z1 - 0.7, 0.17, "round", carved)
        for i in range(len(xs) - 1):
            for y in (-cy, cy):
                K.arch_band(hb, carved, xs[i] + 0.2, xs[i + 1] - 0.2, y - 0.15, y + 0.15, z1 - 1.4, 0.7, z1, 12, "x")
        for i in range(len(ys) - 1):
            for x in (-cx, cx):
                K.arch_band(hb, carved, ys[i] + 0.2, ys[i + 1] - 0.2, x - 0.15, x + 0.15, z1 - 1.4, 0.7, z1, 12, "y")
    for (p0, p1) in (((-cx, -cy), (cx, -cy)), ((cx, -cy), (cx, cy)), ((cx, cy), (-cx, cy)), ((-cx, cy), (-cx, -cy))):
        K.railing(hb, M["iron"], p0, p1, F1 + 0.2, 0.85, 0.15)
    K.put(hb, "GEO_Haveli_Arcade", c)
    # facade: arched gate (pol) with carved doors, jharokhas, chhatris, frieze
    hb = HB()
    K.arch_band(hb, carved, -1.6, 1.6, -Y - 0.25, -Y + T, PH + 3.5, 1.6, F1, 16, "x")
    for gx in (-1.95, 1.95):
        hb.box(gx - 0.35, gx + 0.35, -Y - 0.4, -Y + T, PH, F1 + 0.4, carved)
    K.door(hb, M, 0.0, -Y + 0.2, PH, 3.0, 3.4, 0.2, -1, "wood_dark", 0.55, carved=True)
    for wx in (-7.5, -4.5, 4.5, 7.5):
        for fz in (PH, F1 + 0.2):
            K.arch_band(hb, carved, wx - 0.55, wx + 0.55, -Y - 0.06, -Y + 0.02, fz + 2.6, 0.45, fz + 3.15, 8, "x")
            hb.box(wx - 0.55, wx + 0.55, -Y + 0.15, -Y + 0.2, fz + 1.0, fz + 2.6, M["wood_dark"])
    for jx in (-6.0, 6.0):                                                                    # jharokhas
        jz = F1 + 0.6
        hb.box(jx - 1.1, jx + 1.1, -Y - 0.9, -Y, jz - 0.15, jz, carved)
        for k in range(5):
            hb.box(jx - 1.0 + k * 0.48, jx - 0.9 + k * 0.48, -Y - 1.0, -Y - 0.9, jz - 0.9 + 0.1 * (k % 2), jz, carved)  # brackets
        for sx in (-1, 1):
            K.column(hb, M, jx + sx * 0.95, -Y - 0.75, jz, jz + 2.0, 0.07, "round", carved)
        hb.box(jx - 1.05, jx + 1.05, -Y - 0.9, -Y - 0.85, jz, jz + 0.75, carved)                     # jaali parapet
        hb.box(jx - 1.25, jx + 1.25, -Y - 1.1, -Y, jz + 2.0, jz + 2.15, carved)
        hb.lathe(carved, [(0.0, 0.0), (0.95, 0.0), (0.9, 0.3), (0.65, 0.65), (0.3, 0.85), (0.08, 0.95), (0.0, 1.05)], 20, jx, -Y - 0.5, jz + 2.15)
        lights.append((jx, -Y - 0.5, jz + 1.2, 30))
    for (hx, hy) in ((-X + 0.9, -Y + 0.9), (X - 0.9, -Y + 0.9), (-X + 0.9, Y - 0.9), (X - 0.9, Y - 0.9)):   # roof chhatris
        hz = F2 + 0.2
        hb.box(hx - 0.9, hx + 0.9, hy - 0.9, hy + 0.9, hz, hz + 0.25, carved)
        for sx in (-1, 1):
            for sy in (-1, 1):
                K.column(hb, M, hx + sx * 0.7, hy + sy * 0.7, hz + 0.25, hz + 2.0, 0.06, "round", carved)
        hb.box(hx - 1.0, hx + 1.0, hy - 1.0, hy + 1.0, hz + 2.0, hz + 2.15, carved)
        hb.lathe(carved, [(0.0, 0.0), (0.85, 0.0), (0.8, 0.3), (0.55, 0.62), (0.25, 0.8), (0.07, 0.9), (0.0, 1.1)], 20, hx, hy, hz + 2.15)
    hb.box(-X - 0.05, X + 0.05, -Y - 0.06, -Y, F1 - 0.2, F1 + 0.25, M["saffron"])                  # painted frieze band
    K.put(hb, "GEO_Haveli_Facade", c)
    # courtyard life: tulsi chaura, swing, diwan with masnads, brass pots
    hb = HB()
    hb.box(-0.5, 0.5, -0.5, 0.5, PH, PH + 0.8, M["white"])
    hb.box(-0.55, 0.55, -0.55, 0.55, PH + 0.8, PH + 0.88, M["saffron"])
    for j in range(80):
        hb.ellipsoid(rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), PH + 1.0 + rng.uniform(0, 0.5), 0.05, 0.03, 0.015, M["leaf"], 6, 3)
    sw_x, sw_y = 0.0, cy + 0.8                                                                     # jhoola in the back gallery
    for sx in (-0.8, 0.8):
        hb.rod(M["iron"], (sw_x + sx, sw_y, F1), (sw_x + sx, sw_y, PH + 0.6), 0.012, 5)
    hb.box(sw_x - 0.95, sw_x + 0.95, sw_y - 0.35, sw_y + 0.35, PH + 0.5, PH + 0.6, M["wood_dark"])
    K.durrie(hb, M, -X + 1.0, -cx - 1.8, -2.5, 2.5, PH + 0.005)
    for k in range(4):
        hb.ellipsoid(-X + 1.5 + k * 0.8, 2.3, PH + 0.25, 0.32, 0.18, 0.2, M["fabric"], 12, 6)
    for k, (px, py) in enumerate(((cx - 0.5, -cy + 0.5), (cx - 1.0, -cy + 0.5), (-cx + 0.5, cy - 0.5))):
        hb.lathe(M["brass"], [(0.0, 0.0), (0.14, 0.0), (0.22, 0.15), (0.2, 0.3), (0.08, 0.42), (0.1, 0.46)], 16, px, py, PH)
    K.ceiling_fan(hb, M, -X + 2.5, 0.0, F1)
    K.put(hb, "GEO_Haveli_Interior", c)
    lights += [(0.0, 0.0, F1 - 0.5, 60), (0.0, -Y - 0.8, PH + 3.8, 50), (-X + 2.5, 0.0, F1 - 0.6, 35), (0.0, cy + 0.8, F2 - 0.6, 30),
               (-cx, -cy, F1 - 0.8, 25), (cx, cy, F1 - 0.8, 25)]
    c["night_lights"] = [list(map(float, l)) for l in lights]
    return c


# ============================================================================ shops
SHOPS = {
    "Kirana": dict(text="SHARMA KIRANA STORE", paint="#8DB2C8", awning="cloth_red", sign=("sign_bg", "sign_txt")),
    "Chai": dict(text="GUPTA CHAI & NASHTA", paint="#E3C47D", awning="cloth_green", sign=("sign_bg2", "sign_txt2")),
    "Cloth": dict(text="LAXMI CLOTH HOUSE", paint="#D9A6A0", awning="cloth_blue", sign=("sign_bg", "sign_txt")),
}


def shop(M, kind):
    spec = SHOPS[kind]
    c = new_asset("AST_Shop_%s_A" % kind)
    rng = random.Random(len(kind))
    Mp = dict(M)
    Mp["plaster"] = H.mat_plaster("MAT_Wall_Plaster_%s" % spec["paint"][1:], spec["paint"], band="#5A4A3A", band_top=0.5)
    PH, TOP = 0.45, 3.6
    x0, x1, y0, y1, T = -2.4, 2.4, -3.0, 3.4, 0.23
    hb = HB()
    hb.box(x0 - 0.1, x1 + 0.1, -3.5, y1 + 0.1, -0.2, PH, M["stone"])
    K.wall_x(hb, Mp["plaster"], x0, x1, y0, y0 + T, PH, TOP, [(-2.05, 2.05, PH, PH + 2.6)])
    hb.box(x0, x1, y1 - T, y1, PH, TOP, Mp["plaster"])
    hb.box(x0, x0 + T, y0 + T, y1 - T, PH, TOP, Mp["plaster"])
    hb.box(x1 - T, x1, y0 + T, y1 - T, PH, TOP, Mp["plaster"])
    hb.box(x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, TOP, TOP + 0.15, M["concrete"])
    K.parapet(hb, Mp["plaster"], x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, TOP + 0.15, 0.6, 0.12, M["concrete"])
    hb.box(-2.05, 2.05, y0 - 0.05, y0 + T, PH + 2.6, PH + 3.0, M["shutter"])                       # rolled-up shutter box
    for k in range(4):
        hb.box(-2.05, 2.05, y0 - 0.06, y0 - 0.05, PH + 2.62 + k * 0.09, PH + 2.66 + k * 0.09, M["iron"])
    K.put(hb, "GEO_Shop%s_Shell" % kind, c)
    hb = HB()
    K.awning(hb, M[spec["awning"]], x0 - 0.1, x1 + 0.1, y0 - 0.05, PH + 3.05, 1.3, 0.5)
    # interior + front display by kind
    if kind == "Kirana":
        K.shelf_goods(hb, M, 0.0, y1 - 0.5, PH, 0.0, 4.2, 2.6, 5, rng)
        hb.box(-1.6, 1.6, -2.3, -1.8, PH, PH + 0.95, M["wood"])                                    # counter
        hb.box(-1.65, 1.65, -2.35, -1.75, PH + 0.95, PH + 1.0, M["kota"])
        for k in range(5):
            hb.lathe(M["glass"], [(0.0, 0.0), (0.09, 0.0), (0.1, 0.25), (0.06, 0.3), (0.07, 0.34)], 12, -1.3 + k * 0.6, -2.05, PH + 1.0)
        K.sacks(hb, M, -2.0, -3.4, PH - 0.2, 4, rng)
        K.sacks(hb, M, 1.2, -3.4, PH - 0.2, 4, rng)
        hb.box(1.4, 1.8, -2.1, -1.9, PH + 1.0, PH + 1.25, M["steel"])                                # scale
    elif kind == "Chai":
        hb.box(-1.8, 1.4, -2.4, -1.9, PH, PH + 0.95, M["blue"])
        hb.box(-1.85, 1.45, -2.45, -1.85, PH + 0.95, PH + 1.0, M["steel"])
        hb.frustum(-1.2, -2.15, PH + 1.0, PH + 1.15, 0.18, 0.18, 14, M["iron"])                    # stove
        hb.lathe(M["brass"], [(0.0, 0.0), (0.13, 0.0), (0.15, 0.12), (0.13, 0.2), (0.06, 0.26), (0.08, 0.3)], 16, -1.2, -2.15, PH + 1.15)
        for k in range(6):
            hb.lathe(M["glass"], [(0.0, 0.0), (0.03, 0.0), (0.035, 0.08)], 10, 0.0 + k * 0.12, -2.2, PH + 1.0)
        for k in range(3):
            hb.lathe(M["glass"], [(0.0, 0.0), (0.12, 0.0), (0.13, 0.3), (0.1, 0.34)], 12, 0.6 + k * 0.28, -2.05, PH + 1.0)
        K.bench(hb, M, -1.0, -4.3, 0.0, 0.0, 1.8)
        K.bench(hb, M, 1.4, -4.3, 0.0, 0.0, 1.4, M["blue"])
        K.shelf_goods(hb, M, 0.0, y1 - 0.5, PH, 0.0, 3.0, 2.0, 3, rng)
    else:
        for k in range(9):                                                                         # hanging fabrics
            mat = M[["cloth_red", "cloth_blue", "cloth_green", "bedsheet", "saffron"][k % 5]]
            x = -1.9 + k * 0.47
            hb.add([(x, -2.6, PH + 2.5), (x + 0.4, -2.6, PH + 2.5), (x + 0.42, -2.62, PH + 1.1 - 0.1 * (k % 3)),
                    (x - 0.02, -2.6, PH + 1.15 - 0.1 * (k % 2))], [(0, 1, 2, 3)], mat)
        hb.rod(M["iron"], (-2.0, -2.6, PH + 2.5), (2.0, -2.6, PH + 2.5), 0.015, 6)
        hb.box(-1.6, 1.6, -0.6, 0.6, PH, PH + 0.75, M["wood"])
        for k in range(6):                                                                         # bolts of cloth
            hb.rod(M[["cloth_red", "cloth_blue", "bedsheet"][k % 3]], (-1.4 + k * 0.5, -0.4, PH + 0.86), (-1.4 + k * 0.5, 0.4, PH + 0.86), 0.1, 10)
        K.shelf_goods(hb, M, 0.0, y1 - 0.5, PH, 0.0, 4.2, 2.6, 5, rng)
    K.ceiling_fan(hb, M, 0.0, 0.4, TOP)
    K.put(hb, "GEO_Shop%s_Dressing" % kind, c)
    sgn = spec["sign"]
    K.sign(c, "GEO_Shop%s_Sign" % kind, spec["text"], (0.0, y0 - 0.06, PH + 3.3), 0.0, 0.32, M[sgn[0]], M[sgn[1]], 4.4, 0.55)
    c["night_lights"] = [[0.0, 0.0, TOP - 0.3, 45.0], [0.0, y0 - 0.6, PH + 2.8, 30.0]]
    return c


def shop2(M):
    c = new_asset("AST_Shop2_Hardware_A")
    rng = random.Random(5)
    Mp = dict(M)
    Mp["plaster"] = H.mat_plaster("MAT_Wall_Plaster_A8C6A2", "#A8C6A2", band="#4C6A5A", band_top=0.5)
    PH, F1, F2 = 0.45, 3.7, 6.8
    x0, x1, y0, y1, T = -2.9, 2.9, -3.5, 3.9, 0.23
    hb = HB()
    hb.box(x0 - 0.1, x1 + 0.1, -4.0, y1 + 0.1, -0.2, PH, M["stone"])
    K.wall_x(hb, Mp["plaster"], x0, x1, y0, y0 + T, PH, F1 - 0.15, [(-2.5, 2.5, PH, PH + 2.7)])
    hb.box(x0, x1, y1 - T, y1, PH, F2, Mp["plaster"])
    hb.box(x0, x0 + T, y0 + T, y1 - T, PH, F2, Mp["plaster"])
    hb.box(x1 - T, x1, y0 + T, y1 - T, PH, F2, Mp["plaster"])
    hb.box(x0, x1, y0, y1, F1 - 0.15, F1, M["concrete"])
    hb.box(x0 + 0.2, x1 - 0.2, y0 - 1.0, y0, F1 - 0.15, F1, M["concrete"])                         # balcony slab
    K.wall_x(hb, Mp["plaster"], x0, x1, y0, y0 + T, F1, F2, [(-0.5, 0.5, F1, F1 + 2.1), (-2.2, -1.2, F1 + 0.9, F1 + 2.1), (1.2, 2.2, F1 + 0.9, F1 + 2.1)])
    hb.box(x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, F2, F2 + 0.15, M["concrete"])
    K.parapet(hb, Mp["plaster"], x0 - 0.1, x1 + 0.1, y0 - 0.1, y1 + 0.1, F2 + 0.15, 0.8, 0.12, M["concrete"])
    hb.box(-2.5, 2.5, y0 - 0.05, y0 + T, PH + 2.7, PH + 3.05, M["shutter"])
    K.put(hb, "GEO_Shop2_Shell", c)
    hb = HB()
    K.railing(hb, M["grill"], (x0 + 0.25, y0 - 0.95), (x1 - 0.25, y0 - 0.95), F1)
    K.door(hb, M, 0.0, y0, F1, 0.95, 2.05, T, -1, "blue")
    for wx in (-1.7, 1.7):
        K.window(hb, M, wx, y0, F1 + 0.9, 1.0, 1.2, T, -1, "blue")
    K.shelf_goods(hb, M, 0.0, y1 - 0.5, PH, 0.0, 5.0, 2.7, 5, rng)
    for k in range(5):                                                                             # pipes, buckets, rope coils
        hb.rod(M["steel"], (-2.6, -2.8 + k * 0.12, PH), (-2.4, -2.6 + k * 0.12, PH + 2.4), 0.03, 8)
        hb.lathe(M[["goods1", "goods3", "steel"][k % 3]], [(0.0, 0.0), (0.14, 0.0), (0.17, 0.3), (0.18, 0.31)], 14, 1.6 + (k % 2) * 0.4, -3.2 - (k // 2) * 0.4, PH)
    hb.box(-1.8, 1.0, -2.4, -1.9, PH, PH + 0.95, M["wood"])
    K.ceiling_fan(hb, M, 0.0, 0.5, F1 - 0.15)
    K.bed(hb, M, -1.2, 2.2, F1, math.pi)
    K.almirah(hb, M, 2.2, 3.2, F1, math.pi)
    K.water_tank(hb, M, 1.6, 2.4, F2 + 0.15)
    K.put(hb, "GEO_Shop2_Dressing", c)
    K.sign(c, "GEO_Shop2_Sign", "VERMA HARDWARE & PAINTS", (0.0, y0 - 1.06, F1 + 0.05), 0.0, 0.3, M["sign_bg2"], M["sign_txt2"], 5.2, 0.5)
    c["night_lights"] = [[0.0, 0.0, F1 - 0.5, 50.0], [0.0, 1.0, F2 - 0.4, 35.0], [0.0, y0 - 0.6, F1 - 0.4, 25.0]]
    return c


# ============================================================================ temple
def temple(M):
    c = new_asset("AST_Temple_Shiv_A")
    rng = random.Random(11)
    white = H.mat_plaster("MAT_Plaster_Temple_Cream", "#F2E5C9")
    J = 1.2                                                                                        # jagati height
    hb = HB()
    hb.box(-7.5, 7.5, -7.5, 7.5, -0.3, J, M["stone"])                                              # jagati
    for k in range(6):
        hb.box(-2.0, 2.0, -7.5 - (6 - k) * 0.32, -7.5 - (5 - k) * 0.32, -0.3, (k + 1) * J / 6, M["stone"])
    hb.box(-7.6, 7.6, -7.6, 7.6, J, J + 0.08, M["kota"])
    # garbhagriha + shikhara (curvilinear nagara tower)
    gx0, gx1, gy0, gy1 = -2.2, 2.2, 1.6, 6.0
    K.wall_x(hb, white, gx0, gx1, gy0, gy0 + 0.4, J, J + 3.6, [(-0.6, 0.6, J, J + 2.3)])
    hb.box(gx0, gx1, gy1 - 0.4, gy1, J, J + 3.6, white)
    hb.box(gx0, gx0 + 0.4, gy0 + 0.4, gy1 - 0.4, J, J + 3.6, white)
    hb.box(gx1 - 0.4, gx1, gy0 + 0.4, gy1 - 0.4, J, J + 3.6, white)
    hb.box(gx0 - 0.2, gx1 + 0.2, gy0 - 0.2, gy1 + 0.2, J + 3.6, J + 3.9, white)
    scx, scy = 0.0, (gy0 + gy1) / 2
    levels = 14
    for k in range(levels):
        t0, t1 = k / levels, (k + 1) / levels
        h0 = J + 3.9 + t0 * 8.0
        h1 = J + 3.9 + t1 * 8.0
        w0 = 2.4 * (1 - t0 ** 1.6 * 0.72)
        w1 = 2.4 * (1 - t1 ** 1.6 * 0.72)
        hb.box(scx - w0, scx + w0, scy - w0, scy + w0, h0, h1 - 0.06, white)
        hb.box(scx - w1 - 0.05, scx + w1 + 0.05, scy - w1 - 0.05, scy + w1 + 0.05, h1 - 0.08, h1, M["saffron"] if k % 4 == 3 else white)
        for s in (-1, 1):                                                                           # offset projections (ratha)
            hb.box(scx - w0 * 0.35, scx + w0 * 0.35, scy + s * w0, scy + s * (w0 + 0.18), h0, h1 - 0.06, white)
            hb.box(scx + s * w0, scx + s * (w0 + 0.18), scy - w0 * 0.35, scy + w0 * 0.35, h0, h1 - 0.06, white)
    top = J + 11.9
    hb.lathe(white, [(0.0, 0.0), (0.9, 0.0), (1.05, 0.2), (0.9, 0.42), (0.3, 0.5), (0.0, 0.5)], 24, scx, scy, top)       # amalaka
    for k in range(24):
        a = 2 * math.pi * k / 24
        hb.ellipsoid(scx + 0.98 * math.cos(a), scy + 0.98 * math.sin(a), top + 0.2, 0.09, 0.09, 0.14, white, 8, 4)
    hb.lathe(M["brass"], [(0.0, 0.0), (0.25, 0.0), (0.32, 0.25), (0.2, 0.45), (0.1, 0.55), (0.15, 0.6), (0.0, 0.95)], 16, scx, scy, top + 0.5)
    hb.rod(M["wood_dark"], (scx + 0.3, scy, top + 0.5), (scx + 0.3, scy, top + 3.2), 0.025, 6)
    hb.add([(scx + 0.3, scy, top + 3.15), (scx + 1.6, scy - 0.1, top + 2.85), (scx + 0.3, scy, top + 2.45)], [(0, 1, 2)], M["saffron"])
    # mandapa (pillared hall) + pyramidal roof
    mx0, mx1, my0, my1 = -3.4, 3.4, -4.8, gy0
    for x in np.linspace(mx0 + 0.3, mx1 - 0.3, 4):
        for y in np.linspace(my0 + 0.3, my1 - 0.3, 3):
            K.column(hb, M, x, y, J + 0.08, J + 3.4, 0.2, "square", white)
    hb.box(mx0 - 0.3, mx1 + 0.3, my0 - 0.3, my1 + 0.1, J + 3.4, J + 3.65, white)
    for k in range(5):
        s = 1 - k * 0.18
        hb.box(-3.4 * s, 3.4 * s, (my0 + my1) / 2 - 3.2 * s, (my0 + my1) / 2 + 3.2 * s, J + 3.65 + k * 0.4, J + 4.0 + k * 0.4,
               M["saffron"] if k == 2 else white)
    hb.lathe(M["brass"], [(0.0, 0.0), (0.18, 0.0), (0.22, 0.2), (0.1, 0.35), (0.0, 0.6)], 14, 0.0, (my0 + my1) / 2, J + 5.65)
    K.put(hb, "GEO_Temple_Structure", c, bevel=0.02)
    # compound wall + gate, bell, nandi, lamp pillar, interior
    hb = HB()
    for (a0, a1, b0, b1) in ((-12, -2.2, -12, -11.7), (2.2, 12, -12, -11.7), (-12, -11.7, -11.7, 12), (11.7, 12, -11.7, 12), (-12, 12, 11.7, 12)):
        hb.box(a0, a1, b0, b1, -0.2, 1.5, white)
        hb.box(a0, a1, b0, b1, 1.5, 1.62, M["saffron"])
    for gx in (-2.4, 2.4):
        hb.box(gx - 0.25, gx + 0.25, -12.1, -11.6, -0.2, 3.0, white)
        hb.lathe(white, [(0.0, 0.0), (0.3, 0.0), (0.25, 0.25), (0.1, 0.45), (0.0, 0.6)], 12, gx, -11.85, 3.0)
    K.arch_band(hb, white, -2.15, 2.15, -12.1, -11.6, 2.4, 0.8, 3.4, 12, "x")
    hb.rod(M["iron"], (0.0, my0 + 0.2, J + 3.4), (0.0, my0 + 0.2, J + 2.7), 0.01, 4)                 # bell
    hb.lathe(M["brass"], [(0.0, 0.0), (0.2, 0.0), (0.18, 0.08), (0.12, 0.3), (0.05, 0.38), (0.0, 0.4)], 16, 0.0, my0 + 0.2, J + 2.3)
    nd = CL.Clay("Temple_Nandi", 0.02)                                                              # seated nandi facing the sanctum
    ny = my0 - 1.7
    nd.ellipsoid((0, ny, J + 0.45), 0.35, 0.65, 0.35)
    nd.ellipsoid((0, ny - 0.15, J + 0.75), 0.2, 0.25, 0.18)
    nd.capsule((0, ny + 0.35, J + 0.6), (0, ny + 0.62, J + 0.82), 0.18, 0.13)
    nd.ellipsoid((0, ny + 0.75, J + 0.82), 0.12, 0.17, 0.12)
    for sx in (-1, 1):
        nd.capsule((sx * 0.25, ny - 0.2, J + 0.2), (sx * 0.3, ny + 0.35, J + 0.12), 0.1, 0.08)
    nd.to_mesh(H.mat_simple("MAT_Stone_Nandi_Black", "#2A2826", 0.4, noise=0.15), 3, c)
    hb.box(-0.5, 0.5, ny - 0.8, ny + 0.5, J + 0.08, J + 0.2, M["stone"])
    hb.lathe(M["stone"], [(0.0, 0.0), (0.35, 0.0), (0.3, 0.2), (0.12, 0.3), (0.12, 2.4), (0.3, 2.5), (0.0, 2.6)], 12, -5.5, -6.0, J)   # deepastambha
    for k in range(6):
        hb.frustum(-5.5, -6.0, J + 0.6 + k * 0.32, J + 0.66 + k * 0.32, 0.3 - k * 0.02, 0.3 - k * 0.02, 12, M["stone"])
    sx_, sy_ = 0.0, scy                                                                             # shivling on yoni base
    hb.box(-0.45, 0.45, sy_ - 0.45, sy_ + 0.45, J, J + 0.35, M["stone"])
    hb.box(-0.12, 0.12, sy_ - 0.85, sy_ - 0.45, J + 0.22, J + 0.3, M["stone"])
    hb.lathe(H.mat_simple("MAT_Stone_Shivling", "#1E1C1B", 0.25), [(0.0, 0.0), (0.2, 0.0), (0.2, 0.35), (0.14, 0.52), (0.0, 0.58)], 20, sx_, sy_, J + 0.35)
    for k in range(9):
        a = 2 * math.pi * k / 9
        hb.ellipsoid(0.32 * math.cos(a), sy_ + 0.32 * math.sin(a), J + 0.38, 0.05, 0.05, 0.03, M["saffron"], 8, 4)
    diyas = []
    for k in range(7):
        x = -1.2 + k * 0.4
        hb.lathe(M["terracotta"], [(0.0, 0.0), (0.05, 0.0), (0.065, 0.025), (0.0, 0.03)], 12, x, gy0 + 0.6, J)
        diyas.append((x, gy0 + 0.6, J + 0.06, 4))
    K.put(hb, "GEO_Temple_Compound", c)
    c["night_lights"] = [list(map(float, d)) for d in diyas] + [[0.0, scy, J + 2.8, 40.0], [0.0, -1.5, J + 3.0, 60.0],
                                                             [-5.5, -6.0, J + 2.7, 30.0], [-2.4, -11.85, 3.4, 25.0], [2.4, -11.85, 3.4, 25.0]]
    return c


# ============================================================================ school
def school(M):
    c = new_asset("AST_School_A")
    rng = random.Random(13)
    Mp = dict(M)
    Mp["plaster"] = H.mat_plaster("MAT_Wall_Plaster_School_Yellow", "#E3B85A", band="#7E2C24", band_top=1.0)
    PH, TOP = 0.5, 4.0
    hb = HB()
    hb.box(-20, 20, -17, 17, -0.2, 0.02, H.mat_ground("MAT_Ground_Playground"))
    blocks = [(-15.0, 15.0, 9.0, 15.5, "x"), (-15.0, -8.5, -6.0, 9.0, "y"), (8.5, 15.0, -6.0, 9.0, "y")]
    for (bx0, bx1, by0, by1, ax) in blocks:
        hb.box(bx0 - 0.2, bx1 + 0.2, by0 - 2.6 if ax == "x" else by0 - 0.2, by1 + 0.2, 0.02, PH, M["stone"])
        if ax == "x":
            doors = [(x - 0.55, x + 0.55, PH, PH + 2.2) for x in (-10.5, -0.5, 9.5)]
            wins = [(x - 0.8, x + 0.8, PH + 0.9, PH + 2.3) for x in (-13.0, -7.5, -3.5, 3.0, 7.0, 12.5)]
            K.wall_x(hb, Mp["plaster"], bx0, bx1, by0, by0 + 0.25, PH, TOP, doors + wins)
            K.wall_x(hb, Mp["plaster"], bx0, bx1, by1 - 0.25, by1, PH, TOP, wins)
            for x in (bx0, bx1 - 0.25, -5.0, 5.0):
                hb.box(x, x + 0.25, by0 + 0.25, by1 - 0.25, PH, TOP, Mp["plaster"])
        else:
            inner_x = bx1 - 0.25 if bx0 < 0 else bx0
            doors = [(y - 0.55, y + 0.55, PH, PH + 2.2) for y in (-3.0, 5.0)]
            wins = [(y - 0.8, y + 0.8, PH + 0.9, PH + 2.3) for y in (-0.5, 2.5, 7.3)]
            K.wall_y(hb, Mp["plaster"], inner_x, inner_x + 0.25, by0, by1, PH, TOP, doors + wins)
            outer_x = bx0 if bx0 < 0 else bx1 - 0.25
            K.wall_y(hb, Mp["plaster"], outer_x, outer_x + 0.25, by0, by1, PH, TOP, wins)
            hb.box(bx0, bx1, by0, by0 + 0.25, PH, TOP, Mp["plaster"])
            hb.box(bx0, bx1, 1.5, 1.75, PH, TOP, Mp["plaster"])
        hb.box(bx0 - 0.2, bx1 + 0.2, by0 - 0.2, by1 + 0.2, TOP, TOP + 0.18, M["concrete"])
        K.parapet(hb, Mp["plaster"], bx0 - 0.2, bx1 + 0.2, by0 - 0.2, by1 + 0.2, TOP + 0.18, 0.6, 0.12, M["concrete"])
    # verandahs on the courtyard sides
    hb.box(-15.2, 15.2, 6.4, 9.0, TOP, TOP + 0.15, M["concrete"])
    for x in np.arange(-14.5, 15.0, 2.9):
        K.column(hb, M, x, 6.6, PH, TOP, 0.15, "square", M["white"])
    for sx, xv in ((-1, -8.5), (1, 8.5)):
        hb.box(min(xv, xv + sx * 2.4), max(xv, xv + sx * 2.4), -6.0, 6.4, TOP, TOP + 0.15, M["concrete"])
        hb.box(min(xv, xv + sx * 2.4), max(xv, xv + sx * 2.4), -6.0, 6.4, 0.02, PH, M["stone"])
        for y in np.arange(-5.5, 6.4, 2.9):
            K.column(hb, M, xv + sx * 2.2, y, PH, TOP, 0.15, "square", M["white"])
    K.put(hb, "GEO_School_Buildings", c)
    # boundary wall + gate with board, flag pole, hand pump, mural strip
    hb = HB()
    for (a0, a1, b0, b1) in ((-20, -2.5, -17, -16.75), (2.5, 20, -17, -16.75), (-20, -19.75, -16.75, 17), (19.75, 20, -16.75, 17), (-20, 20, 16.75, 17)):
        hb.box(a0, a1, b0, b1, 0.0, 1.5, Mp["plaster"])
        hb.box(a0 - 0.03, a1 + 0.03, b0 - 0.03, b1 + 0.03, 1.5, 1.58, M["concrete"])
    for gx in (-2.6, 2.6):
        hb.box(gx - 0.3, gx + 0.3, -17.15, -16.6, 0.0, 3.4, Mp["plaster"])
    hb.box(-2.9, 2.9, -17.1, -16.65, 3.4, 3.6, M["concrete"])
    hb.rod(M["steel"], (0.0, -4.0, 0.0), (0.0, -4.0, 8.0), 0.05, 10)                                  # flag pole + tricolour
    hb.box(-0.6, 0.6, -4.6, -3.4, 0.0, 0.4, M["white"])
    for k, col in enumerate(("#E8802A", "#F4F2EC", "#2E8B3A")):
        hb.box(0.05, 1.85, -4.03, -3.97, 7.8 - (k + 1) * 0.4, 7.8 - k * 0.4, H.mat_simple("MAT_Flag_%d" % k, col, 0.7))
    hb.frustum(0.95, -4.04, 7.2, 7.21, 0.17, 0.17, 24, H.mat_simple("MAT_Flag_Chakra", "#1F3A8A", 0.6))
    hb.box(-14.8, -9.0, -5.95, -5.9, PH + 0.6, PH + 2.0, H.mat_simple("MAT_Mural_Alphabet", "#3F8ACB", 0.7, noise=0.5))
    K.put(hb, "GEO_School_Grounds", c)
    K.sign(c, "GEO_School_Sign", "GOVT. PRIMARY SCHOOL  AMALTASPUR", (0.0, -17.18, 3.0), 0.0, 0.32, M["sign_bg2"], M["sign_txt2"], 5.6, 0.55)
    # classroom interior (west wing): desks, blackboard, teacher table, fan
    hb = HB()
    for r in range(4):
        for k in range(2):
            K.school_desk(hb, M, -12.6 + k * 1.5, -4.6 + r * 1.3 + 0.2, PH, -math.pi / 2)
    hb.box(-14.72, -14.7, -3.6, 0.0, PH + 0.9, PH + 2.1, M["black"])
    hb.box(-14.74, -14.7, -3.7, 0.1, PH + 0.85, PH + 0.9, M["wood"])
    K.table(hb, M, -13.9, 1.0, PH, math.pi / 2, 1.2, 0.6)
    K.chair(hb, M, -14.4, 1.0, PH, -math.pi / 2)
    K.ceiling_fan(hb, M, -11.8, -2.0, TOP)
    K.put(hb, "GEO_School_Classroom", c)
    c["night_lights"] = [[x, 7.6, TOP - 0.3, 25.0] for x in (-10.0, 0.0, 10.0)] + [[-11.8, -2.0, TOP - 0.5, 35.0], [0.0, -17.0, 3.7, 25.0]]
    return c


# ============================================================================ panchayat
def panchayat(M):
    c = new_asset("AST_Panchayat_A")
    Mp = dict(M)
    Mp["plaster"] = H.mat_plaster("MAT_Wall_Panchayat_White_Blue", "#EEE7D7", band="#2F5A8A", band_top=1.0)
    PH, TOP = 0.75, 4.4
    x0, x1, y0, y1 = -7.0, 7.0, -1.5, 5.5
    hb = HB()
    hb.box(-9.0, 9.0, -5.5, 5.5, -0.2, 0.02, M["concrete"])
    hb.box(x0 - 0.2, x1 + 0.2, -4.2, y1 + 0.2, 0.02, PH, M["stone"])
    for k in range(4):
        hb.box(-2.5, 2.5, -4.2 - (4 - k) * 0.3, -4.2 - (3 - k) * 0.3, 0.02, 0.02 + (k + 1) * (PH - 0.02) / 4, M["stone"])
    K.wall_x(hb, Mp["plaster"], x0, x1, y0, y0 + 0.25, PH, TOP, [(-0.75, 0.75, PH, PH + 2.4), (-4.8, -3.6, PH + 0.9, PH + 2.3), (3.6, 4.8, PH + 0.9, PH + 2.3)])
    K.wall_x(hb, Mp["plaster"], x0, x1, y1 - 0.25, y1, PH, TOP, [(-4.0, -2.8, PH + 0.9, PH + 2.3), (2.8, 4.0, PH + 0.9, PH + 2.3)])
    K.wall_y(hb, Mp["plaster"], x0, x0 + 0.25, y0 + 0.25, y1 - 0.25, PH, TOP, [(1.4, 2.6, PH + 0.9, PH + 2.3)])
    K.wall_y(hb, Mp["plaster"], x1 - 0.25, x1, y0 + 0.25, y1 - 0.25, PH, TOP, [(1.4, 2.6, PH + 0.9, PH + 2.3)])
    hb.box(x0 - 0.3, x1 + 0.3, -4.3, y1 + 0.3, TOP, TOP + 0.2, M["concrete"])
    K.parapet(hb, Mp["plaster"], x0 - 0.3, x1 + 0.3, -4.3, y1 + 0.3, TOP + 0.2, 0.75, 0.15, M["concrete"])
    xs = np.linspace(x0, x1, 6)                                                                      # arched verandah
    for x in xs:
        K.column(hb, M, x, -3.95, PH, TOP - 0.9, 0.2, "square", M["white"])
    for i in range(len(xs) - 1):
        K.arch_band(hb, Mp["plaster"], xs[i] + 0.25, xs[i + 1] - 0.25, -4.15, -3.75, TOP - 1.9, 1.0, TOP, 14, "x")
    K.put(hb, "GEO_Panchayat_Shell", c, bevel=0.015)
    hb = HB()
    K.door(hb, M, 0.0, y0, PH, 1.5, 2.4, 0.25, -1, "blue", 0.4)
    for wx in (-4.2, 4.2):
        K.window(hb, M, wx, y0, PH + 0.9, 1.2, 1.4, 0.25, -1, "blue")
    hb.box(-6.3, -4.9, y0 - 0.06, y0, PH + 1.0, PH + 2.0, M["wood"])                               # notice board
    for k in range(5):
        hb.box(-6.2 + k * 0.27, -6.0 + k * 0.27, y0 - 0.075, y0 - 0.06, PH + 1.2 + 0.1 * (k % 3), PH + 1.6 + 0.1 * (k % 2), M["white"])
    for bx in (-5.0, 5.0):
        K.bench(hb, M, bx, -5.0, 0.02, 0.0, 2.0, M["concrete"])
    hb.rod(M["steel"], (7.8, -4.8, 0.02), (7.8, -4.8, 7.0), 0.045, 10)
    for k, col in enumerate(("#E8802A", "#F4F2EC", "#2E8B3A")):
        hb.box(7.85, 9.4, -4.83, -4.77, 6.8 - (k + 1) * 0.33, 6.8 - k * 0.33, bpy.data.materials.get("MAT_Flag_%d" % k) or H.mat_simple("MAT_Flag_%d" % k, col, 0.7))
    # interior: meeting hall
    K.durrie(hb, M, -5.0, 5.0, 0.2, 4.6, PH + 0.005)
    K.table(hb, M, 0.0, 4.4, PH, 0.0, 2.4, 0.9)
    for k in range(4):
        K.chair(hb, M, -1.2 + k * 0.8, 5.0, PH, math.pi)
    for k in range(6):
        K.chair(hb, M, -3.0 + k * 1.2, 1.4, PH, 0.0, M["steel"])
    K.almirah(hb, M, 6.2, 4.9, PH, math.pi)
    for fx in (-3.0, 3.0):
        K.ceiling_fan(hb, M, fx, 2.5, TOP)
    K.put(hb, "GEO_Panchayat_Details", c)
    K.sign(c, "GEO_Panchayat_Sign", "GRAM PANCHAYAT BHAVAN  AMALTASPUR", (0.0, -4.35, TOP - 0.45), 0.0, 0.34, M["sign_bg2"], M["sign_txt2"], 9.0, 0.6)
    c["night_lights"] = [[-3.0, 2.5, TOP - 0.6, 45.0], [3.0, 2.5, TOP - 0.6, 45.0], [-4.2, -3.9, TOP - 1.0, 25.0], [4.2, -3.9, TOP - 1.0, 25.0]]
    return c


BUILDERS = {
    "AST_House_Middle_A": house_middle, "AST_Haveli_A": haveli, "AST_Shop_Kirana_A": lambda M: shop(M, "Kirana"),
    "AST_Shop_Chai_A": lambda M: shop(M, "Chai"), "AST_Shop_Cloth_A": lambda M: shop(M, "Cloth"), "AST_Shop2_Hardware_A": shop2,
    "AST_Temple_Shiv_A": temple, "AST_School_A": school, "AST_Panchayat_A": panchayat,
}


def main():
    global LIB
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    LIB = bpy.data.collections.new("LIB_BUILDINGS_B2")
    sc.collection.children.link(LIB)
    M = K.materials()
    only = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
    for name, fn in BUILDERS.items():
        if only and name not in only:
            continue
        fn(M)
        print("[b2] built", name, "objects", len(bpy.data.collections[name].objects))
    for o in list(sc.collection.objects):
        if o.type == "META":
            bpy.data.objects.remove(o, do_unlink=True)
    for ch in LIB.children:
        bpy.context.view_layer.layer_collection.children["LIB_BUILDINGS_B2"].children[ch.name].exclude = True
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_Buildings_B2_%s.blend" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[b2] saved", OUT_BLEND)


if __name__ == "__main__":
    main()
