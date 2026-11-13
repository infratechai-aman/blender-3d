"""Side-by-side before|after comparison (same camera).  Both images are scaled to the same height.

  blender -b --factory-startup --python make_compare.py -- BEFORE.png AFTER.png OUT.png [HEIGHT]
"""
import sys

import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
before, after, out = a[0], a[1], a[2]
H = int(a[3]) if len(a) > 3 else 720


def load(path):
    im = bpy.data.images.load(path)
    w, h = im.size
    px = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)
    if h != H:                                     # nearest-neighbour resample to height H
        nw = int(round(w * H / h))
        ys = (np.arange(H) * h / H).astype(int)
        xs = (np.arange(nw) * w / nw).astype(int)
        px = px[ys][:, xs]
    return px


A, B = load(before), load(after)
gap = np.ones((H, 12, 4), np.float32)
img = np.concatenate([A, gap, B], axis=1)
h, w = img.shape[:2]
o = bpy.data.images.new("compare", w, h, alpha=True)
o.pixels.foreach_set(img.ravel())
o.filepath_raw = out
o.file_format = "PNG"
o.save()
print("[compare] wrote", out, w, "x", h)
