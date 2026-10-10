"""stack_one.py <tag> <id> <palette-json> <out-dir>"""
import os, sys, subprocess, shutil
W = os.path.normpath(os.path.expanduser("~/ClaudePCB_work")); PY = os.path.join(W, ".venv", "Scripts", "python.exe")
tag, idn, pal, out = sys.argv[1:5]
proj = os.path.join(W, "styles", "proj_" + tag); shutil.rmtree(proj, ignore_errors=True)
r = subprocess.run([PY, "-I", "-W", "ignore", os.path.join(W, "tools", "make_face_stack.py"), pal, proj], capture_output=True, text=True)
if r.returncode: print(r.stderr[-1500:]); sys.exit(1)
os.environ["SRCP"] = proj; sys.path.insert(0, os.path.join(W, "tools"))
import build_m0style
build_m0style.build(tag, idn, out)
