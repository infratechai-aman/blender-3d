"""
VILLAGE ANIMALS v001 - built in the approved bullock style (clay metaball bodies, swept horns/tails, glossy eyes).

  blender -b --factory-startup --python hero_animals_farm.py -- [--render] [--quick] [--only CAM_A,CAM_B]

Output: 04_CHARACTERS/ANIMALS/LIB_Animals_Farm.blend
  CHR_Animal_Cow_001       desi cow, red-brown with white patches, small hump, long drooping ears, udder
  CHR_Animal_Buffalo_001   heavy black buffalo, tight curled horns, broad muzzle, no hump
  CHR_Animal_Goat_001      brown-and-white goat, long floppy ears, small swept-back horns, beard
  CHR_Animal_Dog_001       indie street dog, fawn, upright ears, tail curled over the back
  CHR_Animal_Hen_001       brown desi hen, red comb + wattles, tail fan
Reviews: 10_EXPORTS/REVIEWS/G7_ANIMALS_FARM_v001/ (lineup with Bullock_001 for scale).  Not rigged yet.
Every animal: origin on the ground under the body centre, faces -Y.
"""
import datetime
import math
import os
import shutil
import sys

import bpy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import char_lib as CL  # noqa: E402
import hero_animal_bullock_001 as BU  # noqa: E402
import hero_lib as H  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "04_CHARACTERS", "ANIMALS", "LIB_Animals_Farm.blend")
BULL_BLEND = os.path.join(ROOT, "04_CHARACTERS", "ANIMALS", "CHR_Animal_Bullock_001.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "G7_ANIMALS_FARM_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
LIB = None


def mat_coat(name, base, patch=None, patch_amt=0.0, patch_scale=2.2, dark=None, dark_from=None, belly=None,
             muzzle=None, muzzle_y=None, rough=0.6, sheen=0.35, hair_dir="Y"):
    """Generic coat: base colour, optional irregular patches, darker lower legs, lighter belly, muzzle tint."""
    m, t = H._mat(name, base)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=obj)
    y, z = sx.outputs["Y"], sx.outputs["Z"]
    n = t.noise(obj, 3.0, 5.0, 0.55)
    fine = t.noise(obj, 40.0, 6.0, 0.6)
    col = t.ramp(fine.outputs["Fac"], [(0.3, H.hex_lin(base, 0.9)), (0.7, H.hex_lin(base, 1.08))])
    if patch:
        pn = t.noise(obj, patch_scale, 4.0, 0.6)
        pm = t.n("ShaderNodeMapRange", Value=pn.outputs["Fac"],
                 **{"From Min": 1.0 - patch_amt - 0.03, "From Max": 1.0 - patch_amt + 0.03, "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
        col = t.mix(pm, col, H.hex_lin(patch))
    if belly:
        bm = t.n("ShaderNodeMapRange", Value=z, **{"From Min": belly[1] + 0.06, "From Max": belly[1] - 0.03,
                                                    "To Min": 0.0, "To Max": 0.8}).outputs["Result"]
        low = t.n("ShaderNodeMapRange", Value=z, **{"From Min": belly[1] - 0.12, "From Max": belly[1] - 0.05,
                                                     "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
        bm = t.math("MULTIPLY", bm, low)
        col = t.mix(bm, col, H.hex_lin(belly[0]))
    if dark:
        dm = t.n("ShaderNodeMapRange", Value=z, **{"From Min": dark_from, "From Max": dark_from * 0.4,
                                                    "To Min": 0.0, "To Max": 0.85}).outputs["Result"]
        col = t.mix(dm, col, H.hex_lin(dark))
    if muzzle:
        mm = t.n("ShaderNodeMapRange", Value=y, **{"From Min": muzzle_y, "From Max": muzzle_y - 0.05,
                                                    "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
        col = t.mix(mm, col, H.hex_lin(muzzle))
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.inp(b, "Roughness").default_value = rough
    try:
        t.inp(b, "Sheen Weight").default_value = sheen
    except Exception:
        pass
    sc = {"Y": (300.0, 60.0, 300.0), "Z": (300.0, 300.0, 60.0)}[hair_dir]
    hn = t.noise(t.n("ShaderNodeMapping", Vector=obj, Scale=sc).outputs[0], 1.0, 3.0, 0.6)
    t.link(t.bump(t.math("ADD", hn.outputs["Fac"], t.math("MULTIPLY", n.outputs["Fac"], 0.4)), 0.12, 0.003), t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def new_coll(name):
    c = bpy.data.collections.new(name)
    LIB.children.link(c)
    BU.COLL = c
    CL_COLL[0] = c
    return c


CL_COLL = [None]


def sphere(name, c, r, mat, seg=16):
    hb = H.HB()
    hb.ellipsoid(c[0], c[1], c[2], r[0], r[1], r[2], mat, seg, max(4, seg // 2))
    me = hb.to_mesh("ME_" + name, recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me)
    CL_COLL[0].objects.link(o)
    return o


def eyes(prefix, M, centres, r, lid_mat, sx_axis=True):
    for k, e in enumerate(centres):
        e = np.asarray(e, float)
        side = "L" if e[0] < 0 else "R"
        sphere("GEO_%s_Eye_%s" % (prefix, side), e, (r, r * 1.1, r * 0.9), M["eye"], 18)
        lid = CL.Clay("%s_Lid_%s" % (prefix, side), r * 0.15)
        s = np.sign(e[0])
        lid.ellipsoid(tuple(e + np.array([s * r * 0.1, 0, r * 0.6])), r * 1.02, r * 1.15, r * 0.5)
        lid.ellipsoid(tuple(e + np.array([s * r * 0.1, 0, -r * 0.65])), r * 0.95, r * 1.05, r * 0.38)
        lid.to_mesh(lid_mat, 2, CL_COLL[0])


def legs(c, fx, fy, hx, hy, top_f, top_h, r_top, r_knee, r_cannon, knee_h, hock_h, hoof_h=0.06):
    for sx in (-1, 1):
        x = sx * fx
        c.capsule((x, fy, top_f), (x * 0.95, fy - 0.02, knee_h), r_top, r_knee * 1.2)
        c.capsule((x * 0.95, fy - 0.02, knee_h), (x * 0.93, fy - 0.03, hoof_h * 2), r_knee, r_cannon)
        c.ball((x * 0.95, fy - 0.02, knee_h), r_knee * 1.25)
        c.ball((x * 0.93, fy - 0.03, hoof_h * 1.9), r_cannon * 1.2)
        c.capsule((x * 0.93, fy - 0.03, hoof_h * 1.9), (x * 0.93, fy - 0.045, hoof_h), r_cannon * 1.05, r_cannon)
        x = sx * hx
        c.capsule((x, hy, top_h), (x * 0.92, hy + 0.1 * (top_h - hock_h), hock_h + (top_h - hock_h) * 0.4), r_top * 1.25, r_knee * 1.5)
        c.capsule((x * 0.92, hy + 0.1 * (top_h - hock_h), hock_h + (top_h - hock_h) * 0.4), (x * 0.9, hy + 0.2 * (top_h - hock_h), hock_h),
                  r_knee * 1.4, r_knee)
        c.ball((x * 0.9, hy + 0.2 * (top_h - hock_h) + 0.01, hock_h), r_knee * 1.2)
        c.capsule((x * 0.9, hy + 0.2 * (top_h - hock_h), hock_h), (x * 0.9, hy + 0.1 * (top_h - hock_h), hoof_h * 1.9), r_knee, r_cannon)
        c.ball((x * 0.9, hy + 0.1 * (top_h - hock_h), hoof_h * 1.9), r_cannon * 1.2)
        c.capsule((x * 0.9, hy + 0.1 * (top_h - hock_h), hoof_h * 1.9), (x * 0.9, hy + 0.1 * (top_h - hock_h) - 0.015, hoof_h),
                  r_cannon * 1.05, r_cannon)


def hooves(prefix, M, pts, r, h):
    hb = H.HB()
    for (x, y) in pts:
        for dx in (-r * 0.75, r * 0.75):
            hb.lathe(M["hoof"], [(0.0, 0.0), (r, 0.0), (r * 0.96, h * 0.4), (r * 0.76, h * 0.93), (0.0, h)], 14, x + dx, y, 0.0)
    me = hb.to_mesh("ME_%s_Hooves" % prefix, recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    CL_COLL[0].objects.link(bpy.data.objects.new("GEO_%s_Hooves" % prefix, me))


def tail(prefix, M, pts, radii, coat, switch_mat, sw_r):
    BU.tube("GEO_%s_Tail" % prefix, pts, radii, coat, 10)
    sw = CL.Clay(prefix + "_TailSwitch", sw_r * 0.2)
    end = np.asarray(pts[-1], float)
    for k in range(4):
        sw.ellipsoid(tuple(end + np.array([0, 0, -k * sw_r * 1.2])), sw_r * (1 - 0.12 * k), sw_r * (1 - 0.12 * k), sw_r * 1.6)
    sw.to_mesh(switch_mat, 2, CL_COLL[0])


def udder(c, y, z, s):
    c.ellipsoid((0, y, z), 0.1 * s, 0.1 * s, 0.07 * s)
    for sx in (-1, 1):
        for dy in (-1, 1):
            c.capsule((sx * 0.04 * s, y + dy * 0.04 * s, z - 0.05 * s), (sx * 0.04 * s, y + dy * 0.04 * s, z - 0.1 * s), 0.012 * s, 0.009 * s, 4)


def nostrils(prefix, M, y, z, dx, r):
    hb = H.HB()
    for sx in (-1, 1):
        hb.ellipsoid(sx * dx, y, z, r, r * 0.5, r * 1.3, M["nostril"], 12, 6)
    CL_COLL[0].objects.link(bpy.data.objects.new("GEO_%s_Nostrils" % prefix, hb.to_mesh("ME_%s_Nostrils" % prefix, recalc=False)))


# ============================================================================ species
def cow(M):
    new_coll("CHR_Animal_Cow_001")
    coat = mat_coat("MAT_Coat_Cow_RedWhite", "#7A4128", patch="#E7DED0", patch_amt=0.42, dark="#5A2E1C", dark_from=0.3,
                    muzzle="#3A2B26", muzzle_y=-1.12)
    c = CL.Clay("Cow001_Body", 0.011)
    c.ellipsoid((0, 0.05, 0.92), 0.24, 0.55, 0.26)
    c.ellipsoid((0, -0.02, 0.8), 0.22, 0.38, 0.2)
    c.ellipsoid((0, -0.38, 0.93), 0.21, 0.24, 0.28)
    c.ellipsoid((0, 0.48, 0.95), 0.22, 0.25, 0.25)
    c.ellipsoid((0, 0.62, 1.04), 0.15, 0.11, 0.12)
    c.ellipsoid((0, -0.38, 1.17), 0.08, 0.11, 0.08, CL.q_axis((1, 0, 0), -0.3))
    c.ellipsoid((0, -0.2, 1.12), 0.13, 0.22, 0.07)
    c.capsule((0, -0.55, 1.03), (0, -0.82, 1.1), 0.12, 0.09)
    c.ellipsoid((0, -0.95, 1.1), 0.088, 0.1, 0.1)
    c.capsule((0, -0.97, 1.06), (0, -1.15, 0.88), 0.074, 0.06)
    c.ellipsoid((0, -1.17, 0.86), 0.064, 0.055, 0.055)
    for k in range(6):
        t = k / 5
        c.ellipsoid((0, -0.48 - 0.42 * t, 0.8 + 0.2 * t ** 1.4), 0.025, 0.07, 0.09 - 0.04 * t)
    udder(c, 0.34, 0.63, 1.0)
    legs(c, 0.145, -0.42, 0.14, 0.5, 0.86, 0.9, 0.085, 0.045, 0.032, 0.46, 0.44)
    c.capsule((0, 0.68, 1.06), (0, 0.74, 0.96), 0.035, 0.025)
    c.to_mesh(coat, 5, CL_COLL[0])
    tail("Cow001", M, [(0, 0.72, 1.0), (0, 0.76, 0.8), (0.01, 0.77, 0.6), (0.02, 0.76, 0.42)], [0.02, 0.015, 0.012, 0.01],
         coat, M["dark_hair"], 0.028)
    hooves("Cow001", M, [(-0.135, -0.465), (0.135, -0.465), (-0.126, 0.55), (0.126, 0.55)], 0.022, 0.065)
    ears = CL.Clay("Cow001_Ears", 0.004)
    for sx in (-1, 1):                                                        # long drooping ears
        ears.ellipsoid((sx * 0.14, -0.92, 1.03), 0.12, 0.04, 0.022, CL.q_axis((0, 1, 0), sx * -1.05))
        ears.ellipsoid((sx * 0.145, -0.927, 1.03), 0.09, 0.026, 0.012, CL.q_axis((0, 1, 0), sx * -1.05), neg=True)
    ears.to_mesh(coat, 3, CL_COLL[0])
    for sx in (-1, 1):
        BU.tube("GEO_Cow001_Horn_%s" % ("L" if sx < 0 else "R"),
                [(sx * 0.05, -0.9, 1.17), (sx * 0.09, -0.88, 1.22), (sx * 0.115, -0.84, 1.27), (sx * 0.115, -0.8, 1.31)],
                [0.026, 0.02, 0.013, 0.007], M["horn_plain"], 12, 6)
    eyes("Cow001", M, [(-0.085, -1.0, 1.11), (0.085, -1.0, 1.11)], 0.018, M["lid_dark"])
    nostrils("Cow001", M, -1.222, 0.865, 0.026, 0.01)


def buffalo(M):
    new_coll("CHR_Animal_Buffalo_001")
    coat = mat_coat("MAT_Coat_Buffalo_Black", "#2A2626", dark="#161414", dark_from=0.35, muzzle="#0F0D0D", muzzle_y=-1.17,
                    rough=0.72, sheen=0.45, patch="#3A3433", patch_amt=0.35, patch_scale=6.0)
    c = CL.Clay("Buffalo001_Body", 0.012)
    c.ellipsoid((0, 0.05, 0.9), 0.3, 0.6, 0.3)
    c.ellipsoid((0, -0.02, 0.76), 0.28, 0.42, 0.22)
    c.ellipsoid((0, -0.42, 0.9), 0.27, 0.27, 0.32)
    c.ellipsoid((0, 0.52, 0.94), 0.27, 0.28, 0.28)
    c.ellipsoid((0, 0.66, 1.03), 0.18, 0.12, 0.13)
    c.ellipsoid((0, -0.1, 1.1), 0.22, 0.55, 0.11)
    c.ellipsoid((0, 0.2, 1.08), 0.24, 0.35, 0.1)
    c.capsule((0, -0.6, 1.0), (0, -0.85, 0.98), 0.15, 0.12)
    c.ellipsoid((0, -0.95, 1.0), 0.1, 0.11, 0.1)
    c.capsule((0, -0.98, 0.97), (0, -1.18, 0.78), 0.09, 0.077)
    c.ellipsoid((0, -1.21, 0.76), 0.085, 0.07, 0.066)
    udder(c, 0.36, 0.6, 1.15)
    legs(c, 0.17, -0.45, 0.17, 0.52, 0.82, 0.86, 0.1, 0.05, 0.036, 0.42, 0.4)
    c.capsule((0, 0.72, 1.04), (0, 0.78, 0.94), 0.04, 0.028)
    c.to_mesh(coat, 5, CL_COLL[0])
    tail("Buffalo001", M, [(0, 0.77, 0.98), (0, 0.8, 0.78), (0.01, 0.8, 0.56), (0.02, 0.79, 0.4)], [0.022, 0.016, 0.012, 0.01],
         coat, M["dark_hair"], 0.028)
    hooves("Buffalo001", M, [(-0.158, -0.495), (0.158, -0.495), (-0.153, 0.57), (0.153, 0.57)], 0.026, 0.07)
    ears = CL.Clay("Buffalo001_Ears", 0.004)
    for sx in (-1, 1):
        ears.ellipsoid((sx * 0.15, -0.9, 0.97), 0.08, 0.035, 0.02, CL.q_axis((0, 1, 0), sx * -0.3))
    ears.to_mesh(coat, 3, CL_COLL[0])
    for sx in (-1, 1):                                                        # tight curled horns (flattened)
        pts = [(sx * 0.07, -0.95, 1.09), (sx * 0.15, -0.9, 1.15), (sx * 0.23, -0.8, 1.15), (sx * 0.26, -0.68, 1.07),
               (sx * 0.23, -0.6, 0.97), (sx * 0.17, -0.62, 0.9), (sx * 0.14, -0.7, 0.92), (sx * 0.16, -0.75, 0.98)]
        o, _ = BU.tube("GEO_Buffalo001_Horn_%s" % ("L" if sx < 0 else "R"), pts, [0.055, 0.05, 0.044, 0.036, 0.028, 0.02, 0.014, 0.008],
                       M["horn_dark"], 12, 6)
    eyes("Buffalo001", M, [(-0.095, -0.99, 1.0), (0.095, -0.99, 1.0)], 0.019, M["lid_black"])
    nostrils("Buffalo001", M, -1.272, 0.765, 0.034, 0.012)


def goat(M):
    new_coll("CHR_Animal_Goat_001")
    coat = mat_coat("MAT_Coat_Goat_BrownWhite", "#4E3220", patch="#E9E2D4", patch_amt=0.38, patch_scale=4.0,
                    muzzle="#2A1E18", muzzle_y=-0.54)
    c = CL.Clay("Goat001_Body", 0.006)
    c.ellipsoid((0, 0.02, 0.5), 0.13, 0.29, 0.14)
    c.ellipsoid((0, -0.19, 0.51), 0.12, 0.13, 0.16)
    c.ellipsoid((0, 0.24, 0.52), 0.12, 0.13, 0.13)
    c.ellipsoid((0, 0.32, 0.57), 0.08, 0.06, 0.06)
    c.capsule((0, -0.26, 0.58), (0, -0.37, 0.72), 0.058, 0.044)
    c.ellipsoid((0, -0.41, 0.76), 0.048, 0.058, 0.052)
    c.capsule((0, -0.43, 0.74), (0, -0.54, 0.66), 0.038, 0.029)
    c.ellipsoid((0, -0.555, 0.65), 0.027, 0.028, 0.027)
    legs(c, 0.075, -0.2, 0.075, 0.26, 0.45, 0.47, 0.045, 0.022, 0.016, 0.24, 0.24, 0.035)
    c.capsule((0, 0.33, 0.58), (0, 0.37, 0.65), 0.02, 0.012)                  # short tail, up
    c.to_mesh(coat, 4, CL_COLL[0])
    hooves("Goat001", M, [(-0.07, -0.23), (0.07, -0.23), (-0.0675, 0.28), (0.0675, 0.28)], 0.011, 0.035)
    ears = CL.Clay("Goat001_Ears", 0.0025)
    for sx in (-1, 1):                                                        # long floppy ears
        ears.ellipsoid((sx * 0.06, -0.43, 0.7), 0.09, 0.026, 0.012, CL.q_axis((0, 1, 0), sx * -1.2))
    ears.to_mesh(coat, 2, CL_COLL[0])
    for sx in (-1, 1):
        BU.tube("GEO_Goat001_Horn_%s" % ("L" if sx < 0 else "R"),
                [(sx * 0.022, -0.42, 0.8), (sx * 0.03, -0.39, 0.84), (sx * 0.04, -0.34, 0.86), (sx * 0.05, -0.3, 0.84)],
                [0.013, 0.01, 0.007, 0.003], M["horn_plain"], 10, 6)
    beard = CL.Clay("Goat001_Beard", 0.002)
    beard.ellipsoid((0, -0.52, 0.6), 0.012, 0.012, 0.035)
    beard.to_mesh(M["dark_hair"], 2, CL_COLL[0])
    eyes("Goat001", M, [(-0.04, -0.45, 0.77), (0.04, -0.45, 0.77)], 0.0105, M["lid_dark"])
    nostrils("Goat001", M, -0.582, 0.655, 0.012, 0.005)


def dog(M):
    new_coll("CHR_Animal_Dog_001")
    coat = mat_coat("MAT_Coat_Dog_Fawn", "#B07A45", belly=("#E6D2B0", 0.36), muzzle="#3A281C", muzzle_y=-0.47, rough=0.55)
    c = CL.Clay("Dog001_Body", 0.005)
    c.ellipsoid((0, -0.14, 0.43), 0.085, 0.12, 0.125)                         # deep chest
    c.ellipsoid((0, 0.04, 0.45), 0.075, 0.16, 0.085)
    c.ellipsoid((0, 0.13, 0.44), 0.062, 0.09, 0.065)                          # tucked waist
    c.ellipsoid((0, 0.23, 0.44), 0.075, 0.09, 0.085)
    c.capsule((0, -0.21, 0.49), (0, -0.29, 0.6), 0.055, 0.045)
    c.ellipsoid((0, -0.33, 0.63), 0.052, 0.058, 0.05)
    c.capsule((0, -0.37, 0.615), (0, -0.47, 0.585), 0.03, 0.021)
    for sx in (-1, 1):
        x = sx * 0.05
        c.capsule((x, -0.15, 0.38), (x, -0.16, 0.2), 0.04, 0.024)
        c.capsule((x, -0.16, 0.2), (x, -0.165, 0.04), 0.021, 0.017)
        c.ellipsoid((x, -0.18, 0.018), 0.019, 0.03, 0.017)                     # paw
        x = sx * 0.05
        c.capsule((x, 0.24, 0.42), (x, 0.28, 0.25), 0.055, 0.028)
        c.capsule((x, 0.28, 0.25), (x, 0.31, 0.14), 0.025, 0.019)
        c.capsule((x, 0.31, 0.14), (x, 0.29, 0.04), 0.019, 0.017)
        c.ellipsoid((x, 0.275, 0.018), 0.019, 0.03, 0.017)
    c.to_mesh(coat, 4, CL_COLL[0])
    BU.tube("GEO_Dog001_Tail", [(0, 0.3, 0.48), (0, 0.36, 0.56), (0, 0.33, 0.63), (0.02, 0.27, 0.63), (0.03, 0.245, 0.585)],
            [0.022, 0.02, 0.018, 0.015, 0.01], coat, 10)
    ears = CL.Clay("Dog001_Ears", 0.002)
    for sx in (-1, 1):                                                        # upright pointed ears
        base = np.array([sx * 0.032, -0.31, 0.665])
        ears.chain([base, base + np.array([sx * 0.008, 0.005, 0.035]), base + np.array([sx * 0.014, 0.008, 0.062])],
                   [0.018, 0.011, 0.004])
    ears.to_mesh(coat, 2, CL_COLL[0])
    sphere("GEO_Dog001_Nose", (0, -0.483, 0.592), (0.013, 0.01, 0.01), M["nostril"])
    eyes("Dog001", M, [(-0.03, -0.37, 0.645), (0.03, -0.37, 0.645)], 0.0095, M["lid_dark"])


def hen(M):
    new_coll("CHR_Animal_Hen_001")
    feath = mat_coat("MAT_Feathers_Hen_Brown", "#8A4A22", patch="#5A2E14", patch_amt=0.45, patch_scale=18.0,
                     rough=0.7, sheen=0.5)
    neck = CL.mat_principled("MAT_Feathers_Hen_Gold", "#B9772F", 0.6, sheen=0.5, noise=0.25, noise_scale=120)
    red = CL.mat_principled("MAT_Comb_Red", "#B8221C", 0.45, noise=0.1, noise_scale=80)
    yellow = CL.mat_principled("MAT_Beak_Legs_Yellow", "#D9A23A", 0.5)
    c = CL.Clay("Hen001_Body", 0.003)
    c.ellipsoid((0, 0.02, 0.23), 0.085, 0.12, 0.095, CL.q_axis((1, 0, 0), 0.25))
    c.ellipsoid((0, -0.06, 0.22), 0.075, 0.075, 0.085)
    c.ellipsoid((0, 0.1, 0.27), 0.06, 0.06, 0.06)
    for sx in (-1, 1):
        c.ellipsoid((sx * 0.07, 0.03, 0.24), 0.028, 0.09, 0.055, CL.q_axis((1, 0, 0), 0.25))     # wings
    c.to_mesh(feath, 3, CL_COLL[0])
    n = CL.Clay("Hen001_Neck", 0.0025)
    n.capsule((0, -0.07, 0.29), (0, -0.095, 0.36), 0.042, 0.03)
    n.ellipsoid((0, -0.105, 0.385), 0.028, 0.034, 0.03)
    n.to_mesh(neck, 3, CL_COLL[0])
    hb = H.HB()
    for k in range(9):                                                          # tail fan
        a = math.radians(-50 + k * 12.5)
        base = np.array([0.0, 0.1, 0.29])
        d = np.array([math.sin(a) * 0.35, 0.55, 0.75])
        d /= np.linalg.norm(d)
        side = np.cross(d, [0, 1, 0])
        side /= np.linalg.norm(side) + 1e-9
        L = 0.12 + 0.03 * math.cos(a * 2)
        pts = [base + d * L * t + np.array([0, 0.04 * t * t, -0.02 * t * t]) for t in np.linspace(0, 1, 6)]
        V = []
        for j, p in enumerate(pts):
            w = 0.018 * math.sin(math.pi * min(1.0, 0.15 + j / 5.0))
            V += [tuple(p - side * w), tuple(p + side * w)]
        hb.add(V, [(2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2) for j in range(5)], feath)
    me = hb.to_mesh("ME_Hen001_Tail", recalc=False)
    o = bpy.data.objects.new("GEO_Hen001_Tail", me)
    CL_COLL[0].objects.link(o)
    o.modifiers.new("Thick", "SOLIDIFY").thickness = 0.002
    comb = CL.Clay("Hen001_Comb", 0.0015)
    for k in range(5):
        comb.ellipsoid((0, -0.125 + k * 0.012, 0.413 + 0.006 * math.sin(math.pi * k / 4)), 0.004, 0.007, 0.01 + 0.003 * (k % 2))
    for sx in (-1, 1):
        comb.ellipsoid((sx * 0.006, -0.128, 0.352), 0.006, 0.006, 0.011)
    comb.to_mesh(red, 1, CL_COLL[0])
    hb = H.HB()
    hb.frustum(0, 0, 0, 0.02, 0.008, 0.0005, 10, yellow)
    me = hb.to_mesh("ME_Hen001_Beak", recalc=False)
    beak = bpy.data.objects.new("GEO_Hen001_Beak", me)
    CL_COLL[0].objects.link(beak)
    beak.location = (0, -0.135, 0.38)
    beak.rotation_euler = (math.radians(100), 0, 0)
    for sx in (-1, 1):                                                          # legs + toes
        hip = np.array([sx * 0.03, 0.02, 0.16])
        knee = np.array([sx * 0.032, 0.03, 0.09])
        ft = np.array([sx * 0.032, 0.015, 0.012])
        hb = H.HB()
        hb.rod(yellow, hip, knee, 0.006, 8)
        hb.rod(yellow, knee, ft, 0.005, 8)
        for a in (-0.45, 0.0, 0.45):
            hb.rod(yellow, ft, ft + np.array([math.sin(a) * 0.04, -math.cos(a) * 0.04, -0.008]), 0.003, 6)
        hb.rod(yellow, ft, ft + np.array([0, 0.025, -0.006]), 0.003, 6)
        me = hb.to_mesh("ME_Hen001_Leg", recalc=False)
        CL_COLL[0].objects.link(bpy.data.objects.new("GEO_Hen001_Leg_%s" % ("L" if sx < 0 else "R"), me))
    eyes("Hen001", {"eye": M["eye_amber"]}, [(-0.022, -0.115, 0.392), (0.022, -0.115, 0.392)], 0.006, neck)


# ============================================================================
def main():
    global LIB
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "LIB_Animals_Farm"
    LIB = bpy.data.collections.new("LIB_ANIMALS")
    sc.collection.children.link(LIB)
    M = {
        "dark_hair": CL.mat_principled("MAT_Hair_Tail_Switch", "#1E1B1A", 0.55, sheen=0.4, noise=0.3, noise_scale=200),
        "hoof": CL.mat_principled("MAT_Hoof_Dark", "#2B2622", 0.5, noise=0.2, noise_scale=60),
        "horn_plain": CL.mat_principled("MAT_Horn_Plain", "#6B5A49", 0.45, noise=0.25, noise_scale=40),
        "horn_dark": CL.mat_principled("MAT_Horn_Buffalo", "#26221F", 0.4, noise=0.25, noise_scale=40),
        "eye": CL.mat_principled("MAT_Eye_Bovine", "#1A120D", 0.05, coat=1.0),
        "eye_amber": CL.mat_principled("MAT_Eye_Bird_Amber", "#B5701C", 0.05, coat=1.0),
        "nostril": CL.mat_principled("MAT_Nostril", "#0E0B0A", 0.4),
        "lid_dark": CL.mat_principled("MAT_Lid_Dark", "#2E2420", 0.6),
        "lid_black": CL.mat_principled("MAT_Lid_Black", "#141212", 0.5),
    }
    cow(M)
    buffalo(M)
    goat(M)
    dog(M)
    hen(M)
    for o in list(sc.collection.objects):
        if o.type == "META":
            bpy.data.objects.remove(o, do_unlink=True)
    for ch in LIB.children:
        bpy.context.view_layer.layer_collection.children["LIB_ANIMALS"].children[ch.name].exclude = True
    # lineup stage: bullock (linked) + the five, side by side, facing the camera's left
    stage = bpy.data.collections.new("STAGE_LINEUP")
    sc.collection.children.link(stage)
    lib = {c.name: c for c in LIB.children}
    with bpy.data.libraries.load(BULL_BLEND, link=True, relative=True) as (src, dst):
        dst.collections = [n for n in src.collections if n == "CHR_Animal_Bullock_001"]
    if dst.collections and dst.collections[0]:
        lib["CHR_Animal_Bullock_001"] = dst.collections[0]
    order = [("CHR_Animal_Bullock_001", -4.6), ("CHR_Animal_Buffalo_001", -2.2), ("CHR_Animal_Cow_001", 0.2),
             ("CHR_Animal_Goat_001", 2.1), ("CHR_Animal_Dog_001", 3.15), ("CHR_Animal_Hen_001", 3.95)]
    for name, x in order:
        if name not in lib:
            continue
        e = bpy.data.objects.new("STG_" + name, None)
        e.instance_type = "COLLECTION"
        e.instance_collection = lib[name]
        e.location = (x, 0, 0)
        e.rotation_euler = (0, 0, math.radians(90))
        stage.objects.link(e)
    quick = "--quick" in ARGS
    cams = {
        "CAM_Lineup_Side":   ((-0.3, -11.0, 0.9), (-0.3, 0.0, 0.6), 50, 2000, 900),
        "CAM_Lineup_34":     ((6.0, -8.5, 2.6), (-0.4, 0.0, 0.55), 45, 2000, 1100),
        "CAM_Cow_Buffalo":   ((-1.0, -4.4, 1.2), (-1.0, 0.0, 0.8), 50, 1500, 1000),
        "CAM_Goat_Dog_Hen":  ((3.05, -2.4, 0.75), (3.05, 0.0, 0.38), 45, 1500, 1000),
        "CAM_Heads":         ((0.2, -2.6, 1.3), (-1.2, 0.0, 0.95), 60, 1500, 1000),
    }
    if quick:
        cams = {k: (p, t, l, rx * 2 // 3, ry * 2 // 3) for k, (p, t, l, rx, ry) in cams.items()}
    objs = CL.review_stage(cams, OUT_REVIEW, "Animals", samples=48 if quick else 128)
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_Animals_Farm_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[char] saved", OUT_BLEND, "animals:", [c.name for c in LIB.children])
    if "--render" in ARGS:
        only = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
        CL.render_cams(objs, OUT_REVIEW, only)


if __name__ == "__main__":
    main()
