"""Shared helpers for production ("hero") assets: extended mesh builder and the
procedural production material library (MAT_*).  Works in EEVEE and Cycles."""
import math

import bpy
import numpy as np
from mathutils import Matrix, Vector

from bld_meshes import MeshBuilder


# ============================================================================
# Geometry
# ============================================================================
class HB(MeshBuilder):
    def box_inv(self, x0, x1, y0, y1, z0, z1, mat):
        """Box with inward normals (inner shell of a hollow wall)."""
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(v, [tuple(reversed(x)) for x in f], mat)

    def obox(self, mat, c, U, V, hu, hv, hw):
        """Oriented box centred at c; U, V unit axes (W = U x V)."""
        c, U, V = (np.asarray(a, float) for a in (c, U, V))
        U = U / np.linalg.norm(U)
        V = V - U * (V @ U)
        V = V / np.linalg.norm(V)
        W = np.cross(U, V)
        pts = []
        for sw in (-1, 1):
            for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                pts.append(c + su * hu * U + sv * hv * V + sw * hw * W)
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(pts, f, mat)

    def beam(self, mat, p0, p1, up, w, h):
        """Rectangular member from p0 to p1; `up` sets which way the h side faces."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        a = p1 - p0
        L = np.linalg.norm(a)
        self.obox(mat, (p0 + p1) / 2, a / L, up, L / 2, h / 2, w / 2)

    def rod(self, mat, p0, p1, r, sides=8):
        """Cylinder between two points."""
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        a = p1 - p0
        L = float(np.linalg.norm(a))
        tmp = HB()
        tmp.frustum(0, 0, 0, L, r, r, sides, mat)
        z = Vector((0, 0, 1))
        q = z.rotation_difference(Vector(a / L))
        M = Matrix.Translation(Vector(p0)) @ q.to_matrix().to_4x4()
        self.merge(tmp, M)

    def lathe(self, mat, profile, segs=24, cx=0.0, cy=0.0, cz=0.0):
        """Revolve [(r, z), ...] (bottom to top) around Z.  r=0 first point closes the base."""
        v, f = [], []
        rings = []
        for r, z in profile:
            if r <= 1e-5:
                rings.append([len(v)])
                v.append((cx, cy, cz + z))
            else:
                ring = []
                for i in range(segs):
                    a = 2 * math.pi * i / segs
                    ring.append(len(v))
                    v.append((cx + r * math.cos(a), cy + r * math.sin(a), cz + z))
                rings.append(ring)
        for ra, rb in zip(rings[:-1], rings[1:]):
            if len(ra) == 1:
                for i in range(segs):
                    f.append((ra[0], rb[(i + 1) % segs], rb[i]))
            elif len(rb) == 1:
                for i in range(segs):
                    f.append((ra[i], ra[(i + 1) % segs], rb[0]))
            else:
                for i in range(segs):
                    j = (i + 1) % segs
                    f.append((ra[i], ra[j], rb[j], rb[i]))
        self.add(v, f, mat)

    def merge(self, other, M):
        """Append another builder's geometry transformed by 4x4 matrix M."""
        o = len(self.v)
        for x, y, z in other.v:
            p = M @ Vector((x, y, z))
            self.v.append((p.x, p.y, p.z))
        for fc, mi in zip(other.f, other.mi):
            self.f.append(tuple(i + o for i in fc))
            self.mi.append(self._slot(other.mats[mi]))

    def corrugated(self, mat, origin, A, La, D, Ld, N, course, overlap, period, amp,
                   profile="abs", lip=0.03, step_lift=0.03, dx=0.04, rng=None, jitter=0.012):
        """Courses of roofing laid up a slope.  profile 'abs' = country clay tiles,
        'sin' = corrugated sheet.  Each course's lower edge has a lip so courses step."""
        origin, A, D, N = (np.asarray(a, float) for a in (origin, A, D, N))
        if np.cross(A, D) @ N < 0:            # keep faces pointing up/out
            origin = origin + A * La
            A = -A
        xs = np.arange(0.0, La + 1e-6, dx)
        if xs[-1] < La:
            xs = np.append(xs, La)
        n = len(xs)
        s0 = 0.0
        while s0 < Ld - 1e-3:
            s1 = min(s0 + course + overlap, Ld)
            jit = rng.uniform(-jitter, jitter) if rng else 0.0
            sag = rng.uniform(-0.006, 0.006) if rng else 0.0
            t = (xs + jit) / period
            if profile == "abs":
                h = amp * np.abs(np.cos(np.pi * t))
            else:
                h = amp * 0.5 * (1.0 + np.sin(2 * np.pi * t))
            rows = []
            for s, off in ((s0, step_lift - lip), (s0, step_lift + sag), (s1, 0.0)):
                rows.append(origin + np.outer(xs, A) + s * D + np.outer(h + off, N))
            base = len(self.v)
            for r in rows:
                self.v.extend(map(tuple, r.tolist()))
            sl = self._slot(mat)
            for k in range(2):
                for i in range(n - 1):
                    a = base + k * n + i
                    self.f.append((a, a + 1, a + n + 1, a + n))
                    self.mi.append(sl)
            s0 += course

    def ridge_caps(self, mat, x0, x1, y, z, r=0.14, piece=0.42, rng=None):
        segs = 8
        x = x0
        while x < x1 - 1e-3:
            xe = min(x + piece, x1)
            r1 = r * (1.0 + (rng.uniform(-0.04, 0.04) if rng else 0.0))
            base = len(self.v)
            for xx, rr in ((x, r1), (xe + 0.04, r1 * 1.07)):
                for i in range(segs + 1):
                    a = math.pi * i / segs
                    self.v.append((xx, y + rr * math.cos(a), z + rr * math.sin(a)))
            sl = self._slot(mat)
            for i in range(segs):
                a = base + i
                b = base + segs + 1 + i
                self.f.append((a, a + 1, b + 1, b))
                self.mi.append(sl)
            x = xe


# ============================================================================
# Materials
# ============================================================================
def hex_lin(h, mul=1.0):
    h = h.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        c = c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
        out.append(min(1.0, c * mul))
    return (*out, 1.0)


class NT:
    """Tiny node-tree helper."""

    def __init__(self, mat):
        if mat.node_tree is None:
            try:
                mat.use_nodes = True
            except Exception:
                pass
        self.nt = mat.node_tree
        for n in list(self.nt.nodes):
            self.nt.nodes.remove(n)
        self.x = -1400

    def n(self, typ, **inputs):
        node = self.nt.nodes.new(typ)
        node.location = (self.x, 0)
        self.x += 180
        for k, v in inputs.items():
            s = self.inp(node, k)
            if s is None:
                setattr(node, k, v)
            elif hasattr(v, "bl_idname") or isinstance(v, bpy.types.NodeSocket):
                self.nt.links.new(v, s)
            else:
                s.default_value = v
        return node

    @staticmethod
    def inp(node, name, kind=None):
        for s in node.inputs:
            if s.name == name and s.enabled and (kind is None or s.type == kind):
                return s
        for s in node.inputs:
            if s.name == name and (kind is None or s.type == kind):
                return s
        return None

    @staticmethod
    def out(node, name, kind=None):
        for s in node.outputs:
            if s.name == name and (kind is None or s.type == kind):
                return s
        return node.outputs[0]

    def link(self, a, b):
        self.nt.links.new(a, b)

    def mix(self, fac, a, b):
        m = self.nt.nodes.new("ShaderNodeMix")
        m.location = (self.x, -300)
        self.x += 180
        m.data_type = "RGBA"
        f = self.inp(m, "Factor", "VALUE")
        sa = self.inp(m, "A", "RGBA")
        sb = self.inp(m, "B", "RGBA")
        for sock, val in ((f, fac), (sa, a), (sb, b)):
            if isinstance(val, bpy.types.NodeSocket):
                self.link(val, sock)
            else:
                sock.default_value = val
        return self.out(m, "Result", "RGBA")

    def ramp(self, fac, stops, interp="LINEAR"):
        r = self.nt.nodes.new("ShaderNodeValToRGB")
        r.location = (self.x, 200)
        self.x += 180
        r.color_ramp.interpolation = interp
        els = r.color_ramp.elements
        while len(els) < len(stops):
            els.new(0.5)
        for e, (pos, col) in zip(els, stops):
            e.position = pos
            e.color = col
        self.link(fac, r.inputs["Fac"])
        return r.outputs["Color"]

    def math(self, op, a, b=0.0, c=None):
        m = self.nt.nodes.new("ShaderNodeMath")
        m.location = (self.x, -500)
        self.x += 120
        m.operation = op
        for i, val in enumerate((a, b) if c is None else (a, b, c)):
            if isinstance(val, bpy.types.NodeSocket):
                self.link(val, m.inputs[i])
            else:
                m.inputs[i].default_value = val
        return m.outputs[0]

    def noise(self, vec, scale, detail=4.0, rough=0.55):
        return self.n("ShaderNodeTexNoise", Vector=vec, Scale=scale, Detail=detail, Roughness=rough)

    def finish(self, color, rough, normal=None, metallic=0.0, emission=None, estr=0.0):
        b = self.n("ShaderNodeBsdfPrincipled")
        for name, val in (("Base Color", color), ("Roughness", rough), ("Metallic", metallic)):
            s = self.inp(b, name)
            if isinstance(val, bpy.types.NodeSocket):
                self.link(val, s)
            else:
                s.default_value = val
        if normal is not None:
            self.link(normal, self.inp(b, "Normal"))
        if emission is not None:
            self.inp(b, "Emission Color").default_value = emission
            self.inp(b, "Emission Strength").default_value = estr
        o = self.n("ShaderNodeOutputMaterial")
        self.link(b.outputs[0], o.inputs["Surface"])
        return b

    def bump(self, height, strength, dist=0.01):
        return self.n("ShaderNodeBump", Strength=strength, Distance=dist, Height=height).outputs["Normal"]


def _mat(name, preview_hex):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = hex_lin(preview_hex)
    return m, NT(m)


def mat_plaster(name, base, band=None, band_top=1.3, grime="#6E5A45", rough=0.88):
    m, t = _mat(name, base)
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    z = t.n("ShaderNodeSeparateXYZ", Vector=obj).outputs["Z"]
    var = t.noise(obj, 1.3, 3.0)
    col = t.ramp(var.outputs["Fac"], [(0.3, hex_lin(base, 0.90)), (0.7, hex_lin(base, 1.05))])
    if band:
        bvar = t.ramp(var.outputs["Fac"], [(0.3, hex_lin(band, 0.88)), (0.7, hex_lin(band, 1.06))])
        col = t.mix(t.math("LESS_THAN", z, band_top), col, bvar)
        col = t.mix(t.math("COMPARE", z, band_top + 0.012, 0.012), col, hex_lin("#2A2A2E"))
    gn = t.noise(obj, 4.0, 6.0, 0.6)
    gz = t.n("ShaderNodeMapRange", Value=z, **{"From Min": 0.45, "From Max": 1.35, "To Min": 0.75, "To Max": 0.0})
    g = t.math("MULTIPLY", gz.outputs["Result"], gn.outputs["Fac"])
    col = t.mix(g, col, hex_lin(grime))
    # large soft stains (rain, age)
    st = t.noise(obj, 0.45, 2.0, 0.5)
    sf = t.ramp(st.outputs["Fac"], [(0.5, (0, 0, 0, 1)), (0.75, (0.32, 0.32, 0.32, 1))])
    col = t.mix(t.n("ShaderNodeSeparateColor", Color=sf).outputs[0], col, hex_lin(grime, 1.2))
    # B5: vertical rain streaks (noise stretched along Z), strongest high on the wall under the roof line
    sm = t.n("ShaderNodeMapping", Vector=obj, Scale=(26.0, 26.0, 0.9))
    streak = t.noise(sm.outputs[0], 1.0, 4.0, 0.55)
    sk = t.ramp(streak.outputs["Fac"], [(0.55, (0, 0, 0, 1)), (0.72, (0.38, 0.38, 0.38, 1))])
    col = t.mix(t.n("ShaderNodeSeparateColor", Color=sk).outputs[0], col, hex_lin(grime, 0.85))
    # B5: cement repair patches (blocky voronoi cells, sparse)
    vor = t.n("ShaderNodeTexVoronoi", Vector=obj, Scale=2.8)
    vor.feature = "F1"
    pv = t.n("ShaderNodeSeparateColor", Color=vor.outputs["Color"]).outputs[0]
    patch = t.math("GREATER_THAN", pv, 0.975)
    col = t.mix(t.math("MULTIPLY", patch, 0.35), col, hex_lin("#B7B1A5"))
    # B5: plaster flaked off near the ground showing brick
    flake_n = t.noise(obj, 3.2, 6.0, 0.7)
    low = t.n("ShaderNodeMapRange", Value=z, **{"From Min": 0.35, "From Max": 1.1, "To Min": 1.0, "To Max": 0.0}).outputs["Result"]
    flake = t.math("GREATER_THAN", t.math("MULTIPLY", flake_n.outputs["Fac"], t.math("ADD", low, 0.2)), 0.62)
    col = t.mix(flake, col, hex_lin("#8E4A33"))
    bn = t.noise(obj, 22.0, 8.0, 0.62)
    rgh = t.math("ADD", rough, t.math("MULTIPLY", t.math("SUBTRACT", streak.outputs["Fac"], 0.5), 0.08))
    t.finish(col, rgh, t.bump(t.math("ADD", bn.outputs["Fac"], t.math("MULTIPLY", flake, -0.6)), 0.22, 0.01))
    return m


def mat_tile(name="MAT_Roof_Terracotta_CountryTile"):
    m, t = _mat(name, "#A5523A")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n1 = t.noise(obj, 2.6, 2.0)
    col = t.ramp(n1.outputs["Fac"], [(0.3, hex_lin("#8A3F2C")), (0.5, hex_lin("#A9553A")), (0.72, hex_lin("#BE6A44"))])
    n2 = t.noise(obj, 0.7, 4.0, 0.6)
    dirt = t.ramp(n2.outputs["Fac"], [(0.58, (0, 0, 0, 1)), (0.78, (0.55, 0.55, 0.55, 1))])
    col = t.mix(t.n("ShaderNodeSeparateColor", Color=dirt).outputs[0], col, hex_lin("#4E4235"))
    # B5: per-tile colour shift (voronoi cells ~ tile size), lichen/moss in damp patches, sun-bleached tops
    vt = t.n("ShaderNodeTexVoronoi", Vector=obj, Scale=5.5)
    tv = t.n("ShaderNodeSeparateColor", Color=vt.outputs["Color"]).outputs[0]
    col = t.mix(t.math("MULTIPLY", t.math("SUBTRACT", tv, 0.5), 0.5), col, hex_lin("#6E2E20"))
    mo = t.noise(obj, 1.4, 5.0, 0.65)
    moss = t.ramp(mo.outputs["Fac"], [(0.62, (0, 0, 0, 1)), (0.74, (0.7, 0.7, 0.7, 1))])
    col = t.mix(t.n("ShaderNodeSeparateColor", Color=moss).outputs[0], col, hex_lin("#5E6A3A"))
    up = t.n("ShaderNodeSeparateXYZ", Vector=t.n("ShaderNodeNewGeometry").outputs["Normal"]).outputs["Z"]
    col = t.mix(t.math("MULTIPLY", t.math("MAXIMUM", t.math("SUBTRACT", up, 0.6), 0.0), 0.5), col, hex_lin("#C98B6A"))
    bn = t.noise(obj, 45.0, 6.0, 0.6)
    t.finish(col, 0.72, t.bump(bn.outputs["Fac"], 0.25, 0.006))
    return m


def mat_wood(name="MAT_Wood_Weathered", c1="#5A3D28", c2="#7E5A3B", rough=0.74):
    # Direction-free weathered wood (no UVs yet): soft mottling + fine fibre bump.
    m, t = _mat(name, c2)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n1 = t.noise(obj, 2.2, 3.0, 0.5)
    col = t.ramp(n1.outputs["Fac"], [(0.3, hex_lin(c1)), (0.7, hex_lin(c2))])
    n2 = t.noise(obj, 11.0, 6.0, 0.6)
    col = t.mix(t.math("MULTIPLY", n2.outputs["Fac"], 0.25), col, hex_lin(c1, 0.75))
    # B5: long grain (noise stretched along Z, most posts/planks are vertical) + silver-grey weathering
    gm = t.n("ShaderNodeMapping", Vector=obj, Scale=(38.0, 38.0, 2.2))
    grain = t.noise(gm.outputs[0], 1.0, 6.0, 0.65)
    col = t.mix(t.math("MULTIPLY", t.math("GREATER_THAN", grain.outputs["Fac"], 0.56), 0.45), col, hex_lin(c1, 0.6))
    wz = t.noise(obj, 0.9, 3.0, 0.5)
    col = t.mix(t.math("MULTIPLY", t.math("MAXIMUM", t.math("SUBTRACT", wz.outputs["Fac"], 0.5), 0.0), 0.9), col, hex_lin("#8C8579"))
    fib = t.noise(obj, 60.0, 4.0, 0.6)
    t.finish(col, rough, t.bump(t.math("ADD", fib.outputs["Fac"], t.math("MULTIPLY", grain.outputs["Fac"], 0.8)), 0.16, 0.003))
    return m


def mat_painted(name, paint, wood="#6B4A33", chip=0.66):
    m, t = _mat(name, paint)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n = t.noise(obj, 9.0, 8.0, 0.65)
    mask = t.ramp(n.outputs["Fac"], [(chip, (0, 0, 0, 1)), (chip + 0.02, (1, 1, 1, 1))], "LINEAR")
    fac = t.n("ShaderNodeSeparateColor", Color=mask).outputs[0]
    v = t.noise(obj, 2.0, 2.0)
    pc = t.ramp(v.outputs["Fac"], [(0.3, hex_lin(paint, 0.88)), (0.7, hex_lin(paint, 1.05))])
    col = t.mix(fac, pc, hex_lin(wood))
    rough = t.math("ADD", t.math("MULTIPLY", fac, 0.3), 0.5)
    t.finish(col, rough, t.bump(fac, 0.3, 0.004))
    return m


def mat_stone_blocks(name="MAT_Stone_Plinth_Blocks", c1="#8F867B", c2="#A69B8B", mortar="#5E574F",
                     scale=1.4, bw=0.5, rh=0.25, rough=0.85):
    m, t = _mat(name, c2)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=obj)
    # wall-friendly projection: (x + y, z) so blocks read correctly on every vertical face
    uv = t.n("ShaderNodeCombineXYZ", X=t.math("ADD", sx.outputs["X"], sx.outputs["Y"]), Y=sx.outputs["Z"]).outputs[0]
    br = t.n("ShaderNodeTexBrick", Vector=uv, Color1=hex_lin(c1), Color2=hex_lin(c2), Mortar=hex_lin(mortar),
             Scale=scale, **{"Mortar Size": 0.018, "Mortar Smooth": 0.2, "Brick Width": bw, "Row Height": rh})
    br.offset = 0.5
    n = t.noise(obj, 6.0, 6.0)
    col = t.mix(t.math("MULTIPLY", n.outputs["Fac"], 0.3), br.outputs["Color"], hex_lin(mortar))
    # B5: per-block tone shift, eroded mortar, damp dark + moss at the foot of the wall
    bv = t.n("ShaderNodeTexWhiteNoise", Vector=t.n("ShaderNodeMapping", Vector=uv, Scale=(scale / bw, scale / rh, 1.0)).outputs[0])
    bvv = t.n("ShaderNodeSeparateColor", Color=bv.outputs["Color"]).outputs[0]
    col = t.mix(t.math("MULTIPLY", t.math("SUBTRACT", bvv, 0.5), 0.35), col, hex_lin(c1, 0.7))
    z = sx.outputs["Z"]
    damp = t.n("ShaderNodeMapRange", Value=z, **{"From Min": 0.05, "From Max": 0.6, "To Min": 0.55, "To Max": 0.0}).outputs["Result"]
    dn = t.noise(obj, 3.0, 5.0, 0.6)
    col = t.mix(t.math("MULTIPLY", damp, dn.outputs["Fac"]), col, hex_lin("#4A4E36"))
    h = t.math("ADD", t.math("MULTIPLY", br.outputs["Fac"], -1.2), t.math("MULTIPLY", n.outputs["Fac"], 0.3))
    t.finish(col, rough, t.bump(h, 0.4, 0.012))
    return m


def mat_kota(name="MAT_Floor_Kota_Stone"):
    m, t = _mat(name, "#7F8C86")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    br = t.n("ShaderNodeTexBrick", Vector=obj, Color1=hex_lin("#78867F"), Color2=hex_lin("#8D9A91"),
             Mortar=hex_lin("#55605B"), Scale=1.0, **{"Mortar Size": 0.006, "Brick Width": 0.6, "Row Height": 0.6})
    n = t.noise(obj, 3.0, 5.0)
    col = t.mix(t.math("MULTIPLY", n.outputs["Fac"], 0.25), br.outputs["Color"], hex_lin("#4C5752"))
    t.finish(col, 0.32, t.bump(br.outputs["Fac"], -0.15, 0.004))
    return m


def mat_mud(name="MAT_Mud_Plaster_Ochre", base="#A9825B", rough=0.95):
    m, t = _mat(name, base)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n = t.noise(obj, 1.8, 5.0, 0.6)
    col = t.ramp(n.outputs["Fac"], [(0.3, hex_lin(base, 0.82)), (0.7, hex_lin(base, 1.08))])
    # B5: shrinkage cracks (voronoi edges, sparse) + hand-smoothing strokes
    cv = t.n("ShaderNodeTexVoronoi", Vector=obj, Scale=3.5)
    cv.feature = "DISTANCE_TO_EDGE"
    cn = t.noise(obj, 2.0, 3.0, 0.5)
    crack = t.math("MULTIPLY", t.math("LESS_THAN", cv.outputs["Distance"], 0.02), t.math("GREATER_THAN", cn.outputs["Fac"], 0.55))
    col = t.mix(t.math("MULTIPLY", crack, 0.7), col, hex_lin(base, 0.45))
    wave = t.n("ShaderNodeTexWave", Vector=obj, Scale=1.6, Distortion=9.0, Detail=2.0)
    col = t.mix(t.math("MULTIPLY", wave.outputs["Fac"], 0.12), col, hex_lin(base, 1.15))
    bn = t.noise(obj, 9.0, 10.0, 0.7)
    t.finish(col, rough, t.bump(t.math("ADD", bn.outputs["Fac"], t.math("MULTIPLY", crack, -1.0)), 0.35, 0.02))
    return m


def mat_tin(name="MAT_Metal_Tin_Rusty"):
    m, t = _mat(name, "#8C8F8E")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n = t.noise(obj, 2.5, 8.0, 0.65)
    mask = t.ramp(n.outputs["Fac"], [(0.52, (0, 0, 0, 1)), (0.6, (1, 1, 1, 1))])
    fac = t.n("ShaderNodeSeparateColor", Color=mask).outputs[0]
    col = t.mix(fac, hex_lin("#8E9392"), hex_lin("#7A4A2A"))
    t.finish(col, t.math("ADD", t.math("MULTIPLY", fac, 0.45), 0.42), None,
             t.math("SUBTRACT", 0.75, t.math("MULTIPLY", fac, 0.75)))
    return m


def mat_simple(name, hexc, rough=0.6, metallic=0.0, emission=None, estr=0.0, noise=0.0):
    m, t = _mat(name, hexc)
    col = hex_lin(hexc)
    if noise > 0:
        obj = t.n("ShaderNodeTexCoord").outputs["Object"]
        n = t.noise(obj, 4.0, 4.0)
        col = t.ramp(n.outputs["Fac"], [(0.3, hex_lin(hexc, 1 - noise)), (0.7, hex_lin(hexc, 1 + noise * 0.5))])
    t.finish(col, rough, None, metallic, emission, estr)
    return m


def mat_rope(name="MAT_Rope_Weave"):
    m, t = _mat(name, "#C8B08A")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    mp = t.n("ShaderNodeMapping", Vector=obj, Rotation=(0, 0, math.radians(45)))
    br = t.n("ShaderNodeTexBrick", Vector=mp.outputs[0], Color1=hex_lin("#C9B089"), Color2=hex_lin("#B39872"),
             Mortar=hex_lin("#5A4A36"), Scale=14.0, **{"Mortar Size": 0.05, "Brick Width": 0.5, "Row Height": 0.5})
    t.finish(br.outputs["Color"], 0.9, t.bump(br.outputs["Fac"], -0.4, 0.004))
    return m


def mat_stone_wet(name, c1, c2, mortar, wet_top=-0.9, scale=1.1, bw=0.6, rh=0.32, moss="#4F5A33"):
    """Dressed stone blocks that darken and pick up moss toward the waterline (bridge, ghat)."""
    m, t = _mat(name, c2)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=obj)
    uv = t.n("ShaderNodeCombineXYZ", X=t.math("ADD", sx.outputs["X"], sx.outputs["Y"]), Y=sx.outputs["Z"]).outputs[0]
    br = t.n("ShaderNodeTexBrick", Vector=uv, Color1=hex_lin(c1), Color2=hex_lin(c2), Mortar=hex_lin(mortar),
             Scale=scale, **{"Mortar Size": 0.015, "Mortar Smooth": 0.3, "Brick Width": bw, "Row Height": rh})
    br.offset = 0.5
    n = t.noise(obj, 5.0, 6.0, 0.6)
    col = t.mix(t.math("MULTIPLY", n.outputs["Fac"], 0.35), br.outputs["Color"], hex_lin(mortar))
    big = t.noise(obj, 0.6, 3.0, 0.55)
    col = t.mix(t.math("MULTIPLY", big.outputs["Fac"], 0.3), col, hex_lin("#5A5146"))
    # wet band + moss near the water
    wz = t.n("ShaderNodeMapRange", Value=sx.outputs["Z"], **{"From Min": wet_top, "From Max": wet_top - 0.8,
                                                             "To Min": 0.0, "To Max": 1.0})
    wet = t.math("MULTIPLY", wz.outputs["Result"], t.math("ADD", 0.55, t.math("MULTIPLY", n.outputs["Fac"], 0.6)))
    col = t.mix(t.math("MINIMUM", wet, 1.0), col, hex_lin(moss))
    rough = t.math("SUBTRACT", 0.85, t.math("MULTIPLY", t.math("MINIMUM", wet, 1.0), 0.45))
    h = t.math("ADD", t.math("MULTIPLY", br.outputs["Fac"], -1.0), t.math("MULTIPLY", n.outputs["Fac"], 0.35))
    t.finish(col, rough, t.bump(h, 0.4, 0.012))
    return m


def mat_water(name="MAT_Water_River"):
    """Clear-ish river water: refractive surface with flow ripples + volume absorption for depth colour.
    Needs a closed water body (surface + sides + bottom) for the volume to work."""
    m, t = _mat(name, "#2C5F5A")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    mp = t.n("ShaderNodeMapping", Vector=obj, Scale=(1.0, 0.25, 1.0))
    n1 = t.noise(mp.outputs[0], 1.6, 4.0, 0.55)
    n2 = t.noise(obj, 7.0, 3.0, 0.5)
    h = t.math("ADD", n1.outputs["Fac"], t.math("MULTIPLY", n2.outputs["Fac"], 0.35))
    b = t.n("ShaderNodeBsdfPrincipled")
    t.inp(b, "Base Color").default_value = hex_lin("#3F6E5C")
    t.inp(b, "Roughness").default_value = 0.035
    t.inp(b, "IOR").default_value = 1.333
    tw = t.inp(b, "Transmission Weight") or t.inp(b, "Transmission")
    tw.default_value = 0.82      # a little diffuse body colour so the river reads green-teal from above
    t.link(t.bump(h, 0.22, 0.02), t.inp(b, "Normal"))
    # murky green-teal body: light absorption + a little scattering so depth glows instead of going black
    ab = t.n("ShaderNodeVolumeAbsorption", Color=hex_lin("#5C8A6E"), Density=0.12)
    scat = t.n("ShaderNodeVolumeScatter", Color=hex_lin("#8DB091"), Density=0.32)
    add = t.n("ShaderNodeAddShader")
    t.link(ab.outputs[0], add.inputs[0])
    t.link(scat.outputs[0], add.inputs[1])
    o = t.n("ShaderNodeOutputMaterial")
    t.link(b.outputs[0], o.inputs["Surface"])
    t.link(add.outputs[0], o.inputs["Volume"])
    return m


def mat_riverbank(name="MAT_Terrain_Riverbank"):
    """Height-driven bank: dark riverbed -> wet mud -> damp sand -> dry sand -> grass."""
    m, t = _mat(name, "#8C7556")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    z = t.n("ShaderNodeSeparateXYZ", Vector=obj).outputs["Z"]
    n = t.noise(obj, 0.9, 4.0, 0.6)
    zf = t.n("ShaderNodeMapRange", Value=t.math("ADD", z, t.math("MULTIPLY", t.math("SUBTRACT", n.outputs["Fac"], 0.5), 0.9)),
             **{"From Min": -3.2, "From Max": 0.6, "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
    col = t.ramp(zf, [(0.0, hex_lin("#40392D")), (0.33, hex_lin("#4E3F2F")), (0.42, hex_lin("#7A6247")),
                      (0.6, hex_lin("#A48A64")), (0.8, hex_lin("#8E8B52")), (0.95, hex_lin("#6C8642"))])
    fine = t.noise(obj, 9.0, 8.0, 0.65)
    col = t.mix(t.math("MULTIPLY", fine.outputs["Fac"], 0.3), col, hex_lin("#3A3226"))
    rough = t.ramp(zf, [(0.3, (0.35, 0.35, 0.35, 1)), (0.45, (0.92, 0.92, 0.92, 1))])
    rr = t.n("ShaderNodeSeparateColor", Color=rough).outputs[0]
    t.finish(col, rr, t.bump(fine.outputs["Fac"], 0.45, 0.03))
    return m


def instancer(name, src_obj):
    """GN group: instance src_obj on points using point attributes 'rot' (euler) and 'scl'."""
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, L = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    iop = N.new("GeometryNodeInstanceOnPoints")
    oi = N.new("GeometryNodeObjectInfo")
    oi.inputs["Object"].default_value = src_obj
    oi.inputs["As Instance"].default_value = True
    nr = N.new("GeometryNodeInputNamedAttribute")
    nr.data_type = "FLOAT_VECTOR"
    nr.inputs["Name"].default_value = "rot"
    ns = N.new("GeometryNodeInputNamedAttribute")
    ns.data_type = "FLOAT"
    ns.inputs["Name"].default_value = "scl"
    L.new(gi.outputs[0], iop.inputs["Points"])
    L.new(oi.outputs["Geometry"], iop.inputs["Instance"])
    ro = nr.outputs["Attribute"]
    try:
        e2r = N.new("FunctionNodeEulerToRotation")
        L.new(ro, e2r.inputs[0])
        ro = e2r.outputs[0]
    except Exception:
        pass
    L.new(ro, iop.inputs["Rotation"])
    L.new(ns.outputs["Attribute"], iop.inputs["Scale"])
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
    o.modifiers.new("Instances", "NODES").node_group = ng
    return o


def mat_paving(name, c1, c2, mortar, scale=2.0, bw=0.5, rh=0.25, rough=0.8):
    """Horizontal paving / setts (XY projection)."""
    m, t = _mat(name, c2)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    br = t.n("ShaderNodeTexBrick", Vector=obj, Color1=hex_lin(c1), Color2=hex_lin(c2), Mortar=hex_lin(mortar),
             Scale=scale, **{"Mortar Size": 0.02, "Mortar Smooth": 0.3, "Brick Width": bw, "Row Height": rh})
    n = t.noise(obj, 4.0, 5.0)
    col = t.mix(t.math("MULTIPLY", n.outputs["Fac"], 0.3), br.outputs["Color"], hex_lin(mortar))
    t.finish(col, rough, t.bump(t.math("MULTIPLY", br.outputs["Fac"], -1.0), 0.35, 0.01))
    return m


def mat_leaf(name, cols, transl=0.22, rough=0.48):
    """Leaf: per-instance colour variation (Object Info random) + translucency."""
    m, t = _mat(name, cols[1])
    oi = t.n("ShaderNodeObjectInfo")
    col = t.ramp(oi.outputs["Random"], [(0.0, hex_lin(cols[0])), (0.5, hex_lin(cols[1])), (1.0, hex_lin(cols[2]))])
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.inp(b, "Roughness").default_value = rough
    tr = t.n("ShaderNodeBsdfTranslucent")
    t.link(col, t.inp(tr, "Color"))
    mx = t.n("ShaderNodeMixShader")
    mx.inputs[0].default_value = transl
    t.link(b.outputs[0], mx.inputs[1])
    t.link(tr.outputs[0], mx.inputs[2])
    t.link(mx.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def mat_glass(name="MAT_Glass_Clear"):
    """Thin lantern/window glass: transparent + glossy so lamps inside still cast light (no caustic block)."""
    m, t = _mat(name, "#DDE6E8")
    tr = t.n("ShaderNodeBsdfTransparent", Color=hex_lin("#F4F2E8"))
    gl = t.n("ShaderNodeBsdfGlossy", Roughness=0.05)
    mx = t.n("ShaderNodeMixShader")
    mx.inputs[0].default_value = 0.12
    t.link(tr.outputs[0], mx.inputs[1])
    t.link(gl.outputs[0], mx.inputs[2])
    t.link(mx.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def mat_glow(name="MAT_Lamp_Glow", hexc="#FFD08A", strength=0.0):
    """Lamp bulb / lantern glass glow.  Day = 0, dusk/night ~ 15-30 (set by the render script)."""
    m, t = _mat(name, hexc)
    b = t.n("ShaderNodeBsdfPrincipled")
    t.inp(b, "Base Color").default_value = hex_lin("#FFF6E6")
    t.inp(b, "Roughness").default_value = 0.2
    t.inp(b, "Emission Color").default_value = hex_lin(hexc)
    t.inp(b, "Emission Strength").default_value = strength
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def mat_straw(name="MAT_Thatch_Straw", c1="#9C7F4A", c2="#C8AA6C"):
    """Thatch / hay: fibres streak along local Y (lay roofs so the slope runs along Y)."""
    m, t = _mat(name, c2)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    mp = t.n("ShaderNodeMapping", Vector=obj, Scale=(40.0, 2.5, 40.0))
    n = t.noise(mp.outputs[0], 3.0, 8.0, 0.7)
    col = t.ramp(n.outputs["Fac"], [(0.3, hex_lin(c1, 0.7)), (0.55, hex_lin(c1)), (0.75, hex_lin(c2))])
    big = t.noise(obj, 0.8, 3.0)
    col = t.mix(t.math("MULTIPLY", big.outputs["Fac"], 0.4), col, hex_lin("#5C4E3A"))
    t.finish(col, 0.92, t.bump(n.outputs["Fac"], 0.6, 0.02))
    return m


def mat_ground(name="MAT_Ground_Dirt_Grass"):
    m, t = _mat(name, "#8F7A55")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    big = t.noise(obj, 0.12, 3.0, 0.5)
    mask = t.ramp(big.outputs["Fac"], [(0.45, (0, 0, 0, 1)), (0.62, (1, 1, 1, 1))])
    fac = t.n("ShaderNodeSeparateColor", Color=mask).outputs[0]
    small = t.noise(obj, 3.0, 6.0, 0.6)
    dirt = t.ramp(small.outputs["Fac"], [(0.3, hex_lin("#8A6E4E")), (0.7, hex_lin("#A88B66"))])
    grass = t.ramp(small.outputs["Fac"], [(0.3, hex_lin("#5F7A3A")), (0.7, hex_lin("#86964F"))])
    col = t.mix(fac, dirt, grass)
    bn = t.noise(obj, 14.0, 8.0, 0.7)
    t.finish(col, 0.95, t.bump(bn.outputs["Fac"], 0.4, 0.02))
    return m
