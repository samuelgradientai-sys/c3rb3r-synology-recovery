#!/usr/bin/env python3
"""Solo lectura: mira el interior de un .buk de Active Backup en las zonas que quedaron en claro."""
import os, sys, struct, math, collections

p = sys.argv[1]
fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOATIME", 0))
sz = os.fstat(fd).st_size
N = sz - 588
foot = os.pread(fd, 588, N)
mode, pct = foot[572], foot[573]
w = 4 * (N // 100); gap = (N - 3 * w) // 2
cifr = [(0, w), (w + gap, 2 * w + gap), (2 * (w + gap), 3 * w + 2 * gap)]
print("archivo", p, "N", N, "modo %#x pct %d" % (mode, pct))
print("franjas cifradas:", cifr)

def claro(a, b):
    return all(b <= x or a >= y for x, y in cifr)

def entropia(b):
    c = collections.Counter(b); n = len(b)
    return -sum(v / n * math.log2(v / n) for v in c.values())

# muestras en zonas claras
for frac in (0.06, 0.20, 0.35, 0.60, 0.85):
    off = int(N * frac) // 4096 * 4096
    if not claro(off, off + 4096):
        continue
    b = os.pread(fd, 4096, off)
    print("\n@%.0f%% off=%d entropia=%.2f" % (frac * 100, off, entropia(b)))
    print("  hex:", b[:64].hex())
    print("  txt:", "".join(chr(x) if 32 <= x < 127 else "." for x in b[:96]))

# buscar firmas en todo lo claro
MAG = {b"%PDF-": "pdf", b"PK\x03\x04": "zip/office", b"\x28\xb5\x2f\xfd": "zstd",
       b"\x04\x22\x4d\x18": "lz4frame", b"FILE0": "ntfs_mft", b"\xd0\xcf\x11\xe0": "ole(doc/xls)",
       b"\xff\xd8\xff": "jpeg", b"\x89PNG": "png", b"\x1f\x8b\x08": "gzip", b"SQLite format 3": "sqlite",
       b"NTFS    ": "ntfs_boot", b"\x78\x9c": "zlib", b"\x78\x01": "zlib1", b"\x78\xda": "zlib9"}
cnt = collections.Counter(); prim = {}
CH = 8 << 20; off = 0
while off < N:
    n = min(CH, N - off)
    b = os.pread(fd, n + 16, off)
    for m, nom in MAG.items():
        i = b.find(m)
        while i != -1 and i < n:
            if claro(off + i, off + i + len(m)):
                cnt[nom] += 1
                prim.setdefault(nom, off + i)
            i = b.find(m, i + 1)
    off += n
os.close(fd)
print("\nfirmas en zona clara:", dict(cnt.most_common()))
print("primer offset:", prim)
