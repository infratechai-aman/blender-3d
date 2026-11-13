"""
BATCH 4 - vegetation variety: new species with distinct silhouettes (complements LIB_Trees: mango, neem, palm,
peepal, amaltas, banyan).

  blender -b --factory-startup --python hero_trees_b4.py

Output: 01_ENVIRONMENT/LANDSCAPE/LIB_Trees_B4.blend
  VEG_Bamboo_Clump_A     arching clump of 26 culms with nodes + narrow leaf sprays        (~11 m)
  VEG_Eucalyptus_A       tall straight pale trunk, high sparse drooping crown           (~19 m)
  VEG_Babool_A           crooked trunk, flat umbrella canopy of fine leaflets + yellow puffs (~6 m)
  VEG_Gulmohar_A         wide umbrella crown smothered in scarlet-orange blossom         (~9 m)
  VEG_Ashoka_A           tall narrow columnar drooping tree                            (~11 m)
  VEG_Ber_Shrub_A        thorny shrub-tree, dense small leaves                         (~3 m)
  AST_Sugarcane_Patch_A  8 x 8 m patch: rows of 2.5-3.2 m canes with long blades
  AST_Hedge_Row_A        4 m clipped karonda hedge, 1.2 m tall
Origin: ground at the trunk / patch centre.  Leaves are GN-instanced cards (the master bakes them).
"""
import datetime
import math
import os
import random
import shutil
import sys

import bpy
from mathutils import Matrix

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import char_lib as CL  # noqa: E402
import hero_animal_bullock_001 as BU  # noqa: E402
import hero_banyan_chowk as HBY  # noqa: E402
import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Trees_B4.blend")
LIB = SRC = None


def asset(name):
    c = bpy.data.collections.new(name)
    LIB.children.link(c)
    BU.COLL = c
    return c


def card(name, mat, L, W, curve=0.08, prof=0.65):
    hb = HB()
    st = 6
    V, F = [], []
    for i in range(st + 1):
        tt = i / st
        w = W * math.sin(math.pi * tt) ** prof
        for sx in (-1, 0, 1):
            V.append((sx * w, tt * L, -curve * L * tt * tt + (0.15 * w if sx else 0.0)))
    for i in range(st):
        for j in range(2):
            a = i * 3 + j
            F.append((a, a + 1, a + 4, a + 3))
    hb.add(V, F, mat)
    o = bpy.data.objects.new("SRC_" + name, hb.to_mesh("ME_SRC_" + name, recalc=False))
    SRC.objects.link(o)
    return o


def leaves_on(coll, name, src, clumps, n_per, rng, size=(0.85, 1.25), shell=None):
    P, R, S = [], [], []
    for c, rad in clumps:
        p, r, s = HBY._shell(rng, n_per, np.asarray(c, float), rad)
        P += p
        R += r
        S += [x * rng.uniform(*size) for x in s]
    H.points_object("FOL_" + name, P, R, S, coll, H.instancer("GN_" + name, src))
    return len(P)


def bamboo(M, S):
    c = asset("VEG_Bamboo_Clump_A")
    rng = random.Random(1)
    culm = H.mat_simple("MAT_Bamboo_Culm_Green", "#6E8A3A", 0.45, noise=0.25)
    node = H.mat_simple("MAT_Bamboo_Node", "#4E5E2A", 0.5)
    tips = []
    hb = HB()
    for k in range(26):
        a = rng.uniform(0, 2 * math.pi)
        r0 = rng.uniform(0.05, 0.6)
        base = np.array([r0 * math.cos(a), r0 * math.sin(a), 0.0])
        lean = rng.uniform(0.15, 0.45) * (0.5 + r0)
        Ht = rng.uniform(8.0, 12.0)
        d = np.array([math.cos(a), math.sin(a), 0.0])
        pts = [base + d * lean * Ht * (t ** 2) + np.array([0, 0, Ht * t - 0.9 * lean * Ht * t ** 3]) for t in np.linspace(0, 1, 9)]
        r = rng.uniform(0.035, 0.06)
        for i in range(len(pts) - 1):
            hb.rod(culm, pts[i], pts[i + 1], r * (1 - 0.6 * i / 8), 7)
            hb.frustum(pts[i + 1][0], pts[i + 1][1], pts[i + 1][2] - 0.02, pts[i + 1][2] + 0.02, r * 1.15, r * 1.15, 7, node)
        tips.append(pts)
    CL.mesh_obj("GEO_Bamboo_Culms", np.zeros((0, 3)), [], culm, c) if False else None
    me = hb.to_mesh("ME_Bamboo_Culms", recalc=False)
    c.objects.link(bpy.data.objects.new("GEO_Bamboo_Culms", me))
    clumps = []
    for pts in tips:
        for i in range(4, 9):
            clumps.append((pts[i], (0.6, 0.6, 0.45)))
    leaves_on(c, "Bamboo_Leaves", S["bamboo"], clumps, 34, rng)


def eucalyptus(M, S):
    c = asset("VEG_Eucalyptus_A")
    rng = random.Random(2)
    bark = H.mat_simple("MAT_Bark_Eucalyptus_Pale", "#C9C2B2", 0.55, noise=0.35)
    pts = [(0, 0, -0.2), (0.15, 0.05, 6.0), (0.05, 0.25, 12.0), (0.3, 0.2, 17.0)]
    BU.tube("GEO_Eucalyptus_Trunk", pts, [0.32, 0.24, 0.16, 0.06], bark, 12, 6)
    clumps = []
    for k in range(9):
        a = rng.uniform(0, 2 * math.pi)
        z = rng.uniform(11.0, 18.5)
        r = rng.uniform(0.8, 2.2) * (1.2 - (z - 11) / 12)
        p0 = np.array([0.2, 0.2, z - 1.5])
        tip = np.array([r * math.cos(a), r * math.sin(a), z])
        BU.tube("GEO_Eucalyptus_Branch_%d" % k, [tuple(p0), tuple((p0 + tip) / 2 + np.array([0, 0, 0.3])), tuple(tip)], [0.07, 0.04, 0.015], bark, 6, 4)
        clumps.append((tip + np.array([0, 0, -0.2]), (1.1, 1.1, 0.9)))
    leaves_on(c, "Eucalyptus_Leaves", S["euc"], clumps, 160, rng)


def babool(M, S):
    c = asset("VEG_Babool_A")
    rng = random.Random(3)
    bark = H.mat_wood("MAT_Bark_Babool_Dark", "#2E2620", "#4A3E33", 0.9)
    BU.tube("GEO_Babool_Trunk", [(0, 0, -0.2), (0.3, 0.1, 1.5), (0.1, 0.3, 2.8)], [0.22, 0.17, 0.13], bark, 10, 6)
    clumps = []
    for k in range(7):
        a = 2 * math.pi * k / 7 + rng.uniform(-0.3, 0.3)
        tip = np.array([3.0 * math.cos(a), 3.0 * math.sin(a), rng.uniform(4.6, 5.6)])
        mid = np.array([1.2 * math.cos(a), 1.2 * math.sin(a), 3.8])
        BU.tube("GEO_Babool_Limb_%d" % k, [(0.1, 0.3, 2.8), tuple(mid), tuple(tip)], [0.12, 0.07, 0.03], bark, 7, 5)
        clumps.append((tip, (1.6, 1.6, 0.45)))
    clumps.append(((0, 0, 5.3), (2.0, 2.0, 0.5)))
    leaves_on(c, "Babool_Leaves", S["babool"], clumps, 420, rng, (0.7, 1.1))
    fl = []
    for k in range(60):
        cc = clumps[k % len(clumps)][0]
        fl.append((np.array(cc) + np.array([rng.uniform(-1.4, 1.4), rng.uniform(-1.4, 1.4), rng.uniform(0.2, 0.45)]), (0.05, 0.05, 0.05)))
    hb = HB()
    yel = H.mat_simple("MAT_Flower_Babool_Yellow", "#E8C52A", 0.6)
    for p, r in fl:
        hb.ellipsoid(p[0], p[1], p[2], 0.045, 0.045, 0.045, yel, 8, 5)
    c.objects.link(bpy.data.objects.new("GEO_Babool_Puffs", hb.to_mesh("ME_Babool_Puffs", recalc=False)))


def gulmohar(M, S):
    c = asset("VEG_Gulmohar_A")
    rng = random.Random(4)
    bark = H.mat_wood("MAT_Bark_Gulmohar", "#6A5E52", "#8C8070", 0.8)
    BU.tube("GEO_Gulmohar_Trunk", [(0, 0, -0.2), (0.2, 0.0, 2.2), (0.0, 0.2, 3.4)], [0.35, 0.28, 0.22], bark, 12, 6)
    clumps = []
    for k in range(6):
        a = 2 * math.pi * k / 6 + rng.uniform(-0.3, 0.3)
        tip = np.array([4.6 * math.cos(a), 4.6 * math.sin(a), rng.uniform(6.8, 7.8)])
        mid = np.array([2.0 * math.cos(a), 2.0 * math.sin(a), 5.6])
        BU.tube("GEO_Gulmohar_Limb_%d" % k, [(0.0, 0.2, 3.4), tuple(mid), tuple(tip)], [0.2, 0.12, 0.05], bark, 8, 5)
        clumps.append((mid + np.array([0, 0, 1.3]), (1.9, 1.9, 1.0)))
        clumps.append((tip, (2.0, 2.0, 0.9)))
    clumps.append(((0, 0, 8.2), (2.6, 2.6, 1.0)))
    leaves_on(c, "Gulmohar_Leaves", S["gul_leaf"], clumps, 230, rng, (0.8, 1.2))
    P, R, Sc = [], [], []
    for cc, rad in clumps:
        p, r, s = HBY._shell(rng, 150, np.asarray(cc) + np.array([0, 0, 0.12]), tuple(x * 1.05 for x in rad))
        P += p
        R += r
        Sc += s
    H.points_object("FLW_Gulmohar_Blossom", P, R, Sc, c, H.instancer("GN_Gulmohar_Blossom", S["gul_flower"]))


def ashoka(M, S):
    c = asset("VEG_Ashoka_A")
    rng = random.Random(5)
    bark = H.mat_wood("MAT_Bark_Ashoka", "#4A3A2E", "#625040", 0.85)
    BU.tube("GEO_Ashoka_Trunk", [(0, 0, -0.2), (0, 0, 5.0), (0, 0, 10.8)], [0.18, 0.12, 0.04], bark, 10, 6)
    clumps = []
    for k in range(14):
        z = 1.6 + k * 0.68
        r = 1.15 * (1 - (z - 1.6) / 11.0) ** 0.7 + 0.15
        clumps.append(((0, 0, z), (r, r, 0.55)))
    leaves_on(c, "Ashoka_Leaves", S["ashoka"], clumps, 200, rng)


def ber(M, S):
    c = asset("VEG_Ber_Shrub_A")
    rng = random.Random(6)
    bark = H.mat_wood("MAT_Bark_Ber", "#4E3E30", "#6E5A46", 0.9)
    clumps = []
    for k in range(6):
        a = rng.uniform(0, 6.28)
        tip = np.array([1.1 * math.cos(a), 1.1 * math.sin(a), rng.uniform(1.8, 2.8)])
        BU.tube("GEO_Ber_Stem_%d" % k, [(0, 0, -0.1), tuple(tip * 0.5), tuple(tip)], [0.07, 0.045, 0.02], bark, 6, 4)
        clumps.append((tip, (0.8, 0.8, 0.6)))
    clumps.append(((0, 0, 2.2), (1.2, 1.2, 0.9)))
    leaves_on(c, "Ber_Leaves", S["ber"], clumps, 330, rng, (0.7, 1.0))


def sugarcane(M, S):
    c = asset("AST_Sugarcane_Patch_A")
    rng = random.Random(7)
    cane = H.mat_simple("MAT_Sugarcane_Cane", "#8A8A3A", 0.5, noise=0.3)
    hb = HB()
    P, R, Sc = [], [], []
    for row in np.arange(-3.8, 3.81, 0.95):
        for y in np.arange(-3.9, 3.91, 0.42):
            if rng.random() < 0.08:
                continue
            x = row + rng.uniform(-0.12, 0.12)
            Ht = rng.uniform(2.4, 3.2)
            lean = np.array([rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), 0])
            top = np.array([x, y, Ht]) + lean
            hb.rod(cane, (x, y, -0.05), top, 0.022, 5)
            for k in range(7):                                                    # long arching blades from the upper half
                z = Ht * (0.45 + 0.08 * k)
                a = rng.uniform(0, 2 * math.pi)
                el = rng.uniform(0.2, 0.9)
                e = (Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(-el, 3, "X")).to_euler()
                P.append(np.array([x, y, z]) + lean * (z / Ht))
                R.append((e.x, e.y, e.z))
                Sc.append(rng.uniform(0.8, 1.2))
    c.objects.link(bpy.data.objects.new("GEO_Sugarcane_Canes", hb.to_mesh("ME_Sugarcane_Canes", recalc=False)))
    H.points_object("FOL_Sugarcane_Blades", P, R, Sc, c, H.instancer("GN_Sugarcane_Blades", S["cane"]))


def hedge(M, S):
    c = asset("AST_Hedge_Row_A")
    rng = random.Random(8)
    core = H.mat_simple("MAT_Hedge_Core", "#1F3A18", 0.85)
    hb = HB()
    hb.box(-2.0, 2.0, -0.35, 0.35, 0.0, 1.05, core)
    c.objects.link(bpy.data.objects.new("GEO_Hedge_Core", hb.to_mesh("ME_Hedge_Core")))
    clumps = [((x, 0.0, 0.62), (0.5, 0.45, 0.6)) for x in np.arange(-1.75, 1.76, 0.5)]
    leaves_on(c, "Hedge_Leaves", S["hedge"], clumps, 260, rng, (0.7, 1.0))


def main():
    global LIB, SRC
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    LIB = bpy.data.collections.new("LIB_TREES_B4")
    sc.collection.children.link(LIB)
    SRC = bpy.data.collections.new("SRC_TREES_B4")
    sc.collection.children.link(SRC)
    bpy.context.view_layer.layer_collection.children["SRC_TREES_B4"].exclude = True
    S = {
        "bamboo": card("Leaf_Bamboo", H.mat_leaf("MAT_Leaf_Bamboo", ("#5E8A34", "#76A03E", "#8EB24C")), 0.28, 0.035, 0.25),
        "euc": card("Leaf_Eucalyptus", H.mat_leaf("MAT_Leaf_Eucalyptus", ("#5E7A5A", "#78927A", "#8FA58A")), 0.22, 0.03, 0.4),
        "babool": card("Leaf_Babool", H.mat_leaf("MAT_Leaf_Babool", ("#3E5E2A", "#50733A", "#6A8446")), 0.12, 0.05, 0.05),
        "gul_leaf": card("Leaf_Gulmohar", H.mat_leaf("MAT_Leaf_Gulmohar", ("#3E6E2A", "#56873A", "#6E9A44")), 0.2, 0.07, 0.05),
        "gul_flower": card("Flower_Gulmohar", H.mat_leaf("MAT_Flower_Gulmohar", ("#C8231A", "#E2401E", "#F0702A"), transl=0.35), 0.14, 0.09, -0.1, 0.5),
        "ashoka": card("Leaf_Ashoka", H.mat_leaf("MAT_Leaf_Ashoka", ("#1E4A1C", "#2E5E24", "#3E7030")), 0.3, 0.045, 0.5),
        "ber": card("Leaf_Ber", H.mat_leaf("MAT_Leaf_Ber", ("#4A6E2E", "#5E843A", "#7A9A48")), 0.07, 0.04, 0.05),
        "cane": card("Leaf_Sugarcane", H.mat_leaf("MAT_Leaf_Sugarcane", ("#6E9A3A", "#86AE4A", "#A8BE5E")), 1.2, 0.04, 0.35, 0.4),
        "hedge": card("Leaf_Hedge", H.mat_leaf("MAT_Leaf_Karonda", ("#23461C", "#2F5824", "#3E6A2C"), rough=0.4), 0.07, 0.03),
    }
    for fn in (bamboo, eucalyptus, babool, gulmohar, ashoka, ber, sugarcane, hedge):
        fn(None, S)
        print("[b4] built", fn.__name__)
    for ch in LIB.children:
        bpy.context.view_layer.layer_collection.children["LIB_TREES_B4"].children[ch.name].exclude = True
    if os.path.exists(OUT_BLEND):
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_Trees_B4_%s.blend" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[b4] saved", OUT_BLEND, [c.name for c in LIB.children])


if __name__ == "__main__":
    main()
