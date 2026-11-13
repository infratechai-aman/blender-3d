"""
FIRST HUMAN CHARACTER - style test (G5 gate).  CHR_Human_Woman_001 "young village woman", ~25 y.

  blender -b --factory-startup --python hero_human_woman_001.py -- [--render] [--quick] [--only CAM_A,CAM_B]

Output: 04_CHARACTERS/HUMANS/CHR_Human_Woman_001.blend  (collection CHR_Human_Woman_001)
Reviews: 10_EXPORTS/REVIEWS/G5_HUMAN_WOMAN_001_v001/  front, side, back, 3/4, face close-ups

Build method (script-only, as agreed):  head = analytic sculpt of a dense sphere (jaw, cheekbones, nose, eye
sockets, lips, chin);  body/hands/feet = clay metaballs;  eyes = sclera/iris/pupil + lids + lashes;  hair =
centre-parted cap + braid with a jasmine gajra;  clothing = fitted blouse cut from the body, lathe saree skirt
with front pleats and hem border, swept pallu over the left shoulder;  bangles, bindi, nose stud, earrings.
NOT rigged yet - that comes after the look is approved.  Height 1.58 m, faces -Y.
"""
import datetime
import math
import os
import random
import shutil
import sys

import bmesh
import bpy
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import char_lib as CL  # noqa: E402
import hero_lib as H  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "04_CHARACTERS", "HUMANS", "CHR_Human_Woman_001.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "G5_HUMAN_WOMAN_001_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HC = np.array([0.0, 0.008, 1.455])          # head centre (world)
HEAD_ABC = (0.077, 0.093, 0.113)            # head half-width / half-depth / half-height
COLL = None


def ss(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def g2(x, z, cx, cz, sx, sz):
    return np.exp(-((x - cx) ** 2) / (2 * sx * sx) - ((z - cz) ** 2) / (2 * sz * sz))


# ============================================================================ materials
def materials():
    M = {
        "skin": CL.mat_skin("MAT_Skin_Woman_001", "#A06A4A"),
        "lip": CL.mat_skin("MAT_Lip_Woman_001", "#8A4842", rough=0.35),
        "hair": mat_hair("MAT_Hair_Black_Oiled", "#1A1310"),
        "brow": CL.mat_principled("MAT_Hair_Brow", "#1E1611", 0.6),
        "sclera": CL.mat_principled("MAT_Eye_Sclera", "#E9E2D8", 0.15, coat=1.0),
        "iris": CL.mat_principled("MAT_Eye_Iris_Brown", "#3A2316", 0.12, coat=1.0, noise=0.35, noise_scale=900),
        "pupil": CL.mat_principled("MAT_Eye_Pupil", "#050403", 0.05, coat=1.0),
        "kajal": CL.mat_principled("MAT_Kajal_Lash", "#0D0A09", 0.5),
        "blouse": CL.mat_principled("MAT_Cloth_Blouse_Magenta", "#9C1E48", 0.75, sheen=0.4, noise=0.12, noise_scale=400),
        "gold": CL.mat_principled("MAT_Metal_Gold_Jewellery", "#C9962E", 0.25, 1.0),
        "bangle_red": CL.mat_principled("MAT_Glass_Bangle_Red", "#B3121F", 0.08, coat=1.0),
        "bangle_green": CL.mat_principled("MAT_Glass_Bangle_Green", "#1F7A2E", 0.08, coat=1.0),
        "bindi": CL.mat_principled("MAT_Bindi_Red", "#B0101A", 0.3),
        "jasmine": CL.mat_principled("MAT_Flower_Jasmine", "#F3EFE2", 0.6, sheen=0.3),
        "leaf": CL.mat_principled("MAT_Leaf_Gajra", "#3C6A2A", 0.5),
        "sole": CL.mat_principled("MAT_Chappal_Leather", "#5A3A26", 0.7),
    }
    M["skin_head"] = mat_skin_head("MAT_Skin_Woman_001_Head", "#A06A4A", "#86443F")
    M["saree_skirt"] = mat_saree("MAT_Saree_Teal_Skirt", "skirt")
    M["saree_pallu"] = mat_saree("MAT_Saree_Teal_Pallu", "pallu")
    return M


def mat_hair(name, base):
    """Oiled black hair: strand streaks (noise stretched along Z) for colour, roughness and bump."""
    m, t = H._mat(name, base)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    mp = t.n("ShaderNodeMapping", Vector=obj, Scale=(900.0, 900.0, 25.0))
    n = t.noise(mp.outputs[0], 1.0, 4.0, 0.6)
    col = t.ramp(n.outputs["Fac"], [(0.3, H.hex_lin(base, 0.7)), (0.6, H.hex_lin(base)), (0.8, H.hex_lin("#3A2A20"))])
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.link(t.n("ShaderNodeMapRange", Value=n.outputs["Fac"], **{"To Min": 0.36, "To Max": 0.55}).outputs["Result"], t.inp(b, "Roughness"))
    t.link(t.bump(n.outputs["Fac"], 0.5, 0.002), t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def mat_skin_head(name, base, lip):
    """Skin with a soft lip-colour mask (object space = world, head centre HC) and a hint of cheek warmth."""
    m, t = H._mat(name, base)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=obj)
    x = sx.outputs["X"]
    y = t.math("SUBTRACT", sx.outputs["Y"], float(HC[1]))
    z = t.math("SUBTRACT", sx.outputs["Z"], float(HC[2]))
    ex = t.math("DIVIDE", x, 0.0185)
    ez = t.math("DIVIDE", t.math("ADD", z, 0.0565), 0.0105)
    r2 = t.math("ADD", t.math("MULTIPLY", ex, ex), t.math("MULTIPLY", ez, ez))
    lipm = t.n("ShaderNodeMapRange", Value=r2, **{"From Min": 0.75, "From Max": 1.05, "To Min": 1.0, "To Max": 0.0}).outputs["Result"]
    lipm = t.math("MULTIPLY", lipm, t.math("LESS_THAN", y, -0.06))
    cx = t.math("DIVIDE", t.math("SUBTRACT", t.math("ABSOLUTE", x), 0.045), 0.02)
    cz = t.math("DIVIDE", t.math("ADD", z, 0.02), 0.018)
    ch = t.n("ShaderNodeMapRange", Value=t.math("ADD", t.math("MULTIPLY", cx, cx), t.math("MULTIPLY", cz, cz)),
             **{"From Min": 0.0, "From Max": 1.0, "To Min": 0.25, "To Max": 0.0}).outputs["Result"]
    big = t.noise(obj, 6.0, 3.0, 0.5)
    col = t.ramp(big.outputs["Fac"], [(0.35, H.hex_lin(base, 0.94)), (0.65, H.hex_lin(base, 1.04))])
    col = t.mix(t.math("MULTIPLY", ch, t.math("LESS_THAN", y, -0.04)), col, H.hex_lin("#B0604A"))
    col = t.mix(lipm, col, H.hex_lin(lip))
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.link(t.n("ShaderNodeMapRange", Value=lipm, **{"To Min": 0.5, "To Max": 0.3}).outputs["Result"], t.inp(b, "Roughness"))
    for nm, val in (("Subsurface Weight", 0.25), ("Subsurface Scale", 0.012)):
        try:
            t.inp(b, nm).default_value = val
        except Exception:
            pass
    try:
        t.inp(b, "Subsurface Radius").default_value = (1.0, 0.45, 0.3)
    except Exception:
        pass
    fine = t.noise(obj, 60.0, 4.0, 0.5)
    t.link(t.bump(fine.outputs["Fac"], 0.06, 0.002), t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def mat_saree(name, mode):
    """Teal cotton-silk with small gold buttis; magenta + zari border from the UV (skirt: hem, pallu: edges + end)."""
    m, t = H._mat(name, "#16716F")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    uv = t.n("ShaderNodeUVMap").outputs["UV"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=uv)
    u, v = sx.outputs["X"], sx.outputs["Y"]
    weave = t.noise(obj, 900.0, 2.0, 0.5)
    base = t.ramp(weave.outputs["Fac"], [(0.3, H.hex_lin("#11605E")), (0.7, H.hex_lin("#1B807C"))])
    vor = t.n("ShaderNodeTexVoronoi", Vector=obj, Scale=28.0)
    dot = t.ramp(vor.outputs["Distance"], [(0.07, (1, 1, 1, 1)), (0.1, (0, 0, 0, 1))])
    dotf = t.n("ShaderNodeSeparateColor", Color=dot).outputs[0]
    col = t.mix(dotf, base, H.hex_lin("#C79A3A"))
    if mode == "skirt":
        edge = t.math("LESS_THAN", v, 0.085)
        zari = t.math("MULTIPLY", t.math("COMPARE", v, 0.075, 0.006), 1.0)
        inner = t.math("COMPARE", v, 0.02, 0.006)
    else:
        e1 = t.math("MAXIMUM", t.math("LESS_THAN", u, 0.14), t.math("GREATER_THAN", u, 0.86))
        edge = t.math("MAXIMUM", e1, t.math("GREATER_THAN", v, 0.78))
        zari = t.math("MAXIMUM", t.math("COMPARE", u, 0.13, 0.012), t.math("COMPARE", u, 0.87, 0.012))
        zari = t.math("MAXIMUM", zari, t.math("COMPARE", v, 0.79, 0.008))
        inner = t.math("MULTIPLY", t.math("GREATER_THAN", v, 0.84),
                       t.math("GREATER_THAN", t.math("SINE", t.math("MULTIPLY", v, 260.0)), 0.6))
    border = t.ramp(weave.outputs["Fac"], [(0.3, H.hex_lin("#8E1A46")), (0.7, H.hex_lin("#A8245A"))])
    col = t.mix(edge, col, border)
    col = t.mix(t.math("MINIMUM", t.math("ADD", zari, inner), 1.0), col, H.hex_lin("#D2A443"))
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.inp(b, "Roughness").default_value = 0.6
    try:
        t.inp(b, "Sheen Weight").default_value = 0.5
        t.inp(b, "Sheen Tint").default_value = (1.0, 0.95, 0.85, 1)
    except Exception:
        pass
    t.link(t.bump(weave.outputs["Fac"], 0.15, 0.001), t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


# ============================================================================ head
def head_surface(nu=160, nv=120):
    """Dense sculpted head (head-local).  Returns V (nv*nu,3), F, front-surface sampler."""
    a, b, c = HEAD_ABC
    th = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    ph = np.linspace(0.0001, np.pi - 0.0001, nv)
    TH, PH = np.meshgrid(th, ph)
    x = a * np.sin(PH) * np.cos(TH)
    y = b * np.sin(PH) * np.sin(TH)
    z = c * np.cos(PH)
    # skull + jaw
    jaw = ss(-0.02, -0.112, z)
    x = x * (1 - 0.27 * jaw) * (1 + 0.05 * np.exp(-((z + 0.045) ** 2) / (2 * 0.02 ** 2)))   # softer jaw, fuller cheeks
    back = y > 0
    y = np.where(back, y * (1 - 0.42 * jaw) * (1 + 0.08 * ss(0.0, 0.07, z)), y * (1 - 0.10 * jaw))
    x = x * (1 + 0.04 * ss(0.02, 0.08, z))                     # temples / crown width
    z = np.where(z < -0.07, z - 0.012 * ss(-0.07, -0.11, z) * (1 - np.abs(x) / 0.05).clip(0), z)  # chin length
    z = np.where(z < -0.078, -0.078 + (z + 0.078) * 0.55, z)              # shorter face, flatter jaw underside
    x = x * (1 + 0.10 * np.exp(-((z + 0.088) ** 2) / (2 * 0.012 ** 2)))  # broader chin
    # flatten the face plane a touch
    front = ss(-0.03, -0.075, y)
    y = y + 0.004 * front * ss(0.06, -0.02, z)
    # features: displacement toward -Y on the front of the face
    d = np.zeros_like(x)
    tn = np.clip((0.022 - z) / 0.052, 0, 1)                    # 0 at bridge (z=.022) -> 1 at tip (z=-.03)
    prot = (0.0015 + 0.0165 * tn ** 1.9) * (1 - ss(-0.027, -0.040, z)) * (z < 0.03)
    d -= prot * np.exp(-(x ** 2) / (2 * (0.0055 + 0.005 * tn) ** 2))
    for sxn in (-1, 1):
        d -= 0.0065 * g2(x, z, sxn * 0.0125, -0.031, 0.006, 0.006)        # alae
        d += 0.0125 * g2(x, z, sxn * 0.032, 0.013, 0.015, 0.011)         # eye sockets
        d -= 0.0035 * g2(x, z, sxn * 0.031, 0.034, 0.02, 0.006)          # brow ridge
        d -= 0.0080 * g2(x, z, sxn * 0.046, -0.020, 0.019, 0.017)        # cheekbones
    d += 0.0030 * g2(x, z, 0.0, -0.040, 0.004, 0.004)                     # under-nose
    d -= 0.0060 * g2(x, z, 0.0, -0.0505, 0.0165, 0.0055)                  # upper lip
    for sxn in (-1, 1):
        d -= 0.0012 * g2(x, z, sxn * 0.006, -0.0485, 0.004, 0.003)        # cupid bow peaks
    d -= 0.0058 * g2(x, z, 0.0, -0.0625, 0.0150, 0.0058)                  # lower lip
    d += 0.0026 * g2(x, z, 0.0, -0.0565, 0.0175, 0.0013)                  # mouth line
    d += 0.0030 * g2(x, z, 0.0, -0.074, 0.016, 0.005)                     # mentolabial fold
    d -= 0.0055 * g2(x, z, 0.0, -0.091, 0.0145, 0.010)                    # chin
    y = y + d * ss(-0.035, -0.07, y)
    V = np.stack([x, y, z], -1).reshape(-1, 3)
    F = []
    for j in range(nv - 1):
        for i in range(nu):
            a0 = j * nu + i
            b0 = j * nu + (i + 1) % nu
            F.append((a0, b0, b0 + nu, a0 + nu))
    return V, F, (nu, nv)


def front_y(V, x, z, tol=None):
    """Y of the face surface at (x, z): nearest front vertex in the x/z plane."""
    fr = V[V[:, 1] < -0.02]
    d = (fr[:, 0] - x) ** 2 + (fr[:, 2] - z) ** 2
    return float(fr[int(np.argmin(d)), 1])


def build_head(M):
    V, F, (nu, nv) = head_surface()
    # lips material by face centre
    Vw = V + HC
    o = CL.mesh_obj("GEO_Woman001_Head", Vw, F, M["skin_head"], COLL)
    o.modifiers.new("Sub", "SUBSURF").levels = 1
    # eyes
    for sx in (-1, 1):
        ex, ez = sx * 0.0325, 0.0125
        ys = front_y(V, ex, ez)
        r = 0.0132
        ec = HC + np.array([ex, ys + r - 0.0042, ez])
        eye(M, ec, r, sx)
        brow(M, V, sx)
    # ears (clay)
    ear = CL.Clay("Woman001_Ears", 0.0025)
    for sx in (-1, 1):
        cx = HC + np.array([sx * 0.0715, 0.012, -0.005])
        ear.ellipsoid(tuple(cx), 0.0075, 0.016, 0.027, CL.q_axis((0, 1, 0), sx * 0.25))
        ear.ellipsoid(tuple(cx + np.array([sx * 0.006, -0.002, -0.004])), 0.004, 0.009, 0.014, neg=True)
    ear.to_mesh(M["skin"], 3, COLL)
    # bindi, nose stud
    yb = front_y(V, 0.0, 0.043)
    put_sphere("GEO_Woman001_Bindi", HC + np.array([0, yb - 0.0005, 0.043]), (0.0042, 0.0012, 0.0042), M["bindi"])
    yn = front_y(V, -0.0135, -0.029, 0.003)
    put_sphere("GEO_Woman001_NoseStud", HC + np.array([-0.0135, yn - 0.0006, -0.029]), (0.0017, 0.0017, 0.0017), M["gold"])
    for sx in (-1, 1):                                                      # jhumka earrings
        top = HC + np.array([sx * 0.074, 0.006, -0.028])
        put_sphere("GEO_Woman001_EarStud_%s" % ("L" if sx < 0 else "R"), top, (0.003, 0.003, 0.003), M["gold"])
        hb = H.HB()
        hb.lathe(M["gold"], [(0.0, -0.028), (0.009, -0.027), (0.008, -0.018), (0.004, -0.008), (0.0012, 0.0)], 16,
                 top[0], top[1], top[2] - 0.004)
        for k in range(10):
            a = 2 * math.pi * k / 10
            hb.ellipsoid(top[0] + 0.0095 * math.cos(a), top[1] + 0.0095 * math.sin(a), top[2] - 0.033, 0.0015, 0.0015, 0.0015,
                         M["gold"], 6, 4)
        o2 = bpy.data.objects.new("GEO_Woman001_Jhumka_%s" % ("L" if sx < 0 else "R"), hb.to_mesh("ME_Jhumka", recalc=False))
        COLL.objects.link(o2)
    return V


def put_sphere(name, c, r, mat, seg=16):
    hb = H.HB()
    hb.ellipsoid(c[0], c[1], c[2], r[0], r[1], r[2], mat, seg, seg // 2)
    me = hb.to_mesh("ME_" + name, recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    return o


def sphere_cap(c, r, max_ang, nseg=32, nring=10, front=(0, -1, 0)):
    """Spherical cap around `front` direction (for iris / pupil / lids)."""
    f = np.asarray(front, float)
    f /= np.linalg.norm(f)
    up = np.array([0, 0, 1.0])
    sd = np.cross(f, up)
    sd /= np.linalg.norm(sd)
    up = np.cross(sd, f)
    V = [c + f * r]
    for j in range(1, nring + 1):
        a = max_ang * j / nring
        for i in range(nseg):
            t = 2 * math.pi * i / nseg
            dvec = f * math.cos(a) + (sd * math.cos(t) + up * math.sin(t)) * math.sin(a)
            V.append(c + dvec * r)
    F = [(0, 1 + i, 1 + (i + 1) % nseg) for i in range(nseg)]
    for j in range(nring - 1):
        for i in range(nseg):
            a0 = 1 + j * nseg + i
            b0 = 1 + j * nseg + (i + 1) % nseg
            F.append((a0, b0, b0 + nseg, a0 + nseg))
    return V, F


def eye(M, c, r, sx):
    side = "L" if sx < 0 else "R"
    put_sphere("GEO_Woman001_Eye_%s" % side, c, (r, r, r), M["sclera"], 24)
    gaze = np.array([sx * -0.04, -1.0, -0.03])                         # slight convergence, eyes a touch down
    V, F = sphere_cap(c, r * 1.004, 0.62, front=gaze)
    CL.mesh_obj("GEO_Woman001_Iris_%s" % side, V, F, M["iris"], COLL)
    V, F = sphere_cap(c, r * 1.006, 0.25, front=gaze)
    CL.mesh_obj("GEO_Woman001_Pupil_%s" % side, V, F, M["pupil"], COLL)
    # lids: shells over the eyeball; the gap between them is the almond opening
    R = r * 1.12
    nseg, nring = 40, 16
    for lid, (a0, a1, closed) in (("Upper", (0.0, 1.0, 0.50)), ("Lower", (0.0, 1.0, 0.33))):
        Vl = []
        for j in range(nring + 1):
            v = j / nring
            for i in range(nseg + 1):
                u = i / nseg
                az = -1.25 + 2.5 * u                                    # across the eye (radians around Z)
                rim = closed * (1 - 0.55 * (2 * u - 1) ** 2)            # almond: lids meet at the corners
                el = (0.5 * math.pi - v * (0.5 * math.pi - rim)) if lid == "Upper" else -(0.5 * math.pi - v * (0.5 * math.pi - rim))
                if lid == "Upper":
                    el += 0.06 * (u - 0.5) * sx                         # tilt the outer corner up a little
                dvec = np.array([math.sin(az) * math.cos(el) * -1, -math.cos(az) * math.cos(el), math.sin(el)])
                Vl.append(c + dvec * R)
        Fl = []
        for j in range(nring):
            for i in range(nseg):
                a = j * (nseg + 1) + i
                Fl.append((a, a + 1, a + nseg + 2, a + nseg + 1))
        o = CL.mesh_obj("GEO_Woman001_Lid%s_%s" % (lid, side), Vl, Fl, M["skin"], COLL)
        sol = o.modifiers.new("Thick", "SOLIDIFY")
        sol.thickness = 0.0016
        sol.offset = 1.0
        # lash/kajal line along the lid edge
        edge = np.array(Vl[nring * (nseg + 1):(nring + 1) * (nseg + 1)])
        out = edge - c
        out /= np.linalg.norm(out, axis=1)[:, None]
        L = 0.0035 if lid == "Upper" else 0.0016
        tip = edge + out * 0.0006 + np.array([0, -0.6, 1.0 if lid == "Upper" else -1.0]) * L
        Vk = np.r_[edge + out * 0.0003, tip]
        Fk = [(i, i + 1, len(edge) + i + 1, len(edge) + i) for i in range(len(edge) - 1)]
        k = CL.mesh_obj("GEO_Woman001_Lash%s_%s" % (lid, side), Vk, Fk, M["kajal"], COLL)
        k.modifiers.new("Thick", "SOLIDIFY").thickness = 0.0005


def brow(M, V, sx):
    xs = np.linspace(0.014, 0.052, 18)
    pts, sides = [], []
    for k, x in enumerate(xs):
        t = k / (len(xs) - 1)
        z = 0.031 + 0.007 * math.sin(math.pi * min(t * 1.25, 1.0)) - 0.004 * t
        y = front_y(V, sx * x, z, 0.003) - 0.0012
        pts.append(HC + np.array([sx * x, y, z]))
        sides.append(np.array([0, 0, 1.0]))
    w = [0.0026 * (1.0 - 0.55 * (k / (len(xs) - 1)) ** 1.5) + 0.0006 for k in range(len(xs))]
    Vb, Fb, _ = CL.sweep(pts, sides, w, 4)
    o = CL.mesh_obj("GEO_Woman001_Brow_%s" % ("L" if sx < 0 else "R"), Vb, Fb, M["brow"], COLL)
    o.modifiers.new("Thick", "SOLIDIFY").thickness = 0.0008


# ============================================================================ hair
def build_hair(M, V):
    nu, nv = 160, 120
    a, b, c = HEAD_ABC
    th = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    ph = np.linspace(0.0001, np.pi * 0.72, 90)
    TH, PH = np.meshgrid(th, ph)
    dx = np.sin(PH) * np.cos(TH)
    dy = np.sin(PH) * np.sin(TH)
    dz = np.cos(PH)
    hl = np.where(dy < 0, 0.068 - 0.05 * ss(0.25, 0.9, np.abs(dx)) * (1 - ss(-0.2, 0.3, dy)), 0.0226 - 0.11 * ss(0.0, 0.9, dy))
    hl = np.maximum(hl, np.where(dy < -0.3, 0.045, -1.0))               # never below the brow line on the face
    vol = 0.0028 + 0.0035 * ss(0.3, 1.0, dz) + 0.0025 * ss(0.0, 0.8, dy)
    wv = ss(-0.008, 0.003, c * dz - hl)
    vol = vol * wv - 0.006 * (1 - wv)
    x = (a + vol) * dx * (1 + 0.04 * ss(0.02, 0.08, c * dz))
    y = (b + vol) * dy
    z = (c + vol) * dz
    part = np.exp(-(x ** 2) / (2 * 0.0025 ** 2)) * ss(0.0, -0.06, y) * ss(0.04, 0.1, z)       # centre parting
    z = z - 0.0035 * part
    # hairline: forehead / temples / nape
    keep = z > np.where(dy < -0.3, hl - 0.004, hl - 0.016)
    # swept hair covers the upper ear a little
    Vh = np.stack([x, y, z], -1).reshape(-1, 3)
    keep = keep.ravel()
    idx = -np.ones(len(Vh), int)
    idx[keep] = np.arange(keep.sum())
    F = []
    nphi = len(ph)
    for j in range(nphi - 1):
        for i in range(nu):
            q = [j * nu + i, j * nu + (i + 1) % nu, (j + 1) * nu + (i + 1) % nu, (j + 1) * nu + i]
            if all(keep[k] for k in q):
                F.append(tuple(idx[k] for k in q))
    o = CL.mesh_obj("GEO_Woman001_HairCap", Vh[keep] + HC, F, M["hair"], COLL)
    sol = o.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = 0.003
    sol.offset = -1.0
    o.modifiers.new("Sub", "SUBSURF").levels = 1
    # braid: alternating lobes down the back, gajra at the top, tassel at the end
    clay = CL.Clay("Woman001_Braid", 0.003)
    top = HC + np.array([0.0, 0.088, -0.045])
    n = 22
    for k in range(n):
        t = k / (n - 1)
        p = top + np.array([0.006 * math.sin(t * 2.0), 0.035 * t + 0.02 * math.sin(t * 2.6), -0.50 * t])
        w = 0.024 * (1 - 0.55 * t) + 0.007
        s = 1 if k % 2 else -1
        clay.ellipsoid(tuple(p + np.array([s * w * 0.35, 0.0, 0.0])), w * 0.62, w * 0.55, w * 1.15,
                       CL.q_axis((0, 1, 0), s * 0.45))
    clay.ball(tuple(top + np.array([0, -0.01, 0.025])), 0.03)
    clay.to_mesh(M["hair"], 2, COLL)
    rng = random.Random(3)
    hb = H.HB()
    for ring in range(3):                                                    # gajra
        zc = top[2] + 0.012 - ring * 0.02
        for k in range(18):
            ang = 2 * math.pi * k / 18 + ring * 0.2
            r = 0.031 - ring * 0.004
            px, py = top[0] + r * math.cos(ang), top[1] + 0.008 + r * math.sin(ang) * 0.9
            if py < top[1] - 0.012:
                continue
            hb.ellipsoid(px, py, zc + rng.uniform(-0.003, 0.003), 0.0055, 0.0055, 0.0075, M["jasmine"], 8, 5)
    tip = top + np.array([0, 0.035 + 0.02 * math.sin(2.6), -0.52])
    hb.frustum(tip[0], tip[1], tip[2] - 0.05, tip[2] + 0.01, 0.006, 0.012, 10, M["hair"])
    for k in range(6):
        hb.ellipsoid(tip[0] + rng.uniform(-0.006, 0.006), tip[1] + rng.uniform(-0.006, 0.006), tip[2] - 0.05 - k * 0.006,
                     0.006, 0.006, 0.006, M["bangle_red"], 8, 4)
    me = hb.to_mesh("ME_Woman001_Gajra", recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new("GEO_Woman001_Gajra_Paranda", me)
    COLL.objects.link(o)


# ============================================================================ body
ARM = {}


def build_body(M):
    c = CL.Clay("Woman001_Body", 0.0055)
    c.capsule((0, 0.016, 1.285), (0, 0.010, 1.39), 0.042, 0.038)                    # neck
    c.ellipsoid((0, 0.008, 1.245), 0.135, 0.075, 0.06)                              # shoulder girdle
    c.ellipsoid((0, -0.004, 1.16), 0.128, 0.088, 0.095)                             # rib cage
    for sx in (-1, 1):
        c.ball((sx * 0.052, -0.058, 1.148), 0.05)                                    # bust
        c.ball((sx * 0.148, 0.008, 1.25), 0.048)                                     # deltoid
    c.ellipsoid((0, 0.004, 1.025), 0.104, 0.075, 0.075)                             # waist
    c.ellipsoid((0, 0.016, 0.905), 0.158, 0.105, 0.095)                             # pelvis
    for sx in (-1, 1):
        c.capsule((sx * 0.085, 0.012, 0.86), (sx * 0.078, 0.0, 0.49), 0.078, 0.05)   # thigh
        c.capsule((sx * 0.078, 0.0, 0.49), (sx * 0.074, 0.012, 0.09), 0.046, 0.031)  # shin
        c.ball((sx * 0.079, 0.022, 0.36), 0.045)                                     # calf
        c.capsule((sx * 0.074, 0.01, 0.07), (sx * 0.084, -0.14, 0.024), 0.034, 0.024)  # foot
        c.ball((sx * 0.074, 0.03, 0.035), 0.032)                                     # heel
        # arm, relaxed A-pose
        sh = np.array([sx * 0.16, 0.008, 1.245])
        el = np.array([sx * 0.245, 0.022, 0.995])
        wr = np.array([sx * 0.305, -0.004, 0.772])
        c.capsule(sh, el, 0.041, 0.031)
        c.capsule(el, wr, 0.032, 0.0235)
        c.ball(tuple(el + np.array([0, 0.008, 0.035])), 0.034)                       # forearm mass
        palm = wr + np.array([sx * 0.012, -0.006, -0.048])
        c.ellipsoid(tuple(palm), 0.013, 0.031, 0.043, CL.q_axis((0, 1, 0), sx * 0.22))
        c.capsule(wr, palm, 0.021, 0.018)
        ARM[sx] = dict(sh=sh, el=el, wr=wr, palm=palm)
    body = c.to_mesh(M["skin"], 6, COLL)
    # fingers: own clay families so they never web together
    for sx in (-1, 1):
        palm = ARM[sx]["palm"]
        base_z = palm[2] - 0.034
        for k, (dy, L, r) in enumerate(((-0.022, 0.058, 0.0074), (-0.0075, 0.066, 0.0076), (0.0075, 0.062, 0.0072),
                                        (0.021, 0.05, 0.0064))):
            f = CL.Clay("Woman001_Finger_%s%d" % ("L" if sx < 0 else "R", k), 0.0018)
            p0 = np.array([palm[0] + sx * 0.004, palm[1] + dy, base_z + 0.01])
            curl = 0.012 + 0.004 * k
            p1 = p0 + np.array([sx * 0.002, 0, -L * 0.45])
            p2 = p1 + np.array([-sx * curl * 0.5, -0.002, -L * 0.33])
            p3 = p2 + np.array([-sx * curl * 0.8, -0.002, -L * 0.22])
            f.chain([p0, p1, p2, p3], [r, r * 0.92, r * 0.85, r * 0.72])
            f.ball(tuple(p3), r * 0.72)
            f.to_mesh(M["skin"], 2, COLL)
        t = CL.Clay("Woman001_Thumb_%s" % ("L" if sx < 0 else "R"), 0.0018)
        q0 = palm + np.array([-sx * 0.004, -0.026, 0.012])
        q1 = q0 + np.array([-sx * 0.006, -0.016, -0.024])
        q2 = q1 + np.array([-sx * 0.008, -0.006, -0.022])
        t.chain([q0, q1, q2], [0.0105, 0.0088, 0.0075])
        t.ball(tuple(q2), 0.0075)
        t.to_mesh(M["skin"], 2, COLL)
    return body


# ============================================================================ clothing
def build_blouse(M, body):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    bm = bmesh.new()
    bm.from_mesh(me)
    kill = []
    for v in bm.verts:
        x, y, z = v.co
        keep = 1.075 < z < 1.305 and abs(x) < 0.30
        if keep and y < -0.02 and z > 1.235 and abs(x) < 0.075 - (1.305 - z) * 0.4:
            keep = False                                                     # front neckline scoop
        if keep and y > 0.03 and z > 1.27 and abs(x) < 0.06:
            keep = False                                                     # back neckline
        if keep and abs(x) > 0.15:                                           # sleeves stop mid upper arm
            sxn = 1 if x > 0 else -1
            sh, el = ARM[sxn]["sh"], ARM[sxn]["el"]
            ax = (el - sh) / np.linalg.norm(el - sh)
            s = float((np.array(v.co) - sh) @ ax)
            keep = s < 0.105
        if not keep:
            kill.append(v)
    bmesh.ops.delete(bm, geom=kill, context="VERTS")
    for _ in range(12):
        bnd = [v for v in bm.verts if v.is_boundary]
        new = {}
        for v in bnd:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                new[v] = (v.co * 0.4 + (nb[0].co + nb[1].co) * 0.3)
        for v, co in new.items():
            v.co = co
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * 0.0045
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    me.materials.append(M["blouse"])
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new("GEO_Woman001_Blouse", me)
    COLL.objects.link(o)
    s = o.modifiers.new("Thick", "SOLIDIFY")
    s.thickness = 0.0025
    s.offset = 1.0
    # sleeve hem piping
    return o


def skirt_radius(theta, z):
    """Saree skirt: elliptical lathe that flares from the tuck to the hem, with folds + front pleats."""
    zt = np.clip((1.0 - z) / 0.96, 0, 1)
    r = 0.122 + 0.07 * ss(0.0, 0.14, zt) + 0.055 * zt ** 1.3
    rng_phase = 1.7
    amp = 0.0015 + 0.011 * zt ** 1.2
    folds = amp * (0.6 * np.sin(7 * theta + rng_phase + 2.0 * zt) + 0.4 * np.sin(13 * theta + 0.4 + 3.0 * zt))
    front = np.exp(-((theta + np.pi / 2) ** 2) / (2 * 0.3 ** 2))         # pleat fan at -Y
    tri = 2 * np.abs((theta * 24 / np.pi) % 2 - 1) - 1
    pleat = (0.004 + 0.016 * zt) * tri * front * ss(0.97, 0.9, z)
    return r + folds * (1 - 0.6 * front) + pleat


def build_skirt(M):
    nu, nv = 220, 90
    th = np.linspace(-np.pi, np.pi, nu, endpoint=False)
    zs = np.linspace(1.005, 0.045, nv)
    TH, Z = np.meshgrid(th, zs)
    R = skirt_radius(TH, Z)
    yc = 0.012
    X = R * np.cos(TH)
    Y = yc + R * np.sin(TH) * 0.78
    hem_drop = 0.012 * np.sin(TH * 3 + 0.3) * ss(0.2, 0.045, Z)
    Z2 = Z + hem_drop
    V = np.stack([X, Y, Z2], -1).reshape(-1, 3)
    F = CL.grid_faces(nu, nv, closed_u=True)
    o = CL.mesh_obj("GEO_Woman001_SareeSkirt", V, F, M["saree_skirt"], COLL)
    uv = np.stack([(TH + np.pi) / (2 * np.pi), (Z - 0.045) / 0.96 * 1.0], -1).reshape(-1, 2)
    CL.set_uv(o, [tuple(u) for u in uv])
    s = o.modifiers.new("Thick", "SOLIDIFY")
    s.thickness = 0.003
    o.modifiers.new("Sub", "SUBSURF").levels = 1
    # waist tuck band (the rolled top of the saree)
    hb = H.HB()
    for k in range(48):
        a0, a1 = 2 * math.pi * k / 48, 2 * math.pi * (k + 1) / 48
        p0 = np.array([0.124 * math.cos(a0), yc + 0.124 * math.sin(a0) * 0.8, 1.0])
        p1 = np.array([0.124 * math.cos(a1), yc + 0.124 * math.sin(a1) * 0.8, 1.0])
        hb.rod(M["saree_skirt"], p0, p1, 0.007, 8)
    me = hb.to_mesh("ME_Woman001_Tuck", recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    t = bpy.data.objects.new("GEO_Woman001_SareeTuck", me)
    COLL.objects.link(t)


def build_pallu(M):
    """Pallu: tucked at the right hip, pleated diagonally over the bust, over the left shoulder, down the back."""
    ctrl = [(0.10, -0.098, 0.985), (0.06, -0.118, 1.06), (0.005, -0.127, 1.135), (-0.055, -0.118, 1.205),
            (-0.105, -0.075, 1.27), (-0.135, -0.01, 1.298), (-0.14, 0.055, 1.282), (-0.13, 0.11, 1.2),
            (-0.10, 0.145, 1.04), (-0.07, 0.165, 0.86), (-0.05, 0.18, 0.69)]
    from geo import catmull_rom
    P = catmull_rom([(p[0], p[1], p[2]) for p in ctrl], 10)
    n = len(P)
    sides, half = [], []
    for k in range(n):
        t = k / (n - 1)
        tg = P[min(k + 1, n - 1)] - P[max(k - 1, 0)]
        tg /= np.linalg.norm(tg)
        out = np.array([P[k][0], P[k][1] - 0.01, 0.0])
        if t > 0.42 and t < 0.6:
            out = out * 0.4 + np.array([0, 0, 1.0])                          # over the shoulder top
        out /= np.linalg.norm(out)
        sd = np.cross(tg, out)
        sd /= np.linalg.norm(sd)
        sides.append(sd)
        half.append(0.03 + 0.008 * ss(0.0, 0.3, t) + 0.14 * ss(0.62, 1.0, t))
    sides = np.array(sides)

    def fold(t, s):
        k = int(round(t * (n - 1)))
        out = np.array([P[k][0], P[k][1], 0.0])
        out = out / (np.linalg.norm(out) + 1e-9)
        gathered = 1.0 - ss(0.45, 0.7, t)
        amp = 0.006 * gathered + 0.009 * ss(0.6, 1.0, t)
        freq = 5.5 if gathered > 0.5 else 3.0
        return out * amp * math.sin(s * math.pi * freq + t * 6.0) + np.array([0, 0, -0.03 * ss(0.8, 1.0, t) * (1 - abs(s))])

    V, F, UV = CL.sweep(P, sides, half, 18, fold)
    o = CL.mesh_obj("GEO_Woman001_Pallu", V, F, M["saree_pallu"], COLL)
    CL.set_uv(o, UV)
    s = o.modifiers.new("Thick", "SOLIDIFY")
    s.thickness = 0.0025
    s.offset = 1.0
    o.modifiers.new("Sub", "SUBSURF").levels = 1


def build_jewellery(M):
    for sx in (-1, 1):
        el, wr = ARM[sx]["el"], ARM[sx]["wr"]
        ax = (wr - el) / np.linalg.norm(wr - el)
        for k in range(7):
            c = wr - ax * (0.012 + k * 0.0075)
            mat = M["gold"] if k in (0, 6) else (M["bangle_red"] if k % 2 else M["bangle_green"])
            torus("GEO_Woman001_Bangle_%s%d" % ("L" if sx < 0 else "R", k), c, ax, 0.036 + 0.001 * k, 0.0028, mat)
    for sx in (-1, 1):                                                         # chappals
        hb = H.HB()
        hb.box(sx * 0.074 - 0.042, sx * 0.084 + 0.042, -0.19, 0.075, -0.001, 0.012, M["sole"])
        hb.rod(M["sole"], (sx * 0.084 - 0.035, -0.11, 0.012), (sx * 0.084 + 0.035, -0.11, 0.012), 0.008, 6)
        o = bpy.data.objects.new("GEO_Woman001_Chappal_%s" % ("L" if sx < 0 else "R"), hb.to_mesh("ME_Chappal"))
        COLL.objects.link(o)


def torus(name, c, axis, R, r, mat, nu=48, nv=10):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    a = np.cross(axis, [0, 0, 1.0])
    if np.linalg.norm(a) < 1e-3:
        a = np.cross(axis, [1, 0, 0])
    a /= np.linalg.norm(a)
    b = np.cross(axis, a)
    V = []
    for i in range(nu):
        u = 2 * math.pi * i / nu
        ring = a * math.cos(u) + b * math.sin(u)
        for j in range(nv):
            v = 2 * math.pi * j / nv
            V.append(c + ring * (R + r * math.cos(v)) + axis * r * math.sin(v))
    F = []
    for i in range(nu):
        for j in range(nv):
            F.append((i * nv + j, ((i + 1) % nu) * nv + j, ((i + 1) % nu) * nv + (j + 1) % nv, i * nv + (j + 1) % nv))
    CL.mesh_obj(name, V, F, mat, COLL)


# ============================================================================
def main():
    global COLL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "CHR_Human_Woman_001"
    sc.unit_settings.system = "METRIC"
    COLL = bpy.data.collections.new("CHR_Human_Woman_001")
    sc.collection.children.link(COLL)
    M = materials()
    V = build_head(M)
    build_hair(M, V)
    body = build_body(M)
    build_blouse(M, body)
    build_skirt(M)
    build_pallu(M)
    build_jewellery(M)
    for o in list(sc.collection.objects):                               # stray empty metaball parents
        if o.type == "META":
            bpy.data.objects.remove(o, do_unlink=True)
    quick = "--quick" in ARGS
    cams = {
        "CAM_Front":      ((0.0, -3.6, 0.86), (0.0, 0.0, 0.82), 50, 1200, 1500),
        "CAM_Side_L":     ((-3.6, 0.0, 0.86), (0.0, 0.0, 0.82), 50, 1200, 1500),
        "CAM_Back":       ((0.0, 3.6, 0.86), (0.0, 0.0, 0.82), 50, 1200, 1500),
        "CAM_ThreeQuarter": ((-2.2, -2.7, 1.05), (0.0, 0.0, 0.84), 50, 1200, 1500),
        "CAM_Face":       ((0.0, -0.78, 1.47), (0.0, 0.0, 1.45), 85, 1200, 1200),
        "CAM_Face_34":    ((-0.5, -0.62, 1.49), (0.0, 0.0, 1.445), 85, 1200, 1200),
        "CAM_Hands_Cloth": ((-0.55, -0.75, 1.0), (-0.18, 0.0, 0.95), 60, 1400, 1050),
    }
    if quick:
        cams = {k: (p, t, l, rx * 2 // 3, ry * 2 // 3) for k, (p, t, l, rx, ry) in cams.items()}
    objs = CL.review_stage(cams, OUT_REVIEW, "Woman001", samples=48 if quick else 128)
    sc.camera = objs["CAM_Front"][0]
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "CHR_Human_Woman_001_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[char] saved", OUT_BLEND, "objects:", len(COLL.objects))
    if "--render" in ARGS:
        only = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
        CL.render_cams(objs, OUT_REVIEW, only)


if __name__ == "__main__":
    main()
