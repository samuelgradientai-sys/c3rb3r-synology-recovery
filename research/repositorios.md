# Repositorios de C3RB3R / `.L0CK3D` evaluados

Cada entrada dice **qué aporta, qué requisito pide y qué pasó cuando lo probamos**. Orden por utilidad
real, no por popularidad. Última revisión: 3-nov-2026.

## Corridos y útiles

| Repositorio | Qué aporta | Qué pasó al usarlo |
|---|---|---|
| [soimy/c3rb3r-rescue](https://github.com/soimy/c3rb3r-rescue) | Evidencia forense, extracción de la llave desde la memoria del proceso vivo, descifrado sobre copias. Trae `decrypt_copy.py` (motor) e `inspect_footer.py` (modo, marcador, rangos cifrados). | Clonado. `inspect_footer.py` corrió sobre todas las muestras; `decrypt_copy.py` pasó sus tests. La ruta de memoria no aplicó porque el equipo ya se había reiniciado. |
| [hongjiahao371-pixel/L0CK3D-Recovery](https://github.com/hongjiahao371-pixel/L0CK3D-Recovery) | Rescate probabilístico sin llave sobre un archivo suelto (audio, video, JPG, PDF). Solo stdlib, no hace red. | Sobre una muestra de 202 archivos: 200 sin nada, 2 parciales. Sirve para archivos grandes, no para documentos pequeños. |
| [DRCRecoveryData/JPEG_Recovery](https://github.com/DRCRecoveryData/JPEG_Recovery) | `jpegmedic`: reconstruye un JPEG cuando la cabecera (SOI/DQT/SOF/DHT/SOS) se perdió, usando otra foto del mismo sensor. | **El hallazgo más rentable del caso**: 10/10 legibles en la prueba y el lote completo del share salió igual. Sin esto, las fotos parecían perdidas. |

## Aplican con acceso al disco (requisito: root y solo lectura)

| Repositorio | Qué aporta | Requisito / advertencia |
|---|---|---|
| [crt106/c3rb3r-btrfs-recovery](https://github.com/crt106/c3rb3r-btrfs-recovery) | Recupera los originales desde bloques viejos de Btrfs sin llave, verificado con el CRC de Btrfs. Caso: 35.445 archivos / 230 GB. | Corre por SSH dentro del NAS. Empezar por `preflight` + `survey`. Si hay NoCOW sin snapshots, devuelve 0 candidatos. |
| [miyanagaaoi/L0CK3D-recover](https://github.com/miyanagaaoi/L0CK3D-recover) | Caso completo con números: 1.295.238 archivos → 73.809 recuperados (9,42% de archivos / 21,37% de bytes). Toolkit de delta, tallado y verificación por csum. | Lee el bloque del disco (`/dev/mapper/cachedev_0`). Es la referencia honesta de expectativas. |
| [kmyqchy/c3rb3r-small-config-lastresort](https://github.com/kmyqchy/c3rb3r-small-config-lastresort) | Tallado de configuraciones de texto pequeñas (`.env`, `docker-compose`, llaves SSH) desde disco crudo. | Su autor midió 60 archivos `0x24`: recuperó 0. No aplica a documentos. |
| [hjs785053766/c3rb3r-btrfs-recovery](https://github.com/hjs785053766/c3rb3r-btrfs-recovery) | Cinco rutas en un solo kit (extents por FIEMAP, bookend de raíz vieja, reensamblado 0x25, tallado, repo de Synology Drive). Caso: 205.973 archivos / 1,03 TB, 65,4% recuperado. | Trae `AGENT_RUNBOOK.md`. Los `local_drivers/` tienen rutas de Windows hardcodeadas: hay que editarlas. |
| [wangyilindahaoren-glitch/c3rb3r-nas-recovery-lab](https://github.com/wangyilindahaoren-glitch/c3rb3r-nas-recovery-lab) | Fork ampliado de crt106 (81 scripts): extents, texto claro, copias en el volumen, tallado con foremost, ext4/jbd2. | Propone instalar entware en el NAS: **no hacerlo**, es la evidencia. Usar el `c3r_carve.py` original. |

## Dependen de la memoria del proceso (solo si el cifrador sigue vivo)

| Repositorio | Qué aporta |
|---|---|
| [Benjamin-zlt/c3rb3r-baremetal-rescue](https://github.com/Benjamin-zlt/c3rb3r-baremetal-rescue) | Caso independiente: 84.500 archivos / 940 GB con una sola llave de sesión. Documenta el layout del footer y el puntero de la llave. |
| [penv13/c3rb3r-inplace-rescue](https://github.com/penv13/c3rb3r-inplace-rescue) | Descifrado en el mismo disco, sin espacio extra. Necesita volcado de memoria; sus binarios precompilados no se usan: compilar del fuente. |
| [code-gyu/c3rb3r-dsm-recovery-journal](https://github.com/code-gyu/c3rb3r-dsm-recovery-journal) | Bitácora real: 63.667 archivos (98 GB) con la memoria congelada; detalla la verificación por lotes y los huecos de la captura. |
| [hitushen/synology-ransomware-recovery](https://github.com/hitushen/synology-ransomware-recovery) | Skill que unifica todas las rutas con su tabla de decisión. Sirve como manual, no como herramienta. |

## Prevención y auditoría

| Repositorio | Qué aporta |
|---|---|
| [akari-sora/synology-nas-cli](https://github.com/akari-sora/synology-nas-cli) | CLI + servidor MCP para auditar DSM 7 (QuickConnect, puertos, firewall, AutoBlock, SMB, admin, snapshots inmutables) y `contain` (SIGSTOP al cifrador). Auditoría al final, solo lectura. |
| [SHIFox8/synology-dsm-vuln-scanner](https://github.com/SHIFox8/synology-dsm-vuln-scanner) | Escáner de solo lectura de las fallas usadas en el ataque. |

## Casos documentados (para comparar cifras, no para correr)

- [lllong1377/c3rb3r-never-rebooted-still-no-key](https://github.com/lllong1377/c3rb3r-never-rebooted-still-no-key) — nunca se reinició y aun así no había llave: el proceso llevaba 30 h muerto.
- [Ericality/c3rb3r-dsm-case-20261028](https://github.com/Ericality/c3rb3r-dsm-case-20261028) — segundo caso independiente; el cifrador murió por OOM del kernel.
- [Creeper-OF/synology-c3rb3r-nas-case-study](https://github.com/Creeper-OF/synology-c3rb3r-nas-case-study) — 885.014 objetos Btrfs, parte irrecuperable.
- [weilizhang0813-eng/C3RB3R](https://github.com/weilizhang0813-eng/C3RB3R) — investigación del formato; sin descifrador funcional.
- [sunkangbo121-ship-it/c3rb3r-btrfs-extent-rescue](https://github.com/sunkangbo121-ship-it/c3rb3r-btrfs-extent-rescue) — extents de Btrfs; midió 117 de 6.725 `0x24` recuperados.

## Para trabajar offline con los discos (no específico de C3RB3R)

| Repositorio | Qué aporta | Estado |
|---|---|---|
| [007revad/Synology_Recover_Data](https://github.com/007revad/Synology_Recover_Data) | Montar los discos del Synology en un PC (Linux) y leer el volumen sin el NAS vivo: MD-RAID + LVM + Btrfs. 96★, MIT. | **El complemento natural de la imagen forense**: permite montar en solo lectura y trabajar sin depender del equipo encendido. |

## Nuevos (4-nov-2026), sin probar todavía

| Repositorio | Qué aporta | Estado |
|---|---|---|
| [ychcom/L0CK3D-recovery](https://github.com/ychcom/L0CK3D-recovery) | Caso completo en VM con pRDM: metodología, herramientas y —lo más útil— la lista de **8 vías descartadas con el motivo**. Su caso: 156.127 cifrados, 8.326 recuperados (47 GB), 1.709 completos. | Documentación, no kit: se lee, no se corre. |
| [sgInnora/innora-cve-research](https://github.com/sgInnora/innora-cve-research) | Causa raíz de **CVE-2024-10441** (`synoplugind`, inyección de variables de entorno → RCE root, CWE-116), con entorno QEMU reproducible y cadena verificada. Es el vector de entrada de la campaña. | Referencia para el informe de entrada; no interviene en el rescate. |
| [MRdark-ops/scanner-syno](https://github.com/MRdark-ops/scanner-syno) | Escáner **de solo lectura** que detecta CVE-2024-10441 y CVE-2026-13684/13639 sin ejecutar exploits; incluye BeeStation OS. | Candidato para verificar el parque del cliente. Revisar el código antes de correrlo. |
| [SecurityRonin/btrfs-forensic](https://github.com/SecurityRonin/btrfs-forensic) | Lector de btrfs en Rust (Apache-2.0): chunk tree, fs-tree, raíces viejas, bloques con csum roto, inodos huérfanos y archivos borrados carvables de una generación anterior. | **El más interesante sin probar**: sería una segunda opinión al `c3r_btrfs.py` en Python. |

## Límites verificados en el código de crt106 (4-nov-2026)

Leído en `c3r_btrfs.py`, no en su README:

- La fórmula de franjas del `0x25` solo se aplica si el parámetro de porcentaje es **10**:
  `if mode == 0x25 and pct == 0x0a`. Un `0x25` con otro `pct` **no se modela** y hay que derivar los
  rangos a mano.
- Su `parse_footer` es más laxo que el de soimy: se queda con modo, marcador y tamaño original, y no
  valida el byte de cifrado real/señuelo (`0x20`/`0x21`).
- No cubre perfiles rayados (striped), extents comprimidos ni inline.

En el pool de Active Backup medido aquí, **todos los `0x25` son `pct=10`**, así que esa limitación no
aplica a ese conjunto; sí puede aplicar a shares donde el cifrador usó otro porcentaje.

## Estado de los repos clave (4-nov-2026)

- **crt106/c3rb3r-btrfs-recovery** — el PR #1 (`herakles-cow`) añade `scripts/c3r_carve.py` con 237 líneas
  de tests y sigue **sin fusionar**. El carving de espacio libre se usa desde el PR o desde la rama, no
  desde `main`. Es el repo que más se está moviendo.
- **akari-sora/synology-nas-cli** — trae `docs/INCIDENT-C3RB3R.md` (y versiones en chino) con la
  cronología del incidente: útil para el informe al cliente, no para el rescate.
- **soimy/c3rb3r-rescue** — los issues son la fuente viva: #22 (EXT4 sin ruta), #23 (caso del 65% con las
  cinco vías), #24 (memoria sin `capture.json`: leer los 48 B en `0x5427f8`), #10 (xattr de descarga como IOC).
- **hjs785053766/c3rb3r-btrfs-recovery** — publicado con 37 scripts y manual en chino; su quinta vía
  (repo de Synology Drive) rinde 34,4% en bloques de 500–1000 MB.

## Herramientas propias

- `scripts/` de este repo: `censo_modos.py`, `inventario_rutas.py`, `tallar_pool.py`, `reparar_pdf.py`, `reparar_office.py`, `rescatar_fotos.py` y el resto del kit.
- `docs/references/` — el detalle técnico de cada vía.
