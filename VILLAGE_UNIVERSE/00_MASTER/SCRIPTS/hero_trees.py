"""
HERO VEGETATION LIBRARY: procedural stylised trees for Amaltaspur.

  blender -b --factory-startup --python hero_trees.py -- [--render] [--quick] [--only CAM]

Output: 01_ENVIRONMENT/LANDSCAPE/LIB_Trees.blend
  Collections VEG_Tree_<Species>_A (hero, close-up ready) and VEG_Tree_<Species>_A_LOD1 (village scatter).
Look: feature-animation stylisation = readable foliage clumps (dense core + real leaf instances on the
surface) on a believable branch skeleton.  Leaves are Geometry-Nodes instances (cheap in memory).
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
OUT_BLEND = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Trees.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "PH1B_TREES_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
UP = np.array([0.0, 0.0, 1.0])


def nrm(v):
    return v / (np.linalg.norm(v) + 1e-9)


# ============================================================================
# Species definitions
# ============================================================================
SPECIES = {
    "Mango": dict(trunk_len=2.4, trunk_r=0.36, depth=3, children=[4, 3, 2], angle=[42, 34, 30],
                  len_ratio=[1.5, 0.62, 0.6], rad_ratio=0.62, child_start=[0.88, 0.45, 0.45],
                  tropism=[0.06, 0.05, 0.04], gnarl=0.17, seg_len=0.45, clump_r=1.35, density=80,
                  leaf="lance", leaf_size=0.32, leaf_cols=("#2E5524", "#4A7A31", "#5E8C3A"), core="#2B4A22",
                  bark=("#3F342B", "#5A4C40"), seed=11),
    "Neem": dict(trunk_len=3.6, trunk_r=0.27, depth=3, children=[5, 3, 2], angle=[36, 32, 30],
                 len_ratio=[0.95, 0.62, 0.6], rad_ratio=0.5, child_start=[0.45, 0.4, 0.4],
                 tropism=[0.12, 0.08, 0.05], gnarl=0.22, seg_len=0.45, clump_r=0.95, density=44, core_scale=0.5,
                 leaf="sprig", leaf_size=1.0, leaf_cols=("#4D7A2E", "#6A9638", "#80A845"), core="#3E6427",
                 bark=("#3A2E25", "#55473A"), seed=23),
    "Peepal": dict(trunk_len=2.6, trunk_r=0.42, depth=3, children=[5, 3, 2], angle=[50, 38, 32],
                   len_ratio=[1.45, 0.62, 0.6], rad_ratio=0.52, child_start=[0.75, 0.45, 0.45],
                   tropism=[0.08, 0.06, 0.04], gnarl=0.2, seg_len=0.45, clump_r=1.2, density=80,
                   leaf="heart", leaf_size=0.2, leaf_cols=("#3F6E2A", "#5C8E35", "#7AA545"), core="#335A24",
                   bark=("#6C665C", "#8A8478"), seed=37),
    "Banyan": dict(trunk_len=4.6, trunk_r=1.2, depth=3, children=[7, 3, 2], angle=[80, 36, 28],
                   len_ratio=[2.6, 0.55, 0.55], rad_ratio=0.5, child_start=[0.7, 0.35, 0.4],
                   tropism=[-0.012, 0.025, 0.02], gnarl=0.1, seg_len=0.6, clump_r=1.9, density=60,
                   leaf="oval", leaf_size=0.22, leaf_cols=("#2F5A26", "#47753A", "#5E8740"), core="#294A21",
                   bark=("#5E584E", "#7A7266"), seed=5, aerial_roots=28),
    "Amaltas": dict(trunk_len=2.6, trunk_r=0.2, depth=3, children=[4, 3, 2], angle=[38, 34, 30],
                    len_ratio=[1.3, 0.6, 0.55], rad_ratio=0.55, child_start=[0.7, 0.5, 0.45],
                    tropism=[0.1, 0.08, 0.05], gnarl=0.25, seg_len=0.4, clump_r=0.9, density=40, core_scale=0.42,
                    leaf="compound", leaf_size=1.0, leaf_cols=("#557F2F", "#6E963A", "#86A84A"), core="#4A6E2A",
                    bark=("#5B5047", "#776A5E"), seed=47, flowers=True),
}


# ============================================================================
# Skeleton
# ============================================================================
def rand_unit(rng):
    while True:
        v = np.array([rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1)])
        n = np.linalg.norm(v)
        if 0.1 < n <= 1.0:
            return v / n


def rotate(v, axis, ang):
    return np.array(Matrix.Rotation(ang, 3, Vector(axis)) @ Vector(v))


def grow(rng, sp, pos, d, length, radius, depth, branches, clumps, phase):
    nseg = max(3, int(length / sp["seg_len"]))
    pts, rads = [np.array(pos, float)], [radius]
    for i in range(nseg):
        trop = sp["tropism"][min(depth, len(sp["tropism"]) - 1)]
        d = nrm(d + rand_unit(rng) * sp["gnarl"] + UP * trop)
        pts.append(pts[-1] + d * (length / nseg))
        rads.append(radius * (1.0 - (i + 1) / nseg * 0.55))
    branches.append((pts, rads, depth))
    if depth >= sp["depth"]:
        R = sp["clump_r"]
        clumps.append((pts[-1] + rand_unit(rng) * 0.2 * R, R * rng.uniform(0.85, 1.15)))
        for frac, scale in ((0.62, 0.8), (0.32, 0.62)):
            if rng.random() < 0.8:
                i = max(1, int(nseg * frac))
                clumps.append((pts[i] + rand_unit(rng) * 0.35 * R, R * scale * rng.uniform(0.85, 1.1)))
        return
    nc = sp["children"][depth]
    golden = math.radians(137.5)
    for c in range(nc):
        t = rng.uniform(sp["child_start"][depth], 1.0) if c < nc - 1 else rng.uniform(0.92, 1.0)
        idx = min(nseg, max(1, int(round(t * nseg))))
        base = pts[idx]
        pd = nrm(pts[idx] - pts[idx - 1])
        perp = nrm(np.cross(pd, UP if abs(pd[2]) < 0.95 else np.array([1.0, 0, 0])))
        perp = rotate(perp, pd, phase + c * golden + rng.uniform(-0.3, 0.3))
        ang = math.radians(sp["angle"][depth] + rng.uniform(-8, 8))
        cd = rotate(pd, perp, ang)
        ln = length * sp["len_ratio"][depth] * rng.uniform(0.8, 1.1)
        if depth == 0:
            ln = sp["trunk_len"] * sp["len_ratio"][0] * rng.uniform(0.85, 1.1)
        grow(rng, sp, base, cd, ln, rads[idx] * sp["rad_ratio"] * rng.uniform(0.9, 1.1), depth + 1,
             branches, clumps, phase + c)


def tube(hb, mat, pts, rads, sides):
    """Tapered tube along a polyline using parallel-transport frames."""
    pts = [np.asarray(p, float) for p in pts]
    tangents = []
    for i in range(len(pts)):
        a = pts[max(0, i - 1)]
        b = pts[min(len(pts) - 1, i + 1)]
        tangents.append(nrm(b - a))
    ref = np.array([1.0, 0, 0]) if abs(tangents[0][0]) < 0.9 else np.array([0, 1.0, 0])
    n = nrm(np.cross(tangents[0], ref))
    v, f = [], []
    for i, (p, r) in enumerate(zip(pts, rads)):
        if i > 0:
            axis = np.cross(tangents[i - 1], tangents[i])
            s = np.linalg.norm(axis)
            if s > 1e-6:
                ang = math.asin(min(1.0, s))
                n = rotate(n, axis / s, ang)
        b = np.cross(tangents[i], n)
        for k in range(sides):
            a = 2 * math.pi * k / sides
            v.append(tuple(p + r * (math.cos(a) * n + math.sin(a) * b)))
    for i in range(len(pts) - 1):
        for k in range(sides):
            a0 = i * sides + k
            a1 = i * sides + (k + 1) % sides
            f.append((a0, a1, a1 + sides, a0 + sides))
    hb.add(v, f, mat)


# ============================================================================
# Leaves
# ============================================================================
def leaf_blade(hb, mat, L, Wd, prof="lance", y0=0.0, x0=0.0, rotz=0.0, curve=0.25, fold=0.25):
    st = 7
    v, f = [], []
    for i in range(st + 1):
        t = i / st
        if prof == "lance":
            w = Wd * (math.sin(math.pi * t) ** 0.85)
        elif prof == "heart":
            w = Wd * (math.sin(math.pi * min(1.0, t * 1.25)) ** 0.55) if t < 0.8 else Wd * 0.25 * (1 - t) / 0.2
        else:  # oval
            w = Wd * (math.sin(math.pi * t) ** 0.6)
        z = -curve * L * t * t
        for sx in (-1, 0, 1):
            x, y = sx * w, t * L
            zz = z + (fold * w if sx != 0 else 0.0)
            c, s = math.cos(rotz), math.sin(rotz)
            v.append((x0 + x * c - y * s, y0 + x * s + y * c, zz))
    for i in range(st):
        for j in range(2):
            a = i * 3 + j
            f.append((a, a + 1, a + 4, a + 3))
    hb.add(v, f, mat)


def make_leaf_object(kind, size, mat, coll):
    hb = HB()
    if kind == "lance":
        hb.rod(mat, (0, -0.04 * size / 0.28, 0), (0, 0.0, 0), 0.004, 4)
        leaf_blade(hb, mat, size, size * 0.14, "lance")
    elif kind == "heart":
        leaf_blade(hb, mat, size, size * 0.42, "heart", curve=0.15, fold=0.15)
    elif kind == "oval":
        leaf_blade(hb, mat, size, size * 0.3, "oval", curve=0.15, fold=0.2)
    elif kind == "sprig":                          # neem: pinnate sprig
        hb.rod(mat, (0, 0, 0), (0, 0.32, -0.02), 0.003, 4)
        for i in range(7):
            y = 0.04 + i * 0.042
            for sx in (-1, 1):
                leaf_blade(hb, mat, 0.075, 0.012, "lance", y0=y, rotz=sx * math.radians(65), curve=0.3, fold=0.3)
        leaf_blade(hb, mat, 0.08, 0.013, "lance", y0=0.32)
    elif kind == "compound":                       # amaltas: ovate leaflets
        hb.rod(mat, (0, 0, 0), (0, 0.36, -0.02), 0.004, 4)
        for i in range(4):
            y = 0.06 + i * 0.08
            for sx in (-1, 1):
                leaf_blade(hb, mat, 0.11, 0.028, "oval", y0=y, rotz=sx * math.radians(70), curve=0.15, fold=0.15)
    o = bpy.data.objects.new("SRC_Leaf_%s" % kind, hb.to_mesh("ME_Leaf_%s" % kind, recalc=False))
    coll.objects.link(o)
    return o


def leaf_material(name, cols):
    m, t = H._mat(name, cols[1])
    oi = t.n("ShaderNodeObjectInfo")
    col = t.ramp(oi.outputs["Random"], [(0.0, H.hex_lin(cols[0])), (0.5, H.hex_lin(cols[1])), (1.0, H.hex_lin(cols[2]))])
    tc = t.n("ShaderNodeTexCoord")
    n = t.noise(tc.outputs["Generated"], 3.0, 2.0)
    col = t.mix(t.math("MULTIPLY", n.outputs["Fac"], 0.25), col, H.hex_lin(cols[0], 0.6))
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.inp(b, "Roughness").default_value = 0.48
    tr = t.n("ShaderNodeBsdfTranslucent")
    t.link(col, t.inp(tr, "Color"))
    mx = t.n("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.22
    t.link(b.outputs[0], mx.inputs[1])
    t.link(tr.outputs[0], mx.inputs[2])
    o = t.n("ShaderNodeOutputMaterial")
    t.link(mx.outputs[0], o.inputs["Surface"])
    return m


def core_material(name, hexc):
    """Inner foliage mass: dark, broken-up, reads as depth between leaves (never as a smooth ball)."""
    m, t = H._mat(name, hexc)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    vor = t.n("ShaderNodeTexVoronoi", Vector=obj, Scale=7.0)
    n = t.noise(obj, 5.0, 6.0, 0.7)
    f = t.math("ADD", t.math("MULTIPLY", vor.outputs["Distance"], 0.6), t.math("MULTIPLY", n.outputs["Fac"], 0.5))
    col = t.ramp(f, [(0.25, H.hex_lin(hexc, 0.45)), (0.75, H.hex_lin(hexc, 1.05))])
    t.finish(col, 0.9, t.bump(f, 0.9, 0.05))
    return m


def bark_material(name, cols):
    m, t = H._mat(name, cols[1])
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    mp = t.n("ShaderNodeMapping", Vector=obj, Scale=(9.0, 9.0, 1.8))
    fis = t.noise(mp.outputs[0], 2.5, 6.0, 0.7)
    col = t.ramp(fis.outputs["Fac"], [(0.35, H.hex_lin(cols[0], 0.8)), (0.65, H.hex_lin(cols[1]))])
    big = t.noise(obj, 0.8, 2.0)
    col = t.mix(t.math("MULTIPLY", big.outputs["Fac"], 0.35), col, H.hex_lin("#6B6A55"))   # lichen tint
    t.finish(col, 0.88, t.bump(fis.outputs["Fac"], 0.55, 0.03))
    return m


def leaf_instancer(name, leaf_obj):
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N = ng.nodes
    gi = N.new("NodeGroupInput")
    go = N.new("NodeGroupOutput")
    iop = N.new("GeometryNodeInstanceOnPoints")
    oi = N.new("GeometryNodeObjectInfo")
    oi.inputs["Object"].default_value = leaf_obj
    oi.inputs["As Instance"].default_value = True
    na_r = N.new("GeometryNodeInputNamedAttribute")
    na_r.data_type = "FLOAT_VECTOR"
    na_r.inputs["Name"].default_value = "rot"
    na_s = N.new("GeometryNodeInputNamedAttribute")
    na_s.data_type = "FLOAT"
    na_s.inputs["Name"].default_value = "scl"
    L = ng.links
    L.new(gi.outputs[0], iop.inputs["Points"])
    L.new(oi.outputs["Geometry"], iop.inputs["Instance"])
    rot_out = na_r.outputs["Attribute"]
    try:
        e2r = N.new("FunctionNodeEulerToRotation")
        L.new(rot_out, e2r.inputs[0])
        rot_out = e2r.outputs[0]
    except Exception:
        pass
    L.new(rot_out, iop.inputs["Rotation"])
    L.new(na_s.outputs["Attribute"], iop.inputs["Scale"])
    L.new(iop.outputs["Instances"], go.inputs[0])
    return ng


def points_object(name, P, R, S, coll, ng):
    me = bpy.data.meshes.new("ME_" + name)
    me.vertices.add(len(P))
    me.vertices.foreach_set("co", np.asarray(P, np.float32).ravel())
    a = me.attributes.new("rot", "FLOAT_VECTOR", "POINT")
    a.data.foreach_set("vector", np.asarray(R, np.float32).ravel())
    s = me.attributes.new("scl", "FLOAT", "POINT")
    s.data.foreach_set("value", np.asarray(S, np.float32))
    me.update()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    mod = o.modifiers.new("Leaves", "NODES")
    mod.node_group = ng
    return o


def clump_leaf_points(rng, clumps, density, size_scale):
    P, R, S = [], [], []
    for ci, (c, r) in enumerate(clumps):
        n = int(density * 4 * math.pi * r * r * 0.75)
        for _ in range(n):
            u = rand_unit(rng)
            if u[2] < -0.35 and rng.random() < 0.65:
                continue
            p = c + np.array([u[0], u[1], u[2] * 0.8]) * r * (0.62 + 0.46 * rng.random() ** 0.45)
            hidden = False
            for cj, (c2, r2) in enumerate(clumps):
                if cj != ci and np.linalg.norm((p - c2) * np.array([1, 1, 1.25])) < r2 * 0.66:
                    hidden = True
                    break
            if hidden:
                continue
            z = nrm(u + np.array([0, 0, 0.35]))
            t = nrm(np.cross(z, rand_unit(rng)))
            x = np.cross(t, z)
            Mx = Matrix(((x[0], t[0], z[0]), (x[1], t[1], z[1]), (x[2], t[2], z[2])))
            e = Mx.to_euler()
            P.append(p)
            R.append((e.x, e.y, e.z))
            S.append(size_scale * rng.uniform(0.75, 1.2))
    return P, R, S


# ============================================================================
def build_tree(name, sp, M, src_coll):
    rng = random.Random(sp["seed"])
    hero = bpy.data.collections.new("VEG_Tree_%s_A" % name)
    lod = bpy.data.collections.new("VEG_Tree_%s_A_LOD1" % name)
    LIB.children.link(hero)
    LIB.children.link(lod)
    branches, clumps = [], []
    grow(rng, sp, (0, 0, -0.3), np.array([rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 1.0]),
         sp["trunk_len"], sp["trunk_r"], 0, branches, clumps, rng.uniform(0, 6.28))
    bark = bark_material("MAT_Bark_%s" % name, sp["bark"])
    hb = HB()
    for pts, rads, depth in branches:
        sides = 14 if depth == 0 else (9 if depth == 1 else 6)
        if depth == 0:   # root flare
            rads = [r * (1.0 + 0.45 * max(0.0, 1.0 - i / 2.5)) for i, r in enumerate(rads)]
        tube(hb, bark, pts, rads, sides)
    # buttress roots
    for k in range(5 if sp["trunk_r"] > 0.3 else 3):
        a = 2 * math.pi * k / 5 + rng.uniform(-0.3, 0.3)
        d = np.array([math.cos(a), math.sin(a), 0.0])
        r0 = sp["trunk_r"] * 0.45
        tube(hb, bark, [np.array([0, 0, 0.5]), d * sp["trunk_r"] * 1.1 + np.array([0, 0, 0.05]),
                        d * sp["trunk_r"] * 2.0 + np.array([0, 0, -0.15])], [r0, r0 * 0.6, r0 * 0.2], 8)
    if sp.get("aerial_roots"):
        limbs = [b for b in branches if b[2] == 1]
        for k in range(sp["aerial_roots"]):
            pts, rads, _ = limbs[k % len(limbs)]
            i = rng.randint(len(pts) // 4, len(pts) - 2)
            top = pts[i]
            thick = rng.random() < 0.25
            r = rng.uniform(0.12, 0.22) if thick else rng.uniform(0.025, 0.06)
            bottom = top.copy()
            bottom[2] = -0.2 if thick or rng.random() < 0.5 else top[2] * rng.uniform(0.2, 0.6)
            sway = [top + (bottom - top) * s + np.array([rng.uniform(-0.15, 0.15), rng.uniform(-0.15, 0.15), 0]) * (s * (1 - s) * 4)
                    for s in np.linspace(0, 1, 6)]
            tube(hb, bark, sway, [r * (1.0 + 0.3 * s) for s in np.linspace(0, 1, 6)], 8 if thick else 5)
    me_bark = hb.to_mesh("ME_Bark_%s" % name, recalc=False)
    me_bark.polygons.foreach_set("use_smooth", [True] * len(me_bark.polygons))
    for c in (hero, lod):
        c.objects.link(bpy.data.objects.new("TRK_%s%s" % (name, "" if c is hero else "_LOD1"), me_bark))

    # foliage cores
    core_mat = core_material("MAT_FoliageCore_%s" % name, sp["core"])
    cs = sp.get("core_scale", 0.62)
    hb = HB()
    for (c, r) in clumps:
        base = len(hb.v)
        hb.ellipsoid(c[0], c[1], c[2] - 0.05 * r, r * cs, r * cs, r * cs * 0.78, core_mat, 16, 10)
        ph = rng.uniform(0, 6.28)
        for i in range(base, len(hb.v)):          # lumpy silhouette
            p = np.array(hb.v[i])
            k = 1.0 + 0.16 * math.sin(p[0] * 4.1 + p[2] * 3.3 + ph) * math.cos(p[1] * 3.7 - ph)
            hb.v[i] = tuple(c + (p - c) * k)
    me_core = hb.to_mesh("ME_Core_%s" % name)
    me_core.polygons.foreach_set("use_smooth", [True] * len(me_core.polygons))
    for c in (hero, lod):
        c.objects.link(bpy.data.objects.new("FOL_Core_%s%s" % (name, "" if c is hero else "_LOD1"), me_core))

    # leaves
    lmat = leaf_material("MAT_Leaf_%s" % name, sp["leaf_cols"])
    size = sp["leaf_size"] / 0.28 if sp["leaf"] == "lance" else 1.0
    leaf_obj = make_leaf_object(sp["leaf"], sp["leaf_size"] if sp["leaf"] in ("lance", "heart", "oval") else 1.0,
                                lmat, src_coll)
    ng = leaf_instancer("GN_Leaves_%s" % name, leaf_obj)
    P, R, S = clump_leaf_points(random.Random(sp["seed"] + 1), clumps, sp["density"], 1.0)
    points_object("FOL_Leaves_%s" % name, P, R, S, hero, ng)
    keep = [i for i in range(len(P)) if (i * 7919) % 100 < 14]
    points_object("FOL_Leaves_%s_LOD1" % name, [P[i] for i in keep], [R[i] for i in keep],
                  [S[i] * 1.7 for i in keep], lod, ng)

    nfl = 0
    if sp.get("flowers"):
        fmat = H.mat_simple("MAT_Flower_Amaltas", "#F2C12E", 0.45, emission=H.hex_lin("#F2C12E"), estr=0.08)
        hb = HB()
        fr = random.Random(99)
        for (c, r) in clumps:
            for _ in range(fr.randint(10, 18)):
                u = rand_unit(fr)
                u[2] = -abs(u[2]) * 0.6
                top = c + nrm(u) * r * fr.uniform(0.75, 1.0)
                L = fr.uniform(0.3, 0.6)
                sway = np.array([fr.uniform(-0.08, 0.08), fr.uniform(-0.08, 0.08), -L])
                hb.rod(lmat, top, top + sway, 0.004, 4)
                for k in range(int(L / 0.04)):
                    if fr.random() < 0.18:
                        continue
                    s = (k * 0.04 + 0.03) / L
                    p = top + sway * s
                    rr = fr.uniform(0.026, 0.046) * (1.0 - 0.45 * s)
                    hb.ellipsoid(p[0] + fr.uniform(-0.045, 0.045), p[1] + fr.uniform(-0.045, 0.045), p[2],
                                 rr, rr * fr.uniform(0.7, 1.0), rr * 0.75, fmat, 6, 4)
                    nfl += 1
        me_f = hb.to_mesh("ME_Flowers_%s" % name)
        hero.objects.link(bpy.data.objects.new("FLW_%s" % name, me_f))
    height = max(c[2] + r * 0.7 for c, r in clumps)
    width = 2 * max(math.hypot(c[0], c[1]) + r for c, r in clumps)
    hero["height_m"] = round(height, 1)
    hero["crown_width_m"] = round(width, 1)
    print("[trees] %-8s branches=%d clumps=%d leaves=%d (LOD1 %d) flowers=%d  H=%.1fm W=%.1fm"
          % (name, len(branches), len(clumps), len(P), len(keep), nfl, height, width))
    return hero, lod


def build_palm(M, src_coll):
    rng = random.Random(71)
    hero = bpy.data.collections.new("VEG_Tree_Palm_A")
    lod = bpy.data.collections.new("VEG_Tree_Palm_A_LOD1")
    LIB.children.link(hero)
    LIB.children.link(lod)
    bark = bark_material("MAT_Bark_Palm", ("#6A6157", "#8C8274"))
    hb = HB()
    H_ = 10.5
    n = 64
    pts, rads = [], []
    for i in range(n + 1):
        t = i / n
        pts.append(np.array([1.1 * t * t + 0.25 * math.sin(t * 3.0), 0.3 * t * t, -0.2 + H_ * t]))
        ring = 1.0 + 0.07 * max(0.0, math.cos(t * H_ / 0.28 * 2 * math.pi)) ** 4
        rads.append((0.25 - 0.08 * t + 0.12 * max(0.0, 1 - t * 8)) * ring)
    tube(hb, bark, pts, rads, 12)
    top = pts[-1]
    hb.ellipsoid(top[0], top[1], top[2] + 0.05, 0.32, 0.32, 0.35, bark, 10, 6)
    me_tr = hb.to_mesh("ME_Bark_Palm", recalc=False)
    me_tr.polygons.foreach_set("use_smooth", [True] * len(me_tr.polygons))
    green = leaf_material("MAT_Leaf_Palm", ("#4A7330", "#638C3A", "#7C9E45"))
    dry = H.mat_simple("MAT_Leaf_Palm_Dry", "#9C844F", 0.8, noise=0.2)
    nut = H.mat_simple("MAT_Coconut", "#6E7A2E", 0.5, noise=0.15)
    hb = HB()
    nf = 18
    for k in range(nf):
        az = 2 * math.pi * k / nf + rng.uniform(-0.15, 0.15)
        old = k % 6 == 0
        el = math.radians(rng.uniform(-40, -25) if old else rng.uniform(-10, 55))
        L = rng.uniform(4.0, 4.8)
        d0 = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        mat = dry if (old and k % 12 == 0) else green
        spine = [top + d0 * s + np.array([0, 0, -0.09 * s * s]) for s in np.linspace(0, L, 14)]
        tube(hb, mat, spine, list(np.linspace(0.04, 0.008, 14)), 4)
        for j in range(12, 0, -1):
            pass
        side = nrm(np.cross(d0, UP))
        for s in np.arange(0.3 * L, L, 0.075):
            i = s / L * 13
            a = spine[int(i)]
            b = spine[min(13, int(i) + 1)]
            p = a + (b - a) * (i - int(i))
            tng = nrm(b - a)
            sd = nrm(np.cross(tng, UP))
            ll = 0.25 + 0.8 * math.sin(math.pi * (s - 0.35 * L) / (0.65 * L))
            for sx in (-1, 1):
                dirl = nrm(sd * sx + tng * 0.45 + np.array([0, 0, -0.55]))
                wv = nrm(np.cross(dirl, UP)) * 0.04
                q1 = p + dirl * ll * 0.5 + np.array([0, 0, -0.05])
                q2 = p + dirl * ll + np.array([0, 0, -0.18])
                v = [p - wv * 0.5, p + wv * 0.5, q1 + wv, q1 - wv, q2]
                hb.add(v, [(0, 1, 2, 3), (3, 2, 4)], mat)
    for k in range(9):
        a = 2 * math.pi * k / 9
        hb.ellipsoid(top[0] + 0.35 * math.cos(a), top[1] + 0.35 * math.sin(a), top[2] - 0.45 - 0.1 * (k % 2),
                     0.13, 0.13, 0.15, nut, 10, 6)
    me_fr = hb.to_mesh("ME_Fronds_Palm", recalc=False)
    for c, suf in ((hero, ""), (lod, "_LOD1")):
        c.objects.link(bpy.data.objects.new("TRK_Palm" + suf, me_tr))
        c.objects.link(bpy.data.objects.new("FOL_Fronds_Palm" + suf, me_fr))
    hero["height_m"] = round(float(top[2]) + 1.5, 1)
    print("[trees] Palm     fronds=%d  H=%.1fm" % (nf, top[2] + 1.5))
    return hero, lod


# ============================================================================
LIB = None


def main():
    global LIB
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "LIB_Trees"
    sc.unit_settings.system = "METRIC"
    LIB = bpy.data.collections.new("LIB_VEGETATION")
    sc.collection.children.link(LIB)
    src = bpy.data.collections.new("SRC_LEAVES")
    sc.collection.children.link(src)
    bpy.context.view_layer.layer_collection.children["SRC_LEAVES"].exclude = True
    stage = bpy.data.collections.new("STAGE")
    sc.collection.children.link(stage)

    M = {}
    made = {}
    made["Palm"] = build_palm(M, src)
    for name, sp in SPECIES.items():
        made[name] = build_tree(name, sp, M, src)

    # review lineup: instance hero collections along X; LOD1 collections excluded from the view layer
    for name, (hero, lod) in made.items():
        bpy.context.view_layer.layer_collection.children["LIB_VEGETATION"].children[lod.name].exclude = True
        bpy.context.view_layer.layer_collection.children["LIB_VEGETATION"].children[hero.name].exclude = True
    xs = {"Palm": 0.0, "Neem": 13.0, "Mango": 28.0, "Banyan": 52.0, "Peepal": 77.0, "Amaltas": 92.0}
    for name, x in xs.items():
        e = bpy.data.objects.new("STG_%s" % name, None)
        e.instance_type = "COLLECTION"
        e.instance_collection = made[name][0]
        e.location = (x, 0, 0)
        stage.objects.link(e)
    e = bpy.data.objects.new("STG_Mango_LOD1_compare", None)
    e.instance_type = "COLLECTION"
    e.instance_collection = made["Mango"][1]
    e.location = (28, 26, 0)
    stage.objects.link(e)

    gm = H.mat_ground()
    hb = HB()
    hb.add([(-300, -300, 0), (300, -300, 0), (300, 300, 0), (-300, 300, 0)], [(0, 1, 2, 3)], gm)
    stage.objects.link(bpy.data.objects.new("STG_Ground", hb.to_mesh("ME_STG_Ground", recalc=False)))

    w = bpy.data.worlds.new("WLD_Day_Clear")
    sc.world = w
    t = H.NT(w)
    tc = t.n("ShaderNodeTexCoord")
    z = t.n("ShaderNodeSeparateXYZ", Vector=tc.outputs["Generated"]).outputs["Z"]
    col = t.ramp(z, [(0.0, H.hex_lin("#F2DCB8")), (0.12, H.hex_lin("#B9D2E6")), (0.45, H.hex_lin("#5E93CC"))])
    bg = t.n("ShaderNodeBackground", Color=col, Strength=1.0)
    t.link(bg.outputs[0], t.n("ShaderNodeOutputWorld").inputs["Surface"])
    sd = bpy.data.lights.new("LGT_Sun_Afternoon", "SUN")
    sd.energy = 4.5
    sd.color = (1.0, 0.9, 0.77)
    sd.angle = math.radians(1.5)
    sun = bpy.data.objects.new("LGT_Sun_Afternoon", sd)
    sun.rotation_euler = (math.radians(52), 0.0, math.radians(-38))
    stage.objects.link(sun)
    cams = {
        "CAM_Trees_Lineup":   ((46.0, -78.0, 5.5), (46.0, 0.0, 7.0), 26, None),
        "CAM_Mango_Canopy":   ((22.0, -9.0, 1.6), (28.0, 0.0, 5.0), 24, None),
        "CAM_Banyan_Trunk":   ((44.0, -16.0, 1.6), (52.0, 0.0, 4.0), 24, None),
        "CAM_Amaltas_Close":  ((88.5, -5.0, 2.2), (92.0, 0.0, 4.2), 40, 5.5),
        "CAM_Palm_Neem":      ((4.0, -22.0, 2.0), (7.5, 0.0, 6.5), 30, None),
        "CAM_LOD_Compare":    ((28.0, -28.0, 6.0), (28.0, 13.0, 4.5), 30, None),
    }
    for name, (pos, tgt, lens, focus) in cams.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 3000
        if focus:
            cd.dof.use_dof = True
            cd.dof.focus_distance = focus
            cd.dof.aperture_fstop = 2.8
        co = bpy.data.objects.new(name, cd)
        co.location = pos
        co.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        stage.objects.link(co)
    sc.camera = bpy.data.objects["CAM_Trees_Lineup"]

    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception as ex:
        print("[trees] GPU setup failed:", ex)
    quick = "--quick" in ARGS
    sc.cycles.samples = 48 if quick else 192
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = (1280, 720) if quick else (1920, 1080)

    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_Trees_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[trees] saved", OUT_BLEND)
    if "--render" in ARGS:
        os.makedirs(OUT_REVIEW, exist_ok=True)
        only = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None
        for c in cams:
            if only and c != only:
                continue
            sc.camera = bpy.data.objects[c]
            sc.render.filepath = os.path.join(OUT_REVIEW, c + ".png")
            bpy.ops.render.render(write_still=True)
            print("[trees] rendered", c)


main()
