# Plan de recuperación, en orden de probabilidad

> Para un NAS ya cifrado y **ya reiniciado** (sin memoria del proceso, sin llave). Si el cifrador sigue
> vivo, esto no aplica: ve a `CHECKLIST-ventana-viva.md`.

**Regla que no se negocia: no se escribe en `/volume1`.** Ni paquetes, ni Docker, ni borrar los `.L0CK3D`
para "hacer sitio". Cada bloque que se reasigna es un extent viejo que se pierde. Las herramientas van al
USB. Y nada de `btrfs check --repair` (puede empeorar el árbol) ni `btrfs balance` (reescribe medio
volumen).

## A. Inventario de copias — gratis, y es donde está el dinero

Por orden de probabilidad. Se tacha a medida que se descarta.

1. **Carpetas compartidas cifradas que estaban bloqueadas.** Si tenían contraseña y estaban cerradas
   durante el ataque, su contenido está intacto: el cifrador no llegó. Desbloquear es seguro (es una capa
   dm-crypt por debajo); lo que no se hace es escribir dentro. Montar en solo lectura si es posible.
2. **Unidad de expansión (DX) apagada o desconectada.** No se tocó.
3. **Discos USB/eSATA conectados pero desmontados**, y el disco de **Hyper Backup** desenchufado. Los
   `.hbk` se abren con Hyper Backup Explorer en un PC, sin NAS.
4. **Snapshot Replication a un segundo Synology.** Si existe, son snapshots inmutables: el problema se
   acabó para esa carpeta.
5. **Papelera por carpeta compartida**: `/volume1/@recycle/<carpeta>/`. Lo borrado y no purgado sigue ahí.
6. **Historial de versiones de Synology Drive**: `@synologydrive` en el NAS, y la **caché del cliente
   Drive en el PC** (carpeta de sincronización local).
7. **Cloud Sync / C2 Backup / Active Backup**: versiones en el proveedor o en C2, aunque el destino esté
   desconectado ahora.
8. **Los PC cliente**: descargas de los shares, "Archivos sin conexión" de Windows, copias locales,
   papelera, Puntos de restauración.
9. **Móviles, correo y mensajería**: las fotos suelen estar en el teléfono; lo importante, adjunto en
   enviados o en chats.
10. **Otros equipos** de la casa u oficina con sincronización o copia parcial.

Con que una de estas cubra lo irremplazable, no se paga.

## B. Snapshots

Verdad de base, no la interfaz: `btrfs subvolume list /volume1`. Sirve solo lo anterior al inicio del
cifrado. Restaurar a **carpeta nueva**, nunca encima de los cifrados. Si el snapshot es inmutable, mejor.

## C. Archivos que el cifrador no tocó

El cifrador salta directorios de sistema, ejecutables, scripts y archivos ya cifrados; y las extensiones
fuera de su lista prioritaria se cifran solo en parte. Muchos `.zip`, `.rar`, `.7z`, `.gz`, `.mp4`, `.iso`
pueden estar íntegros. Contarlos antes de dar nada por perdido:

```bash
sudo find /volume1 -type f ! -name '*.L0CK3D' -printf '%p\n' \
  | awk -F/ '{print $NF}' | awk -F. 'NF>1{print tolower($NF)}' \
  | sort | uniq -c | sort -rn | head -40
```

Tres trampas de ese comando, que es fácil correr mal:

- **`-xdev` no sirve aquí**: cada carpeta compartida de Synology es un subvolumen Btrfs con su propio
  `st_dev`, así que `-xdev` no entra en ninguna y el resultado sale vacío.
- `sed 's/.*\.//'` destroza las rutas sin punto en el nombre; de ahí el `awk` sobre el nombre base.
- El `find` va a descender también por `@recycle`, `@synologydrive`, `@sharesnap` y el pool de Active
  Backup. Conviene correr uno **por carpeta compartida**, no sobre `/volume1` entero, para saber de qué
  share sale cada cosa y no tardar horas.

**Ojo con `btrfs restore`:** restaura el árbol **actual**, es decir los archivos cifrados. Para sacar
datos viejos hay que apuntar a una **raíz anterior** (`btrfs-find-root -a`, y luego `btrfs restore -r
<id>`), y hacerlo contra un montaje de solo lectura o una imagen, no contra el volumen vivo.

## Anatomía del daño: qué proporción se puede rescatar

Medido sobre un inventario real de **731.473 archivos cifrados** (leído del footer de cada uno):

| Modo | Archivos | % de archivos | Bytes | Qué se conserva |
|---|---|---|---|---|
| `0x24` | 549.261 | 75,1 % | 91 GB | Nada: cifrado completo (archivos pequeños) |
| `0x26` | 167.920 | 23,0 % | 365 GB | Todo menos el primer MiB |
| `0x25` | 14.292 | 2,0 % | **1.971 GB** | Todo menos 3-5 tramos (~12 %) |

La lección del reparto: **por archivos, tres cuartas partes están perdidas; por bytes, el 96 % está en los
modos parciales**. El esfuerzo va donde está el tamaño, no donde está el conteo. Y entre los archivos
parciales más grandes de un NAS de oficina siempre aparecen los buzones `.pst` (33-48 GB en `0x25`), que
son justo lo que más duele perder.

## D. Archivos grandes parcialmente cifrados

Es el margen técnico real. `inspect_footer.py` dice qué rangos se cifraron y el tamaño original. Sobre
una **copia**, se recorta el tramo perdido y se rearma el resto: audio y vídeo aguantan bien un hueco;
los contenedores con índice al final (ZIP, OOXML) pierden estructura y hay que reconstruirlos por
entradas. Ojo: ~187 extensiones "prioritarias" se cifran enteras aunque el archivo sea grande.

## E. Tallado de la imagen

Solo si A–D fallan y el volumen es Btrfs.

- Imagen con `ddrescue` a un disco **del tamaño del dispositivo completo, no de lo usado**: lo que se
  busca vive justamente en el espacio libre, y "lo usado" lo deja fuera.
- Del volumen a la imagen, nunca al revés, y nunca sobre el volumen vivo.
- Tallado dirigido con `c3r_carve.py` (acepta un candidato solo si su longitud coincide exacta con el
  `orig` del footer) y **PhotoRec como complemento**: PhotoRec devuelve fragmentos sin nombre ni ruta;
  el emparejamiento por tamaño es lo que les devuelve identidad.

## F. Lo que no se hace

- "Decryptors L0CK3D" de webs sueltas: reempaquetados o estafa.
- Servicios que piden acceso remoto y escriben en el volumen.
- Pagar antes de haber agotado A y B.
- Ejecutar cualquier cosa que venga del atacante fuera de un entorno aislado.
