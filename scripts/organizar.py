#!/usr/bin/env python3
"""Organiza lo rescatado del pool de Active Backup:
 - detecta tipo real (zip -> docx/xlsx/pptx), comprueba integridad, lee de qué trata;
 - cruza por TAMAÑO EXACTO + extensión con el inventario de .L0CK3D del NAS (ruta original);
 - copia a ~/Escritorio/CLIENTE_RECUPERADO/<share>/<carpetas>/<nombre original>
   o, si no hay ruta, a _SIN_RUTA_ORIGINAL/<tipo>/<nombre por contenido>;
 - escribe INDICE.csv (abre en Excel). Re-ejecutable: solo procesa lo nuevo."""
import csv, gzip, html, os, re, shutil, subprocess, sys, zipfile
from collections import defaultdict

ORIG = os.path.expanduser("~/Escritorio/RESCATE_CLIENTE_BACKUP")
DEST = os.path.expanduser("~/Escritorio/NAS-3PL")
EXTRA = os.path.expanduser("~/Escritorio/NAS-3PL_SIN_UBICAR")
INV = os.path.expanduser("~/rescate_cliente/salida/inventario_rutas.tsv.gz")
IDX = os.path.join(EXTRA, "INDICE.csv")
CAMPOS = ["archivo_rescatado", "tipo", "estado", "ruta_original", "coincidencia",
          "otras_rutas_posibles", "de_que_trata", "guardado_en", "bytes"]

# ---------- inventario: tamaño -> rutas
por_tam = defaultdict(list)
if os.path.exists(INV):
    with gzip.open(INV, "rt", encoding="utf-8", errors="surrogateescape") as f:
        for ln in f:
            p = ln.rstrip("\n").split("\t")
            if len(p) < 3 or "/@" in p[0] or "/#recycle" in p[0]:
                continue
            try:
                por_tam[int(p[1])].append(p[0])
            except ValueError:
                pass

def ext_de(r):
    return os.path.splitext(r)[1].lower().lstrip(".")

COMPAT = {"pdf": {"pdf"}, "docx": {"docx", "docm"}, "xlsx": {"xlsx", "xlsm"},
          "pptx": {"pptx"}, "zip": {"zip", "docx", "xlsx", "xlsm", "pptx", "odt", "ods", "jar", "apk"}}

# ---------- lectura de contenido
def limpio_txt(s):
    s = html.unescape(re.sub(r"\s+", " ", s)).strip()
    return s

def tipo_zip(p):
    try:
        with zipfile.ZipFile(p) as z:
            n = z.namelist()
    except Exception:
        return "zip"
    if any(x.startswith("word/") for x in n): return "docx"
    if any(x.startswith("xl/") for x in n): return "xlsx"
    if any(x.startswith("ppt/") for x in n): return "pptx"
    return "zip"

def leer_zip(p, tipo):
    try:
        z = zipfile.ZipFile(p)
        malo = z.testzip()
    except Exception as e:
        return "dañado", ""
    estado = "perfecto" if malo is None else "dañado"
    txt = ""
    try:
        def x(nombre):
            return z.read(nombre).decode("utf-8", "ignore") if nombre in z.namelist() else ""
        core = x("docProps/core.xml")
        tit = re.search(r"<dc:title>(.*?)</dc:title>", core or "")
        tit = limpio_txt(tit.group(1)) if tit else ""
        if tipo == "docx":
            cuerpo = re.sub(r"</w:p>", "\n", x("word/document.xml"))
            cuerpo = re.sub(r"<[^>]+>", "", cuerpo)
            lineas = [limpio_txt(l) for l in cuerpo.split("\n") if len(limpio_txt(l)) > 3]
            txt = " | ".join(([tit] if tit else []) + lineas[:3])
        elif tipo == "xlsx":
            hojas = re.findall(r'<sheet [^>]*name="([^"]+)"', x("xl/workbook.xml"))
            ss = re.findall(r"<t[^>]*>([^<]{3,})</t>", x("xl/sharedStrings.xml"))
            txt = "Hojas: " + ", ".join(html.unescape(h) for h in hojas[:6])
            if ss:
                txt += " | " + " · ".join(limpio_txt(s) for s in ss[:6])
            if tit: txt = tit + " | " + txt
        elif tipo == "pptx":
            s1 = re.findall(r"<a:t>([^<]+)</a:t>", x("ppt/slides/slide1.xml"))
            txt = " ".join(([tit] if tit else []) + s1[:8])
        else:
            txt = "ZIP con: " + ", ".join(z.namelist()[:6])
    except Exception:
        pass
    return estado, limpio_txt(txt)[:250]

def leer_pdf(p):
    r = subprocess.run(["pdftotext", "-l", "2", "-layout", p, "-"], capture_output=True, timeout=60)
    errs = r.stderr.decode("utf-8", "ignore").lower().count("error")
    info = subprocess.run(["pdfinfo", p], capture_output=True, timeout=30).stdout.decode("utf-8", "ignore")
    paginas = re.search(r"Pages:\s+(\d+)", info)
    estado = "perfecto" if (r.returncode == 0 and errs == 0 and paginas) else "dañado"
    tit = re.search(r"Title:\s+(.+)", info)
    tit = tit.group(1).strip() if tit else ""
    tit = re.sub(r"^(Microsoft (Word|Excel|PowerPoint) - )", "", tit)
    if re.fullmatch(r"(untitled|sin t[ií]tulo|documento\d*|\s*|.*\.(tmp|aspx)|[0-9a-f-]{20,})", tit, re.I):
        tit = ""
    lineas = [limpio_txt(l) for l in r.stdout.decode("utf-8", "ignore").splitlines()]
    lineas = [l for l in lineas if len(re.findall(r"[A-Za-zÁÉÍÓÚÑáéíóúñ]", l)) >= 4][:4]
    txt = " | ".join(([tit] if tit else []) + lineas)
    if paginas:
        txt = "(%s pág) %s" % (paginas.group(1), txt)
    return estado, txt[:250]

def nombre_seguro(s, n=90):
    s = re.sub(r"^\(\d+ pág\) ", "", s)
    s = re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", s)
    s = re.sub(r"\s+", " ", s).strip(" .|-")
    return (s[:n].rstrip(" .|-") or "sin_texto")

def destino_libre(p):
    if not os.path.exists(p):
        return p
    base, ext = os.path.splitext(p)
    i = 2
    while os.path.exists("%s (%d)%s" % (base, i, ext)):
        i += 1
    return "%s (%d)%s" % (base, i, ext)

# ---------- índice previo (re-ejecutable)
hechos = {}
if os.path.exists(IDX):
    with open(IDX, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            hechos[row["archivo_rescatado"]] = row

filas = list(hechos.values())
os.makedirs(DEST, exist_ok=True); os.makedirs(EXTRA, exist_ok=True)
nuevos = 0
for carpeta in ("pdf", "word", "excel", "powerpoint", "zip"):
    d = os.path.join(ORIG, carpeta)
    if not os.path.isdir(d):
        continue
    for fn in sorted(os.listdir(d)):
        rel = carpeta + "/" + fn
        if rel in hechos:
            continue
        p = os.path.join(d, fn)
        tam = os.path.getsize(p)
        tipo = "pdf" if carpeta == "pdf" else tipo_zip(p)
        try:
            estado, txt = leer_pdf(p) if tipo == "pdf" else leer_zip(p, tipo)
        except Exception as e:
            estado, txt = "dañado", ""
        cands = [r for r in por_tam.get(tam, []) if ext_de(r) in COMPAT[tipo]]
        if len(cands) == 1:
            coinc = "exacta (única)"
        elif cands and len({os.path.basename(c) for c in cands}) == 1:
            coinc = "exacta (mismo archivo en %d carpetas)" % len(cands)
        elif cands:
            coinc = "ambigua (%d archivos con ese tamaño)" % len(cands)
        else:
            coinc = "sin coincidencia"
        if cands and not coinc.startswith("ambigua"):
            ruta = cands[0]
            rel_dest = re.sub(r"^/volume\d+/", "", ruta)
            dst = os.path.join(DEST, rel_dest)
            if estado != "perfecto":
                b, e = os.path.splitext(dst); dst = b + " [DAÑADO]" + e
        else:
            ruta = ""
            sub = {"pdf": "PDF", "docx": "Word", "xlsx": "Excel", "pptx": "PowerPoint", "zip": "ZIP"}[tipo]
            if estado != "perfecto":
                sub += "/_dañados"
            dst = os.path.join(EXTRA, sub, nombre_seguro(txt) + "." + tipo)
        dst = destino_libre(dst)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            os.link(p, dst)          # mismo disco: no ocupa espacio extra
        except OSError:
            shutil.copy2(p, dst)
        if coinc.startswith("exacta (mismo"):   # replicar en cada carpeta donde existía
            for otra in cands[1:]:
                d2 = os.path.join(DEST, re.sub(r"^/volume\d+/", "", otra))
                if estado != "perfecto":
                    b2, e2 = os.path.splitext(d2); d2 = b2 + " [DAÑADO]" + e2
                if os.path.exists(d2):
                    continue
                os.makedirs(os.path.dirname(d2), exist_ok=True)
                try:
                    os.link(p, d2)
                except OSError:
                    shutil.copy2(p, d2)
        filas.append({"archivo_rescatado": rel, "tipo": tipo, "estado": estado,
                      "ruta_original": ruta, "coincidencia": coinc,
                      "otras_rutas_posibles": " || ".join(cands[1:6]) if cands else "",
                      "de_que_trata": txt, "guardado_en": dst.replace(os.path.expanduser("~/Escritorio/"), ""), "bytes": tam})
        nuevos += 1

with open(IDX, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";")
    w.writeheader(); w.writerows(filas)

from collections import Counter
print("inventario NAS: %d tamaños distintos" % len(por_tam))
print("procesados ahora: %d · total en índice: %d" % (nuevos, len(filas)))
print("estado:", dict(Counter(r["estado"] for r in filas)))
print("tipo:", dict(Counter(r["tipo"] for r in filas)))
print("coincidencia:", dict(Counter(r["coincidencia"].split(" (")[0] for r in filas)))
