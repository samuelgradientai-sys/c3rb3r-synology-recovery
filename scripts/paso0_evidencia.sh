#!/bin/sh
# PASO 0 — Congelar la escena. SOLO LECTURA. No escribe nada en los volúmenes de datos.
# Uso:  sh paso0_evidencia.sh > /tmp/evidencia_cliente.txt 2>&1 ; tail -40 /tmp/evidencia_cliente.txt
# (en DSM, /tmp está en la partición de sistema; son unos pocos KB de texto)

echo "===== 1. FECHA Y EQUIPO ====="
date -u; echo; uname -a 2>/dev/null; echo
cat /etc/VERSION 2>/dev/null; cat /etc.defaults/VERSION 2>/dev/null | head -6

echo; echo "===== 2. VOLÚMENES Y ESPACIO LIBRE (clave: define si el carving sirve) ====="
df -h 2>/dev/null | grep -Ev "^(Filesystem|tmpfs|none)" | head -20
echo; echo "-- btrfs:"
btrfs fi show 2>/dev/null || echo "(btrfs no disponible en PATH)"
echo; echo "-- uso por volumen:"
btrfs fi usage -T /volume1 2>/dev/null | tail -20

echo; echo "===== 3. SNAPSHOTS OCULTOS (la via mas rapida si existen) ====="
for v in /volume1 /volume2 /volume3 /volume4; do
  [ -d "$v" ] || continue
  echo "-- $v/@sharesnap:"
  ls -la "$v/@sharesnap" 2>&1 | head -12
  echo "-- $v/@sharesnap/*/ (por share):"
  ls -d "$v"/@sharesnap/*/* 2>/dev/null | head -10
done
echo; echo "-- snapshots visibles por share:"
ls -d /volume*/@*/ 2>/dev/null | grep -i snap | head -10

echo; echo "===== 4. SHARES Y CONTEO DE CIFRADOS ====="
for v in /volume1 /volume2 /volume3 /volume4; do
  [ -d "$v" ] || continue
  echo "-- $v:"
  ls -1 "$v" 2>/dev/null | grep -v "^@" | head -25
  echo "   archivos .L0CK3D: $(find "$v" -name '*.L0CK3D' 2>/dev/null | wc -l)"
  echo "   bytes cifrados:   $(find "$v" -name '*.L0CK3D' -type f -exec stat -c %s {} + 2>/dev/null | awk '{s+=$1} END {print s+0}')"
done

echo; echo "===== 5. NOTA DE RESCATE (evidencia, no borrar) ====="
find /volume* -maxdepth 6 -iname "read-me3*" -o -maxdepth 6 -iname "*RESTORE*" 2>/dev/null | head -5

echo; echo "===== 6. ¿SIGUE VIVO EL CIFRADOR? ====="
ps 2>/dev/null | grep -iE "libgld|c3rb|lock3d" | grep -v grep
echo "-- procesos sospechosos de reciente creacion:"
ls -lt /proc/*/exe 2>/dev/null | head -8

echo; echo "===== 7. CONEXIONES HACIA EL C2 (208.87.128.140:4001) ====="
netstat -tnp 2>/dev/null | grep -E "4001|208.87.128.140" || echo "(sin conexiones visibles)"
ss -tnp 2>/dev/null | grep -E "4001|208.87.128.140" || true

echo; echo "===== 8. PERSISTENCIA: TAREAS PROGRAMADAS ====="
echo "-- /etc/crontab:"; cat /etc/crontab 2>/dev/null
echo "-- /etc/cron.d:"; ls -la /etc/cron.d 2>/dev/null; cat /etc/cron.d/* 2>/dev/null | head -40
echo "-- crontab de root:"; crontab -l 2>/dev/null
echo "-- tareas con pinta de bomba de tiempo (synot*, curl, wget, IP):"
grep -rEli "synot|curl|wget" /etc/cron.d /etc/crontab /var/spool/cron 2>/dev/null | head -10

echo; echo "===== 9. INTENTOS DE ACCESO Y VERSION DE DSM ====="
grep -aE "CVE|libgld|c3rb3r|\.L0CK3D" /var/log/messages 2>/dev/null | tail -5
echo "-- usuarios con shell:"; grep -E "sh$" /etc/passwd 2>/dev/null | head -10
echo "-- Telnet/SSH habilitados:"; grep -iE "telnet|ssh" /etc/ssh/sshd_config 2>/dev/null | grep -viE "^#" | head -6

echo; echo "===== 10. PYTHON DEL NAS (lo necesita la herramienta) ====="
python3 -V 2>&1; python -V 2>&1; which python3 python 2>/dev/null

echo; echo "===== FIN. Nada de esto modifica datos. ====="
