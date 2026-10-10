"""Build 22 palettes for each of the two alternative styles (minimal, blueprint) + one contact sheet per style."""
import os, sys, json, subprocess
from PIL import Image, ImageDraw, ImageFont
W = os.path.normpath(os.path.expanduser("~/ClaudePCB_work")); PY = os.path.join(W, ".venv", "Scripts", "python.exe")
OUT = os.path.join(W, "styles_out"); os.makedirs(OUT, exist_ok=True)
mix = lambda a, b, k: [round(a[i] + (b[i] - a[i]) * k) for i in range(3)]

def m(clock, accent, date, stat=None, logo=None):
    return {"bg": [0, 0, 0], "clock": list(clock), "accent": list(accent), "date": list(date), "stat": list(stat or clock), "logo": list(logo or accent)}
MINIMAL = [
 ("White / Claude orange", m((245, 245, 245), (255, 140, 60), (150, 150, 160))),
 ("White / cyan",          m((245, 248, 250), (0, 220, 255), (140, 160, 170))),
 ("White / red",           m((245, 245, 245), (255, 55, 55), (155, 150, 150))),
 ("White / lime",          m((245, 248, 240), (170, 255, 40), (150, 160, 145))),
 ("White / magenta",       m((248, 244, 248), (255, 60, 200), (160, 150, 160))),
 ("Warm white / gold",     m((250, 240, 225), (255, 196, 70), (170, 155, 130))),
 ("Mono",                  m((240, 240, 240), (160, 160, 160), (110, 110, 110))),
 ("Silver / ice",          m((210, 218, 228), (150, 215, 255), (120, 130, 145))),
 ("Mint",                  m((200, 255, 230), (60, 230, 160), (100, 160, 140))),
 ("Lavender / violet",     m((230, 220, 255), (160, 100, 255), (140, 130, 170))),
 ("Peach / coral",         m((255, 225, 205), (255, 110, 90), (170, 140, 125))),
 ("Amber mono",            m((255, 186, 60), (255, 140, 0), (170, 120, 40))),
 ("Cyan mono",             m((120, 240, 255), (0, 190, 230), (60, 140, 160))),
 ("Rose / pink",           m((255, 220, 230), (255, 90, 150), (170, 130, 145))),
 ("Sky / sunset",          m((200, 230, 255), (255, 120, 60), (120, 150, 175))),
 ("Green phosphor",        m((120, 255, 140), (40, 200, 90), (60, 150, 80))),
 ("Night red",             m((200, 40, 30), (150, 20, 15), (110, 25, 20))),
 ("Sand / teal",           m((235, 220, 190), (0, 190, 170), (160, 145, 120))),
 ("Ice / electric blue",   m((235, 245, 255), (40, 120, 255), (130, 145, 170))),
 ("Lilac / lime",          m((225, 210, 255), (190, 255, 60), (145, 130, 170))),
 ("Gold / white",          m((255, 200, 90), (250, 250, 250), (170, 140, 90), stat=(250, 250, 250))),
 ("Coral / mint",          m((255, 140, 120), (90, 240, 190), (170, 120, 110), stat=(250, 235, 230))),
]

def b(paper, line, accent, clock=None):
    clock = clock or line
    return {"paper": list(paper), "grid": mix(paper, line, 0.09), "grid2": mix(paper, line, 0.18), "line": list(line), "accent": list(accent),
            "clock": list(clock), "hatch": mix(paper, clock, 0.55), "hatch2": mix(paper, accent, 0.55), "logo": list(clock)}
BLUEPRINT = [
 ("Classic blueprint",   b((10, 42, 96), (225, 238, 255), (120, 200, 255))),
 ("Midnight blueprint",  b((4, 14, 40), (200, 220, 255), (90, 170, 255))),
 ("CAD black / cyan",    b((0, 0, 0), (0, 230, 255), (255, 255, 255))),
 ("CAD black / green",   b((0, 0, 0), (60, 255, 120), (230, 255, 230))),
 ("AutoCAD dark",        b((30, 33, 38), (235, 235, 235), (255, 220, 0))),
 ("Sepia vellum",        b((40, 26, 14), (240, 220, 180), (255, 160, 80))),
 ("Engineering green",   b((8, 40, 24), (210, 255, 220), (255, 230, 120))),
 ("Redline",             b((10, 30, 70), (220, 235, 255), (255, 70, 70))),
 ("Graph paper night",   b((0, 0, 0), (235, 235, 240), (255, 140, 40))),
 ("Cyanotype",           b((0, 46, 99), (190, 225, 245), (255, 255, 255))),
 ("Purple drafting",     b((26, 10, 52), (230, 210, 255), (200, 120, 255))),
 ("Teal technical",      b((0, 40, 44), (200, 255, 250), (0, 230, 200))),
 ("Graphite",            b((22, 22, 24), (220, 220, 220), (140, 140, 140))),
 ("Amber CRT",           b((14, 8, 0), (255, 186, 60), (255, 230, 150))),
 ("Safety orange",       b((0, 0, 0), (255, 120, 20), (255, 230, 200))),
 ("Arctic",              b((16, 30, 44), (220, 240, 255), (130, 220, 255))),
 ("Claude coral",        b((10, 6, 4), (245, 230, 215), (232, 128, 90), clock=(232, 128, 90))),
 ("Magenta CAD",         b((0, 0, 0), (255, 80, 210), (120, 230, 255))),
 ("Oxide",               b((50, 14, 10), (255, 225, 210), (255, 170, 90))),
 ("Olive field",         b((30, 34, 16), (230, 235, 200), (255, 200, 80))),
 ("Ocean",               b((0, 30, 50), (180, 240, 255), (0, 200, 255), clock=(150, 235, 255))),
 ("Daylight vellum",     b((236, 232, 220), (20, 50, 110), (210, 60, 40))),
]

def sheet(tiles, path, title):
    TW, TH, LH, COLS = 246, 301, 24, 6; rows = -(-len(tiles) // COLS)
    s = Image.new("RGB", (COLS * (TW + 8) + 8, rows * (TH + LH + 8) + 40), (22, 22, 22)); d = ImageDraw.Draw(s)
    f = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 16); d.text((10, 8), title, font=ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 22), fill=(240, 240, 240))
    for k, (label, im) in enumerate(tiles):
        x = 8 + (k % COLS) * (TW + 8); y = 40 + (k // COLS) * (TH + LH + 8)
        d.text((x + 2, y + 2), label, font=f, fill=(235, 235, 235)); s.paste(im.resize((TW, TH), Image.LANCZOS), (x, y + LH))
    s.save(path)

for style, pals, letter, idbase, cols in (("minimal", MINIMAL, "M", 500, ("255", "255")), ("blueprint", BLUEPRINT, "B", 600, ("24", "24"))):
    tiles = []
    for i, (name, pal) in enumerate(pals, 1):
        tag = f"ClaudePCB_{letter}{i:02d}"
        env = dict(os.environ, M0_BGC=cols[0], M0_LC=cols[1])
        r = subprocess.run([PY, "-I", "-W", "ignore", os.path.join(W, "tools", "style_one.py"), style, tag, f"167210{idbase + i}", json.dumps(pal), OUT], env=env, capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr[-600:])
        tiles.append((f"{letter}{i:02d} {name}", Image.open(os.path.join(W, "m0style", tag + "_preview.png")).convert("RGB")))
    sheet(tiles, os.path.join(OUT, f"00_{style}_sheet.png"), f"{style.upper()}: {len(pals)} palettes")
