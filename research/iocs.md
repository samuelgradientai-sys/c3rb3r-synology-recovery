# IOCs y datos de identificación

Solo indicadores **del malware**, no de las víctimas. Sirven para reconocer la campaña en un equipo y
para buscar en VirusTotal o en los repositorios de la comunidad.

## Binario del cifrador

- **SHA-256:** `802ac85d19dc6db2b1849bb3499877280544d04a0ae94d4c408b6c321669903d` (UPX)
- Nombres con los que aparece en DSM: `libgld`, `libgittcb`, `qnetd`, `init-rsysd`, `init-rsysd.lo`
- Arquitectura: x86-64 (ELF). El mismo binario se ha confirmado en al menos cuatro casos independientes.

### Direcciones útiles dentro del binario (mismas en varias víctimas)

| Qué | Dirección |
|---|---|
| Firma de entrada | `0x401f90` |
| Byte de modo | `0x53fc8c` (`0x20` = cifrado real) |
| Puntero a la maestra de 48 B | `0x5427f8` |

Que las direcciones coincidan no significa que la llave sirva: **la maestra es aleatoria por sesión**.

## Indicadores de red

| Indicador | Contexto |
|---|---|
| `208.87.128.140:4001` | Shell inverso reportado tras la intrusión (dossier de la comunidad). |
| `46.8.78.122`, ruta `/xdy5.6xc?x86_64` | Origen de descarga del cifrador, recuperado del atributo extendido `user.xdg.origin.url` en dos víctimas independientes. |

## Vector de entrada (documentado el 4-nov-2026)

- **CVE-2024-10441** — `synoplugind` del DSM: inyección de variables de entorno que rompe el
  *framing* del plugin y termina en **ejecución de código como root sin autenticación** (CWE-116,
  CVSS 9.8, en el catálogo KEV de CISA). Análisis de causa raíz con entorno reproducible publicado
  por Innora Security Research.
- Vectores secundarios: **CVE-2024-50629** (lectura arbitraria de archivos) y **CVE-2024-10445**
  (escritura arbitraria vía MITM del actualizador).
- La campaña usa una falla **parcheada en diciembre de 2024**. Un DSM sin actualizar desde entonces
  está expuesto aunque tenga QuickConnect en vez de puertos abiertos.

## Archivos en disco

- Extensión `.L0CK3D` (con cero) en cada archivo cifrado.
- `read-me3.txt` («C3RB3R INSTRUCTIONS») en cada carpeta.
- Footer de **588 bytes** al final de cada archivo cifrado. Medido en nuestras muestras, tiene cuatro
  zonas (no dos):

| Offset | Bytes | Contenido |
|---|---|---|
| 0 | 48 | Clave de archivo envuelta (sin un solo byte en cero) |
| 48 | 256 | Bloque RSA-2048 del atacante |
| 304 | 264 | Relleno en cero — reservado |
| 568 | 20 | `marcador[568:572]` · `modo[572]` · `pct[573]` · `cripto[574]` · `tamaño original[-8:]` |

  La zona de 520 B que algunos análisis describen como "área RSA" son 256 B útiles más 264 B de ceros;
  saberlo evita parsers que se comen el relleno como si fuera ciphertext.

## Lo que NO es un IOC compartible

- **El marcador de sesión** (`footer[568:572]`) cambia en cada ataque y sirve para identificar a la
  víctima. No se publica.
- **El token de víctima** de la nota (260 hex) y la URL `.onion` completa: con eso se entra al portal
  del atacante como la víctima. No se comparten, ni con quien ofrezca "rescate".
- El hash de un archivo cifrado concreto: no identifica el malware, identifica a quien lo tiene.

## Superficie expuesta y parches: son DOS avisos, y manda el más nuevo

Shadowserver rastrea **más de 380.000 NAS Synology** con la interfaz publicada en internet. Hay dos
avisos implicados y confundirlos deja equipos a la intemperie:

| Aviso | CVE | Builds corregidos |
|---|---|---|
| **SA-24:20** (dic-2024) — el vector de entrada original | CVE-2024-10441 (RCE root), CVE-2024-50629 (lectura), CVE-2024-10445 (escritura) | 7.2.2-72806-1 · 7.2.1-69057-6 · 7.2-64570-4 · 7.1.1-42962-7 · 6.2.4-25556-8 |
| **SA-26:13** (sep-2026) — el que fija la barra hoy | CVE-2026-13684 (SCGI, CWE-116, CVSS 9.8), CVE-2026-13639 (entropía del login, 9.8) y seis más | **7.4-90075 · 7.3.2-86009-4 · 7.2.2-72806-9 · 7.2.1-69057-12** |

Los CVE de SA-26:13 dicen "**before** 7.2.2-72806-9": un equipo en **72806-1** —el mínimo de SA-24:20—
sigue afectado. El build de referencia es el más alto de las dos tablas, no el de la primera.
7.1.1 y 6.2 no figuran en SA-26:13 porque esa rama no está soportada ahí, no porque estén a salvo.

Aviso de la campaña: Synology, 2-nov-2026 · difundido por BleepingComputer con respuesta de la empresa.
Tabla de SA-26:13 verificada en el aviso original (synology.com/en-global/security/advisory/Synology_SA_26_13).
