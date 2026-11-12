"""Blockout mesh builders: one function per building family.

All builders work in LOCAL coordinates: footprint centred on the origin, width along X,
depth along Y, FRONT DOOR ON THE -Y SIDE, z = 0 at the highest terrain point under the
footprint.  Plinths extend 1.2 m below zero so buildings never float on sloped ground.
"""
import math
import random

import bmesh
import bpy


class MeshBuilder:
    def __init__(self):
        self.v, self.f, self.mi = [], [], []
        self.mats = []

    def _slot(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def add(self, verts, faces, mat):
        o = len(self.v)
        s = self._slot(mat)
        self.v.extend((float(a), float(b), float(c)) for a, b, c in verts)
        for fc in faces:
            self.f.append(tuple(i + o for i in fc))
            self.mi.append(s)

    # --- primitives -----------------------------------------------------
    def box(self, x0, x1, y0, y1, z0, z1, mat):
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(v, f, mat)

    def gable(self, x0, x1, y0, y1, z0, rise, mat):
        """Gable roof, ridge runs along X (parallel to the street)."""
        ym = (y0 + y1) / 2.0
        z1 = z0 + rise
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, ym, z1), (x1, ym, z1)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (0, 4, 3), (1, 2, 5), (0, 3, 2, 1)]
        self.add(v, f, mat)

    def hip(self, x0, x1, y0, y1, z0, rise, mat):
        """Hip roof (thatch / tiled cottage)."""
        ym = (y0 + y1) / 2.0
        inset = min(x1 - x0, y1 - y0) / 2.0
        xa, xb = x0 + inset, x1 - inset
        if xb < xa:
            xa = xb = (x0 + x1) / 2.0
        z1 = z0 + rise
        v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (xa, ym, z1), (xb, ym, z1)]
        f = [(0, 1, 5, 4), (2, 3, 4, 5), (3, 0, 4), (1, 2, 5), (0, 3, 2, 1)]
        self.add(v, f, mat)

    def slope_slab(self, x0, x1, y0, y1, z_front, z_back, thick, mat):
        """Thin sloping slab: y0 edge at z_front, y1 edge at z_back."""
        v = [(x0, y0, z_front), (x1, y0, z_front), (x1, y1, z_back), (x0, y1, z_back),
             (x0, y0, z_front + thick), (x1, y0, z_front + thick), (x1, y1, z_back + thick), (x0, y1, z_back + thick)]
        f = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
        self.add(v, f, mat)

    def frustum(self, cx, cy, z0, z1, r0, r1, sides, mat, rot=0.0):
        v, f = [], []
        for i in range(sides):
            a = rot + 2 * math.pi * i / sides
            v.append((cx + r0 * math.cos(a), cy + r0 * math.sin(a), z0))
        if r1 <= 1e-4:
            v.append((cx, cy, z1))
            for i in range(sides):
                f.append((i, (i + 1) % sides, sides))
        else:
            for i in range(sides):
                a = rot + 2 * math.pi * i / sides
                v.append((cx + r1 * math.cos(a), cy + r1 * math.sin(a), z1))
            for i in range(sides):
                j = (i + 1) % sides
                f.append((i, j, sides + j, sides + i))
            f.append(tuple(range(sides, 2 * sides)))
        f.append(tuple(range(sides - 1, -1, -1)))
        self.add(v, f, mat)

    def ellipsoid(self, cx, cy, cz, rx, ry, rz, mat, seg=14, rings=8):
        v = [(cx, cy, cz - rz)]
        for r in range(1, rings):
            phi = math.pi * r / rings - math.pi / 2
            for s in range(seg):
                th = 2 * math.pi * s / seg
                v.append((cx + rx * math.cos(phi) * math.cos(th), cy + ry * math.cos(phi) * math.sin(th),
                          cz + rz * math.sin(phi)))
        v.append((cx, cy, cz + rz))
        top = len(v) - 1
        f = []
        for s in range(seg):
            f.append((0, 1 + (s + 1) % seg, 1 + s))
        for r in range(rings - 2):
            b = 1 + r * seg
            for s in range(seg):
                s2 = (s + 1) % seg
                f.append((b + s, b + s2, b + seg + s2, b + seg + s))
        b = 1 + (rings - 2) * seg
        for s in range(seg):
            f.append((b + s, b + (s + 1) % seg, top))
        self.add(v, f, mat)

    def ring_wall(self, w, d, t, z0, z1, mat, gate=0.0):
        """Rectangular compound wall, optional gate gap centred on the -Y side."""
        hw, hd = w / 2.0, d / 2.0
        self.box(-hw, hw, hd - t, hd, z0, z1, mat)
        self.box(-hw, -hw + t, -hd, hd, z0, z1, mat)
        self.box(hw - t, hw, -hd, hd, z0, z1, mat)
        if gate > 0:
            self.box(-hw, -gate / 2.0, -hd, -hd + t, z0, z1, mat)
            self.box(gate / 2.0, hw, -hd, -hd + t, z0, z1, mat)
        else:
            self.box(-hw, hw, -hd, -hd + t, z0, z1, mat)

    def parapet(self, x0, x1, y0, y1, z0, h, t, mat):
        self.box(x0, x1, y0, y0 + t, z0, z0 + h, mat)
        self.box(x0, x1, y1 - t, y1, z0, z0 + h, mat)
        self.box(x0, x0 + t, y0, y1, z0, z0 + h, mat)
        self.box(x1 - t, x1, y0, y1, z0, z0 + h, mat)

    # --- output ---------------------------------------------------------
    def to_mesh(self, name, recalc=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        for m in self.mats:
            me.materials.append(m)
        me.polygons.foreach_set("material_index", self.mi)
        if recalc:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        me.update()
        return me


# ----------------------------------------------------------------------------
# Building families.  M is a dict of materials by palette key.
# ----------------------------------------------------------------------------
PLINTH_BASE = -1.2


def _door(mb, M, x, yface, ph, w=1.1, h=2.1):
    mb.box(x - w / 2, x + w / 2, yface - 0.08, yface + 0.02, ph, ph + h, M["wood_dark"])


def _window(mb, M, x, yface, z, w=0.9, h=1.0):
    mb.box(x - w / 2, x + w / 2, yface - 0.06, yface + 0.02, z, z + h, M["wood_dark"])


def house_small(mb, M, p, rng):
    w, d = p["w"], p["d"]
    ph, wh = 0.4, rng.uniform(2.5, 2.8)
    wall = M[p["wall"]]
    mb.box(-w / 2 - 0.2, w / 2 + 0.2, -d / 2 - 0.2, d / 2 + 0.2, PLINTH_BASE, ph, M["plinth_stone"])
    mb.box(-w / 2, w / 2, -d / 2, d / 2, ph, ph + wh, wall)
    roof = M["roof_thatch"] if rng.random() < 0.65 else M["roof_terracotta"]
    mb.hip(-w / 2 - 0.6, w / 2 + 0.6, -d / 2 - 0.6, d / 2 + 0.6, ph + wh, rng.uniform(1.8, 2.3), roof)
    _door(mb, M, rng.uniform(-0.8, 0.8), -d / 2, ph, 0.95, 1.9)
    _window(mb, M, w / 2 - 1.2 if rng.random() < 0.5 else -w / 2 + 1.2, -d / 2, ph + 1.0, 0.6, 0.6)
    # small front yard boundary (low mud wall) on one side
    if rng.random() < 0.6:
        s = rng.choice((-1, 1))
        mb.box(s * w / 2 - 0.15, s * w / 2 + 0.15, -d / 2 - 3.0, -d / 2, 0.0, 0.9, wall)


def house_common(mb, M, p, rng):
    w, d = p["w"], p["d"]
    ph, wh, vd = 0.5, rng.uniform(3.0, 3.3), 2.3
    wall = M[p["wall"]]
    yb = -d / 2 + vd                       # front face of the main body
    mb.box(-w / 2 - 0.2, w / 2 + 0.2, -d / 2 - 0.2, d / 2 + 0.2, PLINTH_BASE, ph, M["plinth_stone"])
    mb.box(-w / 2, w / 2, yb, d / 2, ph, ph + wh, wall)
    mb.gable(-w / 2 - 0.5, w / 2 + 0.5, yb - 0.5, d / 2 + 0.5, ph + wh, rng.uniform(1.6, 2.0), M["roof_terracotta"])
    # veranda: lean-to roof on posts
    mb.slope_slab(-w / 2, w / 2, -d / 2 - 0.4, yb, ph + 2.45, ph + wh - 0.05, 0.12, M["roof_terracotta"])
    n = 4 if w > 9 else 3
    for i in range(n):
        x = -w / 2 + 0.35 + i * (w - 0.7) / (n - 1)
        mb.box(x - 0.12, x + 0.12, -d / 2 + 0.05, -d / 2 + 0.29, ph, ph + 2.45, M["wood_dark"])
    _door(mb, M, rng.uniform(-1.0, 1.0), yb, ph)
    _window(mb, M, -w / 2 + 1.6, yb, ph + 0.9)
    _window(mb, M, w / 2 - 1.6, yb, ph + 0.9)


def house_middle(mb, M, p, rng):
    """Courtyard house: two-storey front block, single-storey side/back wings."""
    w, d = p["w"], p["d"]
    ph, t = 0.6, 4.2
    wall = M[p["wall"]]
    h1 = 3.3
    mb.box(-w / 2 - 0.2, w / 2 + 0.2, -d / 2 - 0.2, d / 2 + 0.2, PLINTH_BASE, ph, M["plinth_stone"])
    # front block (2 storeys, flat roof + parapet)
    mb.box(-w / 2, w / 2, -d / 2, -d / 2 + t, ph, ph + 2 * h1, wall)
    mb.parapet(-w / 2, w / 2, -d / 2, -d / 2 + t, ph + 2 * h1, 0.8, 0.2, wall)
    # back + side wings (1 storey, lean-to tile roofs draining into the court)
    mb.box(-w / 2, w / 2, d / 2 - t, d / 2, ph, ph + h1, wall)
    mb.slope_slab(-w / 2, w / 2, d / 2 - t - 0.6, d / 2 + 0.4, ph + h1, ph + h1 + 1.2, 0.12, M["roof_terracotta"])
    for s in (-1, 1):
        x0, x1 = (-w / 2, -w / 2 + t - 0.6) if s < 0 else (w / 2 - t + 0.6, w / 2)
        mb.box(x0, x1, -d / 2 + t, d / 2 - t, ph, ph + h1, wall)
        mb.box(x0 - 0.3, x1 + 0.3, -d / 2 + t, d / 2 - t, ph + h1, ph + h1 + 0.15, M["roof_terracotta"])
    # courtyard floor
    mb.box(-w / 2 + t - 0.6, w / 2 - t + 0.6, -d / 2 + t, d / 2 - t, ph - 0.05, ph + 0.02, M["chowk_stone"])
    # balcony + door + windows
    mb.box(-2.2, 2.2, -d / 2 - 1.2, -d / 2, ph + h1 - 0.15, ph + h1 + 0.05, M["roof_concrete"])
    mb.box(-2.2, 2.2, -d / 2 - 1.2, -d / 2 - 1.05, ph + h1, ph + h1 + 1.0, M["wood_dark"])
    _door(mb, M, 0.0, -d / 2, ph, 1.6, 2.4)
    for x in (-w / 2 + 2.0, w / 2 - 2.0):
        _window(mb, M, x, -d / 2, ph + 0.9)
        _window(mb, M, x, -d / 2, ph + h1 + 0.9)


def house_rich(mb, M, p, rng):
    """Haveli: two-storey ring around a courtyard, parapet, jharokhas, corner chhatris."""
    w, d = p["w"], p["d"]
    ph, t, h = 0.9, 5.0, 7.4
    wall = M[p["wall"]]
    mb.box(-w / 2 - 0.3, w / 2 + 0.3, -d / 2 - 0.3, d / 2 + 0.3, PLINTH_BASE, ph, M["plinth_stone"])
    mb.box(-w / 2, w / 2, -d / 2, -d / 2 + t, ph, ph + h, wall)
    mb.box(-w / 2, w / 2, d / 2 - t, d / 2, ph, ph + h, wall)
    mb.box(-w / 2, -w / 2 + t, -d / 2 + t, d / 2 - t, ph, ph + h, wall)
    mb.box(w / 2 - t, w / 2, -d / 2 + t, d / 2 - t, ph, ph + h, wall)
    mb.box(-w / 2 + t, w / 2 - t, -d / 2 + t, d / 2 - t, ph - 0.05, ph + 0.02, M["chowk_stone"])
    mb.parapet(-w / 2, w / 2, -d / 2, d / 2, ph + h, 1.0, 0.3, wall)
    # band between storeys
    mb.box(-w / 2 - 0.15, w / 2 + 0.15, -d / 2 - 0.15, -d / 2 + 0.1, ph + 3.6, ph + 3.85, M["plinth_stone"])
    # grand entrance
    mb.box(-1.6, 1.6, -d / 2 - 0.6, -d / 2 + 0.02, ph, ph + 3.4, M["wood_dark"])
    mb.box(-2.4, 2.4, -d / 2 - 0.9, -d / 2, ph + 3.4, ph + 3.9, M["plinth_stone"])
    # jharokhas (projecting balconies)
    for x in (-w / 2 + 4.5, w / 2 - 4.5):
        mb.box(x - 1.3, x + 1.3, -d / 2 - 1.0, -d / 2, ph + 4.3, ph + 6.3, wall)
        mb.frustum(x, -d / 2 - 0.5, ph + 6.3, ph + 7.3, 1.2, 0.0, 4, M["roof_terracotta"], rot=math.pi / 4)
        _window(mb, M, x, -d / 2 - 1.0, ph + 4.8, 1.4, 1.1)
        _window(mb, M, x, -d / 2, ph + 1.0, 1.2, 1.4)
    # chhatris on the front corners
    for x in (-w / 2 + 1.2, w / 2 - 1.2):
        y = -d / 2 + 1.2
        mb.box(x - 0.9, x + 0.9, y - 0.9, y + 0.9, ph + h, ph + h + 0.2, M["plinth_stone"])
        for dx in (-0.7, 0.7):
            for dy in (-0.7, 0.7):
                mb.box(x + dx - 0.1, x + dx + 0.1, y + dy - 0.1, y + dy + 0.1, ph + h + 0.2, ph + h + 2.0, wall)
        mb.frustum(x, y, ph + h + 2.0, ph + h + 3.3, 1.1, 0.0, 8, wall)


def shop(mb, M, p, rng, storeys=1):
    w, d = p["w"], p["d"]
    ph, h1 = 0.45, 3.0
    wall = M[p["wall"]]
    H = h1 * storeys
    mb.box(-w / 2 - 0.1, w / 2 + 0.1, -d / 2 - 0.1, d / 2 + 0.1, PLINTH_BASE, ph, M["plinth_stone"])
    mb.box(-w / 2, w / 2, -d / 2, d / 2, ph, ph + H, wall)
    mb.parapet(-w / 2, w / 2, -d / 2, d / 2, ph + H, 0.7, 0.18, wall)
    # shop opening / rolling shutter
    mb.box(-w / 2 + 0.4, w / 2 - 0.4, -d / 2 - 0.05, -d / 2 + 0.02, ph, ph + 2.5, M["shutter_metal"])
    aw = M[rng.choice(["awning_red", "awning_blue", "awning_green", "roof_tin"])]
    mb.slope_slab(-w / 2 - 0.05, w / 2 + 0.05, -d / 2 - 1.7, -d / 2, ph + 2.55, ph + 2.95, 0.06, aw)
    if storeys > 1:
        mb.box(-w / 2, w / 2, -d / 2 - 1.0, -d / 2, ph + h1 + 0.05, ph + h1 + 0.25, M["roof_concrete"])
        mb.box(-w / 2, w / 2, -d / 2 - 1.0, -d / 2 - 0.9, ph + h1 + 0.25, ph + h1 + 1.15, wall)
        _window(mb, M, 0.0, -d / 2, ph + h1 + 0.8, 1.6, 1.6)
    # signboard
    mb.box(-w / 2 + 0.3, w / 2 - 0.3, -d / 2 - 0.12, -d / 2 - 0.02, ph + 3.0 if storeys == 1 else ph + 2.95,
           ph + 3.55 if storeys == 1 else ph + 3.0, M["awning_red"] if rng.random() < 0.5 else M["awning_blue"])


def cattle_shed(mb, M, p, rng):
    w, d = p["w"], p["d"]
    mb.box(-w / 2 - 0.1, w / 2 + 0.1, -d / 2 - 0.1, d / 2 + 0.1, PLINTH_BASE, 0.2, M["road_dirt"])
    mb.box(-w / 2, w / 2, d / 2 - 0.3, d / 2, 0.2, 1.8, M[p["wall"]])
    for x in (-w / 2 + 0.2, 0.0, w / 2 - 0.2):
        mb.box(x - 0.12, x + 0.12, -d / 2 + 0.2, -d / 2 + 0.44, 0.2, 2.3, M["wood_dark"])
    mb.slope_slab(-w / 2 - 0.3, w / 2 + 0.3, -d / 2 - 0.4, d / 2 + 0.3, 2.3, 2.9, 0.08,
                  M["roof_thatch"] if rng.random() < 0.5 else M["roof_tin"])
    # hay stack beside the shed
    mb.frustum(w / 2 + 2.0, 0.0, 0.0, 2.6, 1.6, 0.0, 10, M["roof_thatch"])


def grain_store(mb, M, p, rng):
    w, d = p["w"], p["d"]
    mb.box(-w / 2 - 0.2, w / 2 + 0.2, -d / 2 - 0.2, d / 2 + 0.2, PLINTH_BASE, 0.8, M["plinth_stone"])
    mb.box(-w / 2, w / 2, -d / 2, d / 2, 0.8, 3.6, M[p["wall"]])
    mb.gable(-w / 2 - 0.4, w / 2 + 0.4, -d / 2 - 0.4, d / 2 + 0.4, 3.6, 1.6, M["roof_tin"])
    _door(mb, M, 0.0, -d / 2, 0.8, 1.8, 2.3)


def temple(mb, M, p, rng):
    """Compound 24 x 24 m; sanctum + shikhara at the back, mandapa in front, gate on -Y."""
    w, d = p["w"], p["d"]
    W = M["temple_white"]
    mb.box(-w / 2, w / 2, -d / 2, d / 2, PLINTH_BASE, 0.15, M["chowk_stone"])
    mb.ring_wall(w, d, 0.5, 0.15, 1.6, W, gate=4.0)
    mb.box(-2.6, -2.0, -d / 2 - 0.3, -d / 2 + 0.6, 0.15, 3.6, W)       # gate pillars
    mb.box(2.0, 2.6, -d / 2 - 0.3, -d / 2 + 0.6, 0.15, 3.6, W)
    mb.box(-2.8, 2.8, -d / 2 - 0.4, -d / 2 + 0.7, 3.6, 4.2, M["saffron"])
    ph = 1.5
    mb.box(-5.5, 5.5, -6.0, 9.0, 0.15, ph, M["plinth_stone"])          # jagati (platform)
    for i in range(4):                                                  # front steps
        mb.box(-2.0, 2.0, -6.0 - 0.45 * (i + 1), -6.0 - 0.45 * i, 0.15, ph - 0.33 * (i + 1) + 0.33, M["plinth_stone"])
    mb.box(-3.0, 3.0, 2.5, 8.5, ph, ph + 5.0, W)                         # garbhagriha
    z = ph + 5.0
    r = 4.0
    for k in range(6):                                                  # stepped shikhara
        r2 = r * 0.82
        mb.frustum(0.0, 5.5, z, z + 2.1, r, r2, 8, W, rot=math.pi / 8)
        z += 2.1
        r = r2
    mb.frustum(0.0, 5.5, z, z + 0.6, r + 0.4, r + 0.4, 16, M["plinth_stone"])   # amalaka
    mb.frustum(0.0, 5.5, z + 0.6, z + 1.8, 0.5, 0.0, 8, M["saffron"])            # kalash
    mb.box(-0.05, 0.05, 5.45, 5.55, z + 1.8, z + 4.0, M["wood_dark"])           # flag pole
    mb.box(0.05, 1.6, 5.47, 5.53, z + 3.0, z + 4.0, M["saffron"])
    mb.box(-3.6, 3.6, -5.5, 2.5, ph, ph + 0.25, M["plinth_stone"])     # mandapa floor
    for x in (-3.3, -1.1, 1.1, 3.3):
        for y in (-5.2, -1.5):
            mb.box(x - 0.2, x + 0.2, y - 0.2, y + 0.2, ph + 0.25, ph + 3.6, W)
    mb.box(-3.8, 3.8, -5.7, 2.6, ph + 3.6, ph + 4.0, W)
    mb.frustum(0.0, -1.5, ph + 4.0, ph + 6.6, 5.0, 0.6, 4, W, rot=math.pi / 4)
    # peepal / sacred tree platform inside the compound
    mb.frustum(-7.5, -6.5, 0.15, 0.75, 2.6, 2.6, 16, M["plinth_stone"])


def panchayat(mb, M, p, rng):
    w, d = p["w"], p["d"]
    wall = M[p["wall"]]
    ph, h = 0.8, 4.2
    vd = 3.2
    mb.box(-w / 2 - 0.2, w / 2 + 0.2, -d / 2 - 0.2, d / 2 + 0.2, PLINTH_BASE, ph, M["plinth_stone"])
    mb.box(-w / 2, w / 2, -d / 2 + vd, d / 2, ph, ph + h, wall)
    for i in range(7):
        x = -w / 2 + 0.4 + i * (w - 0.8) / 6
        mb.box(x - 0.22, x + 0.22, -d / 2 + 0.1, -d / 2 + 0.54, ph, ph + h, M["temple_white"])
    mb.box(-w / 2 - 0.2, w / 2 + 0.2, -d / 2 - 0.2, d / 2 + 0.2, ph + h, ph + h + 0.3, M["roof_concrete"])
    mb.parapet(-w / 2 - 0.2, w / 2 + 0.2, -d / 2 - 0.2, d / 2 + 0.2, ph + h + 0.3, 0.8, 0.2, wall)
    mb.box(-3.5, 3.5, -d / 2 - 0.3, -d / 2 - 0.1, ph + h + 0.3, ph + h + 1.4, M["temple_white"])  # name board
    for i in range(3):
        mb.box(-2.5, 2.5, -d / 2 - 0.4 * (i + 1), -d / 2 - 0.4 * i, 0.0, ph - 0.27 * i, M["plinth_stone"])
    _door(mb, M, 0.0, -d / 2 + vd, ph, 1.5, 2.4)
    for x in (-5.5, -3.0, 3.0, 5.5):
        _window(mb, M, x, -d / 2 + vd, ph + 1.0, 1.2, 1.4)
    mb.frustum(-w / 2 - 3.0, -d / 2 - 3.0, 0.0, 9.0, 0.08, 0.06, 8, M["roof_tin"])   # flag pole
    mb.box(-w / 2 - 3.6, -w / 2 - 2.4, -d / 2 - 3.6, -d / 2 - 2.4, 0.0, 0.5, M["plinth_stone"])


def school(mb, M, p, rng):
    """Compound 40 x 34 m; L-shaped single-storey block at the back, yard in front."""
    w, d = p["w"], p["d"]
    wall = M[p["wall"]]
    mb.box(-w / 2, w / 2, -d / 2, d / 2, PLINTH_BASE, 0.05, M["road_dirt"])
    mb.ring_wall(w, d, 0.35, 0.05, 1.5, M["wall_lime_white"], gate=5.0)
    ph, h = 0.6, 4.0
    y0, y1 = d / 2 - 10.0, d / 2 - 1.0
    mb.box(-w / 2 + 1, w / 2 - 1, y0 - 2.6, y1, -0.5, ph, M["plinth_stone"])
    mb.box(-w / 2 + 1, w / 2 - 1, y0, y1, ph, ph + h, wall)
    mb.box(-w / 2 + 0.6, w / 2 - 0.6, y0 - 2.8, y1 + 0.4, ph + h, ph + h + 0.25, M["roof_concrete"])
    mb.parapet(-w / 2 + 0.6, w / 2 - 0.6, y0 - 2.8, y1 + 0.4, ph + h + 0.25, 0.7, 0.2, wall)
    for i in range(9):
        x = -w / 2 + 1.4 + i * (w - 2.8) / 8
        mb.box(x - 0.18, x + 0.18, y0 - 2.5, y0 - 2.14, ph, ph + h, M["wall_lime_white"])
    for i in range(6):
        x = -w / 2 + 4.0 + i * (w - 8.0) / 5
        _door(mb, M, x, y0, ph, 1.0, 2.2)
    # wing on the east end
    mb.box(w / 2 - 10, w / 2 - 1, -d / 2 + 9, y0 - 2.6, -0.5, ph, M["plinth_stone"])
    mb.box(w / 2 - 9.5, w / 2 - 1, -d / 2 + 9, y0 - 2.6, ph, ph + h, wall)
    mb.box(w / 2 - 10, w / 2 - 0.6, -d / 2 + 8.6, y0 - 2.6, ph + h, ph + h + 0.25, M["roof_concrete"])
    mb.frustum(-4.0, -d / 2 + 6.0, 0.05, 8.5, 0.08, 0.06, 8, M["roof_tin"])        # flag pole
    mb.frustum(-4.0, -d / 2 + 6.0, 0.05, 0.6, 1.3, 1.1, 8, M["plinth_stone"])


BUILDERS = {
    "house_small": house_small,
    "house_common": house_common,
    "house_middle": house_middle,
    "house_rich": house_rich,
    "shop": lambda mb, M, p, rng: shop(mb, M, p, rng, 1),
    "shop_2storey": lambda mb, M, p, rng: shop(mb, M, p, rng, 2),
    "cattle_shed": cattle_shed,
    "grain_store": grain_store,
    "temple": temple,
    "panchayat": panchayat,
    "school": school,
}

OBJECT_PREFIX = {
    "house_small": ("OBJ_House_Small", "BLD_HOUSES"),
    "house_common": ("OBJ_House_Common", "BLD_HOUSES"),
    "house_middle": ("OBJ_House_Middle", "BLD_HOUSES"),
    "house_rich": ("OBJ_House_Haveli", "BLD_HOUSES"),
    "shop": ("OBJ_Shop_Single", "BLD_SHOPS"),
    "shop_2storey": ("OBJ_Shop_Double", "BLD_SHOPS"),
    "cattle_shed": ("OBJ_Utility_CattleShed", "BLD_UTILITY"),
    "grain_store": ("OBJ_Utility_GrainStore", "BLD_UTILITY"),
    "temple": ("OBJ_Landmark_Temple", "BLD_LANDMARKS"),
    "panchayat": ("OBJ_Landmark_Panchayat", "BLD_LANDMARKS"),
    "school": ("OBJ_Landmark_School", "BLD_LANDMARKS"),
}


def build_plot_mesh(p, M):
    mb = MeshBuilder()
    BUILDERS[p["family"]](mb, M, p, random.Random(p["seed"]))
    return mb
