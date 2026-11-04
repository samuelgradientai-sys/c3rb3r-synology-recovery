#!/usr/bin/env python3
"""SOLO LECTURA en el NAS. Recibe por la 1a línea de stdin (tras el script) una lista JSON de
[ruta_L0CK3D_sin_sufijo, tamaño_original, modo]; manda por stdout un tar.gz con cada archivo
recortado a su tamaño original y con las zonas cifradas puestas en CERO, más un .json de zonas."""
import os, sys, io, json, tarfile, time, gzip, base64

LISTA = json.loads(os.environ["LISTA_JSON"]) if "LISTA_JSON" in os.environ else json.loads(sys.argv[1])

def zonas(modo, n):
    if modo == "26":
        return [(0, min(n, 1 << 20))]
    w = 4 * (n // 100); gap = (n - 3 * w) // 2
    return [(0, w), (w + gap, 2 * w + gap), (2 * (w + gap), 3 * w + 2 * gap)]

gz = gzip.GzipFile(fileobj=sys.stdout.buffer, mode="wb", compresslevel=1)
tf = tarfile.open(fileobj=gz, mode="w|")
for ruta, n, modo in LISTA:
    p = ruta + ".L0CK3D"
    try:
        fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOATIME", 0))
        foot = os.pread(fd, 588, os.fstat(fd).st_size - 588)
        if foot[572] == 0x25 and foot[573] != 0x0a:
            os.close(fd); continue          # variante de porcentaje no verificada
        buf = bytearray(os.pread(fd, n, 0)); os.close(fd)
    except OSError:
        continue
    zs = zonas(modo, n)
    for a, b in zs:
        buf[a:b] = bytes(b - a)
    nombre = ruta.split("/", 3)[3]          # quita /volumeN/
    ti = tarfile.TarInfo(nombre); ti.size = len(buf); ti.mtime = int(time.time())
    tf.addfile(ti, io.BytesIO(bytes(buf)))
    meta = json.dumps({"zonas": zs, "modo": modo, "n": n}).encode()
    ti = tarfile.TarInfo(nombre + ".zonas.json"); ti.size = len(meta)
    tf.addfile(ti, io.BytesIO(meta))
tf.close()
gz.close()
