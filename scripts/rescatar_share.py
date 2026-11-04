#!/usr/bin/env python3
"""Procesa lo que llega a ~/rescate_cliente/share_crudo/ y lo deja en ~/Escritorio/NAS-3PL/Share/
con la misma ruta del NAS:
  - PDF: '<nombre> [PARCIAL].pdf' con las páginas que sobrevivieron + carpeta '<nombre> [IMÁGENES]'
  - docx/xlsx/pptx: '<nombre> [PARCIAL].ext' si quedó el cuerpo + carpeta '<nombre> [IMÁGENES]'
  - doc/xls/ppt: carpeta '<nombre> [IMÁGENES]' con JPEG/PNG tallados
Índice: ~/Escritorio/NAS-3PL_SIN_UBICAR/Share_RESCATE_PARCIAL.csv. Re-ejecutable."""
import csv, json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reparar_office import entradas, reparar as rep_office

CRUDO = os.path.expanduser("~/rescate_cliente/share_crudo")
DEST = os.path.expanduser("~/Escritorio/NAS-3PL/Share")
IDX = os.path.expanduser("~/Escritorio/NAS-3PL/Share/_SIN_UBICAR/Share_RESCATE_PARCIAL.csv")
VENV = os.path.expanduser("~/rescate_cliente/.venv/bin/python")
RPDF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reparar_pdf.py")
CAMPOS = ["ruta_original", "tipo", "modo", "resultado", "paginas", "paginas_con_contenido",
          "imagenes", "guardado_en"]

hechos = set()
if os.path.exists(IDX):
    with open(IDX, encoding="utf-8-sig") as f:
        hechos = {r["ruta_original"] for r in csv.DictReader(f, delimiter=";")}
nuevo_idx = not os.path.exists(IDX)
fidx = open(IDX, "a", encoding="utf-8-sig", newline="")
w = csv.DictWriter(fidx, fieldnames=CAMPOS, delimiter=";")
if nuevo_idx:
    w.writeheader()

def base_dest(rel):
    b, e = os.path.splitext(os.path.join(DEST, rel))
    return b, e

def tallar_imagenes(data, zonas, carpeta, minimo=25_000):
    limpio = lambda a, z: all(z <= x or a >= y for x, y in zonas)
    n = 0
    for m in re.finditer(rb"\xff\xd8\xff[\xe0-\xef\xdb]", data):
        i = m.start(); f = data.find(b"\xff\xd9", i + 2000)
        while f != -1 and f - i < minimo:
            f = data.find(b"\xff\xd9", f + 2)
        if f == -1 or f - i > 40_000_000 or not limpio(i, f + 2):
            continue
        os.makedirs(carpeta, exist_ok=True); n += 1
        open(os.path.join(carpeta, "imagen_%03d.jpg" % n), "wb").write(data[i:f + 2])
    for m in re.finditer(rb"\x89PNG\r\n\x1a\n", data):
        i = m.start(); f = data.find(b"IEND\xaeB`\x82", i)
        if f == -1 or f + 8 - i < minimo or not limpio(i, f + 8):
            continue
        os.makedirs(carpeta, exist_ok=True); n += 1
        open(os.path.join(carpeta, "imagen_%03d.png" % n), "wb").write(data[i:f + 8])
    return n

cont = {"ok": 0, "nada": 0}
for raiz, _, fs in os.walk(CRUDO):
    for fn in fs:
        if fn.endswith(".zonas.json") or fn.startswith("_"):
            continue
        p = os.path.join(raiz, fn)
        if not os.path.exists(p + ".zonas.json"):
            continue                              # aún llegando
        rel = os.path.relpath(p, CRUDO)
        if rel in hechos:
            continue
        meta = json.load(open(p + ".zonas.json")); zonas = [tuple(z) for z in meta["zonas"]]
        ext = fn.rsplit(".", 1)[-1].lower()
        b, e = base_dest(rel)
        fila = {"ruta_original": rel, "tipo": ext, "modo": meta["modo"], "resultado": "nada",
                "paginas": "", "paginas_con_contenido": "", "imagenes": 0, "guardado_en": ""}
        os.makedirs(os.path.dirname(b), exist_ok=True)
        try:
            if ext == "pdf":
                salida = b + " [PARCIAL].pdf"
                r = subprocess.run([VENV, RPDF, p, salida], capture_output=True, timeout=300)
                res = json.loads(r.stdout.decode().strip().splitlines()[-1])
                fila["imagenes"] = res.get("imagenes", 0)
                fila["paginas"] = res.get("paginas", ""); fila["paginas_con_contenido"] = res.get("paginas_con_contenido", "")
                if res.get("paginas_con_contenido"):
                    fila["resultado"] = "páginas recuperadas"; fila["guardado_en"] = salida
                else:
                    if os.path.exists(salida): os.remove(salida)
                    if fila["imagenes"]:
                        fila["resultado"] = "solo imágenes"; fila["guardado_en"] = b + " [IMÁGENES]"
            elif ext in ("docx", "xlsx", "xlsm", "pptx"):
                data = open(p, "rb").read(); ent = entradas(data, zonas)
                media = {n: c for n, c in ent.items() if "/media/" in n and len(c) >= 15_000}
                if media:
                    car = b + " [IMÁGENES]"; os.makedirs(car, exist_ok=True)
                    for n, c in media.items():
                        open(os.path.join(car, os.path.basename(n)), "wb").write(c)
                    fila["imagenes"] = len(media); fila["resultado"] = "solo imágenes"; fila["guardado_en"] = car
                cuerpo = {"docx": "word/document.xml", "xlsx": "xl/workbook.xml", "xlsm": "xl/workbook.xml",
                          "pptx": "ppt/presentation.xml"}[ext]
                hojas = any(re.match(r"(xl/worksheets/sheet|ppt/slides/slide)\d+\.xml$", n) for n in ent)
                if cuerpo in ent or (ext != "docx" and hojas):
                    salida = b + " [PARCIAL]" + e
                    rep_office(p, salida)
                    fila["resultado"] = "documento parcial" + (" + imágenes" if media else "")
                    fila["guardado_en"] = salida
            elif ext in ("doc", "xls", "ppt", "cdr"):
                data = open(p, "rb").read()
                n = tallar_imagenes(data, zonas, b + " [IMÁGENES]")
                if n:
                    fila["imagenes"] = n; fila["resultado"] = "solo imágenes"; fila["guardado_en"] = b + " [IMÁGENES]"
            else:
                fila["resultado"] = "no recuperable (cabecera cifrada)"
        except Exception as ex:
            fila["resultado"] = "error: %s" % str(ex)[:80]
        if fila["guardado_en"]:
            fila["guardado_en"] = fila["guardado_en"].replace(os.path.expanduser("~/Escritorio/"), "")
            cont["ok"] += 1
        else:
            cont["nada"] += 1
        w.writerow(fila); fidx.flush()
print(time.strftime("%H:%M"), cont)
