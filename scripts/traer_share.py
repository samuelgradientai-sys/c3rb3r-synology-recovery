#!/usr/bin/env python3
"""Trae Share (zonas cifradas en cero) a ~/rescate_cliente/share_crudo/, por lotes, reanudable."""
import base64, json, os, subprocess, sys, tarfile, time

AQUI = os.path.dirname(os.path.abspath(__file__))
KEY = os.environ.get("NAS_KEY", os.path.join(AQUI, "..", "acceso", "nas_key"))
CRUDO = os.path.expanduser("~/rescate_cliente/share_crudo")
LISTA = json.load(open(os.path.expanduser("~/rescate_cliente/salida/dt_lista.json")))
HECHOS = os.path.join(CRUDO, "_hechos.txt")
LOG = os.path.join(CRUDO, "_progreso.log")
src = open(os.path.join(AQUI, "nas_parcial.py")).read()
LINEA = [l for l in src.splitlines() if l.startswith("LISTA = ")][0]

os.makedirs(CRUDO, exist_ok=True)
hechos = set(open(HECHOS).read().split("\n")) if os.path.exists(HECHOS) else set()

def log(m):
    m = time.strftime("%H:%M:%S ") + m
    print(m, flush=True); open(LOG, "a").write(m + "\n")

MAXB = 400 * 2**20      # ~400 MB por lote
lote = []; tam = 0; lotes = []
for it in LISTA:
    if it[0] in hechos:
        continue
    lote.append(it); tam += it[1]
    if tam >= MAXB or len(lote) >= 150:
        lotes.append(lote); lote = []; tam = 0
if lote:
    lotes.append(lote)
log("lotes pendientes: %d (%d archivos)" % (len(lotes), sum(map(len, lotes))))

for i, lote in enumerate(lotes, 1):
    code = src.replace(LINEA, "LISTA = json.loads(base64.b64decode(%r).decode('ascii'))" % base64.b64encode(json.dumps(lote, ensure_ascii=True).encode()).decode())
    for intento in range(1, 6):
        t = time.time(); n = 0; byt = 0
        try:
            pr = subprocess.Popen(["ssh", "-i", KEY, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
                                   "-o", "UserKnownHostsFile=/dev/null", "-o", "LogLevel=ERROR",
                                   "-o", "ServerAliveInterval=30", "root@" + os.environ.get("NAS_IP", "IP_DE_LA_NAS"), "python3 -"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            pr.stdin.write(code.encode("utf-8", "surrogateescape")); pr.stdin.close()
            tf = tarfile.open(fileobj=pr.stdout, mode="r|gz")
            for m in tf:
                dst = os.path.join(CRUDO, m.name)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                with open(dst, "wb") as f:
                    f.write(tf.extractfile(m).read())
                if not m.name.endswith(".zonas.json"):
                    n += 1; byt += m.size
            pr.wait()
            if pr.returncode != 0:
                raise RuntimeError("rc=%s" % pr.returncode)
            with open(HECHOS, "a") as f:
                for it in lote:
                    f.write(it[0] + "\n")
            log("lote %d/%d: %d archivos, %.0f MB en %.0fs (%s)" % (i, len(lotes), n, byt / 1e6, time.time() - t,
                lote[0][0].rsplit(".", 1)[-1]))
            break
        except Exception as e:
            log("lote %d intento %d falló: %s" % (i, intento, e)); time.sleep(20 * intento)
log("TERMINADO")
