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

## Archivos en disco

- Extensión `.L0CK3D` (con cero) en cada archivo cifrado.
- `read-me3.txt` («C3RB3R INSTRUCTIONS») en cada carpeta.
- Footer de **588 bytes** al final de cada archivo cifrado: `marcador[568:572]` · `modo[572]` ·
  `pct[573]` · `cripto[574]` · `tamaño original[-8:]`.

## Lo que NO es un IOC compartible

- **El marcador de sesión** (`footer[568:572]`) cambia en cada ataque y sirve para identificar a la
  víctima. No se publica.
- **El token de víctima** de la nota (260 hex) y la URL `.onion` completa: con eso se entra al portal
  del atacante como la víctima. No se comparten, ni con quien ofrezca "rescate".
- El hash de un archivo cifrado concreto: no identifica el malware, identifica a quien lo tiene.

## Superficie expuesta

Shadowserver rastrea **más de 380.000 NAS Synology** con la interfaz publicada en internet. La campaña
explota una vulnerabilidad parcheada en **diciembre de 2024** (SA-24:20: CVE-2024-10441 ejecución de
código, CVE-2024-50629 lectura de archivos, CVE-2024-10445 escritura). Versiones corregidas:

| DSM | Versión mínima |
|---|---|
| 7.2.2 | 7.2.2-72806-1 |
| 7.2.1 | 7.2.1-69057-6 |
| 7.2 | 7.2-64570-4 |
| 7.1 | 7.1.1-42962-7 |
| 6.2 | 6.2.4-25556-8 |

Aviso oficial: Synology, 2-nov-2026 · difundido por BleepingComputer con respuesta de la empresa.
