#!/usr/bin/env python3
"""Repara docx/xlsx/pptx parcialmente cifrados (zonas en cero): reconstruye el ZIP con las
entradas internas que quedaron íntegras. Uso: reparar_office.py <crudo> <salida>"""
import io, json, os, re, struct, sys, zlib, zipfile

CT = {
 "docx": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Default Extension="jpeg" ContentType="image/jpeg"/><Default Extension="emf" ContentType="image/x-emf"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/><Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>',
 "xlsx": '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>{SHEETS}<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
}
RELS_DOC = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="{T}"/></Relationships>'

def entradas(data, zonas):
    def limpio(a, b):
        return all(b <= x or a >= y for x, y in zonas)
    out = {}
    i = data.find(b"PK\x03\x04")
    while i != -1:
        try:
            (ver, flag, met, _, _, crc, csz, usz, nl, xl) = struct.unpack("<HHHHHIIIHH", data[i+4:i+30])
            nombre = data[i+30:i+30+nl].decode("utf-8", "replace")
            ini = i + 30 + nl + xl
            if flag & 8 and csz == 0:                 # tamaño en descriptor: buscar fin del deflate
                d = zlib.decompressobj(-15)
                raw = d.decompress(data[ini:ini + 50_000_000])
                if not d.eof: raise ValueError
                fin = len(data[ini:ini + 50_000_000]) - len(d.unused_data) + ini
                if not limpio(i, fin): raise ValueError
                cont = raw
            else:
                fin = ini + csz
                if not limpio(i, fin) or fin > len(data): raise ValueError
                blob = data[ini:fin]
                cont = zlib.decompress(blob, -15) if met == 8 else blob
                if crc and zlib.crc32(cont) & 0xffffffff != crc: raise ValueError
            if nombre and nombre not in out and not nombre.endswith("/"):
                out[nombre] = cont
            i = data.find(b"PK\x03\x04", max(fin, i + 4))
        except Exception:
            i = data.find(b"PK\x03\x04", i + 4)
    return out

def reparar(crudo, dst):
    ext = crudo.rsplit(".", 1)[-1].lower()
    data = open(crudo, "rb").read()
    zj = crudo + ".zonas.json"
    zonas = [tuple(z) for z in json.load(open(zj))["zonas"]] if os.path.exists(zj) else []
    ent = entradas(data, zonas)
    clave = {"docx": "word/document.xml", "xlsx": "xl/workbook.xml", "xlsm": "xl/workbook.xml",
             "pptx": "ppt/presentation.xml"}.get(ext)
    if not ent:
        return "sin_contenido", 0
    tipo = "xlsx" if ext in ("xlsx", "xlsm") else ext
    if tipo == "xlsx" and "xl/workbook.xml" not in ent:
        hojas = sorted((int(m.group(1)), n) for n in ent
                       for m in [re.match(r"xl/worksheets/sheet(\d+)\.xml$", n)] if m)
        if hojas:
            nombres = {}
            app = ent.get("docProps/app.xml", b"").decode("utf-8", "ignore")
            tit = re.findall(r"<vt:lpstr>([^<]+)</vt:lpstr>", app)
            sh = "".join('<sheet name="%s" sheetId="%d" r:id="rS%d"/>' % (
                ("Hoja%d" % k), k, k) for k, _ in hojas)
            ent["xl/workbook.xml"] = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets>%s</sheets></workbook>' % sh).encode()
            R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
            rels = "".join('<Relationship Id="rS%d" Type="%sworksheet" Target="worksheets/sheet%d.xml"/>' % (k, R, k)
                           for k, _ in hojas)
            if "xl/styles.xml" in ent:
                rels += '<Relationship Id="rSt" Type="%sstyles" Target="styles.xml"/>' % R
            if "xl/sharedStrings.xml" in ent:
                rels += '<Relationship Id="rSS" Type="%ssharedStrings" Target="sharedStrings.xml"/>' % R
            if "xl/theme/theme1.xml" in ent:
                rels += '<Relationship Id="rTh" Type="%stheme" Target="theme/theme1.xml"/>' % R
            ent["xl/_rels/workbook.xml.rels"] = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s'
                '</Relationships>' % rels).encode()
            # Content_Types propio para garantizar los overrides de las hojas
            ent.pop("[Content_Types].xml", None)
            # quitar partes que dependen del workbook perdido (tablas dinámicas, conexiones)
            for n in [n for n in ent if n.startswith(("xl/pivotCache/", "xl/pivotTables/", "xl/externalLinks/",
                                                     "xl/connections", "xl/calcChain"))]:
                ent.pop(n)
            for n in [n for n in ent if re.match(r"xl/worksheets/_rels/sheet\d+\.xml\.rels$", n)]:
                ent.pop(n)                             # dibujos/tablas pueden faltar: hojas sin adornos
            for _, n in hojas:                         # quitar referencias r:id que ya no existen
                x = ent[n].decode("utf-8", "ignore")
                x = re.sub(r"<(drawing|legacyDrawing|legacyDrawingHF|picture)\b[^>]*/>", "", x)
                x = re.sub(r"<tableParts\b.*?</tableParts>", "", x, flags=re.S)
                x = re.sub(r"<hyperlinks\b.*?</hyperlinks>", "", x, flags=re.S)
                x = re.sub(r"<pageSetup\b[^>]*/>", "", x)
                ent[n] = x.encode("utf-8")
    if "[Content_Types].xml" not in ent and tipo in CT:
        hojas = "".join('<Override PartName="/%s" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % n
                        for n in ent if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
        ent["[Content_Types].xml"] = CT[tipo].replace("{SHEETS}", hojas).encode()
    if "_rels/.rels" not in ent and clave:
        ent["_rels/.rels"] = RELS_DOC.replace("{T}", clave).encode()
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ent.pop("[Content_Types].xml"))
        for n, c in ent.items():
            z.writestr(n, c)
    estado = "completo_estructura" if clave in ent or clave is None else "sin_cuerpo_principal"
    return estado, len(ent)

if __name__ == "__main__":
    print(reparar(sys.argv[1], sys.argv[2]))
