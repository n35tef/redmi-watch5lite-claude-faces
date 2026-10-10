"""Generate the Mi Create project (assets + .fprj) for a Redmi Watch 5 Lite PCB face."""
import json
import os
import sys
import xmltodict
from PIL import Image, ImageDraw, ImageFilter, ImageFont

P = sys.argv[1]
IMG = os.path.join(P, "images")
W, H = 410, 502
PAL = json.loads(os.environ.get("PAL", "{}"))   # optional palette override (see palette_previews)


def pc(key, default):
    return tuple(PAL.get(key, default)) + (255,)


RED = pc("clock", (232, 128, 90))     # (name kept) clock digits, heart icon
BLUE = pc("date", (150, 185, 255))    # date text
PALE = pc("stat", (214, 226, 255))    # stat digits
ORANGE = (217, 119, 87, 255)          # Claude orange (logo only)
ICE = pc("icon", (232, 128, 90))     # thermometer icon
FONT = "C:/Windows/Fonts/consolab.ttf"
S = 4  # supersampling for icons
ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
CDW, CDH = 66, 112  # clock digit cell (was 47 x 80)
CLW = 16            # colon between HH and MM
SDW, SDH = 40, 84   # seconds: 75% height
SGAP = 8            # gap between MM and ss


def save(im, name):
    im.save(os.path.join(IMG, name))


def text_img(txt, size, color, w=None, h=None, pad=0):
    f = ImageFont.truetype(FONT, size)
    l, t, r, b = f.getbbox(txt)
    iw, ih = w or (r + pad * 2), h or (b - t + pad * 2)
    im = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text(((iw - (r - l)) // 2 - l, (ih - (b - t)) // 2 - t), txt, font=f, fill=color)
    return im


# ---------- background: hand-routed PCB (made by pcb_bg.py) ----------
save(Image.open(os.environ["BG_PATH"]).convert("RGB"), "bg_pcb.png")   # made by pcb_bg_wide.py

# ---------- 7-segment digits ----------
SEGS = {0: "abcdef", 1: "bc", 2: "abdeg", 3: "abcdg", 4: "bcfg", 5: "acdfg",
        6: "acdefg", 7: "abc", 8: "abcdefg", 9: "abcdfg"}


def seg_polys(w, h, t, g):
    """Return {segment: polygon} for a w x h cell, thickness t, gap g."""
    c = t / 2
    def hseg(cy, x1, x2):
        return [(x1, cy), (x1 + c, cy - c), (x2 - c, cy - c), (x2, cy), (x2 - c, cy + c), (x1 + c, cy + c)]
    def vseg(cx, y1, y2):
        return [(cx, y1), (cx + c, y1 + c), (cx + c, y2 - c), (cx, y2), (cx - c, y2 - c), (cx - c, y1 + c)]
    m = h / 2
    return {
        "a": hseg(c, c + g, w - c - g), "g": hseg(m, c + g, w - c - g), "d": hseg(h - c, c + g, w - c - g),
        "f": vseg(c, c + g, m - g), "b": vseg(w - c, c + g, m - g),
        "e": vseg(c, m + g, h - c - g), "c": vseg(w - c, m + g, h - c - g),
    }


def seg_img(lit, dw, dh, t, color, pad=3, ghost=True):
    """Draw the given lit segments in a dw x dh transparent image (4x supersampled)."""
    k = S
    im = Image.new("RGBA", (dw * k, dh * k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    polys = seg_polys((dw - 2 * pad) * k, (dh - 2 * pad) * k, t * k, 0.6 * k)
    dim = color[:3] + (38,)
    for name, pts in polys.items():
        pts = [(x + pad * k, y + pad * k) for x, y in pts]
        if name in lit:
            d.polygon(pts, fill=color)
        elif ghost:
            d.polygon(pts, fill=dim)
    return im.resize((dw, dh), Image.LANCZOS)


for prefix, dw, dh, t, col, pd in (("time_digit_", CDW, CDH, 13, RED, 5), ("sec_digit_", SDW, SDH, 9, RED, 4), ("stat_digit_", 20, 34, 4, PALE, 2)):
    for n in range(10):
        save(seg_img(SEGS[n], dw, dh, t, col, pad=pd), f"{prefix}{n}.png")

# colon: two square dots
im = Image.new("RGBA", (CLW, CDH), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
for cy in (round(CDH * 0.33), round(CDH * 0.67)):
    d.rectangle((CLW // 2 - 5, cy - 5, CLW // 2 + 5, cy + 5), fill=RED)
save(im, "time_colon.png")

# percent: two dots + slash
im = Image.new("RGBA", (26 * S, 34 * S), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
u = S
d.rectangle((3 * u, 4 * u, 9 * u, 10 * u), fill=PALE)
d.rectangle((17 * u, 24 * u, 23 * u, 30 * u), fill=PALE)
d.polygon([(19 * u, 3 * u), (23 * u, 3 * u), (7 * u, 31 * u), (3 * u, 31 * u)], fill=PALE)
save(im.resize((26, 34), Image.LANCZOS), "stat_pct.png")

# degree + C (C = segments a, d, e, f)
im = Image.new("RGBA", (44, 34), (0, 0, 0, 0))
c_img = seg_img("adef", 20, 34, 4, PALE, pad=2, ghost=True)
im.alpha_composite(c_img, (22, 0))
ImageDraw.Draw(im).rectangle((3, 4, 13, 14), outline=PALE, width=3)
save(im, "stat_unit_c.png")

# ---------- date: names and numbers share ONE font (swap DATE_FONT to change it) ----------
DAYS = ["Sunday,", "Monday,", "Tuesday,", "Wednesday,", "Thursday,", "Friday,", "Saturday,"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DATE_FONT = os.path.join(ASSETS, "digital-7.ttf")  # Digital-7 (freeware for home use); no lowercase glyphs
CAP = 22                 # cap height of the date text
NAME_H = 34              # image height: room below the baseline for descenders (y, g, p)
BASE = 2 + CAP           # common baseline for names and digits
K = 4                    # supersampling
_probe = ImageFont.truetype(DATE_FONT, 100)
_ct = _probe.getbbox("H")
NAME_SIZE = round(100 * CAP / (_ct[3] - _ct[1]))
_f = ImageFont.truetype(DATE_FONT, NAME_SIZE * K)
DW = -(-int(_f.getlength("0")) // K)                      # digit cell width
WD_W = -(-int(max(_f.getlength(n) for n in DAYS)) // K) + 2   # weekday field (widest name + comma)
MO_W = -(-int(max(_f.getlength(n) for n in MONTHS)) // K) + 2


def text_cell(txt, w):
    big = Image.new("RGBA", (w * K, NAME_H * K), (0, 0, 0, 0))
    ImageDraw.Draw(big).text(((w * K - _f.getlength(txt)) / 2, BASE * K), txt, font=_f, fill=BLUE, anchor="ls")
    return big.resize((w, NAME_H), Image.LANCZOS)


for i, n in enumerate(DAYS):
    save(text_cell(n, WD_W), f"date_weekday_{i}.png")
for i, n in enumerate(MONTHS):
    save(text_cell(n, MO_W), f"date_month_{i + 1}.png")
for n in range(10):
    save(text_cell(str(n), DW), f"date_digit_{n}.png")

# ---------- icons (drawn 4x then downsampled) ----------
def icon(draw_fn, name, size=34):
    im = Image.new("RGBA", (size * S, size * S), (0, 0, 0, 0))
    draw_fn(ImageDraw.Draw(im), size * S)
    save(im.resize((size, size), Image.LANCZOS), name)


def heart(d, s):
    u = s / 34
    d.ellipse((3 * u, 6 * u, 18 * u, 21 * u), fill=RED)
    d.ellipse((16 * u, 6 * u, 31 * u, 21 * u), fill=RED)
    d.polygon([(4 * u, 16 * u), (30 * u, 16 * u), (17 * u, 31 * u)], fill=RED)


def steps(d, s):
    u = s / 34
    d.rounded_rectangle((5 * u, 3 * u, 15 * u, 17 * u), radius=5 * u, fill=BLUE)
    d.ellipse((5 * u, 19 * u, 14 * u, 28 * u), fill=BLUE)
    d.rounded_rectangle((19 * u, 8 * u, 29 * u, 22 * u), radius=5 * u, fill=BLUE)
    d.ellipse((19 * u, 24 * u, 28 * u, 33 * u), fill=BLUE)


def battery(d, s):
    u = s / 34
    d.rounded_rectangle((3 * u, 9 * u, 29 * u, 25 * u), radius=3 * u, outline=PALE, width=int(2.2 * u))
    d.rectangle((29 * u, 14 * u, 32 * u, 20 * u), fill=PALE)
    d.rectangle((6 * u, 12 * u, 22 * u, 22 * u), fill=PALE)


def therm(d, s):
    u = s / 34
    d.rounded_rectangle((13 * u, 3 * u, 21 * u, 21 * u), radius=4 * u, outline=ICE, width=int(2.4 * u))
    d.ellipse((9 * u, 17 * u, 25 * u, 33 * u), fill=ICE)
    d.rectangle((15.5 * u, 9 * u, 18.5 * u, 22 * u), fill=ICE)


icon(heart, "stat_icon_heart.png")
icon(steps, "stat_icon_steps.png")
icon(battery, "stat_icon_battery.png")
icon(therm, "stat_icon_temp.png")

# ---------- Claude Code logo: official mascot (clawd.svg from the VS Code extension) + label ----------
clawd = Image.open(os.path.join(ASSETS, "clawd_big.png")).convert("RGBA").resize((30, 24), Image.LANCZOS)
logo = Image.new("RGBA", (72, 28), (0, 0, 0, 0))
logo.alpha_composite(clawd, (0, 2))
lf = ImageFont.truetype(FONT, 10)
ld = ImageDraw.Draw(logo)
ld.text((35, 3), "claude", font=lf, fill=PALE)
ld.text((35, 15), "code", font=lf, fill=ORANGE)
save(logo, "logo_claude.png")
LOGO_W, LOGO_H = logo.size
LOGO_X, LOGO_Y = 169, 454

# ---------- layout ----------
widgets = []


def base(shape, name, x, y, w, h):
    return {"@Shape": shape, "@Name": name, "@X": str(x), "@Y": str(y),
            "@Width": str(w), "@Height": str(h), "@Alpha": "255", "@Visible_Src": "0"}


def image(name, bitmap, x, y, w, h):
    d = base("30", name, x, y, w, h)
    d["@Bitmap"] = bitmap
    widgets.append(d)


def number(name, prefix, src, x, y, digits, dw, dh, spacing=0, blanking="1"):
    d = base("32", name, x, y, dw * digits + spacing * (digits - 1), dh)
    d.update({"@BitmapList": "|".join(f"{prefix}{n}.png" for n in range(10)),
              "@Digits": str(digits), "@Alignment": "0", "@Value_Src": src,
              "@Spacing": str(spacing), "@Blanking": blanking})
    widgets.append(d)


def imagelist(name, files, src, x, y, w, h):
    d = base("31", name, x, y, w, h)
    d.update({"@BitmapList": "|".join(f"({i}):{f}" for i, f in files),
              "@Index_Src": src, "@Alignment": "0", "@DefaultIndex": "0",
              "@Spacing": "0", "@Blanking": "0"})
    widgets.append(d)


image("background", "bg_pcb.png", 0, 0, W, H)
image("claude_logo", "logo_claude.png", LOGO_X, LOGO_Y, LOGO_W, LOGO_H)

# date row: "Saturday, 10 Oct 2026" - one font throughout, names centred in their fields
ROW_W = WD_W + 6 + 2 * DW + 6 + MO_W + 6 + 4 * DW
dx, dy = (W - ROW_W) // 2, 83 - 2 - CAP // 2   # centred in the date frame
imagelist("date_weekday", [(i, f"date_weekday_{i}.png") for i in range(7)], "2012", dx, dy, WD_W, NAME_H)
number("date_day", "date_digit_", "1812", dx + WD_W + 6, dy, 2, DW, NAME_H, blanking="0")
imagelist("date_month", [(i, f"date_month_{i}.png") for i in range(1, 13)], "1012", dx + WD_W + 6 + 2 * DW + 6, dy, MO_W, NAME_H)
number("date_year", "date_digit_", "0812", dx + WD_W + 6 + 2 * DW + 6 + MO_W + 6, dy, 4, DW, NAME_H, blanking="0")
print("date row width", ROW_W, "digit cell", DW, "font size", NAME_SIZE)

# time row: hh:mm:ss  (6 digits x 47 + 2 colons x 22 = 326), vertically centred in the 96 px clock frame
TW_ = 4 * CDW + CLW + SGAP + 2 * SDW   # HH:MM + gap + small ss
tx = (W - TW_) // 2
ty = 122 + (148 - CDH) // 2
number("time_hour", "time_digit_", "0811", tx, ty, 2, CDW, CDH, blanking="0")
image("time_colon1", "time_colon.png", tx + 2 * CDW, ty, CLW, CDH)
number("time_min", "time_digit_", "1011", tx + 2 * CDW + CLW, ty, 2, CDW, CDH, blanking="0")
number("time_sec", "sec_digit_", "1811", tx + 4 * CDW + CLW + SGAP, ty + CDH - SDH, 2, SDW, SDH, blanking="0")

# stats grid, two columns
LX, RX = 36, 222
Y1, Y2 = 302, 372
image("ic_heart", "stat_icon_heart.png", LX, Y1, 34, 34)
number("heart_rate", "stat_digit_", "0822", LX + 44, Y1, 3, 20, 34, spacing=1)
image("ic_steps", "stat_icon_steps.png", RX, Y1, 34, 34)
number("steps", "stat_digit_", "0821", RX + 44, Y1, 5, 20, 34, spacing=1)
image("ic_batt", "stat_icon_battery.png", LX, Y2, 34, 34)
number("battery", "stat_digit_", "0841", LX + 44, Y2, 3, 20, 34, spacing=1)
image("battery_pct", "stat_pct.png", LX + 44 + 63, Y2, 26, 34)
image("ic_temp", "stat_icon_temp.png", RX, Y2, 34, 34)
number("weather_temp", "stat_digit_", "2031", RX + 44, Y2, 2, 20, 34, spacing=1)
image("weather_unit", "stat_unit_c.png", RX + 44 + 41, Y2, 44, 34)

# thumbnail = flat composite of the background + logo
thumb = Image.open(os.path.join(IMG, "bg_pcb.png")).convert("RGBA")
thumb.alpha_composite(logo, (LOGO_X, LOGO_Y))
save(thumb, "thumb.png")

project = {"FaceProject": {"@DeviceType": "3652", "@Id": "",
                           "Screen": {"@Title": "Claude PCB", "@Bitmap": "thumb.png",
                                      "Widget": widgets}}}
with open(os.path.join(P, "ClaudePCB.fprj"), "w", encoding="utf8") as f:
    f.write(xmltodict.unparse(project, pretty=True))
print("widgets:", len(widgets))
