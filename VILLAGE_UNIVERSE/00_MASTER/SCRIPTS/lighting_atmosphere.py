"""
BATCH 1 - cinematic lighting + atmosphere for MASTER_WORLD (non-destructive: replaces only the world, the sun and
the compositor; geometry untouched).

  apply to the saved master (archives a checkpoint first) and render before/after comparisons:
    blender -b MASTER_WORLD.blend --python lighting_atmosphere.py -- [--preset morning|golden|dusk] [--render]
                                                                       [--only CAM_A,CAM_B] [--no-save]
  from build_master_v2:  import lighting_atmosphere as LA; LA.apply(bpy.context.scene, "morning")

Layers
  sky        physical Multiple-Scattering sky (sun disc off) + procedural cumulus band; strength balanced to the sun
  sun        low, warm, soft (1.6-3 deg disc) -> long shadows, readable form; cool sky fill from the world
  haze       mist pass -> aerial perspective (distance fades to a warm-blue haze; mountains layer back)
  grade      gentle lift/gain warm-cool split, soft bloom on highlights, light vignette
  EEVEE      raytracing on, fast GI, soft shadows, higher shadow resolution
Presets: morning (default look), golden (late afternoon), dusk (blue hour, lamps read).
"""
import math
import os
import sys

import bpy

PRESETS = {
    #           sun elev, sun azimuth(deg from +Y, clockwise), sun energy, sun colour, sun angle, sky strength,
    #           haze colour, haze amount, grade gain, grade lift, cloud cover, exposure
    "morning": dict(elev=31.0, azim=118.0, energy=5.0, col=(1.0, 0.89, 0.76), angle=1.8, sky=0.085,
                    haze=(0.70, 0.77, 0.87), haze_amt=0.26, gain=(1.05, 1.01, 0.95), lift=(1.0, 1.0, 1.015),
                    cloud=0.48, exposure=0.3),
    "golden": dict(elev=13.0, azim=-62.0, energy=5.2, col=(1.0, 0.72, 0.45), angle=2.6, sky=0.07,
                   haze=(0.93, 0.78, 0.62), haze_amt=0.62, gain=(1.07, 1.0, 0.9), lift=(1.0, 0.99, 1.02),
                   cloud=0.52, exposure=0.25),
    "dusk": dict(elev=2.5, azim=-70.0, energy=1.2, col=(1.0, 0.55, 0.32), angle=3.0, sky=0.12,
                 haze=(0.42, 0.45, 0.62), haze_amt=0.7, gain=(0.98, 0.99, 1.06), lift=(0.99, 1.0, 1.04),
                 cloud=0.45, exposure=0.6, practicals=True),
    # storybook day (user reference board 2): low warm late-afternoon sun from the west, saturated blue sky,
    # small fair-weather cumulus, crisp long shadows, light warm grade
    "storybook": dict(elev=18.0, azim=-94.0, energy=6.0, col=(1.0, 0.74, 0.48), angle=1.2, sky=0.11,
                      haze=(0.78, 0.83, 0.9), haze_amt=0.12, gain=(1.08, 1.0, 0.9), lift=(1.0, 1.0, 1.03),
                      cloud=0.42, exposure=0.35),
    # moonlit night v2 (user night brief): moon in frame upper-right of CAM_Chowk_Close, cool rim on canopies,
    # warm practicals + chowk rig (trunk uplights, root accents, lantern pools, cool canopy top) + window glow
    "night": dict(elev=17.0, azim=61.0, energy=0.14, col=(0.6, 0.72, 1.0), angle=2.0, sky=0.42,
                  haze=(0.04, 0.06, 0.11), haze_amt=0.22, gain=(1.03, 1.0, 0.98), lift=(1.0, 1.01, 1.04),
                  cloud=0.35, exposure=1.35, night=True, practicals=True, lamp_gain=4.0, chowk_rig=True,
                  windows=True),
}

# practical lights per lamp asset: (local offset, watts, radius, glowing-bulb radius, casts shadow)
PRACTICALS = {
    "AST_StreetLight_Pole_A": ((0.0, -1.635, 6.6), 260.0, 0.12, 0.09, True),
    "AST_LampPost_Lantern_A": ((0.0, 0.0, 2.975), 70.0, 0.06, 0.07, True),
    "AST_WallLantern_A": ((0.0, -0.4, -0.2), 30.0, 0.04, 0.05, False),
    "AST_House_Common_A": ((0.9, -3.0, 2.45), 45.0, 0.05, 0.05, False),
}


def practicals(scene, on, gain=1.0):
    """Warm practical lights at every lamp-asset instance (+ chowk banyan lanterns and diyas) with glowing bulbs."""
    import json

    import bmesh
    from mathutils import Matrix, Vector
    coll = bpy.data.collections.get("FX_NIGHT_LIGHTS")
    if coll is None:
        coll = bpy.data.collections.new("FX_NIGHT_LIGHTS")
        scene.collection.children.link(coll)
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    pts = []
    for o in scene.objects:
        if o.instance_type != "COLLECTION" or o.instance_collection is None:
            continue
        name = o.instance_collection.name
        if name.startswith("VEG_Tree_Banyan_Chowk_Hero"):          # also the _BAKED copy used in the master
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "01_ENVIRONMENT", "LANDSCAPE",
                                "LIB_Hero_Banyan_lanterns.json")
            try:
                J = json.load(open(path))
            except Exception:
                J = {"lanterns": [], "diyas": []}
            pts += [(o.matrix_world @ Vector(q), 90.0, 0.08, 0.09, True) for q in J["lanterns"]]
            pts += [(o.matrix_world @ Vector(q), 4.0, 0.02, 0.018, False) for q in J["diyas"]]
            continue
        own = o.instance_collection.get("night_lights")
        if own:                                        # buildings carry their own lamp list: [x, y, z(, watts)]
            for q in own:
                q = list(q)
                pts.append((o.matrix_world @ Vector(q[:3]), q[3] if len(q) > 3 else 30.0, 0.05, 0.045, False))
            continue
        spec = PRACTICALS.get(name)
        if spec:
            off, wts, rad, bulb, shd = spec
            pts.append((o.matrix_world @ Vector(off), wts, rad, bulb, shd))
    glow = bpy.data.materials.get("MAT_Night_Bulb_Glow")
    if glow is None:
        glow = bpy.data.materials.new("MAT_Night_Bulb_Glow")
        glow.use_nodes = True
        nt = glow.node_tree
        _nodes_clear(nt)
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (1.0, 0.78, 0.48, 1)
        em.inputs["Strength"].default_value = 60.0
        nt.links.new(em.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    bm = bmesh.new()
    for k, (p, wts, rad, bulb, shd) in enumerate(pts):
        ld = bpy.data.lights.new("LGT_Practical_%03d" % k, "POINT")
        ld.energy = wts * gain
        ld.color = (1.0, 0.7, 0.4)
        ld.shadow_soft_size = rad
        ld.use_shadow = shd
        lo = bpy.data.objects.new("LGT_Practical_%03d" % k, ld)
        lo.location = p
        coll.objects.link(lo)
        bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=bulb, matrix=Matrix.Translation(p))
    me = bpy.data.meshes.new("ME_Night_Bulbs")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(glow)
    bo = bpy.data.objects.new("GEO_Night_Bulbs", me)
    bo.visible_shadow = False
    coll.objects.link(bo)
    coll.hide_render = not on
    coll.hide_viewport = not on
    print("[light] practicals: %d lights (%s)" % (len(pts), "on" if on else "off"))


def _light(coll, name, kind, loc, energy, col, size=0.1, aim=None, spot=None, blend=0.6, shadow=True):
    from mathutils import Vector
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = col
    ld.use_shadow = shadow
    if kind == "AREA":
        ld.size = size
    else:
        ld.shadow_soft_size = size
    if kind == "SPOT":
        ld.spot_size = math.radians(spot or 60.0)
        ld.spot_blend = blend
    o = bpy.data.objects.new(name, ld)
    o.location = loc
    if aim is not None:
        o.rotation_euler = (Vector(aim) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(o)
    return o


def chowk_night_rig(scene, on, gain=1.0):
    """Night brief for the Village Chowk (lighting only, geometry untouched):
    warm amber uplights on the banyan trunk + root accents, cool moonlight wash on the upper canopy,
    warm light pools under every chowk lantern, and warm window glow on selected buildings village-wide."""
    import random

    import bmesh
    from mathutils import Matrix, Vector
    coll = bpy.data.collections.get("FX_NIGHT_CHOWK")
    if coll is None:
        coll = bpy.data.collections.new("FX_NIGHT_CHOWK")
        scene.collection.children.link(coll)
    for o in list(coll.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    AMBER, WARM, COOL = (1.0, 0.56, 0.26), (1.0, 0.68, 0.38), (0.55, 0.68, 1.0)
    ban = next((o for o in scene.objects if o.instance_type == "COLLECTION" and o.instance_collection
                and o.instance_collection.name.startswith("VEG_Tree_Banyan_Chowk_Hero")), None)
    z0 = ban.location.z if ban else 1.56
    top = z0                                                 # instance origin sits on the chabutra top
    n = 0
    # 1 warm amber uplights grazing the trunk from the platform edge
    for k in range(6):
        a = 2 * math.pi * k / 6 + 0.3
        p = (5.8 * math.cos(a), 5.8 * math.sin(a), top + 0.3)
        _light(coll, "LGT_Chowk_TrunkUp_%d" % k, "SPOT", p, 900.0 * gain, AMBER, 0.25,
               aim=(0.0, 0.0, top + 5.0), spot=55, blend=0.85)
        n += 1
    # warm bounce up into the canopy underside (soft, from the platform)
    _light(coll, "LGT_Chowk_CanopyUnder", "AREA", (0.0, 0.0, top + 0.8), 16000.0 * gain, AMBER, 9.0, aim=(0.0, 0.0, top + 20.0))
    n += 1
    # 2 low root accents (small, warm, no shadow)
    for k in range(10):
        a = 2 * math.pi * k / 10
        r = 3.4 + 0.5 * (k % 2)
        _light(coll, "LGT_Chowk_Root_%d" % k, "POINT", (r * math.cos(a), r * math.sin(a), top + 0.35),
               45.0 * gain, AMBER, 0.15, shadow=False)
        n += 1
    # 3 cool moon wash on the upper canopy (from high above, slightly toward the moon side)
    # cone sized to the ~19 m canopy radius: only the leaves catch it, the paving outside stays dark
    _light(coll, "LGT_Chowk_CanopyMoon", "SPOT", (4.0, 6.0, z0 + 60.0), 60000.0, COOL, 3.0,
           aim=(0.0, 0.0, z0 + 14.0), spot=46, blend=0.35)
    n += 1
    # 4 warm pools on the paving under every lantern near the chowk
    for o in scene.objects:
        if o.instance_type == "COLLECTION" and o.instance_collection and \
                o.instance_collection.name == "AST_LampPost_Lantern_A" and o.location.length < 70.0:
            p = o.matrix_world @ Vector((0.0, 0.0, 2.95))     # inside the lantern; no shadow so the base plate can't block it
            _light(coll, "LGT_Chowk_Pool_%s" % o.name[-3:], "SPOT", p, 650.0 * gain, WARM, 0.08,
                   aim=(p.x, p.y, p.z - 3.0), spot=120, blend=1.0, shadow=False)
            n += 1
    # 5 warm windows: emissive panes on selected hero houses + interior glow in hero buildings
    glow = bpy.data.materials.get("MAT_Window_Night_Glow") or bpy.data.materials.new("MAT_Window_Night_Glow")
    glow.use_nodes = True
    nt = glow.node_tree
    _nodes_clear(nt)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1.0, 0.66, 0.34, 1)
    em.inputs["Strength"].default_value = 7.0
    nt.links.new(em.outputs[0], nt.nodes.new("ShaderNodeOutputMaterial").inputs["Surface"])
    bm = bmesh.new()
    rng = random.Random(7)
    nw = nb = 0
    for o in scene.objects:
        if o.instance_type != "COLLECTION" or o.instance_collection is None:
            continue
        cn = o.instance_collection.name
        if cn == "AST_House_Common_A" and rng.random() < 0.75:
            for wx in (-3.25, 3.35):                          # front windows (see hero_house_common OPENINGS)
                if rng.random() < 0.8:
                    M = o.matrix_world @ Matrix.Translation((wx, -1.95 + 0.26, 1.97)) @ Matrix.Rotation(math.pi / 2, 4, "X")
                    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5, matrix=M @ Matrix.Diagonal((0.82, 1.22, 1.0, 1.0)))
                    nw += 1
            _light(coll, "LGT_Window_%s" % o.name, "POINT", o.matrix_world @ Vector((0.0, -0.9, 2.0)), 40.0 * gain, WARM,
                   0.3, shadow=False)
            nb += 1
        elif cn.startswith(("AST_Shop", "AST_Panchayat", "AST_House_Middle", "AST_Haveli", "AST_House_Small",
                            "AST_Shop2", "AST_School")) and rng.random() < 0.85:
            _light(coll, "LGT_Interior_%s" % o.name, "POINT", o.matrix_world @ Vector((0.0, 0.0, 2.2)), 160.0 * gain,
                   WARM, 0.4, shadow=False)
            nb += 1
    me = bpy.data.meshes.new("ME_Window_Night_Glow")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(glow)
    wo = bpy.data.objects.new("GEO_Window_Night_Glow", me)
    wo.visible_shadow = False
    coll.objects.link(wo)
    coll.hide_render = not on
    coll.hide_viewport = not on
    print("[light] chowk night rig: %d rig lights, %d glowing windows, %d interior/window lights (%s)"
          % (n, nw, nb, "on" if on else "off"))


def build_night_world(P):
    """Moonlit sky: navy gradient with a faint horizon glow, stars, and a moon disc in the moonlight direction."""
    w = bpy.data.worlds.get("WLD_Night") or bpy.data.worlds.new("WLD_Night")
    w.use_nodes = True
    nt = w.node_tree
    _nodes_clear(nt)
    N, L = nt.nodes, nt.links
    out = N.new("ShaderNodeOutputWorld")
    bg = N.new("ShaderNodeBackground")
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = N.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.07, 0.1, 0.19, 1)          # deep navy, lighter at the horizon
    els[1].position, els[1].color = 0.55, (0.01, 0.017, 0.05, 1)
    els.new(0.1).color = (0.035, 0.055, 0.12, 1)
    L.new(sep.outputs["Z"], ramp.inputs[0])
    vor = N.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 260.0
    L.new(tc.outputs["Generated"], vor.inputs["Vector"])
    st = N.new("ShaderNodeMapRange")
    L.new(vor.outputs["Distance"], st.inputs["Value"])
    st.inputs["From Min"].default_value = 0.035
    st.inputs["From Max"].default_value = 0.0
    st.inputs["To Max"].default_value = 3.0
    stars = _math(N, L, "MULTIPLY", st.outputs["Result"], _math(N, L, "GREATER_THAN", sep.outputs["Z"], 0.08))
    dot = N.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    L.new(tc.outputs["Generated"], dot.inputs[0])
    dot.inputs[1].default_value = sun_dir(P["elev"], P["azim"])
    moon = N.new("ShaderNodeMapRange")
    L.new(dot.outputs["Value"], moon.inputs["Value"])
    moon.inputs["From Min"].default_value = 0.99925                    # ~2.2 deg storybook moon
    moon.inputs["From Max"].default_value = 0.99935
    moon.inputs["To Max"].default_value = 30.0
    mare = N.new("ShaderNodeTexNoise")                                  # soft maria on the disc
    mare.inputs["Scale"].default_value = 900.0
    L.new(tc.outputs["Generated"], mare.inputs["Vector"])
    mm = N.new("ShaderNodeMapRange")
    L.new(mare.outputs["Fac"], mm.inputs["Value"])
    mm.inputs["From Min"].default_value, mm.inputs["From Max"].default_value = 0.35, 0.7
    mm.inputs["To Min"].default_value, mm.inputs["To Max"].default_value = 0.72, 1.0
    moon_c = _math(N, L, "MULTIPLY", moon.outputs["Result"], mm.outputs["Result"])
    halo = N.new("ShaderNodeMapRange")
    L.new(dot.outputs["Value"], halo.inputs["Value"])
    halo.inputs["From Min"].default_value = 0.9965
    halo.inputs["From Max"].default_value = 0.9993
    halo.inputs["To Max"].default_value = 0.16
    # subtle drifting clouds, faintly lit, brighter around the moon
    zc = _math(N, L, "MAXIMUM", sep.outputs["Z"], 0.02)
    cxy = N.new("ShaderNodeCombineXYZ")
    L.new(_math(N, L, "MULTIPLY", _math(N, L, "DIVIDE", sep.outputs["X"], zc), 0.5), cxy.inputs[0])
    L.new(_math(N, L, "MULTIPLY", _math(N, L, "DIVIDE", sep.outputs["Y"], zc), 0.5), cxy.inputs[1])
    cn = N.new("ShaderNodeTexNoise")
    cn.inputs["Scale"].default_value = 1.6
    cn.inputs["Detail"].default_value = 7.0
    cn.inputs["Roughness"].default_value = 0.6
    L.new(cxy.outputs[0], cn.inputs["Vector"])
    cr = N.new("ShaderNodeMapRange")
    L.new(cn.outputs["Fac"], cr.inputs["Value"])
    cr.inputs["From Min"].default_value = 1.0 - P.get("cloud", 0.35)
    cr.inputs["From Max"].default_value = 1.0 - P.get("cloud", 0.35) + 0.22
    hz = N.new("ShaderNodeMapRange")
    L.new(sep.outputs["Z"], hz.inputs["Value"])
    hz.inputs["From Min"].default_value, hz.inputs["From Max"].default_value = 0.04, 0.2
    cmask = _math(N, L, "MULTIPLY", _math(N, L, "MULTIPLY", cr.outputs["Result"], hz.outputs["Result"]), 0.85)
    clit = _math(N, L, "ADD", 0.06, _math(N, L, "MULTIPLY", halo.outputs["Result"], 0.9))
    stars = _math(N, L, "MULTIPLY", stars, _math(N, L, "SUBTRACT", 1.0, cmask))      # clouds hide stars
    add = _math(N, L, "ADD", _math(N, L, "ADD", stars, moon_c), halo.outputs["Result"])
    add = _math(N, L, "ADD", add, _math(N, L, "MULTIPLY", cmask, clit))
    cm = N.new("ShaderNodeCombineColor")
    for i in range(3):
        L.new(add, cm.inputs[i])
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.blend_type = "ADD"
    _sock(mix, "Factor", "VALUE").default_value = 1.0
    L.new(ramp.outputs["Color"], _sock(mix, "A", "RGBA"))
    L.new(cm.outputs[0], _sock(mix, "B", "RGBA"))
    below = N.new("ShaderNodeMapRange")
    L.new(sep.outputs["Z"], below.inputs["Value"])
    below.inputs["From Min"].default_value = 0.02
    below.inputs["From Max"].default_value = -0.02
    floor = N.new("ShaderNodeMix")
    floor.data_type = "RGBA"
    L.new(below.outputs["Result"], _sock(floor, "Factor", "VALUE"))
    L.new(_out(mix, "Result", "RGBA"), _sock(floor, "A", "RGBA"))
    _sock(floor, "B", "RGBA").default_value = tuple(c / max(P["sky"], 1e-3) * 0.25 for c in P["haze"]) + (1.0,)
    L.new(_out(floor, "Result", "RGBA"), bg.inputs["Color"])
    bg.inputs["Strength"].default_value = P["sky"]
    L.new(bg.outputs[0], out.inputs["Surface"])
    w.mist_settings.start = 60.0
    w.mist_settings.depth = 1400.0
    w.mist_settings.falloff = "QUADRATIC"
    return w


def _nodes_clear(nt):
    for n in list(nt.nodes):
        nt.nodes.remove(n)


def _sock(node, name, kind=None):
    for s in node.inputs:
        if s.name == name and s.enabled and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


def _out(node, name, kind=None):
    for s in node.outputs:
        if s.name == name and s.enabled and (kind is None or s.type == kind):
            return s
    raise KeyError(name)


def sun_dir(elev, azim):
    e, a = math.radians(elev), math.radians(azim)
    return (math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e))       # direction TO the sun


def build_world(P):
    if P.get("night"):
        return build_night_world(P)
    w = bpy.data.worlds.get("WLD_Cinematic") or bpy.data.worlds.new("WLD_Cinematic")
    w.use_nodes = True
    nt = w.node_tree
    _nodes_clear(nt)
    N, L = nt.nodes, nt.links
    out = N.new("ShaderNodeOutputWorld")
    bg = N.new("ShaderNodeBackground")
    sky = N.new("ShaderNodeTexSky")
    for t in ("MULTIPLE_SCATTERING", "SINGLE_SCATTERING", "HOSEK_WILKIE"):
        try:
            sky.sky_type = t
            break
        except Exception:
            continue
    sky.sun_disc = False
    sky.sun_elevation = math.radians(max(P["elev"], 0.5))
    sky.sun_rotation = math.radians(-P["azim"] + 90.0)
    for nm, val in (("Air", 1.0), ("Air Density", 1.0), ("Aerosol Density", 1.6), ("Dust", 1.6), ("Ozone", 1.0),
                    ("Altitude", 200.0)):
        if nm in sky.inputs:
            try:
                sky.inputs[nm].default_value = val
            except Exception:
                pass
    # clouds: project the view direction onto a cloud plane, noise -> soft cumulus band above the horizon
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["Generated"], sep.inputs[0])
    m = lambda op, a, b: _math(N, L, op, a, b)  # noqa: E731
    zc = m("MAXIMUM", sep.outputs["Z"], 0.02)
    u = m("DIVIDE", sep.outputs["X"], zc)
    v = m("DIVIDE", sep.outputs["Y"], zc)
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(m("MULTIPLY", u, 0.55), comb.inputs[0])
    L.new(m("MULTIPLY", v, 0.55), comb.inputs[1])
    noise = N.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.7
    noise.inputs["Detail"].default_value = 7.0
    noise.inputs["Roughness"].default_value = 0.58
    L.new(comb.outputs[0], noise.inputs["Vector"])
    ramp = N.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 1.0 - P["cloud"]
    ramp.color_ramp.elements[1].position = 1.0 - P["cloud"] + 0.2
    L.new(noise.outputs["Fac"], ramp.inputs[0])
    horizon = N.new("ShaderNodeMapRange")
    L.new(sep.outputs["Z"], horizon.inputs["Value"])
    horizon.inputs["From Min"].default_value = 0.03
    horizon.inputs["From Max"].default_value = 0.22
    top = N.new("ShaderNodeMapRange")
    L.new(sep.outputs["Z"], top.inputs["Value"])
    top.inputs["From Min"].default_value = 0.75
    top.inputs["From Max"].default_value = 0.35
    cmask = m("MULTIPLY", m("MULTIPLY", ramp.outputs["Color"], horizon.outputs["Result"]), top.outputs["Result"])
    cmask = m("MULTIPLY", cmask, 0.85)
    shade = N.new("ShaderNodeTexNoise")
    shade.inputs["Scale"].default_value = 3.5
    L.new(comb.outputs[0], shade.inputs["Vector"])
    cramp = N.new("ShaderNodeValToRGB")
    sc = P["col"]
    cramp.color_ramp.elements[0].color = (0.78 * sc[0], 0.8 * sc[1], 0.86 * sc[2], 1)
    cramp.color_ramp.elements[1].color = (1.0 * sc[0], 0.98 * sc[1], 0.95 * sc[2], 1)
    L.new(shade.outputs["Fac"], cramp.inputs[0])
    cl_strength = N.new("ShaderNodeMix")
    cl_strength.data_type = "RGBA"
    _sock(cl_strength, "Factor", "VALUE").default_value = 1.0
    cl_strength.blend_type = "MULTIPLY"
    L.new(cramp.outputs["Color"], _sock(cl_strength, "A", "RGBA"))
    _sock(cl_strength, "B", "RGBA").default_value = (1.6,) * 3 + (1,)
    mix = N.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    L.new(cmask, _sock(mix, "Factor", "VALUE"))
    L.new(sky.outputs["Color"], _sock(mix, "A", "RGBA"))
    L.new(_out(cl_strength, "Result", "RGBA"), _sock(mix, "B", "RGBA"))
    # sky -> background, with a separate (brighter) value for camera rays so the sky reads blue but fill stays soft
    L.new(_out(mix, "Result", "RGBA"), bg.inputs["Color"])
    bg.inputs["Strength"].default_value = P["sky"]
    L.new(bg.outputs[0], out.inputs["Surface"])
    w.mist_settings.start = 220.0
    w.mist_settings.depth = 3200.0
    w.mist_settings.falloff = "QUADRATIC"
    return w


def _math(N, L, op, a, b):
    n = N.new("ShaderNodeMath")
    n.operation = op
    for i, x in enumerate((a, b)):
        if isinstance(x, (int, float)):
            n.inputs[i].default_value = x
        else:
            L.new(x, n.inputs[i])
    return n.outputs[0]


def build_sun(P, scene):
    for o in list(bpy.data.objects):
        if o.type == "LIGHT" and o.data.type == "SUN":
            bpy.data.objects.remove(o, do_unlink=True)
    ld = bpy.data.lights.new("LGT_Sun_Key", "SUN")
    ld.energy = P["energy"]
    ld.color = P["col"]
    ld.angle = math.radians(P["angle"])
    o = bpy.data.objects.new("LGT_Sun_Key", ld)
    d = sun_dir(P["elev"], P["azim"])
    from mathutils import Vector
    o.rotation_euler = Vector(d).to_track_quat("Z", "Y").to_euler()      # light points down its -Z
    coll = bpy.data.collections.get("LIGHTING_CAMERAS") or scene.collection
    coll.objects.link(o)
    return o


def build_compositor(P, scene):
    vl = bpy.context.view_layer
    vl.use_pass_mist = True
    vl.use_pass_environment = True
    scene.render.film_transparent = True
    ng = bpy.data.node_groups.get("COMP_Cinematic_Grade") or bpy.data.node_groups.new("COMP_Cinematic_Grade", "CompositorNodeTree")
    _nodes_clear(ng)
    if not any(i.in_out == "OUTPUT" for i in ng.interface.items_tree):
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    N, L = ng.nodes, ng.links
    rl = N.new("CompositorNodeRLayers")
    rl.scene = scene
    go = N.new("NodeGroupOutput")
    bpy.context.view_layer.update()
    img = rl.outputs["Image"]
    alpha = rl.outputs["Alpha"]
    mist = rl.outputs.get("Mist")
    env = rl.outputs.get("Env") or rl.outputs.get("Environment")
    if mist is not None:
        # aerial perspective on geometry only (alpha), then the sky goes back in behind it
        f = _math(N, L, "MULTIPLY", _math(N, L, "MULTIPLY", mist, P["haze_amt"]), alpha)
        hz = N.new("ShaderNodeMix")
        hz.data_type = "RGBA"
        L.new(f, _sock(hz, "Factor", "VALUE"))
        L.new(img, _sock(hz, "A", "RGBA"))
        _sock(hz, "B", "RGBA").default_value = (*P["haze"], 1.0)
        img = _out(hz, "Result", "RGBA")
    if env is not None:
        sk = N.new("ShaderNodeMix")
        sk.data_type = "RGBA"
        L.new(_math(N, L, "SUBTRACT", 1.0, alpha), _sock(sk, "Factor", "VALUE"))
        L.new(img, _sock(sk, "A", "RGBA"))
        L.new(env, _sock(sk, "B", "RGBA"))
        img = _out(sk, "Result", "RGBA")
    cb = N.new("CompositorNodeColorBalance")
    L.new(img, cb.inputs["Image"])
    try:
        for s in cb.inputs:
            if s.name == "Lift" and s.type == "RGBA":
                s.default_value = (*P["lift"], 1)
            if s.name == "Gain" and s.type == "RGBA":
                s.default_value = (*P["gain"], 1)
    except Exception as ex:
        print("[light] colour balance:", ex)
    img = cb.outputs["Image"]
    gl = N.new("CompositorNodeGlare")
    L.new(img, gl.inputs["Image"])
    for nm, val in (("Type", "Bloom"), ("Quality", "Medium"), ("Threshold", 1.2), ("Strength", 0.35), ("Size", 0.6)):
        if nm in gl.inputs:
            try:
                gl.inputs[nm].default_value = val
            except Exception:
                pass
    img = gl.outputs["Image"]
    # vignette
    em = N.new("CompositorNodeEllipseMask")
    for nm, val in (("Size", (0.92, 0.82)),):
        if nm in em.inputs:
            try:
                em.inputs[nm].default_value = val
            except Exception:
                pass
    bl = N.new("CompositorNodeBlur")
    L.new(em.outputs["Mask"], bl.inputs["Image"])
    if "Size" in bl.inputs:
        try:
            bl.inputs["Size"].default_value = (220, 220)
        except Exception:
            pass
    vg = N.new("ShaderNodeMix")
    vg.data_type = "RGBA"
    vg.blend_type = "MULTIPLY"
    vf = _math(N, L, "MULTIPLY", _math(N, L, "SUBTRACT", 1.0, bl.outputs["Image"]), 0.28)
    L.new(vf, _sock(vg, "Factor", "VALUE"))
    L.new(img, _sock(vg, "A", "RGBA"))
    _sock(vg, "B", "RGBA").default_value = (0.55, 0.52, 0.5, 1)
    L.new(_out(vg, "Result", "RGBA"), go.inputs[0])
    scene.compositing_node_group = ng
    scene.render.use_compositing = True


def eevee_quality(scene):
    e = scene.eevee
    for k, v in (("use_raytracing", True), ("use_fast_gi", True), ("fast_gi_method", "GLOBAL_ILLUMINATION"),
                 ("fast_gi_distance", 8.0), ("use_shadows", True), ("shadow_ray_count", 3), ("shadow_step_count", 10),
                 ("shadow_resolution_scale", 1.0), ("taa_render_samples", 64), ("use_volumetric_shadows", False),
                 ("shadow_pool_size", "2048")):
        try:
            setattr(e, k, v)
        except Exception:
            pass
    vs = scene.view_settings
    vs.view_transform = "AgX"
    for look in ("AgX - Medium High Contrast", "AgX - Base Contrast"):
        try:
            vs.look = look
            break
        except Exception:
            continue


def apply(scene, preset="morning"):
    P = PRESETS[preset]
    w = build_world(P)
    scene.world = w
    build_sun(P, scene)
    build_compositor(P, scene)
    eevee_quality(scene)
    practicals(scene, bool(P.get("practicals")), P.get("lamp_gain", 1.0))
    chowk_night_rig(scene, bool(P.get("chowk_rig")), 1.0)
    for o in scene.objects:                        # tiny/many scatter never casts shadows (EEVEE shadow map memory)
        if o.name.startswith(("B6_GEO_Pebbles", "ENV_GrassTufts", "ENV_Kans")):
            o.visible_shadow = False
    scene.view_settings.exposure = P["exposure"]
    scene["lighting_preset"] = preset
    for o in bpy.data.objects:                          # long lenses on wide shots keep their far clip
        if o.type == "CAMERA":
            o.data.clip_end = max(o.data.clip_end, 9000)
    print("[light] preset", preset, "applied")


# ---------------------------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    import datetime
    import shutil
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    arg = lambda n, d=None: args[args.index(n) + 1] if n in args else d  # noqa: E731
    preset = arg("--preset", "morning")
    sc = bpy.context.scene
    path = bpy.data.filepath
    root = os.path.abspath(os.path.join(os.path.dirname(path), ".."))
    if "--no-save" not in args:
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(path, os.path.join(root, "99_ARCHIVE", "MASTER_WORLD_preB1_%s.blend" % stamp))
    apply(sc, preset)
    if "--no-save" not in args:
        bpy.ops.wm.save_mainfile()
        print("[light] saved", path)
    if "--render" in args:
        only = arg("--only")
        cams = only.split(",") if only else [o.name for o in bpy.data.collections["LIGHTING_CAMERAS"].objects if o.type == "CAMERA"]
        out = os.path.join(root, "10_EXPORTS", "REVIEWS", arg("--out", "G4_B1_LIGHTING_%s" % preset))
        os.makedirs(out, exist_ok=True)
        sc.render.engine = "BLENDER_EEVEE"
        sc.render.resolution_x, sc.render.resolution_y = (int(arg("--rx", 1280)), int(arg("--ry", 720)))
        sc.eevee.taa_render_samples = int(arg("--samples", 32))
        for name in cams:
            sc.camera = bpy.data.objects[name]
            sc.render.filepath = os.path.join(out, name + ".png")
            bpy.ops.render.render(write_still=True)
            print("[light] rendered", name)
