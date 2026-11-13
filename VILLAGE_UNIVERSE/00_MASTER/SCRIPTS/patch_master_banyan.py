"""Swap the chowk banyan in the saved MASTER_WORLD for the hero banyan (checkpoint first). Same result as a rebuild."""
import datetime
import os
import shutil

import bpy

path = bpy.data.filepath
root = os.path.abspath(os.path.join(os.path.dirname(path), ".."))
shutil.copy2(path, os.path.join(root, "99_ARCHIVE", "MASTER_WORLD_preBanyan_%s.blend" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")))
old = bpy.data.objects.get("INST_Hero_Banyan_Chowk")
loc = old.location.copy() if old else (0, 0, 0)
if old:
    bpy.data.objects.remove(old, do_unlink=True)
lib = os.path.join(root, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Hero_Banyan.blend")
with bpy.data.libraries.load(lib, link=True) as (src, dst):
    dst.collections = ["VEG_Tree_Banyan_Chowk_Hero"]
e = bpy.data.objects.new("INST_Hero_Banyan_Chowk", None)
e.instance_type = "COLLECTION"
e.instance_collection = dst.collections[0]
ch = bpy.data.objects.get("OBJ_Landmark_Chabutra_Chowk")
e.location = (0.0, 0.0, (ch.location.z if ch else loc[2] - 0.7) + 0.85)
e.rotation_euler = (0, 0, 0.4)
bpy.data.collections["ENV_VEGETATION"].objects.link(e)
bpy.ops.wm.save_mainfile()
print("[patch] hero banyan placed at", tuple(e.location))
