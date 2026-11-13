"""
BATCH 3 - environmental storytelling props.

  blender -b --factory-startup --python hero_props_b3.py

Output: 06_PROPS/LIB_Props_B3.blend
  AST_UtilityPole_A        PCC pole, cross-arm, porcelain insulators, street-side bulb bracket
  AST_TransformerPole_A    double pole with transformer, fuse box, earthing
  AST_PublicTap_A          public tap (nal) on a concrete stand with a soak pit and a steel pot
  AST_Charpai_A            rope cot (outdoor)
  AST_Bicycle_A            black roadster with carrier
  AST_Thela_A              vegetable handcart with produce
  AST_Dustbin_A            municipal bin
  AST_BusStop_A            bus shelter with bench and board
  AST_WaterTower_A         village overhead water tank (OHT) on columns with ladder
  AST_MobileTower_A        lattice tower with antennas
  AST_Milestone_A          yellow-topped milestone "AMALTASPUR 0"
  AST_DirectionBoard_A     green direction board
  AST_StoneBench_A         stone slab bench
Generated in the master instead (needs the layout): wires between poles, drains along lanes, buntings.
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
import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "06_PROPS", "LIB_Props_B3.blend")
LIB = None


def asset(name):
    c = bpy.data.collections.new(name)
    LIB.children.link(c)
    return c


def utility_pole(M):
    c = asset("AST_UtilityPole_A")
    hb = HB()
    hb.frustum(0, 0, -0.8, 8.5, 0.11, 0.07, 4, M["concrete"], rot=math.pi / 4)
    hb.box(-0.75, 0.75, -0.05, 0.05, 7.8, 7.9, M["iron"])
    for x in (-0.65, 0.0, 0.65):
        hb.lathe(M["white"], [(0.0, 0.0), (0.04, 0.0), (0.06, 0.04), (0.04, 0.08), (0.06, 0.12), (0.03, 0.17), (0.0, 0.17)], 10, x, 0.0, 7.9)
    hb.rod(M["iron"], (0.0, 0.0, 6.6), (0.0, -0.9, 6.75), 0.02, 6)                         # bulb bracket
    hb.frustum(0.0, -0.95, 6.55, 6.7, 0.1, 0.04, 10, M["iron"])
    hb.ellipsoid(0.0, -0.95, 6.53, 0.05, 0.05, 0.05, M["glow"], 8, 5)
    hb.box(-0.12, 0.12, 0.12, 0.2, 1.5, 1.9, M["tin"])                                       # meter box
    K.put(hb, "GEO_UtilityPole", c)
    c["night_lights"] = [[0.0, -0.95, 6.45, 70.0]]
    c["wire_points"] = [[-0.65, 0.0, 8.06], [0.0, 0.0, 8.06], [0.65, 0.0, 8.06]]


def transformer_pole(M):
    c = asset("AST_TransformerPole_A")
    hb = HB()
    for x in (-1.0, 1.0):
        hb.frustum(x, 0, -0.8, 8.8, 0.13, 0.08, 4, M["concrete"], rot=math.pi / 4)
    hb.box(-1.25, 1.25, -0.08, 0.08, 3.0, 3.15, M["iron"])
    hb.box(-1.25, 1.25, -0.08, 0.08, 8.0, 8.12, M["iron"])
    hb.box(-0.6, 0.6, -0.45, 0.45, 3.15, 4.4, M["grill"])                                   # transformer tank
    for k in range(6):
        hb.box(-0.62, 0.62, -0.47 + k * 0.18, -0.43 + k * 0.18, 3.25, 4.25, M["grill"])
    for x in (-0.35, 0.0, 0.35):
        hb.lathe(M["white"], [(0.0, 0.0), (0.05, 0.0), (0.07, 0.06), (0.05, 0.12), (0.07, 0.18), (0.0, 0.3)], 10, x, 0.0, 4.4)
    hb.box(0.85, 1.35, -0.35, -0.15, 1.4, 2.1, M["tin"])
    K.put(hb, "GEO_TransformerPole", c)
    c["wire_points"] = [[-1.0, 0.0, 8.2], [0.0, 0.0, 8.2], [1.0, 0.0, 8.2]]


def public_tap(M):
    c = asset("AST_PublicTap_A")
    hb = HB()
    hb.box(-0.9, 0.9, -0.9, 0.9, -0.1, 0.12, M["concrete"])
    hb.box(-0.9, 0.9, -0.9, -0.78, 0.12, 0.22, M["concrete"])
    hb.box(-0.15, 0.15, 0.55, 0.85, 0.12, 1.0, M["concrete"])
    hb.rod(M["steel"], (0.0, 0.6, 0.8), (0.0, 0.3, 0.8), 0.022, 8)
    hb.rod(M["steel"], (0.0, 0.3, 0.8), (0.0, 0.3, 0.7), 0.022, 8)
    hb.box(-0.05, 0.05, 0.62, 0.7, 0.86, 0.95, M["iron"])
    hb.box(-0.6, 0.6, -0.6, 0.4, 0.11, 0.125, M["water"])
    hb.lathe(M["steel"], [(0.0, 0.0), (0.13, 0.0), (0.18, 0.12), (0.17, 0.24), (0.09, 0.3), (0.1, 0.33)], 16, 0.0, 0.25, 0.12)
    hb.lathe(M["goods1"], [(0.0, 0.0), (0.12, 0.0), (0.15, 0.28), (0.16, 0.29)], 14, 0.5, -0.4, 0.12)
    K.put(hb, "GEO_PublicTap", c)


def charpai(M):
    c = asset("AST_Charpai_A")
    hb = HB()
    L, W_, h = 1.9, 0.9, 0.45
    for sx in (-1, 1):
        hb.box(-L / 2, L / 2, sx * W_ / 2 - 0.04, sx * W_ / 2 + 0.04, h - 0.08, h, M["wood"])
        hb.box(sx * L / 2 - 0.04, sx * L / 2 + 0.04, -W_ / 2, W_ / 2, h - 0.08, h, M["wood"])
        for sy in (-1, 1):
            hb.lathe(M["wood"], [(0.0, 0.0), (0.04, 0.0), (0.05, 0.15), (0.035, 0.3), (0.045, h), (0.0, h)], 10, sx * L / 2, sy * W_ / 2, 0)
    for k in range(14):
        x = -L / 2 + 0.06 + k * (L - 0.12) / 13
        hb.rod(M["rope"], (x, -W_ / 2, h - 0.04), (x + 0.05, W_ / 2, h - 0.04), 0.008, 4)
    for k in range(8):
        y = -W_ / 2 + 0.05 + k * (W_ - 0.1) / 7
        hb.rod(M["rope"], (-L / 2, y, h - 0.035), (L / 2, y + 0.03, h - 0.035), 0.008, 4)
    K.put(hb, "GEO_Charpai", c)


def bicycle(M):
    c = asset("AST_Bicycle_A")
    hb = HB()
    R = 0.34
    for wx in (-0.53, 0.53):
        n = 32
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            hb.rod(M["iron"], (wx + R * math.cos(a0), 0, R + R * math.sin(a0)), (wx + R * math.cos(a1), 0, R + R * math.sin(a1)), 0.018, 5)
        for i in range(12):
            a = 2 * math.pi * i / 12
            hb.rod(M["steel"], (wx, 0, R), (wx + R * math.cos(a), 0, R + R * math.sin(a)), 0.003, 3)
    pts = {"bb": (0.0, 0, 0.3), "seat": (-0.15, 0, 0.88), "head": (0.42, 0, 0.92), "rear": (-0.53, 0, R), "front": (0.53, 0, R)}
    for a, b in (("bb", "seat"), ("bb", "head"), ("seat", "head"), ("bb", "rear"), ("seat", "rear"), ("head", "front")):
        hb.rod(M["iron"], pts[a], pts[b], 0.016, 6)
    hb.box(-0.27, -0.04, -0.07, 0.07, 0.9, 0.95, M["wood_dark"])
    hb.rod(M["iron"], (0.42, -0.25, 1.0), (0.42, 0.25, 1.0), 0.012, 6)
    hb.rod(M["iron"], (0.42, 0, 0.92), (0.42, 0, 1.0), 0.014, 6)
    hb.box(-0.75, -0.3, -0.1, 0.1, 0.72, 0.74, M["iron"])                                    # carrier
    K.put(hb, "GEO_Bicycle", c)


def thela(M):
    c = asset("AST_Thela_A")
    rng = random.Random(3)
    hb = HB()
    hb.box(-1.0, 1.0, -0.55, 0.55, 0.62, 0.7, M["wood"])
    for sx in (-1, 1):
        hb.box(-1.0, 1.0, sx * 0.55 - 0.02, sx * 0.55 + 0.02, 0.7, 0.82, M["wood"])
        for i in range(24):
            a0, a1 = 2 * math.pi * i / 24, 2 * math.pi * (i + 1) / 24
            hb.rod(M["iron"], (0.0 + 0.32 * math.cos(a0), sx * 0.62, 0.32 + 0.32 * math.sin(a0)),
                   (0.32 * math.cos(a1), sx * 0.62, 0.32 + 0.32 * math.sin(a1)), 0.02, 5)
    hb.rod(M["iron"], (0, -0.62, 0.32), (0, 0.62, 0.32), 0.02, 6)
    for x in (-1.0, 1.0):
        hb.rod(M["wood"], (x, 0, 0.62), (x * 1.1, 0, 0.0), 0.03, 6)
    hb.rod(M["wood"], (1.0, -0.4, 0.75), (1.6, -0.4, 0.85), 0.025, 6)
    hb.rod(M["wood"], (1.0, 0.4, 0.75), (1.6, 0.4, 0.85), 0.025, 6)
    cols = [H.mat_simple("MAT_Veg_Tomato", "#C2281E", 0.35), H.mat_simple("MAT_Veg_Onion", "#9C4A58", 0.4),
            H.mat_simple("MAT_Veg_Potato", "#B48A55", 0.7), H.mat_simple("MAT_Veg_Greens", "#3E7A2C", 0.6)]
    for k in range(4):
        x0 = -0.9 + k * 0.45
        for i in range(70):
            hb.ellipsoid(x0 + rng.uniform(0, 0.4), rng.uniform(-0.45, 0.45), 0.75 + rng.uniform(0, 0.12) * (1 - abs(rng.uniform(-1, 1))),
                         0.045, 0.045, 0.04, cols[k], 8, 5)
    hb.rod(M["iron"], (0.9, 0.0, 0.7), (0.9, 0.0, 1.6), 0.01, 4)
    hb.box(0.7, 1.1, -0.15, 0.15, 1.55, 1.58, M["steel"])                                     # hanging scale
    K.put(hb, "GEO_Thela", c, smooth=False)


def dustbin(M):
    c = asset("AST_Dustbin_A")
    hb = HB()
    hb.lathe(M["blue"], [(0.0, 0.0), (0.28, 0.0), (0.33, 0.85), (0.35, 0.88), (0.0, 0.88)], 16, 0, 0, 0)
    hb.box(-0.36, 0.36, -0.36, 0.36, 0.88, 0.94, M["blue"])
    K.put(hb, "GEO_Dustbin", c)


def bus_stop(M):
    c = asset("AST_BusStop_A")
    hb = HB()
    hb.box(-2.5, 2.5, -1.0, 1.0, -0.1, 0.18, M["concrete"])
    for x in (-2.3, 2.3):
        hb.box(x - 0.1, x + 0.1, 0.7, 0.9, 0.18, 2.7, M["grill"])
    hb.box(-2.5, 2.5, 0.75, 0.85, 0.18, 2.3, M["plaster"])
    hb.slope_slab(-2.8, 2.8, -1.4, 1.1, 2.75, 2.95, 0.04, M["tin"])
    K.bench(hb, M, 0.0, 0.4, 0.18, 0.0, 3.6, M["concrete"])
    K.put(hb, "GEO_BusStop", c)
    K.sign(c, "GEO_BusStop_Sign", "BUS STOP  AMALTASPUR", (0.0, -1.2, 2.55), 0.0, 0.22, M["sign_bg2"], M["sign_txt2"], 3.0, 0.38)


def water_tower(M):
    c = asset("AST_WaterTower_A")
    hb = HB()
    for k in range(6):
        a = 2 * math.pi * k / 6
        hb.box(2.8 * math.cos(a) - 0.22, 2.8 * math.cos(a) + 0.22, 2.8 * math.sin(a) - 0.22, 2.8 * math.sin(a) + 0.22, -0.5, 15.0, M["concrete"])
    for z in (5.0, 10.0):
        for k in range(6):
            a0, a1 = 2 * math.pi * k / 6, 2 * math.pi * (k + 1) / 6
            hb.obox(M["concrete"], ((2.8 * math.cos(a0) + 2.8 * math.cos(a1)) / 2, (2.8 * math.sin(a0) + 2.8 * math.sin(a1)) / 2, z),
                    (math.cos(a1) - math.cos(a0), math.sin(a1) - math.sin(a0), 0), (0, 0, 1), 1.4, 0.18, 0.15)
    hb.lathe(M["concrete"], [(0.0, 15.0), (3.6, 15.0), (4.4, 16.0), (4.4, 19.0), (4.0, 19.6), (0.6, 20.3), (0.0, 20.4)], 32)
    hb.lathe(M["white"], [(4.41, 17.2), (4.42, 17.6)], 32)
    for k in range(48):
        hb.rod(M["iron"], (3.0, -0.25, k * 0.42), (3.0, 0.25, k * 0.42), 0.012, 4)
    hb.rod(M["iron"], (3.0, -0.25, 0.0), (3.0, -0.25, 19.0), 0.015, 4)
    hb.rod(M["iron"], (3.0, 0.25, 0.0), (3.0, 0.25, 19.0), 0.015, 4)
    K.put(hb, "GEO_WaterTower", c)
    K.sign(c, "GEO_WaterTower_Sign", "JAL JEEVAN MISSION", (0.0, -4.45, 18.0), 0.0, 0.5, M["sign_bg2"], M["sign_txt2"], 5.5, 0.9)


def mobile_tower(M):
    c = asset("AST_MobileTower_A")
    hb = HB()
    Ht = 36.0
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        hb.rod(M["steel"], (2.0 * math.cos(a), 2.0 * math.sin(a), 0.0), (0.45 * math.cos(a), 0.45 * math.sin(a), Ht), 0.06, 6)
    for z in np.arange(1.0, Ht, 3.0):
        s = 2.0 - (2.0 - 0.45) * z / Ht
        s2 = 2.0 - (2.0 - 0.45) * (z + 3.0) / Ht
        for k in range(4):
            a0, a1 = math.pi / 4 + k * math.pi / 2, math.pi / 4 + (k + 1) * math.pi / 2
            hb.rod(M["steel"], (s * math.cos(a0), s * math.sin(a0), z), (s * math.cos(a1), s * math.sin(a1), z), 0.025, 4)
            hb.rod(M["steel"], (s * math.cos(a0), s * math.sin(a0), z), (s2 * math.cos(a1), s2 * math.sin(a1), z + 3.0), 0.02, 4)
    for k in range(3):
        a = 2 * math.pi * k / 3
        hb.box(0.7 * math.cos(a) - 0.15, 0.7 * math.cos(a) + 0.15, 0.7 * math.sin(a) - 0.06, 0.7 * math.sin(a) + 0.06, Ht - 3.0, Ht - 0.8, M["white"])
    hb.box(-1.0, 1.0, 3.0, 5.0, 0.0, 2.6, M["white"])
    K.put(hb, "GEO_MobileTower", c)
    c["night_lights"] = [[0.0, 0.0, Ht + 0.3, 8.0]]


def milestone(M):
    c = asset("AST_Milestone_A")
    hb = HB()
    hb.box(-0.25, 0.25, -0.1, 0.1, -0.2, 0.6, M["white"])
    hb.lathe(M["sign_bg"], [(0.0, 0.0), (0.25, 0.0), (0.24, 0.12), (0.17, 0.22), (0.0, 0.25)], 16, 0, 0, 0.6)
    K.put(hb, "GEO_Milestone", c)
    K.sign(c, "GEO_Milestone_Text", "AMALTASPUR 0", (0.0, -0.105, 0.35), 0.0, 0.07, M["white"], M["black"], 0.48, 0.2)


def direction_board(M):
    c = asset("AST_DirectionBoard_A")
    hb = HB()
    for x in (-1.2, 1.2):
        hb.rod(M["steel"], (x, 0, 0), (x, 0, 3.4), 0.04, 8)
    K.put(hb, "GEO_DirectionBoard_Posts", c)
    green = H.mat_simple("MAT_Sign_Board_Green", "#1F6B3A", 0.5)
    K.sign(c, "GEO_DirectionBoard", "<- MANDIR  |  GHAT  |  SCHOOL ->", (0.0, -0.05, 2.9), 0.0, 0.2, green, M["sign_txt2"], 2.8, 0.75)


def stone_bench(M):
    c = asset("AST_StoneBench_A")
    hb = HB()
    hb.box(-0.9, 0.9, -0.25, 0.25, 0.38, 0.48, M["stone"])
    for x in (-0.65, 0.65):
        hb.box(x - 0.12, x + 0.12, -0.2, 0.2, 0.0, 0.38, M["stone"])
    K.put(hb, "GEO_StoneBench", c, bevel=0.02)


def main():
    global LIB
    bpy.ops.wm.read_factory_settings(use_empty=True)
    LIB = bpy.data.collections.new("LIB_PROPS_B3")
    bpy.context.scene.collection.children.link(LIB)
    M = K.materials(palette="#E8DFCB")
    M["water"] = H.mat_simple("MAT_Water_Puddle", "#3C6E68", 0.05)
    for fn in (utility_pole, transformer_pole, public_tap, charpai, bicycle, thela, dustbin, bus_stop, water_tower, mobile_tower,
               milestone, direction_board, stone_bench):
        fn(M)
    for ch in LIB.children:
        bpy.context.view_layer.layer_collection.children["LIB_PROPS_B3"].children[ch.name].exclude = True
    if os.path.exists(OUT_BLEND):
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_Props_B3_%s.blend" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[b3] saved", OUT_BLEND, [c.name for c in LIB.children])


if __name__ == "__main__":
    main()
