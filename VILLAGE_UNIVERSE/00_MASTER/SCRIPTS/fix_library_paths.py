"""
Repair library links so the project opens on any machine.

  blender -b SOME.blend --python fix_library_paths.py [-- --dry-run]

1. Project libraries linked by an absolute path from another machine (e.g. C:\\Users\\<someone>\\Downloads\\...) are
   re-pointed at the same file inside THIS checkout (matched by the path below VILLAGE_UNIVERSE), stored relative.
2. Blender's bundled node-asset libraries (datafiles/assets/...) from another Blender version are re-pointed at the
   running Blender's own datafiles, then made LOCAL so the file no longer depends on any install path.
3. Every remaining project library path is made relative.
A checkpoint copy goes to 99_ARCHIVE before saving.
"""
import datetime
import os
import shutil
import sys

import bpy

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DRY = "--dry-run" in ARGS
blend = bpy.data.filepath
here = os.path.dirname(blend)
root = here
while root and os.path.basename(root) != "VILLAGE_UNIVERSE":
    parent = os.path.dirname(root)
    if parent == root:
        root = None
        break
    root = parent
datafiles = os.path.join(os.path.dirname(bpy.app.binary_path), "%d.%d" % bpy.app.version[:2], "datafiles")

changed = 0
for lib in list(bpy.data.libraries):
    old = lib.filepath
    absold = os.path.normpath(bpy.path.abspath(old))
    new = None
    norm = old.replace("\\", "/")
    if "/VILLAGE_UNIVERSE/" in norm and root:
        tail = norm.split("/VILLAGE_UNIVERSE/", 1)[1]
        cand = os.path.join(root, *tail.split("/"))
        if os.path.exists(cand):
            new = cand
    elif "/datafiles/" in norm:
        tail = norm.split("/datafiles/", 1)[1]
        cand = os.path.join(datafiles, *tail.split("/"))
        if os.path.exists(cand):
            new = cand
    if new is None and os.path.exists(absold):
        new = absold
    if new is None:
        print("[paths] UNRESOLVED", old)
        continue
    rel = bpy.path.relpath(new) if "datafiles" not in new else new
    if rel != old:
        print("[paths] %s\n        -> %s" % (old, rel))
        if not DRY:
            lib.filepath = rel
            lib.reload()
        changed += 1

# make bundled node assets local (no install-path dependency)
if not DRY:
    for lib in list(bpy.data.libraries):
        if "datafiles" in lib.filepath.replace("\\", "/"):
            ids = [i for coll in (bpy.data.node_groups, bpy.data.materials, bpy.data.objects) for i in coll if i.library == lib]
            for i in ids:
                i.make_local()
            print("[paths] made local %d datablocks from %s" % (len(ids), os.path.basename(lib.filepath)))

missing = [l.filepath for l in bpy.data.libraries if not os.path.exists(bpy.path.abspath(l.filepath))
           and not any(i.library == l for i in bpy.data.node_groups)]
print("[paths] %d links changed, still missing: %s" % (changed, missing))
if changed and not DRY:
    arch = os.path.join(root, "99_ARCHIVE") if root else here
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(blend, os.path.join(arch, "%s_prePathFix_%s.blend" % (os.path.splitext(os.path.basename(blend))[0], stamp)))
    bpy.ops.wm.save_mainfile(relative_remap=True, compress=True)
    print("[paths] saved", blend)
