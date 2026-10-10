"""Build one style+palette into a face + preview: style_one.py <style> <tag> <id> <palette-json> <out-dir>"""
import os, sys, subprocess, importlib, shutil
W = os.path.normpath(os.path.expanduser("~/ClaudePCB_work")); PY = os.path.join(W, ".venv", "Scripts", "python.exe")
style, tag, idn, pal, out = sys.argv[1:6]
proj = os.path.join(W, "styles", "proj_" + tag); shutil.rmtree(proj, ignore_errors=True)
r = subprocess.run([PY, "-I", "-W", "ignore", os.path.join(W, "tools", "make_face_styles.py"), style, pal, proj], capture_output=True, text=True)
if r.returncode: print(r.stderr[-1500:]); sys.exit(1)
os.environ["SRCP"] = proj; sys.path.insert(0, os.path.join(W, "tools"))
import build_m0style
build_m0style.build(tag, idn, out)
