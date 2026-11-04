#!/usr/bin/env python3
"""Reconstruye lo que se pueda de un .xlsx/.docx/.pptx .L0CK3D en modo HEADER (0x26).

En modo 0x26 solo se cifró el primer 1 MB; el resto quedó en claro, incluido el
directorio central del ZIP (que va al final). Parseando ese directorio sabemos
nombre y tamaño de cada pieza y si su contenido sobrevivió, y rearmamos un ZIP
con las que sí.
"""
import io
import struct
import sys
import zipfile
import zlib
from pathlib import Path

CORTE = 1024 * 1024


def entradas(b: bytes):
    """Recorre el directorio central del ZIP y devuelve las piezas encontradas."""
    i = b.rfind(b"PK\x05\x06")
    if i < 0:
        raise SystemExit("no hay fin de directorio central (EOCD)")
    total = struct.unpack("<H", b[i + 10:i + 12])[0]
    pos = struct.unpack("<I", b[i + 16:i + 20])[0]
    piezas = []
    for _ in range(total):
        if b[pos:pos + 4] != b"PK\x01\x02":
            break
        (metodo,) = struct.unpack("<H", b[pos + 10:pos + 12])
        (crc,) = struct.unpack("<I", b[pos + 16:pos + 20])
        (comp, desc) = struct.unpack("<II", b[pos + 20:pos + 28])
        (nl, ex, nc) = struct.unpack("<HHH", b[pos + 28:pos + 34])
        (off,) = struct.unpack("<I", b[pos + 42:pos + 46])
        nombre = b[pos + 46:pos + 46 + nl].decode("utf-8", "replace")
        piezas.append({"nombre": nombre, "metodo": metodo, "crc": crc, "comp": comp,
                       "desc": desc, "off": off})
        pos += 46 + nl + ex + nc
    return piezas


def datos(b: bytes, e: dict):
    """Devuelve el contenido descomprimido de una pieza, o None si cayó en la zona cifrada."""
    p = e["off"]
    if p < CORTE or b[p:p + 4] != b"PK\x03\x04":
        return None
    nl, ex = struct.unpack("<HH", b[p + 26:p + 30])
    ini = p + 30 + nl + ex
    crudo = b[ini:ini + e["comp"]]
    if len(crudo) < e["comp"]:
        return None
    if e["metodo"] == 0:
        out = crudo
    elif e["metodo"] == 8:
        try:
            out = zlib.decompress(crudo, -15)
        except zlib.error:
            return None
    else:
        return None
    if len(out) != e["desc"] or (zlib.crc32(out) & 0xFFFFFFFF) != e["crc"]:
        return None
    return out


def main(origen: str, destino: str) -> None:
    b = Path(origen).read_bytes()
    piezas = entradas(b)
    ok, perdidas = [], []
    for e in piezas:
        d = datos(b, e)
        (ok if d is not None else perdidas).append((e, d))
    print(f"piezas: {len(piezas)} | recuperadas: {len(ok)} | perdidas: {len(perdidas)}")
    print("\nRECUPERADAS:")
    for e, d in sorted(ok, key=lambda x: -len(x[1])):
        print(f"  {len(d):>9,} B  {e['nombre']}")
    print("\nPERDIDAS (primer MB cifrado):")
    for e, _ in perdidas:
        print(f"  {e['desc']:>9,} B  {e['nombre']}")
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for e, d in ok:
            z.writestr(e["nombre"], d)
    print(f"\nescrito {destino}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
