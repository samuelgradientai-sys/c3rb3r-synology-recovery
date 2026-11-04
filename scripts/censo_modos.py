#!/usr/bin/env python3
"""Censo de solo lectura de los .L0CK3D: lee los últimos 588 bytes (footer) de cada archivo.
Se ejecuta en el NAS por stdin (python3 -), no escribe nada en los volúmenes.
Salida: JSON resumen por modo y bytes recuperables (en claro) estimados."""
import os, sys, json, struct
from collections import Counter, defaultdict

RAICES = sys.argv[1:] or ["/volume1", "/volume2"]
SALTAR = {"@eaDir", "#snapshot", "@docker"}
FOOT = 588
MiB = 1 << 20

modo_n = Counter(); modo_bytes = Counter(); claro = Counter()
ext_modo = defaultdict(Counter); errores = 0; total = 0
marcadores = Counter(); ejemplos = defaultdict(list)

for raiz in RAICES:
    for d, subdirs, files in os.walk(raiz):
        subdirs[:] = [s for s in subdirs if s not in SALTAR]
        for f in files:
            if not f.endswith(".L0CK3D"):
                continue
            p = os.path.join(d, f)
            try:
                fd = os.open(p, os.O_RDONLY | getattr(os, "O_NOATIME", 0))
                try:
                    st = os.fstat(fd)
                    if st.st_size < FOOT:
                        continue
                    foot = os.pread(fd, FOOT, st.st_size - FOOT)
                finally:
                    os.close(fd)
            except OSError:
                errores += 1
                continue
            total += 1
            modo = foot[572]
            pct = foot[573]
            orig = struct.unpack("<Q", foot[580:588])[0]
            marcadores[foot[568:572].hex()] += 1
            m = "0x%02x" % modo
            modo_n[m] += 1
            modo_bytes[m] += orig
            # estimación de bytes que quedan en claro
            if modo == 0x26:          # solo el primer MiB
                c = max(0, orig - MiB)
            elif modo == 0x25:        # franjas: cifra pct% en 3 bloques
                c = orig - min(orig, 3 * (orig // 100) * max(pct, 1))
            else:                     # 0x24 completo
                c = 0
            claro[m] += c
            ext = f[:-7].rsplit(".", 1)[-1].lower() if "." in f[:-7] else "(sin)"
            ext_modo[m][ext] += 1
            if len(ejemplos[m]) < 3 and orig > 2 * MiB:
                ejemplos[m].append([p, orig, pct])

GB = 1e9
print(json.dumps({
    "archivos": total, "errores": errores,
    "marcadores": dict(marcadores.most_common(5)),
    "por_modo": {m: {"archivos": modo_n[m],
                     "GB_original": round(modo_bytes[m] / GB, 2),
                     "GB_en_claro_estimado": round(claro[m] / GB, 2),
                     "ext_top": ext_modo[m].most_common(8),
                     "ejemplos": ejemplos[m]} for m in sorted(modo_n)},
}, ensure_ascii=False, indent=1))
