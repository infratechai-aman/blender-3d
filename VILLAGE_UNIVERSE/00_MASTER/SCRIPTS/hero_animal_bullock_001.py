"""
FIRST ANIMAL - style test (G7 gate).  CHR_Animal_Bullock_001: desi zebu bullock (bail), silver-grey,
dark forequarters, big hump, dewlap, lyre horns with painted tips and brass caps, nose rope + halter, neck bell.

  blender -b --factory-startup --python hero_animal_bullock_001.py -- [--render] [--quick] [--only CAM_A,CAM_B]

Output: 04_CHARACTERS/ANIMALS/CHR_Animal_Bullock_001.blend (collection CHR_Animal_Bullock_001)
Reviews: 10_EXPORTS/REVIEWS/G7_ANIMAL_BULLOCK_001_v001/
Body = clay metaballs (barrel, shoulders, hump, haunches, legs, neck, skull, muzzle, dewlap); horns = swept
tubes; eyes = glossy eyeballs with lids.  Standing pose, faces -Y, height at withers ~1.38 m.  NOT rigged yet.
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
import hero_lib as H  # noqa: E402
from geo import catmull_rom  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "04_CHARACTERS", "ANIMALS", "CHR_Animal_Bullock_001.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "G7_ANIMAL_BULLOCK_001_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
COLL = None


def mat_coat(name):
    """Zebu coat: silver-white body, charcoal neck/hump/shoulders and lower legs, dark muzzle; soft mottling."""
    m, t = H._mat(name, "#CFCAC0")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=obj)
    y, z = sx.outputs["Y"], sx.outputs["Z"]
    n = t.noise(obj, 3.0, 5.0, 0.55)
    fine = t.noise(obj, 40.0, 6.0, 0.6)
    yn = t.math("ADD", y, t.math("MULTIPLY", t.math("SUBTRACT", n.outputs["Fac"], 0.5), 0.25))
    fore = t.n("ShaderNodeMapRange", Value=yn, **{"From Min": -0.15, "From Max": -0.6, "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
    high = t.n("ShaderNodeMapRange", Value=z, **{"From Min": 0.75, "From Max": 1.05, "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
    face = t.n("ShaderNodeMapRange", Value=yn, **{"From Min": -0.95, "From Max": -1.12, "To Min": 1.0, "To Max": 0.25}).outputs["Result"]
    dark = t.math("MULTIPLY", t.math("MULTIPLY", fore, high), face)
    legs = t.n("ShaderNodeMapRange", Value=z, **{"From Min": 0.35, "From Max": 0.12, "To Min": 0.0, "To Max": 0.8}).outputs["Result"]
    muzzle = t.n("ShaderNodeMapRange", Value=y, **{"From Min": -1.27, "From Max": -1.33, "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
    body = t.ramp(fine.outputs["Fac"], [(0.3, H.hex_lin("#C2BDB3")), (0.7, H.hex_lin("#DAD5CB"))])
    col = t.mix(t.math("MINIMUM", t.math("MAXIMUM", dark, legs), 1.0), body, H.hex_lin("#5E5955"))
    col = t.mix(muzzle, col, H.hex_lin("#2A2624"))
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.inp(b, "Roughness").default_value = 0.62
    try:
        t.inp(b, "Sheen Weight").default_value = 0.35
        t.inp(b, "Subsurface Weight").default_value = 0.05
    except Exception:
        pass
    hair = t.n("ShaderNodeMapping", Vector=obj, Scale=(300.0, 60.0, 300.0))
    hn = t.noise(hair.outputs[0], 1.0, 3.0, 0.6)
    t.link(t.bump(t.math("ADD", hn.outputs["Fac"], t.math("MULTIPLY", n.outputs["Fac"], 0.5)), 0.12, 0.004), t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def mat_horn(name):
    """Horn: dark keratin base, painted saffron/turquoise bands toward the tip (festival paint, worn)."""
    m, t = H._mat(name, "#4E443B")
    uv = t.n("ShaderNodeUVMap").outputs["UV"]
    v = t.n("ShaderNodeSeparateXYZ", Vector=uv).outputs["Y"]
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n = t.noise(obj, 30.0, 6.0, 0.6)
    base = t.ramp(n.outputs["Fac"], [(0.3, H.hex_lin("#3F362F")), (0.7, H.hex_lin("#6A5C4E"))])
    band1 = t.math("MULTIPLY", t.math("GREATER_THAN", v, 0.55), t.math("LESS_THAN", v, 0.78))
    band2 = t.math("GREATER_THAN", v, 0.78)
    wear = t.math("GREATER_THAN", n.outputs["Fac"], 0.38)
    col = t.mix(t.math("MULTIPLY", band1, wear), base, H.hex_lin("#D9661F"))
    col = t.mix(t.math("MULTIPLY", band2, wear), col, H.hex_lin("#1E8C8A"))
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.inp(b, "Roughness").default_value = 0.45
    t.link(t.bump(n.outputs["Fac"], 0.3, 0.002), t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def tube(name, pts, radii, mat, ring=14, per=8):
    P = catmull_rom([tuple(p) for p in pts], per)
    R = np.interp(np.linspace(0, 1, len(P)), np.linspace(0, 1, len(radii)), radii)
    V, UV = [], []
    prev = None
    for k in range(len(P)):
        tg = P[min(k + 1, len(P) - 1)] - P[max(k - 1, 0)]
        tg /= np.linalg.norm(tg)
        if prev is None:
            a = np.cross(tg, [0, 0, 1.0])
            if np.linalg.norm(a) < 1e-3:
                a = np.cross(tg, [1, 0, 0])
        else:
            a = prev - tg * (prev @ tg)
        a /= np.linalg.norm(a)
        prev = a
        b = np.cross(tg, a)
        for i in range(ring):
            th = 2 * math.pi * i / ring
            V.append(P[k] + (a * math.cos(th) + b * math.sin(th)) * R[k])
            UV.append((i / ring, k / (len(P) - 1)))
    F = []
    for k in range(len(P) - 1):
        for i in range(ring):
            a0 = k * ring + i
            b0 = k * ring + (i + 1) % ring
            F.append((a0, b0, b0 + ring, a0 + ring))
    tip = len(V)
    V.append(P[-1] + (P[-1] - P[-2]) / np.linalg.norm(P[-1] - P[-2]) * R[-1] * 0.6)
    UV.append((0.5, 1.0))
    for i in range(ring):
        F.append(((len(P) - 1) * ring + i, (len(P) - 1) * ring + (i + 1) % ring, tip))
    o = CL.mesh_obj(name, V, F, mat, COLL)
    CL.set_uv(o, UV)
    return o, P


def build(M):
    c = CL.Clay("Bullock001_Body", 0.012)
    c.ellipsoid((0, 0.08, 0.98), 0.27, 0.6, 0.29)                       # barrel
    c.ellipsoid((0, -0.05, 0.86), 0.25, 0.42, 0.2)                      # belly
    c.ellipsoid((0, -0.42, 1.0), 0.25, 0.26, 0.33)                      # chest / shoulders
    c.ellipsoid((0, 0.52, 1.03), 0.25, 0.27, 0.28)                      # haunches
    c.ellipsoid((0, 0.68, 1.12), 0.17, 0.12, 0.14)                      # pin bones / rump
    c.ellipsoid((0, -0.42, 1.36), 0.11, 0.16, 0.16, CL.q_axis((1, 0, 0), -0.35))   # hump
    c.ellipsoid((0, -0.25, 1.24), 0.15, 0.25, 0.08)                     # withers -> back
    c.capsule((0, -0.6, 1.12), (0, -0.9, 1.2), 0.15, 0.115)             # neck
    c.ellipsoid((0, -1.05, 1.21), 0.105, 0.12, 0.12)                    # skull
    c.capsule((0, -1.08, 1.17), (0, -1.28, 0.98), 0.09, 0.07)           # face
    c.ellipsoid((0, -1.31, 0.95), 0.078, 0.065, 0.066)                  # muzzle
    for k in range(7):                                                   # dewlap folds
        t = k / 6
        c.ellipsoid((0, -0.5 - 0.5 * t, 0.84 + 0.22 * t ** 1.4), 0.03, 0.08, 0.13 - 0.06 * t)
    c.ellipsoid((0, 0.05, 0.69), 0.05, 0.08, 0.05)                      # sheath
    for sx in (-1, 1):
        x = sx * 0.165
        c.capsule((x, -0.46, 0.92), (x * 0.95, -0.49, 0.5), 0.1, 0.06)   # forearm
        c.capsule((x * 0.95, -0.49, 0.5), (x * 0.93, -0.5, 0.13), 0.045, 0.035)
        c.ball((x * 0.95, -0.49, 0.5), 0.05)                            # knee
        c.ball((x * 0.93, -0.5, 0.12), 0.042)                           # fetlock
        c.capsule((x * 0.93, -0.5, 0.12), (x * 0.93, -0.53, 0.06), 0.036, 0.034)
        c.capsule((x, 0.52, 0.98), (x * 0.92, 0.62, 0.62), 0.13, 0.075)  # gaskin
        c.capsule((x * 0.92, 0.62, 0.62), (x * 0.9, 0.72, 0.46), 0.07, 0.05)
        c.ball((x * 0.9, 0.73, 0.46), 0.05)                             # hock
        c.capsule((x * 0.9, 0.72, 0.46), (x * 0.9, 0.62, 0.13), 0.042, 0.035)
        c.ball((x * 0.9, 0.62, 0.12), 0.042)
        c.capsule((x * 0.9, 0.62, 0.12), (x * 0.9, 0.59, 0.06), 0.036, 0.034)
    c.capsule((0, 0.75, 1.13), (0, 0.82, 1.0), 0.04, 0.03)               # tail root
    body = c.to_mesh(M["coat"], 5, COLL)
    # tail + switch
    tube("GEO_Bullock001_Tail", [(0, 0.8, 1.04), (0, 0.84, 0.85), (0.01, 0.85, 0.62), (0.02, 0.84, 0.42)],
         [0.025, 0.018, 0.014, 0.012], M["coat"], 10)
    sw = CL.Clay("Bullock001_TailSwitch", 0.006)
    for k in range(5):
        sw.ellipsoid((0.02, 0.84, 0.4 - k * 0.04), 0.03 - k * 0.003, 0.03 - k * 0.003, 0.05)
    sw.to_mesh(M["dark_hair"], 3, COLL)
    # hooves (cloven)
    hb = H.HB()
    for (x, y) in ((-0.153, -0.535), (0.153, -0.535), (-0.148, 0.585), (0.148, 0.585)):
        for dx in (-0.019, 0.019):
            hb.lathe(M["hoof"], [(0.0, 0.0), (0.025, 0.0), (0.024, 0.03), (0.019, 0.07), (0.0, 0.075)], 14, x + dx, y - 0.01, 0.0)
    me = hb.to_mesh("ME_Bullock001_Hooves", recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    COLL.objects.link(bpy.data.objects.new("GEO_Bullock001_Hooves", me))
    # ears (drooping, slightly cupped)
    ears = CL.Clay("Bullock001_Ears", 0.004)
    for sx in (-1, 1):
        ears.ellipsoid((sx * 0.155, -1.0, 1.2), 0.1, 0.045, 0.02, CL.q_axis((0, 1, 0), sx * -0.55))
        ears.ellipsoid((sx * 0.16, -1.007, 1.205), 0.075, 0.03, 0.012, CL.q_axis((0, 1, 0), sx * -0.55), neg=True)
    ears.to_mesh(M["coat"], 3, COLL)
    # horns: lyre curve, painted bands, brass tips
    for sx in (-1, 1):
        pts = [(sx * 0.06, -1.0, 1.29), (sx * 0.11, -0.99, 1.35), (sx * 0.17, -0.97, 1.44), (sx * 0.2, -0.95, 1.55),
               (sx * 0.19, -0.96, 1.65), (sx * 0.15, -0.99, 1.72)]
        o, P = tube("GEO_Bullock001_Horn_%s" % ("L" if sx < 0 else "R"), pts, [0.042, 0.034, 0.027, 0.02, 0.014, 0.009],
                    M["horn"], 16, 8)
        tipc = P[-1]
        hb = H.HB()
        hb.ellipsoid(tipc[0], tipc[1], tipc[2] + 0.012, 0.012, 0.012, 0.02, M["brass"], 12, 8)
        me = hb.to_mesh("ME_HornCap", recalc=False)
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        COLL.objects.link(bpy.data.objects.new("GEO_Bullock001_HornCap_%s" % ("L" if sx < 0 else "R"), me))
    # poll boss between the horns
    pb = CL.Clay("Bullock001_Poll", 0.004)
    pb.ellipsoid((0, -1.0, 1.29), 0.085, 0.055, 0.04)
    pb.to_mesh(M["coat"], 2, COLL)
    # eyes + lids
    for sx in (-1, 1):
        e = np.array([sx * 0.098, -1.115, 1.215])
        hb = H.HB()
        hb.ellipsoid(e[0], e[1], e[2], 0.019, 0.022, 0.017, M["eye"], 20, 12)
        me = hb.to_mesh("ME_BullEye", recalc=False)
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        COLL.objects.link(bpy.data.objects.new("GEO_Bullock001_Eye_%s" % ("L" if sx < 0 else "R"), me))
        lid = CL.Clay("Bullock001_Lid_%s" % ("L" if sx < 0 else "R"), 0.0025)
        lid.ellipsoid(tuple(e + np.array([sx * 0.002, 0.0, 0.012])), 0.02, 0.026, 0.011)
        lid.ellipsoid(tuple(e + np.array([sx * 0.002, 0.0, -0.013])), 0.019, 0.024, 0.008)
        lid.to_mesh(M["coat_dark"], 2, COLL)
    # nostrils (dark ovals) on the muzzle front
    hb = H.HB()
    for sx in (-1, 1):
        hb.ellipsoid(sx * 0.03, -1.372, 0.955, 0.012, 0.006, 0.016, M["nostril"], 12, 6)
    COLL.objects.link(bpy.data.objects.new("GEO_Bullock001_Nostrils", hb.to_mesh("ME_Nostrils", recalc=False)))
    # tack: nose rope (nath), halter, neck rope with brass bell
    rope = M["rope"]
    for sx in (-1, 1):
        tube("GEO_Bullock001_Halter_%s" % ("L" if sx < 0 else "R"),
             [(0, -1.35, 1.0), (sx * 0.075, -1.25, 1.03), (sx * 0.105, -1.12, 1.1), (sx * 0.11, -1.0, 1.21),
              (sx * 0.08, -0.97, 1.31), (0, -0.96, 1.33)], [0.008] * 6, rope, 8, 6)
    tube("GEO_Bullock001_NoseRope", [(0.03, -1.36, 0.955), (0.07, -1.33, 0.9), (0.1, -1.22, 0.78), (0.12, -1.05, 0.72),
                                     (0.16, -0.95, 0.78)], [0.007] * 5, rope, 8, 6)
    ring = []
    for k in range(25):
        a = 2 * math.pi * k / 24
        ring.append((0.15 * math.cos(a), -0.8 + 0.07 * math.sin(a) * 1.0 - 0.0, 1.13 + 0.13 * math.sin(a) - 0.02))
    ring = [(0.16 * math.cos(2 * math.pi * k / 24), -0.8 + 0.02 * math.sin(2 * math.pi * k / 24),
             1.12 + 0.16 * math.sin(2 * math.pi * k / 24)) for k in range(25)]
    tube("GEO_Bullock001_NeckRope", ring, [0.012] * 25, M["red_rope"], 8, 3)
    hb = H.HB()
    hb.lathe(M["brass"], [(0.0, 0.0), (0.05, 0.0), (0.048, 0.02), (0.04, 0.06), (0.03, 0.1), (0.012, 0.12), (0.0, 0.122)],
             20, 0.0, -0.81, 0.86)
    hb.ellipsoid(0.0, -0.81, 0.855, 0.014, 0.014, 0.014, M["brass"], 10, 6)
    me = hb.to_mesh("ME_Bell", recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    COLL.objects.link(bpy.data.objects.new("GEO_Bullock001_Bell", me))
    return body


def main():
    global COLL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "CHR_Animal_Bullock_001"
    sc.unit_settings.system = "METRIC"
    COLL = bpy.data.collections.new("CHR_Animal_Bullock_001")
    sc.collection.children.link(COLL)
    M = {
        "coat": mat_coat("MAT_Coat_Zebu_SilverGrey"),
        "coat_dark": CL.mat_principled("MAT_Coat_Zebu_Charcoal", "#4A4542", 0.6, sheen=0.3),
        "dark_hair": CL.mat_principled("MAT_Hair_Tail_Switch", "#1E1B1A", 0.55, sheen=0.4, noise=0.3, noise_scale=200),
        "hoof": CL.mat_principled("MAT_Hoof_Dark", "#2B2622", 0.5, noise=0.2, noise_scale=60),
        "horn": mat_horn("MAT_Horn_Painted"),
        "brass": CL.mat_principled("MAT_Metal_Brass", "#B8903A", 0.3, 1.0),
        "eye": CL.mat_principled("MAT_Eye_Bovine", "#1A120D", 0.05, coat=1.0),
        "nostril": CL.mat_principled("MAT_Nostril", "#0E0B0A", 0.4),
        "rope": H.mat_rope(),
        "red_rope": CL.mat_principled("MAT_Rope_Red_Wool", "#A3271F", 0.85, sheen=0.5, noise=0.2, noise_scale=150),
    }
    build(M)
    for o in list(sc.collection.objects):
        if o.type == "META":
            bpy.data.objects.remove(o, do_unlink=True)
    quick = "--quick" in ARGS
    cams = {
        "CAM_Side_L":       ((-4.6, 0.0, 0.9), (0.0, -0.1, 0.85), 50, 1600, 1100),
        "CAM_Front":        ((0.0, -4.4, 1.0), (0.0, -0.3, 0.9), 50, 1300, 1300),
        "CAM_ThreeQuarter": ((-3.2, -3.4, 1.4), (0.0, -0.2, 0.9), 50, 1600, 1100),
        "CAM_Back34":       ((2.8, 3.6, 1.5), (0.0, 0.0, 0.85), 50, 1600, 1100),
        "CAM_Head":         ((-0.9, -2.2, 1.35), (0.0, -1.1, 1.18), 70, 1300, 1100),
    }
    if quick:
        cams = {k: (p, t, l, rx * 2 // 3, ry * 2 // 3) for k, (p, t, l, rx, ry) in cams.items()}
    objs = CL.review_stage(cams, OUT_REVIEW, "Bullock001", samples=48 if quick else 128)
    sc.camera = objs["CAM_ThreeQuarter"][0]
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "CHR_Animal_Bullock_001_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[char] saved", OUT_BLEND, "objects:", len(COLL.objects))
    if "--render" in ARGS:
        only = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
        CL.render_cams(objs, OUT_REVIEW, only)


if __name__ == "__main__":
    main()
