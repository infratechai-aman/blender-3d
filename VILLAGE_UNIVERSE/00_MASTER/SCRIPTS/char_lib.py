"""Shared helpers for character style tests (humans + animals).

Organic forms are sculpted with metaballs (clay-like blending between masses), converted to a mesh and
smoothed.  Sizes passed to the helpers are the REAL surface radii: Blender's metaball surface for
stiffness 2 / threshold 0.6 sits at 0.575 x element radius (measured), so the helpers divide by that.
Coordinates: metres, Z up, character faces -Y.
"""
import math
import os

import bpy
import numpy as np
from mathutils import Quaternion, Vector

import hero_lib as H

K = 0.575


class Clay:
    """One metaball 'family' -> one blended mesh."""

    def __init__(self, name, res=0.006):
        self.name = name
        self.mb = bpy.data.metaballs.new("MB_" + name)
        self.mb.resolution = res
        self.mb.render_resolution = res
        self.mb.threshold = 0.6
        self.obj = bpy.data.objects.new("MB_" + name, self.mb)
        bpy.context.scene.collection.objects.link(self.obj)

    def ball(self, c, r, neg=False, stiff=2.0):
        e = self.mb.elements.new(type="BALL")
        e.co = c
        e.radius = r / K
        e.stiffness = stiff
        e.use_negative = neg
        return e

    def ellipsoid(self, c, rx, ry, rz, rot=None, neg=False, stiff=2.0):
        e = self.mb.elements.new(type="ELLIPSOID")
        R = max(rx, ry, rz)
        e.co = c
        e.radius = R / K
        e.size_x, e.size_y, e.size_z = rx / R, ry / R, rz / R
        if rot is not None:
            e.rotation = rot
        e.stiffness = stiff
        e.use_negative = neg
        return e

    def capsule(self, p0, p1, r0, r1=None, steps=None, stiff=2.0):
        """Tapered limb: chain of balls (smoother taper than metaball capsules)."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        r1 = r0 if r1 is None else r1
        L = float(np.linalg.norm(p1 - p0))
        n = steps or max(2, int(L / (0.45 * min(r0, r1))) + 1)
        for i in range(n):
            t = i / (n - 1)
            self.ball(tuple(p0 + (p1 - p0) * t), r0 + (r1 - r0) * t, stiff=stiff)

    def chain(self, pts, radii, per=None):
        for (a, b), (ra, rb) in zip(zip(pts[:-1], pts[1:]), zip(radii[:-1], radii[1:])):
            self.capsule(a, b, ra, rb, per)

    def to_mesh(self, mat, smooth_iter=6, coll=None):
        bpy.context.view_layer.update()
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        bpy.context.view_layer.objects.active = self.obj
        self.obj.select_set(True)
        bpy.ops.object.convert(target="MESH")
        o = bpy.context.view_layer.objects.active
        o.name = "GEO_" + self.name
        o.data.name = "ME_" + self.name
        o.data.materials.clear()
        o.data.materials.append(mat)
        o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
        if smooth_iter:
            m = o.modifiers.new("Smooth", "CORRECTIVE_SMOOTH")
            m.iterations = smooth_iter
            m.use_only_smooth = True
            m.smooth_type = "LENGTH_WEIGHTED"
            m.rest_source = "ORCO"
            m2 = o.modifiers.new("Smooth2", "SMOOTH")
            m2.factor = 0.5
            m2.iterations = smooth_iter
        if coll is not None:
            for c in list(o.users_collection):
                c.objects.unlink(o)
            coll.objects.link(o)
        return o


def mesh_obj(name, V, F, mat, coll, smooth=True, mats=None, midx=None):
    me = bpy.data.meshes.new("ME_" + name)
    me.from_pydata([tuple(map(float, v)) for v in V], [], [tuple(f) for f in F])
    for m in (mats or [mat]):
        me.materials.append(m)
    if midx is not None:
        me.polygons.foreach_set("material_index", midx)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    return o


def grid_faces(nu, nv, closed_u=False):
    F = []
    for j in range(nv - 1):
        for i in range(nu if closed_u else nu - 1):
            a = j * nu + i
            b = j * nu + (i + 1) % nu
            F.append((a, b, b + nu, a + nu))
    return F


def sweep(centers, sides, half_w, widths_n=8, fold=None):
    """Ribbon surface: centres[k] + side[k]*s for s in [-w, w].  Returns V (n*m,3), F, uv (n*m,2)."""
    V, UV = [], []
    n = len(centers)
    for k in range(n):
        c, sd, w = np.asarray(centers[k]), np.asarray(sides[k]), half_w[k]
        for j in range(widths_n):
            s = -1 + 2 * j / (widths_n - 1)
            p = c + sd * s * w
            if fold is not None:
                p = p + fold(k / (n - 1), s)
            V.append(p)
            UV.append((j / (widths_n - 1), k / (n - 1)))
    F = []
    for k in range(n - 1):
        for j in range(widths_n - 1):
            a = k * widths_n + j
            F.append((a, a + 1, a + widths_n + 1, a + widths_n))
    return np.array(V), F, UV


def set_uv(obj, uv_per_vert):
    me = obj.data
    uvl = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices:
            uvl.data[li].uv = uv_per_vert[me.loops[li].vertex_index]


# ---------------------------------------------------------------- materials
def mat_skin(name, base, sss=(1.0, 0.45, 0.3), rough=0.48):
    m, t = H._mat(name, base)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n = t.noise(obj, 60.0, 4.0, 0.5)
    big = t.noise(obj, 6.0, 3.0, 0.5)
    col = t.ramp(big.outputs["Fac"], [(0.35, H.hex_lin(base, 0.92)), (0.65, H.hex_lin(base, 1.06))])
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.inp(b, "Roughness").default_value = rough
    for nm, val in (("Subsurface Weight", 0.25), ("Subsurface Scale", 0.012)):
        try:
            t.inp(b, nm).default_value = val
        except Exception:
            pass
    try:
        t.inp(b, "Subsurface Radius").default_value = sss
    except Exception:
        pass
    bump = t.bump(n.outputs["Fac"], 0.08, 0.002)
    t.link(bump, t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def mat_principled(name, hexc, rough=0.5, metallic=0.0, coat=0.0, sheen=0.0, noise=0.0, noise_scale=40.0):
    m, t = H._mat(name, hexc)
    b = t.n("ShaderNodeBsdfPrincipled")
    col = H.hex_lin(hexc)
    if noise:
        obj = t.n("ShaderNodeTexCoord").outputs["Object"]
        n = t.noise(obj, noise_scale, 6.0, 0.6)
        col = t.ramp(n.outputs["Fac"], [(0.3, H.hex_lin(hexc, 1 - noise)), (0.7, H.hex_lin(hexc, 1 + noise * 0.5))])
        t.link(col, t.inp(b, "Base Color"))
    else:
        t.inp(b, "Base Color").default_value = col
    t.inp(b, "Roughness").default_value = rough
    t.inp(b, "Metallic").default_value = metallic
    for nm, val in (("Coat Weight", coat), ("Sheen Weight", sheen)):
        try:
            t.inp(b, nm).default_value = val
        except Exception:
            pass
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


# ---------------------------------------------------------------- review stage
def review_stage(cams, out_dir, prefix, samples=96, res=(1200, 1500), only=None, floor_hex="#B8AE9C"):
    """Studio cyclorama + 3-point light, Cycles (CUDA), renders the given cameras."""
    sc = bpy.context.scene
    st = bpy.data.collections.new("REVIEW_STAGE")
    sc.collection.children.link(st)
    floor = mat_principled("MAT_Stage_Cyc", floor_hex, 0.8)
    V, F = [], []
    nx, ny = 2, 24
    for j in range(ny):
        a = j / (ny - 1)
        y = -6 + 10 * min(a / 0.7, 1.0)
        z = 0.0 if a < 0.7 else (a - 0.7) / 0.3 * 6.0
        if 0.6 < a < 0.8:
            r = 1.5
            th = (a - 0.6) / 0.2 * math.pi / 2
            y = 4.0 - r + r * math.sin(th)
            z = r - r * math.cos(th)
        for x in (-8, 8):
            V.append((x, y, z))
    F = [(2 * j, 2 * j + 1, 2 * j + 3, 2 * j + 2) for j in range(ny - 1)]
    mesh_obj("STG_Cyclorama", V, F, floor, st)
    w = bpy.data.worlds.new("WLD_Studio")
    sc.world = w
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (*H.hex_lin("#C9D6E2")[:3], 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    for nm, loc, rot, energy, size, col in (
            ("LGT_Key", (-2.6, -3.0, 3.2), (math.radians(55), 0, math.radians(-40)), 450, 1.6, (1.0, 0.93, 0.84)),
            ("LGT_Fill", (3.0, -2.5, 1.6), (math.radians(70), 0, math.radians(50)), 140, 2.5, (0.85, 0.9, 1.0)),
            ("LGT_Rim", (1.5, 3.0, 3.0), (math.radians(-60), 0, math.radians(160)), 380, 1.0, (1.0, 0.95, 0.9))):
        ld = bpy.data.lights.new(nm, "AREA")
        ld.energy = energy
        ld.size = size
        ld.color = col
        o = bpy.data.objects.new(nm, ld)
        o.location = loc
        o.rotation_euler = rot
        st.objects.link(o)
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "CUDA"
        sc.cycles.device = "GPU"
    except Exception as ex:
        print("[char] GPU setup failed:", ex)
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    os.makedirs(out_dir, exist_ok=True)
    objs = {}
    for name, (pos, tgt, lens, rx, ry) in cams.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        o = bpy.data.objects.new(name, cd)
        o.location = pos
        o.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        st.objects.link(o)
        objs[name] = (o, rx, ry)
    return objs


def render_cams(objs, out_dir, only=None):
    sc = bpy.context.scene
    for name, (o, rx, ry) in objs.items():
        if only and name not in only:
            continue
        sc.camera = o
        sc.render.resolution_x, sc.render.resolution_y = rx, ry
        sc.render.filepath = os.path.join(out_dir, name + ".png")
        bpy.ops.render.render(write_still=True)
        print("[char] rendered", name)


def look_quat(direction):
    """Quaternion rotating +X onto direction (for ellipsoid elements)."""
    return Vector((1, 0, 0)).rotation_difference(Vector(direction).normalized())


def q_axis(axis, ang):
    return Quaternion(axis, ang)
