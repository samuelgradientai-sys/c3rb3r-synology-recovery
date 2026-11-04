#!/usr/bin/env python3
"""SOLO LECTURA en el NAS. Talla PDF y Office (docx/xlsx/pptx/zip) de los .buk del pool de
Active Backup, solo en zonas que quedaron en claro (modo 0x25), sin duplicados (sha1),
y los manda como tar por stdout. Uso: python3 - INICIO FIN   (índices de bucket ordenados)."""
import os, sys, io, tarfile, hashlib, struct, json, time

POOL = "/volume1/ActiveBackupforBusiness/@ActiveBackup/@data/Pool"
ini, fin = int(sys.argv[1]), int(sys.argv[2])
MAXF = 60_000_000

bucks = []
for d, _, fs in os.walk(POOL):
    for f in fs:
        if f.endswith(".buk.L0CK3D"):
            bucks.append(os.path.join(d, f))
bucks.sort(key=lambda p: int(os.path.basename(p).split(".")[0]))
lote = bucks[ini:fin]

tf = tarfile.open(fileobj=sys.stdout.buffer, mode="w|")
vistos = set()
stats = {"buckets": 0, "pdf": 0, "office": 0, "dup": 0, "cruza_franja": 0, "bytes": 0}

def meter(nombre, blob):
    h = hashlib.sha1(blob).hexdigest()
    if h in vistos:
        stats["dup"] += 1
        return False
    vistos.add(h)
    ti = tarfile.TarInfo(nombre); ti.size = len(blob); ti.mtime = int(time.time())
    tf.addfile(ti, io.BytesIO(blob)); stats["bytes"] += len(blob)
    return True

for p in lote:
    b = int(os.path.basename(p).split(".")[0])
    try:
        fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOATIME", 0))
        sz = os.fstat(fd).st_size
        N = sz - 588
        foot = os.pread(fd, 588, N)
        if foot[572] != 0x25:
            os.close(fd); continue
        data = os.pread(fd, N, 0); os.close(fd)
    except OSError:
        continue
    stats["buckets"] += 1
    w = 4 * (N // 100); gap = (N - 3 * w) // 2
    cif = [(0, w), (w + gap, 2 * w + gap), (2 * (w + gap), 3 * w + 2 * gap)]
    limpio = lambda a, z: all(z <= x or a >= y for x, y in cif)

    # --- PDF: %PDF- hasta el último %%EOF antes del siguiente %PDF-
    i = data.find(b"%PDF-")
    while i != -1:
        sig = data.find(b"%PDF-", i + 5)
        tope = sig if sig != -1 else N
        e = data.rfind(b"%%EOF", i, tope)
        if e != -1:
            e += 5
            while e < tope and data[e:e + 1] in (b"\r", b"\n"):
                e += 1
            if 1500 < e - i < MAXF:
                if limpio(i, e):
                    if meter("pdf/b%05d_%08d.pdf" % (b, i), data[i:e]):
                        stats["pdf"] += 1
                else:
                    stats["cruza_franja"] += 1
        i = sig

    # --- ZIP/Office: desde cada fin de directorio central (EOCD) se calcula el inicio exacto
    j = data.find(b"PK\x05\x06")
    while j != -1:
        if j + 22 <= N:
            cd_size, cd_off, clen = struct.unpack("<IIH", data[j + 12:j + 22])
            ini_z = j - cd_size - cd_off
            fin_z = j + 22 + clen
            if 0 <= ini_z < j and data[ini_z:ini_z + 4] == b"PK\x03\x04" and fin_z - ini_z < MAXF:
                blob = data[ini_z:fin_z]
                if limpio(ini_z, fin_z):
                    cab = blob[:4000] + data[j - min(cd_size, 200000):j]
                    if b"word/" in cab: ext, car = "docx", "word"
                    elif b"xl/" in cab: ext, car = "xlsx", "excel"
                    elif b"ppt/" in cab: ext, car = "pptx", "powerpoint"
                    else: ext, car = "zip", "zip"
                    if meter("%s/b%05d_%08d.%s" % (car, b, ini_z, ext), blob):
                        stats["office"] += 1
                else:
                    stats["cruza_franja"] += 1
        j = data.find(b"PK\x05\x06", j + 4)

blob = json.dumps(dict(stats, ini=ini, fin=fin)).encode()
ti = tarfile.TarInfo("_stats/lote_%05d_%05d.json" % (ini, fin)); ti.size = len(blob)
tf.addfile(ti, io.BytesIO(blob))
tf.close()
