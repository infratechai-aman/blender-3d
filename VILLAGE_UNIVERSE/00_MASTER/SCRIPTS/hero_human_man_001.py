"""
CHR_Human_Man_001 - village farmer, ~55 y, in the approved Woman_001 aesthetic (MPFB CC0 base + own stylisation).

  blender -b --factory-startup --python hero_human_man_001.py -- [--render] [--quick] [--only CAM_A,CAM_B] [--tpose]

  body      MPFB male, sun-tanned, wiry farmer build, light stylisation (eyes, nose, cheekbones)
  rig       MPFB "mixamo" skeleton; clothes weighted to it; strand hair rides a scalp surface; moustache + brows
            are strand curves parented to the head bone
  hair      short salt-and-pepper strands, combed back
  clothing  cotton kurta (torso cut from the body + flared skirt to the knee), dhoti (draped legs + front pleat
            panel, coloured border), red-and-white checked gamchha over the right shoulder, chappals, steel kada
Output: 04_CHARACTERS/HUMANS/CHR_Human_Man_001.blend   Reviews: 10_EXPORTS/REVIEWS/G5_HUMAN_MAN_001_v001/
"""
import datetime
import math
import os
import shutil
import sys

import bpy
from mathutils import Matrix

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import numpy as np  # noqa: E402

import char_lib as CL  # noqa: E402
import hair_strands as HS_  # noqa: E402
import hero_human_woman_001 as W1  # noqa: E402
import hero_human_woman_001_v2 as V2  # noqa: E402
import hero_lib as H  # noqa: E402
from geo import catmull_rom  # noqa: E402

ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUT_BLEND = os.path.join(ROOT, "04_CHARACTERS", "HUMANS", "CHR_Human_Man_001.blend")
OUT_REVIEW = os.path.join(ROOT, "10_EXPORTS", "REVIEWS", "G5_HUMAN_MAN_001_v001")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
PREFIX = "Man001"
LM = V2.LM

MACRO = dict(gender=1.0, age=0.72, muscle=0.55, weight=0.4, proportions=0.65, height=0.4, cupsize=0.5, firmness=0.5,
             race={"asian": 0.55, "african": 0.3, "caucasian": 0.15})
STYLE = [("l-eye-scale-incr", 0.3), ("r-eye-scale-incr", 0.3), ("nose-point-width-decr", 0.1), ("nose-volume-incr", 0.1),
         ("l-cheek-bones-incr", 0.35), ("r-cheek-bones-incr", 0.35), ("chin-prominent-incr", 0.2), ("head-round", 0.15),
         ("mouth-scale-vert-decr", 0.25), ("mouth-lowerlip-height-decr", 0.2), ("neck-scale-horiz-decr", 0.05), ("eyebrows-trans-down", 0.1)]


def mat_check(name, c1, c2, scale=24.0):
    """Gamchha madras check from the UV (u across the cloth, v along it) + a fringe-coloured end band."""
    m, t = H._mat(name, c1)
    uv = t.n("ShaderNodeUVMap").outputs["UV"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=uv)
    u = t.math("GREATER_THAN", t.math("SINE", t.math("MULTIPLY", sx.outputs["X"], scale * 0.5)), 0.2)
    v = t.math("GREATER_THAN", t.math("SINE", t.math("MULTIPLY", sx.outputs["Y"], scale * 2.0)), 0.2)
    both = t.math("MULTIPLY", u, v)
    one = t.math("MAXIMUM", u, v)
    col = t.mix(one, H.hex_lin(c2), H.hex_lin("#C9757A"))
    col = t.mix(both, col, H.hex_lin(c1))
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    weave = t.noise(obj, 700.0, 2.0, 0.5)
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.inp(b, "Roughness").default_value = 0.8
    try:
        t.inp(b, "Sheen Weight").default_value = 0.5
    except Exception:
        pass
    t.link(t.bump(weave.outputs["Fac"], 0.2, 0.001), t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def mat_cotton(name, base, border=None, border_z=None, stripe=False):
    m, t = H._mat(name, base)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    weave = t.noise(obj, 800.0, 2.0, 0.5)
    dirt = t.noise(obj, 6.0, 4.0, 0.6)
    col = t.ramp(weave.outputs["Fac"], [(0.3, H.hex_lin(base, 0.95)), (0.7, H.hex_lin(base, 1.03))])
    z = t.n("ShaderNodeSeparateXYZ", Vector=obj).outputs["Z"]
    grime = t.n("ShaderNodeMapRange", Value=z, **{"From Min": 0.35, "From Max": 0.05, "To Min": 0.0, "To Max": 0.35}).outputs["Result"]
    col = t.mix(t.math("MULTIPLY", grime, dirt.outputs["Fac"]), col, H.hex_lin("#9C8A6A"))
    if stripe:
        x = t.n("ShaderNodeSeparateXYZ", Vector=obj).outputs["X"]
        st = t.math("GREATER_THAN", t.math("SINE", t.math("MULTIPLY", x, 160.0)), 0.92)
        col = t.mix(t.math("MULTIPLY", st, 0.35), col, H.hex_lin("#8E9AA8"))
    if border:
        b1 = t.math("MULTIPLY", t.math("GREATER_THAN", z, border_z[0]), t.math("LESS_THAN", z, border_z[1]))
        b2 = t.math("MULTIPLY", t.math("GREATER_THAN", z, border_z[1] + 0.008), t.math("LESS_THAN", z, border_z[1] + 0.014))
        col = t.mix(t.math("MAXIMUM", b1, b2), col, H.hex_lin(border))
    b = t.n("ShaderNodeBsdfPrincipled")
    t.link(col, t.inp(b, "Base Color"))
    t.inp(b, "Roughness").default_value = 0.85
    try:
        t.inp(b, "Sheen Weight").default_value = 0.6
    except Exception:
        pass
    t.link(t.bump(weave.outputs["Fac"], 0.15, 0.001), t.inp(b, "Normal"))
    t.link(b.outputs[0], t.n("ShaderNodeOutputMaterial").inputs["Surface"])
    return m


def bone_parent(obj, arm, bone):
    obj.parent = arm
    obj.parent_type = "BONE"
    obj.parent_bone = bone
    bpy.context.view_layer.update()
    pb = arm.pose.bones[bone]
    obj.matrix_parent_inverse = (arm.matrix_world @ Matrix.Translation(pb.tail) @ pb.matrix.to_3x3().to_4x4()).inverted()


def strand_curves(name, strands, radius, mat):
    cd = bpy.data.hair_curves.new(name)
    cd.add_curves([len(s) for s in strands])
    P = np.concatenate([np.asarray(s, np.float32) for s in strands])
    cd.attributes["position"].data.foreach_set("vector", P.ravel())
    r = cd.attributes.get("radius") or cd.attributes.new("radius", "FLOAT", "POINT")
    R = np.concatenate([[radius * (1 - 0.7 * (j / (len(s) - 1)) ** 1.5) for j in range(len(s))] for s in strands])
    r.data.foreach_set("value", np.asarray(R, np.float32))
    cd.materials.append(mat)
    o = bpy.data.objects.new(name, cd)
    V2.COLL.objects.link(o)
    return o


def moustache_and_brows(M, S, arm):
    rng = np.random.default_rng(11)
    lip = LM["lip_c"]
    sub_z = lip[2] + 0.017
    roots = []
    for _ in range(1400):                                                      # moustache: upper-lip roots
        x = rng.uniform(-0.026, 0.026)
        z = sub_z - rng.uniform(0.0, 0.009) - 0.004 * (abs(x) / 0.026) ** 2
        if abs(x) < 0.003 and rng.random() < 0.6:
            continue
        p, nr = S.front(x, z)
        if p is not None:
            roots.append((p, nr))
    strands = []
    for p, nr in roots:
        s = np.sign(p[0]) if abs(p[0]) > 1e-4 else 1.0
        L = rng.uniform(0.008, 0.016) * (1 + 0.4 * abs(p[0]) / 0.026)
        d = np.array([s * 0.55, -0.35, -1.0])
        d /= np.linalg.norm(d)
        pts = [p + nr * 0.0003]
        for j in range(1, 6):
            t = j / 5
            q = pts[0] + d * L * t + nr * 0.0025 * math.sin(math.pi * t * 0.7) + np.array([s * 0.004 * t * t, 0, -0.002 * t * t])
            pts.append(q)
        strands.append(pts)
    mo = strand_curves("GEO_%s_Moustache" % PREFIX, strands, 0.00022, M["hair_grey"])
    bone_parent(mo, arm, "mixamorig:Head")
    bstr = []
    for side in ("l", "r"):                                                    # brows: short strands along the arch
        c, r = LM["eye_" + side]
        sgn = np.sign(c[0])
        for _ in range(450):
            t = rng.uniform(0, 1)
            x = c[0] + sgn * (-0.012 + 0.042 * t)
            z = c[2] + r * 1.1 + 0.006 * math.sin(math.pi * min(t * 1.2, 1.0)) - 0.003 * t + rng.normal(0, 0.0018)
            p, nr = S.front(x, z)
            if p is None:
                continue
            d = np.array([sgn * (0.6 + 0.4 * t), 0.0, 0.25 - 0.5 * t])
            d /= np.linalg.norm(d)
            L = rng.uniform(0.004, 0.008)
            bstr.append([p + nr * 0.0002, p + d * L * 0.5 + nr * 0.0012, p + d * L + nr * 0.0016])
    br = strand_curves("GEO_%s_Brows" % PREFIX, bstr, 0.00018, M["hair_grey"])
    bone_parent(br, arm, "mixamorig:Head")
    return mo, br


def build_hair(M, body):
    ec = (LM["eye_l"][0] + LM["eye_r"][0]) / 2
    top = LM["body_co"][:, 2].max()
    hc = np.array([0.0, ec[1] + 0.075, (top + LM["mouth"][2]) / 2 + 0.01])

    def hairline(p):
        d = p - hc
        n = d / (np.linalg.norm(d) + 1e-9)
        if n[1] < 0:                                                           # slightly receding temples (M-line)
            hl = ec[2] + 0.068 + 0.012 * W1.ss(0.25, 0.5, abs(n[0])) - 0.08 * W1.ss(0.5, 0.95, abs(n[0])) * (1 - W1.ss(-0.35, 0.2, n[1]))
        else:
            hl = ec[2] - 0.012 - 0.07 * W1.ss(0.0, 0.9, n[1])
        w = W1.ss(0.62, 0.82, abs(n[0])) * W1.ss(-0.6, -0.38, n[1])
        return hl * (1 - w) + (ec[2] - 0.028) * w

    def is_ear(p):
        return abs(p[0]) > 0.072 and ec[2] - 0.06 < p[2] < ec[2] + 0.025 and p[1] > ec[1] + 0.03

    def keep(p):
        if p[2] < LM["neck"][2] + 0.03 or abs(p[0]) > 0.11 or np.linalg.norm(p[:2] - hc[:2]) > 0.14:
            return False
        return p[2] > hairline(p) and not is_ear(p)

    cap = V2.extract(body, "GEO_%s_HairCap" % PREFIX, lambda p: keep(p) and p[2] > hairline(p) + 0.004, M["hair_base_grey"],
                     0.0004, relax=14)
    nape = np.array([0.0, hc[1] + 0.085, ec[2] - 0.06])
    scalp, strands, _ = HS_.build(body, V2.COLL, hc, ec, nape, hairline, keep, np.random.default_rng(5), M["hair_grey"],
                                  n_scalp=9000, prefix="GEO_" + PREFIX, style="short", short_len=0.04, radius=0.00026)
    return cap, scalp, strands


def build_kurta(M, body):
    pel = LM["pelvis"][2]
    neck = LM["neck"][2]
    sh = {s: LM["shoulder_" + s] for s in ("l", "r")}
    el = {s: LM["elbow_" + s] for s in ("l", "r")}
    wr = {s: LM["hand_" + s] for s in ("l", "r")}

    def keep(p):
        if p[2] < pel - 0.1 or p[2] > neck + 0.015:
            return False
        if p[1] < 0 and p[2] > neck - 0.04 and abs(p[0]) < 0.04 + 0.4 * (p[2] - (neck - 0.04)):
            return False                                                    # round neck with a short placket
        if abs(p[0]) > 0.15:
            s = "l" if p[0] > 0 else "r"
            if p[2] < pel + 0.02 and abs(p[0]) > 0.17:
                return False
            ax = (el[s] - sh[s]) / np.linalg.norm(el[s] - sh[s])
            if float((p - sh[s]) @ ax) < np.linalg.norm(el[s] - sh[s]):
                return True
            ax2 = (wr[s] - el[s]) / np.linalg.norm(wr[s] - el[s])
            return float((p - el[s]) @ ax2) < 0.11                          # 3/4 sleeves
        return True

    def vol(p):
        return 0.009 + 0.012 * W1.ss(pel + 0.25, pel, p[2])
    top = V2.extract(body, "GEO_%s_Kurta" % PREFIX, keep, M["kurta"], 0.0, relax=10, vol_fn=vol)
    top.modifiers.new("Thick", "SOLIDIFY").thickness = 0.003
    # kurta skirt: flared tube from the hip to the knee with soft folds
    co = LM["body_co"]
    z0, z1 = pel - 0.05, LM["body_co"][:, 2].min() + 0.48
    nv, nu = 26, 120
    zs = np.linspace(z0, z1, nv)
    th = np.linspace(-np.pi, np.pi, nu, endpoint=False)
    mx, y0, y1 = V2.measure(co, pel - 0.06, pel + 0.02, 0.2)
    V = []
    for k, z in enumerate(zs):
        t = k / (nv - 1)
        ax = mx + 0.034 + 0.045 * t ** 0.8
        ay = (y1 - y0) / 2 + 0.034 + 0.035 * t ** 0.8
        cy = (y0 + y1) / 2
        for a in th:
            f = 1 + ((0.003 + 0.014 * t) * math.sin(7 * a + 1.1 + 2 * t) + 0.006 * t * math.sin(13 * a)) / max(ax, 0.1)
            V.append((ax * math.cos(a) * f, cy + ay * math.sin(a) * f, z - 0.01 * t * math.cos(2 * a)))
    sk = CL.mesh_obj("GEO_%s_KurtaSkirt" % PREFIX, V, CL.grid_faces(nu, nv, closed_u=True), M["kurta"], V2.COLL)
    sk.modifiers.new("Thick", "SOLIDIFY").thickness = 0.003
    sk.modifiers.new("Sub", "SUBSURF").levels = 1
    return top, sk


def build_dhoti(M, body):
    pel = LM["pelvis"][2]

    def keep(p):
        return 0.07 < p[2] < pel + 0.02 and abs(p[0]) < 0.22

    rng = np.random.default_rng(3)
    ph = rng.uniform(0, 6.28, 3)

    def vol(p):
        drape = 0.016 + 0.03 * W1.ss(pel, 0.15, p[2])
        fold = 0.005 * math.sin(p[2] * 60 + ph[0] + p[0] * 40) + 0.003 * math.sin(p[1] * 90 + ph[1])
        return max(drape + fold * W1.ss(pel, 0.3, p[2]), 0.012)
    d = V2.extract(body, "GEO_%s_Dhoti" % PREFIX, keep, M["dhoti"], 0.0, relax=8, vol_fn=vol)
    d.modifiers.new("Thick", "SOLIDIFY").thickness = 0.003
    d.modifiers.new("Sub", "SUBSURF").levels = 1
    # front pleat panel (kachha fall) between the legs
    S = V2.Surface(body)
    P = []
    for z in np.linspace(pel - 0.02, 0.16, 12):
        p, nr = S.front(0.0, z)
        y = (p[1] if p is not None else -0.1) - 0.03
        P.append(np.array([0.0, min(y, -0.06), z]))
    C = catmull_rom([tuple(p) for p in P], 6)
    sides = [np.array([1.0, 0, 0])] * len(C)
    half = [0.05 + 0.03 * (k / (len(C) - 1)) for k in range(len(C))]

    def fold(t, s):
        return np.array([0, 0.008 * math.sin(s * math.pi * 3 + t * 4), 0])
    V, F, UV = CL.sweep(C, sides, half, 12, fold)
    pnl = CL.mesh_obj("GEO_%s_DhotiPleat" % PREFIX, V, F, M["dhoti"], V2.COLL)
    pnl.modifiers.new("Thick", "SOLIDIFY").thickness = 0.003
    return d, pnl


def build_gamchha(M, S):
    shr = LM["shoulder_r"]
    neck = LM["neck"][2]
    spec = [("front", shr[0] + 0.06, neck - 0.3), ("front", shr[0] + 0.03, neck - 0.16), ("front", shr[0] + 0.0, neck - 0.06),
            ("top", shr[0] + 0.02, shr[1] - 0.02), ("top", shr[0] + 0.02, shr[1] + 0.05), ("back", shr[0] + 0.02, neck - 0.08),
            ("back", shr[0] + 0.05, neck - 0.22), ("back", shr[0] + 0.07, neck - 0.36)]
    P = []
    for kind, a, b in spec:
        p, nr = (S.front(a, b) if kind == "front" else S.back(a, b) if kind == "back" else S.top(a, b))
        if p is not None:
            P.append(p + nr * 0.02)
    C = catmull_rom([tuple(p) for p in P], 8)
    n = len(C)
    sides, half = [], []
    for k in range(n):
        tg = C[min(k + 1, n - 1)] - C[max(k - 1, 0)]
        tg /= np.linalg.norm(tg)
        out = np.array([C[k][0], C[k][1], 0.0])
        out = out / (np.linalg.norm(out) + 1e-9)
        t = k / (n - 1)
        if 0.35 < t < 0.65:
            out = np.array([0, 0, 1.0])
        sd = np.cross(tg, out)
        sd /= np.linalg.norm(sd)
        sides.append(sd)
        half.append(0.045 + 0.02 * abs(2 * t - 1))

    def fold(t, s):
        return np.array([0, 0, 0.004 * math.sin(s * math.pi * 3 + t * 7)])
    V, F, UV = CL.sweep(C, sides, half, 12, fold)
    o = CL.mesh_obj("GEO_%s_Gamchha" % PREFIX, V, F, M["gamchha"], V2.COLL)
    CL.set_uv(o, UV)
    s = o.modifiers.new("Thick", "SOLIDIFY")
    s.thickness = 0.003
    s.offset = 1.0
    o.modifiers.new("Sub", "SUBSURF").levels = 1
    return o


def accessories(M):
    objs = []
    el, wr = LM["elbow_r"], LM["hand_r"]
    ax = (wr - el) / np.linalg.norm(wr - el)
    W1.torus("GEO_%s_Kada" % PREFIX, wr - ax * 0.04, ax, 0.038, 0.0042, M["steel"])
    objs.append(V2.COLL.objects["GEO_%s_Kada" % PREFIX])
    co = LM["body_co"]
    for side in ("l", "r"):
        an = LM["ankle_" + side]
        sel = co[(np.abs(co[:, 0] - an[0]) < 0.07) & (co[:, 2] < 0.05)]
        x0, x1 = sel[:, 0].min() - 0.01, sel[:, 0].max() + 0.01
        y0, y1 = sel[:, 1].min() - 0.014, sel[:, 1].max() + 0.01
        hb = H.HB()
        hb.box(x0, x1, y0, y1, -0.014, 0.0, M["sole"])
        ym = y0 + (y1 - y0) * 0.32
        hb.rod(M["sole"], (x0 + 0.004, ym, 0.0), ((x0 + x1) / 2, ym, 0.026), 0.006, 6)
        hb.rod(M["sole"], ((x0 + x1) / 2, ym, 0.026), (x1 - 0.004, ym, 0.0), 0.006, 6)
        o = bpy.data.objects.new("GEO_%s_Chappal_%s" % (PREFIX, side.upper()), hb.to_mesh("ME_Chappal_M"))
        V2.COLL.objects.link(o)
        objs.append(o)
    return objs


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    HS, TS = V2.mpfb()
    sc = bpy.context.scene
    sc.name = "CHR_Human_Man_001"
    sc.unit_settings.system = "METRIC"
    V2.COLL = bpy.data.collections.new("CHR_Human_Man_001")
    sc.collection.children.link(V2.COLL)
    W1.COLL = V2.COLL
    V2.MACRO = MACRO
    V2.STYLE_TARGETS = STYLE
    M = W1.materials()
    M["hair_grey"] = HS_.mat_hair_strands("MAT_Hair_Strands_SaltPepper", melanin=0.38, rough=0.32)
    for nd in M["hair_grey"].node_tree.nodes:
        if nd.bl_idname == "ShaderNodeBsdfHairPrincipled":
            nd.parametrization = "COLOR"
            nd.inputs["Color"].default_value = (0.055, 0.05, 0.048, 1.0)       # charcoal with grey strands
            for k, v in (("Random Color", 0.0), ("Roughness", 0.38), ("Coat", 0.05)):
                if k in nd.inputs:
                    nd.inputs[k].default_value = v
            info = M["hair_grey"].node_tree.nodes.new("ShaderNodeHairInfo")
            ramp = M["hair_grey"].node_tree.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.interpolation = "CONSTANT"
            ramp.color_ramp.elements[0].color = (0.03, 0.028, 0.027, 1)
            ramp.color_ramp.elements[1].position = 0.55
            ramp.color_ramp.elements[1].color = (0.42, 0.41, 0.4, 1)
            M["hair_grey"].node_tree.links.new(info.outputs["Random"], ramp.inputs[0])
            M["hair_grey"].node_tree.links.new(ramp.outputs[0], nd.inputs["Color"])
    M["hair_base_grey"] = CL.mat_principled("MAT_Hair_Scalp_Base_Grey", "#2A2624", 0.6)
    M["kajal"] = CL.mat_principled("MAT_Lash_Man", "#2A211C", 0.6)                 # no kohl look on him
    M["kurta"] = mat_cotton("MAT_Cloth_Kurta_Cream", "#E2D8BF", stripe=False)
    M["dhoti"] = mat_cotton("MAT_Cloth_Dhoti_White", "#EFEADB", border="#7A2A2A", border_z=(0.1, 0.125))
    M["gamchha"] = mat_check("MAT_Cloth_Gamchha_Check", "#B3262B", "#EDE6D8")
    M["steel"] = CL.mat_principled("MAT_Metal_Steel_Kada", "#B9BEC2", 0.25, 1.0)
    body = V2.build_body(M, HS, TS)
    body.name = "GEO_%s_Body" % PREFIX
    arm = HS.add_builtin_rig(body, "mixamo")
    arm.name = "RIG_Human_Man_001"
    for c in list(arm.users_collection):
        c.objects.unlink(arm)
    V2.COLL.objects.link(arm)
    S = V2.Surface(body)
    LM["lip_c"] = V2.find_lips(S)
    M["skin_mouth"] = V2.mat_skin_mouth("MAT_Skin_Man_001", "#8C5A3A", "#7A4A3E", LM["lip_c"])
    body.data.materials.clear()
    body.data.materials.append(M["skin_mouth"])
    lashes = V2.build_eyes(M, body)
    cap, scalp, strands = build_hair(M, body)
    kurta, kskirt = build_kurta(M, body)
    dhoti, pleat = build_dhoti(M, body)
    gam = build_gamchha(M, S)
    acc = accessories(M)
    mo, br = moustache_and_brows(M, S, arm)
    sub = body.modifiers.new("Sub", "SUBSURF")
    sub.levels = 1
    for o in (lashes, cap, kurta, dhoti, scalp):
        V2.rig_follow(o, arm)
    for o in [kskirt, pleat, gam] + acc + [x for x in V2.COLL.objects if x.name.startswith(("GEO_Woman001_Eye_",
              "GEO_Woman001_Iris", "GEO_Woman001_Pupil"))]:
        V2.rig_follow(o, arm, body)
    for o in list(sc.collection.objects):
        if o.type == "META":
            bpy.data.objects.remove(o, do_unlink=True)
    for o in list(V2.COLL.objects):                                       # shared builders name things Woman001
        o.name = o.name.replace("Woman001", PREFIX)
        if getattr(o, "data", None) is not None and hasattr(o.data, "name"):
            o.data.name = o.data.name.replace("Woman001", PREFIX)
    if "--tpose" not in ARGS:
        V2.pose_arms(arm, 30.0)
    quick = "--quick" in ARGS
    top = LM["body_co"][:, 2].max()
    ec = LM["eye_l"][0]
    cams = {
        "CAM_Front":        ((0.0, -3.8, top * 0.55), (0.0, 0.0, top * 0.52), 50, 1200, 1500),
        "CAM_Side_L":       ((3.8, 0.0, top * 0.55), (0.0, 0.0, top * 0.52), 50, 1200, 1500),
        "CAM_Back":         ((0.0, 3.8, top * 0.55), (0.0, 0.0, top * 0.52), 50, 1200, 1500),
        "CAM_ThreeQuarter": ((2.3, -2.9, top * 0.66), (0.0, 0.0, top * 0.53), 50, 1200, 1500),
        "CAM_Face":         ((0.0, -0.8, ec[2] + 0.01), (0.0, 0.0, ec[2] - 0.02), 85, 1200, 1200),
        "CAM_Face_34":      ((0.5, -0.64, ec[2] + 0.03), (0.0, 0.0, ec[2] - 0.025), 85, 1200, 1200),
    }
    if quick:
        cams = {k: (p, t, l, rx * 2 // 3, ry * 2 // 3) for k, (p, t, l, rx, ry) in cams.items()}
    objs = CL.review_stage(cams, OUT_REVIEW, PREFIX, samples=48 if quick else 128)
    try:
        sc.cycles_curves.shape = "THICK"
    except Exception:
        pass
    sc.camera = objs["CAM_Front"][0]
    os.makedirs(os.path.dirname(OUT_BLEND), exist_ok=True)
    if os.path.exists(OUT_BLEND):
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(OUT_BLEND, os.path.join(ROOT, "99_ARCHIVE", "CHR_Human_Man_001_%s.blend" % stamp))
    bpy.ops.wm.save_as_mainfile(filepath=OUT_BLEND, compress=True)
    print("[char] saved", OUT_BLEND, "objects:", len(V2.COLL.objects))
    if "--render" in ARGS:
        only = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
        CL.render_cams(objs, OUT_REVIEW, only)


if __name__ == "__main__":
    main()
