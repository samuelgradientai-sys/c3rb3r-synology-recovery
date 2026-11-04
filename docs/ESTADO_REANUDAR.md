# Rescate de un cliente — estado al pausar (3-nov-2026 ~15:20)

Acceso: `ssh -i ~/rescate_cliente/acceso/nas_key root@<IP_NAS>` (DS923+, DSM 7.4.1-90080U1,
cortafuegos: 22 solo desde <IP_OFICINA>). Tarea `llave` en Programador de tareas DSM (borrarla al final).
NAS reiniciado el 3-nov ~10:18 → vía memoria muerta. 0 snapshots. Extents viejos (crt106): 0/902.

## Procesos (todos DETENIDOS, reanudables, no repiten trabajo)
1. Share parcial (PRIORIDAD del responsable): `cd ~/rescate_cliente/kit_nas && nohup python3 traer_share.py &`
   - lista: salida/dt_lista.json (13.631 archivos 0x25/0x26, 62 GB); hecho: 68/158 lotes (6.278 archivos)
   - crudo (zonas en cero): ~/rescate_cliente/share_crudo/ ; progreso en _progreso.log / _hechos.txt
   - procesar al Escritorio: `python3 rescatar_share.py` (re-ejecutable; en bucle mientras corre la descarga)
     usa reparar_pdf.py (venv ~/rescate_cliente/.venv con pymupdf, openpyxl) y reparar_office.py
   - salida: ~/Escritorio/NAS-3PL/Share/ (`[PARCIAL]`, `[IMÁGENES]/`, `[DAÑADO]`), índice
     NAS-3PL/Share/_SIN_UBICAR/Share_RESCATE_PARCIAL.csv
2. Pool de Active Backup (1.071 GB, 0x25 = 88 % en claro): `python3 traer_pool.py --lote 300`
   - va en lote 28 de ~105 → ~/Escritorio/RESCATE_CLIENTE_BACKUP/ ; luego `python3 organizar.py`
   - organizar.py cruza por TAMAÑO EXACTO con salida/inventario_rutas.tsv.gz (731.473 .L0CK3D) →
     ~/Escritorio/NAS-3PL/<share>/<ruta original> ; sin ruta → ~/Escritorio/NAS-3PL_SIN_UBICAR/ (+INDICE.csv)

## Share parcial: TERMINADO 3-nov 17:04 (13.630 procesados, 7.861 con algo; PDF 6.270/7.961,
62.875 páginas; 107.090 imágenes; jpg 0/3.395 → idea: trasplante de cabecera JPEG de foto sana misma cámara)

## Repos pendientes (3-nov ~18:00) — clonados en ~/rescate_cliente/repos/
- Carving espacio libre (miyanagaaoi fase 5 = c3r_carve.py de crt106): targets listos en
  salida/carve_targets.tsv (355.751 archivos 0x24 pdf/zip/ole/jpg/png/bmp; 97.161 pares tipo/tamaño; Share 76.832).
  Siguiente: `python3 mkjob.py --tool carve -- freemap --mount /volume1 | ssh ... "sh -s"` (luego volume2), después scan.
- sunkangbo121 = mismo método bookend que crt106 → no aplica con NoCOW (confirmar lsattr -d de cada share).
- kmyqchy: solo configs de texto, no aplica a documentos.
- SHIFox8 / akari-sora: auditoría al final (solo lectura, sin aplicar cambios).
- 18:00: NAS DEJÓ DE RESPONDER (22/5001/5000/445 y ping muertos; nuestra IP sigue <IP_OFICINA>).

## FOTOS Share (reanudado 3-nov 19:20) — EN CURSO
- 3.412 fotos ya están en crudo (11,7 GB). Rescate por trasplante de cabecera JPEG
  (`repos/jpeg_recovery` = jpegmedic, DRCRecoveryData): cabecera de foto sana del mismo
  sensor (4096 px, 4:2:0) con altura holgada; la altura real se recalcula con las filas que
  sobrevivieron. Las fotos salen completas y legibles.
- Modo 26 (3.329): cero en los primeros 1 MB → prefijo fijo 1.048.576.
- Modo 25 (83): varios bloques en cero (cada ~3,4 MB) → se intenta con el fin del primer bloque;
  si falla queda marcado en el índice.
- Script: `rescatar_fotos.py` (7 procesos, re-ejecutable, salta lo hecho, índice CSV).
  Salida espejo: ~/Escritorio/NAS-3PL/Share/<ruta original>.jpg
  Índice: NAS-3PL/Share/_SIN_UBICAR/FOTOS_RECUPERADAS.csv · log: _fotos_progreso.log
- Ritmo medido: ~25 fotos/110 s con 7 procesos → ~4 h para el lote completo.

## Pendientes / ideas
- 31 xlsx [PARCIAL] aún no abren; PDF de Share apenas empezaban.
- .pst gigantes (gerencia/contabilidad/RRHH, 33–51 GB, 0x25) → ~88 % en claro: intentar extraer correos.
- OneDrive-DT (41.633 archivos de Share): preguntar si el OneDrive original existe (restaurar en la nube).
- Prueba gratis de los atacantes: el responsable lo evalúa; candidato = backup_db.sqlite de 1,6–1,7 MB (catálogo).
  Juntar archivos NO sirve (llave por archivo en el footer). No compartir ID/onion por chat.
- No escribir en /volume1, no actualizar DSM sin avisar, al final: borrar llave + tarea `llave`, apagar SSH.
