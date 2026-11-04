#!/usr/bin/env python3
"""Trae al Escritorio los PDF/Office tallados del pool de Active Backup del NAS de la víctima.
Por lotes, reanudable, deduplica por sha1 entre lotes. Nada se escribe en el NAS.
Uso: python3 traer_pool.py [--desde N] [--hasta N] [--lote 300]"""
import argparse, hashlib, json, os, subprocess, sys, tarfile, time

AQUI = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("NAS_KEY", os.path.join(AQUI, "..", "acceso", "nas_key"))
NAS = "root@" + os.environ.get("NAS_IP", "IP_DE_LA_NAS")
CARVER = os.path.join(AQUI, "tallar_pool.py")
DEST = os.path.expanduser("~/Escritorio/RESCATE_CLIENTE_BACKUP")
ESTADO = os.path.join(DEST, "_estado")
TOTAL = 31398

ap = argparse.ArgumentParser()
ap.add_argument("--desde", type=int, default=0)
ap.add_argument("--hasta", type=int, default=TOTAL + 600)
ap.add_argument("--lote", type=int, default=300)
a = ap.parse_args()

os.makedirs(ESTADO, exist_ok=True)
f_hechos = os.path.join(ESTADO, "lotes_hechos.txt")
f_hash = os.path.join(ESTADO, "hashes.txt")
f_log = os.path.join(ESTADO, "progreso.log")
hechos = set(open(f_hechos).read().split()) if os.path.exists(f_hechos) else set()
vistos = set(open(f_hash).read().split()) if os.path.exists(f_hash) else set()

def log(msg):
    linea = time.strftime("%Y-%m-%d %H:%M:%S ") + msg
    print(linea, flush=True)
    with open(f_log, "a") as f:
        f.write(linea + "\n")

def un_lote(ini, fin):
    cmd = ["ssh", "-i", KEY, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
           "-o", "UserKnownHostsFile=/dev/null", "-o", "ServerAliveInterval=30",
           "-o", "LogLevel=ERROR", NAS, "python3 - %d %d" % (ini, fin)]
    with open(CARVER, "rb") as src:
        pr = subprocess.Popen(cmd, stdin=src, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    nuevos = dup = 0; st = {}
    tf = tarfile.open(fileobj=pr.stdout, mode="r|")
    for m in tf:
        if not m.isfile():
            continue
        blob = tf.extractfile(m).read()
        if m.name.startswith("_stats/"):
            st = json.loads(blob); continue
        h = hashlib.sha1(blob).hexdigest()
        if h in vistos:
            dup += 1; continue
        destino = os.path.join(DEST, m.name)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as f:
            f.write(blob)
        vistos.add(h); nuevos += 1
        with open(f_hash, "a") as f:
            f.write(h + "\n")
    pr.wait()
    if pr.returncode != 0 or not st:
        raise RuntimeError("ssh rc=%s err=%s" % (pr.returncode, pr.stderr.read()[-300:]))
    return nuevos, dup, st

t0 = time.time()
for ini in range(a.desde, a.hasta, a.lote):
    fin = ini + a.lote
    clave = "%d-%d" % (ini, fin)
    if clave in hechos:
        continue
    for intento in range(1, 6):
        try:
            s = time.time()
            nuevos, dup, st = un_lote(ini, fin)
            mb = st.get("bytes", 0) / 1e6
            log("lote %s: %d nuevos, %d dup local, NAS: pdf=%d office=%d dup=%d cruza=%d, %.1f MB en %.0fs"
                % (clave, nuevos, dup, st.get("pdf", 0), st.get("office", 0), st.get("dup", 0),
                   st.get("cruza_franja", 0), mb, time.time() - s))
            with open(f_hechos, "a") as f:
                f.write(clave + "\n")
            hechos.add(clave)
            if st.get("buckets", 0) == 0 and ini > TOTAL:
                log("fin del pool"); sys.exit(0)
            break
        except Exception as e:
            log("lote %s intento %d falló: %s" % (clave, intento, str(e)[:200]))
            time.sleep(30 * intento)
    else:
        log("lote %s abandonado tras 5 intentos; sigo con el siguiente" % clave)
log("terminado en %.1f h · archivos únicos: %d" % ((time.time() - t0) / 3600, len(vistos)))
