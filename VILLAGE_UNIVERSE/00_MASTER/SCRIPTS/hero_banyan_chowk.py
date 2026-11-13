"""
HERO BANYAN for the village chowk (the village's signature tree).

  blender -b --factory-startup --python hero_banyan_chowk.py -- [--render] [--quick]

Output: 01_ENVIRONMENT/LANDSCAPE/LIB_Hero_Banyan.blend, collection VEG_Tree_Banyan_Chowk_Hero
        + LIB_Hero_Banyan_lanterns.json (lantern / diya positions, local space -> night lights in the master)
Origin = top of the chabutra at the trunk centre.  ~30 m canopy, ~17 m tall.
  trunk     fused multi-stem trunk (clay) with flaring buttress roots
  limbs     6 sweeping primary limbs + secondary branches (tubes)
  roots     ~60 hanging aerial roots + 7 pillar roots that reached the ground
  canopy    ~130 foliage clumps forming a broad dome: dark core + instanced leaf cards
  shrine    kalava threads round the trunk, a small saffron stone shrine with diyas, hanging lanterns
"""
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

import char_lib as CL  # noqa: E402
import hero_animal_bullock_001 as BU  # noqa: E402  (tube helper)
import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Hero_Banyan.blend")
OUT_JSON = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Hero_Banyan_lanterns.json")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "B2_HERO_BANYAN_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def mat_bark(name):
    m, t = H._mat(name, "#5B4A3B")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    mp = t.n("ShaderNodeMapping", Vector=obj, Scale=(9.0, 9.0, 1.4))
    fib = t.noise(mp.outputs[0], 1.0, 8.0, 0.65)
    big = t.noise(obj, 0.6, 3.0, 0.5)
    col = t.ramp(fib.outputs["Fac"], [(0.3, H.hex_lin("#3E3128")), (0.55, H.hex_lin("#5E4C3D")), (0.8, H.hex_lin("#86735E"))])
    z = t.n("ShaderNodeSeparateXYZ", Vector=obj).outputs["Z"]
    moss = t.n("ShaderNodeMapRange", Value=z, **{"From Min": 1.2, "From Max": 0.0, "To Min": 0.0, "To Max": 0.55}).outputs["Result"]
    col = t.mix(t.math("MULTIPLY", moss, big.outputs["Fac"]), col, H.hex_lin("#4E5A2E"))
    t.finish(col, 0.88, t.bump(fib.outputs["Fac"], 0.8, 0.03))
    return m


def leaf_source(src_coll, mat):
    hb = HB()
    st = 6
    V, F = [], []
    L, W = 0.34, 0.2
    for i in range(st + 1):
        tt = i / st
        w = W * math.sin(math.pi * tt) ** 0.65
        for sx in (-1, 0, 1):
            V.append((sx * w, tt * L, -0.06 * L * tt * tt + (0.03 * w if sx else 0.0)))
    for i in range(st):
        for j in range(2):
            a = i * 3 + j
            F.append((a, a + 1, a + 4, a + 3))
    hb.add(V, F, mat)
    o = bpy.data.objects.new("SRC_Leaf_Banyan_Hero", hb.to_mesh("ME_SRC_Leaf_Banyan_Hero", recalc=False))
    src_coll.objects.link(o)
    return o


def build(coll, src):
    rng = random.Random(19)
    nrng = np.random.default_rng(19)
    BU.COLL = coll
    bark = mat_bark("MAT_Bark_Banyan_Hero")
    leaf = H.mat_leaf("MAT_Leaf_Banyan_Hero", ("#2B5422", "#3C722B", "#5C8C36"), transl=0.3)
    core = CL.mat_principled("MAT_Foliage_Banyan_Core", "#1E3A18", 0.8)
    # ---- trunk (clay): fused stems + buttress roots
    c = CL.Clay("BanyanHero_Trunk", 0.07)
    for k in range(7):
        a = 2 * math.pi * k / 7 + 0.3
        r0 = 0.62 + 0.12 * math.sin(k * 2.3)
        p0 = np.array([r0 * math.cos(a), r0 * math.sin(a), -0.3])
        tw = a + 0.5
        p1 = np.array([0.42 * math.cos(tw), 0.42 * math.sin(tw), 2.6])
        p2 = np.array([0.3 * math.cos(tw + 0.4), 0.3 * math.sin(tw + 0.4), 4.6])
        c.chain([p0, p1, p2], [0.62, 0.55, 0.5])
    for k in range(9):
        a = 2 * math.pi * k / 9 + rng.uniform(-0.15, 0.15)
        d = np.array([math.cos(a), math.sin(a), 0.0])
        c.chain([d * 0.9 + np.array([0, 0, 1.5]), d * 2.2 + np.array([0, 0, 0.45]), d * (3.1 + rng.uniform(-0.3, 0.5)) + np.array([0, 0, -0.15])],
                [0.5, 0.33, 0.16])
    # primary limbs (clay where they leave the trunk, tubes further out)
    limbs = []
    for k in range(6):
        a = 2 * math.pi * k / 6 + rng.uniform(-0.25, 0.25)
        d = np.array([math.cos(a), math.sin(a), 0.0])
        rise = rng.uniform(-0.6, 0.8)
        pts = [np.array([0, 0, 4.2]) + d * 0.3, d * 3.4 + np.array([0, 0, 7.2 + rise]), d * 7.4 + np.array([0, 0, 9.4 + rise]),
               d * 11.2 + np.array([0, 0, 10.2 + rise * 0.6]), d * 13.6 + np.array([0, 0, 10.0])]
        c.chain(pts[:3], [0.62, 0.45, 0.32])
        limbs.append(pts)
    c.to_mesh(bark, 3, coll)
    for k, pts in enumerate(limbs):
        BU.tube("GEO_BanyanHero_Limb_%d" % k, [tuple(p) for p in pts[2:]], [0.3, 0.2, 0.1], bark, 12, 6)
        for j in range(4):                                         # secondary branches into the canopy
            t0 = pts[2] + (pts[3] - pts[2]) * rng.uniform(0.0, 0.9)
            a = rng.uniform(0, 2 * math.pi)
            tip = t0 + np.array([3.0 * math.cos(a), 3.0 * math.sin(a), rng.uniform(1.0, 3.0)])
            BU.tube("GEO_BanyanHero_Branch_%d_%d" % (k, j), [tuple(t0), tuple((t0 + tip) / 2 + np.array([0, 0, 0.6])), tuple(tip)],
                    [0.14, 0.08, 0.03], bark, 8, 5)
    # ---- roots: hanging aerial roots + pillar roots
    pillars = CL.Clay("BanyanHero_Pillars", 0.05)
    root_tips = []
    for k, pts in enumerate(limbs):
        for j in range(10):
            s = rng.uniform(0.15, 0.95)
            seg = int(s * 3)
            q = pts[seg] + (pts[seg + 1] - pts[seg]) * (s * 3 - seg)
            q = q + np.array([rng.uniform(-0.8, 0.8), rng.uniform(-0.8, 0.8), -0.2])
            if j == 0 and k < 7:                                   # one pillar per limb
                pillars.chain([q, np.array([q[0], q[1], q[2] * 0.5]), np.array([q[0] * 1.02, q[1] * 1.02, -0.2])], [0.2, 0.22, 0.3])
                pillars.ball((q[0] * 1.02, q[1] * 1.02, 0.1), 0.42)
                continue
            L = rng.uniform(0.35, 1.0) * q[2]
            end = q + np.array([rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), -L])
            mid = (q + end) / 2 + np.array([rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), 0])
            BU.tube("GEO_BanyanHero_AerialRoot_%d_%d" % (k, j), [tuple(q), tuple(mid), tuple(end)],
                    [rng.uniform(0.04, 0.07), 0.035, 0.012], bark, 6, 5)
            root_tips.append(end)
    pillars.to_mesh(bark, 2, coll)
    # ---- canopy: broad dome of clumps (dark core + leaf cards)
    centres = []
    tries = 0
    while len(centres) < 135 and tries < 5000:
        tries += 1
        a = rng.uniform(0, 2 * math.pi)
        rr = 15.0 * math.sqrt(rng.uniform(0.0, 1.0))
        z = 10.6 + 5.6 * (1 - (rr / 15.2) ** 2) + rng.uniform(-0.8, 0.8)
        p = np.array([rr * math.cos(a), rr * math.sin(a), z])
        if any(np.linalg.norm(p - q) < 2.2 for q in centres):
            continue
        centres.append(p)
    hb = HB()
    P, R, S = [], [], []
    for p in centres:
        rad = (rng.uniform(2.4, 3.4), rng.uniform(2.4, 3.4), rng.uniform(1.5, 2.1))
        hb.ellipsoid(p[0], p[1], p[2] - 0.15, rad[0] * 0.78, rad[1] * 0.78, rad[2] * 0.72, core, 14, 8)
        pp, rr_, ss = _shell(rng, 420, p, rad)
        P += pp
        R += rr_
        S += ss
    me = hb.to_mesh("ME_BanyanHero_CanopyCore", recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    coll.objects.link(bpy.data.objects.new("GEO_BanyanHero_CanopyCore", me))
    H.points_object("FOL_BanyanHero_Leaves", P, R, S, coll, H.instancer("GN_BanyanHero_Leaves", src))
    print("[banyan] canopy clumps %d, leaves %d, aerial roots %d" % (len(centres), len(P), len(root_tips)))
    return limbs, root_tips


def _shell(rng, n, c, radii):
    from mathutils import Matrix
    P, R, S = [], [], []
    while len(P) < n:
        v = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)])
        L = np.linalg.norm(v)
        if not 0.1 < L <= 1.0:
            continue
        u = v / L
        if u[2] < -0.55:
            continue
        k = 0.82 + 0.2 * rng.random() ** 0.5
        p = c + u * np.array(radii) * k
        z = u + np.array([0, 0, 0.35])
        z /= np.linalg.norm(z)
        tt = np.cross(z, [rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)])
        tt /= np.linalg.norm(tt) + 1e-9
        x = np.cross(tt, z)
        e = Matrix(((x[0], tt[0], z[0]), (x[1], tt[1], z[1]), (x[2], tt[2], z[2]))).to_euler()
        P.append(p)
        R.append((e.x, e.y, e.z))
        S.append(rng.uniform(0.85, 1.3))
    return P, R, S


def shrine_and_lanterns(coll, limbs):
    rng = random.Random(4)
    red = CL.mat_principled("MAT_Thread_Kalava_Red", "#B3201C", 0.7, sheen=0.4)
    yel = CL.mat_principled("MAT_Thread_Kalava_Yellow", "#E0A21E", 0.7, sheen=0.4)
    saff = CL.mat_principled("MAT_Paint_Sindoor_Saffron", "#D9541C", 0.6)
    stone = H.mat_stone_blocks()
    clay = CL.mat_principled("MAT_Clay_Diya", "#9C5232", 0.7)
    brass = CL.mat_principled("MAT_Metal_Brass_Lantern", "#B8903A", 0.3, 1.0)
    glass = CL.mat_principled("MAT_Glass_Lantern_Amber", "#F2B060", 0.15)
    rope = H.mat_rope()
    hb = HB()
    for k in range(9):                                             # kalava wound round the trunk
        z = 1.05 + k * 0.045 + rng.uniform(-0.01, 0.01)
        n = 64
        for i in range(n):
            a0, a1 = 2 * math.pi * i / n, 2 * math.pi * (i + 1) / n
            r0 = 1.18 + 0.06 * math.sin(a0 * 7)
            r1 = 1.18 + 0.06 * math.sin(a1 * 7)
            hb.rod(red if k % 3 else yel, (r0 * math.cos(a0), r0 * math.sin(a0), z), (r1 * math.cos(a1), r1 * math.sin(a1), z), 0.012, 4)
    me = hb.to_mesh("ME_BanyanHero_Kalava", recalc=False)
    coll.objects.link(bpy.data.objects.new("GEO_BanyanHero_Kalava", me))
    # small shrine on the -Y side of the trunk
    hb = HB()
    sx, sy = 0.0, -2.0
    hb.box(sx - 0.55, sx + 0.55, sy - 0.45, sy + 0.45, 0.0, 0.35, stone)
    hb.ellipsoid(sx, sy, 0.62, 0.2, 0.16, 0.3, saff, 14, 8)
    diyas = []
    for k in range(5):
        x = sx - 0.4 + k * 0.2
        y = sy - 0.33
        hb.lathe(clay, [(0.0, 0.0), (0.045, 0.0), (0.06, 0.02), (0.055, 0.03), (0.0, 0.025)], 12, x, y, 0.35)
        diyas.append((x, y, 0.42))
    me = hb.to_mesh("ME_BanyanHero_Shrine")
    coll.objects.link(bpy.data.objects.new("GEO_BanyanHero_Shrine", me))
    # hanging lanterns from the limbs
    lanterns = []
    hb = HB()
    for k, pts in enumerate(limbs):
        for s in (0.45, 0.8):
            q = pts[1] + (pts[2] - pts[1]) * s
            hang = q - np.array([0, 0, 0.35])
            L = rng.uniform(1.0, 2.0)
            top = hang - np.array([0, 0, L])
            hb.rod(rope, hang, top + np.array([0, 0, 0.18]), 0.008, 4)
            for dx in (-0.08, 0.08):
                for dy in (-0.08, 0.08):
                    hb.rod(brass, top + np.array([dx, dy, 0.12]), top + np.array([dx, dy, -0.12]), 0.008, 4)
            hb.frustum(top[0], top[1], top[2] + 0.12, top[2] + 0.2, 0.11, 0.03, 8, brass)
            hb.frustum(top[0], top[1], top[2] - 0.14, top[2] - 0.12, 0.11, 0.11, 8, brass)
            hb.box(top[0] - 0.075, top[0] + 0.075, top[1] - 0.075, top[1] + 0.075, top[2] - 0.11, top[2] + 0.11, glass)
            lanterns.append(tuple(float(v) for v in top))
    me = hb.to_mesh("ME_BanyanHero_Lanterns")
    coll.objects.link(bpy.data.objects.new("GEO_BanyanHero_Lanterns", me))
    return lanterns, diyas


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    lib = bpy.data.collections.new("LIB_HERO_BANYAN")
    sc.collection.children.link(lib)
    src = bpy.data.collections.new("SRC_BANYAN")
    sc.collection.children.link(src)
    bpy.context.view_layer.layer_collection.children["SRC_BANYAN"].exclude = True
    coll = bpy.data.collections.new("VEG_Tree_Banyan_Chowk_Hero")
    lib.children.link(coll)
    leaf = H.mat_leaf("MAT_Leaf_Banyan_Hero", ("#2B5422", "#3C722B", "#5C8C36"), transl=0.3)
    s = leaf_source(src, leaf)
    limbs, roots = build(coll, s)
    lanterns, diyas = shrine_and_lanterns(coll, limbs)
    for o in list(sc.collection.objects):
        if o.type == "META":
            bpy.data.objects.remove(o, do_unlink=True)
    with open(OUT_JSON, "w") as f:
        json.dump({"lanterns": lanterns, "diyas": diyas}, f, indent=1)
    # review stage (day): ground disc + the tree, camera from the chowk edge
    cams = {"CAM_Banyan_Front": ((0.0, -34.0, 3.0), (0.0, 0.0, 8.0), 24, 1600, 1000),
            "CAM_Banyan_Trunk": ((-6.0, -11.0, 1.7), (0.0, 0.0, 3.5), 24, 1600, 1000)}
    objs = CL.review_stage(cams, OUT_REVIEW, "Banyan", samples=48)
    hb = HB()
    hb.frustum(0, 0, -0.75, 0.0, 7.5, 7.5, 48, H.mat_stone_blocks())
    bpy.data.objects["STG_Cyclorama"].scale = (8, 8, 8)
    sc.collection.objects.link(bpy.data.objects.new("STG_Chabutra", hb.to_mesh("ME_STG_Chabutra")))
    st = bpy.data.collections["REVIEW_STAGE"]
    e = bpy.data.objects.new("STG_Banyan", None)
    e.instance_type = "COLLECTION"
    e.instance_collection = coll
    st.objects.link(e)
    bpy.context.view_layer.layer_collection.children["LIB_HERO_BANYAN"].exclude = True
    for o in st.objects:
        if o.type == "LIGHT":
            o.data.energy *= 40
            o.location = o.location * 10
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_Hero_Banyan_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[banyan] saved", OUT_BLEND, "lanterns", len(lanterns))
    if "--render" in ARGS:
        CL.render_cams(objs, OUT_REVIEW)


if __name__ == "__main__":
    main()
