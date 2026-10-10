"""Render the current face layout in 30 colour schemes and lay the previews out on one sheet."""
import os, sys, json, subprocess, shutil, importlib
from PIL import Image, ImageDraw, ImageFont
W = os.path.normpath(os.path.expanduser("~/ClaudePCB_work")); GEN = os.path.join(W, "gen"); PY = os.path.join(W, ".venv", "Scripts", "python.exe")
OUT = os.path.join(W, "palettes30"); sys.path.insert(0, os.path.join(W, "tools"))

def mix(c, k, base=(0, 0, 0)): return [round(base[i] + (c[i] - base[i]) * k) for i in range(3)]
def light(c, k=0.45): return [round(v + (255 - v) * k) for v in c]
def scheme(w1, w2, edge, clock, date, stat, icon=None, grad=None, bg=(0, 0, 0)):
    return {"bg": list(bg), "w1": list(w1), "w2": list(w2), "pad": light(w1, 0.35), "body": mix(w1, 0.04), "edge": list(edge),
            "pin_dim": mix(w1, 0.28), "band": [0, 0, 0], "band_o": list(edge), "band_i": list(w1), "tick_maj": list(icon or clock),
            "tick_min": list(w1), "rivet": mix(w1, 0.6), "clock": list(clock), "date": list(date), "stat": list(stat),
            "icon": list(icon or clock), "_grad": grad}

S = [  # name, scheme
 ("Neon blue / amber",      scheme((0, 90, 255), (0, 200, 255), (0, 170, 255), (255, 160, 20), (90, 200, 255), (210, 240, 255))),
 ("Neon blue / coral",      scheme((0, 90, 255), (0, 200, 255), (0, 170, 255), (255, 120, 80), (90, 200, 255), (210, 240, 255))),
 ("Neon blue / red-orange", scheme((0, 90, 255), (0, 200, 255), (0, 170, 255), (255, 70, 40), (90, 200, 255), (210, 240, 255))),
 ("Neon blue / sunset",     scheme((0, 90, 255), (0, 200, 255), (0, 170, 255), (255, 120, 40), (90, 200, 255), (210, 240, 255), grad=((255, 196, 60), (255, 64, 48)))),
 ("Tron",                   scheme((0, 150, 200), (0, 230, 255), (0, 230, 255), (200, 250, 255), (0, 230, 255), (220, 250, 255), icon=(255, 140, 30))),
 ("Synthwave",              scheme((190, 0, 200), (0, 220, 255), (255, 40, 200), (0, 240, 255), (255, 90, 220), (240, 220, 255), icon=(255, 60, 160))),
 ("Hot pink / purple",      scheme((110, 40, 220), (190, 80, 255), (170, 90, 255), (255, 40, 150), (210, 160, 255), (240, 230, 255))),
 ("Cyan / magenta",         scheme((0, 150, 190), (0, 230, 220), (0, 220, 230), (255, 30, 200), (90, 240, 240), (230, 255, 255))),
 ("Matrix",                 scheme((0, 150, 40), (0, 230, 90), (0, 220, 80), (150, 255, 150), (60, 255, 120), (210, 255, 220))),
 ("Toxic lime / violet",    scheme((90, 200, 0), (190, 255, 0), (150, 255, 0), (190, 80, 255), (200, 255, 90), (240, 255, 220))),
 ("Ice",                    scheme((60, 130, 220), (150, 210, 255), (140, 200, 255), (235, 248, 255), (160, 215, 255), (220, 240, 255), icon=(120, 200, 255))),
 ("Ferrari",                scheme((200, 20, 20), (255, 70, 40), (255, 40, 30), (255, 220, 0), (255, 120, 90), (255, 235, 220))),
 ("Classic PCB",            scheme((0, 150, 70), (0, 200, 110), (210, 170, 60), (255, 40, 30), (230, 200, 120), (240, 240, 220), bg=(0, 10, 4))),
 ("Blue LED",               scheme((0, 60, 230), (0, 120, 255), (0, 110, 255), (60, 150, 255), (80, 160, 255), (190, 220, 255))),
 ("Amber terminal",         scheme((200, 110, 0), (255, 160, 0), (255, 150, 0), (255, 176, 0), (255, 190, 60), (255, 225, 160))),
 ("Red alert",              scheme((150, 0, 10), (230, 20, 30), (220, 20, 30), (255, 40, 40), (255, 110, 100), (255, 210, 205))),
 ("Cyberpunk yellow",       scheme((220, 200, 0), (255, 240, 60), (255, 230, 0), (0, 240, 255), (255, 240, 90), (255, 250, 210), icon=(255, 60, 120))),
 ("Miami",                  scheme((0, 170, 160), (0, 230, 210), (0, 220, 200), (255, 80, 170), (120, 240, 230), (230, 255, 250))),
 ("Ultraviolet",            scheme((100, 30, 230), (150, 70, 255), (140, 80, 255), (210, 170, 255), (180, 140, 255), (235, 225, 255), icon=(255, 80, 200))),
 ("Neon green / magenta",   scheme((0, 200, 90), (60, 255, 140), (0, 255, 120), (255, 30, 180), (120, 255, 170), (220, 255, 235))),
 ("Blue / white",           scheme((0, 90, 255), (0, 170, 255), (0, 150, 255), (240, 245, 255), (120, 190, 255), (215, 235, 255), icon=(255, 110, 60))),
 ("Claude terracotta",      scheme((170, 80, 50), (230, 120, 80), (217, 119, 87), (250, 236, 215), (240, 180, 150), (250, 236, 215), icon=(217, 119, 87), bg=(6, 3, 2))),
 ("Mint / coral",           scheme((0, 170, 130), (80, 240, 190), (60, 230, 180), (255, 110, 90), (130, 240, 210), (225, 255, 245))),
 ("Purple / lime",          scheme((120, 30, 220), (170, 80, 255), (160, 90, 255), (180, 255, 30), (200, 160, 255), (240, 230, 255))),
 ("Copper / cyan",          scheme((180, 90, 30), (230, 140, 60), (220, 130, 60), (0, 230, 255), (240, 170, 110), (255, 230, 210), icon=(0, 220, 255))),
 ("Steel / neon orange",    scheme((90, 100, 120), (150, 165, 190), (150, 165, 190), (255, 110, 20), (190, 205, 225), (230, 236, 245))),
 ("Ocean aqua",             scheme((0, 80, 160), (0, 170, 200), (0, 160, 210), (0, 230, 230), (90, 210, 230), (210, 245, 250), grad=((120, 255, 230), (0, 150, 255)))),
 ("Lava",                   scheme((150, 20, 0), (230, 60, 0), (240, 70, 0), (255, 120, 0), (255, 150, 90), (255, 225, 200), grad=((255, 230, 60), (255, 30, 10)))),
 ("Aurora",                 scheme((0, 90, 200), (0, 200, 160), (0, 190, 200), (0, 255, 160), (100, 230, 220), (215, 255, 245), grad=((150, 255, 120), (0, 190, 255)))),
 ("Vaporwave",              scheme((0, 170, 220), (120, 230, 255), (0, 210, 255), (255, 80, 200), (130, 220, 255), (240, 230, 255), grad=((255, 120, 220), (150, 70, 255)))),
]

def gradient(path, top, bot):
    im = Image.open(path).convert("RGBA"); px = im.load()
    for y in range(im.height):
        k = y / max(1, im.height - 1); c = tuple(round(top[i] + (bot[i] - top[i]) * k) for i in range(3))
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a: lum = max(r, g, b) / 255; px[x, y] = tuple(round(v * lum) for v in c) + (a,)
    im.save(path)

if __name__ == "__main__":
    shutil.rmtree(OUT, ignore_errors=True); os.makedirs(OUT)
    tiles = []
    for i, (name, pal) in enumerate(S, 1):
        grad = pal.pop("_grad"); env = dict(os.environ, PAL=json.dumps(pal))
        bg = os.path.join(OUT, f"bg_{i:02d}.png"); proj = os.path.join(OUT, f"proj_{i:02d}")
        subprocess.run([PY, "-I", "pcb_bg_wide.py", bg, "24"], cwd=GEN, env=env, check=True, capture_output=True)
        os.makedirs(os.path.join(proj, "images"))
        subprocess.run([PY, "-I", "-W", "ignore", "make_face_v39.py", proj], cwd=GEN, env=dict(env, BG_PATH=bg), check=True, capture_output=True)
        if grad:
            for f in os.listdir(os.path.join(proj, "images")):
                if f.startswith(("time_digit_", "sec_digit_", "time_colon")): gradient(os.path.join(proj, "images", f), *grad)
        os.environ["SRCP"] = proj
        import build_m0style; importlib.reload(build_m0style)
        build_m0style.build(f"ClaudePCB_P{i:02d}", f"1672104{i:02d}", OUT)
        prev = os.path.join(W, "m0style", f"ClaudePCB_P{i:02d}_preview.png")
        shutil.copy(prev, os.path.join(OUT, f"{i:02d}_{name.replace(' / ', '_').replace(' ', '_').lower()}.png"))
        tiles.append((f"{i:02d} {name}", Image.open(prev).convert("RGB")))
    TW, TH, LH, COLS = 246, 301, 26, 6
    rows = -(-len(tiles) // COLS)
    sheet = Image.new("RGB", (COLS * (TW + 8) + 8, rows * (TH + LH + 8) + 8), (22, 22, 22))
    d = ImageDraw.Draw(sheet); f = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 17)
    for k, (label, im) in enumerate(tiles):
        x = 8 + (k % COLS) * (TW + 8); y = 8 + (k // COLS) * (TH + LH + 8)
        d.text((x + 2, y + 2), label, font=f, fill=(235, 235, 235)); sheet.paste(im.resize((TW, TH), Image.LANCZOS), (x, y + LH))
    sheet.save(os.path.join(OUT, "00_palettes30_sheet.png")); print("sheet saved")
