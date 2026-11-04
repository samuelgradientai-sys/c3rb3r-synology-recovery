#!/usr/bin/env python3
"""Rescate de las fotos .L0CK3D de Share (cabecera JPEG destruida).

Modo 26 (98 % de los archivos): los primeros 1 MB están en cero (zona cifrada,
irrecuperable sin llave). Se reconstruye la cabecera con la de una foto sana del
mismo sensor y se conserva la parte baja de la imagen que sobrevivió.

Re-ejecutable: salta lo que ya está hecho. Escribe un índice CSV con resultado
por archivo.
"""
from __future__ import annotations

import csv
import json
import os
import signal
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, "~/rescate_cliente/repos/jpeg_recovery")

CRUDO = "~/rescate_cliente/share_crudo"
SALIDA = os.environ.get("FOTOS_SALIDA", "~/Escritorio/NAS-3PL/Share")
MUESTRA = ("~/.clawksis/cache/scratch/jpgtest/"
           "Atrazina por 10kg lote ALLG26040102 (1).jpg")
INDICE = os.path.join(SALIDA, "_SIN_UBICAR", "FOTOS_RECUPERADAS.csv")
LOG = "~/rescate_cliente/_fotos_progreso.log"
_PREFIX_DEFECTO = 1048576
_TIMEOUT = 300


class _Tarde(Exception):
    pass


def _alarma(signum, frame):  # noqa: ARG001
    raise _Tarde("archivo demasiado lento (>300 s)")


_HEADER = None


def _init():
    global _HEADER
    from jpegmedic.core.jpeg import parse_jpeg
    h = parse_jpeg(open(MUESTRA, "rb").read())
    # Altura sobrada: la real se recalcula con las filas que sobrevivieron.
    h.frame.height = 8192
    _HEADER = h
    signal.signal(signal.SIGALRM, _alarma)


def _proc(ruta: str):
    """Devuelve un dict con el resultado para una foto."""
    from jpegmedic.core.recovery import recover_bytes

    rel = os.path.relpath(ruta, CRUDO)
    zona = json.load(open(ruta + ".zonas.json"))
    modo = zona.get("modo", "?")
    zonas = zona.get("zonas", [])
    destino = os.path.join(SALIDA, os.path.splitext(rel)[0] + ".jpg")
    base = dict(origen=rel, salida=destino, modo=modo)

    if os.path.exists(destino) and os.path.getsize(destino) > 0:
        return {**base, "ok": "ya", "ancho": "", "alto": "", "perdidas": "",
                "segundos": 0, "mensaje": "existía"}

    if modo == "26":
        prefijos = [_PREFIX_DEFECTO]
    else:  # modo 25: primer bloque en cero distinto según archivo
        prefijos = [z[1] for z in zonas if z[0] == 0] or [_PREFIX_DEFECTO]

    datos = open(ruta, "rb").read()
    t0 = time.time()
    ultimo = ""
    for prefijo in prefijos:
        try:
            signal.alarm(_TIMEOUT)
            a = recover_bytes(datos, _HEADER, prefijo)
            signal.alarm(0)
        except Exception as exc:  # noqa: BLE001 - el lote no se cae
            signal.alarm(0)
            ultimo = f"{type(exc).__name__}: {exc}"
            continue
        if a.ok and a.data:
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            tmp = destino + ".part"
            with open(tmp, "wb") as fh:
                fh.write(a.data)
            os.replace(tmp, destino)
            return {**base, "ok": "si", "ancho": a.width, "alto": a.height,
                    "perdidas": "",
                    "segundos": round(time.time() - t0, 1), "mensaje": "OK"}
        ultimo = a.message
    return {**base, "ok": "no", "ancho": "", "alto": "", "perdidas": "",
            "segundos": round(time.time() - t0, 1), "mensaje": ultimo[:120]}


def main() -> None:
    archivos = []
    for raiz, _dirs, ficheros in os.walk(CRUDO):
        for n in ficheros:
            if n.lower().endswith((".jpg", ".jpeg")):
                p = os.path.join(raiz, n)
                if os.path.exists(p + ".zonas.json"):
                    archivos.append(p)
    archivos.sort()
    limite = int(os.environ.get("FOTOS_LIMITE", "0"))
    if limite:
        archivos = archivos[:limite]
    total = len(archivos)
    print(f"fotos a procesar: {total}", flush=True)

    nuevos = not os.path.exists(INDICE)
    os.makedirs(os.path.dirname(INDICE), exist_ok=True)
    campos = ["origen", "salida", "modo", "ok", "ancho", "alto",
              "perdidas", "segundos", "mensaje"]
    cuentas: dict[str, int] = {}
    t0 = time.time()
    with open(INDICE, "a", newline="") as fh, open(LOG, "a") as lg:
        w = csv.DictWriter(fh, fieldnames=campos)
        if nuevos:
            w.writeheader()
        with Pool(processes=7, initializer=_init) as pool:
            for i, r in enumerate(pool.imap_unordered(_proc, archivos, chunksize=2), 1):
                w.writerow(r)
                cuentas[r["ok"]] = cuentas.get(r["ok"], 0) + 1
                if i % 25 == 0 or i == total:
                    fh.flush()
                    linea = (f"{i}/{total} ({time.time()-t0:.0f}s) {cuentas}")
                    print(linea, flush=True)
                    lg.write(linea + "\n")
                    lg.flush()
    print("FIN", cuentas, f"en {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
