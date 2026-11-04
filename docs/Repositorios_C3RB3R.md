# Repositorios de C3RB3R / .L0CK3D usados y evaluados

Actualizado: 1-nov-2026. Caso de referencia: un cliente (NAS Synology, ataque 28-oct-2026 20:32, marcador `<omitido>`).

## Los que usamos directamente

| Repo | Qué aporta | Cómo lo usamos |
|---|---|---|
| https://github.com/soimy/c3rb3r-rescue | Evidencia forense, recuperación de la llave desde la memoria del proceso vivo, descifrado sobre copias. Incluye `decrypt_copy.py` (el motor) e `inspect_footer.py` (lee modo, marcador y rangos cifrados). | Clonado. `inspect_footer.py` sobre todos nuestros archivos; `decrypt_copy.py` probado con su suite de tests (5 en verde). La ruta de memoria no aplica: el NAS ya se reinició. |
| https://github.com/hongjiahao371-pixel/L0CK3D-Recovery | Rescate probabilístico sin llave desde un archivo suelto (audio, video, JPG, PDF). | Clonado y corrido sobre los 202 archivos: 200 sin nada, 2 parciales (una foto que ya teníamos y una imagen incrustada). |

## Los que aplican si hay acceso a los discos (no ejecutados aún)

| Repo | Qué aporta | Requisito |
|---|---|---|
| https://github.com/crt106/c3rb3r-btrfs-recovery | **La vía más prometedora para este caso.** Recupera los datos originales desde los bloques viejos de Btrfs, sin llave, verificado bloque a bloque con el CRC de Btrfs. Caso real: 35.445 archivos / 230 GB. | Correr por SSH dentro del NAS, en solo lectura. Empezar por `preflight` y `survey`. |
| https://github.com/miyanagaaoi/L0CK3D-recover | Caso completo con números: 1.295.238 archivos cifrados → 73.809 recuperados = 9,42 % de archivos / 21,37 % de los bytes. Trae el toolkit (delta, carving de espacio libre, verificación por csum). | Lee el bloque del disco (`/dev/mapper/cachedev_0`), root en el NAS. |
| https://github.com/kmyqchy/c3rb3r-small-config-lastresort | Carving de configuraciones de texto pequeñas (`.env`, `docker-compose`, llaves SSH) desde el disco crudo. | Disco desmontado y zona sin sobrescribir. Su autor midió 60 archivos `0x24` y recuperó 0. |

## Los que dependen de la memoria del proceso (no aplican: NAS reiniciado)

| Repo | Qué aporta |
|---|---|
| https://github.com/Benjamin-zlt/c3rb3r-baremetal-rescue | Segundo caso de éxito independiente: 84.500 archivos / 940 GB con una sola llave de sesión, sobre físico. Mismo binario que el nuestro (`802ac85d…903d`) y mismo puntero de la llave (`0x5427f8`). Documenta el layout del footer: 588 B, marcador en 568, modo en 572, cripto en 574 (`0x20` real / `0x21` señuelo), tamaño original en 580. |
| https://github.com/penv13/c3rb3r-inplace-rescue | Descifrado en el mismo disco (sin espacio extra). Necesita el volcado de memoria. Trae binarios precompilados: compilar desde el fuente. |
| https://github.com/code-gyu/c3rb3r-dsm-recovery-journal | Bitácora real: 63.667 archivos recuperados (98 GB) con la memoria congelada. Detalla la verificación por lotes y los huecos de 12.288 B en la captura. |
| https://github.com/hitushen/synology-ransomware-recovery | Skill que unifica todas las rutas (memoria, Btrfs, copias, Telnet) con su tabla de decisión. Útil como manual. |

## Prevención y auditoría

| Repo | Qué aporta |
|---|---|
| https://github.com/akari-sora/synology-nas-cli | CLI + servidor MCP para auditar DSM 7 contra SA-26:13/SA-26:14 y arreglar: QuickConnect, puertos, firewall, AutoBlock, SMB, cuenta admin, snapshots inmutables. Trae `contain` (SIGSTOP al cifrador) y `alert-deploy` (chequeo cada 10 min). |
| https://github.com/SHIFox8/synology-dsm-vuln-scanner | Escáner de solo lectura de las fallas usadas en el ataque. |

## Casos documentados (solo lectura, para el informe)

- https://github.com/lllong1377/c3rb3r-never-rebooted-still-no-key — nunca reiniciado y aun así sin llave (149 días de uptime, proceso muerto 30 h antes).
- https://github.com/Ericality/c3rb3r-dsm-case-20261028 — segundo caso independiente; el cifrador murió por OOM del kernel.
- https://github.com/Creeper-OF/synology-c3rb3r-nas-case-study — 885.014 objetos Btrfs, parte irrecuperable.
- https://github.com/weilizhang0813-eng/C3RB3R — investigación del formato; sin descifrador funcional.
- https://github.com/sunkangbo121-ship-it/c3rb3r-btrfs-extent-rescue — rescate por extents de Btrfs.

## Herramientas propias que escribimos durante el caso

- `~/.clawksis/skills/security/c3rb3r-locked-rescue/scripts/` — `examen_bytes.py` (triage por entropía y firmas), `desarmar_footer.py`, `rescate_pdf.py` (PDF sin llave), `carve_zip.py` y `reconstruir_xlsx.py` (Office por entradas del ZIP).
- `~/.clawksis/scripts/rescatar_zip_header.py` — rearma un `.xlsx`/`.docx`/`.pptx` desde el directorio central cuando el modo es `0x26`.
- `~/.clawksis/scripts/c3rb3r_vigia.py` — vigía diario de novedades (GitHub, Reddit, BleepingComputer, No More Ransom, Emsisoft).

## Estado de la víctima (1-nov)

- 202 archivos `.L0CK3D`: **197 en modo `0x24`** (cifrado completo, sin rescate posible), **3 en `0x26`**, **2 en `0x25`**. Todos con cifrado real (`0x20`), un solo marcador de sesión, sin modo señuelo.
- Rescatado: 10 de 13 páginas del PDF de la notificación a la ANLA + 6 fotos; el libro macro de tarifas; una página de cada gráfica manual; imágenes sueltas de un Excel. **Ningún documento pequeño.**
- Pendiente y decisivo: revisar `/volume1/@sharesnap/` y correr `preflight`/`survey` de crt106 con el NAS en solo lectura y sin internet.
