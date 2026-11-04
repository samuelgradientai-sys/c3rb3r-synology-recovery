# Checklist — ventana viva (el cifrador todavía corre)

> **Si el equipo ya se reinició, esta checklist NO aplica.** Ve directo a
> [Caso ya reiniciado](#caso-ya-reiniciado-el-más-común). Un reinicio mata la ruta de la memoria:
> la maestra de 48 B vivía solo en RAM. Es el escenario más común y el que menos se documenta.

Esta checklist existe porque el orden importa más que los comandos: **cada minuto que el proceso sigue
vivo es un minuto de archivos que se cifran**, y la mayoría de las guías dedican ese primer minuto a
cosas que no detienen nada.

## Regla base

- No reiniciar, no apagar, no desinstalar, no `kill -9`. El apagado de pánico es tan letal como el reinicio.
- `SIGSTOP` es reversible: si te equivocas de PID, un `SIGCONT` lo devuelve. Por eso **congelar es lo
  primero**, incluso sin certeza total.
- Nada de lo que hagas debe escribir en `/volume1`.

## Orden correcto (y por qué)

| # | Paso | Por qué |
|---|---|---|
| 1 | Identificar el PID y **guardar el ejecutable** (`cp /proc/PID/exe`) con su SHA-256 | Sin el binario no hay perfil de direcciones que aplicar |
| 2 | **`kill -STOP` — antes de cualquier GUI** | Es lo único que detiene el cifrado, y son 2 segundos |
| 3 | Confirmar que dejó de escribir (mtime del directorio) | Si no, "congelado" es una suposición |
| 4 | Contener red: QuickConnect, reenvíos, Cloud Sync | Importa para el C2, **no** para el cifrado |
| 5 | Desactivar actualización automática de DSM | Un reinicio programado te borra la ventana entera |
| 6 | Persistencia: comentar las `synot*` de `/etc/crontab` y `/etc/cron.d` | Sin borrarlas: son evidencia y te vuelven a cifrar tras un reinicio |
| 7 | Capturar memoria (a USB, nunca al volumen cifrado) | El dump es la única copia de la maestra |

Congelar antes de contener no es un detalle de estilo: en la secuencia inversa se pierden minutos
apagando QuickConnect mientras el binario sigue escribiendo.

## Puertas duras

Si una falla, no sigas como si nada: la captura puede salir "bien" y no servir para la clave.

**Puerta 1 — está congelado de verdad.**
```bash
cat /proc/$PID/status | grep -E 'State|Threads|TracerPid'
# Todos los hilos en T (un D está esperando E/S: reintentar STOP), TracerPid en 0
ls -la --time-style=full-iso /volume1/<carpeta-afectada> | head   # el mtime deja de avanzar
```
Repetir el `ls` dos veces con 10 s de diferencia. Si los mtimes siguen cambiando, hay otro proceso
cifrando: `for p in $(pgrep -f libgld); do ...` y congelarlos todos.

**Puerta 2 — el proceso no tiene memoria paginada fuera del dump.**
```bash
grep VmSwap /proc/$PID/status
```
Si `VmSwap` no es 0, parte de la maestra puede estar en swap o zram y el dump del proceso no la
incluirá. DSM usa zram por defecto en bastantes modelos. En ese caso hay que volcar también
`/proc/swaps` y el dispositivo zram, o barrer una imagen completa de RAM (`recover_ram_keys.py`).

**Puerta 3 — la dirección del puntero está dentro de algo capturado.**
Después de capturar, antes de correr `recover_process_key.py`:
```bash
grep -n '0x5427f8' <salida>/regions.jsonl || echo "PUNTERO FUERA DEL DUMP"
```
El perfil apunta a `0x5427f8` (48 B). Si ese mapeo quedó excluido —el colector puede salir con
código 2 por páginas ilegibles—, el dump no vale para la clave por mucho que pese. Este es el fallo
práctico más común: se culpa al perfil cuando el problema es la región.

**Puerta 4 — el binario es el de la muestra.**
```bash
sha256sum encryptor.bin   # debe empezar por 802ac85d
```
Si no coincide: **el toolkit probablemente no dará la clave**. Ni `recover_process_key.py` ni
`recover_ram_keys.py` sirven como plan B automático — ambos usan el layout verificado de esa muestra.
Las salidas honestas son: el test gratuito de 1 MB, pagar, o ingeniería inversa propia. Ubicar el
puntero a mano solo tiene sentido si el layout es igual y lo que falló fue la captura de la región.

## Captura

```bash
python3 <usb>/scripts/capture_process_memory.py inspect --pid $PID
python3 <usb>/scripts/capture_process_memory.py capture \
  --pid $PID \
  --expected-start-ticks $(cat 15-start-ticks.txt) \
  --expected-exe-sha256 $(cat 11-exe-sha.txt) \
  --expected-output-device $(cat 16-output-device.txt) \
  --output <usb>/caso1/process-new
```

El directorio de salida no debe existir. Los huecos del dump son rellenos a cero, **no** memoria cero.
Código de salida 2 = páginas ilegibles o mapeos excluidos: la captura sigue sirviendo, pero revisa la
Puerta 3 antes de ilusionarte. El colector no usa debugger y no cambia el estado del proceso.

Sellar y desmontar:

```bash
sha256sum <usb>/caso1/process-new/* > 17-dump-sha.txt
sync; cd /; umount <usb>
```

## Extraer y validar la clave

```bash
.venv/bin/python scripts/recover_process_key.py \
  --capture /analisis/process-copy \
  --profile assets/libgld-802ac85d.json \
  --output /analisis/private/master.bin
```

`master.bin` son 48 bytes: IV16 + clave AES32. **Extraer 48 bytes no es haber descifrado.**

Al verificar, la regla que casi nadie escribe y que evita días perdidos:

> **Una IV equivocada pasa la comprobación de nonce repetido y produce basura.** Que el archivo
> decodifique no prueba nada. Hay que abrirlo y comprobarlo a mano, y probar varios archivos y los
> tres modos (`0x24`, `0x25`, `0x26`) antes de extender el descifrado a todo el volumen.

Si tienes un original conocido, úsalo: `--expected-sha256` convierte "parece que sí" en verificación.

**No uses la clave candidata publicada de otro incidente.** La del 28-oct está publicada en
`profiles/recovery-key-20261028.json` y fue validada **solo** para ese incidente; en otro caso falla el
chequeo de nonce. Está publicada, no es universal.

## Parches: dos avisos, y manda el más nuevo

| Aviso | CVE | Builds corregidos |
|---|---|---|
| SA-24:20 (dic-2024) | CVE-2024-10441 (RCE root), -50629 (lectura), -10445 (escritura) | 7.2.2-72806-1 · 7.2.1-69057-6 · 7.2-64570-4 · 7.1.1-42962-7 · 6.2.4-25556-8 |
| **SA-26:13 (sep-2026)** | CVE-2026-13684 (SCGI, CWE-116), -13639 (entropía del login), +6 más | **7.4-90075 · 7.3.2-86009-4 · 7.2.2-72806-9 · 7.2.1-69057-12** |

Ojo con la semántica: los CVE dicen "**before** 7.2.2-72806-9", así que un equipo en 72806-1 —el mínimo
de SA-24:20— sigue afectado por SA-26:13. La barra real es el build más nuevo de las dos tablas.
7.1.1 y 6.2 no aparecen en SA-26:13 porque esa rama no está soportada ahí, no porque esté a salvo.

## Caso ya reiniciado (el más común)

La RAM ya no existe. Quedan snapshots y bloques viejos de Btrfs, en ese orden.

```bash
sudo btrfs subvolume list /volume1          # verdad de base, no la GUI
sudo ls -la --time-style=full-iso /volume1/@sharesnap/
```

- De cada snapshot interesa **la fecha**: solo sirve lo anterior al inicio del cifrado.
- La interfaz puede mostrar `#snapshot` o el contador **vacío con snapshots intactos**. No te fíes de ella.
- Si hay uno bueno: **Clonar** a una carpeta nueva, nunca "Restaurar" encima.
- Revisar también Hyper Backup y cualquier copia en disco desconectado.

Sin snapshots útiles: imagen de solo lectura del volumen y reconstrucción por bloques viejos
([crt106/c3rb3r-btrfs-recovery](https://github.com/crt106/c3rb3r-btrfs-recovery)). Nada de escribir en
`/volume1` mientras se trabaja. Si el volumen está en **EXT4**, no hay copy-on-write y esta vía no existe:
quedan copias externas.

Si no hay nada de eso: el test gratuito de 1 MB existe, pero aplica justo a los archivos pequeños —los
más irrecuperables— y el reloj de la duplicación corre **desde la nota**, no desde el reinicio.

## Errores que se cometen siempre

1. Contener la red antes de congelar el proceso.
2. Confiar en la interfaz para saber si hay snapshots.
3. Copiar el dump a una carpeta del volumen cifrado.
4. Creer que el toolkit sirve con otro binario.
5. Dar por descifrado un archivo porque decodifica.
6. Volver a encender el equipo con la persistencia activa y el router conectado.
