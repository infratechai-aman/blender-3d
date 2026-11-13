"""Architecture kit for the Batch-2 building library (houses, haveli, shops, temple, school, panchayat).

Every builder writes into an HB (hero_lib mesh builder); call kit.put(hb, name, coll) to make the object.
Conventions: metres, Z up, building front faces -Y, origin = footprint centre at ground.
Night: each asset collection stores ["night_lights"] = [[x, y, z, watts], ...] in local space; the master's
lighting_atmosphere.practicals() turns them into warm lights at night.
"""
import math
import os
import random

import bpy
import numpy as np
from mathutils import Matrix

import char_lib as CL
import hero_lib as H
from hero_lib import HB

FONT_DIR = "C:/Windows/Fonts"


# ---------------------------------------------------------------- materials (cached by name)
def materials(palette="#E3C47D", band="#8E3B2E", seed=0):
    g = bpy.data.materials.get
    M = {
        "plaster": H.mat_plaster("MAT_Wall_Plaster_%s" % palette[1:], palette, band=band, band_top=0.9),
        "plaster_in": H.mat_plaster("MAT_Wall_Plaster_Interior_Cream", "#E8DFCB"),
        "white": H.mat_plaster("MAT_Wall_Lime_White", "#EEE7D7"),
        "concrete": g("MAT_Concrete_Weathered") or H.mat_simple("MAT_Concrete_Weathered", "#A39C90", 0.85, noise=0.18),
        "stone": H.mat_stone_blocks(),
        "sandstone": H.mat_stone_blocks("MAT_Wall_Sandstone_Haveli", "#C99A70", "#D8AA80", "#9A7558", 1.2, 0.6, 0.3),
        "sand_smooth": H.mat_simple("MAT_Sandstone_Carved", "#D2A274", 0.75, noise=0.15),
        "kota": H.mat_kota(),
        "tile": H.mat_tile(),
        "wood": H.mat_wood(),
        "wood_dark": H.mat_wood("MAT_Wood_Dark_Aged", "#3E2A1C", "#5A3E29"),
        "teal": H.mat_painted("MAT_Wood_Painted_Teal", "#2F7A72"),
        "green": H.mat_painted("MAT_Wood_Painted_Green", "#3E6B4E"),
        "blue": H.mat_painted("MAT_Wood_Painted_Blue", "#2F5A8A"),
        "iron": H.mat_simple("MAT_Metal_CastIron_Black", "#1F1F1F", 0.42, 0.65),
        "grill": H.mat_simple("MAT_Metal_Grill_Green", "#2F5E4A", 0.45, 0.5, noise=0.1),
        "tin": H.mat_tin(),
        "shutter": H.mat_simple("MAT_Metal_Shutter_Grey", "#7E8A8E", 0.45, 0.6, noise=0.12),
        "tank": H.mat_simple("MAT_Plastic_WaterTank_Black", "#1C1C1C", 0.5, noise=0.05),
        "glass": H.mat_simple("MAT_Glass_Window_Dark", "#2E3A3E", 0.08, 0.2),
        "cloth_red": H.mat_simple("MAT_Cloth_Awning_Red", "#B4473A", 0.8, noise=0.15),
        "cloth_blue": H.mat_simple("MAT_Cloth_Awning_Blue", "#3D6F95", 0.8, noise=0.15),
        "cloth_green": H.mat_simple("MAT_Cloth_Awning_Green", "#4F8452", 0.8, noise=0.15),
        "saffron": H.mat_simple("MAT_Cloth_Saffron", "#E3722A", 0.7, noise=0.1),
        "sign_bg": H.mat_simple("MAT_Sign_Board_Yellow", "#E8B82E", 0.6, noise=0.1),
        "sign_txt": H.mat_simple("MAT_Sign_Text_Red", "#9E1F1A", 0.5),
        "sign_bg2": H.mat_simple("MAT_Sign_Board_Blue", "#1F4E8C", 0.6, noise=0.1),
        "sign_txt2": H.mat_simple("MAT_Sign_Text_White", "#F4F0E6", 0.5),
        "steel": H.mat_simple("MAT_Metal_Steel_Utensil", "#B9BEC2", 0.25, 0.9),
        "fabric": H.mat_simple("MAT_Fabric_Sofa_Maroon", "#7A2F35", 0.85, noise=0.2),
        "durrie": H.mat_simple("MAT_Fabric_Durrie_Stripe", "#A8453A", 0.9, noise=0.3),
        "bedsheet": H.mat_simple("MAT_Fabric_Bedsheet_Floral", "#D98AA0", 0.85, noise=0.35),
        "black": H.mat_simple("MAT_Board_Black", "#1E2420", 0.7),
        "glow": H.mat_simple("MAT_Bulb_Off", "#F4EEDC", 0.2),
        "goods1": H.mat_simple("MAT_Goods_Pack_Red", "#C23A2E", 0.5, noise=0.3),
        "goods2": H.mat_simple("MAT_Goods_Pack_Yellow", "#E0B030", 0.5, noise=0.3),
        "goods3": H.mat_simple("MAT_Goods_Pack_Green", "#3E8A4A", 0.5, noise=0.3),
        "sack": H.mat_simple("MAT_Jute_Sack", "#B39A6A", 0.95, noise=0.3),
        "brass": H.mat_simple("MAT_Metal_Brass", "#B8903A", 0.3, 1.0),
        "terracotta": H.mat_simple("MAT_Clay_Pot_Terracotta", "#A45A3C", 0.6, noise=0.14),
        "leaf": H.mat_simple("MAT_Leaf_Tulsi_Simple", "#3E6A2A", 0.6, noise=0.25),
        "rope": H.mat_rope(),
    }
    return M


def put(hb, name, coll, recalc=True, smooth=False, bevel=0.0):
    me = hb.to_mesh("ME_" + name, recalc=recalc)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me)
    coll.objects.link(o)
    if bevel:
        b = o.modifiers.new("Bevel", "BEVEL")
        b.width = bevel
        b.segments = 2
        b.limit_method = "ANGLE"
    return o


# ---------------------------------------------------------------- walls + openings
def wall_x(hb, mat, x0, x1, y0, y1, z0, z1, holes):
    """Wall slab running along X with holes [(x0, x1, z0, z1)]."""
    pos = x0
    for (h0, h1, v0, v1) in sorted(holes):
        if h0 > pos:
            hb.box(pos, h0, y0, y1, z0, z1, mat)
        if v0 > z0:
            hb.box(h0, h1, y0, y1, z0, v0, mat)
        if v1 < z1:
            hb.box(h0, h1, y0, y1, v1, z1, mat)
        pos = h1
    if pos < x1:
        hb.box(pos, x1, y0, y1, z0, z1, mat)


def wall_y(hb, mat, x0, x1, y0, y1, z0, z1, holes):
    pos = y0
    for (h0, h1, v0, v1) in sorted(holes):
        if h0 > pos:
            hb.box(x0, x1, pos, h0, z0, z1, mat)
        if v0 > z0:
            hb.box(x0, x1, h0, h1, z0, v0, mat)
        if v1 < z1:
            hb.box(x0, x1, h0, h1, v1, z1, mat)
        pos = h1
    if pos < y1:
        hb.box(x0, x1, pos, y1, z0, z1, mat)


def window(hb, M, cx, face_y, z0, w=1.0, h=1.2, depth=0.25, sgn=-1, shutter="teal", grill=True, chhajja=True,
           open_frac=0.6, axis="x"):
    """Window on a wall face: frame, sill, two leaf shutters (partly open), bar grill, concrete chhajja.
    axis='x' -> wall along X, face at y=face_y, outward = sgn*Y.  axis='y' -> wall along Y, face at x=face_y."""
    sub = HB()
    fw = 0.07
    sub.box(-w / 2 - fw, w / 2 + fw, -0.04, depth, -fw, 0.0, M["concrete"])                   # sill
    sub.box(-w / 2 - fw, -w / 2, -0.03, depth, 0.0, h, M["wood_dark"])
    sub.box(w / 2, w / 2 + fw, -0.03, depth, 0.0, h, M["wood_dark"])
    sub.box(-w / 2 - fw, w / 2 + fw, -0.03, depth, h, h + fw, M["wood_dark"])
    sub.box(-w / 2, w / 2, depth * 0.6, depth * 0.62, 0.0, h, M["glass"])
    if grill:
        for k in range(1, 6):
            x = -w / 2 + k * w / 6
            sub.rod(M["grill"], (x, depth * 0.3, 0.0), (x, depth * 0.3, h), 0.008, 5)
        for z in (h * 0.33, h * 0.66):
            sub.rod(M["grill"], (-w / 2, depth * 0.3, z), (w / 2, depth * 0.3, z), 0.008, 5)
    for s in (-1, 1):                                                          # shutters swung out
        leaf = HB()
        leaf.box(0.0, w / 2, -0.02, 0.0, 0.02, h - 0.02, M[shutter])
        for z in (0.25, h - 0.25):
            leaf.box(0.03, w / 2 - 0.03, -0.035, -0.02, z - 0.04, z + 0.04, M[shutter])
        ang = s * math.radians(100 * open_frac)
        sub.merge(leaf, Matrix.Translation((s * w / 2, 0, 0)) @ Matrix.Rotation(ang if s < 0 else -ang, 4, "Z") @
                  Matrix.Scale(-1 if s < 0 else 1, 4, (1, 0, 0)))
    if chhajja:
        sub.box(-w / 2 - 0.25, w / 2 + 0.25, -0.5, depth, h + 0.18, h + 0.26, M["concrete"])
    if axis == "x":
        T = Matrix.Translation((cx, face_y, z0)) @ (Matrix.Rotation(math.pi, 4, "Z") if sgn > 0 else Matrix())
    else:
        T = Matrix.Translation((face_y, cx, z0)) @ Matrix.Rotation(-math.pi / 2 if sgn < 0 else math.pi / 2, 4, "Z")
    hb.merge(sub, T)


def door(hb, M, cx, face_y, z0, w=1.1, h=2.15, depth=0.25, sgn=-1, paint="teal", open_frac=0.0, axis="x", carved=False):
    sub = HB()
    fw = 0.09
    sub.box(-w / 2 - fw, -w / 2, -0.04, depth, 0.0, h + fw, M["wood_dark"])
    sub.box(w / 2, w / 2 + fw, -0.04, depth, 0.0, h + fw, M["wood_dark"])
    sub.box(-w / 2 - fw, w / 2 + fw, -0.04, depth, h, h + fw, M["wood_dark"])
    sub.box(-w / 2 - 0.12, w / 2 + 0.12, -0.12, depth, -0.02, 0.0, M["stone"])            # threshold
    for s in (-1, 1):
        leaf = HB()
        leaf.box(0.0, w / 2, 0.0, 0.05, 0.0, h, M[paint])
        for k in range(3):
            z = 0.25 + k * (h - 0.4) / 2
            leaf.box(0.07, w / 2 - 0.07, -0.015, 0.0, z, z + (h - 0.6) / 3, M[paint])
        if carved:
            for k in range(4):
                for j in range(2):
                    leaf.ellipsoid(0.12 + j * (w / 2 - 0.24), -0.02, 0.3 + k * (h - 0.5) / 3, 0.025, 0.02, 0.025, M["brass"], 8, 4)
        ang = math.radians(80 * open_frac)
        sub.merge(leaf, Matrix.Translation((s * w / 2, depth * 0.5, 0)) @ Matrix.Rotation(-ang * s, 4, "Z") @
                  Matrix.Scale(-1 if s > 0 else 1, 4, (1, 0, 0)))
    if axis == "x":
        T = Matrix.Translation((cx, face_y, z0)) @ (Matrix.Rotation(math.pi, 4, "Z") if sgn > 0 else Matrix())
    else:
        T = Matrix.Translation((face_y, cx, z0)) @ Matrix.Rotation(-math.pi / 2 if sgn < 0 else math.pi / 2, 4, "Z")
    hb.merge(sub, T)


def parapet(hb, mat, x0, x1, y0, y1, z0, h=0.9, t=0.15, coping=None, gaps=()):
    hb.box(x0, x1, y0, y0 + t, z0, z0 + h, mat)
    hb.box(x0, x1, y1 - t, y1, z0, z0 + h, mat)
    hb.box(x0, x0 + t, y0 + t, y1 - t, z0, z0 + h, mat)
    hb.box(x1 - t, x1, y0 + t, y1 - t, z0, z0 + h, mat)
    if coping is not None:
        c = 0.04
        hb.box(x0 - c, x1 + c, y0 - c, y0 + t + c, z0 + h, z0 + h + 0.05, coping)
        hb.box(x0 - c, x1 + c, y1 - t - c, y1 + c, z0 + h, z0 + h + 0.05, coping)
        hb.box(x0 - c, x0 + t + c, y0 + t, y1 - t, z0 + h, z0 + h + 0.05, coping)
        hb.box(x1 - t - c, x1 + c, y0 + t, y1 - t, z0 + h, z0 + h + 0.05, coping)


def railing(hb, mat, p0, p1, z, h=0.95, spacing=0.12, r=0.012):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    L = float(np.linalg.norm(p1[:2] - p0[:2]))
    n = max(2, int(L / spacing))
    for k in range(n + 1):
        q = p0 + (p1 - p0) * k / n
        hb.rod(mat, (q[0], q[1], z), (q[0], q[1], z + h), r, 6)
    hb.rod(mat, (p0[0], p0[1], z + h), (p1[0], p1[1], z + h), r * 2.5, 6)
    hb.rod(mat, (p0[0], p0[1], z + 0.1), (p1[0], p1[1], z + 0.1), r * 1.5, 6)


def stair(hb, mat, x0, x1, y0, y1, z0, z1, along="y"):
    """Straight solid stair from (y0, z0) up to (y1, z1) (or along x)."""
    rise = 0.17
    n = max(1, int(round((z1 - z0) / rise)))
    for k in range(n):
        zt = z0 + (k + 1) * (z1 - z0) / n
        if along == "y":
            ya = y0 + k * (y1 - y0) / n
            yb = ya + (y1 - y0) / n
            hb.box(x0, x1, min(ya, yb), max(ya, yb), z0, zt, mat)
        else:
            xa = x0 + k * (x1 - x0) / n
            hb.box(min(xa, xa + (x1 - x0) / n), max(xa, xa + (x1 - x0) / n), y0, y1, z0, zt, mat)


def column(hb, M, x, y, z0, z1, r=0.16, kind="round", mat=None):
    mat = mat or M["white"]
    if kind == "round":
        hb.lathe(mat, [(0.0, 0.0), (r * 1.5, 0.0), (r * 1.5, 0.1), (r * 1.15, 0.16), (r, 0.22), (r * 0.9, z1 - z0 - 0.3),
                       (r * 1.2, z1 - z0 - 0.2), (r * 1.4, z1 - z0 - 0.08), (r * 1.4, z1 - z0), (0.0, z1 - z0)], 16, x, y, z0)
    else:
        hb.box(x - r * 1.3, x + r * 1.3, y - r * 1.3, y + r * 1.3, z0, z0 + 0.18, mat)
        hb.box(x - r, x + r, y - r, y + r, z0 + 0.18, z1 - 0.15, mat)
        hb.box(x - r * 1.3, x + r * 1.3, y - r * 1.3, y + r * 1.3, z1 - 0.15, z1, mat)


def arch_band(hb, mat, x0, x1, y0, y1, z_spring, rise, z_top, n=14, axis="x"):
    """Fills the wall above a semicircular/segmental arch opening between x0..x1 (axis x) up to z_top."""
    span = x1 - x0
    for i in range(n):
        a0, a1 = math.pi * i / n, math.pi * (i + 1) / n
        xa = x0 + span * (1 - math.cos(a0)) / 2
        xb = x0 + span * (1 - math.cos(a1)) / 2
        za = z_spring + rise * math.sin(a0)
        zb = z_spring + rise * math.sin(a1)
        V = [(xa, y0, za), (xb, y0, zb), (xb, y0, z_top), (xa, y0, z_top), (xa, y1, za), (xb, y1, zb), (xb, y1, z_top), (xa, y1, z_top)]
        if axis != "x":
            V = [(y, x, z) for (x, y, z) in V]
        F = [(0, 1, 2, 3), (5, 4, 7, 6), (0, 4, 5, 1), (3, 2, 6, 7), (0, 3, 7, 4), (1, 5, 6, 2)]
        hb.add(V, F, mat)


def water_tank(hb, M, x, y, z):
    hb.box(x - 0.7, x + 0.7, y - 0.7, y + 0.7, z, z + 0.35, M["concrete"])
    hb.lathe(M["tank"], [(0.0, 0.0), (0.55, 0.0), (0.58, 0.1), (0.58, 0.95), (0.5, 1.1), (0.25, 1.18), (0.25, 1.25), (0.0, 1.25)],
             24, x, y, z + 0.35)
    for k in range(5):
        zz = z + 0.55 + k * 0.17
        hb.lathe(M["tank"], [(0.585, zz - z - 0.35), (0.6, zz - z - 0.34), (0.585, zz - z - 0.33)], 24, x, y, z + 0.35)


def awning(hb, mat, x0, x1, y_wall, z_top, depth=1.3, drop=0.45, scallop=True):
    V = [(x0, y_wall, z_top), (x1, y_wall, z_top), (x1, y_wall - depth, z_top - drop), (x0, y_wall - depth, z_top - drop)]
    hb.add(V, [(0, 1, 2, 3)], mat)
    if scallop:
        n = max(3, int((x1 - x0) / 0.3))
        for k in range(n):
            xa = x0 + (x1 - x0) * k / n
            xb = x0 + (x1 - x0) * (k + 1) / n
            hb.add([(xa, y_wall - depth, z_top - drop), (xb, y_wall - depth, z_top - drop),
                    ((xa + xb) / 2, y_wall - depth - 0.02, z_top - drop - 0.14)], [(0, 1, 2)], mat)
    for x in (x0 + 0.05, x1 - 0.05):
        hb.rod(bpy.data.materials.get("MAT_Metal_CastIron_Black") or mat, (x, y_wall, z_top), (x, y_wall - depth, z_top - drop), 0.012, 5)


def sign(coll, name, text, loc, rot_z, size, bg_mat, txt_mat, w, h, font="bahnschrift.ttf", extrude=0.01):
    """Painted board with raised lettering (text converted to a mesh)."""
    hb = HB()
    hb.box(-w / 2, w / 2, -0.03, 0.0, -h / 2, h / 2, bg_mat)
    bo = put(hb, name + "_Board", coll)
    cu = bpy.data.curves.new(name + "_Text", "FONT")
    cu.body = text
    try:
        cu.font = bpy.data.fonts.load(os.path.join(FONT_DIR, font), check_existing=True)
    except Exception:
        pass
    cu.size = size
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = extrude
    cu.materials.append(txt_mat)
    to = bpy.data.objects.new(name + "_Text", cu)
    to.rotation_euler = (math.pi / 2, 0, 0)
    to.location = (0, -0.035, 0)
    coll.objects.link(to)
    # fit the text into the board
    bpy.context.view_layer.update()
    dims = to.dimensions
    if dims.x > w * 0.9:
        s = w * 0.9 / dims.x
        to.scale = (s, s, 1)
    for o in (bo, to):
        o.matrix_world = Matrix.Translation(loc) @ Matrix.Rotation(rot_z, 4, "Z") @ o.matrix_world
    # convert text to mesh so the asset links cleanly
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(to.evaluated_get(dg))
    tm = bpy.data.objects.new(name + "_Lettering", me)
    tm.matrix_world = to.matrix_world.copy()
    coll.objects.link(tm)
    bpy.data.objects.remove(to, do_unlink=True)
    return bo, tm


# ---------------------------------------------------------------- furniture (local, at (x, y, z), facing -Y)
def _at(hb, sub, x, y, z, rz=0.0):
    hb.merge(sub, Matrix.Translation((x, y, z)) @ Matrix.Rotation(rz, 4, "Z"))


def bed(hb, M, x, y, z, rz=0.0, L=2.0, W_=1.5):
    s = HB()
    s.box(-W_ / 2, W_ / 2, -L / 2, L / 2, 0.2, 0.45, M["wood"])
    s.box(-W_ / 2 + 0.03, W_ / 2 - 0.03, -L / 2 + 0.03, L / 2 - 0.03, 0.45, 0.6, M["bedsheet"])
    s.box(-W_ / 2, W_ / 2, L / 2 - 0.06, L / 2, 0.0, 1.05, M["wood"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            s.box(sx * W_ / 2 - 0.05 * (sx + 1), sx * W_ / 2 - 0.05 * (sx - 1), sy * L / 2 - 0.05 * (sy + 1), sy * L / 2 - 0.05 * (sy - 1), 0.0, 0.25, M["wood"])
    for sx in (-0.35, 0.35):
        s.ellipsoid(sx, L / 2 - 0.3, 0.66, 0.28, 0.16, 0.08, M["white"], 10, 6)
    _at(hb, s, x, y, z, rz)


def sofa(hb, M, x, y, z, rz=0.0, L=2.0):
    s = HB()
    s.box(-L / 2, L / 2, -0.4, 0.4, 0.15, 0.45, M["fabric"])
    s.box(-L / 2, L / 2, 0.25, 0.45, 0.45, 0.9, M["fabric"])
    for sx in (-1, 1):
        s.box(sx * L / 2 - (0.15 if sx > 0 else 0.0), sx * L / 2 + (0.0 if sx > 0 else 0.15), -0.4, 0.45, 0.15, 0.65, M["fabric"])
    s.box(-L / 2, L / 2, -0.4, 0.45, 0.0, 0.15, M["wood_dark"])
    _at(hb, s, x, y, z, rz)


def table(hb, M, x, y, z, rz=0.0, L=1.2, W_=0.7, h=0.75, mat=None):
    mat = mat or M["wood"]
    s = HB()
    s.box(-L / 2, L / 2, -W_ / 2, W_ / 2, h - 0.04, h, mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            s.box(sx * (L / 2 - 0.06) - 0.025, sx * (L / 2 - 0.06) + 0.025, sy * (W_ / 2 - 0.06) - 0.025, sy * (W_ / 2 - 0.06) + 0.025, 0.0, h - 0.04, mat)
    _at(hb, s, x, y, z, rz)


def chair(hb, M, x, y, z, rz=0.0, mat=None):
    mat = mat or M["wood"]
    s = HB()
    s.box(-0.22, 0.22, -0.22, 0.22, 0.42, 0.46, mat)
    for sx in (-1, 1):
        for sy in (-1, 1):
            s.box(sx * 0.19 - 0.02, sx * 0.19 + 0.02, sy * 0.19 - 0.02, sy * 0.19 + 0.02, 0.0, 0.42 if sy < 0 else 0.95, mat)
    s.box(-0.2, 0.2, 0.17, 0.21, 0.6, 0.92, mat)
    _at(hb, s, x, y, z, rz)


def almirah(hb, M, x, y, z, rz=0.0):
    s = HB()
    s.box(-0.5, 0.5, -0.28, 0.28, 0.0, 1.9, M["steel"])
    s.box(-0.005, 0.005, -0.29, -0.28, 0.1, 1.8, M["iron"])
    for sx in (-0.06, 0.06):
        s.box(sx - 0.01, sx + 0.01, -0.31, -0.28, 0.9, 1.1, M["iron"])
    _at(hb, s, x, y, z, rz)


def kitchen(hb, M, x, y, z, rz=0.0, L=2.4):
    s = HB()
    s.box(-L / 2, L / 2, -0.3, 0.3, 0.0, 0.8, M["kota"])
    s.box(-L / 2, L / 2, -0.32, 0.32, 0.8, 0.84, M["stone"])
    s.box(-0.35, 0.25, -0.2, 0.2, 0.84, 0.92, M["steel"])                                     # two-burner stove
    for bx in (-0.2, 0.1):
        s.frustum(bx, 0.0, 0.92, 0.94, 0.07, 0.07, 12, M["iron"])
    s.lathe(M["steel"], [(0.0, 0.0), (0.12, 0.0), (0.13, 0.15), (0.12, 0.16)], 14, -0.2, 0.0, 0.94)
    s.box(-L / 2, L / 2, 0.2, 0.32, 1.4, 1.43, M["wood"])                                     # utensil shelf
    for k in range(7):
        s.lathe(M["steel"], [(0.0, 0.0), (0.07, 0.0), (0.09, 0.05), (0.09, 0.06)], 12, -L / 2 + 0.2 + k * 0.33, 0.26, 1.43)
    s.frustum(L / 2 - 0.25, 0.0, 0.84, 1.2, 0.15, 0.15, 14, M["tank"])                       # gas cylinder... drum
    _at(hb, s, x, y, z, rz)


def tv_unit(hb, M, x, y, z, rz=0.0):
    s = HB()
    s.box(-0.8, 0.8, -0.2, 0.2, 0.0, 0.5, M["wood_dark"])
    s.box(-0.5, 0.5, -0.03, 0.03, 0.55, 1.15, M["black"])
    s.box(-0.08, 0.08, -0.08, 0.08, 0.5, 0.55, M["black"])
    _at(hb, s, x, y, z, rz)


def ceiling_fan(hb, M, x, y, z_ceiling):
    hb.rod(M["white"], (x, y, z_ceiling), (x, y, z_ceiling - 0.35), 0.015, 6)
    hb.frustum(x, y, z_ceiling - 0.45, z_ceiling - 0.35, 0.09, 0.09, 12, M["white"])
    for k in range(3):
        a = 2 * math.pi * k / 3
        p = np.array([x, y, z_ceiling - 0.42])
        d = np.array([math.cos(a), math.sin(a), 0])
        hb.obox(M["white"], p + d * 0.42, d, np.cross([0, 0, 1], d), 0.36, 0.06, 0.006)


def bench(hb, M, x, y, z, rz=0.0, L=1.6, mat=None):
    mat = mat or M["wood"]
    s = HB()
    s.box(-L / 2, L / 2, -0.18, 0.18, 0.42, 0.47, mat)
    for sx in (-1, 1):
        s.box(sx * (L / 2 - 0.1) - 0.04, sx * (L / 2 - 0.1) + 0.04, -0.15, 0.15, 0.0, 0.42, mat)
    _at(hb, s, x, y, z, rz)


def school_desk(hb, M, x, y, z, rz=0.0):
    s = HB()
    s.box(-0.6, 0.6, -0.2, 0.2, 0.7, 0.74, M["wood"])
    s.box(-0.6, 0.6, 0.35, 0.6, 0.42, 0.46, M["wood"])
    for sx in (-0.55, 0.55):
        s.box(sx - 0.03, sx + 0.03, -0.2, 0.6, 0.0, 0.05, M["iron"])
        s.box(sx - 0.02, sx + 0.02, -0.15, -0.11, 0.05, 0.7, M["iron"])
        s.box(sx - 0.02, sx + 0.02, 0.45, 0.49, 0.05, 0.42, M["iron"])
    _at(hb, s, x, y, z, rz)


def shelf_goods(hb, M, x, y, z, rz=0.0, L=2.0, H_=2.0, rows=4, rng=None):
    rng = rng or random.Random(1)
    s = HB()
    s.box(-L / 2, L / 2, 0.2, 0.25, 0.0, H_, M["wood"])
    for k in range(rows + 1):
        zz = k * H_ / rows
        s.box(-L / 2, L / 2, -0.15, 0.25, zz, zz + 0.03, M["wood"])
        if k == rows:
            break
        xx = -L / 2 + 0.05
        while xx < L / 2 - 0.15:
            bw = rng.uniform(0.08, 0.2)
            bh = rng.uniform(0.12, H_ / rows - 0.08)
            mat = M[rng.choice(["goods1", "goods2", "goods3", "steel", "sack"])]
            s.box(xx, xx + bw, -0.12, 0.18, zz + 0.03, zz + 0.03 + bh, mat)
            xx += bw + rng.uniform(0.01, 0.04)
    for sx in (-1, 1):
        s.box(sx * L / 2 - 0.03, sx * L / 2 + 0.03, -0.15, 0.25, 0.0, H_, M["wood"])
    _at(hb, s, x, y, z, rz)


def sacks(hb, M, x, y, z, n=4, rng=None):
    rng = rng or random.Random(2)
    for k in range(n):
        hb.ellipsoid(x + (k % 2) * 0.45, y + (k // 2) * 0.4, z + 0.25, 0.22, 0.18, 0.28, M["sack"], 12, 8)
        hb.ellipsoid(x + (k % 2) * 0.45, y + (k // 2) * 0.4, z + 0.52, 0.18, 0.15, 0.06, M["goods2"], 10, 5)


def durrie(hb, M, x0, x1, y0, y1, z):
    hb.box(x0, x1, y0, y1, z, z + 0.01, M["durrie"])
