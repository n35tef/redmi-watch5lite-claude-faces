"""Stacked bold face inspired by the user's example (Fitbit-style): HH over MM on the left, slanted accent
divider, big weekday + month / day / year on the right, battery and temperature in the top corners,
heart rate and steps at the bottom. Black background.
Usage: make_face_stack.py <palette-json> <out-project-dir>   (then tools/build_m0style.py)"""
import json, os, sys
import xmltodict
from PIL import Image, ImageDraw, ImageFont

PAL, P = json.loads(sys.argv[1]), sys.argv[2]
IMG = os.path.join(P, "images"); os.makedirs(IMG, exist_ok=True)
W, H, K = 410, 502, 4
SEG = "C:/Windows/Fonts/SegUIVar.ttf"
ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
col = lambda k: tuple(PAL[k]) + (255,)
FG, ACC, SUB = col("fg"), col("accent"), col("sub")
C_WD, C_MO, C_DD, C_STEPS = (col(k) if k in PAL else ACC for k in ("weekday", "month", "day", "steps"))   # optional per-element colours

def save(im, name): im.save(os.path.join(IMG, name))
def seg(px, var):
    f = ImageFont.truetype(SEG, px); f.set_variation_by_name(var); return f
_d = ImageDraw.Draw(Image.new("L", (1, 1)))

def cell(txt, w, h, var, c, cap, align="l", digits_ref="0"):
    """txt in a w x h cell; cap = cap height in px; vertical position from the digit '0' box so rows line up"""
    f = seg(200 * K, var); l, t, r, b = _d.textbbox((0, 0), digits_ref, font=f); f = seg(round(200 * K * cap * K / (b - t)), var)
    l, t, r, b = _d.textbbox((0, 0), digits_ref, font=f)
    im = Image.new("RGBA", (w * K, h * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im); tw = d.textlength(txt, font=f)
    if tw > w * K * 0.97:                                   # shrink to fit the cell
        f = seg(max(8, int(f.size * w * K * 0.97 / tw)), var); l, t, r, b = d.textbbox((0, 0), digits_ref, font=f); tw = d.textlength(txt, font=f)
    x = {"l": 0, "c": (w * K - tw) / 2, "r": w * K - tw}[align]
    d.text((x, (h * K - (b - t)) / 2 - t), txt, font=f, fill=c)
    return im.resize((w, h), Image.LANCZOS)

def digits(prefix, w, h, var, c, cap, extra=()):
    for n in "0123456789": save(cell(n, w, h, var, c, cap, "c"), f"{prefix}{n}.png")
    for ch, name in extra: save(cell(ch, w, h, var, c, cap, "c"), name)

# ---------- geometry ----------
HW, HH, HSP = 76, 120, 4            # hour / minute digit cell
HX, HY, MY = 34, 128, 258
SW_, SH_ = 19, 32                   # small stat digits
DX = 240                            # date column
WD = (DX, 150, 156, 62)             # weekday x, y, w, h
MO = (DX, 220, 110, 42)
DD = (DX, 268, 30, 44)              # day digit cell (2 digits)
YR = (DX, 322, 19, 30)              # year digit cell (4 digits)
TOP_Y, BOT_Y = 64, 412

# ---------- images ----------
digits("time_digit_", HW, HH, "Bold Display", FG, 96)
digits("day_digit_", DD[2], DD[3], "Bold Display", C_DD, 34)
digits("date_digit_", YR[2], YR[3], "Semibold Display", SUB, 22, extra=(("-", "date_digit_minus.png"),))
digits("stat_digit_", SW_, SH_, "Semibold Display", FG, 23, extra=(("-", "stat_digit_minus.png"), (".", "stat_dot.png")))
DAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
for i, t in enumerate(DAYS): save(cell(t, WD[2], WD[3], "Bold Display", C_WD, 50, "l", "H"), f"date_weekday_{i}.png")
for i, t in enumerate(MONTHS, 1): save(cell(t, MO[2], MO[3], "Semibold Display", C_MO, 30, "l", "H"), f"date_month_{i}.png")
save(cell("%", 28, SH_, "Semibold Display", FG, 23, "l"), "stat_pct.png")
save(cell("°C", 34, SH_, "Semibold Display", FG, 23, "l"), "stat_unit_c.png")

def icon(kind, c, size=30, sw=2.6):
    im = Image.new("RGBA", (size * K, size * K), (0, 0, 0, 0)); d = ImageDraw.Draw(im); u = size * K / 34
    if kind == "heart":
        d.ellipse((3 * u, 6 * u, 18 * u, 21 * u), fill=c); d.ellipse((16 * u, 6 * u, 31 * u, 21 * u), fill=c); d.polygon([(4 * u, 16 * u), (30 * u, 16 * u), (17 * u, 31 * u)], fill=c)
    elif kind == "steps":
        d.rounded_rectangle((5 * u, 3 * u, 15 * u, 17 * u), radius=5 * u, fill=c); d.ellipse((5 * u, 19 * u, 14 * u, 28 * u), fill=c)
        d.rounded_rectangle((19 * u, 8 * u, 29 * u, 22 * u), radius=5 * u, fill=c); d.ellipse((19 * u, 24 * u, 28 * u, 33 * u), fill=c)
    elif kind == "battery":   # lightning bolt, like the example
        d.polygon([(19 * u, 2 * u), (7 * u, 19 * u), (16 * u, 19 * u), (13 * u, 32 * u), (27 * u, 13 * u), (18 * u, 13 * u)], fill=c)
    elif kind == "temp":
        d.rounded_rectangle((13 * u, 3 * u, 21 * u, 22 * u), radius=4 * u, outline=c, width=int(sw * K)); d.ellipse((9.5 * u, 18 * u, 24.5 * u, 33 * u), fill=c)
    return im.resize((size, size), Image.LANCZOS)
save(icon("heart", ACC), "ic_heart.png"); save(icon("steps", C_STEPS), "ic_steps.png"); save(icon("battery", FG), "ic_batt.png"); save(icon("temp", FG), "ic_temp.png")
clawd = Image.open(os.path.join(ASSETS, "clawd_big.png")).convert("RGBA"); clawd = clawd.crop(clawd.getbbox()).resize((26, 21), Image.LANCZOS)
save(clawd, "logo.png")

# background: black + slanted accent divider
bg = Image.new("RGBA", (W * K, H * K), col("bg")); d = ImageDraw.Draw(bg)
d.line([(232 * K, 118 * K), (206 * K, 392 * K)], fill=ACC, width=int(4 * K))
bg = bg.resize((W, H), Image.LANCZOS); save(bg.convert("RGB"), "bg_pcb.png"); save(bg.convert("RGB"), "thumb.png")

# ---------- widgets (original form; build_m0style bakes the static ones into the background) ----------
widgets = []
def base(shape, name, x, y, w, h): return {"@Shape": shape, "@Name": name, "@X": str(x), "@Y": str(y), "@Width": str(w), "@Height": str(h), "@Alpha": "255", "@Visible_Src": "0"}
def image(name, bitmap, x, y, w, h): dd = base("30", name, x, y, w, h); dd["@Bitmap"] = bitmap; widgets.append(dd)
def number(name, prefix, src, x, y, n, dw, dh, spacing=0, blanking="1"):
    dd = base("32", name, x, y, dw * n + spacing * (n - 1), dh)
    dd.update({"@BitmapList": "|".join(f"{prefix}{i}.png" for i in range(10)), "@Digits": str(n), "@Alignment": "0", "@Value_Src": src, "@Spacing": str(spacing), "@Blanking": blanking}); widgets.append(dd)
def imagelist(name, files, src, x, y, w, h):
    dd = base("31", name, x, y, w, h); dd.update({"@BitmapList": "|".join(f"({i}):{f}" for i, f in files), "@Index_Src": src, "@Alignment": "0", "@DefaultIndex": "0", "@Spacing": "0", "@Blanking": "0"}); widgets.append(dd)
image("background", "bg_pcb.png", 0, 0, W, H)
number("time_hour", "time_digit_", "0811", HX, HY, 2, HW, HH, HSP, "0")
number("time_min", "time_digit_", "1011", HX, MY, 2, HW, HH, HSP, "0")
imagelist("date_weekday", [(i, f"date_weekday_{i}.png") for i in range(7)], "2012", WD[0], WD[1], WD[2], WD[3])
imagelist("date_month", [(i, f"date_month_{i}.png") for i in range(1, 13)], "1012", MO[0], MO[1], MO[2], MO[3])
number("date_day", "day_digit_", "1812", DD[0], DD[1], 2, DD[2], DD[3], 1, "0")
number("date_year", "date_digit_", "0812", YR[0], YR[1], 4, YR[2], YR[3], 1, "0")
image("ic_batt", "ic_batt.png", 64, TOP_Y + 1, 30, 30)
number("battery", "stat_digit_", "0841", 96, TOP_Y, 3, SW_, SH_, 1)
image("battery_pct", "stat_pct.png", 96 + 3 * SW_ + 3, TOP_Y, 28, SH_)
image("ic_temp", "ic_temp.png", 262, TOP_Y + 1, 30, 30)
number("weather_temp", "stat_digit_", "2031", 294, TOP_Y, 2, SW_, SH_, 1)
image("weather_unit", "stat_unit_c.png", 294 + 2 * SW_ + 2, TOP_Y, 34, SH_)
image("ic_heart", "ic_heart.png", 48, BOT_Y + 1, 30, 30)
number("heart_rate", "stat_digit_", "0822", 82, BOT_Y, 3, SW_, SH_, 1)
image("ic_steps", "ic_steps.png", 236, BOT_Y + 1, 30, 30)
number("steps", "stat_digit_", "0821", 270, BOT_Y, 5, SW_, SH_, 1)
image("claude_logo", "logo.png", W // 2 - 13, 460, 26, 21)
project = {"FaceProject": {"@DeviceType": "3652", "@Id": "", "Screen": {"@Title": "Claude PCB", "@Bitmap": "thumb.png", "Widget": widgets}}}
open(os.path.join(P, "ClaudePCB.fprj"), "w", encoding="utf8").write(xmltodict.unparse(project, pretty=True))
print("widgets:", len(widgets))
