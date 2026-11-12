"""
HERO BACKDROP: rocky sandstone hills with a waterfall (Amaltaspur, north of the village).

  blender -b --factory-startup --python hero_mountains.py -- [--render] [--quick] [--only CAM]

Output: 01_ENVIRONMENT/LANDSCAPE/LIB_Mountains_Waterfall.blend
  AST_Mountain_Massif_A   terrain mesh 900 x 520 m (origin = foot of the waterfall's plunge pool, falls face -Y)
  AST_Waterfall_A         cascade curtain + plunge pool + foam + mist
Vegetation uses LOD1 trees linked from LIB_Trees.blend.
"""
import datetime
import math
import os
import random
import shutil
import sys

import bpy
from mathutils import Vector, noise

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import hero_lib as H  # noqa: E402
from hero_lib import HB  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Mountains_Waterfall.blend")
TREES_BLEND = os.path.join(ROOT, "01_ENVIRONMENT", "LANDSCAPE", "LIB_Trees.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "PH1B_MOUNTAINS_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
POOL = (0.0, 42.0)


def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def fbm(x, y, f, oct=5, off=0.0):
    out = np.zeros_like(x)
    amp, tot = 1.0, 0.0
    for o in range(oct):
        out += amp * np.array([noise.noise(Vector((a * f, b * f, off + o * 7.3))) for a, b in zip(x.ravel(), y.ravel())]).reshape(x.shape)
        tot += amp
        amp *= 0.5
        f *= 2.03
    return out / tot


def channel_x(y):
    return 8.0 * np.sin(np.asarray(y) * 0.02)


PEAKS = [(-250, 300, 150, 120), (-120, 250, 235, 110), (10, 330, 255, 120), (150, 270, 205, 105),
         (300, 320, 175, 125), (430, 260, 120, 110), (-400, 230, 110, 100), (70, 190, 120, 70)]


def ridged(X, Y, f):
    return np.array([noise.ridged_multi_fractal(Vector((a * f, b * f, 3.1)), 1.0, 2.0, 5, 1.0, 2.0)
                     for a, b in zip(X.ravel(), Y.ravel())]).reshape(X.shape)


def height(X, Y):
    """Irregular sandstone massif: several peaks, ridged erosion, strata cliffs only in some regions."""
    warp = fbm(X, Y, 0.003, 3, 9.0)
    t = ss(-10.0, 230.0, Y + 60.0 * warp)
    peaks = np.zeros_like(X)
    for px, py, ph, pr in PEAKS:
        peaks = np.maximum(peaks, ph * np.exp(-(((X - px) / (pr * 1.6)) ** 2 + ((Y - py) / pr) ** 2)))
    R = ridged(X, Y, 0.0042)
    R = (R - 0.2) / 1.6
    base = (peaks * (0.55 + 0.45 * np.clip(R, 0, 1.2)) + 35.0 * t) * t
    step = 26.0 + 16.0 * (fbm(X, Y, 0.002, 2, 4.0) + 0.5)
    q = (base + 16.0 * fbm(X, Y, 0.009, 2, 21.0)) / step                # warped so cliff bands wander
    fq = q - np.floor(q)
    terr = (np.floor(q) + ss(0.55, 0.97, fq)) * step                   # strata: cliffs + ledges
    wt = 0.12 * ss(-0.15, 0.3, fbm(X, Y, 0.003, 2, 13.0))           # base hills stay soft; rock comes from outcrops
    h = base * (1 - wt) + terr * wt
    h += 7.0 * fbm(X, Y, 0.03, 3, 5.0) * t
    d = np.abs(X - channel_x(Y))
    h -= 22.0 * np.exp(-(d / 11.0) ** 2) * ss(45.0, 130.0, Y)          # gorge for the falls
    pd = np.hypot(X - POOL[0], (Y - POOL[1]) * 1.3)
    h = np.where(pd < 26, np.minimum(h, -2.6 + 3.2 * ss(10, 26, pd)), h)  # plunge pool bowl
    flat = 0.4 * np.sin(X * 0.05) * np.cos(Y * 0.04)
    return np.where(Y < 0, flat + 0.0, h * ss(-5.0, 25.0, Y) + flat * (1 - ss(-5.0, 25.0, Y)))


def rock_chunk(seed, sx, sy, sz):
    """Big stylised sandstone boulder/mesa: lumpy, flat-topped, stepped strata, buried base."""
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=4, radius=1.0)
    off = Vector((seed * 3.7, seed * 1.3, seed * 2.1))
    for v in bm.verts:
        p = v.co.copy()
        d = 1.0 + 0.3 * noise.noise(p * 0.9 + off) + 0.14 * noise.noise(p * 2.6 + off) - 0.07 * abs(noise.noise(p * 5.0 + off)) + 0.03 * noise.noise(p * 11 + off)
        p = p * d
        z = p.z
        if z > 0.5:
            z = 0.5 + (z - 0.5) * 0.22                       # flat-ish tops
        z += 0.045 * math.sin(z * 14.0 + seed) + 0.02 * math.sin(z * 37.0)   # strata steps
        v.co = Vector((p.x * sx, p.y * sy, z * sz))
    me = bpy.data.meshes.new("ME_Rock_Outcrop_%02d" % seed)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return me


def build_outcrops(coll, mat):
    rng = random.Random(29)
    meshes = None
    spots = []
    for side in (-1, 1):                                       # cliff walls flanking the falls
        for k, y in enumerate((70, 115, 160, 205)):
            spots.append((channel_x(y) + side * rng.uniform(27, 34), y, rng.uniform(22, 30), rng.uniform(16, 22), rng.uniform(34, 48)))
    for px, py, ph, pr in PEAKS:                               # crowns on every peak
        for _ in range(4):
            spots.append((px + rng.uniform(-0.6, 0.6) * pr, py + rng.uniform(-0.4, 0.4) * pr,
                          rng.uniform(20, 42), rng.uniform(15, 28), rng.uniform(22, 46)))
    while len(spots) < 72:                                     # scattered mid-slope outcrops
        x, y = rng.uniform(-430, 430), rng.uniform(80, 360)
        if abs(x - channel_x(y)) < 30:
            continue
        spots.append((x, y, rng.uniform(8, 20), rng.uniform(6, 14), rng.uniform(8, 20)))
    for i, (x, y, sx, sy, sz) in enumerate(spots):
        z = float(height(np.array([x]), np.array([y]))[0])
        me = rock_chunk(i + 1, sx, sy, sz)                    # real-size mesh so textures read in metres
        me.materials.append(mat)
        o = bpy.data.objects.new("GEO_Rock_Outcrop_%03d" % i, me)
        o.location = (x, y, z - 0.3 * sz)
        o.rotation_euler = (rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), rng.uniform(0, 6.28))
        coll.objects.link(o)
    print("[mtn] %d sandstone outcrops" % len(spots))


def rock_material(name="MAT_Rock_Sandstone_Strata", vmin=0.5, vmax=0.7):
    m, t = H._mat(name, "#A86A48")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=obj)
    warp = t.noise(obj, 0.02, 3.0, 0.5)
    zz = t.math("ADD", sx.outputs["Z"], t.math("MULTIPLY", warp.outputs["Fac"], 14.0))
    # rock: mottled sandstone + vertical fracture blocks (voronoi stretched along Z), faint strata only
    n = t.noise(obj, 0.05, 6.0, 0.6)
    rock = t.ramp(n.outputs["Fac"], [(0.3, H.hex_lin("#8A5A44")), (0.5, H.hex_lin("#A9734F")), (0.72, H.hex_lin("#C08E68"))])
    mp = t.n("ShaderNodeMapping", Vector=obj, Scale=(0.45, 0.45, 0.14))
    vor = t.n("ShaderNodeTexVoronoi", Vector=mp.outputs[0], Scale=1.0)
    vor.feature = "DISTANCE_TO_EDGE"
    crack = t.ramp(vor.outputs["Distance"], [(0.0, (1, 1, 1, 1)), (0.035, (0, 0, 0, 1))])
    crackf = t.n("ShaderNodeSeparateColor", Color=crack).outputs[0]
    rock = t.mix(t.math("MULTIPLY", crackf, 0.35), rock, H.hex_lin("#5A3A2E"))
    band = t.n("ShaderNodeTexWave", Vector=t.n("ShaderNodeCombineXYZ", Z=zz).outputs[0], Scale=0.012,
               Distortion=9.0, Detail=4.0)
    band.wave_type = "BANDS"
    band.bands_direction = "Z"
    rock = t.mix(t.math("MULTIPLY", band.outputs["Fac"], 0.18), rock, H.hex_lin("#D2A27A"))
    geo = t.n("ShaderNodeNewGeometry")
    nz = t.n("ShaderNodeSeparateXYZ", Vector=geo.outputs["Normal"]).outputs["Z"]
    gn = t.noise(obj, 0.08, 4.0, 0.6)
    veg = t.n("ShaderNodeMapRange", Value=t.math("ADD", nz, t.math("MULTIPLY", t.math("SUBTRACT", gn.outputs["Fac"], 0.5), 0.25)),
              **{"From Min": vmin, "From Max": vmax, "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
    alt = t.n("ShaderNodeMapRange", Value=sx.outputs["Z"], **{"From Min": 170.0, "From Max": 250.0,
                                                               "To Min": 1.0, "To Max": 0.45}).outputs["Result"]
    vf = t.math("MULTIPLY", veg, alt)
    green = t.ramp(gn.outputs["Fac"], [(0.25, H.hex_lin("#3C5A26")), (0.5, H.hex_lin("#587A30")), (0.75, H.hex_lin("#7E8A45"))])
    col = t.mix(vf, rock, green)
    fine = t.noise(obj, 1.6, 8.0, 0.65)
    h = t.math("ADD", t.math("MULTIPLY", crackf, -0.6), fine.outputs["Fac"])
    t.finish(col, 0.9, t.bump(h, 0.7, 0.8))
    return m


def falls_material():
    m, t = H._mat("MAT_Water_Waterfall", "#E8F2F0")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    mp = t.n("ShaderNodeMapping", Vector=obj, Scale=(2.5, 2.5, 0.05))
    s = t.noise(mp.outputs[0], 3.0, 6.0, 0.6)
    streak = t.ramp(s.outputs["Fac"], [(0.35, (0, 0, 0, 1)), (0.65, (1, 1, 1, 1))])
    fac = t.n("ShaderNodeSeparateColor", Color=streak).outputs[0]
    b = t.n("ShaderNodeBsdfPrincipled")
    t.inp(b, "Base Color").default_value = H.hex_lin("#EAF4F2")
    t.inp(b, "Roughness").default_value = 0.25
    t.inp(b, "Emission Color").default_value = H.hex_lin("#DDEEEE")
    t.inp(b, "Emission Strength").default_value = 0.25
    tr = t.n("ShaderNodeBsdfTransparent")
    mx = t.n("ShaderNodeMixShader")
    t.link(t.math("ADD", t.math("MULTIPLY", fac, 0.55), 0.2), mx.inputs[0])
    t.link(tr.outputs[0], mx.inputs[1])
    t.link(b.outputs[0], mx.inputs[2])
    t.link(mx.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def mist_material():
    m, t = H._mat("MAT_Volume_Mist", "#FFFFFF")
    v = t.n("ShaderNodeVolumePrincipled")
    t.inp(v, "Color").default_value = H.hex_lin("#F2F6F6")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n = t.noise(obj, 0.15, 3.0)
    g = t.n("ShaderNodeTexGradient", Vector=obj)
    g.gradient_type = "SPHERICAL"
    dens = t.math("MULTIPLY", t.math("MULTIPLY", g.outputs["Fac"], n.outputs["Fac"]), 0.12)
    t.link(dens, t.inp(v, "Density"))
    t.link(v.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Volume"])
    return m


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "LIB_Mountains_Waterfall"
    sc.unit_settings.system = "METRIC"
    cm = bpy.data.collections.new("AST_Mountain_Massif_A")
    cw = bpy.data.collections.new("AST_Waterfall_A")
    st = bpy.data.collections.new("STAGE")
    for c in (cm, cw, st):
        sc.collection.children.link(c)

    # ---------------- massif
    xs = np.arange(-460.0, 460.01, 2.5)
    ys = np.arange(-120.0, 520.01, 2.5)
    X, Y = np.meshgrid(xs, ys)
    Z = height(X, Y)
    nx, ny = len(xs), len(ys)
    idx = np.arange(nx * ny).reshape(ny, nx)
    f = np.stack([idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, 1:].ravel(), idx[1:, :-1].ravel()], 1)
    me = bpy.data.meshes.new("ME_Mountain_Massif_A")
    me.from_pydata(np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1).tolist(), [], f.tolist())
    me.materials.append(rock_material("MAT_Hill_Scrub_Earth", 0.3, 0.5))
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    cm.objects.link(bpy.data.objects.new("GEO_Mountain_Massif_A", me))
    build_outcrops(cm, rock_material("MAT_Rock_Sandstone_Outcrop", 0.78, 0.9))
    print("[mtn] massif %d x %d verts, max height %.0f m" % (nx, ny, Z.max()))

    # ---------------- waterfall curtain following the gorge
    fm = falls_material()
    hb = HB()
    yy = np.arange(POOL[1] + 6.0, 340.0, 1.0)[::-1]
    cx = channel_x(yy)
    zc = height(cx, yy) + 0.5
    zc = np.minimum.accumulate(zc)                                    # water only flows downhill
    foam_pts = []
    for stream, (dx, wmul) in enumerate(((0.0, 1.0), (2.6, 0.45))):
        v, fcs = [], []
        for i, (y, x, z) in enumerate(zip(yy, cx, zc)):
            w = (1.4 + 0.9 * math.sin(i * 0.11 + stream) + 0.5 * math.sin(i * 0.37)) * wmul
            for k, sx in enumerate((-1, -0.3, 0.3, 1)):
                bulge = 0.35 if abs(sx) < 0.5 else 0.0
                v.append((x + dx + sx * w, y - 0.9 - bulge, z + 0.05 * math.sin(i * 0.9 + k)))
            if stream == 0 and i > 0 and zc[i - 1] - z > 2.5 and (not foam_pts or foam_pts[-1][1] - y > 4):
                foam_pts.append((x, y - 1.0, z))
        for i in range(len(yy) - 1):
            for k in range(3):
                a = 4 * i + k
                fcs.append((a, a + 1, a + 5, a + 4))
        hb.add(v, fcs, fm)
    o = bpy.data.objects.new("GEO_Waterfall_Curtain", hb.to_mesh("ME_Waterfall_Curtain", recalc=False))
    cw.objects.link(o)
    o.data.polygons.foreach_set("use_smooth", [True] * len(o.data.polygons))
    # plunge pool, foam, mist
    hb = HB()
    hb.frustum(POOL[0], POOL[1], -3.0, -0.6, 24.0, 24.0, 48, H.mat_water())
    pool = bpy.data.objects.new("GEO_Waterfall_PlungePool", hb.to_mesh("ME_PlungePool"))
    cw.objects.link(pool)
    foam = H.mat_simple("MAT_Water_Foam", "#F4F8F6", 0.4, emission=H.hex_lin("#FFFFFF"), estr=0.15)
    hb = HB()
    rng = random.Random(3)
    for _ in range(60):
        a = rng.uniform(0, 6.28)
        r = rng.uniform(0, 7.0)
        hb.ellipsoid(POOL[0] + r * math.cos(a), POOL[1] + 6 + r * math.sin(a) * 0.6, -0.6,
                     rng.uniform(0.6, 1.6), rng.uniform(0.6, 1.4), rng.uniform(0.15, 0.45), foam, 10, 6)
    for (x, y, z) in foam_pts:                                          # white water at each ledge drop
        for _ in range(8):
            hb.ellipsoid(x + rng.uniform(-1.6, 1.6), y + rng.uniform(-0.6, 0.4), z + rng.uniform(-0.3, 0.6),
                         rng.uniform(0.4, 1.0), rng.uniform(0.3, 0.7), rng.uniform(0.3, 0.6), foam, 8, 5)
    print("[mtn] waterfall: %d cascade drops with foam" % len(foam_pts))
    fo = bpy.data.objects.new("GEO_Waterfall_Foam", hb.to_mesh("ME_Waterfall_Foam"))
    fo.data.polygons.foreach_set("use_smooth", [True] * len(fo.data.polygons))
    cw.objects.link(fo)
    hb = HB()
    hb.ellipsoid(0, 0, 0, 1, 1, 1, mist_material(), 16, 10)
    mist = bpy.data.objects.new("VOL_Waterfall_Mist", hb.to_mesh("ME_Mist"))
    mist.location = (POOL[0], POOL[1] + 6, 6.0)
    mist.scale = (22, 14, 14)
    cw.objects.link(mist)
    # outflow stream toward the village (south, -Y)
    hb = HB()
    sm = H.mat_water("MAT_Water_Stream")
    pts = [(POOL[0] + 6 * math.sin(t_ * 0.05), t_) for t_ in np.arange(POOL[1] - 20, -120, -2.0)]
    v, fcs = [], []
    for i, (x, y) in enumerate(pts):
        w = 9.0
        v += [(x - w, y, -0.55), (x + w, y, -0.55)]
    for i in range(len(pts) - 1):
        a = 2 * i
        fcs.append((a, a + 2, a + 3, a + 1))
    hb.add(v, fcs, sm)
    so = bpy.data.objects.new("GEO_Waterfall_Stream", hb.to_mesh("ME_Stream", recalc=False))
    st.objects.link(so)

    # ---------------- vegetation on gentle slopes (LOD1 trees)
    if os.path.exists(TREES_BLEND):
        want = ["VEG_Tree_Neem_A_LOD1", "VEG_Tree_Mango_A_LOD1", "VEG_Tree_Peepal_A_LOD1", "VEG_Tree_Palm_A_LOD1"]
        with bpy.data.libraries.load(TREES_BLEND, link=True) as (src, dst):
            dst.collections = [c for c in src.collections if c in want]
        T = [c for c in dst.collections]
        vr = random.Random(11)
        placed = 0
        tries = 0
        while placed < 2200 and tries < 60000:
            tries += 1
            x = vr.uniform(-440, 440)
            y = vr.uniform(20, 330) if vr.random() < 0.75 else vr.uniform(-100, 20)
            if abs(x - channel_x(y)) < 16 and y > 20:
                continue
            if math.hypot(x - POOL[0], (y - POOL[1]) * 1.3) < 30:
                continue
            z = float(height(np.array([x]), np.array([y]))[0])
            gx = float(height(np.array([x + 2.0]), np.array([y]))[0]) - z
            gy = float(height(np.array([x]), np.array([y + 2.0]))[0]) - z
            slope = math.hypot(gx, gy) / 2.0
            if slope > 0.7 or z > 215:
                continue
            if y < -20 and vr.random() < 0.7:
                continue
            e = bpy.data.objects.new("INST_MtnTree_%03d" % placed, None)
            e.instance_type = "COLLECTION"
            e.instance_collection = T[vr.randrange(len(T)) if y < 10 else vr.choice([0, 1, 2]) % len(T)]
            e.location = (x, y, z - 0.2)
            e.rotation_euler = (0, 0, vr.uniform(0, 6.28))
            s = vr.uniform(0.7, 1.25) * (0.6 if z > 80 else 1.0)
            e.scale = (s, s, s)
            cm.objects.link(e)
            placed += 1
        print("[mtn] %d trees on slopes and ledges" % placed)

    # ---------------- stage
    gm = H.mat_ground()
    hb = HB()
    hb.add([(-2000, -1500, -0.3), (2000, -1500, -0.3), (2000, -110, -0.3), (-2000, -110, -0.3)], [(0, 1, 2, 3)], gm)
    st.objects.link(bpy.data.objects.new("STG_Ground", hb.to_mesh("ME_STG_Ground", recalc=False)))
    w = bpy.data.worlds.new("WLD_Day_Clear")
    sc.world = w
    t = H.NT(w)
    tc = t.n("ShaderNodeTexCoord")
    z = t.n("ShaderNodeSeparateXYZ", Vector=tc.outputs["Generated"]).outputs["Z"]
    col = t.ramp(z, [(0.0, H.hex_lin("#F2DCB8")), (0.12, H.hex_lin("#B9D2E6")), (0.45, H.hex_lin("#5E93CC"))])
    bg = t.n("ShaderNodeBackground", Color=col, Strength=1.0)
    t.link(bg.outputs[0], t.n("ShaderNodeOutputWorld").inputs["Surface"])
    sd = bpy.data.lights.new("LGT_Sun_Afternoon", "SUN")
    sd.energy, sd.color, sd.angle = 4.5, (1.0, 0.9, 0.77), math.radians(1.5)
    sun = bpy.data.objects.new("LGT_Sun_Afternoon", sd)
    sun.rotation_euler = (math.radians(50), 0.0, math.radians(-30))
    st.objects.link(sun)
    cams = {
        "CAM_Mountains_Wide":   ((40.0, -420.0, 45.0), (0.0, 250.0, 95.0), 32),
        "CAM_Waterfall_Medium": ((70.0, -95.0, 12.0), (0.0, 120.0, 55.0), 30),
        "CAM_Waterfall_Pool":   ((22.0, -12.0, 3.0), (0.0, 70.0, 25.0), 24),
    }
    for name, (pos, tgt, lens) in cams.items():
        cd = bpy.data.cameras.new(name)
        cd.lens = lens
        cd.clip_end = 6000
        co = bpy.data.objects.new(name, cd)
        co.location = pos
        co.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        st.objects.link(co)
    sc.camera = bpy.data.objects["CAM_Mountains_Wide"]
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
    except Exception as ex:
        print("[mtn] GPU setup failed:", ex)
    quick = "--quick" in ARGS
    sc.cycles.samples = 64 if quick else 256
    sc.cycles.use_denoising = True
    sc.cycles.volume_bounces = 1
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = (1280, 720) if quick else (1920, 1080)
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "LIB_Mountains_Waterfall_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[mtn] saved", OUT_BLEND)
    if "--render" in ARGS:
        os.makedirs(OUT_REVIEW, exist_ok=True)
        only = ARGS[ARGS.index("--only") + 1] if "--only" in ARGS else None
        for c in cams:
            if only and c != only:
                continue
            sc.camera = bpy.data.objects[c]
            sc.render.filepath = os.path.join(OUT_REVIEW, c + ".png")
            bpy.ops.render.render(write_still=True)
            print("[mtn] rendered", c)


main()
