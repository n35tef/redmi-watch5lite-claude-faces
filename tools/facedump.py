import struct, sys
def dump(p):
    b = open(p, "rb").read()
    print(f"== {p} ({len(b)})  hdr@0xAC..0xE0: {b[0xAC:0xE0].hex(' ')}")
    o = 0x1E0; lo = len(b)
    while o + 16 <= lo:
        idx, z, typ, _, off, size = struct.unpack_from("<HBBIII", b, o)
        if not (0 < off <= len(b)): break
        lo = min(lo, off)
        d = b[off:off + min(size, 64)]
        print(f"  t{typ} #{idx:<3} off={off:<6} size={size:<6} {d.hex(' ') if typ in (0, 7) else d[:16].hex(' ')}")
        o += 16
    print(f"  table region 0x100..0x1E0: {b[0x100:0x1E0].hex(' ')[:400]}")
for p in sys.argv[1:]: dump(p)
