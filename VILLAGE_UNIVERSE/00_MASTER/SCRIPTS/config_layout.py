"""
AMALTASPUR - village layout configuration (single source of truth for the blockout).

Units: 1 Blender unit = 1 metre.  +X = east, +Y = north, +Z = up.
Village chowk (banyan tree) sits at the world origin.

Edit values here, then rerun build_blockout.py.  Nothing in this file touches bpy.
"""

VILLAGE_NAME = "Amaltaspur"
BLOCKOUT_VERSION = "v001"

# --------------------------------------------------------------------------
# Terrain extents
# --------------------------------------------------------------------------
TERRAIN_X = (-800.0, 800.0)
TERRAIN_Y = (-900.0, 1100.0)
TERRAIN_CELL = 5.0            # metres between terrain vertices
RIVER_BED_Z = -3.2
WATER_Z = -1.7
TEMPLE_POS = (114.0, 65.0)    # also used for the small rise in the terrain

# --------------------------------------------------------------------------
# River (centre line, north -> south).  Water is ~30 m wide.
# --------------------------------------------------------------------------
RIVER_CTRL = [(146, 1160), (150, 820), (158, 600), (172, 380), (170, 200), (166, 110),
              (150, 40), (142, -30), (160, -140), (196, -280), (215, -460), (230, -720), (245, -960)]
RIVER_CLEAR = 24.0            # buildings must stay this far from the river centre line

# --------------------------------------------------------------------------
# Roads.  ctrl points are smoothed with Catmull-Rom.  Width in metres.
# kind -> material: paved (tar), dirt_main (compacted earth), dirt (lane), stone
# --------------------------------------------------------------------------
ROADS = {
    "R01": dict(name="Main_Approach",   kind="paved",     width=7.0,
                ctrl=[(-30, -700), (-30, -430), (-22, -280), (-12, -160), (-6, -80), (-1, -22)]),
    "R02": dict(name="Market_Street",   kind="dirt_main", width=6.5,
                ctrl=[(-21, 3), (-60, 6), (-100, 3), (-140, -6), (-200, -20), (-330, -32), (-700, -60)]),
    "R03": dict(name="Temple_Road",     kind="stone",     width=5.0,
                ctrl=[(15, 15), (45, 38), (78, 54), (98, 59)]),
    "R04": dict(name="Bridge_Road",     kind="paved",     width=6.5,
                ctrl=[(21, -6), (60, -17), (100, -25), (130, -28), (165, -31), (220, -37), (430, -52), (700, -70)]),
    "R05": dict(name="North_Road",      kind="dirt_main", width=5.5,
                ctrl=[(-2, 22), (-6, 60), (-14, 110), (-30, 170), (-55, 270), (-80, 380)]),
    "L01": dict(name="West_Lane",       kind="dirt",      width=3.6,
                ctrl=[(-6, 70), (-45, 74), (-90, 70), (-128, 58)]),
    "L02": dict(name="Southeast_Lane",  kind="dirt",      width=3.6,
                ctrl=[(-5, -62), (30, -66), (70, -60), (108, -50)]),
    "L03": dict(name="Southwest_Lane",  kind="dirt",      width=3.6,
                ctrl=[(-8, -70), (-50, -74), (-92, -68), (-130, -55)]),
    "L04": dict(name="Northeast_Lane",  kind="dirt",      width=3.4,
                ctrl=[(-5, 52), (28, 80), (50, 118)]),
    "L05": dict(name="Market_Link",     kind="dirt",      width=3.2,
                ctrl=[(-114, 1), (-117, 32), (-116, 62)]),
    "P01": dict(name="Ghat_Path",       kind="stone",     width=2.4,
                ctrl=[(97, 56), (104, 45), (118, 41), (131, 46)]),
}
ROAD_Z_OFFSET = {"paved": 0.14, "dirt_main": 0.12, "stone": 0.13, "dirt": 0.10}
ROAD_MARGIN = 0.6             # min gap between a building and any road edge

CHOWK_CENTER = (0.0, 0.0)
CHOWK_RADIUS = 23.0
GATE_ROAD = "R01"
GATE_POINT = (-11.0, -140.0)  # entrance gate straddles R01 at the road point nearest this

# Circles nothing may be built inside: (x, y, radius)
CIRCLE_OBSTACLES = [(0.0, 0.0, CHOWK_RADIUS + 2.0)]

# --------------------------------------------------------------------------
# Building families.  w = frontage (m), d = depth (m).
# --------------------------------------------------------------------------
KINDS = {
    "sh":  dict(family="shop",          w=5.0,  d=7.0,  setback=(0.8, 1.4), gap=(0.15, 0.4)),
    "sh2": dict(family="shop_2storey",  w=6.0,  d=8.0,  setback=(0.8, 1.4), gap=(0.15, 0.4)),
    "s":   dict(family="house_small",   w=6.5,  d=5.5,  setback=(1.5, 3.5), gap=(2.2, 4.5)),
    "c":   dict(family="house_common",  w=10.0, d=8.5,  setback=(1.5, 3.5), gap=(2.2, 4.5)),
    "m":   dict(family="house_middle",  w=14.0, d=14.0, setback=(2.5, 4.5), gap=(2.5, 5.0)),
    "r":   dict(family="house_rich",    w=22.0, d=20.0, setback=(5.0, 7.0), gap=(5.0, 8.0)),
    "cs":  dict(family="cattle_shed",   w=9.0,  d=5.5,  setback=(2.0, 4.0), gap=(2.5, 4.5)),
    "gs":  dict(family="grain_store",   w=7.0,  d=6.0,  setback=(3.0, 5.0), gap=(3.0, 6.0)),
    "temple":    dict(family="temple",    w=24.0, d=24.0),
    "panchayat": dict(family="panchayat", w=18.0, d=11.0),
    "school":    dict(family="school",    w=40.0, d=34.0),
}
SHOP_KINDS = ("sh", "sh2")
BUILDING_GAP = 2.0            # min gap between non-shop neighbours
MAX_SLOPE_RANGE = 2.5         # max terrain height difference under a footprint

# Landmarks placed before the frontage fill.
#   mode "abs":  pos + face (point the front door looks toward)
#   mode "road": road, t (metres along road), side (+1 left / -1 right of travel), setback
LANDMARKS = [
    dict(key="temple",    kind="temple",    label="Shiv Temple",     mode="abs",  pos=TEMPLE_POS, face=(80, 56)),
    dict(key="panchayat", kind="panchayat", label="Panchayat Bhavan", mode="road", road="R02", t=14.0, side=+1, setback=7.0),
    dict(key="school",    kind="school",    label="Village School",   mode="road", road="R05", t=105.0, side=+1, setback=2.0),
    dict(key="haveli_a",  kind="r",         label="Haveli A (chowk)", mode="abs",  pos=(-46, 44), face=(0, 0)),
    dict(key="haveli_b",  kind="r",         label="Haveli B (temple road)", mode="road", road="R03", t=40.0, side=-1, setback=6.0),
]

# Frontage fill: (road, side, t_start, t_end, sequence of kinds, neighbourhood)
FRONTAGES = [
    ("R02", -1,   6, 200, ["sh", "sh", "sh2", "sh", "sh", "c", "m", "c", "s", "cs"], "Market North"),
    ("R02", +1,  26, 200, ["sh", "sh2", "sh", "sh", "sh", "c", "c", "s"],            "Market South"),
    ("R01", +1, 562, 655, ["c", "m", "c", "s"],                      "Approach West"),
    ("R01", -1, 562, 655, ["c", "c", "s"],                           "Approach East"),
    ("R04", +1,  10, 100, ["sh", "c", "m"],                          "Bridge Road North"),
    ("R04", -1,  10, 100, ["c", "gs"],                               "Bridge Road South"),
    ("R05", +1,  40,  95, ["c"],                                     "North Road West"),
    ("R05", -1,  40, 150, ["m", "c", "cs"],                          "North Road East"),
    ("L01", +1,  18, 130, ["c", "s"],                                "West Lane South"),
    ("L01", -1,  24, 130, ["c"],                                     "West Lane North"),
    ("L02", +1,  20, 110, ["c", "s"],                                "SE Lane North"),
    ("L02", -1,  30, 110, ["cs"],                                    "SE Lane South"),
    ("L03", -1,  16, 125, ["c", "s"],                                "SW Lane North"),
    ("L04", +1,   8,  90, ["m"],                                     "NE Lane West"),
    ("L04", -1,   8,  90, ["c", "s"],                                "NE Lane East"),
]

# --------------------------------------------------------------------------
# Farmland zones (axis-aligned rectangles) -> field patches
# --------------------------------------------------------------------------
FIELD_ZONES = [
    dict(name="West",       x=(-470, -150), y=(-210, 220), cell=(34, 46)),
    dict(name="SouthWest",  x=(-360,  -45), y=(-470, -160), cell=(42, 32)),
    dict(name="SouthEast",  x=(  25,  200), y=(-470, -150), cell=(36, 44)),
    dict(name="EastBank",   x=( 205,  480), y=(-300,  200), cell=(40, 36)),
    dict(name="NorthEast",  x=(  20,  140), y=( 150,  330), cell=(30, 36)),
    dict(name="NorthWest",  x=(-300,  -95), y=( 150,  300), cell=(34, 30)),
]
FIELD_GAP = 1.6
CROPS = [  # name, weight
    ("mustard", 0.30), ("wheat", 0.34), ("paddy", 0.16), ("fallow", 0.20),
]

TREE_COUNT_TARGET = 420
TREE_MIN_SPACING = 7.0

# --------------------------------------------------------------------------
# Review cameras.  ground=True -> z is height above terrain (eye level).
# --------------------------------------------------------------------------
CAMERAS = {
    "CAM_Aerial_Establishing_001": dict(pos=(310, -430, 175), target=(-10, 15, 0), lens=30),
    "CAM_Entrance_Ground_001":     dict(pos=(-25, -228, 1.7), target=(-8, -110, 4.5), lens=26, ground=True),
    "CAM_Chowk_Wide_001":          dict(pos=(14, -31, 1.7), target=(-8, 10, 5.5), lens=22, ground=True),
    "CAM_Market_Street_001":       dict(pos=(-112, 0.2, 1.7), target=(-20, 4, 3.0), lens=30, ground=True),
    "CAM_River_Ghat_001":          dict(pos=(196, 28, 4.0), target=(112, 60, 7.0), lens=30, ground=True),
    "CAM_TopDown_Plan":            dict(pos=(-10, -5, 900), target=(-10, -5, 0), ortho=True, ortho_scale=400),
    "CAM_TopDown_Context":         dict(pos=(-10, -40, 1500), target=(-10, -40, 0), ortho=True, ortho_scale=1150),
}

# --------------------------------------------------------------------------
# Blockout palette (sRGB hex).  Also recorded in WORLD_BIBLE.md.
# --------------------------------------------------------------------------
PALETTE = {
    "wall_lime_white":   "#EDE5D3",
    "wall_clay_ochre":   "#B98758",
    "wall_mud_brown":    "#9E7653",
    "wall_pastel_blue":  "#8DB2C8",
    "wall_pastel_yellow":"#E3C47D",
    "wall_pastel_pink":  "#D9A6A0",
    "wall_mint":         "#A8C6A2",
    "wall_sandstone":    "#D6A47A",
    "roof_terracotta":   "#A5523A",
    "roof_thatch":       "#B69862",
    "roof_concrete":     "#BDB5A8",
    "roof_tin":          "#8C8F8E",
    "plinth_stone":      "#8C8378",
    "wood_dark":         "#4A3426",
    "shutter_metal":     "#6F7B80",
    "awning_red":        "#B4473A",
    "awning_blue":       "#3D6F95",
    "awning_green":      "#4F8452",
    "temple_white":      "#F2E5C9",
    "saffron":           "#E8761E",
    "road_tar":          "#57534F",
    "road_dirt":         "#B49A76",
    "road_dirt_main":    "#A88D69",
    "road_stone":        "#A69A87",
    "chowk_stone":       "#B3A58E",
    "grass_dry":         "#8A9452",
    "grass_lush":        "#6F8C45",
    "rock":              "#8A7E72",
    "water":             "#3C7884",
    "foliage_mango":     "#3E6A34",
    "foliage_neem":      "#5F8C3D",
    "foliage_banyan":    "#46733A",
    "foliage_palm":      "#557D3A",
    "foliage_amaltas":   "#E9B923",
    "bark":              "#5B4636",
    "crop_mustard":      "#D8B72D",
    "crop_wheat":        "#8EAA45",
    "crop_paddy":        "#67A83F",
    "crop_fallow":       "#9A7A55",
    "label_plate":       "#1E1E1E",
    "label_text":        "#FFFFFF",
}

WALL_CHOICES = {
    "house_small":  ["wall_clay_ochre", "wall_mud_brown", "wall_clay_ochre"],
    "house_common": ["wall_lime_white", "wall_pastel_blue", "wall_pastel_yellow", "wall_mint", "wall_lime_white"],
    "house_middle": ["wall_pastel_yellow", "wall_lime_white", "wall_pastel_pink"],
    "house_rich":   ["wall_sandstone", "wall_pastel_pink"],
    "shop":         ["wall_lime_white", "wall_pastel_blue", "wall_pastel_yellow", "wall_mint", "wall_pastel_pink"],
    "shop_2storey": ["wall_lime_white", "wall_pastel_yellow", "wall_pastel_blue"],
    "cattle_shed":  ["wall_mud_brown"],
    "grain_store":  ["wall_clay_ochre"],
    "temple":       ["temple_white"],
    "panchayat":    ["wall_pastel_yellow"],
    "school":       ["wall_pastel_yellow"],
}
