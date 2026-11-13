"""
FIRST HUMAN CHARACTER v002 - CHR_Human_Woman_001 on an MPFB (MakeHuman) CC0 base mesh.

  blender -b --factory-startup --python hero_human_woman_001_v2.py -- [--render] [--quick] [--only CAM_A,CAM_B]

Requires the MPFB extension (installed 2026-11-13, v2.0.18, extensions.blender.org).
Output: 04_CHARACTERS/HUMANS/CHR_Human_Woman_001.blend (v001 archived)   Reviews: G5_HUMAN_WOMAN_001_v002/

  body      MPFB base mesh, female ~25 y, South-Asian-leaning race mix, light stylisation targets
            (larger eyes, softer nose, fuller lips, rounder head), subdivided, own skin shader with lip mask
  rig       MPFB built-in "mixamo" skeleton + weights (Mixamo bone names) - clothes are weighted to it
  eyes      own eyeballs fitted to MPFB eye helpers; MPFB eyelash helpers kept as lashes; brows projected
  hair      scalp cut from the head (smooth hairline), centre parting, braid with jasmine gajra
  clothing  blouse cut from the body; saree skirt fitted to measured hips/legs with front pleats + border;
            pallu swept from the right hip over the LEFT shoulder (nivi drape), projected onto the body
  jewellery bangles, bindi, nose stud, jhumkas, chappals
Faces -Y.
"""
import datetime
import math
import os
import shutil
import sys

import addon_utils
import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import char_lib as CL  # noqa: E402
import hero_human_woman_001 as W1  # noqa: E402
import hair_strands as HS_  # noqa: E402
import hero_lib as H  # noqa: E402
from geo import catmull_rom  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "04_CHARACTERS", "HUMANS", "CHR_Human_Woman_001.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "G5_HUMAN_WOMAN_001_v002")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
COLL = None
LM = {}            # landmarks (world)

MACRO = dict(gender=0.0, age=0.5, muscle=0.45, weight=0.44, proportions=0.8, height=0.47, cupsize=0.45, firmness=0.6,
             race={"asian": 0.55, "african": 0.3, "caucasian": 0.15})
STYLE_TARGETS = [            # gentle feature-animation stylisation on top of the realistic base
    ("l-eye-scale-incr", 0.45), ("r-eye-scale-incr", 0.45), ("l-eye-height2-incr", 0.25), ("r-eye-height2-incr", 0.25),
    ("nose-scale-horiz-decr", 0.2), ("nose-point-width-decr", 0.25), ("nose-point-up", 0.25), ("nose-volume-decr", 0.2),
    ("nose-nostrils-width-decr", 0.2), ("mouth-lowerlip-volume-incr", 0.35), ("mouth-upperlip-volume-incr", 0.25),
    ("mouth-cupidsbow-incr", 0.4), ("mouth-angles-up", 0.15), ("l-cheek-volume-incr", 0.25), ("r-cheek-volume-incr", 0.25),
    ("head-round", 0.35), ("head-scale-horiz-incr", 0.08), ("chin-width-decr", 0.1), ("neck-scale-horiz-decr", 0.12),
    ("eyebrows-trans-up", 0.1),
]


def mpfb():
    addon_utils.enable("bl_ext.user_default.mpfb", default_set=True)
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    return HumanService, TargetService


def full_mesh(body):
    """Evaluated basemesh WITH helper geometry (mask off) - targets/shape keys applied, weights kept."""
    mods = [m for m in body.modifiers if m.type == "MASK"]
    for m in mods:
        m.show_viewport = False
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    for m in mods:
        m.show_viewport = True
    bpy.context.view_layer.update()
    return me


def vg_points(obj, me, name):
    gi = obj.vertex_groups[name].index
    pts = [obj.matrix_world @ v.co for v in me.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)]
    return np.array([p[:] for p in pts])


def mat_skin_mouth(name, base, lip, mc):
    """Skin + soft lip mask around the mouth landmark (object space == world: basemesh sits at the origin)."""
    m, t = H._mat(name, base)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=obj)
    x = t.math("SUBTRACT", sx.outputs["X"], float(mc[0]))
    y = t.math("SUBTRACT", sx.outputs["Y"], float(mc[1]))
    z = t.math("SUBTRACT", sx.outputs["Z"], float(mc[2]))
    ex = t.math("DIVIDE", x, 0.024)
    ez = t.math("DIVIDE", t.math("SUBTRACT", z, 0.0), 0.0115)
    r2 = t.math("ADD", t.math("MULTIPLY", ex, ex), t.math("MULTIPLY", ez, ez))
    lipm = t.n("ShaderNodeMapRange", Value=r2, **{"From Min": 0.55, "From Max": 1.0, "To Min": 1.0, "To Max": 0.0}).outputs["Result"]
    lipm = t.math("MULTIPLY", lipm, t.math("LESS_THAN", y, 0.012))
    big = t.noise(obj, 6.0, 3.0, 0.5)
    col = t.ramp(big.outputs["Fac"], [(0.35, H.hex_lin(base, 0.94)), (0.65, H.hex_lin(base, 1.05))])
    col = t.mix(lipm, col, H.hex_lin(lip))
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.link(t.n("ShaderNodeMapRange", Value=lipm, **{"To Min": 0.5, "To Max": 0.32}).outputs["Result"], t.inp(b, "Roughness"))
    for nm, val in (("Subsurface Weight", 0.3), ("Subsurface Scale", 0.01)):
        try:
            t.inp(b, nm).default_value = val
        except Exception:
            pass
    try:
        t.inp(b, "Subsurface Radius").default_value = (1.0, 0.45, 0.3)
    except Exception:
        pass
    fine = t.noise(obj, 80.0, 4.0, 0.5)
    t.link(t.bump(fine.outputs["Fac"], 0.05, 0.001), t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def find_lips(S):
    """Walk the centre-line profile below the eyes: nose tip -> subnasal recess -> lips."""
    ez = LM["eye_l"][0][2]
    zs = np.arange(ez - 0.02, ez - 0.13, -0.001)
    ys = np.array([S.front(0.0, z)[0][1] if S.front(0.0, z)[0] is not None else 0.0 for z in zs])
    i_tip = int(np.argmin(ys[:60]))
    seg = ys[i_tip + 5:i_tip + 30]
    i_sub = i_tip + 5 + int(np.argmax(seg))
    seg2 = ys[i_sub:i_sub + 40]
    i_up = i_sub + int(np.argmin(seg2[:18]))
    c = np.array([0.0, ys[i_up], zs[i_up] - 0.007])
    LM["nose_tip"] = np.array([0.0, ys[i_tip], zs[i_tip]])
    print("[char] nose tip z %.3f, subnasal z %.3f, lip centre z %.3f" % (zs[i_tip], zs[i_sub], c[2]))
    return c


def pose_arms(arm, angle_deg=32.0):
    """Relaxed review pose: upper arms rotated down from the MPFB A-pose (also proves the rig deforms the outfit)."""
    from mathutils import Matrix
    bpy.context.view_layer.update()
    for name, sgn in (("mixamorig:LeftArm", 1), ("mixamorig:RightArm", -1)):
        pb = arm.pose.bones.get(name)
        if pb is None:
            print("[char] missing bone", name)
            continue
        head = pb.head.copy()
        R = Matrix.Rotation(math.radians(angle_deg) * sgn, 4, "Y")
        pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ pb.matrix
        bpy.context.view_layer.update()
    for name, sgn in (("mixamorig:LeftForeArm", 1), ("mixamorig:RightForeArm", -1)):
        pb = arm.pose.bones.get(name)
        if pb is None:
            continue
        head = pb.head.copy()
        R = Matrix.Rotation(math.radians(-10) * sgn, 4, "Y") @ Matrix.Rotation(math.radians(8), 4, "X")
        pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ pb.matrix
        bpy.context.view_layer.update()


# ============================================================================
class Surface:
    """BVH of the evaluated body for projecting clothing / brows onto the skin."""

    def __init__(self, obj):
        dg = bpy.context.evaluated_depsgraph_get()
        self.bvh = BVHTree.FromObject(obj, dg)

    def hit(self, origin, direction):
        loc, nrm, _, _ = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized(), 5.0)
        return (np.array(loc[:]), np.array(nrm[:])) if loc is not None else (None, None)

    def front(self, x, z):
        return self.hit((x, -1.0, z), (0, 1, 0))

    def back(self, x, z):
        return self.hit((x, 1.0, z), (0, -1, 0))

    def top(self, x, y):
        return self.hit((x, y, 3.0), (0, 0, -1))

    def side(self, sx, y, z):
        return self.hit((sx * 1.0, y, z), (-sx, 0, 0))


def extract(src, name, keep_fn, mat, offset, relax=10, vol_fn=None):
    """Copy of the evaluated body restricted to keep_fn(co) vertices, pushed out along normals (keeps weights)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep_fn(np.array(v.co[:]))], context="VERTS")
    for _ in range(relax):
        new = {}
        for v in bm.verts:
            if not v.is_boundary:
                continue
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                new[v] = v.co * 0.4 + (nb[0].co + nb[1].co) * 0.3
        for v, co in new.items():
            v.co = co
    bm.normal_update()
    for v in bm.verts:
        o = offset if vol_fn is None else vol_fn(np.array(v.co[:]))
        v.co += v.normal * o
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    me.materials.append(mat)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me)
    COLL.objects.link(o)
    for g in src.vertex_groups:
        if g.name not in o.vertex_groups:
            o.vertex_groups.new(name=g.name)
    return o


def rig_follow(obj, arm, body=None):
    """Weight a generated cloth piece from the body (nearest face) and bind it to the armature."""
    if body is not None:
        for g in body.vertex_groups:
            if g.name not in obj.vertex_groups:
                obj.vertex_groups.new(name=g.name)
        dt = obj.modifiers.new("Weights", "DATA_TRANSFER")
        dt.object = body
        dt.use_vert_data = True
        dt.data_types_verts = {"VGROUP_WEIGHTS"}
        dt.vert_mapping = "POLYINTERP_NEAREST"
        dt.layers_vgroup_select_src = "ALL"
        dt.layers_vgroup_select_dst = "NAME"
        bpy.context.view_layer.objects.active = obj
        with bpy.context.temp_override(object=obj, active_object=obj):
            bpy.ops.object.modifier_apply(modifier=dt.name)
    m = obj.modifiers.new("Armature", "ARMATURE")
    m.object = arm
    obj.modifiers.move(len(obj.modifiers) - 1, 0)
    obj.parent = arm


# ============================================================================
def build_body(M, HS, TS):
    md = dict(MACRO)
    body = HS.create_human(macro_detail_dict=md, feet_on_ground=True)
    for nm, val in STYLE_TARGETS:
        p = TS.target_full_path(nm)
        if p:
            TS.load_target(body, p, weight=val)
        else:
            print("[char] missing target", nm)
    body.name = "GEO_Woman001_Body"
    for c in list(body.users_collection):
        c.objects.unlink(body)
    COLL.objects.link(body)
    full_w = full_mesh(body)                     # landmarks from MPFB helper / joint groups (targets applied)
    for side, s in (("l", 1), ("r", -1)):
        P = vg_points(body, full_w, "helper-%s-eye" % side)
        LM["eye_" + side] = (P.mean(0), float((P.max(0) - P.min(0)).max() / 2))
        LM["lash_" + side] = ["helper-%s-eyelashes-1" % side, "helper-%s-eyelashes-2" % side]
        for j in ("shoulder", "elbow", "hand", "ankle", "foot-1", "upper-leg", "clavicle"):
            LM["%s_%s" % (j, side)] = vg_points(body, full_w, "joint-%s-%s" % (side, j)).mean(0)
    for j in ("mouth", "neck", "head", "head-2", "pelvis", "jaw"):
        LM[j] = vg_points(body, full_w, "joint-" + j).mean(0)
    # body verts only (no helpers) for measuring
    bi = body.vertex_groups["body"].index
    LM["body_co"] = np.array([v.co[:] for v in full_w.vertices if any(g.group == bi for g in v.groups)])
    print("[char] body height %.3f m, eyes at z %.3f, mouth %s" % (LM["body_co"][:, 2].max(), LM["eye_l"][0][2],
                                                                   np.round(LM["mouth"], 3)))
    return body


def build_eyes(M, body):
    for side in ("l", "r"):
        c, r = LM["eye_" + side]
        r *= 0.98
        W1.put_sphere("GEO_Woman001_Eye_%s" % side.upper(), c, (r, r, r), M["sclera"], 32)
        gaze = np.array([-np.sign(c[0]) * 0.03, -1.0, -0.02])
        V, F = W1.sphere_cap(c, r * 1.004, 0.6, front=gaze)
        CL.mesh_obj("GEO_Woman001_Iris_%s" % side.upper(), V, F, M["iris"], COLL)
        V, F = W1.sphere_cap(c, r * 1.007, 0.26, front=gaze)
        CL.mesh_obj("GEO_Woman001_Pupil_%s" % side.upper(), V, F, M["pupil"], COLL)
    # lashes from the MPFB helper geometry
    full = full_mesh(body)
    names = LM["lash_l"] + LM["lash_r"]
    gis = {body.vertex_groups[n].index for n in names}
    bm = bmesh.new()
    bm.from_mesh(full)
    dl = bm.verts.layers.deform.active
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not any(k in gis and w > 0.5 for k, w in v[dl].items())], context="VERTS")
    bm.to_mesh(full)
    bm.free()
    full.materials.clear()
    full.materials.append(M["kajal"])
    o = bpy.data.objects.new("GEO_Woman001_Lashes", full)
    COLL.objects.link(o)
    for g in body.vertex_groups:
        o.vertex_groups.new(name=g.name)
    return o


def build_brows(M, S):
    out = []
    for side in ("l", "r"):
        c, r = LM["eye_" + side]
        s = np.sign(c[0])
        pts, sides = [], []
        n = 16
        for k in range(n):
            t = k / (n - 1)
            x = c[0] + s * (-0.011 + 0.038 * t)
            z = c[2] + r * 1.15 + 0.006 * math.sin(math.pi * min(t * 1.2, 1.0)) - 0.004 * t
            p, nr = S.front(x, z)
            if p is None:
                continue
            pts.append(p + nr * 0.0006)
            sides.append(np.array([0, 0, 1.0]))
        w = [0.0019 * math.sin(math.pi * min(1.0, 0.25 + 0.75 * k / (len(pts) - 1))) ** 0.6 + 0.0004 for k in range(len(pts))]
        V, F, _ = CL.sweep(pts, sides, w, 4)
        o = CL.mesh_obj("GEO_Woman001_Brow_%s" % side.upper(), V, F, M["brow"], COLL)
        o.modifiers.new("Thick", "SOLIDIFY").thickness = 0.0007
        out.append(o)
    return out


def gajra_at(M, nape):
    import random
    rng = random.Random(3)
    hb = H.HB()
    for ring in range(3):
        zc = nape[2] + 0.005 - ring * 0.018
        for k in range(18):
            ang = 2 * math.pi * k / 18 + ring * 0.2
            r = 0.03 - ring * 0.003
            px, py = nape[0] + r * math.cos(ang), nape[1] + 0.012 + r * math.sin(ang) * 0.9
            if py < nape[1] - 0.008:
                continue
            hb.ellipsoid(px, py, zc + rng.uniform(-0.003, 0.003), 0.0055, 0.0055, 0.0075, M["jasmine"], 8, 5)
    me = hb.to_mesh("ME_Woman001_Gajra", recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    g = bpy.data.objects.new("GEO_Woman001_Gajra", me)
    COLL.objects.link(g)
    return g


def build_hair(M, body):
    ec = (LM["eye_l"][0] + LM["eye_r"][0]) / 2
    hc = np.array([0.0, ec[1] + 0.075, ec[2] + 0.012])                     # skull centre estimate
    top = LM["body_co"][:, 2].max()
    hc[2] = (top + LM["mouth"][2]) / 2 + 0.01

    def hairline(p):
        d = p - hc
        n = d / (np.linalg.norm(d) + 1e-9)
        if n[1] < 0:
            hl = ec[2] + 0.06 - 0.075 * W1.ss(0.25, 0.95, abs(n[0])) * (1 - W1.ss(-0.35, 0.2, n[1]))
            if n[1] < -0.45:
                hl = max(hl, ec[2] + 0.035)
        else:
            hl = ec[2] - 0.015 - 0.085 * W1.ss(0.0, 0.9, n[1])     # down to the top of the ear, then the nape
        w = W1.ss(0.62, 0.82, abs(n[0])) * W1.ss(-0.6, -0.38, n[1])   # sideburn in front of the ear
        return hl * (1 - w) + (ec[2] - 0.022) * w

    def is_ear(p):
        return abs(p[0]) > 0.071 and ec[2] - 0.06 < p[2] < ec[2] + 0.025 and p[1] > ec[1] + 0.03

    def keep(p):
        if p[2] < LM["neck"][2] + 0.02 or abs(p[0]) > 0.11:
            return False
        if np.linalg.norm(p[:2] - hc[:2]) > 0.14:
            return False
        return p[2] > hairline(p) and not is_ear(p)

    def keep_cap(p):                       # the dark under-layer stops short of the strands, so its edge never shows
        return keep(p) and p[2] > hairline(p) + 0.004

    def vol(p):
        d = p - hc
        n = d / (np.linalg.norm(d) + 1e-9)
        v = 0.0012 + 0.0015 * W1.ss(0.2, 1.0, n[2])
        return v * W1.ss(-0.004, 0.006, p[2] - hairline(p)) + 0.0003

    o = extract(body, "GEO_Woman001_HairCap", keep_cap, M["hair"], 0.0, relax=14, vol_fn=vol)
    sol = o.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = 0.0015
    sol.offset = -1.0
    o.modifiers.new("Sub", "SUBSURF").levels = 1
    o.data.materials.clear()
    o.data.materials.append(M["hair_base"])
    nape = np.array([0.0, hc[1] + 0.085, ec[2] - 0.05])
    hit, _ = Surface(body).hit(nape + np.array([0, 0.3, 0.02]), (0, -1, 0))
    if hit is not None:
        nape = hit + np.array([0, 0.004, 0])
    scalp, strands, braid_c = HS_.build(body, COLL, hc, ec, nape, hairline, keep, np.random.default_rng(7), M["hair_strand"],
                                      n_scalp=7500)
    LM["scalp"] = scalp
    if "--solid-braid" not in ARGS:
        return o, braid_c, gajra_at(M, nape)
    # (legacy solid braid kept behind a flag)
    W1.HC = hc + np.array([0.0, -0.002, 0.0])
    clay = CL.Clay("Woman001_Braid", 0.003)
    nape = np.array([0.0, hc[1] + 0.085, ec[2] - 0.05])
    n = 22
    for k in range(n):
        t = k / (n - 1)
        p = nape + np.array([0.006 * math.sin(t * 2.0), 0.03 * t + 0.02 * math.sin(t * 2.6), -0.50 * t])
        w = 0.024 * (1 - 0.55 * t) + 0.007
        s = 1 if k % 2 else -1
        clay.ellipsoid(tuple(p + np.array([s * w * 0.35, 0.0, 0.0])), w * 0.62, w * 0.55, w * 1.15, CL.q_axis((0, 1, 0), s * 0.45))
    clay.ball(tuple(nape + np.array([0, -0.012, 0.03])), 0.032)
    braid_o = clay.to_mesh(M["hair"], 2, COLL)
    hb = H.HB()
    import random
    rng = random.Random(3)
    for ring in range(3):
        zc = nape[2] + 0.015 - ring * 0.02
        for k in range(18):
            ang = 2 * math.pi * k / 18 + ring * 0.2
            r = 0.033 - ring * 0.004
            px, py = nape[0] + r * math.cos(ang), nape[1] + 0.006 + r * math.sin(ang) * 0.9
            if py < nape[1] - 0.012:
                continue
            hb.ellipsoid(px, py, zc + rng.uniform(-0.003, 0.003), 0.0055, 0.0055, 0.0075, M["jasmine"], 8, 5)
    tip = nape + np.array([0, 0.03 + 0.02 * math.sin(2.6), -0.52])
    hb.frustum(tip[0], tip[1], tip[2] - 0.05, tip[2] + 0.01, 0.006, 0.012, 10, M["hair"])
    for k in range(6):
        hb.ellipsoid(tip[0] + rng.uniform(-0.006, 0.006), tip[1] + rng.uniform(-0.006, 0.006), tip[2] - 0.05 - k * 0.006,
                     0.006, 0.006, 0.006, M["bangle_red"], 8, 4)
    me = hb.to_mesh("ME_Woman001_Gajra", recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    g = bpy.data.objects.new("GEO_Woman001_Gajra_Paranda", me)
    COLL.objects.link(g)
    return o, braid_o, g


# ============================================================================ clothing
def measure(co, z0, z1, xmax=0.24):
    sel = co[(co[:, 2] > z0) & (co[:, 2] < z1) & (np.abs(co[:, 0]) < xmax)]
    if len(sel) == 0:
        return 0.0, 0.0, 0.0
    return float(np.abs(sel[:, 0]).max()), float(sel[:, 1].min()), float(sel[:, 1].max())


def build_blouse(M, body):
    co = LM["body_co"]
    pel = LM["pelvis"][2]
    zs = np.arange(pel + 0.04, pel + 0.3, 0.01)
    widths = [measure(co, z - 0.005, z + 0.005, 0.2)[0] for z in zs]
    waist = float(zs[int(np.argmin(widths))])
    LM["waist_z"] = waist
    neck = LM["neck"][2]
    sh = {s: LM["shoulder_" + s] for s in ("l", "r")}
    el = {s: LM["elbow_" + s] for s in ("l", "r")}

    def keep(p):
        if p[2] < waist + 0.055 or p[2] > neck + 0.02:
            return False
        if p[1] < -0.0 and p[2] > neck - 0.07 and abs(p[0]) < 0.065 - (neck + 0.02 - p[2]) * 0.25:
            return False                                                  # front neckline
        if p[1] > 0.02 and p[2] > neck - 0.03 and abs(p[0]) < 0.06:
            return False                                                  # back neckline
        if abs(p[0]) > 0.14:                                              # sleeves to mid upper arm
            s = "l" if p[0] > 0 else "r"
            ax = (el[s] - sh[s]) / np.linalg.norm(el[s] - sh[s])
            return float((p - sh[s]) @ ax) < 0.11
        return True

    o = extract(body, "GEO_Woman001_Blouse", keep, M["blouse"], 0.004, relax=14)
    s = o.modifiers.new("Thick", "SOLIDIFY")
    s.thickness = 0.0025
    s.offset = 1.0
    return o


def build_skirt(M):
    co = LM["body_co"]
    top = LM["waist_z"] - 0.025
    nv, nu = 80, 220
    zs = np.linspace(top, 0.045, nv)
    rx, ry0, ry1 = [], [], []
    cur = (0.0, 0.0, 0.0)
    for z in zs:
        mx, y0, y1 = measure(co, z - 0.02, z + 0.02, 0.22 if z > 0.75 else 0.3)
        cur = (max(cur[0], mx), min(cur[1], y0), max(cur[2], y1))           # only ever flares downward
        rx.append(cur[0])
        ry0.append(cur[1])
        ry1.append(cur[2])
    rx, ry0, ry1 = np.array(rx), np.array(ry0), np.array(ry1)
    t = (top - zs) / (top - 0.045)
    ease = 0.005 + 0.022 * W1.ss(0.0, 0.35, t) + 0.035 * t
    cx = 0.0
    cy = (ry0 + ry1) / 2
    ax = rx + ease
    ay = (ry1 - ry0) / 2 + ease * 0.85
    th = np.linspace(-np.pi, np.pi, nu, endpoint=False)
    TH, Z = np.meshgrid(th, zs)
    T = np.meshgrid(th, t)[1]
    AX = np.meshgrid(th, ax)[1]
    AY = np.meshgrid(th, ay)[1]
    CY = np.meshgrid(th, cy)[1]
    amp = 0.0015 + 0.011 * T ** 1.2
    folds = amp * (0.6 * np.sin(7 * TH + 1.7 + 2 * T) + 0.4 * np.sin(13 * TH + 0.4 + 3 * T))
    front = np.exp(-((TH + np.pi / 2) ** 2) / (2 * 0.3 ** 2))
    tri = 2 * np.abs((TH * 24 / np.pi) % 2 - 1) - 1
    pleat = (0.004 + 0.016 * T) * tri * front * W1.ss(0.02, 0.1, T)
    k = 1 + (folds * (1 - 0.6 * front) + pleat) / np.maximum(AX, 0.05)
    X = cx + AX * np.cos(TH) * k
    Y = CY + AY * np.sin(TH) * k
    Z2 = Z + 0.012 * np.sin(TH * 3 + 0.3) * W1.ss(0.8, 1.0, T)
    V = np.stack([X, Y, Z2], -1).reshape(-1, 3)
    o = CL.mesh_obj("GEO_Woman001_SareeSkirt", V, CL.grid_faces(nu, nv, closed_u=True), M["saree_skirt"], COLL)
    uv = np.stack([(TH + np.pi) / (2 * np.pi), (Z - 0.045) / (top - 0.045)], -1).reshape(-1, 2)
    CL.set_uv(o, [tuple(u) for u in uv])
    o.modifiers.new("Thick", "SOLIDIFY").thickness = 0.003
    o.modifiers.new("Sub", "SUBSURF").levels = 1
    hb = H.HB()                                                               # rolled tuck at the top
    for kk in range(64):
        a0, a1 = 2 * math.pi * kk / 64, 2 * math.pi * (kk + 1) / 64
        p0 = np.array([ax[0] * math.cos(a0), cy[0] + ay[0] * math.sin(a0), top])
        p1 = np.array([ax[0] * math.cos(a1), cy[0] + ay[0] * math.sin(a1), top])
        hb.rod(M["saree_skirt"], p0, p1, 0.0065, 8)
    me = hb.to_mesh("ME_Woman001_Tuck", recalc=False)
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    tk = bpy.data.objects.new("GEO_Woman001_SareeTuck", me)
    COLL.objects.link(tk)
    return o, tk


def build_pallu(M, S):
    """Nivi pallu: from the right hip, pleated diagonally across the bust, over the LEFT (+X) shoulder, down the back."""
    shl = LM["shoulder_l"]
    w = LM["waist_z"]
    neck = LM["neck"][2]
    spec = [("front", -0.10, w - 0.01), ("front", -0.06, w + 0.07), ("front", -0.005, w + 0.15),
            ("front", 0.05, w + 0.22), ("front", 0.095, neck - 0.045), ("top", shl[0] - 0.02, shl[1] - 0.045),
            ("top", shl[0] - 0.025, shl[1] + 0.04), ("back", shl[0] - 0.02, neck - 0.07), ("back", shl[0] - 0.05, w + 0.12),
            ("back", shl[0] - 0.07, w - 0.08), ("back", shl[0] - 0.085, w - 0.3), ("back", shl[0] - 0.09, w - 0.47)]
    P, N = [], []
    for kind, a, b in spec:
        p, nr = (S.front(a, b) if kind == "front" else S.back(a, b) if kind == "back" else S.top(a, b))
        if p is None:
            print("[char] pallu miss", kind, a, b)
            continue
        P.append(p + nr * 0.014)
        N.append(nr)
    # back drape hangs free below the shoulder blade: push the last points away from the body
    P = np.array(P)
    P[-4:, 1] += np.array([0.01, 0.025, 0.04, 0.05])
    C = catmull_rom([tuple(p) for p in P], 10)
    n = len(C)
    sides, half = [], []
    for k in range(n):
        t = k / (n - 1)
        tg = C[min(k + 1, n - 1)] - C[max(k - 1, 0)]
        tg /= np.linalg.norm(tg)
        q, nr = (S.hit(C[k] + np.array([0, -0.3, 0]) if C[k][1] < 0 else C[k] + np.array([0, 0.3, 0]),
                       (0, 1, 0) if C[k][1] < 0 else (0, -1, 0)))
        if 0.4 < t < 0.62:
            q, nr = S.top(C[k][0], C[k][1])
        out = nr if nr is not None else np.array([0, -1.0, 0])
        sd = np.cross(tg, out)
        sd /= np.linalg.norm(sd)
        sides.append(sd)
        half.append(0.03 + 0.008 * W1.ss(0.0, 0.3, t) + 0.11 * W1.ss(0.6, 0.85, t) + 0.015 * W1.ss(0.85, 1.0, t))
        LM.setdefault("pallu_out", []).append(out)

    outs = LM["pallu_out"]

    def fold(t, s):
        k = int(round(t * (n - 1)))
        gathered = 1.0 - W1.ss(0.45, 0.7, t)
        amp = 0.006 * gathered + 0.009 * W1.ss(0.64, 1.0, t)
        freq = 5.5 if gathered > 0.5 else 3.0
        return outs[k] * amp * math.sin(s * math.pi * freq + t * 6.0) + np.array([0, 0, -0.03 * W1.ss(0.85, 1.0, t) * (1 - abs(s))])

    V, F, UV = CL.sweep(C, sides, half, 18, fold)
    o = CL.mesh_obj("GEO_Woman001_Pallu", V, F, M["saree_pallu"], COLL)
    CL.set_uv(o, UV)
    sol = o.modifiers.new("Thick", "SOLIDIFY")
    sol.thickness = 0.0025
    sol.offset = 1.0
    o.modifiers.new("Sub", "SUBSURF").levels = 1
    return o


def build_jewellery(M, S):
    objs = []
    W1.COLL = COLL
    for side in ("l", "r"):
        el, wr = LM["elbow_" + side], LM["hand_" + side]
        ax = (wr - el) / np.linalg.norm(wr - el)
        for k in range(7):
            c = wr - ax * (0.035 + k * 0.0075)
            mat = M["gold"] if k in (0, 6) else (M["bangle_red"] if k % 2 else M["bangle_green"])
            W1.torus("GEO_Woman001_Bangle_%s%d" % (side.upper(), k), c, ax, 0.034 + 0.0008 * k, 0.0027, mat)
            objs.append(COLL.objects["GEO_Woman001_Bangle_%s%d" % (side.upper(), k)])
    ec = (LM["eye_l"][0] + LM["eye_r"][0]) / 2
    p, nr = S.front(0.0, ec[2] + 0.024)
    objs.append(W1.put_sphere("GEO_Woman001_Bindi", p + nr * 0.0004, (0.0042, 0.0013, 0.0042), M["bindi"]))
    p, nr = S.front(0.016, LM["mouth"][2] + 0.03)
    if p is not None:
        objs.append(W1.put_sphere("GEO_Woman001_NoseStud", p + nr * 0.0008, (0.0017, 0.0017, 0.0017), M["gold"]))
    for side, sx in (("L", 1), ("R", -1)):
        p, nr = S.side(sx, ec[1] + 0.085, LM["mouth"][2] + 0.012)
        if p is None:
            continue
        top = p + np.array([sx * 0.002, 0, 0])
        objs.append(W1.put_sphere("GEO_Woman001_EarStud_%s" % side, top, (0.003, 0.003, 0.003), M["gold"]))
        hb = H.HB()
        hb.lathe(M["gold"], [(0.0, -0.028), (0.009, -0.027), (0.008, -0.018), (0.004, -0.008), (0.0012, 0.0)], 16,
                 top[0], top[1], top[2] - 0.004)
        for k in range(10):
            a = 2 * math.pi * k / 10
            hb.ellipsoid(top[0] + 0.0095 * math.cos(a), top[1] + 0.0095 * math.sin(a), top[2] - 0.033, 0.0015, 0.0015, 0.0015,
                         M["gold"], 6, 4)
        o2 = bpy.data.objects.new("GEO_Woman001_Jhumka_%s" % side, hb.to_mesh("ME_Jhumka", recalc=False))
        COLL.objects.link(o2)
        objs.append(o2)
    for side in ("l", "r"):                                                    # chappals under the feet
        an, ft = LM["ankle_" + side], LM["foot-1_" + side]
        co = LM["body_co"]
        sel = co[(np.abs(co[:, 0] - an[0]) < 0.06) & (co[:, 2] < 0.05)]
        x0, x1 = sel[:, 0].min() - 0.008, sel[:, 0].max() + 0.008
        y0, y1 = sel[:, 1].min() - 0.012, sel[:, 1].max() + 0.008
        hb = H.HB()
        hb.box(x0, x1, y0, y1, -0.012, 0.0, M["sole"])
        ym = y0 + (y1 - y0) * 0.3
        hb.rod(M["sole"], (x0 + 0.004, ym, 0.0), ((x0 + x1) / 2, ym, 0.022), 0.005, 6)
        hb.rod(M["sole"], ((x0 + x1) / 2, ym, 0.022), (x1 - 0.004, ym, 0.0), 0.005, 6)
        o3 = bpy.data.objects.new("GEO_Woman001_Chappal_%s" % side.upper(), hb.to_mesh("ME_Chappal"))
        COLL.objects.link(o3)
        objs.append(o3)
    return objs


# ============================================================================
def main():
    global COLL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    HS, TS = mpfb()
    sc = bpy.context.scene
    sc.name = "CHR_Human_Woman_001"
    sc.unit_settings.system = "METRIC"
    COLL = bpy.data.collections.new("CHR_Human_Woman_001")
    sc.collection.children.link(COLL)
    W1.COLL = COLL
    M = W1.materials()
    M["hair_strand"] = HS_.mat_hair_strands("MAT_Hair_Strands_Black")
    M["hair_base"] = CL.mat_principled("MAT_Hair_Scalp_Base", "#120D0A", 0.6)
    M["cornea"] = CL.mat_principled("MAT_Eye_Cornea_Wet", "#FFFFFF", 0.02)
    M["cornea"].node_tree.nodes["Principled BSDF"].inputs["Alpha"].default_value = 0.08
    body = build_body(M, HS, TS)
    arm = HS.add_builtin_rig(body, "mixamo")
    S = Surface(body)
    lip_c = find_lips(S)
    M["skin_mouth"] = mat_skin_mouth("MAT_Skin_Woman_001", "#A06A4A", "#8A4640", lip_c)
    body.data.materials.clear()
    body.data.materials.append(M["skin_mouth"])
    arm.name = "RIG_Human_Woman_001"
    for c in list(arm.users_collection):
        c.objects.unlink(arm)
    COLL.objects.link(arm)
    print("[char] rig bones:", len(arm.data.bones), [b.name for b in arm.data.bones][:6])
    lashes = build_eyes(M, body)
    brows = build_brows(M, S)
    hair, braid, gajra = build_hair(M, body)
    blouse = build_blouse(M, body)
    skirt, tuck = build_skirt(M)
    pallu = build_pallu(M, S)
    jew = build_jewellery(M, S)
    sub = body.modifiers.new("Sub", "SUBSURF")
    sub.levels = 1
    sub.render_levels = 1
    # bind everything to the rig
    for o in (lashes, hair, blouse, LM["scalp"]):
        rig_follow(o, arm)
    for o in [gajra, skirt, tuck, pallu] + brows + jew + [x for x in COLL.objects if x.name.startswith(("GEO_Woman001_Eye_",
              "GEO_Woman001_Iris", "GEO_Woman001_Pupil", "GEO_Woman001_Cornea"))]:
        rig_follow(o, arm, body)
    for o in list(sc.collection.objects):
        if o.type == "META":
            bpy.data.objects.remove(o, do_unlink=True)
    if "--tpose" not in ARGS:
        pose_arms(arm)
    quick = "--quick" in ARGS
    top = LM["body_co"][:, 2].max()
    ec = LM["eye_l"][0]
    cams = {
        "CAM_Front":        ((0.0, -3.6, top * 0.55), (0.0, 0.0, top * 0.52), 50, 1200, 1500),
        "CAM_Side_L":       ((3.6, 0.0, top * 0.55), (0.0, 0.0, top * 0.52), 50, 1200, 1500),
        "CAM_Back":         ((0.0, 3.6, top * 0.55), (0.0, 0.0, top * 0.52), 50, 1200, 1500),
        "CAM_ThreeQuarter": ((2.2, -2.7, top * 0.66), (0.0, 0.0, top * 0.53), 50, 1200, 1500),
        "CAM_Face":         ((0.0, -0.78, ec[2] + 0.01), (0.0, 0.0, ec[2] - 0.02), 85, 1200, 1200),
        "CAM_Face_34":      ((0.5, -0.62, ec[2] + 0.03), (0.0, 0.0, ec[2] - 0.025), 85, 1200, 1200),
        "CAM_Hands_Cloth":  ((0.6, -0.75, top * 0.62), (0.18, 0.0, top * 0.58), 60, 1400, 1050),
    }
    if quick:
        cams = {k: (p, t, l, rx * 2 // 3, ry * 2 // 3) for k, (p, t, l, rx, ry) in cams.items()}
    cams["CAM_Braid_Back34"] = ((-1.1, 1.6, top * 0.82), (0.0, 0.05, top * 0.78), 50, 1000, 1250)
    cams["CAM_Hair_Close"] = ((0.45, -0.55, ec[2] + 0.09), (0.0, 0.02, ec[2] + 0.02), 70, 1100, 1100)
    objs = CL.review_stage(cams, OUT_REVIEW, "Woman001", samples=48 if quick else 128)
    try:
        sc.cycles_curves.shape = "THICK"
        sc.cycles_curves.subdivisions = 2
    except Exception:
        pass
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
    if "--anim" in ARGS:
        anim_test(arm, objs)


def anim_test(arm, objs):
    """Head/torso turn so the braid physics can be judged: bake the sims, render frames from behind."""
    from mathutils import Matrix
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 1, 48
    keys = {1: 0.0, 14: 28.0, 26: -22.0, 38: 8.0, 48: 0.0}
    for bname, share in (("mixamorig:Spine", 0.35), ("mixamorig:Spine1", 0.35), ("mixamorig:Neck", 0.3)):
        pb = arm.pose.bones.get(bname)
        if pb is None:
            continue
        pb.rotation_mode = "QUATERNION"
        for f, deg in keys.items():
            sc.frame_set(f)
            pb.rotation_quaternion = (1, 0, 0, 0)
            bpy.context.view_layer.update()
            head = pb.head.copy()
            R = Matrix.Rotation(math.radians(deg * share), 4, "Z")
            pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ pb.matrix
            bpy.context.view_layer.update()
            pb.keyframe_insert("rotation_quaternion", frame=f)
    sc.frame_set(1)
    try:
        bpy.ops.object.simulation_nodes_cache_bake(selected=False)
        print("[char] simulation baked")
    except Exception as ex:
        print("[char] bake failed:", ex)
    out = os.path.join(OUT_REVIEW, "braid_anim")
    os.makedirs(out, exist_ok=True)
    o, rx, ry = objs["CAM_Braid_Back34"]
    sc.camera = o
    sc.render.resolution_x, sc.render.resolution_y = rx * 2 // 3, ry * 2 // 3
    sc.cycles.samples = 32
    for f in (1, 10, 16, 22, 28, 36):
        sc.frame_set(f)
        sc.render.filepath = os.path.join(out, "frame_%03d.png" % f)
        bpy.ops.render.render(write_still=True)
        print("[char] anim frame", f)
    bpy.ops.wm.save_mainfile()


if __name__ == "__main__":
    main()
