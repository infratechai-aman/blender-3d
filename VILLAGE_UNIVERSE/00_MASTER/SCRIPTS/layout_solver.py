"""Places landmark and house plots along the road network with collision checks.
Deterministic: same config -> same plots.  No bpy here, so it can be tested quickly."""
import random

import numpy as np

import config_layout as C
from geo import Path2D, obb_facing, obb_on_road, river_path, terrain_height


def build_paths():
    return {rid: Path2D(r["ctrl"], r["width"], step=1.0) for rid, r in C.ROADS.items()}


class LayoutSolver:
    def __init__(self):
        self.paths = build_paths()
        self.river = river_path()
        self.plots = []
        self.log = []

    # ------------------------------------------------------------------
    def check(self, obb, kind):
        for rid, p in self.paths.items():
            if obb.dist_points(p.pts).min() < p.width / 2.0 + C.ROAD_MARGIN:
                return "road " + rid
        if obb.dist_points(self.river.pts).min() < C.RIVER_CLEAR:
            return "river"
        for cx, cy, r in C.CIRCLE_OBSTACLES:
            if obb.dist_points([(cx, cy)])[0] < r:
                return "reserved area"
        for pl in self.plots:
            m = 0.25 if (kind in C.SHOP_KINDS and pl["kind"] in C.SHOP_KINDS) else C.BUILDING_GAP
            if obb.overlaps(pl["obb"], m):
                return "overlaps plot %d" % pl["num"]
        cs = obb.corners()
        hs = terrain_height(cs[:, 0], cs[:, 1])
        if hs.max() - hs.min() > C.MAX_SLOPE_RANGE:
            return "slope"
        return None

    def add(self, kind, obb, hood, road, label=None, key=None, rng=None):
        rng = rng or random.Random(len(self.plots))
        fam = C.KINDS[kind]["family"]
        cs = obb.corners()
        hs = terrain_height(np.append(cs[:, 0], obb.c[0]), np.append(cs[:, 1], obb.c[1]))
        plot = dict(
            num=len(self.plots) + 1, kind=kind, family=fam, key=key, label=label or fam,
            hood=hood, road=road, obb=obb,
            x=float(obb.c[0]), y=float(obb.c[1]), z=float(hs.max()),
            w=obb.hw * 2.0, d=obb.hd * 2.0, rot=obb.ang,
            wall=rng.choice(C.WALL_CHOICES[fam]), seed=rng.randint(0, 10 ** 6),
        )
        self.plots.append(plot)
        return plot

    # ------------------------------------------------------------------
    def place_landmarks(self):
        for lm in C.LANDMARKS:
            spec = C.KINDS[lm["kind"]]
            w, d = spec["w"], spec["d"]
            if lm["mode"] == "abs":
                obb = obb_facing(lm["pos"], lm["face"], w, d)
                road = "-"
            else:
                obb = obb_on_road(self.paths[lm["road"]], lm["t"], lm["side"], w, d, lm["setback"])
                road = lm["road"]
            why = self.check(obb, lm["kind"])
            if why:
                self.log.append("WARN landmark %s: %s (placed anyway)" % (lm["key"], why))
            self.add(lm["kind"], obb, "Landmark", road, label=lm["label"], key=lm["key"],
                     rng=random.Random(lm["key"]))

    def run_frontage(self, fr):
        rid, side, t0, t1, seq, hood = fr
        path = self.paths[rid]
        rng = random.Random("%s|%d|%d" % (rid, side, t0))
        t = float(t0)
        for kind in seq:
            spec = C.KINDS[kind]
            w = spec["w"] * rng.uniform(0.92, 1.08)
            d = spec["d"] * rng.uniform(0.92, 1.08)
            setback = rng.uniform(*spec["setback"])
            placed = False
            last_why = "no room"
            while t + w <= min(t1, path.length):
                obb = obb_on_road(path, t + w / 2.0, side, w, d, setback)
                why = self.check(obb, kind)
                if why is None:
                    self.add(kind, obb, hood, rid, rng=rng)
                    t += w + rng.uniform(*spec["gap"])
                    placed = True
                    break
                last_why = why
                t += 1.0
            if not placed:
                self.log.append("SKIP %-4s %s side %+d (%s): %s" % (kind, rid, side, hood, last_why))

    def solve(self):
        self.place_landmarks()
        for fr in C.FRONTAGES:
            self.run_frontage(fr)
        return self.plots

    def summary(self):
        counts = {}
        for p in self.plots:
            counts[p["family"]] = counts.get(p["family"], 0) + 1
        return counts


if __name__ == "__main__":
    s = LayoutSolver()
    plots = s.solve()
    for line in s.log:
        print(line)
    print("TOTAL", len(plots), s.summary())
