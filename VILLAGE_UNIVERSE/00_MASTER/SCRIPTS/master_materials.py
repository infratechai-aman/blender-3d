"""Production materials for the integrated master village (terrain, roads with UVs, crops) and the
upgrade map that swaps blockout palette materials for production ones on non-hero buildings."""
import hero_lib as H
from hero_lib import hex_lin


def terrain_master():
    """Village terrain: riverbank grading by height, grass/dirt mottling, trodden earth near the chowk,
    rock on steep or high ground."""
    m, t = H._mat("MAT_Terrain_Village_Master", "#7E8A4A")
    tc = t.n("ShaderNodeTexCoord")
    obj = tc.outputs["Object"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=obj)
    z = sx.outputs["Z"]
    big = t.noise(obj, 0.02, 3.0, 0.5)
    mid = t.noise(obj, 0.12, 4.0, 0.55)
    fine = t.noise(obj, 2.5, 8.0, 0.65)
    grass = t.ramp(mid.outputs["Fac"], [(0.3, hex_lin("#5E7A36")), (0.5, hex_lin("#76903F")), (0.7, hex_lin("#9A9A55"))])
    dirt = t.ramp(fine.outputs["Fac"], [(0.3, hex_lin("#8E7252")), (0.7, hex_lin("#AE9168"))])
    # trodden earth: stronger close to the chowk (distance from origin in XY)
    r = t.n("ShaderNodeVectorMath", Vector=obj)
    r.operation = "LENGTH"
    near = t.n("ShaderNodeMapRange", Value=r.outputs["Value"], **{"From Min": 60.0, "From Max": 190.0,
                                                                  "To Min": 0.55, "To Max": 0.12}).outputs["Result"]
    df = t.math("MULTIPLY", t.math("ADD", near, t.math("MULTIPLY", t.math("SUBTRACT", big.outputs["Fac"], 0.5), 0.9)), 1.0)
    col = t.mix(t.math("MINIMUM", t.math("MAXIMUM", df, 0.0), 1.0), grass, dirt)
    # riverbank grading
    bank = t.n("ShaderNodeMapRange", Value=t.math("ADD", z, t.math("MULTIPLY", t.math("SUBTRACT", fine.outputs["Fac"], 0.5), 0.5)),
               **{"From Min": -3.2, "From Max": 0.4, "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
    bcol = t.ramp(bank, [(0.0, hex_lin("#40392D")), (0.35, hex_lin("#4E3F2F")), (0.45, hex_lin("#7A6247")),
                         (0.7, hex_lin("#A48A64")), (0.95, hex_lin("#8E8B52"))])
    bmask = t.n("ShaderNodeMapRange", Value=z, **{"From Min": 0.1, "From Max": -0.6, "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
    col = t.mix(bmask, col, bcol)
    # rock on steep / high ground
    geo = t.n("ShaderNodeNewGeometry")
    nz = t.n("ShaderNodeSeparateXYZ", Vector=geo.outputs["Normal"]).outputs["Z"]
    steep = t.n("ShaderNodeMapRange", Value=nz, **{"From Min": 0.8, "From Max": 0.92, "To Min": 1.0, "To Max": 0.0}).outputs["Result"]
    hi = t.n("ShaderNodeMapRange", Value=z, **{"From Min": 30.0, "From Max": 90.0, "To Min": 0.0, "To Max": 0.6}).outputs["Result"]
    rock = t.ramp(mid.outputs["Fac"], [(0.3, hex_lin("#7E6A58")), (0.7, hex_lin("#A88A6C"))])
    col = t.mix(t.math("MAXIMUM", t.math("MULTIPLY", steep, t.math("SUBTRACT", 1.0, bmask)), hi), col, rock)
    rough = t.n("ShaderNodeMapRange", Value=bank, **{"From Min": 0.3, "From Max": 0.5, "To Min": 0.4, "To Max": 0.93}).outputs["Result"]
    t.finish(col, rough, t.bump(fine.outputs["Fac"], 0.35, 0.04))
    return m


def _uv(t):
    return t.n("ShaderNodeUVMap").outputs["UV"]


def road_tar():
    m, t = H._mat("MAT_Road_Tar_Village", "#57534F")
    uv = _uv(t)
    sx = t.n("ShaderNodeSeparateXYZ", Vector=uv)
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n = t.noise(obj, 3.0, 8.0, 0.6)
    col = t.ramp(n.outputs["Fac"], [(0.3, hex_lin("#45423F")), (0.7, hex_lin("#5E5A55"))])
    patch = t.noise(obj, 0.25, 3.0, 0.5)
    pm = t.ramp(patch.outputs["Fac"], [(0.62, (0, 0, 0, 1)), (0.64, (1, 1, 1, 1))], "CONSTANT")
    col = t.mix(t.n("ShaderNodeSeparateColor", Color=pm).outputs[0], col, hex_lin("#34312F"))     # repair patches
    edge = t.n("ShaderNodeMapRange", Value=t.math("ABSOLUTE", t.math("SUBTRACT", sx.outputs["X"], 0.5)),
               **{"From Min": 0.36, "From Max": 0.5, "To Min": 0.0, "To Max": 1.0}).outputs["Result"]
    col = t.mix(t.math("MULTIPLY", edge, t.math("ADD", 0.5, n.outputs["Fac"])), col, hex_lin("#A08A68"))   # dusty crumbled edges
    vor = t.n("ShaderNodeTexVoronoi", Vector=obj, Scale=0.6)
    vor.feature = "DISTANCE_TO_EDGE"
    cr = t.ramp(vor.outputs["Distance"], [(0.0, (1, 1, 1, 1)), (0.025, (0, 0, 0, 1))])
    crf = t.math("MULTIPLY", t.n("ShaderNodeSeparateColor", Color=cr).outputs[0], 0.6)
    col = t.mix(crf, col, hex_lin("#232120"))
    t.finish(col, 0.82, t.bump(t.math("ADD", n.outputs["Fac"], t.math("MULTIPLY", crf, -1.0)), 0.3, 0.01))
    return m


def road_dirt(name, base="#A88D69", grass_mid=False):
    m, t = H._mat(name, base)
    uv = _uv(t)
    sx = t.n("ShaderNodeSeparateXYZ", Vector=uv)
    u = sx.outputs["X"]
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n = t.noise(obj, 2.0, 6.0, 0.6)
    col = t.ramp(n.outputs["Fac"], [(0.3, hex_lin(base, 0.86)), (0.7, hex_lin(base, 1.08))])
    ruts = t.math("ADD", t.math("COMPARE", u, 0.3, 0.06), t.math("COMPARE", u, 0.7, 0.06))
    col = t.mix(t.math("MULTIPLY", ruts, 0.5), col, hex_lin("#6E583F"))
    if grass_mid:
        gm = t.math("MULTIPLY", t.math("COMPARE", u, 0.5, 0.09), t.math("ADD", 0.2, n.outputs["Fac"]))
        col = t.mix(t.math("MINIMUM", gm, 1.0), col, hex_lin("#6E8640"))
    edge = t.n("ShaderNodeMapRange", Value=t.math("ABSOLUTE", t.math("SUBTRACT", u, 0.5)),
               **{"From Min": 0.38, "From Max": 0.5, "To Min": 0.0, "To Max": 0.8}).outputs["Result"]
    col = t.mix(t.math("MULTIPLY", edge, n.outputs["Fac"]), col, hex_lin("#7A8848"))
    fine = t.noise(obj, 12.0, 8.0, 0.7)
    t.finish(col, 0.95, t.bump(t.math("ADD", fine.outputs["Fac"], t.math("MULTIPLY", ruts, -0.5)), 0.45, 0.03))
    return m


def road_stone():
    m, t = H._mat("MAT_Road_Stone_Setts", "#A69A87")
    uv = _uv(t)
    mp = t.n("ShaderNodeMapping", Vector=uv, Scale=(5.0, 1.0, 1.0))
    br = t.n("ShaderNodeTexBrick", Vector=mp.outputs[0], Color1=hex_lin("#9C9080"), Color2=hex_lin("#B2A692"),
             Mortar=hex_lin("#6A6256"), Scale=2.2, **{"Mortar Size": 0.03, "Brick Width": 0.5, "Row Height": 0.25})
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    n = t.noise(obj, 3.0, 5.0)
    col = t.mix(t.math("MULTIPLY", n.outputs["Fac"], 0.3), br.outputs["Color"], hex_lin("#6A6256"))
    t.finish(col, 0.8, t.bump(t.math("MULTIPLY", br.outputs["Fac"], -1.0), 0.4, 0.01))
    return m


def crop(name, kind):
    m, t = H._mat(name, "#8EAA45")
    obj = t.n("ShaderNodeTexCoord").outputs["Object"]
    sx = t.n("ShaderNodeSeparateXYZ", Vector=obj)
    rows = t.math("ADD", 0.5, t.math("MULTIPLY", t.math("SINE", t.math("MULTIPLY", sx.outputs["X"], 10.5)), 0.5))
    n = t.noise(obj, 1.5, 6.0, 0.6)
    fine = t.noise(obj, 9.0, 6.0, 0.6)
    rough = 0.85
    if kind == "mustard":
        green = t.ramp(n.outputs["Fac"], [(0.3, hex_lin("#5E7E32")), (0.7, hex_lin("#76933C"))])
        yellow = t.ramp(fine.outputs["Fac"], [(0.3, hex_lin("#D9B726")), (0.7, hex_lin("#EED24A"))])
        f = t.math("MULTIPLY", t.math("ADD", rows, 0.35), t.math("ADD", fine.outputs["Fac"], 0.3))
        col = t.mix(t.math("MINIMUM", f, 1.0), green, yellow)
    elif kind == "wheat":
        col = t.ramp(n.outputs["Fac"], [(0.3, hex_lin("#7E9A3E")), (0.6, hex_lin("#9EAE50")), (0.8, hex_lin("#BDB466"))])
        col = t.mix(t.math("MULTIPLY", t.math("SUBTRACT", 1.0, rows), 0.45), col, hex_lin("#5A6A2E"))
    elif kind == "paddy":
        col = t.ramp(fine.outputs["Fac"], [(0.3, hex_lin("#5FA03A")), (0.7, hex_lin("#86BC4C"))])
        water = t.math("COMPARE", rows, 0.0, 0.32)
        col = t.mix(t.math("MULTIPLY", water, 0.85), col, hex_lin("#4F6A62"))
        rough = t.math("SUBTRACT", 0.8, t.math("MULTIPLY", water, 0.7))
    else:  # fallow: ploughed furrows
        col = t.ramp(rows, [(0.2, hex_lin("#5E4835")), (0.8, hex_lin("#9A7A57"))])
        col = t.mix(t.math("MULTIPLY", n.outputs["Fac"], 0.3), col, hex_lin("#7A8A48"))
    t.finish(col, rough, t.bump(t.math("ADD", rows, t.math("MULTIPLY", fine.outputs["Fac"], 0.5)), 0.5, 0.06))
    return m


def upgrade_palette(M):
    """Swap blockout palette materials for production materials (non-hero buildings + landmarks)."""
    up = {
        "wall_lime_white": H.mat_plaster("MAT_Wall_Lime_White_Indigo", "#EDE3CF", band="#4A6A9A", band_top=1.15),
        "wall_clay_ochre": H.mat_mud("MAT_Wall_Mud_Ochre", "#B98758"),
        "wall_mud_brown": H.mat_mud("MAT_Wall_Mud_Brown", "#9E7653"),
        "wall_pastel_blue": H.mat_plaster("MAT_Wall_Plaster_Blue", "#8DB2C8"),
        "wall_pastel_yellow": H.mat_plaster("MAT_Wall_Plaster_Yellow_Maroon", "#E3C47D", band="#8E3B2E", band_top=1.15),
        "wall_pastel_pink": H.mat_plaster("MAT_Wall_Plaster_Pink", "#D9A6A0"),
        "wall_mint": H.mat_plaster("MAT_Wall_Plaster_Mint", "#A8C6A2", band="#4C6A5A", band_top=1.15),
        "wall_sandstone": H.mat_stone_blocks("MAT_Wall_Sandstone_Haveli", "#C99A70", "#D8AA80", "#9A7558", 1.2, 0.6, 0.3),
        "roof_terracotta": H.mat_tile(),
        "roof_thatch": H.mat_straw(),
        "roof_concrete": H.mat_simple("MAT_Concrete_Weathered", "#B3AC9F", 0.85, noise=0.15),
        "roof_tin": H.mat_tin(),
        "plinth_stone": H.mat_stone_blocks(),
        "wood_dark": H.mat_painted("MAT_Wood_Painted_Teal", "#2F7A72"),
        "shutter_metal": H.mat_simple("MAT_Metal_Shutter_Grey", "#7E8A8E", 0.45, 0.6, noise=0.1),
        "awning_red": H.mat_simple("MAT_Cloth_Awning_Red", "#B4473A", 0.8, noise=0.15),
        "awning_blue": H.mat_simple("MAT_Cloth_Awning_Blue", "#3D6F95", 0.8, noise=0.15),
        "awning_green": H.mat_simple("MAT_Cloth_Awning_Green", "#4F8452", 0.8, noise=0.15),
        "temple_white": H.mat_plaster("MAT_Plaster_Temple_Cream", "#F2E5C9"),
        "saffron": H.mat_simple("MAT_Cloth_Saffron", "#E3722A", 0.7, noise=0.1),
        "chowk_stone": H.mat_paving("MAT_Paving_Chowk_Stone", "#A89A84", "#BCAE96", "#6E6556", scale=1.4),
        "road_dirt": H.mat_mud("MAT_Mud_Floor_Tabela", "#8E6E4E"),
        "water": H.mat_water(),
        "crop_mustard": crop("MAT_Crop_Mustard", "mustard"),
        "crop_wheat": crop("MAT_Crop_Wheat", "wheat"),
        "crop_paddy": crop("MAT_Crop_Paddy", "paddy"),
        "crop_fallow": crop("MAT_Crop_Fallow", "fallow"),
    }
    M.update(up)
    M["terrain"] = terrain_master()
    M["road_paved"] = road_tar()
    M["road_dirt_main"] = road_dirt("MAT_Road_Dirt_Main", "#A88D69")
    M["road_lane"] = road_dirt("MAT_Road_Dirt_Lane", "#B49A76", grass_mid=True)
    M["road_stone"] = road_stone()
    return M
