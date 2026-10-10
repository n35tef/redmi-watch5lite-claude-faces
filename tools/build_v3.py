"""ClaudePCB rebuilt the way m0tral's working Redmi Watch 5 Lite faces are made:
every image palettized (<=256 colours) and every number list padded with a minus sign
(index 10; temperature also a dot at index 11) so 'no data' / negative values don't index past the list."""
import re, os, shutil, subprocess, sys
from PIL import Image
W = os.path.normpath(os.path.expanduser("~/ClaudePCB_work")); MC = os.path.join(os.environ["LOCALAPPDATA"], "Programs", "Mi Create")
ORIG = os.path.join(W, "images_original_backup")
x = open(os.path.join(W, "ClaudePCB", "ClaudePCB.fprj"), encoding="utf-8").read()
ws = re.findall(r'\t\t<Widget .*?</Widget>\n', x); head = x.split(ws[0])[0]; tail = x.split(ws[-1])[1]
nm = lambda w: re.search(r'Name="([^"]+)"', w).group(1)
A = lambda w, k: re.search(f' {k}="([^"]*)"', w).group(1)
def lum(p): return (p[0] * 3 + p[1] * 6 + p[2]) * p[3] // 2550
def minus_from(d0, d8):
    """middle segment = pixels lit in 8 but not in 0"""
    a, b = Image.open(d0).convert("RGBA"), Image.open(d8).convert("RGBA"); out = Image.new("RGBA", a.size, (0, 0, 0, 0))
    pa, pb, po = a.load(), b.load(), out.load()
    for y in range(a.height):
        for xx in range(a.width):
            if lum(pb[xx, y]) - lum(pa[xx, y]) > 60: po[xx, y] = pb[xx, y]
    return out
def dot_from(d8):
    """small dot at the bottom centre, coloured like the lit segments"""
    b = Image.open(d8).convert("RGBA"); lit = max(b.getdata(), key=lum); out = Image.new("RGBA", b.size, (0, 0, 0, 0))
    w, h = b.size
    for y in range(h - 6, h - 1):
        for xx in range(w // 2 - 3, w // 2 + 3): out.putpixel((xx, y), lit)
    return out
def palettize(path, n=256):
    im = Image.open(path).convert("RGBA")
    if len(set(im.getdata())) > n:
        im = im.quantize(colors=n - 1, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).convert("RGBA")
    im.save(path)
def build(tag, idn, names, out_dir):
    d = os.path.join(W, "v3", tag); shutil.rmtree(d, ignore_errors=True); os.makedirs(os.path.join(d, "output"))
    shutil.copytree(ORIG, os.path.join(d, "images")); img = os.path.join(d, "images")
    shutil.copy(os.path.join(W, "ClaudePCB", "images", "thumb.png"), os.path.join(img, "thumb.png"))   # 244x298 preview
    for pre in ("time_digit", "date_digit", "stat_digit"):
        minus_from(os.path.join(img, f"{pre}_0.png"), os.path.join(img, f"{pre}_8.png")).save(os.path.join(img, f"{pre}_minus.png"))
    dot_from(os.path.join(img, "stat_digit_8.png")).save(os.path.join(img, "stat_dot.png"))
    chosen = []
    for w in ws:
        if nm(w) not in names: continue
        if A(w, "Shape") == "32":
            fs = A(w, "BitmapList").split("|"); pre = fs[0].rsplit("_", 1)[0]
            fs.append(f"{pre}_minus.png")
            if A(w, "Value_Src") == "2031": fs.append("stat_dot.png")
            w = w.replace(A(w, "BitmapList"), "|".join(fs))
        chosen.append(w)
    used = set(re.findall(r'([\w\-]+\.png)', head + "".join(chosen)))
    for f in os.listdir(img):
        if f not in used: os.remove(os.path.join(img, f))
    # shared palette per list group (compiler limit), every single image <=256 colours
    groups = []
    for w in chosen:
        if "BitmapList" in w:
            s = {p.split(":")[-1] for p in A(w, "BitmapList").split("|")}
            for g in [g for g in groups if g & s]: groups.remove(g); s |= g
            groups.append(s)
    for g in groups:
        fs = sorted(g); ims = [Image.open(os.path.join(img, f)).convert("RGBA") for f in fs]
        sheet = Image.new("RGBA", (sum(i.width for i in ims), max(i.height for i in ims))); xo = 0
        for i in ims: sheet.paste(i, (xo, 0)); xo += i.width
        q = sheet.quantize(colors=255, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).convert("RGBA"); xo = 0
        for f, i in zip(fs, ims): q.crop((xo, 0, xo + i.width, i.height)).save(os.path.join(img, f)); xo += i.width
    for f in used - set().union(*groups) if groups else used: palettize(os.path.join(img, f))
    fprj = os.path.join(d, tag + ".fprj")
    open(fprj, "w", encoding="utf-8").write(head.replace('Title="Claude PCB"', f'Title="Claude PCB {tag[-2:]}"') + "".join(chosen) + tail)
    r = subprocess.run([os.path.join(MC, "compiler", "compile.exe"), "-b", fprj, os.path.join(d, "output"), tag + ".face", "1461256429"], cwd=MC, capture_output=True, text=True, errors="replace")
    f = os.path.join(d, "output", tag + ".face")
    if "No Errors" not in r.stdout: print(tag, "FAILED", r.stdout[-400:]); return
    b = bytearray(open(f, "rb").read()); b[40:49] = idn.encode(); open(f, "wb").write(b)
    shutil.copy(f, os.path.join(out_dir, tag + ".face")); print(f"{tag}: {len(b)} bytes")
if __name__ == "__main__":
    out = sys.argv[1]
    base = {"background", "time_hour", "time_colon1", "time_min", "time_colon2", "time_sec", "date_weekday", "date_day",
            "date_month", "date_year", "claude_logo", "ic_heart", "ic_steps", "ic_temp", "weather_unit", "ic_batt", "battery_pct"}
    steps = [("all images + time/date, full colour quality", set()), ("heart rate", {"heart_rate"}), ("steps", {"steps"}),
             ("temperature", {"weather_temp"}), ("battery", {"battery"})]
    names = set(base)
    for i, (label, add) in enumerate(steps, 21):
        names |= add; build(f"ClaudePCB_{i}", f"1672102{i}", names, out); print(f"   {i} = {label}")
