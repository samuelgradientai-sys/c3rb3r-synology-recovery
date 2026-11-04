#!/usr/bin/env python3
"""SOLO LECTURA en el NAS. Inventario de todos los .L0CK3D: ruta original, tamaño original
(footer[580:588]), modo y mtime. Salida TSV gzip por stdout."""
import os, sys, struct, gzip

RAICES = ["/volume1", "/volume2"]
SALTAR = {"@eaDir", "#snapshot", "@docker", "#recycle_x", "ActiveBackupforBusiness"}
out = gzip.GzipFile(fileobj=sys.stdout.buffer, mode="wb")
n = 0
for raiz in RAICES:
    for d, subs, fs in os.walk(raiz):
        if d in RAICES:
            subs[:] = [s for s in subs if not s.startswith("@") and s not in SALTAR]
        else:
            subs[:] = [s for s in subs if s not in SALTAR]
        for f in fs:
            if not f.endswith(".L0CK3D"):
                continue
            p = os.path.join(d, f)
            try:
                fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOATIME", 0))
                try:
                    st = os.fstat(fd)
                    if st.st_size < 588:
                        continue
                    ft = os.pread(fd, 588, st.st_size - 588)
                finally:
                    os.close(fd)
            except OSError:
                continue
            orig = struct.unpack("<Q", ft[580:588])[0]
            out.write(("%s\t%d\t%02x\t%d\n" % (p[:-7], orig, ft[572], int(st.st_mtime))).encode("utf-8", "surrogateescape"))
            n += 1
out.close()
sys.stderr.write("total %d\n" % n)
