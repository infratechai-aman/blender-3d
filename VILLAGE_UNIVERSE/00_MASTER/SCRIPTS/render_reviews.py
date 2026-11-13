"""Render review views from MASTER_WORLD.blend.

  blender -b MASTER_WORLD.blend --python render_reviews.py -- [--quick] [--use-cycles] [--samples N]
          [--out FOLDER_NAME] [--only CAM_A,CAM_B]

Default: EEVEE blockout set into 10_EXPORTS/REVIEWS/G1_BLOCKOUT_<version>/.
--use-cycles renders every camera in LIGHTING_CAMERAS with Cycles + OptiX (integrated reviews).
"""
import os
import sys

import bpy

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import config_layout as C  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default=None):
    return args[args.index(name) + 1] if name in args else default


quick = "--quick" in args
cycles = "--use-cycles" in args
only = arg("--only")
only = set(only.split(",")) if only else None
out_name = arg("--out", "G1_BLOCKOUT_%s" % C.BLOCKOUT_VERSION)
out_dir = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", out_name)
os.makedirs(out_dir, exist_ok=True)

sc = bpy.context.scene
sc.render.image_settings.file_format = "PNG"
if cycles:
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = d.type == "CUDA"
    sc.cycles.device = "CPU" if "--cpu" in args else "GPU"   # --cpu: 4 GB cards run out of memory on the full village
    sc.cycles.samples = int(arg("--samples", 48 if quick else 192))
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 8
    sc.cycles.volume_bounces = 1
else:
    try:
        sc.eevee.taa_render_samples = 16 if quick else 48
    except Exception:
        pass
labels = bpy.data.collections["REVIEW_LABELS"]

all_cams = [o.name for o in bpy.data.collections["LIGHTING_CAMERAS"].objects if o.type == "CAMERA"]
cams = all_cams if (cycles or only) else list(C.CAMERAS)
for name in cams:
    if only and name not in only:
        continue
    sc.camera = bpy.data.objects[name]
    is_plan = name == "CAM_TopDown_Plan"
    labels.hide_render = not is_plan
    if name.startswith("CAM_TopDown"):
        sc.render.resolution_x = sc.render.resolution_y = 1400 if quick else 2000
    else:
        sc.render.resolution_x, sc.render.resolution_y = (1280, 720) if quick else (1920, 1080)
    sc.render.filepath = os.path.join(out_dir, name + ".png")
    bpy.ops.render.render(write_still=True)
    print("[render] wrote", sc.render.filepath)
labels.hide_render = True
