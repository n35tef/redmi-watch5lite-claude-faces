"""Two alternative ClaudePCB styles with the same element positions and formats as the PCB face
(full date row, HH:MM + small bottom-aligned seconds, 2x2 stats, logo at the bottom).

  minimal   - pure black, Bahnschrift Light Condensed numerals, thin line icons, nothing else
  blueprint - engineering drawing: grid paper, sheet border, hatched outline clock digits, dimension lines,
              drafting labels, title block around the logo

Usage: make_face_styles.py <style> <palette-json> <out-project-dir>
Writes ClaudePCB.fprj + images/ in the original 21-widget form; tools/build_m0style.py turns it into the
watch-safe structure."""
import json, os, sys
import xmltodict
from PIL import Image, ImageDraw, ImageFont

STYLE, PAL, P = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
IMG = os.path.join(P, "images"); os.makedirs(IMG, exist_ok=True)
W, H, K = 410, 502, 4
BAHN, CONS = "C:/Windows/Fonts/bahnschrift.ttf", "C:/Windows/Fonts/consola.ttf"
ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
col = lambda k: tuple(PAL[k]) + (255,)

# ---------- same geometry as the PCB face (gen/make_face_v39.py) ----------
CDW, CDH, CLW, SDW, SDH, SGAP = 66, 112, 16, 40, 84, 8
CDW, CLW = PAL.get("cdw", CDW), PAL.get("clw", CLW)   # narrower cells pull the clock digits closer together
TW_ = 4 * CDW + CLW + SGAP + 2 * SDW
TX, TY = (W - TW_) // 2, 122 + (148 - CDH) // 2
LX, RX, Y1, Y2 = 36, 222, 302, 372
SC_W, SC_H, ICO = 20, 34, 34   # stat digit cell, icon size (minimal2 enlarges them)
NAME_H, DATE_MID = 34, 83
LOGO_X, LOGO_Y, LOGO_W, LOGO_H = 169, 454, 72, 28

def save(im, name): im.save(os.path.join(IMG, name))
def font(path, px, var=None):
    f = ImageFont.truetype(path, px)
    if var:
        try: f.set_variation_by_name(var)
        except Exception: pass
    return f

def glyph_cell(ch, w, h, f, fill, stroke=0, stroke_fill=None, cap_top=None, tracking=0, align="c"):
    """Render text into a w x h cell (supersampled); cap height block vertically centred unless cap_top given."""
    im = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    l, t, r, b = d.textbbox((0, 0), "0", font=f, stroke_width=stroke)
    widths = [d.textlength(c, font=f) for c in ch]; tw = sum(widths) + tracking * K * (len(ch) - 1)
    x = {"c": (w * K - tw) / 2, "r": w * K - tw - stroke, "l": stroke}[align]
    y = (h * K - (b - t)) / 2 - t if cap_top is None else cap_top * K - t
    for c, cw in zip(ch, widths):
        d.text((x, y), c, font=f, fill=fill, stroke_width=stroke, stroke_fill=stroke_fill); x += cw + tracking * K
    return im.resize((w, h), Image.LANCZOS)

def hatch(im, color, step=6, width=1.4):
    """Fill the inside of hollow outline glyphs with 45-degree hatching (drafting style)."""
    big = im.resize((im.width * K, im.height * K), Image.NEAREST)
    mask = Image.new("L", big.size, 0); md = ImageDraw.Draw(mask)
    for x in range(-big.height, big.width, step * K):
        md.line([(x, big.height), (x + big.height, 0)], fill=255, width=int(width * K))
    return mask

def tint(im, c):
    """Recolour an RGBA image to colour c, keeping its light/dark structure (mascot eyes stay dark)."""
    px = im.load(); mx = max(max(p[:3]) for p in im.getdata() if p[3]) or 1
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a: k = max(r, g, b) / mx; px[x, y] = (round(c[0] * k), round(c[1] * k), round(c[2] * k), a)
    return im

# ---------- line icons (shared, stroke width per style) ----------
def icon(kind, c, sw, size=34):
    im = Image.new("RGBA", (size * K, size * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im); u = size * K / 34; s = sw * K
    if kind == "heart":
        pts = []
        import math
        for i in range(0, 361, 4):
            t = math.radians(i); x = 16 * math.sin(t) ** 3; y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
            pts.append(((17 + x * 0.88) * u, (16 - y * 0.88) * u))
        d.line(pts + [pts[0]], fill=c, width=int(s), joint="curve")
    elif kind == "steps":
        d.rounded_rectangle((6 * u, 4 * u, 15 * u, 17 * u), radius=4.5 * u, outline=c, width=int(s)); d.ellipse((6 * u, 19.5 * u, 14 * u, 27.5 * u), outline=c, width=int(s))
        d.rounded_rectangle((19 * u, 8 * u, 28 * u, 21 * u), radius=4.5 * u, outline=c, width=int(s)); d.ellipse((19 * u, 23.5 * u, 27 * u, 31.5 * u), outline=c, width=int(s))
    elif kind == "battery":
        d.rounded_rectangle((3 * u, 10 * u, 28 * u, 24 * u), radius=3 * u, outline=c, width=int(s)); d.rectangle((28.5 * u, 14 * u, 31.5 * u, 20 * u), fill=c)
        d.rectangle((6.5 * u, 13.5 * u, 20 * u, 20.5 * u), fill=c)
    elif kind == "temp":
        d.rounded_rectangle((13 * u, 3 * u, 21 * u, 22 * u), radius=4 * u, outline=c, width=int(s)); d.ellipse((9.5 * u, 18 * u, 24.5 * u, 33 * u), outline=c, width=int(s))
        d.ellipse((13.5 * u, 22 * u, 20.5 * u, 29 * u), fill=c); d.rectangle((15.6 * u, 10 * u, 18.4 * u, 24 * u), fill=c)
    return im.resize((size, size), Image.LANCZOS)

# ============================================================ styles
if STYLE == "minimal":
    BG = Image.new("RGBA", (W, H), col("bg"))
    F_CLK = font(BAHN, 1, "Light Condensed"); F_CLK = font(BAHN, round(CDH * K * 1.12), "Light Condensed")
    F_SEC = font(BAHN, round(SDH * K * 1.12), "Light Condensed")
    F_DATE = font(BAHN, 21 * K, "SemiLight SemiCondensed"); DATE_TRACK = 2.2
    F_STAT = font(BAHN, 31 * K, "Light")
    def clock_digit(ch): return glyph_cell(ch, CDW, CDH, F_CLK, col("clock"))
    def sec_digit(ch): return glyph_cell(ch, SDW, SDH, F_SEC, col("accent"))
    def colon():
        im = Image.new("RGBA", (CLW * K, CDH * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = 3.6 * K
        for cy in (CDH * 0.36, CDH * 0.70): d.ellipse((CLW * K / 2 - r, cy * K - r, CLW * K / 2 + r, cy * K + r), fill=col("accent"))
        return im.resize((CLW, CDH), Image.LANCZOS)
    STAT_C, DATE_C, ICON_C, ICON_SW = col("stat"), col("date"), col("accent"), 2.0
    LOGO_TEXT_F = font(BAHN, 10 * K, "SemiLight")
    def decorate(bg): pass

elif STYLE == "minimal2":
    BG = Image.new("RGBA", (W, H), col("bg"))
    SC_W, SC_H, ICO = 22, 38, 38
    CF = PAL.get("clock_font", ["bahn", "SemiBold Condensed"])
    def clock_font(px):
        path = {"bahn": BAHN, "segvar": "C:/Windows/Fonts/SegUIVar.ttf", "impact": "C:/Windows/Fonts/impact.ttf"}[CF[0]]
        return font(path, px, CF[1] if len(CF) > 1 else None)
    def fitted(ch, w, h, c, cap_frac=0.86):
        """digit with cap height = cap_frac*h; squeezed horizontally if it is wider than the cell"""
        f = clock_font(200 * K); d0 = ImageDraw.Draw(Image.new("L", (1, 1)))
        l, t, r, b = d0.textbbox((0, 0), "0", font=f); scale = cap_frac * h * K / (b - t); f = clock_font(round(200 * K * scale))
        l, t, r, b = d0.textbbox((0, 0), ch, font=f); gw = max(d0.textlength(c2, font=f) for c2 in "0123456789")
        l0, t0, r0, b0 = d0.textbbox((0, 0), "0", font=f)
        big = Image.new("RGBA", (int(gw) + 8 * K, h * K), (0, 0, 0, 0)); bd = ImageDraw.Draw(big)
        bd.text(((big.width - d0.textlength(ch, font=f)) / 2, (h * K - (b0 - t0)) / 2 - t0), ch, font=f, fill=c)
        tw = min(big.width, (w - 2) * K)
        sq = big.resize((tw, h * K), Image.LANCZOS); out = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0)); out.alpha_composite(sq, ((w * K - tw) // 2, 0))
        return out.resize((w, h), Image.LANCZOS)
    def clock_digit(ch): return fitted(ch, CDW, CDH, col("clock"))
    def sec_digit(ch): return fitted(ch, SDW, SDH, col("accent"))
    def colon():
        im = Image.new("RGBA", (CLW * K, CDH * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = 5.2 * K
        for cy in (CDH * 0.33, CDH * 0.67): d.ellipse((CLW * K / 2 - r, cy * K - r, CLW * K / 2 + r, cy * K + r), fill=col("accent"))
        return im.resize((CLW, CDH), Image.LANCZOS)
    F_DATE = font(BAHN, 26 * K, "SemiBold SemiCondensed"); DATE_TRACK = 1.0
    F_STAT = font(BAHN, 37 * K, "SemiBold")
    STAT_C, DATE_C, ICON_C, ICON_SW = col("stat"), col("date"), col("accent"), 3.0
    LOGO_TEXT_F = font(BAHN, 11 * K, "SemiBold")
    def decorate(bg): pass

elif STYLE == "atlas":
    import math, random
    from PIL import ImageFilter
    SC_W, SC_H, ICO = 22, 38, 38
    SITKA = "C:/Windows/Fonts/SitkaVF.ttf"
    rnd = random.Random(7)
    paper, edge, ink, rust, land, grat = (col(k)[:3] for k in ("paper", "edge", "ink", "rust", "land", "graticule"))
    # ---- aged parchment: burnt edges, soft mottling, rust stains ----
    base = Image.new("RGB", (W, H), paper)
    vig = Image.new("L", (W, H), 0); vd = ImageDraw.Draw(vig)
    VN = PAL.get("vig", 60)
    for i in range(VN):
        vd.rounded_rectangle((i * 1.2, i * 1.4, W - i * 1.2, H - i * 1.4), radius=max(4, 110 - i), outline=int(255 * (1 - i / VN) ** 1.6), width=2)
    vig = vig.filter(ImageFilter.GaussianBlur(10))
    base = Image.composite(Image.new("RGB", (W, H), edge), base, vig)
    mott = Image.new("L", (W // 8, H // 8)); mott.putdata([rnd.randrange(0, 256) for _ in range((W // 8) * (H // 8))])
    mott = mott.resize((W, H), Image.BICUBIC).filter(ImageFilter.GaussianBlur(6))
    if PAL.get("mottle"): base = Image.composite(Image.new("RGB", (W, H), tuple(int(c * 0.86) for c in paper)), base, mott.point(lambda v: int(max(0, v - 128) * 0.9)))
    stains = Image.new("L", (W, H), 0); sd = ImageDraw.Draw(stains)
    for _ in range(PAL.get("stains", 9)):
        x, y, r = rnd.randrange(20, W - 20), rnd.randrange(20, H - 20), rnd.randrange(14, 46)
        sd.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=rnd.randrange(50, 110))
        sd.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), outline=rnd.randrange(120, 170), width=2)
    stains = stains.filter(ImageFilter.GaussianBlur(3))
    base = Image.composite(Image.new("RGB", (W, H), rust), base, stains)
    BG = base.convert("RGBA")

    def sitka(px, var): return font(SITKA, px, var)
    def fitted(ch, w, h, c, var="Banner Bold", cap_frac=0.80):
        d0 = ImageDraw.Draw(Image.new("L", (1, 1))); f = sitka(200 * K, var)
        l, t, r, b = d0.textbbox((0, 0), "0", font=f); f = sitka(round(200 * K * cap_frac * h * K / (b - t)), var)
        l0, t0, r0, b0 = d0.textbbox((0, 0), "0", font=f); gw = max(d0.textlength(c2, font=f) for c2 in "0123456789")
        big = Image.new("RGBA", (int(gw) + 8 * K, h * K), (0, 0, 0, 0))
        ImageDraw.Draw(big).text(((big.width - d0.textlength(ch, font=f)) / 2, (h * K - (b0 - t0)) / 2 - t0), ch, font=f, fill=c)
        tw = min(big.width, (w - 2) * K); sq = big.resize((tw, h * K), Image.LANCZOS)
        out = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0)); out.alpha_composite(sq, ((w * K - tw) // 2, 0)); return out.resize((w, h), Image.LANCZOS)
    def clock_digit(ch): return fitted(ch, CDW, CDH, col("ink"))
    def sec_digit(ch): return fitted(ch, SDW, SDH, col("rust2"))
    def colon():
        im = Image.new("RGBA", (CLW * K, CDH * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        for cy in (CDH * 0.38, CDH * 0.66):
            r = 5.5 * K; cx = CLW * K / 2; d.polygon([(cx, cy * K - r), (cx + r, cy * K), (cx, cy * K + r), (cx - r, cy * K)], fill=col("ink"))
        return im.resize((CLW, CDH), Image.LANCZOS)
    F_DATE = sitka(23 * K, "Subheading Bold"); DATE_TRACK = 1.4
    F_STAT = sitka(36 * K, "Text Bold")
    STAT_C, DATE_C, ICON_C, ICON_SW = col("ink"), col("ink"), col("rust2"), 2.8
    LOGO_TEXT_F = font("C:/Windows/Fonts/SitkaVF-Italic.ttf", 11 * K, "Text Semibold")

    def decorate(bg):
        im = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        land_c, ink_c, rust_c, grat_c = land + (255,), ink + (255,), rust + (150,), grat + (170,)
        # map: Mercator centred on 10 E, coastlines from Natural Earth 1:110m
        R, LON0, CY = 82, 10, 262
        ym = lambda la: math.log(math.tan(math.pi / 4 + math.radians(max(-80, min(80, la))) / 2)) * R
        Y0 = ym(18)
        def proj(lo, la):
            return (W / 2 + math.radians(((lo - LON0 + 180) % 360) - 180) * R) * K, (CY - (ym(la) - Y0)) * K
        cx, cy = W / 2, CY
        for a in (range(0, 360, 360 // PAL.get("rhumb", 16)) if PAL.get("rhumb", 16) else []):          # portolan rhumb lines
            t = math.radians(a); d.line([(cx * K, cy * K), ((cx + math.cos(t) * 600) * K, (cy + math.sin(t) * 600) * K)], fill=rust_c, width=K)
        for lo in range(-180, 181, 30):             # dotted graticule
            x = proj(lo, 0)[0]
            for y0 in range(int(proj(0, 78)[1]), int(proj(0, -60)[1]), 10 * K): d.line([(x, y0), (x, y0 + 5 * K)], fill=grat_c, width=K)
        for la in (-60, -30, 0, 30, 60):
            y = proj(0, la)[1]
            for x0 in range(0, W * K, 10 * K): d.line([(x0, y), (x0 + 5 * K, y)], fill=grat_c, width=K)
        gj = json.load(open(os.path.join(ASSETS, "..", "mapdata_dl", "ne_110m_land.geojson"), encoding="utf-8"))
        for feat in gj["features"]:
            g = feat["geometry"]; polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                ring = poly[0]
                if max(p[1] for p in ring) < -60: continue      # skip Antarctica
                pts = [proj(lo, la) for lo, la in ring]
                segs, cur = [], [pts[0]]                        # split rings that wrap around the map edge
                for a, b2 in zip(pts, pts[1:]):
                    if abs(b2[0] - a[0]) > W * K * 0.5: segs.append(cur); cur = []
                    cur.append(b2)
                segs.append(cur)
                if len(segs) == 1 and len(pts) > 2: d.polygon(pts, fill=land_c)
                for sg in segs:
                    if len(sg) > 1: d.line(sg, fill=ink_c, width=int(1.3 * K), joint="curve")
        bg.alpha_composite(im.resize((W, H), Image.LANCZOS))
        # soft parchment fog behind the clock and stats: map stays visible but faint
        fog = Image.new("L", (W, H), 0); fd = ImageDraw.Draw(fog)
        fd.rounded_rectangle((24, 128, W - 24, 266), radius=26, fill=190)
        fd.rounded_rectangle((28, 296, W - 28, 414), radius=20, fill=170)
        fog = fog.filter(ImageFilter.GaussianBlur(PAL.get("fogblur", 9)))
        bg.paste(Image.composite(Image.new("RGBA", (W, H), paper + (255,)), bg, fog), (0, 0))
        im = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        # neat line with an alternating degree bar following the rounded screen
        d.rounded_rectangle((6 * K, 6 * K, (W - 6) * K, (H - 6) * K), radius=104 * K, outline=ink_c, width=int(1.6 * K))
        bar = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ImageDraw.Draw(bar).rounded_rectangle((9 * K, 9 * K, (W - 9) * K, (H - 9) * K), radius=101 * K, outline=ink_c, width=int(4 * K))
        ang = Image.new("L", (W, H)); ap = ang.load()
        for y in range(H):
            for x in range(W): ap[x, y] = 255 if int((math.degrees(math.atan2(y - H / 2, x - W / 2)) + 180) / 7.5) % 2 else 0
        im.alpha_composite(Image.composite(bar, Image.new("RGBA", im.size, (0, 0, 0, 0)), ang.resize(im.size, Image.NEAREST)))
        d.rounded_rectangle((13 * K, 13 * K, (W - 13) * K, (H - 13) * K), radius=97 * K, outline=ink_c, width=K)
        # title + ribbon banner behind the date
        tf = sitka(10 * K, "Small Bold"); t = "M A P P A   M V N D I"; tw = d.textlength(t, font=tf)
        d.text(((W * K - tw) / 2, 36 * K), t, font=tf, fill=ink_c)
        yb0, yb1 = DATE_MID - 17, DATE_MID + 17; x0, x1 = 26, W - 26; rib = col("ribbon")
        for side in (-1, 1):
            xa = x0 if side < 0 else x1; xt = xa + side * 14
            d.polygon([(xa * K, (yb0 + 6) * K), (xt * K, (yb0 + 6) * K), ((xt - side * 7) * K, ((yb0 + yb1) / 2 + 6) * K), (xt * K, (yb1 + 6) * K), (xa * K, (yb1 + 6) * K)], fill=rib, outline=ink_c, width=int(1.2 * K))
        d.rectangle(((x0 + 8) * K, yb0 * K, (x1 - 8) * K, yb1 * K), fill=rib, outline=ink_c, width=int(1.4 * K))
        # compass rose (bottom right) and scale bar (bottom left)
        rx, ry, rr = 336, 446, 26
        d.ellipse(((rx - rr) * K, (ry - rr) * K, (rx + rr) * K, (ry + rr) * K), outline=ink_c, width=int(1.2 * K))
        for a in range(0, 360, 45):
            t = math.radians(a - 90); L = rr * (1.0 if a % 90 == 0 else 0.62); wd = rr * 0.16
            tip = (rx + math.cos(t) * L, ry + math.sin(t) * L)
            l2 = (rx + math.cos(t + math.pi / 2) * wd, ry + math.sin(t + math.pi / 2) * wd); r2 = (rx - math.cos(t + math.pi / 2) * wd, ry - math.sin(t + math.pi / 2) * wd)
            d.polygon([(tip[0] * K, tip[1] * K), (l2[0] * K, l2[1] * K), (rx * K, ry * K)], fill=ink_c)
            d.polygon([(tip[0] * K, tip[1] * K), (r2[0] * K, r2[1] * K), (rx * K, ry * K)], outline=ink_c, fill=rib)
        d.text(((rx - 3) * K, (ry - rr - 12) * K), "N", font=sitka(9 * K, "Small Bold"), fill=ink_c)
        sx, sy = 52, 446
        for i in range(4): d.rectangle(((sx + i * 16) * K, sy * K, (sx + i * 16 + 16) * K, (sy + 5) * K), fill=ink_c if i % 2 == 0 else rib, outline=ink_c, width=K)
        d.text((sx * K, (sy + 7) * K), "LEUCAE  0   1000", font=sitka(7 * K, "Small Bold"), fill=ink_c)
        bg.alpha_composite(im.resize((W, H), Image.LANCZOS))

elif STYLE == "blueprint":
    BG = Image.new("RGBA", (W, H), col("paper"))
    F_CLK = font(BAHN, round(CDH * K * 1.08), "Bold Condensed")
    F_SEC = font(BAHN, round(SDH * K * 1.08), "Bold Condensed")
    F_DATE = font(CONS, 22 * K); DATE_TRACK = 0.6
    F_STAT = font(CONS, 29 * K)
    F_LBL = font(CONS, 9 * K)
    BIG = bool(PAL.get("big"))                  # larger text for reading without glasses (clock unchanged)
    if BIG:
        F_DATE = font(CONS, 27 * K); F_STAT = font(CONS, 34 * K); F_LBL = font(CONS, 11 * K)
        SC_W, SC_H, ICO = 22, 40, 38
    def outlined(ch, w, h, f, c, hatch_c):
        sw = 3 * K
        im = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        l, t, r, b = d.textbbox((0, 0), "0", font=f, stroke_width=sw); x = (w * K - d.textlength(ch, font=f)) / 2; y = (h * K - (b - t)) / 2 - t
        inner = Image.new("L", im.size, 0); ImageDraw.Draw(inner).text((x, y), ch, font=f, fill=255)                  # glyph body
        outer = Image.new("L", im.size, 0); ImageDraw.Draw(outer).text((x, y), ch, font=f, fill=255, stroke_width=sw, stroke_fill=255)
        hm = hatch(Image.new("RGBA", (w, h)), None, step=5, width=1.3)
        from PIL import ImageChops
        body_hatch = ImageChops.multiply(inner, hm)
        ring = ImageChops.subtract(outer, inner)
        im.paste(Image.new("RGBA", im.size, hatch_c), mask=body_hatch); im.paste(Image.new("RGBA", im.size, c), mask=ring)
        return im.resize((w, h), Image.LANCZOS)
    def clock_digit(ch): return outlined(ch, CDW, CDH, F_CLK, col("clock"), col("hatch"))
    def sec_digit(ch): return outlined(ch, SDW, SDH, F_SEC, col("accent"), col("hatch2"))
    def colon():
        im = Image.new("RGBA", (CLW * K, CDH * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im); r = 4.2 * K
        for cy in (CDH * 0.36, CDH * 0.70):
            d.rectangle((CLW * K / 2 - r, cy * K - r, CLW * K / 2 + r, cy * K + r), outline=col("clock"), width=int(2.2 * K))
        return im.resize((CLW, CDH), Image.LANCZOS)
    STAT_C, DATE_C, ICON_C, ICON_SW = col("line"), col("line"), col("line"), 1.6
    LOGO_TEXT_F = font(CONS, 11 * K if BIG else 9 * K)

    def decorate(bg):
        im = Image.new("RGBA", (W * K, H * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        g1, g2, ln, ac = col("grid"), col("grid2"), col("line"), col("accent")
        for x in range(5, W, 10): d.line([(x * K, 0), (x * K, H * K)], fill=g2 if (x - 5) % 50 == 0 else g1, width=K if (x - 5) % 50 else int(1.4 * K))
        for y in range(1, H, 10): d.line([(0, y * K), (W * K, y * K)], fill=g2 if (y - 1) % 50 == 0 else g1, width=K if (y - 1) % 50 else int(1.4 * K))
        # sheet border (follows the rounded screen) + registration crosses
        d.rounded_rectangle((8 * K, 8 * K, (W - 8) * K, (H - 8) * K), radius=100 * K, outline=ln, width=int(1.8 * K))
        d.rounded_rectangle((13 * K, 13 * K, (W - 13) * K, (H - 13) * K), radius=95 * K, outline=ln, width=int(0.9 * K))
        for cx, cy in ((W // 2, 22), (W // 2, H - 24)):
            d.line([((cx - 7) * K, cy * K), ((cx + 7) * K, cy * K)], fill=ln, width=K); d.line([(cx * K, (cy - 7) * K), (cx * K, (cy + 7) * K)], fill=ln, width=K)
            d.ellipse(((cx - 3.5) * K, (cy - 3.5) * K, (cx + 3.5) * K, (cy + 3.5) * K), outline=ln, width=K)
        # dimension line under the clock + extension lines
        def arrow(x, y, dirn):
            d.polygon([(x * K, y * K), ((x - dirn * 7) * K, (y - 2.6) * K), ((x - dirn * 7) * K, (y + 2.6) * K)], fill=ac)
        yd = TY + CDH + 14; x0, x1 = TX, TX + TW_
        for x in (x0, x1): d.line([(x * K, (TY + CDH + 4) * K), (x * K, (yd + 5) * K)], fill=ac, width=K)
        d.line([(x0 * K, yd * K), (x1 * K, yd * K)], fill=ac, width=K); arrow(x0, yd, -1); arrow(x1, yd, 1)
        lbl = "TIME  HH:MM:SS"; tw = d.textlength(lbl, font=F_LBL)
        d.rectangle(((W * K - tw) / 2 - 4 * K, (yd - 6) * K, (W * K + tw) / 2 + 4 * K, (yd + 6) * K), fill=col("paper"))
        d.text(((W * K - tw) / 2, (yd - 5.5) * K), lbl, font=F_LBL, fill=ac)
        # vertical dimension at the left of the clock
        xv = TX - 9
        d.line([(xv * K, TY * K), (xv * K, (TY + CDH) * K)], fill=ac, width=K)
        for y, dn in ((TY, -1), (TY + CDH, 1)):
            d.polygon([(xv * K, y * K), ((xv - 2.6) * K, (y - dn * 7) * K), ((xv + 2.6) * K, (y - dn * 7) * K)], fill=ac)
            d.line([((xv - 4) * K, y * K), ((TX - 2) * K, y * K)], fill=ac, width=K)
        # drafting labels
        LB = 18 if BIG else 13
        for txt, x, y in (("DATE", 36, DATE_MID - 20 - LB + 2), ("HR", LX, Y1 - LB), ("STEPS", RX, Y1 - LB), ("BAT", LX, Y2 - LB), ("TEMP", RX, Y2 - LB)):
            d.text((x * K, y * K), txt, font=F_LBL, fill=ac)
        # thin boxes around the date row and stats (drawing "views")
        d.rectangle((30 * K, (DATE_MID - 20) * K, 380 * K, (DATE_MID + 22) * K), outline=ln, width=K)
        BW = 172 if BIG else 166; top = lambda y: y + (34 - SC_H) // 2 - 4
        for x, y in ((LX - 8, Y1), (RX - 8, Y1), (LX - 8, Y2), (RX - 8, Y2)):
            d.rectangle((x * K, top(y) * K, (x + BW) * K, (top(y) + SC_H + 8) * K), outline=ln, width=K)
        # title block around the logo
        d.rectangle((150 * K, 444 * K, 260 * K, 488 * K), fill=col("paper"), outline=ln, width=int(1.4 * K))
        d.line([(150 * K, 482 * K), (260 * K, 482 * K)], fill=ln, width=K)
        d.text((153 * K, 482.2 * K), "SHEET 1/1  SCALE 1:1", font=font(CONS, (6.2 if BIG else 5) * K), fill=ln)
        bg.alpha_composite(im.resize((W, H), Image.LANCZOS))
else:
    raise SystemExit("unknown style " + STYLE)

decorate(BG)
save(BG.convert("RGB"), "bg_pcb.png")

# ---------- digits ----------
for n in "0123456789":
    save(clock_digit(n), f"time_digit_{n}.png"); save(sec_digit(n), f"sec_digit_{n}.png")
save(colon(), "time_colon.png")
for n in "0123456789":
    save(glyph_cell(n, SC_W, SC_H, F_STAT, STAT_C), f"stat_digit_{n}.png")
save(glyph_cell("-", SC_W, SC_H, F_STAT, STAT_C), "stat_digit_minus.png")
save(glyph_cell(".", SC_W, SC_H, F_STAT, STAT_C), "stat_dot.png")
PENCIL = PAL.get("pencil") and col("accent")          # blueprint: red-pencil marks on weekday, heart rate, temperature, logo
if PENCIL:
    for n in "0123456789": save(glyph_cell(n, SC_W, SC_H, F_STAT, PENCIL), f"statr_digit_{n}.png")
    save(glyph_cell("-", SC_W, SC_H, F_STAT, PENCIL), "statr_digit_minus.png"); save(glyph_cell(".", SC_W, SC_H, F_STAT, PENCIL), "statr_digit_dot.png")
save(glyph_cell("%", SC_W + 6, SC_H, F_STAT, STAT_C), "stat_pct.png")
save(glyph_cell("°C", 2 * SC_W + 6, SC_H, F_STAT, PAL.get("pencil") and col("accent") or STAT_C, align="l"), "stat_unit_c.png")

# ---------- date row (uppercase, tracked); weekday right-aligned so it hugs the day number ----------
DAYS = ["SUNDAY,", "MONDAY,", "TUESDAY,", "WEDNESDAY,", "THURSDAY,", "FRIDAY,", "SATURDAY,"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
_m = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
tw = lambda s: (sum(_m.textlength(c, font=F_DATE) for c in s) + DATE_TRACK * K * (len(s) - 1)) / K
DW = int(max(tw(c) for c in "0123456789")) + 2
WD_W = int(max(tw(n) for n in DAYS)) + 2
MO_W = int(max(tw(n) for n in MONTHS)) + 2
for i, n in enumerate(DAYS): save(glyph_cell(n, WD_W, NAME_H, F_DATE, PENCIL or DATE_C, tracking=DATE_TRACK, align="r"), f"date_weekday_{i}.png")
for i, n in enumerate(MONTHS, 1): save(glyph_cell(n, MO_W, NAME_H, F_DATE, DATE_C, tracking=DATE_TRACK), f"date_month_{i}.png")
for n in "0123456789": save(glyph_cell(n, DW, NAME_H, F_DATE, DATE_C), f"date_digit_{n}.png")
save(glyph_cell("-", DW, NAME_H, F_DATE, DATE_C), "date_digit_minus.png")

# ---------- icons + logo ----------
for kind, name in (("heart", "stat_icon_heart.png"), ("steps", "stat_icon_steps.png"), ("battery", "stat_icon_battery.png"), ("temp", "stat_icon_temp.png")):
    save(icon(kind, PENCIL if PENCIL and kind in ("heart", "temp") else (ICON_C if kind in ("heart", "temp") or STYLE == "blueprint" else STAT_C), ICON_SW, ICO), name)
clawd = Image.open(os.path.join(ASSETS, "clawd_big.png")).convert("RGBA"); clawd = clawd.crop(clawd.getbbox()).resize((28, 22), Image.LANCZOS)
clawd = tint(clawd, PAL["logo"])
logo = Image.new("RGBA", (LOGO_W * K, LOGO_H * K), (0, 0, 0, 0)); ld = ImageDraw.Draw(logo)
ld.text((33 * K, 2 * K), "claude", font=LOGO_TEXT_F, fill=PENCIL or STAT_C); ld.text((33 * K, 14 * K), "code", font=LOGO_TEXT_F, fill=tuple(PAL["logo"]) + (255,))
logo = logo.resize((LOGO_W, LOGO_H), Image.LANCZOS); logo.alpha_composite(clawd, (0, 3)); save(logo, "logo_claude.png")

# ---------- widgets: identical positions/format to the PCB face ----------
widgets = []
def base(shape, name, x, y, w, h): return {"@Shape": shape, "@Name": name, "@X": str(x), "@Y": str(y), "@Width": str(w), "@Height": str(h), "@Alpha": "255", "@Visible_Src": "0"}
def image(name, bitmap, x, y, w, h): d = base("30", name, x, y, w, h); d["@Bitmap"] = bitmap; widgets.append(d)
def number(name, prefix, src, x, y, digits, dw, dh, spacing=0, blanking="1"):
    d = base("32", name, x, y, dw * digits + spacing * (digits - 1), dh)
    d.update({"@BitmapList": "|".join(f"{prefix}{n}.png" for n in range(10)), "@Digits": str(digits), "@Alignment": "0", "@Value_Src": src, "@Spacing": str(spacing), "@Blanking": blanking}); widgets.append(d)
def imagelist(name, files, src, x, y, w, h):
    d = base("31", name, x, y, w, h); d.update({"@BitmapList": "|".join(f"({i}):{f}" for i, f in files), "@Index_Src": src, "@Alignment": "0", "@DefaultIndex": "0", "@Spacing": "0", "@Blanking": "0"}); widgets.append(d)
image("background", "bg_pcb.png", 0, 0, W, H)
image("claude_logo", "logo_claude.png", LOGO_X, LOGO_Y, LOGO_W, LOGO_H)
ROW_W = WD_W + 6 + 2 * DW + 6 + MO_W + 6 + 4 * DW
dx, dy = (W - ROW_W) // 2, DATE_MID - NAME_H // 2
imagelist("date_weekday", [(i, f"date_weekday_{i}.png") for i in range(7)], "2012", dx, dy, WD_W, NAME_H)
number("date_day", "date_digit_", "1812", dx + WD_W + 6, dy, 2, DW, NAME_H, blanking="0")
imagelist("date_month", [(i, f"date_month_{i}.png") for i in range(1, 13)], "1012", dx + WD_W + 6 + 2 * DW + 6, dy, MO_W, NAME_H)
number("date_year", "date_digit_", "0812", dx + WD_W + 6 + 2 * DW + 6 + MO_W + 6, dy, 4, DW, NAME_H, blanking="0")
number("time_hour", "time_digit_", "0811", TX, TY, 2, CDW, CDH, blanking="0")
image("time_colon1", "time_colon.png", TX + 2 * CDW, TY, CLW, CDH)
number("time_min", "time_digit_", "1011", TX + 2 * CDW + CLW, TY, 2, CDW, CDH, blanking="0")
number("time_sec", "sec_digit_", "1811", TX + 4 * CDW + CLW + SGAP, TY + CDH - SDH, 2, SDW, SDH, blanking="0")
SY = lambda y: y + (34 - SC_H) // 2          # keep each stat row centred where it was
IY = lambda y: y + (34 - ICO) // 2
GAP = ICO + 10
image("ic_heart", "stat_icon_heart.png", LX, IY(Y1), ICO, ICO)
number("heart_rate", "statr_digit_" if PENCIL else "stat_digit_", "0822", LX + GAP, SY(Y1), 3, SC_W, SC_H, spacing=1)
image("ic_steps", "stat_icon_steps.png", RX, IY(Y1), ICO, ICO)
number("steps", "stat_digit_", "0821", RX + GAP, SY(Y1), 5, SC_W, SC_H, spacing=1)
image("ic_batt", "stat_icon_battery.png", LX, IY(Y2), ICO, ICO)
number("battery", "stat_digit_", "0841", LX + GAP, SY(Y2), 3, SC_W, SC_H, spacing=1)
image("battery_pct", "stat_pct.png", LX + GAP + 3 * SC_W + 3, SY(Y2), SC_W + 6, SC_H)
image("ic_temp", "stat_icon_temp.png", RX, IY(Y2), ICO, ICO)
number("weather_temp", "statr_digit_" if PENCIL else "stat_digit_", "2031", RX + GAP, SY(Y2), 2, SC_W, SC_H, spacing=1)
image("weather_unit", "stat_unit_c.png", RX + GAP + 2 * SC_W + 1, SY(Y2), 2 * SC_W + 6, SC_H)
save(BG.convert("RGB"), "thumb.png")
project = {"FaceProject": {"@DeviceType": "3652", "@Id": "", "Screen": {"@Title": "Claude PCB", "@Bitmap": "thumb.png", "Widget": widgets}}}
open(os.path.join(P, "ClaudePCB.fprj"), "w", encoding="utf8").write(xmltodict.unparse(project, pretty=True))
print("widgets:", len(widgets))
