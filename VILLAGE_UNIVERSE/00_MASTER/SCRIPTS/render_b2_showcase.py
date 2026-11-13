"""Batch 2 showcase: every hero building on its own lot, exterior 3/4 + interior shots, day and night.

  blender -b --factory-startup --python render_b2_showcase.py -- [--preset morning|night] [--only KEY,KEY] [--rx 1280 --ry 720]
Renders -> 10_EXPORTS/REVIEWS/B2_BUILDINGS_v001/<preset>/
"""
import math
import os
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import hero_lib as H  # noqa: E402
import lighting_atmosphere as LA  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
arg = lambda n, d=None: args[args.index(n) + 1] if n in args else d  # noqa: E731
preset = arg("--preset", "morning")
only = arg("--only")
only = set(only.split(",")) if only else None

B2 = os.path.join(ROOT, "02_ARCHITECTURE", "LIB_Buildings_B2.blend")
KACCHA = os.path.join(ROOT, "02_ARCHITECTURE", "HOUSES_SMALL", "HERO_House_Small_Kaccha_A.blend")
COMMON = os.path.join(ROOT, "02_ARCHITECTURE", "HOUSES_MEDIUM", "HERO_House_Common_A.blend")
BANYAN = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Hero_Banyan.blend")
# key: (library, collection, lot size, exterior cam (dx, dy, dz) as fractions of size, interior cam (pos, target, lens) local)
SHOW = {
    "Kaccha":    (KACCHA, "AST_House_Small_Kaccha_A", 8, (0.95, -1.25, 0.42), ((1.9, -1.5, 1.55), (-1.6, 1.4, 0.9), 18)),
    "Common":    (COMMON, "AST_House_Common_A", 12, (0.9, -1.2, 0.4), None),
    "Middle":    (B2, "AST_House_Middle_A", 15, (0.9, -1.25, 0.55), ((-4.3, -1.9, 1.6), (-1.0, 4.5, 1.2), 18)),
    "Haveli":    (B2, "AST_Haveli_A", 23, (0.85, -1.15, 0.5), ((-3.2, -2.8, 2.0), (2.0, 3.0, 3.0), 16)),
    "Kirana":    (B2, "AST_Shop_Kirana_A", 7, (0.8, -1.5, 0.35), ((0.6, -4.8, 1.6), (0.0, 2.0, 1.4), 22)),
    "Chai":      (B2, "AST_Shop_Chai_A", 7, (-0.8, -1.5, 0.35), None),
    "Cloth":     (B2, "AST_Shop_Cloth_A", 7, (0.8, -1.5, 0.35), None),
    "Hardware":  (B2, "AST_Shop2_Hardware_A", 9, (0.85, -1.4, 0.45), None),
    "Temple":    (B2, "AST_Temple_Shiv_A", 26, (0.85, -1.2, 0.45), ((0.0, -1.0, 2.2), (0.0, 3.8, 1.6), 24)),
    "School":    (B2, "AST_School_A", 42, (0.75, -1.05, 0.38), ((-9.4, 0.8, 1.6), (-14.5, -2.0, 1.4), 18)),
    "Panchayat": (B2, "AST_Panchayat_A", 19, (0.8, -1.25, 0.4), ((5.8, -0.6, 1.6), (-1.0, 4.2, 1.2), 18)),
    "Banyan":    (BANYAN, "VEG_Tree_Banyan_Chowk_Hero", 34, (0.0, -1.0, 0.12), ((-6.0, -11.0, 1.7), (0.0, 0.0, 3.5), 24)),
}

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
ground = HB()
ground.add([(-200, -200, -0.02), (900, -200, -0.02), (900, 200, -0.02), (-200, 200, -0.02)], [(0, 1, 2, 3)], H.mat_ground())
sc.collection.objects.link(bpy.data.objects.new("STG_Ground", ground.to_mesh("ME_STG_Ground")))
cams = []
x = 0.0
for key, (lib, cname, size, ext, inte) in SHOW.items():
    if only and key not in only:
        continue
    if not os.path.exists(lib):
        print("[show] missing", lib)
        continue
    with bpy.data.libraries.load(lib, link=True) as (src, dst):
        dst.collections = [cname]
    coll = dst.collections[0]
    if coll is None:
        continue
    x += size * 0.5 + 25.0
    e = bpy.data.objects.new("SHOW_" + key, None)
    e.instance_type = "COLLECTION"
    e.instance_collection = coll
    e.location = (x, 0, 0)
    sc.collection.objects.link(e)
    base = Vector((x, 0, 0))
    pos = base + Vector((ext[0] * size, ext[1] * size, ext[2] * size + 1.5))
    tgt = base + Vector((0, 0, size * 0.16 + 1.0))
    cams.append(("%s_Exterior" % key, pos, tgt, 30 if key != "Banyan" else 24))
    if inte:
        p, t, lens = inte
        cams.append(("%s_Interior" % key, base + Vector(p), base + Vector(t), lens))
    x += size * 0.5
LA.apply(sc, preset)
out = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "B2_BUILDINGS_v001", preset)
os.makedirs(out, exist_ok=True)
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x, sc.render.resolution_y = int(arg("--rx", 1280)), int(arg("--ry", 720))
sc.eevee.taa_render_samples = int(arg("--samples", 32))
for name, pos, tgt, lens in cams:
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.clip_end = 3000
    o = bpy.data.objects.new(name, cd)
    o.location = pos
    o.rotation_euler = (tgt - pos).to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(o)
    sc.camera = o
    sc.render.filepath = os.path.join(out, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("[show] rendered", name)
