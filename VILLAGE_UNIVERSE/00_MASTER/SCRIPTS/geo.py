"""Geometry and terrain helpers shared by the village build scripts.  No bpy here."""
import math
import numpy as np

import config_layout as C


def smoothstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def catmull_rom(ctrl, samples=16):
    pts = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = (np.array(p, float) for p in pts[i - 1:i + 3])
        for j in range(samples):
            t = j / samples
            out.append(0.5 * (2 * p1 + (p2 - p0) * t
                              + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (3 * p1 - p0 - 3 * p2 + p3) * t ** 3))
    out.append(np.array(ctrl[-1], float))
    return np.array(out)


def resample(poly, step):
    seg = np.diff(poly, axis=0)
    cum = np.concatenate([[0.0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])
    n = max(2, int(math.ceil(cum[-1] / step)) + 1)
    ts = np.linspace(0.0, cum[-1], n)
    return np.stack([np.interp(ts, cum, poly[:, 0]), np.interp(ts, cum, poly[:, 1])], 1), ts


class Path2D:
    """Smoothed polyline parameterised by arc length t (metres)."""

    def __init__(self, ctrl, width=0.0, step=1.0):
        self.pts, self.ts = resample(catmull_rom(ctrl), step)
        self.length = float(self.ts[-1])
        self.width = float(width)

    def point(self, t):
        t = min(max(t, 0.0), self.length)
        return np.array([np.interp(t, self.ts, self.pts[:, 0]), np.interp(t, self.ts, self.pts[:, 1])])

    def tangent(self, t):
        d = self.point(t + 1.0) - self.point(t - 1.0)
        return d / (np.linalg.norm(d) + 1e-9)

    def normal(self, t):
        """Left-hand normal (side=+1)."""
        d = self.tangent(t)
        return np.array([-d[1], d[0]])

    def nearest_t(self, p):
        d = np.hypot(self.pts[:, 0] - p[0], self.pts[:, 1] - p[1])
        i = int(np.argmin(d))
        return float(self.ts[i]), float(d[i])


def dist_to_polyline(P, poly):
    P = np.asarray(P, float).reshape(-1, 2)
    best = np.full(len(P), np.inf)
    for a, b in zip(poly[:-1], poly[1:]):
        ab = b - a
        L2 = float(ab @ ab)
        if L2 < 1e-12:
            continue
        t = np.clip(((P - a) @ ab) / L2, 0.0, 1.0)
        qx = a[0] + t * ab[0]
        qy = a[1] + t * ab[1]
        np.minimum(best, np.hypot(P[:, 0] - qx, P[:, 1] - qy), out=best)
    return best


class OBB:
    """Oriented footprint.  u = frontage axis, v = depth axis (points AWAY from the street).
    The front door is on the -v side."""

    def __init__(self, cx, cy, hw, hd, ang):
        self.c = np.array([cx, cy], float)
        self.hw, self.hd, self.ang = float(hw), float(hd), float(ang)
        self.u = np.array([math.cos(ang), math.sin(ang)])
        self.v = np.array([-math.sin(ang), math.cos(ang)])

    def corners(self, grow=0.0):
        hw, hd = self.hw + grow, self.hd + grow
        return np.array([self.c + sx * hw * self.u + sy * hd * self.v
                         for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])

    def dist_points(self, P):
        d = np.asarray(P, float).reshape(-1, 2) - self.c
        lx = np.abs(d @ self.u) - self.hw
        ly = np.abs(d @ self.v) - self.hd
        return np.hypot(np.maximum(lx, 0.0), np.maximum(ly, 0.0))

    def contains(self, P, grow=0.0):
        d = np.asarray(P, float).reshape(-1, 2) - self.c
        return (np.abs(d @ self.u) <= self.hw + grow) & (np.abs(d @ self.v) <= self.hd + grow)

    def overlaps(self, other, margin=0.0):
        A = self.corners(margin / 2.0)
        B = other.corners(margin / 2.0)
        for ax in (self.u, self.v, other.u, other.v):
            pa, pb = A @ ax, B @ ax
            if pa.max() < pb.min() or pb.max() < pa.min():
                return False
        return True


def obb_facing(c, target, w, d):
    """Footprint centred at c whose front (-v) looks toward target."""
    v = np.asarray(c, float) - np.asarray(target, float)
    v /= (np.linalg.norm(v) + 1e-9)
    u = np.array([v[1], -v[0]])
    return OBB(c[0], c[1], w / 2.0, d / 2.0, math.atan2(u[1], u[0]))


def obb_on_road(path, t, side, w, d, setback):
    pt = path.point(t)
    n = path.normal(t) * side
    c = pt + n * (path.width / 2.0 + setback + d / 2.0)
    u = np.array([n[1], -n[0]])
    return OBB(c[0], c[1], w / 2.0, d / 2.0, math.atan2(u[1], u[0]))


_RIVER = None


def river_path():
    global _RIVER
    if _RIVER is None:
        _RIVER = Path2D(C.RIVER_CTRL, 30.0, step=5.0)
    return _RIVER


def river_distance(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    shape = np.broadcast(x, y).shape
    P = np.stack([np.broadcast_to(x, shape).ravel(), np.broadcast_to(y, shape).ravel()], 1)
    return dist_to_polyline(P, river_path().pts).reshape(shape)


def terrain_height(x, y):
    """Analytic terrain height (vectorised).  The terrain mesh, roads, buildings and
    vegetation all sample this same function so nothing floats or sinks."""
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    shape = np.broadcast(x, y).shape
    x = np.broadcast_to(x, shape).ravel()
    y = np.broadcast_to(y, shape).ravel()

    r = np.hypot(x / 1.15, y)
    core = smoothstep(170.0, 340.0, r)          # 0 inside the village, 1 outside
    h = 0.40 * np.sin(x * 0.013 + 1.3) * np.cos(y * 0.011) + 0.22 * np.sin(x * 0.029 + y * 0.021 + 0.7)
    h += core * (2.4 * np.sin(x * 0.006 + 0.4) * np.sin(y * 0.005 + 1.1) + 1.1 * np.sin(x * 0.017 - y * 0.013))
    h += -0.0035 * x * (1.0 - core)            # village drains gently toward the river
    h += 2.5 * core                             # open country sits above the river-mud band (shader paints z<0 as bank)
    tx, ty = C.TEMPLE_POS
    h += 1.3 * np.exp(-((x - tx) ** 2 + (y - ty) ** 2) / 30.0 ** 2)   # temple on a slight rise

    hill = smoothstep(560.0, 1000.0, y)         # low northern foothills (v2: the rocky massif is the backdrop)
    ridge = (0.65 + 0.30 * np.sin(x * 0.009 + 0.5) + 0.12 * np.sin(x * 0.031 + 2.0)
             + 0.06 * np.sin(x * 0.07 + y * 0.05))
    h += (hill ** 1.6) * 38.0 * ridge * (1.0 - massif_lateral_mask(x))
    if MASSIF is not None:                      # massif apron/flanks shaped BEFORE the river carve
        h = massif_shape(x, y, h)

    d = dist_to_polyline(np.stack([x, y], 1), river_path().pts)
    k = 1.0 - smoothstep(9.0, 24.0 + 70.0 * hill, d)
    h = h * (1.0 - k) + C.RIVER_BED_Z * k
    for cut in EXTRA_CUTS:          # e.g. the ghat steps cut into the bank (set by build_master_v2)
        h = cut(x, y, h)
    return h.reshape(shape)


EXTRA_CUTS = []

# ---------------------------------------------------------------------------
# Rocky massif integration (set by build_master_v2 from the linked library mesh).
#   MASSIF = dict(ox, oy, z0, xs, ys, H)  H[j, i] = massif height (library-local z) at (xs[i], ys[j]), NaN = no mesh
# Inside the footprint the terrain is pushed just under the rock (only where the rock rises above the apron);
# outside it the terrain is raised to bury the massif's cliff-wall sides and falls off over ~120-280 m.
# ---------------------------------------------------------------------------
MASSIF = None
MASSIF_X_HALF = 460.0
MASSIF_Y = (-120.0, 520.0)


def massif_lateral_mask(x):
    """1 across the massif's width (old foothills removed in front of it), fading out 150 m beyond its sides."""
    if MASSIF is None:
        return np.zeros_like(np.asarray(x, float))
    dx = np.abs(np.asarray(x, float) - MASSIF["ox"]) - MASSIF_X_HALF
    return 1.0 - smoothstep(-60.0, 150.0, dx)


def _massif_lookup(lx, ly):
    M = MASSIF
    xs, ys, H = M["xs"], M["ys"], M["H"]
    fx = np.clip((lx - xs[0]) / (xs[1] - xs[0]), 0, len(xs) - 1.001)
    fy = np.clip((ly - ys[0]) / (ys[1] - ys[0]), 0, len(ys) - 1.001)
    i0, j0 = fx.astype(int), fy.astype(int)
    tx, ty = fx - i0, fy - j0
    Hn = np.nan_to_num(H, nan=0.0)
    return (Hn[j0, i0] * (1 - tx) * (1 - ty) + Hn[j0, i0 + 1] * tx * (1 - ty)
            + Hn[j0 + 1, i0] * (1 - tx) * ty + Hn[j0 + 1, i0 + 1] * tx * ty)


def massif_shape(x, y, h):
    M = MASSIF
    lx, ly = x - M["ox"], y - M["oy"]
    x0, x1 = -MASSIF_X_HALF + 4.0, MASSIF_X_HALF - 4.0
    y0, y1 = MASSIF_Y[0] + 4.0, MASSIF_Y[1] - 24.0
    inside = (lx > x0) & (lx < x1) & (ly > y0) & (ly < y1)
    cx, cy = np.clip(lx, x0, x1), np.clip(ly, y0, y1)
    Hc = _massif_lookup(cx, cy)
    out = h.copy()
    # inside: sink the terrain under the rock wherever the rock clears the (buried) apron
    w = smoothstep(1.0, 6.0, Hc)
    under = np.minimum(h, M["z0"] + Hc - 1.2)
    out = np.where(inside, h * (1 - w) + under * w, out)
    # outside: raise the ground to meet the rock edge, falling off with distance
    d = np.hypot(lx - cx, ly - cy)
    R = 160.0 + 2.2 * Hc                        # long, gentle flanks (no steep scar against the rock)
    s = smoothstep(0.0, 1.0, d / R)
    T = M["z0"] + Hc + 1.0
    raised = np.maximum(h, T * (1 - s) + h * s)
    out = np.where(inside, out, np.where(Hc > 3.0, raised, h))
    return out
