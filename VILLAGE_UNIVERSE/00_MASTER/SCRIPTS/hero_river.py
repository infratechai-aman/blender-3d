"""
HERO RIVER KIT: water, riverbank, stone arch bridge, ghat (Amaltaspur).

  blender -b --factory-startup --python hero_river.py -- [--render] [--quick] [--only CAM]

Output: 01_ENVIRONMENT/WATER/LIB_River_Bridge_Ghat.blend
  AST_Bridge_Stone_A   3-arch stone bridge, origin = deck centre at river centre line, road along +X
  AST_Ghat_A           river steps + chhatri, origin = top-of-steps centre, steps descend toward +X
  ENV_Riverbank_Kit    boulders, reed clumps, grass tufts (instanced)
Dimensions match the master river: bed -3.2 m, water -1.7 m, ~32 m wide water.
"""
import datetime
import math
import os
import random
import shutil
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector, noise

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "01_ENVIRONMENT", "WATER", "LIB_River_Bridge_Ghat.blend")
TREES_BLEND = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Trees.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "PH1B_RIVER_BRIDGE_GHAT_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

BED, WATER = -3.2, -1.7
DECK = 2.6
HALF_W = 3.7
GHAT_Y = 38.0
COLL = {}


def coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    COLL[name] = c
    return c


def put(hb, name, cname, loc=(0, 0, 0), recalc=True, smooth=False):
    me = hb.to_mesh("ME_" + name, recalc=recalc)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me)
    o.location = loc
    COLL[cname].objects.link(o)
    return o


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def meander(y):
    return 2.5 * np.sin(np.asarray(y) * 0.025)


def bank_h(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    d = np.abs(x - meander(y))
    k = 1 - smoothstep(9.0, 24.0, d)
    top = 0.35 + 0.12 * np.sin(x * 0.21 + y * 0.13) + 0.08 * np.sin(y * 0.41)
    bed = BED + 0.12 * np.sin(x * 1.3) * np.cos(y * 1.1)
    h = top * (1 - k) + bed * k
    # cut the bank back under the ghat so the steps are not buried
    gy0, gy1 = GHAT_Y - 11.8, GHAT_Y + 11.8
    inside = (y > gy0) & (y < gy1) & (x > -28.5) & (x < -8.0)
    step_z = 0.55 - (x + 28.0) / 16.5 * (0.55 - (WATER - 0.9)) - 0.35
    return np.where(inside, np.minimum(h, step_z), h)


# ============================================================================
def materials():
    return {
        "stone": H.mat_stone_wet("MAT_Stone_Bridge_Sandstone", "#A08A70", "#B49C7E", "#6E6050", wet_top=-0.9),
        "arch": H.mat_stone_wet("MAT_Stone_Bridge_ArchRing", "#BCA585", "#C9B293", "#7A6A57", wet_top=-1.0,
                                scale=2.2, bw=0.5, rh=0.5),
        "coping": H.mat_simple("MAT_Stone_Coping_Light", "#C2B39C", 0.75, noise=0.12),
        "setts": H.mat_paving("MAT_Paving_Stone_Setts", "#8C8478", "#9E968A", "#5E584F", scale=3.0, rough=0.85),
        "ghat": H.mat_stone_wet("MAT_Stone_Ghat_Steps", "#B7A38A", "#C7B49A", "#7C6E5C", wet_top=-1.2,
                                scale=1.0, bw=1.0, rh=0.2),
        "chhatri": H.mat_plaster("MAT_Plaster_Chhatri_Cream", "#E9DCC2"),
        "saffron": H.mat_simple("MAT_Cloth_Saffron", "#E3722A", 0.7, noise=0.1),
        "brass": H.mat_simple("MAT_Metal_Brass", "#B8903A", 0.3, 1.0),
        "wood": H.mat_wood(),
        "rope": H.mat_rope(),
        "water": H.mat_water(),
        "bank": H.mat_riverbank(),
        "rock": H.mat_stone_wet("MAT_Rock_River_Boulder", "#7E766B", "#8E857A", "#5C554D", wet_top=-1.4,
                                scale=0.4, bw=1.0, rh=1.0),
        "reed": H.mat_simple("MAT_Foliage_Reed", "#6D8A3A", 0.55, noise=0.25),
        "grass": H.mat_simple("MAT_Foliage_GrassTuft", "#7C9444", 0.6, noise=0.3),
    }


# ============================================================================
def build_terrain(M):
    xs = np.arange(-80, 80.01, 0.5)
    ys = np.arange(-70, 70.01, 0.5)
    X, Y = np.meshgrid(xs, ys)
    Z = bank_h(X, Y)
    nx, ny = len(xs), len(ys)
    idx = np.arange(nx * ny).reshape(ny, nx)
    f = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    me = bpy.data.meshes.new("ME_Riverbank")
    me.from_pydata(np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1).tolist(), [], f.tolist())
    me.materials.append(M["bank"])
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new("ENV_Riverbank_Terrain", me)
    COLL["STAGE"].objects.link(o)
    # closed water body so volume absorption gives depth colour
    hb = HB()
    hb.box(-22.0, 22.0, -70.0, 70.0, BED - 0.6, WATER, M["water"])
    put(hb, "ENV_River_Water_Body", "STAGE")


def build_bridge(M):
    """v002: humpback deck + graduated arches (big centre span) + plan curve (Simple Deform bend).
    Body is built from thin vertical slices so the bend deforms it smoothly."""
    L = 20.0
    zb = -3.9
    zs = -1.3
    BASE, HUMP = 1.6, 2.4                      # structure top at the ends / extra height at the centre
    spans = [(-16.1, -8.1, 2.8), (-5.5, 5.5, 4.2), (8.1, 16.1, 2.8)]
    piers = [-6.8, 6.8]

    def top(x):
        return BASE + HUMP * (1 - (x / L) ** 2)

    arcs = []
    for a, b, rise in spans:
        s = b - a
        R = ((s / 2) ** 2 + rise ** 2) / (2 * rise)
        cz = zs + rise - R
        arcs.append((a, b, (a + b) / 2, R, cz, math.asin((zs - cz) / R)))

    def soffit(x):
        for a, b, cx, R, cz, th0 in arcs:
            if a < x < b:
                return cz + math.sqrt(max(0.0, R * R - (x - cx) ** 2))
        return None

    body = HB()
    xs = np.linspace(-L, L, 161)
    for x0, x1 in zip(xs[:-1], xs[1:]):
        s0, s1 = soffit(x0 + 1e-4), soffit(x1 - 1e-4)
        b0 = zb if s0 is None else s0
        b1 = zb if s1 is None else s1
        if (s0 is None) != (s1 is None):        # slice straddles a springing point
            b0 = b1 = zb if s0 is None else zs
            b0 = zb if s0 is None else b0
            b1 = zb if s1 is None else b1
        v = [(x0, -HALF_W, b0), (x1, -HALF_W, b1), (x1, HALF_W, b1), (x0, HALF_W, b0),
             (x0, -HALF_W, top(x0)), (x1, -HALF_W, top(x1)), (x1, HALF_W, top(x1)), (x0, HALF_W, top(x0))]
        body.add(v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], M["stone"])
    bobj = put(body, "GEO_Bridge_Body", "AST_Bridge_Stone_A")

    hb = HB()
    for a, b, cx, R, cz, th0 in arcs:
        n = max(13, int((math.pi - 2 * th0) * R / 0.55)) | 1
        for i in range(n):
            th = th0 + (math.pi - 2 * th0) * (i + 0.5) / n
            key = i == n // 2
            depth = 1.05 if key else 0.75
            r = R + depth / 2
            c = np.array([cx + r * math.cos(th), 0.0, cz + r * math.sin(th)])
            radial = np.array([math.cos(th), 0.0, math.sin(th)])
            tang = np.array([-math.sin(th), 0.0, math.cos(th)])
            arc_w = (math.pi - 2 * th0) * R / n
            for sy in (-1, 1):
                cc = c.copy()
                cc[1] = sy * (HALF_W + 0.04)
                hb.obox(M["arch"], cc, radial, tang, depth / 2, (arc_w * (1.25 if key else 1.0)) / 2 - 0.015, 0.11)
    for px in piers:
        for sy in (-1, 1):
            y0, y1 = sy * HALF_W, sy * (HALF_W + 1.6)
            v = [(px - 1.3, y0, zb), (px + 1.3, y0, zb), (px, y1, zb),
                 (px - 1.3, y0, zs + 0.7), (px + 1.3, y0, zs + 0.7), (px, y1, zs + 0.7)]
            hb.add(v, [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)], M["stone"])
            v = [(px - 1.3, y0, zs + 0.7), (px + 1.3, y0, zs + 0.7), (px, y1, zs + 0.7), (px, y0 + sy * 0.3, zs + 2.0)]
            hb.add(v, [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)], M["coping"])
    seg = np.linspace(-L, L, 41)
    for sy in (-1, 1):
        ya, yb = (HALF_W - 0.42, HALF_W) if sy > 0 else (-HALF_W, -HALF_W + 0.42)
        sa, sb = (HALF_W - 0.12, HALF_W + 0.1) if sy > 0 else (-HALF_W - 0.1, -HALF_W + 0.12)
        for x0, x1 in zip(seg[:-1], seg[1:]):
            z0, z1 = top(x0), top(x1)

            def slab(ya_, yb_, za0, za1, zb0, zb1, mat):
                hb.add([(x0, ya_, za0), (x1, ya_, za1), (x1, yb_, za1), (x0, yb_, za0),
                        (x0, ya_, zb0), (x1, ya_, zb1), (x1, yb_, zb1), (x0, yb_, zb0)],
                       [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)
            slab(sa, sb, z0 - 0.95, z1 - 0.95, z0 - 0.75, z1 - 0.75, M["coping"])          # string course
            slab(ya, yb, z0, z1, z0 + 1.15, z1 + 1.15, M["stone"])                          # parapet
            slab(ya - 0.06, yb + 0.06, z0 + 1.15, z1 + 1.15, z0 + 1.3, z1 + 1.3, M["coping"])
            slab(-HALF_W + 0.42, HALF_W - 0.42, z0, z1, z0 + 0.4, z1 + 0.4, M["setts"])      # road deck
        for px in (-L, piers[0], piers[1], L):
            ya2, yb2 = (HALF_W - 0.6, HALF_W + 0.1) if sy > 0 else (-HALF_W - 0.1, -HALF_W + 0.6)
            hb.box(px - 0.4, px + 0.4, ya2, yb2, top(px) - 0.2, top(px) + 1.6, M["stone"])
            hb.box(px - 0.5, px + 0.5, ya2 - 0.08, yb2 + 0.08, top(px) + 1.6, top(px) + 1.75, M["coping"])
            hb.frustum(px, (ya2 + yb2) / 2, top(px) + 1.75, top(px) + 2.2, 0.32, 0.0, 4, M["coping"], rot=math.pi / 4)
    # approach ramps (sliced too, so they bend with the deck)
    zr0 = top(L) + 0.4
    for sx in (-1, 1):
        rx = np.linspace(L, L + 16.0, 17)
        for xa, xb in zip(rx[:-1], rx[1:]):
            za = zr0 + (0.42 - zr0) * (xa - L) / 16.0
            zb_ = zr0 + (0.42 - zr0) * (xb - L) / 16.0
            x0, x1 = sx * xa, sx * xb
            if x0 > x1:
                x0, x1, za, zb_ = x1, x0, zb_, za
            for (y0_, y1_, zo, mat) in ((-HALF_W, HALF_W, -0.02, M["stone"]),):
                hb.add([(x0, y0_, -0.8), (x1, y0_, -0.8), (x1, y1_, -0.8), (x0, y1_, -0.8),
                        (x0, y0_, za + zo), (x1, y0_, zb_ + zo), (x1, y1_, zb_ + zo), (x0, y1_, za + zo)],
                       [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)
            hb.add([(x0, -HALF_W + 0.42, za - 0.02), (x1, -HALF_W + 0.42, zb_ - 0.02), (x1, HALF_W - 0.42, zb_ - 0.02),
                    (x0, HALF_W - 0.42, za - 0.02), (x0, -HALF_W + 0.42, za + 0.03), (x1, -HALF_W + 0.42, zb_ + 0.03),
                    (x1, HALF_W - 0.42, zb_ + 0.03), (x0, HALF_W - 0.42, za + 0.03)],
                   [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], M["setts"])
            hgt = 0.9 * (1 - (min(abs(x0), abs(x1)) - L) / 16.0) + 0.15
            for ya, yb in ((HALF_W - 0.42, HALF_W), (-HALF_W, -HALF_W + 0.42)):
                hb.add([(x0, ya, za), (x1, ya, zb_), (x1, yb, zb_), (x0, yb, za),
                        (x0, ya, za + hgt), (x1, ya, zb_ + hgt), (x1, yb, zb_ + hgt), (x0, yb, za + hgt)],
                       [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], M["stone"])
    dobj = put(hb, "GEO_Bridge_Details", "AST_Bridge_Stone_A")
    for o in (bobj, dobj):
        md = o.modifiers.new("PlanCurve", "SIMPLE_DEFORM")
        md.deform_method = "BEND"
        md.deform_axis = "Z"
        md.angle = math.radians(BRIDGE_BEND_DEG)
    print("[river] bridge v002: humpback (+%.1f m), spans 8/11/8 m, plan bend %d deg" % (HUMP, BRIDGE_BEND_DEG))


BRIDGE_BEND_DEG = 22


def build_bridge_v001(M):
    hb = HB()
    L = 20.0
    zb = -3.9
    spans = [(-16.1, -7.1), (-4.5, 4.5), (7.1, 16.1)]
    zs, rise = -1.3, 3.0
    s = 9.0
    R = ((s / 2) ** 2 + rise ** 2) / (2 * rise)
    cz = zs + rise - R
    th0 = math.asin((zs - cz) / R)

    def top(x):
        return DECK - 0.4 + 0.25 * (1 - (x / L) ** 2)       # slight hump; road sits 0.4 above structure

    outline = [(-L, zb)] + [(x, top(x)) for x in np.linspace(-L, L, 21)] + [(L, zb)]
    for a, b in reversed(spans):
        cx = (a + b) / 2
        outline.append((b, zb))
        outline.append((b, zs))
        for th in np.linspace(th0, math.pi - th0, 24)[1:-1]:
            outline.append((cx + R * math.cos(th), cz + R * math.sin(th)))
        outline.append((a, zs))
        outline.append((a, zb))
    bm = bmesh.new()
    vs = [bm.verts.new((x, -HALF_W, z)) for x, z in outline]
    face = bm.faces.new(vs)
    ext = bmesh.ops.extrude_face_region(bm, geom=[face])
    nv = [e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=nv, vec=(0, 2 * HALF_W, 0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("ME_Bridge_Body")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(M["stone"])
    body = bpy.data.objects.new("GEO_Bridge_Body", me)
    COLL["AST_Bridge_Stone_A"].objects.link(body)

    # voussoirs + keystones on both faces
    for a, b in spans:
        cx = (a + b) / 2
        n = 19
        for i in range(n):
            th = th0 + (math.pi - 2 * th0) * (i + 0.5) / n
            key = i == n // 2
            depth = 1.0 if key else 0.72
            r = R + depth / 2
            c = np.array([cx + r * math.cos(th), 0.0, cz + r * math.sin(th)])
            radial = np.array([math.cos(th), 0.0, math.sin(th)])
            tang = np.array([-math.sin(th), 0.0, math.cos(th)])
            arc_w = (math.pi - 2 * th0) * R / n
            for sy in (-1, 1):
                cc = c.copy()
                cc[1] = sy * (HALF_W + 0.04)
                hb.obox(M["arch"], cc, radial, tang, depth / 2, (arc_w * (1.2 if key else 1.0)) / 2 - 0.015, 0.11)
        # cutwaters on the piers
    for px in (-5.8, 5.8):
        for sy in (-1, 1):
            y0 = sy * HALF_W
            y1 = sy * (HALF_W + 1.6)
            for z0, z1, w in ((zb, zs + 0.7, 1.3),):
                v = [(px - w, y0, z0), (px + w, y0, z0), (px, y1, z0), (px - w, y0, z1), (px + w, y0, z1), (px, y1, z1)]
                hb.add(v, [(0, 2, 1), (3, 4, 5), (0, 1, 4, 3), (1, 2, 5, 4), (2, 0, 3, 5)], M["stone"])
            apex = (px, y0 + sy * 0.3, zs + 1.9)
            v = [(px - 1.3, y0, zs + 0.7), (px + 1.3, y0, zs + 0.7), (px, y1, zs + 0.7), apex]
            hb.add(v, [(0, 1, 2), (0, 3, 1), (1, 3, 2), (2, 3, 0)], M["coping"])
    # string course, parapets, pilasters, coping
    for sy in (-1, 1):
        for i in range(20):
            x0, x1 = -L + i * 2.0, -L + (i + 1) * 2.0
            zt = min(top(x0), top(x1))
            hb.box(x0, x1 + 0.01, sy * HALF_W - 0.12 if sy > 0 else -HALF_W - 0.1, sy * HALF_W + 0.1 if sy > 0 else -HALF_W + 0.12,
                   zt - 0.95, zt - 0.75, M["coping"])
            ya, yb = (HALF_W - 0.42, HALF_W) if sy > 0 else (-HALF_W, -HALF_W + 0.42)
            hb.box(x0, x1 + 0.01, ya, yb, zt, zt + 0.4 + 0.75, M["stone"])
            hb.box(x0, x1 + 0.01, ya - 0.06, yb + 0.06, zt + 1.15, zt + 1.3, M["coping"])
        for px in (-L, -5.8, 5.8, L):
            ya, yb = (HALF_W - 0.6, HALF_W + 0.1) if sy > 0 else (-HALF_W - 0.1, -HALF_W + 0.6)
            hb.box(px - 0.4, px + 0.4, ya, yb, top(px) - 0.2, top(px) + 1.6, M["stone"])
            hb.box(px - 0.5, px + 0.5, ya - 0.08, yb + 0.08, top(px) + 1.6, top(px) + 1.75, M["coping"])
            hb.frustum(px, (ya + yb) / 2, top(px) + 1.75, top(px) + 2.2, 0.32, 0.0, 4, M["coping"], rot=math.pi / 4)
    # deck surface (setts) + approach ramps with retaining walls
    for i in range(20):
        x0, x1 = -L + i * 2.0, -L + (i + 1) * 2.0
        hb.add([(x0, -HALF_W + 0.42, top(x0) + 0.4), (x1, -HALF_W + 0.42, top(x1) + 0.4),
                (x1, HALF_W - 0.42, top(x1) + 0.4), (x0, HALF_W - 0.42, top(x0) + 0.4),
                (x0, -HALF_W + 0.42, top(x0)), (x1, -HALF_W + 0.42, top(x1)),
                (x1, HALF_W - 0.42, top(x1)), (x0, HALF_W - 0.42, top(x0))],
               [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], M["setts"])
    for sx in (-1, 1):
        xa, xb = sx * L, sx * (L + 14.0)
        za, zb2 = top(L) + 0.4, 0.42
        lo, hi = sorted((xa, xb))
        zlo = za if lo == xa else zb2
        zhi = za if hi == xa else zb2
        v = [(lo, -HALF_W, -0.8), (hi, -HALF_W, -0.8), (hi, HALF_W, -0.8), (lo, HALF_W, -0.8),
             (lo, -HALF_W, zlo - 0.02), (hi, -HALF_W, zhi - 0.02), (hi, HALF_W, zhi - 0.02), (lo, HALF_W, zlo - 0.02)]
        hb.add(v, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], M["stone"])
        v2 = [(lo, -HALF_W + 0.42, zlo - 0.02), (hi, -HALF_W + 0.42, zhi - 0.02), (hi, HALF_W - 0.42, zhi - 0.02),
              (lo, HALF_W - 0.42, zlo - 0.02)]
        v2 += [(p[0], p[1], p[2] + 0.04) for p in v2]
        hb.add(v2, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], M["setts"])
        for sy in (-1, 1):
            ya, yb = (HALF_W - 0.42, HALF_W) if sy > 0 else (-HALF_W, -HALF_W + 0.42)
            wv = [(lo, ya, zlo), (hi, ya, zhi), (hi, yb, zhi), (lo, yb, zlo)]
            wv += [(p[0], p[1], p[2] + (0.9 if (p[0] == xa) else 0.45)) for p in wv]
            hb.add(wv, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], M["stone"])
    put(hb, "GEO_Bridge_Details", "AST_Bridge_Stone_A")
    print("[river] bridge: 3 segmental arches span %.1f m, rise %.1f m, R %.2f m, deck %.2f m" % (s, rise, R, DECK))


def build_ghat(M):
    """Built in place on the west bank: steps descend toward +X into the river."""
    hb = HB()
    y0, y1 = GHAT_Y - 10.0, GHAT_Y + 10.0
    x_top, x_bot = -28.0, -11.5
    n = 15
    tread = (x_bot - x_top) / n
    z_top = 0.55
    z_bot = WATER - 0.9
    riser = (z_top - z_bot) / n
    for i in range(n):                    # one solid column per tread, each lower than the last
        xa = x_top + i * tread
        z = z_top - (i + 1) * riser
        hb.box(xa, xa + tread + 0.002, y0, y1, BED - 0.8, z, M["ghat"])
        hb.box(xa - 0.04, xa + 0.08, y0, y1, z - 0.04, z + 0.002, M["coping"])      # bullnose lip
    hb.box(-36.0, x_top, y0 - 1.5, y1 + 1.5, -0.6, z_top, M["ghat"])                 # top platform
    for sy, yy in ((-1, y0), (1, y1)):                                                 # stepped side walls
        ya, yb = (yy - 1.2, yy) if sy < 0 else (yy, yy + 1.2)
        for i in range(0, n, 3):
            xa = x_top + i * tread
            z = z_top - i * riser + 0.9
            hb.box(xa, min(x_bot, xa + 3 * tread), ya, yb, BED - 0.8, z, M["ghat"])
            hb.box(xa - 0.05, min(x_bot, xa + 3 * tread) + 0.05, ya - 0.06, yb + 0.06, z, z + 0.1, M["coping"])
        # diya niches in the wall faces
        for i in (1, 4, 7):
            xa = x_top + i * tread + 0.4
            z = z_top - i * riser + 0.25
            face = yb if sy < 0 else ya
            hb.box(xa, xa + 0.4, face - 0.02 if sy < 0 else face - 0.06, face + 0.06 if sy < 0 else face + 0.02,
                   z, z + 0.45, M["chhatri"])
    # chhatri on the platform
    cx, cy = -32.0, y1 - 1.0
    hb.box(cx - 2.2, cx + 2.2, cy - 2.2, cy + 2.2, z_top, z_top + 0.45, M["coping"])
    for dx in (-1.6, 1.6):
        for dy in (-1.6, 1.6):
            hb.frustum(cx + dx, cy + dy, z_top + 0.45, z_top + 0.7, 0.28, 0.24, 8, M["coping"])
            hb.frustum(cx + dx, cy + dy, z_top + 0.7, z_top + 3.2, 0.17, 0.15, 12, M["chhatri"])
            hb.frustum(cx + dx, cy + dy, z_top + 3.2, z_top + 3.4, 0.24, 0.24, 8, M["coping"])
    hb.box(cx - 2.1, cx + 2.1, cy - 2.1, cy + 2.1, z_top + 3.4, z_top + 3.65, M["chhatri"])
    hb.lathe(M["chhatri"], [(1.95, 0), (1.95, 0.15), (1.85, 0.5), (1.55, 0.95), (1.05, 1.3), (0.45, 1.5),
                            (0.12, 1.62), (0.0, 1.66)][::-1][::-1], 24, cx, cy, z_top + 3.65)
    hb.lathe(M["brass"], [(0.0, 0.0), (0.12, 0.05), (0.08, 0.25), (0.13, 0.4), (0.03, 0.6), (0.0, 0.75)], 12,
             cx, cy, z_top + 5.3)
    hb.rod(M["wood"], (cx, cy, z_top + 3.4), (cx, cy, z_top + 2.7), 0.01, 6)          # temple bell
    hb.lathe(M["brass"], [(0.0, 0.0), (0.16, 0.02), (0.13, 0.12), (0.08, 0.26), (0.0, 0.3)], 16, cx, cy, z_top + 2.42)
    # saffron flag on the chhatri
    hb.rod(M["wood"], (cx + 1.6, cy + 1.6, z_top + 3.65), (cx + 1.6, cy + 1.6, z_top + 6.2), 0.03, 6)
    hb.add([(cx + 1.6, cy + 1.6, z_top + 6.1), (cx + 2.7, cy + 1.6, z_top + 5.75), (cx + 1.6, cy + 1.6, z_top + 5.4)],
           [(0, 1, 2), (2, 1, 0)], M["saffron"])
    # mooring post + brass lotas on the steps
    hb.frustum(x_bot - 0.6, y0 + 1.2, z_bot, z_bot + 2.6, 0.18, 0.15, 10, M["wood"])
    lota = [(0.0, 0.0), (0.06, 0.005), (0.11, 0.06), (0.12, 0.12), (0.08, 0.2), (0.05, 0.23), (0.07, 0.26)]
    for (i, dy) in ((3, 2.0), (3, 2.35), (8, -3.0)):
        hb.lathe(M["brass"], lota, 16, x_top + i * tread + 0.4, GHAT_Y + dy, z_top - i * riser)
    put(hb, "GEO_Ghat_Steps_Chhatri", "AST_Ghat_A")
    print("[river] ghat: %d steps, tread %.2f m, riser %.2f m" % (n, tread, riser))
    return (x_top, x_bot, y0, y1)


def rock_meshes(M, k=5):
    out = []
    for i in range(k):
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
        off = Vector((i * 3.1, i * 1.7, i * 0.9))
        for v in bm.verts:
            p = v.co
            d = 1.0 + 0.32 * noise.noise(p * 1.1 + off) + 0.12 * noise.noise(p * 3.0 + off)
            v.co = Vector((p.x * d * 1.25, p.y * d, p.z * d * 0.62))
        me = bpy.data.meshes.new("ME_Rock_River_%02d" % (i + 1))
        bm.to_mesh(me)
        bm.free()
        me.materials.append(M["rock"])
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
        out.append(me)
    return out


def blade_clump(hb, mat, n, hmin, hmax, rng, spread=0.12):
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        lean = rng.uniform(0.15, 0.55)
        h = rng.uniform(hmin, hmax)
        w = 0.012 + 0.01 * h
        d = np.array([math.cos(a), math.sin(a), 0.0])
        side = np.array([-d[1], d[0], 0.0])
        base = d * rng.uniform(0, spread)
        pts = [base + d * lean * h * (t * t) + np.array([0, 0, h * t]) for t in (0, 0.35, 0.7, 1.0)]
        v = []
        for j, p in enumerate(pts):
            ww = w * (1 - j / 3.0) + 0.001
            v += [tuple(p - side * ww), tuple(p + side * ww)]
        hb.add(v, [(0, 1, 3, 2), (2, 3, 5, 4), (4, 5, 7, 6)], mat)


def scatter_bank(M, ghat_box):
    rng = random.Random(17)
    kit = COLL["ENV_Riverbank_Kit"]
    src = COLL["SRC_KIT"]
    rocks = rock_meshes(M)
    gx0, gx1, gy0, gy1 = ghat_box
    nrock = 0
    for i in range(70):
        y = rng.uniform(-68, 68)
        side = rng.choice((-1, 1))
        d = rng.uniform(10.5, 22.0)
        x = meander(y) + side * d
        if abs(y) < 8 or (gy0 - 3 < y < gy1 + 3 and x < -8):
            continue
        s = rng.uniform(0.25, 1.1) * (1.0 if d < 18 else 0.6)
        o = bpy.data.objects.new("ENV_Rock_%03d" % i, rocks[i % len(rocks)])
        o.location = (x, y, float(bank_h(x, y)) - 0.25 * s)
        o.rotation_euler = (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), rng.uniform(0, 6.28))
        o.scale = (s, s, s)
        kit.objects.link(o)
        nrock += 1
    hb = HB()
    blade_clump(hb, M["reed"], 16, 0.6, 1.4, random.Random(1), 0.15)
    reed = bpy.data.objects.new("SRC_Reed_Clump", hb.to_mesh("ME_Reed_Clump", recalc=False))
    src.objects.link(reed)
    hb = HB()
    blade_clump(hb, M["grass"], 22, 0.15, 0.4, random.Random(2), 0.1)
    tuft = bpy.data.objects.new("SRC_Grass_Tuft", hb.to_mesh("ME_Grass_Tuft", recalc=False))
    src.objects.link(tuft)

    def pts(n, dmin, dmax, smin, smax):
        P, R, S = [], [], []
        while len(P) < n:
            y = rng.uniform(-69, 69)
            x = meander(y) + rng.choice((-1, 1)) * rng.uniform(dmin, dmax)
            if abs(y) < 6 and abs(x) < 36:
                continue
            if gy0 - 2 < y < gy1 + 2 and gx0 - 9 < x < gx1 + 1:
                continue
            z = float(bank_h(x, y))
            if z < WATER - 0.15:
                continue
            P.append((x, y, z - 0.02))
            R.append((rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), rng.uniform(0, 6.28)))
            S.append(rng.uniform(smin, smax))
        return P, R, S

    H.points_object("ENV_Reeds_Bank", *pts(900, 14.5, 21.5, 0.6, 1.3), kit, H.instancer("GN_Reeds", reed))
    H.points_object("ENV_GrassTufts_Bank", *pts(5000, 20.0, 78.0, 0.7, 1.6), kit, H.instancer("GN_GrassTufts", tuft))
    print("[river] bank kit: %d boulders, 900 reed clumps, 5000 grass tufts" % nrock)


def link_trees():
    if not os.path.exists(TREES_BLEND):
        print("[river] tree library missing, skipping context trees")
        return
    want = ["VEG_Tree_Peepal_A", "VEG_Tree_Palm_A", "VEG_Tree_Mango_A", "VEG_Tree_Neem_A", "VEG_Tree_Banyan_A_LOD1"]
    with bpy.data.libraries.load(TREES_BLEND, link=True) as (src, dst):
        dst.collections = [c for c in src.collections if c in want]
    lib = {c.name: c for c in dst.collections if c}
    place = [("VEG_Tree_Peepal_A", (-40, 50, 0.4), 0.3), ("VEG_Tree_Palm_A", (-30, 22, 0.3), 1.2),
             ("VEG_Tree_Palm_A", (-34, 25, 0.3), 2.5), ("VEG_Tree_Palm_A", (29, 30, 0.3), 0.5),
             ("VEG_Tree_Mango_A", (-46, 12, 0.35), 1.0), ("VEG_Tree_Neem_A", (34, -24, 0.35), 2.0),
             ("VEG_Tree_Mango_A", (40, 52, 0.35), 4.0), ("VEG_Tree_Banyan_A_LOD1", (-62, -40, 0.35), 0.0)]
    for i, (name, loc, rz) in enumerate(place):
        if name not in lib:
            continue
        e = bpy.data.objects.new("STG_Tree_%02d" % i, None)
        e.instance_type = "COLLECTION"
        e.instance_collection = lib[name]
        e.location = loc
        e.rotation_euler = (0, 0, rz)
        COLL["STAGE"].objects.link(e)


def stage(M):
    sc = bpy.context.scene
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
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(-30))
    COLL["STAGE"].objects.link(sun)
    cams = {
        "CAM_Bridge_34":         ((30.0, -38.0, 3.0), (0.0, 0.0, 0.2), 28, None),
        "CAM_Bridge_WaterLevel": ((5.0, -20.0, -1.05), (-1.0, 0.0, 0.4), 22, None),
        "CAM_Ghat_Front":        ((24.0, 36.0, 1.8), (-22.0, 39.0, -0.2), 28, None),
        "CAM_Ghat_Close":        ((-9.5, 26.5, -0.6), (-22.0, 40.0, 0.4), 24, None),
        "CAM_River_Aerial":      ((52.0, -58.0, 32.0), (-4.0, 12.0, 0.0), 28, None),
    }
    for name, (pos, tgt, lens, focus) in cams.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 3000
        co = bpy.data.objects.new(name, cd)
        co.location = pos
        co.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        COLL["STAGE"].objects.link(co)
    sc.camera = bpy.data.objects["CAM_Bridge_34"]
    return list(cams)


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "LIB_River_Bridge_Ghat"
    sc.unit_settings.system = "METRIC"
    for c in ("AST_Bridge_Stone_A", "AST_Ghat_A", "ENV_Riverbank_Kit", "SRC_KIT", "STAGE"):
        coll(c)
    bpy.context.view_layer.layer_collection.children["SRC_KIT"].exclude = True
    M = materials()
    build_terrain(M)
    build_bridge(M)
    ghat_box = build_ghat(M)
    scatter_bank(M, ghat_box)
    link_trees()
    cams = stage(M)
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception as ex:
        print("[river] GPU setup failed:", ex)
    quick = "--quick" in ARGS
    sc.cycles.samples = 64 if quick else 256
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 10
    sc.cycles.transmission_bounces = 8
    sc.cycles.volume_bounces = 1
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = (1280, 720) if quick else (1920, 1080)
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_River_Bridge_Ghat_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[river] saved", OUT_BLEND)
    if "--render" in ARGS:
        os.makedirs(OUT_REVIEW, exist_ok=True)
        only = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None
        for c in cams:
            if only and c != only:
                continue
            sc.camera = bpy.data.objects[c]
            sc.render.filepath = os.path.join(OUT_REVIEW, c + ".png")
            bpy.ops.render.render(write_still=True)
            print("[river] rendered", c)


main()
