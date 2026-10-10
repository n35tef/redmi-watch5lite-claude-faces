"""PCB background: each watch element lives in an IC-style frame with pins on its edges.

Routing rules (checked by assertions at the end):
  * octilinear paths only: straight runs and 45-degree diagonals, never a turn sharper than 45 degrees
  * different nets keep >= CLEAR px apart wherever they are *visible*; parts hidden under a frame are
    free to cross (frames are drawn over the traces, like traces running under a package)
  * the one explicit via hop is where a net swaps sides under another
"""
import itertools
import json
import os
import random
import sys
from PIL import Image, ImageDraw

PAL = json.loads(os.environ.get("PAL", "{}"))   # optional palette override (see palette_previews)


def pc(key, default):
    return tuple(PAL.get(key, default))


W, H, S = 410, 502, 4
DY = 40  # stack moved down (the logo frame stays at a fixed position)
OUT = sys.argv[1]
rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 5)

BG = pc("bg", (3, 6, 16))
RED = pc("w1", (36, 60, 140))     # primary wire colour (~80% of nets): muted royal blue
BLUE = pc("w2", (44, 104, 160))   # accent wire colour (~20% of nets): muted azure
PAD = pc("pad", (58, 88, 170))    # vias / pads / pins on used nets
BODY = pc("body", (10, 14, 32))
EDGE = pc("edge", (68, 88, 135))
PIN_DIM = pc("pin_dim", (22, 28, 52))  # unused pins: barely lighter than the background
PINLEN, PINW, PITCH = 4, 3, 10
CLEAR = 5.5  # min centre-line distance between different nets (visible parts)
TW = 3       # trace width

img = Image.new("RGB", (W * S, H * S), BG)
d = ImageDraw.Draw(img)


def sc(v):
    return v * S


def rect(x0, y0, x1, y1, **kw):
    d.rectangle((sc(x0), sc(y0), sc(x1), sc(y1)), **kw)


def line(pts, color, w=TW):
    p = [(sc(x), sc(y)) for x, y in pts]
    d.line(p, fill=color, width=sc(w), joint="curve")
    r = sc(w) / 2
    for x, y in (p[0], p[-1]):
        d.ellipse((x - r, y - r, x + r, y + r), fill=color)


def dim(c, k=0.45):
    return tuple(int(v * k + BG[i] * (1 - k)) for i, v in enumerate(c))


def nextcol():
    """~80% red, ~20% blue, scattered at random (seeded)."""
    return BLUE if rng.random() < 0.2 else RED


# name: (x0, y0, x1, y1, sides that carry pins)
FRAMES = {
    "date": (30, 60, 380, 106, "tblr"),
    "time": (16, 122, 394, 270, "tblr"),
    "heart": (30, 296, 180, 342, "tblr"),
    "steps": (216, 296, 380, 342, "tblr"),
    "batt": (30, 366, 180, 412, "tblr"),
    "temp": (216, 366, 380, 412, "tblr"),
    "logo": (162, 448, 248, 488, "t"),
}


def top(n):
    return FRAMES[n][1]


def bot(n):
    return FRAMES[n][3]


def pins_for(name):
    x0, y0, x1, y1, sides = FRAMES[name]
    out = []
    for x in range(x0 + 8, x1 - 7):
        if x % PITCH == 0:
            if "t" in sides:
                out.append(("t", x, y0))
            if "b" in sides:
                out.append(("b", x, y1))
    for y in range(y0 + 8, y1 - 7):
        if y % PITCH == 0:
            if "l" in sides:
                out.append(("l", x0, y))
            if "r" in sides:
                out.append(("r", x1, y))
    return out


def tip(side, x, y):
    return {"t": (x, y - PINLEN), "b": (x, y + PINLEN),
            "l": (x - PINLEN, y), "r": (x + PINLEN, y)}[side]


# ---------- geometry ----------
def _orient(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _pt_seg(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    t = 0 if dx == dy == 0 else max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return ((p[0] - ax - t * dx) ** 2 + (p[1] - ay - t * dy) ** 2) ** 0.5


def seg_dist(a, b, c, e):
    if (_orient(a, b, c) * _orient(a, b, e) < 0) and (_orient(c, e, a) * _orient(c, e, b) < 0):
        return 0.0
    return min(_pt_seg(a, c, e), _pt_seg(b, c, e), _pt_seg(c, a, b), _pt_seg(e, a, b))


def visible_segments(pts):
    """Sub-segments of a polyline that lie outside every frame (what you actually see)."""
    out = []
    for p, q in zip(pts, pts[1:]):
        dx, dy = q[0] - p[0], q[1] - p[1]
        inside = []
        for x0, y0, x1, y1, _ in FRAMES.values():
            lo, hi = 0.0, 1.0
            for pp, dd, a, b in ((p[0], dx, x0, x1), (p[1], dy, y0, y1)):
                if dd == 0:
                    if not (a < pp < b):
                        lo, hi = 1.0, 0.0
                else:
                    t0, t1 = (a - pp) / dd, (b - pp) / dd
                    lo, hi = max(lo, min(t0, t1)), min(hi, max(t0, t1))
            if lo < hi:
                inside.append((lo, hi))
        inside.sort()
        t = 0.0
        for lo, hi in inside + [(1.0, 1.0)]:
            if lo > t + 1e-9:
                out.append(((p[0] + dx * t, p[1] + dy * t), (p[0] + dx * lo, p[1] + dy * lo)))
            t = max(t, hi)
    return out


def vis_dist(A, B):
    return min((seg_dist(a, b, c, e) for a, b in A for c, e in B), default=99)


def clean(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if p != out[-1]:
            out.append(p)
    return out


placed = []   # (name, pts, visible segments)
nets = []     # (pts, colour)
tipcolor = {}
hops = []


def ok(pts):
    v = visible_segments(pts)
    return all(vis_dist(v, q) >= CLEAR for _, _, q in placed)


def put(name, pts, col):
    pts = clean(pts)
    nets.append((pts, col))
    placed.append((name, pts, visible_segments(pts)))
    tipcolor[(round(pts[0][0]), round(pts[0][1]))] = col
    tipcolor[(round(pts[-1][0]), round(pts[-1][1]))] = col


def seg(x0, y0, x1, y1, pad):
    """Shortest octilinear run from (x0,y0) to (x1,y1): `pad` px straight, one 45-degree diagonal, rest straight."""
    n = abs(x1 - x0)
    assert y1 - y0 >= n + pad, (x0, y0, x1, y1, pad)
    if n == 0:
        return [(x0, y0), (x1, y1)]
    return [(x0, y0), (x0, y0 + pad), (x1, y0 + pad + n), (x1, y1)]


def pad_options(G, n):
    free = G - n
    return [free // 2, 0, free, free // 4, 3 * free // 4]


def hidden_run(frame, xin, xout, a):
    """Path under a frame from the top edge at xin to the bottom edge at xout.
    Large shifts: diagonal - horizontal - diagonal. Small shifts: straight, one diagonal, straight."""
    T, B = top(frame), bot(frame)
    H_ = B - T
    n = abs(xout - xin)
    if n == 0:
        return [(xin, T), (xout, B)]
    s_ = -1 if xout < xin else 1
    if n >= H_:
        b = H_ - a
        return [(xin, T), (xin + s_ * a, T + a), (xout - s_ * b, T + a), (xout, B)]
    a = min(a, H_ - n)
    return [(xin, T), (xin, T + a), (xout, T + a + n), (xout, B)]


def gap_candidates(x0, y0, x1, y1):
    """All octilinear paths for one gap: a single diagonal at any height, or diagonal-horizontal-diagonal."""
    G, n = y1 - y0, abs(x1 - x0)
    out = []
    if n == 0:
        return [[(x0, y0), (x1, y1)]]
    for pad in range(0, G - n + 1, 2):
        out.append(seg(x0, y0, x1, y1, pad))
    sg = 1 if x1 > x0 else -1
    for dl in (3, 4, 5, 6):
        if n >= 2 * dl + 6 and 2 * dl <= G:
            for t in range(y0 + dl, y1 - dl + 1, 2):
                out.append([(x0, y0), (x0, t - dl), (x0 + sg * dl, t), (x1 - sg * dl, t), (x1, t + dl), (x1, y1)])
    return out


def chain(name, frames, xs, col=None, hid_a=None, optional=False, pads=None):
    """Net from the bottom pin of frames[0] to the top pin of frames[-1].
    xs[i] is an int, or (x_in, x_out) for a frame crossed *under* (entered at x_in, left at x_out)."""
    col = col or nextcol()
    k = len(frames) - 1
    xin = lambda v: v[0] if isinstance(v, tuple) else v
    xout = lambda v: v[1] if isinstance(v, tuple) else v
    gaps = []
    for i in range(k):
        y0 = bot(frames[i]) + (PINLEN if i == 0 else 0)
        y1 = top(frames[i + 1]) - (PINLEN if i + 1 == k else 0)
        gaps.append((xout(xs[i]), y0, xin(xs[i + 1]), y1))
    cands = [gap_candidates(*g) for g in gaps]
    if pads:  # fixed diagonal height -> neat parallel fan
        cands = [[seg(*g, p)] for g, p in zip(gaps, pads)]
    for _ in range(500):
        pts = []
        for i, c in enumerate(cands):
            pts += rng.choice(c)
            if i + 1 < k:
                pts += hidden_run(frames[i + 1], xin(xs[i + 1]), xout(xs[i + 1]), (hid_a or 20))
        pts = clean(pts)
        if ok(pts):
            put(name, pts, col)
            return True
    if optional:
        return False
    raise RuntimeError("cannot route " + name)


def vnet(name, a, b, xa, xb, col=None, optional=False, pad=None):
    return chain(name, [a, b], [xa, xb], col, optional=optional, pads=[pad] if pad is not None else None)


def hnet(name, a, b, ya, yb, col=None):
    x0, x1 = FRAMES[a][2] + PINLEN, FRAMES[b][0] - PINLEN
    cands = gap_candidates(ya, x0, yb, x1)  # (cross, along) = (y, x)
    rng.shuffle(cands)
    for c in cands:
        pts = clean([(a_, c_) for c_, a_ in c])
        if ok(pts):
            put(name, pts, col or nextcol())
            return
    raise RuntimeError("cannot route " + name)


def mirror(pts):
    return [(W - x, y) for x, y in pts]


# ---------- side wires (left margin; mirrored to the right) ----------
def lpins(name):
    return sorted(y for side, x, y in pins_for(name) if side == "l")


def rpins(name):
    return sorted(y for side, x, y in pins_for(name) if side == "r")


dl, cl, hl, bl = lpins("date"), lpins("time"), lpins("heart"), lpins("batt")
a1, a2, c1, c2 = dl[-2], dl[-1], cl[0], cl[1]
# date -> clock side pins: two nested C-shaped wires (outer one joins first-to-last pins so they never cross)
sideA = [tip("l", 30, a1), (24, a1), (13, a1 + 11), (13, c2 - 11), (24, c2), tip("l", 30, c2)]
sideB = [tip("l", 30, a2), (20, a2 + 6), (20, c1 - 6), tip("l", 30, c1)]
# clock -> heart / battery side buses
yo, yi = cl[-3], cl[-1]
outer = [tip("l", 30, yo), (22, yo), (13, yo + 9), (13, bl[0] - 13), tip("l", 30, bl[0])]
inner = [tip("l", 30, yi), (19, yi + 7), (19, hl[0] - 7), tip("l", 30, hl[0])]
for nm, pts in (("sideA", sideA), ("sideB", sideB), ("bus_outer", outer), ("bus_inner", inner)):
    put(nm + "_l", pts, nextcol())

# right side: deliberately NOT a mirror image - one date->clock C-wire and two buses, other pins and margins
dr_, cr_, sr_, tr_ = rpins("date"), rpins("time"), rpins("steps"), rpins("temp")
ra, rc = dr_[-3], cr_[1]
sideR = [tip("l", 30, ra), (24, ra), (14, ra + 10), (14, rc - 10), (24, rc), tip("l", 30, rc)]
r2a, r2b = cr_[5], sr_[1]   # inner bus starts lower than the outer one -> no crossing
busR1 = [tip("l", 30, r2a), (24, r2a), (20, r2a + 4), (20, r2b - 4), (24, r2b), tip("l", 30, r2b)]
r3a, r3b = cr_[3], tr_[-1]
busR2 = [tip("l", 30, r3a), (22, r3a), (13, r3a + 9), (13, r3b - 13), tip("l", 30, r3b)]
for nm, pts in (("sideR", sideR), ("busR1", busR1), ("busR2", busR2)):
    put(nm + "_r", mirror(pts), nextcol())


# ---------- swap pair: B hops under A with two vias ----------
def swap_pair(a, b, xa, xb):
    col_a, col_b = nextcol(), nextcol()
    a0, a1 = bot(a) + PINLEN, top(b) - PINLEN
    n = abs(xb - xa)
    pre = (a1 - a0 - n) // 2
    A = [(xa, a0), (xa, a0 + pre), (xb, a0 + pre + n), (xb, a1)]
    B = [(xb, a0), (xb, a0 + pre), (xa, a0 + pre + n), (xa, a1)]
    put("swapA", A, col_a)
    put("swapB", B, col_b)
    s, e = B[1], B[2]
    hops.append(((s[0] + (e[0] - s[0]) * 0.3, s[1] + (e[1] - s[1]) * 0.3),
                 (s[0] + (e[0] - s[0]) * 0.7, s[1] + (e[1] - s[1]) * 0.7), col_b))


swap_pair("time", "steps", 280, 290)

# ---------- date -> clock: four straight wires on each side (uneven pin spacing) ----------
for x in (40, 50, 70, 80):
    vnet(f"dl{x}", "date", "time", x, x)
for x in (340, 350, 360, 370):
    vnet(f"dr{x}", "date", "time", x, x)

# ---------- date (bottom-right pins) -> heart (top pins): bundle running diagonally under the clock ----------
for k, (xa, xb) in enumerate([(260, 80), (280, 90), (290, 100), (300, 110)]):
    chain(f"bundle{k}", ["date", "time", "heart"], [xa, (xa, xb), xb], hid_a=14 + 6 * k)

# ---------- date (middle bottom pins) -> heart (middle/right top pins): second bundle, uneven ----------
for k, (xa, xb) in enumerate([(190, 140), (200, 150), (220, 160), (230, 170)]):
    chain(f"bundleB{k}", ["date", "time", "heart"], [xa, (xa, xb), xb], hid_a=8 + 4 * k)

# ---------- long wires passing *under* the components in between ----------
chain("L_date_batt", ["date", "time", "heart", "batt"], [130, (130, 125), (125, 125), 130])
chain("L_date_temp", ["date", "time", "steps", "temp"], [310, (310, 310), (310, 310), 310])

# ---------- neighbour nets: diagonal pin-to-pin links, irregular ----------
vnet("bcl0", "time", "heart", 50, 60)
vnet("bcl1", "time", "heart", 170, 150, optional=True)
for i, (xa, xb) in enumerate([(230, 240), (330, 350), (370, 360)]):
    vnet(f"bcr{i}", "time", "steps", xa, xb)
for i, (xa, xb) in enumerate([(50, 50), (70, 90), (110, 100), (160, 160)]):
    vnet(f"cd{i}", "heart", "batt", xa, xb)
for i, (xa, xb) in enumerate([(230, 240), (270, 270), (360, 350)]):
    vnet(f"cdr{i}", "steps", "temp", xa, xb)
padL, padR = rng.choice([0, 2, 4]), rng.choice([0, 2, 4])   # one diagonal height per bundle keeps parallel wires clear
for i, (xa, xb) in enumerate([(150, 170), (160, 180), (170, 190)]):
    vnet(f"de{i}", "batt", "logo", xa, xb, pad=padL)
for i, (xa, xb) in enumerate([(240, 220), (260, 240)]):   # deliberately not a mirror of the left side
    vnet(f"der{i}", "temp", "logo", xa, xb, pad=padR)
hr, br = rpins("heart"), rpins("batt")
hnet("hr0", "heart", "steps", hr[0], hr[1])
hnet("hr1", "heart", "steps", hr[1], hr[2])
hnet("hr2", "batt", "temp", br[0], br[1])
hnet("hr3", "batt", "temp", br[1], br[2])

# ---------- decorative wiring (connects to nothing): above the date frame, below battery / temperature ----------
R_SCREEN = 104
deco_vias = []
runoff_names = set()


BZ_GAP_M = 17     # via centres stay >= 17 px from the screen edge: bezel (8) + ~5 px air + via radius


def inside(p):
    """Inside the screen minus a margin that leaves a clear gap to the bezel (rounded corners included)."""
    x, y = p
    M, R = BZ_GAP_M, 92
    if x < M or x > W - M or y < M or y > H - M:
        return False
    cx = M + R if x < M + R else (W - M - R if x > W - M - R else None)
    cy = M + R if y < M + R else (H - M - R if y > H - M - R else None)
    if cx is not None and cy is not None:
        return (x - cx) ** 2 + (y - cy) ** 2 <= R * R
    return True


def deco_net(name, frame, side, px, tries=120):
    x0, y0, x1, y1, _ = FRAMES[frame]
    py = y0 if side == "t" else y1
    sx, sy = tip(side, px, py)
    dirn = -1 if side == "t" else 1
    for _ in range(tries):
        run_off = False
        L = rng.randrange(26, 70, 2)
        shifts = [rng.choice([-30, -20, -10, 0, 0, 10, 20, 30])]
        if rng.random() < 0.4:
            shifts.append(rng.choice([-20, -10, 10, 20]))
        need = sum(abs(v) for v in shifts)
        if need + 2 > L:
            continue
        free = L - need
        cuts = sorted(rng.randrange(0, free + 1, 2) for _ in range(len(shifts)))
        verts = [cuts[0]] + [cuts[i] - cuts[i - 1] for i in range(1, len(cuts))] + [free - cuts[-1]]
        if len(shifts) > 1 and verts[1] < 16 and shifts[0] * shifts[1] < 0:
            continue  # opposite diagonals with a short straight between them read as a 90-degree kink
        along, x = 0, sx
        pts = [(sx, sy)]
        for v, sh in zip(verts, shifts):
            along += v
            pts.append((x, sy + dirn * along))
            along += abs(sh)
            x += sh
            pts.append((x, sy + dirn * along))
        along += verts[-1]
        pts.append((x, sy + dirn * along))
        pts = clean(pts)
        if len(pts) < 2 or not all(inside(p) for p in pts):
            continue
        if not ok(pts):
            continue
        put(name, pts, nextcol())
        runoff_names.add(name)           # (kept as the set of decorative wires: passives may go on them)
        deco_vias.append(pts[-1])        # every hanging end gets a via
        return True
    return False


for i, px in enumerate([60, 70, 90, 110, 130, 150, 250, 270, 290, 310, 330, 350]):
    deco_net(f"deco_top{i}", "date", "t", px)
for i, px in enumerate([40, 50, 70, 90, 110, 130]):
    deco_net(f"deco_bl{i}", "batt", "b", px)
for i, px in enumerate([270, 290, 310, 330, 350, 370]):
    deco_net(f"deco_br{i}", "temp", "b", px)

# ---------- checks ----------
for name, pts, _ in placed:
    for i in range(1, len(pts) - 1):
        ax, ay = pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]
        bx, by = pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]
        la, lb = (ax * ax + ay * ay) ** 0.5, (bx * bx + by * by) ** 0.5
        assert (ax * bx + ay * by) / (la * lb) > 0.70, f"{name}: bend sharper than 45 degrees at {pts[i]}"
    for i in range(len(pts) - 1):
        dx, dy = abs(pts[i + 1][0] - pts[i][0]), abs(pts[i + 1][1] - pts[i][1])
        assert dx == 0 or dy == 0 or abs(dx - dy) < 1e-6, f"{name}: not 0/45/90 at {pts[i]}"
for (n1, _, v1), (n2, _, v2) in itertools.combinations(placed, 2):
    if {n1, n2} == {"swapA", "swapB"}:
        continue
    assert vis_dist(v1, v2) >= CLEAR - 0.01, f"clearance: {n1} vs {n2}"

# ---------- draw ----------
for pts, col in nets:
    line(pts, col)

for p, q, col in hops:
    line([p, q], BG, TW + 1)
    line([p, q], dim(col), 2)
    for v in (p, q):
        r = 3.6
        d.ellipse((sc(v[0] - r), sc(v[1] - r), sc(v[0] + r), sc(v[1] + r)), fill=PAD)
        r = 1.5
        d.ellipse((sc(v[0] - r), sc(v[1] - r), sc(v[0] + r), sc(v[1] + r)), fill=BG)

for v in deco_vias:
    r = 3.6
    d.ellipse((sc(v[0] - r), sc(v[1] - r), sc(v[0] + r), sc(v[1] + r)), fill=PAD)
    r = 1.5
    d.ellipse((sc(v[0] - r), sc(v[1] - r), sc(v[0] + r), sc(v[1] + r)), fill=BG)

# ---------- small passive parts, inline on visible vertical runs between components ----------
cands = []   # (name, x, y_centre, kind)
for name, pts, vis in placed:
    if name.startswith(("bus", "side", "swap")):
        continue
    kind = "edge" if name in runoff_names else ("skip" if name.startswith("deco") else "gap")
    if kind == "skip":
        continue
    for p, q in vis:
        if abs(p[0] - q[0]) < 1e-6 and abs(q[1] - p[1]) >= 19:
            cands.append((name, p[0], (p[1] + q[1]) / 2, kind))
rng.shuffle(cands)
chosen = []


def free(c):
    return all(abs(c[2] - o[2]) > 16 or abs(c[1] - o[1]) > 26 for o in chosen)


in_date_gap = lambda c: bot("date") <= c[2] <= top("time")
all_vias = deco_vias + [v for p, q, _ in hops for v in (p, q)]
near_via = lambda c: any((c[1] - vx) ** 2 + (c[2] - vy) ** 2 < 16 ** 2 for vx, vy in all_vias)
cands = [c for c in cands if c[3] != "edge" and not near_via(c)]   # no passives on the wires that end in a via
for c in cands:                      # 2) the rest in the gaps, but at most TWO between date and clock
    if len(chosen) >= 10:
        break
    if c[3] == "gap" and free(c) and not (in_date_gap(c) and sum(in_date_gap(o) for o in chosen) >= 2):
        chosen.append(c)
chosen = [(c[0], c[1], c[2]) for c in chosen]

for name, cx, cy in chosen:  # every passive is the same SMD part: body with two end terminations
    rect(cx - 3.5, cy - 6.5, cx + 3.5, cy + 6.5, fill=BODY, outline=EDGE, width=sc(1))
    rect(cx - 3.5, cy - 6.5, cx + 3.5, cy - 4.5, fill=PAD)
    rect(cx - 3.5, cy + 4.5, cx + 3.5, cy + 6.5, fill=PAD)

# frames (drawn over traces, so nets vanish underneath) and pins
for name, (x0, y0, x1, y1, _) in FRAMES.items():
    for side, px, py in pins_for(name):
        tx, ty = tip(side, px, py)
        col = tipcolor.get((tx, ty), PIN_DIM)
        if side in "tb":
            rect(px - PINW / 2, min(py, ty), px + PINW / 2, max(py, ty), fill=col)
        else:
            rect(min(px, tx), py - PINW / 2, max(px, tx), py + PINW / 2, fill=col)
    rect(x0, y0, x1, y1, fill=BODY, outline=EDGE, width=sc(2))
    r = 2.5
    d.ellipse((sc(x0 + 5 - r), sc(y0 + 5 - r), sc(x0 + 5 + r), sc(y0 + 5 + r)), outline=EDGE, width=sc(1))

# ---------- bezel: a ring with radial tick marks and corner rivets, drawn over everything on the board ----------
import math

BZ_OUT, BZ_IN = 1, 8                 # band spans 1..8 px from the screen edge
BZ_R = 108                           # corner radius of the outer edge
BAND, BAND_EDGE_O, BAND_EDGE_I = pc("band", (14, 22, 50)), pc("band_o", (96, 140, 235)), pc("band_i", (58, 90, 170))
TICK_MAJOR, TICK_MINOR = pc("tick_maj", (235, 130, 95)), pc("tick_min", (62, 94, 180))


def rr_box(m):
    return (m * S, m * S, (W - m) * S - 1, (H - m) * S - 1)


ring = Image.new("L", (W * S, H * S), 0)
rd = ImageDraw.Draw(ring)
rd.rounded_rectangle(rr_box(BZ_OUT), radius=BZ_R * S, fill=255)
rd.rounded_rectangle(rr_box(BZ_IN), radius=(BZ_R - (BZ_IN - BZ_OUT)) * S, fill=0)
img.paste(Image.new("RGB", img.size, BAND), mask=ring)
d.rounded_rectangle(rr_box(BZ_OUT), radius=BZ_R * S, outline=BAND_EDGE_O, width=S)
d.rounded_rectangle(rr_box(BZ_IN), radius=(BZ_R - (BZ_IN - BZ_OUT)) * S, outline=BAND_EDGE_I, width=S)


def rr_point(m, r, s_):
    """Point + inward normal at arc-length s_ along the rounded rectangle inset m (clockwise from top centre)."""
    a, b, c, e = m, m, W - m, H - m
    segs = []  # (length, fn(t)->(x,y,nx,ny))
    hw, hh = (c - a) / 2 - r, (e - b) / 2 - r
    quarter = math.pi * r / 2
    def line(x0, y0, x1, y1, nx, ny):
        L = math.hypot(x1 - x0, y1 - y0)
        return (L, lambda t: (x0 + (x1 - x0) * t / L, y0 + (y1 - y0) * t / L, nx, ny))
    def arc(cx, cy, a0):
        return (quarter, lambda t: (cx + r * math.cos(a0 + t / r), cy + r * math.sin(a0 + t / r),
                                    -math.cos(a0 + t / r), -math.sin(a0 + t / r)))
    mx = (a + c) / 2
    segs = [line(mx, b, c - r, b, 0, 1), arc(c - r, b + r, -math.pi / 2), line(c, b + r, c, e - r, -1, 0),
            arc(c - r, e - r, 0), line(c - r, e, a + r, e, 0, -1), arc(a + r, e - r, math.pi / 2),
            line(a, e - r, a, b + r, 1, 0), arc(a + r, b + r, math.pi), line(a + r, b, mx, b, 0, 1)]
    L = sum(x[0] for x in segs)
    s_ %= L
    for ln, fn in segs:
        if s_ <= ln:
            return fn(s_)
        s_ -= ln
    return segs[-1][1](segs[-1][0])


mid = (BZ_OUT + BZ_IN) / 2
rmid = BZ_R - (mid - BZ_OUT)
Lp = 2 * ((W - 2 * mid) - 2 * rmid) + 2 * ((H - 2 * mid) - 2 * rmid) + 2 * math.pi * rmid
NT = 72
for i in range(NT):
    x, y, nx, ny = rr_point(mid, rmid, i * Lp / NT)
    major = i % 6 == 0
    half = 3.2 if major else 2.0
    d.line((sc(x - nx * half), sc(y - ny * half), sc(x + nx * half), sc(y + ny * half)),
           fill=TICK_MAJOR if major else TICK_MINOR, width=int(round(sc(2.0 if major else 1.2))))

for frac in (0.0, 0.25, 0.5, 0.75):      # rivets at the four corner arcs (middle of each arc)
    pass
for cx_, cy_, a0 in ((W - rmid - mid, mid + rmid, -math.pi / 4), (W - rmid - mid, H - mid - rmid, math.pi / 4),
                     (mid + rmid, H - mid - rmid, 3 * math.pi / 4), (mid + rmid, mid + rmid, -3 * math.pi / 4)):
    x, y = cx_ + rmid * math.cos(a0), cy_ + rmid * math.sin(a0)
    r = 3.3
    d.ellipse((sc(x - r), sc(y - r), sc(x + r), sc(y + r)), fill=pc("rivet", (30, 44, 92)), outline=BAND_EDGE_O, width=S)
    d.line((sc(x - 1.8), sc(y - 1.8), sc(x + 1.8), sc(y + 1.8)), fill=(8, 0, 4), width=sc(1))

img.resize((W, H), Image.LANCZOS).save(OUT)
nb = sum(1 for _, c in nets if c == BLUE)
print(f"bg saved; nets: {len(nets)} (blue {nb}), hops: {len(hops)}, passives: {len(chosen)}, edge-run decos: {len(runoff_names)}")
