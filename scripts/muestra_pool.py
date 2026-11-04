#!/usr/bin/env python3
"""Solo lectura: muestrea .buk del pool de Active Backup y cuenta firmas de documentos en zonas en claro."""
import os, sys, collections

POOL = "/volume1/ActiveBackupforBusiness/@ActiveBackup/@data/Pool"
CADA = int(sys.argv[1]) if len(sys.argv) > 1 else 500
MAG = {b"%PDF-": "pdf", b"PK\x03\x04": "zip/office", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1": "ole_doc_xls",
       b"FILE0": "ntfs_mft", b"\xff\xd8\xff\xe0": "jpeg", b"[Content_Types].xml": "ooxml",
       b"word/document.xml": "docx", b"xl/workbook.xml": "xlsx", b"%%EOF": "pdf_fin"}

bucks = []
for d, _, fs in os.walk(POOL):
    for f in fs:
        if f.endswith(".buk.L0CK3D"):
            bucks.append(os.path.join(d, f))
bucks.sort(key=lambda p: int(os.path.basename(p).split(".")[0]))
mues = bucks[::CADA]
tot = collections.Counter(); por = []
for p in mues:
    fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOATIME", 0))
    sz = os.fstat(fd).st_size; N = sz - 588
    w = 4 * (N // 100); gap = (N - 3 * w) // 2
    cif = [(0, w), (w + gap, 2 * w + gap), (2 * (w + gap), 3 * w + 2 * gap)]
    c = collections.Counter(); off = 0; CH = 8 << 20
    while off < N:
        n = min(CH, N - off); b = os.pread(fd, n + 32, off)
        for m, nom in MAG.items():
            i = b.find(m)
            while i != -1 and i < n:
                a = off + i
                if all(a + len(m) <= x or a >= y for x, y in cif):
                    c[nom] += 1
                i = b.find(m, i + 1)
        off += n
    os.close(fd)
    tot.update(c)
    por.append((os.path.basename(p), N // 1048576, dict(c)))
print("buckets totales:", len(bucks), "| muestreados:", len(mues))
for x in por:
    if x[2]:
        print(" ", x)
print("TOTAL muestra:", dict(tot.most_common()))
