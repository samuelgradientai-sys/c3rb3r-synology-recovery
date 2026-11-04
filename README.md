# Rescate C3RB3R — NAS Synology

Herramientas, método y bitácora del rescate de datos de un **NAS Synology DS923+** afectado por el
ransomware **C3RB3R** (extensión `.L0CK3D`). El trabajo se hizo **en solo lectura sobre el NAS**: no se
escribió nada en sus volúmenes y no se pagó rescate.

> **Versión pública y anonimizada de un caso real.** El nombre del cliente, sus rutas locales, el
> marcador de sesión del ataque y los títulos de sus documentos fueron sustituidos o eliminados. El
> repositorio no contiene datos del cliente: ni documentos, ni fotos, ni rutas, ni la llave SSH del NAS.
> Solo código, documentación técnica y cifras agregadas.

---

## Qué se pudo y qué no

| Situación | Resultado |
|---|---|
| Archivos con zona cifrada pequeña (cabecera) | **Recuperados casi completos** reconstruyendo la cabecera |
| Archivos con los primeros MB en cero (`0x26`) | Se recupera lo que sobrevivió al bloque en cero |
| Archivos 100 % cifrados (`0x24`) | **Imposible sin la llave del atacante**: se intenta tallado en espacio libre |
| PDF / Office / ZIP con cabecera dañada | Reparados a nivel de estructura (páginas, hojas, entradas) |
| Fotos JPG sin cabecera | **Recuperadas** por trasplante de cabecera de una foto sana del mismo sensor |

La regla que ordenó todo: **la llave es por archivo** (va en el pie de cada uno), así que juntar archivos
no sirve. Sin llave no hay descifrado mágico; lo que se rescata es lo que el cifrado no alcanzó a destruir.

## Método

1. **Evidencia y mapa.** Inventario de los `.L0CK3D`, censo de modos de daño por archivo
   (`censo_modos.py`), lectura de los extents Btrfs para ubicar en el disco físico el contenido de cada
   archivo (`scripts/c3r_btrfs.py`, `scripts/c3r_local.py`).
2. **Transporte sin internet en el NAS.** Un túnel SSH inverso (`tunel_nas.sh`) permitió ejecutar Python
   dentro del NAS desde el equipo de rescate, enviando código por *stdin* y recibiendo resultados por
   *stdout*: nada se instala en el NAS, nada se escribe en `/volume1`.
3. **Lectura por *bookends*.** Para cada archivo se leen los extremos que el cifrado no tocó y se unen;
   las zonas en cero se marcan explícitamente (`zonas.json`) para que la reparación sepa qué falta.
4. **Tallado en espacio libre.** Para lo que no tenía registro vivo se barrió el espacio libre del
   volumen buscando firmas de PDF, ZIP, OLE, JPG, PNG y BMP (`scripts/c3r_carve.py`, `mkjob.py`).
5. **Reparación por formato.** PDF por objetos y páginas (`reparar_pdf.py`, con PyMuPDF), Office/OOXML por
   partes y relaciones (`reparar_office.py`), ZIP por directorio central (`rescatar_zip_header.py`).
6. **Fotos.** `rescatar_fotos.py` toma la cabecera de una foto sana del mismo sensor y reconstruye el JPEG
   con la parte del *scan* que sobrevivió; la altura se recalcula con las filas presentes, así que la
   imagen sale completa y legible aunque falte el encabezado.

## Estructura

```
docs/                 informe del incidente, bitácora de estado y notas de investigación
docs/references/      formato .L0CK3D, transporte, tallado, compatibilidad, trampas
scripts/              kit del NAS (Python, solo lectura) + reparadores por formato
scripts/hjs/          driver original del método bookend (referencia)
scripts/taller/       reparador de cabeceras ZIP
scripts/rescatar_fotos.py   rescate masivo de fotos JPG (paralelo, reanudable)
results/              registros de corridas reales (sin datos del cliente)
```

## Uso

Los scripts que hablan con el NAS leen la conexión de variables de entorno:

```bash
export NAS_IP=192.168.1.50          # IP del NAS durante el rescate
export NAS_KEY=~/.ssh/nas_key       # llave SSH (nunca en este repo)
```

Ejemplos:

```bash
python3 scripts/traer_share.py                 # trae los archivos con zona cifrada a cero, por lotes
python3 scripts/rescatar_share.py              # los repara y los deja en el Escritorio
python3 scripts/traer_pool.py --lote 300          # pool de Active Backup
python3 scripts/organizar.py                      # ubica cada archivo en su ruta original por tamaño exacto
python3 scripts/rescatar_fotos.py                 # fotos JPG: cabecera trasplantada, 7 procesos
```

`traer_*` y `rescatar_*` son **reanudables**: guardan progreso y saltan lo ya hecho, así que se pueden
cortar y relanzar sin repetir trabajo.

## Cifras de la operación (3-nov-2026)

- Inventario: **731.473** archivos `.L0CK3D`; modos de daño censados archivo por archivo.
- **Share**: 13.630 archivos procesados, **7.861 con algo recuperado**; PDF **6.270 de 7.961**
  (62.875 páginas) y **107.090 imágenes** extraídas de documentos.
- **Fotos Share**: 3.412 JPG, recuperadas por trasplante de cabecera (~1.000/hora con 7 procesos).
- **Pool de Active Backup**: 1.071 GB, 28 de ~105 lotes; el 88 % de esos archivos (`0x25`) está en claro.
- **Espacio libre**: 355.751 objetivos de tallado listos (97.161 pares tipo/tamaño).

## Límites conocidos

- Sin la llave del atacante, los archivos 100 % cifrados no se recuperan; el tallado solo devuelve
  fragmentos que el sistema haya dejado en espacio libre.
- Los `.pst` gigantes (33–51 GB) quedaron pendientes de extracción de correos.
- 31 libros `.xlsx` rescatados parcialmente aún no abren.
- El NAS dejó de responder durante la operación (red/firewall); el rescate se reanuda al volver.

## Créditos

- `scripts/hjs/` — toolkit público del método *bookend* para C3RB3R sobre Btrfs (licencia MIT, incluida).
- Rescate de fotos — motor [jpegmedic / JPEG_Recovery de DRCRecoveryData](https://github.com/DRCRecoveryData/JPEG_Recovery)
  (reconstrucción de JPEG sin cabecera); `rescatar_fotos.py` lo orquesta en paralelo y lo hace reanudable.

## Ética y manejo

Nada de esto toca al atacante ni paga rescate. No se guardan binarios del ransomware ni direcciones de
contacto en este repositorio. La llave SSH, las credenciales y los datos del cliente viven **fuera** del
repo y se borran al terminar la operación.
