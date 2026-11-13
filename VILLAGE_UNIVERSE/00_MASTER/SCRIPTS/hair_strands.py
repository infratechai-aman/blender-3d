"""Strand hair + braid physics for characters (Blender 5.x hair curves + bundled essentials node assets).

  scalp strands  rooted on a hidden scalp mesh (armature-deformed), combed from a centre parting back to the nape;
                 Hair Dynamics in "Animation" mode keeps the roots glued to the moving scalp; light frizz/noise.
  braid          a bundle of strands from the nape, braided by "Braid Hair Curves" around strand 0 (the guide);
                 Hair Dynamics in "Simulation" mode BEFORE the braid node, so the whole braid swings as one.
"""
import math
import os

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.interpolate import poly_3d_calc

ASSETS = os.path.join(os.path.dirname(bpy.app.binary_path), "%d.%d" % bpy.app.version[:2], "datafiles", "assets", "nodes")


def load_assets():
    need = {"geometry_nodes_dynamics_assets.blend": ["Hair Dynamics"],
            "procedural_hair_node_assets.blend": ["Braid Hair Curves", "Frizz Hair Curves", "Hair Curves Noise",
                                                  "Set Hair Curve Profile", "Smooth Hair Curves"]}
    for f, names in need.items():
        missing = [n for n in names if n not in bpy.data.node_groups]
        if missing:
            with bpy.data.libraries.load(os.path.join(ASSETS, f)) as (src, dst):
                dst.node_groups = [n for n in src.node_groups if n in missing]
    return {n: bpy.data.node_groups[n] for names in need.values() for n in names}


def set_input(mod, name, value):
    """Blender 5.x: modifier inputs live on mod.properties.inputs.<identifier>.value (no more IDProperties)."""
    ng = mod.node_group
    for it in ng.interface.items_tree:
        if it.item_type == "SOCKET" and it.in_out == "INPUT" and it.name == name:
            getattr(mod.properties.inputs, it.identifier).value = value
            return it.identifier
    raise KeyError(name)


def set_menu(mod, name, label):
    """Menu input by item label, e.g. Hair Dynamics Mode: 'Animation' | 'Physics (Experimental)'."""
    set_input(mod, name, label)


def mat_hair_strands(name, melanin=0.95, rough=0.28):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    h = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    try:
        h.parametrization = "MELANIN"
    except Exception:
        pass
    for k, v in (("Melanin", melanin), ("Melanin Redness", 0.45), ("Roughness", rough), ("Radial Roughness", 0.3),
                 ("Coat", 0.12), ("Random Roughness", 0.15), ("Random Color", 0.08)):
        if k in h.inputs:
            h.inputs[k].default_value = v
    info = nt.nodes.new("ShaderNodeHairInfo")
    if "Random Color" in h.inputs and "Random" in info.outputs:
        pass
    nt.links.new(h.outputs[0], out.inputs["Surface"])
    m.diffuse_color = (0.02, 0.015, 0.012, 1)
    return m


def scalp_surface(body, keep_fn, coll, name):
    """Hidden scalp mesh (with weights + UVs) used as the hair attachment surface."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not keep_fn(np.array(v.co[:]))], context="VERTS")
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    for g in body.vertex_groups:
        o.vertex_groups.new(name=g.name)
    o.hide_render = True
    o.visible_camera = False
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    return o


class ScalpUV:
    def __init__(self, scalp):
        me = scalp.data
        self.me = me
        self.verts = [v.co.copy() for v in me.vertices]
        self.polys = [list(p.vertices) for p in me.polygons]
        self.bvh = BVHTree.FromPolygons(self.verts, self.polys)
        uvl = me.uv_layers.active
        self.uv = {}
        for p in me.polygons:
            self.uv[p.index] = [uvl.data[li].uv.copy() for li in p.loop_indices]

    def project(self, p):
        loc, nrm, fi, _ = self.bvh.find_nearest(Vector(p))
        if loc is None:
            return None, None, None
        poly = self.polys[fi]
        w = poly_3d_calc([self.verts[i] for i in poly], loc)
        uv = sum((self.uv[fi][k] * w[k] for k in range(len(poly))), Vector((0.0, 0.0)))
        return np.array(loc[:]), np.array(nrm[:]), (uv.x, uv.y)


def make_curves(name, strands, radii, uvs, scalp, mat, coll):
    n = len(strands)
    npts = len(strands[0])
    cd = bpy.data.hair_curves.new(name)
    cd.add_curves([npts] * n)
    P = np.asarray(strands, np.float32).reshape(-1, 3)
    cd.attributes["position"].data.foreach_set("vector", P.ravel())
    r = cd.attributes.get("radius") or cd.attributes.new("radius", "FLOAT", "POINT")
    r.data.foreach_set("value", np.asarray(radii, np.float32).ravel())
    a = cd.attributes.new("surface_uv_coordinate", "FLOAT2", "CURVE")
    a.data.foreach_set("vector", np.asarray(uvs, np.float32).ravel())
    cd.surface = scalp
    cd.surface_uv_map = scalp.data.uv_layers.active.name
    cd.materials.append(mat)
    o = bpy.data.objects.new(name, cd)
    coll.objects.link(o)
    return o


def build(body, coll, hc, ec, nape, hairline, keep, rng, mat, n_scalp=5500, n_braid=260, braid_len=0.5,
          prefix="GEO_Woman001", style="braid", short_len=0.045, radius=0.00028):
    """style "braid": long hair combed to the nape + physics braid.  style "short": cropped hair, strands of
    ~short_len flowing back/down over the scalp (side parting look), no braid."""
    A = load_assets()
    scalp = scalp_surface(body, lambda p: keep(p) or (np.linalg.norm(p - nape) < 0.05), coll, prefix + "_ScalpSurface")
    SU = ScalpUV(scalp)
    # ---- scalp strands: roots sampled on the scalp faces inside the hairline
    me = scalp.data
    cand = []
    for p in me.polygons:
        c = np.array(p.center[:])
        if keep(c):
            cand.append((p.index, p.area))
    areas = np.array([a for _, a in cand])
    idx = rng.choice(len(cand), n_scalp, p=areas / areas.sum())
    strands, uvs, radii = [], [], []
    d1 = (nape - hc) / np.linalg.norm(nape - hc)
    NP = 16
    for k in idx:
        poly = me.polygons[cand[k][0]]
        vs = [np.array(me.vertices[i].co[:]) for i in poly.vertices]
        w = rng.dirichlet(np.ones(len(vs)))
        root = sum(wi * vi for wi, vi in zip(w, vs))
        loc, nrm, uv = SU.project(root)
        d0 = (loc - hc) / np.linalg.norm(loc - hc)
        side = 1.0 if loc[0] >= 0 else -1.0
        pts = []
        om = math.acos(max(-1.0, min(1.0, float(d0 @ d1))))
        for j in range(NP):
            t = j / (NP - 1)
            if om < 1e-4:
                d = d0
            else:
                d = (math.sin((1 - t) * om) * d0 + math.sin(t * om) * d1) / math.sin(om)
            if style == "short":
                t = t * min(1.0, short_len / max(om * np.linalg.norm(loc - hc), 1e-4))
                if om >= 1e-4:
                    d = (math.sin((1 - t) * om) * d0 + math.sin(t * om) * d1) / math.sin(om)
            d = d + np.array([side * 0.06 * math.sin(math.pi * t) * (1 - t), 0, 0])   # comb away from the parting
            d /= np.linalg.norm(d)
            hit = SU.bvh.ray_cast(Vector(hc + d * 0.4), Vector(-d), 0.4 - 0.035)   # near side only, never through the head
            surf = np.array(hit[0][:]) if hit[0] is not None else hc + d * np.linalg.norm(loc - hc)
            lift = 0.0012 + 0.0045 * math.sin(math.pi * min(t * 1.15, 1.0)) * (0.6 + 0.4 * d[2])
            if style == "short":
                lift = 0.0015 + 0.006 * (j / (NP - 1)) ** 0.7 * (0.5 + 0.5 * max(d[2], 0.0))
            p = surf + d * lift
            if style == "braid" and t > 0.8:              # gather into the braid root
                p = p + (nape - p) * ((t - 0.8) / 0.2) ** 1.5
            pts.append(p)
        pts[0] = loc
        strands.append(pts)
        uvs.append(uv)
        radii.append([radius * (1 - 0.6 * (j / (NP - 1)) ** 2) for j in range(NP)])
    hair = make_curves(prefix + "_HairStrands", strands, radii, uvs, scalp, mat, coll)
    m = hair.modifiers.new("Follow Scalp", "NODES")
    m.node_group = A["Hair Dynamics"]
    set_menu(m, "Mode", "Animation")
    if style == "short":
        m = hair.modifiers.new("Noise", "NODES")
        m.node_group = A["Hair Curves Noise"]
        set_input(m, "Cumulative Offset", False)
        set_input(m, "Distance", 0.0008)
        set_input(m, "Scale", 60.0)
        print("[hair] short style, scalp strands %d" % len(strands))
        return scalp, hair, None
    m = hair.modifiers.new("Noise", "NODES")                 # oiled, combed-back hair: only a whisper of noise
    m.node_group = A["Hair Curves Noise"]
    set_input(m, "Cumulative Offset", False)
    set_input(m, "Distance", 0.00025)
    set_input(m, "Scale", 25.0)
    # ---- braid bundle: strands from a disc at the nape straight down the back
    loc0, nrm0, uv0 = SU.project(nape)
    down = np.array([0.0, 0.18, -1.0])
    down /= np.linalg.norm(down)
    NB = 44
    bstr, buvs, brad = [], [], []
    for k in range(n_braid):
        if k == 0:
            off = np.zeros(3)
        else:
            a, r = rng.uniform(0, 2 * math.pi), 0.016 * math.sqrt(rng.uniform(0, 1))
            off = np.array([r * math.cos(a), 0.4 * r * math.sin(a), r * math.sin(a)])
        root, _, uv = SU.project(nape + off)
        pts = []
        for j in range(NB):
            t = j / (NB - 1)
            p = root + down * braid_len * t + np.array([0, 0.02 * math.sin(t * 2.6), 0]) + off * (1 - 0.6 * t) * (t > 0.02)
            pts.append(p)
        bstr.append(pts)
        buvs.append(uv)
        brad.append([0.0003] * NB)
    braid = make_curves(prefix + "_BraidStrands", bstr, brad, buvs, scalp, mat, coll)
    m = braid.modifiers.new("Braid Physics", "NODES")
    m.node_group = A["Hair Dynamics"]
    set_menu(m, "Mode", "Physics (Experimental)")
    # roots sit inside the scalp patch, so scalp collision would fling the braid: keep it off; moderate stiffness
    for k, v in (("Substeps", 20), ("Bendiness", 0.35), ("Root Bendiness", 0.6), ("Mass", 0.02), ("Linear", 3.0),
                 ("Angular", 3.0), ("Surface Collision", False)):
        set_input(m, k, v)
    m = braid.modifiers.new("Braid", "NODES")
    m.node_group = A["Braid Hair Curves"]
    for k, v in (("Guide Index", 0), ("Radius", 0.022), ("Braid Start", 0.06), ("Frequency", 9.0), ("Thickness", 1.0),
                 ("Thickness Shape", 0.7), ("Shape", 0.5), ("Flare Length", 0.0), ("Flare Opening", 0.0)):
        try:
            set_input(m, k, v)
        except KeyError:
            print("[hair] braid input missing", k)
    print("[hair] scalp strands %d, braid strands %d" % (len(strands), len(bstr)))
    return scalp, hair, braid
