#!/usr/bin/env python3
"""Solo lectura en el NAS: talla PDFs completos de un .buk (zonas en claro) y los manda como tar por stdout."""
import os, sys, tarfile, io

p = sys.argv[1]; MAX = int(sys.argv[2]) if len(sys.argv) > 2 else 8
fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOATIME", 0))
N = os.fstat(fd).st_size - 588
w = 4 * (N // 100); gap = (N - 3 * w) // 2
cif = [(0, w), (w + gap, 2 * w + gap), (2 * (w + gap), 3 * w + 2 * gap)]
data = os.pread(fd, N, 0); os.close(fd)

def limpio(a, b):
    return all(b <= x or a >= y for x, y in cif)

tf = tarfile.open(fileobj=sys.stdout.buffer, mode="w|")
i = data.find(b"%PDF-"); n = 0
while i != -1 and n < MAX:
    sig = data.find(b"%PDF-", i + 5)
    tope = sig if sig != -1 else N
    fin = data.rfind(b"%%EOF", i, tope)
    if fin != -1:
        fin += 5
        while fin < tope and data[fin:fin + 1] in (b"\r", b"\n"):
            fin += 1
        tam = fin - i
        if 2000 < tam < 30_000_000 and limpio(i, fin):
            ti = tarfile.TarInfo("pdf_%s_%d.pdf" % (os.path.basename(p).split(".")[0], i))
            ti.size = tam
            tf.addfile(ti, io.BytesIO(data[i:fin])); n += 1
    i = sig
tf.close()
