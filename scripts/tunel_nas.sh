#!/bin/bash
# TÚNEL SSH para trabajar en la NAS SIN que la NAS tenga internet.
#
# La NAS no necesita internet: solo necesita estar en la MISMA RED que esta máquina
# (LAN, router sin salida o el punto de acceso del celular). El agente nunca se
# conecta a la NAS: se conecta a 127.0.0.1 y el túnel hace el resto.
#
# POR QUÉ HACE FALTA: el agente corre en ESTA máquina, no en la tuya. Una extensión
# de VS Code (Cloud/Remote/Tunnel) corre en el equipo donde abres VS Code, así que
# serviría para que TÚ teclees comandos, no para que el agente trabaje solo.
#
# ANTES (una sola vez): llave pública en la NAS, para no escribir contraseñas.
#   ssh-copy-id -p <PUERTO> admin@<IP_DE_LA_NAS>
#
# USO:  ./tunel_nas.sh <IP_DE_LA_NAS> [PUERTO_SSH]
# Ejemplo: ./tunel_nas.sh 192.168.1.50 22
set -euo pipefail

IP="${1:?Falta la IP de la NAS. Ej: ./tunel_nas.sh 192.168.1.50 22}"
PUERTO="${2:-22}"
USUARIO="${NAS_USER:-admin}"

echo "Túnel hacia ${USUARIO}@${IP}:${PUERTO}"
echo "  Un servicio web de la NAS ....... http://127.0.0.1:9222"
echo "  Otro servicio web de la NAS ..... http://127.0.0.1:9300"
echo "  (deja esta terminal abierta; Ctrl+C para cerrar)"
echo

exec ssh -N \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -L 127.0.0.1:9222:127.0.0.1:9222 \
  -L 127.0.0.1:9300:127.0.0.1:9078 \
  -p "$PUERTO" "${USUARIO}@${IP}"
