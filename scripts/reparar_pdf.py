#!/usr/bin/env python3
"""Reconstruye PDFs parcialmente cifrados (zonas en cero): conserva los objetos sanos,
crea un catálogo y árbol de páginas nuevos con las páginas que sobrevivieron y guarda
un PDF que abre. Además extrae las imágenes JPEG sueltas. Requiere pymupdf.
Uso: reparar_pdf.py <crudo.pdf> <salida.pdf>  -> imprime JSON con resultado."""
import json, os, re, sys
import pymupdf

pymupdf.TOOLS.mupdf_display_errors(False)
pymupdf.TOOLS.mupdf_display_warnings(False)

def limpio_fn(zonas):
    return lambda a, b: all(b <= x or a >= y for x, y in zonas)

def objetos_sanos(data, zonas):
    limpio = limpio_fn(zonas)
    out = []
    for m in re.finditer(rb"(?<![0-9])(\d{1,7})\s+(\d{1,5})\s+obj\b", data):
        ini = m.start()
        fin = data.find(b"endobj", m.end())
        if fin == -1:
            continue
        fin += 6
        if limpio(ini, fin):
            out.append((int(m.group(1)), data[ini:fin]))
    return out

def reparar(crudo, salida):
    data = open(crudo, "rb").read()
    zj = crudo + ".zonas.json"
    zonas = [tuple(z) for z in json.load(open(zj))["zonas"]] if os.path.exists(zj) else []
    objs = objetos_sanos(data, zonas)
    if not objs:
        return {"estado": "sin_objetos", "paginas": 0}
    # 1) PDF provisional solo con objetos sanos (sin xref: MuPDF lo reconstruye)
    vistos = {}
    for num, b in objs:
        vistos[num] = b                       # última versión gana (actualizaciones incrementales)
    maxn = max(vistos)
    cuerpo = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + b"\n".join(vistos[n] for n in sorted(vistos)) + b"\n"
    tmp = salida + ".tmp.pdf"
    open(tmp, "wb").write(cuerpo + b"trailer\n<< /Size %d >>\n%%%%EOF\n" % (maxn + 3))
    doc = pymupdf.open(tmp)
    # 2) localizar páginas (incluidas las que vivían dentro de object streams)
    paginas = []; padres = set()
    for x in range(1, doc.xref_length()):
        try:
            t = doc.xref_get_key(x, "Type")
        except Exception:
            continue
        if t == ("name", "/Page"):
            paginas.append(x)
            p = doc.xref_get_key(x, "Parent")
            if p[0] == "xref":
                padres.add(int(p[1].split()[0]))
    if not paginas:
        n_img = extraer_imagenes(doc, salida)
        doc.close(); os.remove(tmp)
        return {"estado": "sin_paginas" if not n_img else "solo_imagenes", "paginas": 0,
                "objetos": len(vistos), "imagenes": n_img}
    n_img = extraer_imagenes(doc, salida)
    # 3) árbol nuevo: un Pages raíz con todas las páginas; los padres viejos que faltan se crean
    raiz = doc.get_new_xref()
    for pa in padres:
        try:
            existe = doc.xref_get_key(pa, "Type")[0] != "null"
        except Exception:
            existe = False
        if not existe:
            doc.update_object(pa, "<< /Type /Pages /Kids [] /Count 0 /MediaBox [0 0 612 792] >>")
    kids = " ".join("%d 0 R" % p for p in paginas)
    doc.update_object(raiz, "<< /Type /Pages /Kids [%s] /Count %d /MediaBox [0 0 612 792] >>" % (kids, len(paginas)))
    for p in paginas:
        # conservar atributos heredables antes de cambiar el padre
        for k in ("MediaBox", "Resources", "Rotate"):
            if doc.xref_get_key(p, k)[0] == "null":
                pa = doc.xref_get_key(p, "Parent")
                if pa[0] == "xref":
                    v = doc.xref_get_key(int(pa[1].split()[0]), k)
                    if v[0] != "null":
                        doc.xref_set_key(p, k, v[1])
        doc.xref_set_key(p, "Parent", "%d 0 R" % raiz)
    cat = doc.get_new_xref()
    doc.update_object(cat, "<< /Type /Catalog /Pages %d 0 R >>" % raiz)
    doc.xref_set_key(-1, "Root", "%d 0 R" % cat)
    doc.save(salida, garbage=3, deflate=True)
    doc.close(); os.remove(tmp)
    # 4) verificar: cuántas páginas se dibujan de verdad
    d2 = pymupdf.open(salida); buenas = 0; con_texto = 0
    for pg in d2:
        try:
            pix = pg.get_pixmap(dpi=20)
            # página "en blanco" = casi todos los píxeles iguales
            s = pix.samples
            if len(set(s[::97])) > 3:
                buenas += 1
            if len(pg.get_text().strip()) > 30:
                con_texto += 1
        except Exception:
            pass
    total = d2.page_count; d2.close()
    return {"estado": "ok" if buenas else "paginas_vacias", "paginas": total,
            "paginas_con_contenido": buenas, "paginas_con_texto": con_texto, "imagenes": n_img}

def extraer_imagenes(doc, salida, minimo=25_000):
    """Guarda las imágenes incrustadas (escaneos, fotos) en <salida sin .pdf> [IMÁGENES]/"""
    carpeta = salida[:-4].replace(" [PARCIAL]", "") + " [IMÁGENES]"
    n = 0
    for x in range(1, doc.xref_length()):
        try:
            if doc.xref_get_key(x, "Subtype") != ("name", "/Image"):
                continue
            im = doc.extract_image(x)
        except Exception:
            continue
        if not im or len(im.get("image", b"")) < minimo:
            continue
        os.makedirs(carpeta, exist_ok=True)
        n += 1
        open(os.path.join(carpeta, "imagen_%03d.%s" % (n, im.get("ext", "png"))), "wb").write(im["image"])
    return n

if __name__ == "__main__":
    try:
        r = reparar(sys.argv[1], sys.argv[2])
    except Exception as e:
        r = {"estado": "error", "detalle": str(e)[:200]}
    print(json.dumps(r, ensure_ascii=False))
