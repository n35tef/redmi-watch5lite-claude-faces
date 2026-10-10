"""ClaudePCB rebuilt to match m0tral's working Redmi Watch 5 Lite faces:
 - all static images (icons, logo, colons, units) baked into the background -> 12 elements (his max is 14)
 - only the background is a standalone image; everything else is an image list
 - number lists have 11 images (0-9 + extra), temperature 12 (0-9, minus, dot), as in his DOTs face."""
import re, os, shutil, subprocess, sys
from PIL import Image
W = os.path.normpath(os.path.expanduser("~/ClaudePCB_work")); MC = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Mi Create")
BGC, THC, LC = int(os.environ.get("M0_BGC", 255)), 16, int(os.environ.get("M0_LC", 255))
SRCP = os.environ.get("SRCP", os.path.join(W, "ClaudePCB"))   # source project (fprj + images)
ORIG = os.path.join(SRCP, "images") if "SRCP" in os.environ else os.path.join(W, "images_original_backup")
x = open(os.path.join(SRCP, "ClaudePCB.fprj"), encoding="utf-8").read()
ws = re.findall(r'\t\t<Widget .*?</Widget>\n', x); head = x.split(ws[0])[0]; tail = x.split(ws[-1])[1]
nm = lambda w: re.search(r'Name="([^"]+)"', w).group(1)
A = lambda w, k: re.search(f' {k}="([^"]*)"', w).group(1)
sys.path.insert(0, os.path.join(W, "tools"))
from build_v3 import minus_from, dot_from
def quant_group(img, files, n=None):
    n = n or LC
    ims = [Image.open(os.path.join(img, f)).convert("RGBA") for f in files]
    sheet = Image.new("RGBA", (sum(i.width for i in ims), max(i.height for i in ims))); xo = 0
    for i in ims: sheet.paste(i, (xo, 0)); xo += i.width
    q = sheet.quantize(colors=n, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).convert("RGBA"); xo = 0
    for f, i in zip(files, ims): q.crop((xo, 0, xo + i.width, i.height)).save(os.path.join(img, f)); xo += i.width
def build(tag, idn, out_dir, drop=()):
    d = os.path.join(W, "m0style", tag); shutil.rmtree(d, ignore_errors=True); os.makedirs(os.path.join(d, "output"))
    shutil.copytree(ORIG, os.path.join(d, "images")); img = os.path.join(d, "images")
    statics = [w for w in ws if A(w, "Shape") == "30" and nm(w) != "background" and nm(w) not in drop]
    lists = [w for w in ws if A(w, "Shape") in ("31", "32") and nm(w) not in drop]
    # 1. bake static images into the background
    bg = Image.open(os.path.join(img, "bg_pcb.png")).convert("RGBA")
    plain = bg.convert("RGB").copy()
    for w in statics: bg.alpha_composite(Image.open(os.path.join(img, A(w, "Bitmap"))).convert("RGBA"), (int(A(w, "X")), int(A(w, "Y"))))
    # shared palette: PCB colours + colours of the baked-in icons (so small orange areas aren't averaged away)
    pcb = plain.quantize(colors=BGC - 12, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).getpalette()[:3 * (BGC - 12)]
    over = Image.new("RGB", (1, 1)); parts = []
    for w in statics:
        im = Image.open(os.path.join(img, A(w, "Bitmap"))).convert("RGBA"); flat = Image.new("RGBA", im.size, (0, 0, 0, 255)); flat.alpha_composite(im); parts.append(flat.convert("RGB"))
    sheet = Image.new("RGB", (sum(i.width for i in parts), max(i.height for i in parts))); xo = 0
    for i in parts: sheet.paste(i, (xo, 0)); xo += i.width
    ico = sheet.quantize(colors=12, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).getpalette()[:36]
    pal = Image.new("P", (1, 1)); pal.putpalette(pcb + ico + [0, 0, 0] * (256 - BGC))
    bg.convert("RGB").quantize(palette=pal, dither=Image.Dither.NONE).save(os.path.join(img, "bg_pcb.png"))
    # 2. extra list entries like m0tral: time/date lists repeat 0 as 11th; stat lists get a minus; temperature minus + dot
    for pre in ("date_digit", "stat_digit"):   # a style may ship its own minus / dot; otherwise derive them from 7-segment 8 - 0
        if not os.path.exists(os.path.join(img, f"{pre}_minus.png")):
            minus_from(os.path.join(img, f"{pre}_0.png"), os.path.join(img, f"{pre}_8.png")).save(os.path.join(img, f"{pre}_minus.png"))
    if not os.path.exists(os.path.join(img, "stat_dot.png")):
        dot_from(os.path.join(img, "stat_digit_8.png")).save(os.path.join(img, "stat_dot.png"))
    out = []
    for w in lists:
        if A(w, "Shape") == "32":
            fs = A(w, "BitmapList").split("|"); pre = fs[0].rsplit("_", 1)[0]
            src = A(w, "Value_Src")
            if src in ("0811", "1011", "1811", "1812", "1012", "0812"): fs.append(fs[0])
            else: fs.append(f"{pre}_minus.png")
            if src == "2031": fs.append(f"{pre}_dot.png" if os.path.exists(os.path.join(img, f"{pre}_dot.png")) else "stat_dot.png")
            w = w.replace(A(w, "BitmapList"), "|".join(fs))
        out.append(w)
    body = head.replace('Title="Claude PCB"', f'Title="Claude PCB {tag[-2:]}"') + [w for w in ws if nm(w) == "background"][0] + "".join(out) + tail
    used = set(re.findall(r'([\w\-]+\.png)', body))
    for f in os.listdir(img):
        if f not in used: os.remove(os.path.join(img, f))
    groups = []
    for w in out:
        s = {p.split(":")[-1] for p in A(w, "BitmapList").split("|")}
        for g in [g for g in groups if g & s]: groups.remove(g); s |= g
        groups.append(s)
    for g in groups: quant_group(img, sorted(g))
    # 3. preview: render the face (sample values) like the real thing, 244x298 palette PNG
    prev = Image.open(os.path.join(img, "bg_pcb.png")).convert("RGBA")
    sample = {"0811": "10", "1011": "08", "1811": "36", "1812": "10", "0812": "2026", "0822": "72", "0821": "8432", "2031": "21", "0841": "80"}
    for w in out:
        X, Y = int(A(w, "X")), int(A(w, "Y"))
        if A(w, "Shape") == "31":
            m = dict(p.split(":") for p in A(w, "BitmapList").split("|")); f = m.get({"2012": "(3)", "1012": "(10)"}[A(w, "Index_Src")])
            prev.alpha_composite(Image.open(os.path.join(img, f)).convert("RGBA"), (X, Y))
        else:
            fs = A(w, "BitmapList").split("|"); v = sample[A(w, "Value_Src")]; v = v.rjust(int(A(w, "Digits"))) if A(w, "Blanking") == "1" else v.zfill(int(A(w, "Digits")))
            for ch in v:
                g = Image.open(os.path.join(img, fs[int(ch) if ch != " " else 0])).convert("RGBA")
                if ch != " ": prev.alpha_composite(g, (X, Y))
                X += g.width + int(A(w, "Spacing"))
    prev.convert("RGB").save(os.path.join(W, "m0style", tag + "_preview.png"))
    prev.convert("RGB").resize((244, 298), Image.LANCZOS).quantize(colors=THC, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(os.path.join(img, "thumb.png"))
    fprj = os.path.join(d, tag + ".fprj"); open(fprj, "w", encoding="utf-8").write(body)
    r = subprocess.run([os.path.join(MC, "compiler", "compile.exe"), "-b", fprj, os.path.join(d, "output"), tag + ".face", "1461256429"], cwd=MC, capture_output=True, text=True, errors="replace")
    f = os.path.join(d, "output", tag + ".face")
    if "No Errors" not in r.stdout: print(tag, "FAILED", r.stdout[-400:]); return
    b = bytearray(open(f, "rb").read()); b[40:49] = idn.encode(); open(f, "wb").write(b)
    shutil.copy(f, os.path.join(out_dir, tag + ".face")); print(f"{tag}: {len(b)} bytes, elements={body.count('<Widget')}")
if __name__ == "__main__":
    build("ClaudePCB_32", "167210332", sys.argv[1])
