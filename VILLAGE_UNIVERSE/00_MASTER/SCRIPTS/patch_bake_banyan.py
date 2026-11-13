"""Bake the chowk hero banyan's 53k leaf instances into one local mesh (EEVEE shadow-map memory on 8 GB machines)."""
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import patch_b456 as P  # noqa: E402

e = bpy.data.objects.get("INST_Hero_Banyan_Chowk")
src = e.instance_collection if e else None
if src is not None and not src.name.endswith("_BAKED"):
    baked = P.bake(src, "VEG_Tree_Banyan_Chowk_Hero_BAKED")
    for k in ("night_lights",):
        if k in src:
            baked[k] = src[k]
    e["source_collection"] = src.name
    e.instance_collection = baked
    bpy.ops.wm.save_mainfile()
    print("[bake] banyan baked:", len(baked.objects[0].data.polygons), "polys")
else:
    print("[bake] nothing to do")
