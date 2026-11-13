"""Batch 2 placement: swap blockout massing in the saved MASTER_WORLD for the hero buildings (same plot, same
transform, same plot_id).  Checkpoint first; the blockout objects move to a hidden B2_REPLACED_BLOCKOUT collection
(not deleted) so the swap is reversible.  build_master_v2.HERO_FAMILIES does the same on a full rebuild.
"""
import datetime
import os
import shutil

import bpy

path = bpy.data.filepath
root = os.path.abspath(os.path.join(os.path.dirname(path), ".."))
shutil.copy2(path, os.path.join(root, "99_ARCHIVE", "MASTER_WORLD_preB2_%s.blend" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))

LIBS = {os.path.join(root, "02_ARCHITECTURE", "LIB_Buildings_B2.blend"):
        ["AST_House_Middle_A", "AST_Haveli_A", "AST_Shop_Kirana_A", "AST_Shop_Chai_A", "AST_Shop_Cloth_A", "AST_Shop2_Hardware_A",
         "AST_Temple_Shiv_A", "AST_School_A", "AST_Panchayat_A"],
        os.path.join(root, "02_ARCHITECTURE", "HOUSES_SMALL", "HERO_House_Small_Kaccha_A.blend"): ["AST_House_Small_Kaccha_A"]}
assets = {}
for lib, names in LIBS.items():
    if not os.path.exists(lib):
        print("[b2] missing library", lib)
        continue
    with bpy.data.libraries.load(lib, link=True, relative=True) as (src, dst):
        dst.collections = [n for n in src.collections if n in names]
    for c in dst.collections:
        if c:
            assets[c.name] = c

FAMILY = {"house_small": ["AST_House_Small_Kaccha_A"], "house_middle": ["AST_House_Middle_A"], "house_rich": ["AST_Haveli_A"],
          "shop": ["AST_Shop_Kirana_A", "AST_Shop_Chai_A", "AST_Shop_Cloth_A"], "shop_2storey": ["AST_Shop2_Hardware_A"],
          "temple": ["AST_Temple_Shiv_A"], "school": ["AST_School_A"], "panchayat": ["AST_Panchayat_A"]}
hidden = bpy.data.collections.get("B2_REPLACED_BLOCKOUT") or bpy.data.collections.new("B2_REPLACED_BLOCKOUT")
if hidden.name not in bpy.context.scene.collection.children:
    bpy.context.scene.collection.children.link(hidden)
hidden.hide_render = True
hidden.hide_viewport = True
done = {}
for o in list(bpy.data.objects):
    fam = o.get("family")
    if fam not in FAMILY or o.instance_type == "COLLECTION" or o.type != "MESH":
        continue
    pid = int(str(o.get("plot_id", "P0"))[1:] or 0)
    choices = [a for a in FAMILY[fam] if a in assets]
    if not choices:
        continue
    name = choices[pid % len(choices)]
    e = bpy.data.objects.new(o.name + "_HERO", None)
    e.instance_type = "COLLECTION"
    e.instance_collection = assets[name]
    e.matrix_world = o.matrix_world.copy()
    if fam == "house_small":
        e.location.z -= 0.0
    for k in ("plot_id", "family", "neighbourhood"):
        if k in o:
            e[k] = o[k]
    e["status"] = "hero (B2)"
    for c in o.users_collection:
        c.objects.link(e)
        c.objects.unlink(o)
    hidden.objects.link(o)
    done[name] = done.get(name, 0) + 1
bpy.ops.wm.save_mainfile()
print("[b2] placed:", done)
