# Casos publicados con cifras

Para comparar expectativas, no para prometer. Cada fila es un caso real publicado por quien lo hizo.
Ordenados por resultado. Actualizado: 4-nov-2026.

| Caso | Entorno | Estado del cifrador | Método | Resultado |
|---|---|---|---|---|
| Benjamin-zlt | Físico, Btrfs | Vivo (congelado) | Volcado de memoria, una llave de sesión | 84.500 archivos / 940 GB, **100%** |
| code-gyu | DSM, Btrfs | Vivo (congelado) | Memoria, verificación por lotes | 63.667 archivos / 98 GB, **100%** |
| soimy #24 (DS420+, DSM 7.2.1) | Físico, Btrfs | Vivo 22 h, pausado | Memoria: 48 B en el puntero 0x5427f8 | **159/159** con SHA-256 exacto, 3 modos, 97 tipos |
| hjs785053766 | Btrfs 97% lleno | Muerto, sin llave | CoW viejo + bookend + 0x25 + carving + Drive | 205.973 archivos / 1,03 TB → **65,4%** (fotos 97,9%, video 99,4%, <1 MB ~55%) |
| sunkangbo121 | Volumen CoW | Muerto, sin llave | Extents + carving de espacio libre | 0x26 99,8% · 0x25 98,2% · **0x24 1,7%** (117 de 6.725) |
| miyanagaaoi | Volumen Btrfs | Muerto, sin llave | Delta, carving, verificación por csum | 1.295.238 archivos → 73.809 = **9,42% de archivos / 21,37% de bytes** |
| ychcom (VM + pRDM) | Btrfs sin snapshots | Muerto, sin llave | Inversión de CoW generación a generación | 156.127 cifrados → **8.326 archivos (47 GB)**, de ellos 1.709 completos (23 GB) |
| Creeper-OF | Btrfs, dos volúmenes, NoCOW | Muerto | Forense de disco y memoria | 885.014 objetos Btrfs; parte irrecuperable, sin llave |
| lllong1377 | Sin reiniciar en 149 días | Muerto 30 h antes | Memoria (tarde) | **0%**: el proceso ya no estaba |
| felixfungys (abierto) | **EXT4**, reiniciado, sin snapshots | Muerto | Imagen forense de 4 discos (en curso) | **Pendiente**: sin CoW no hay ruta conocida |

## Qué enseña la tabla

- **Si el proceso está vivo, el caso se gana** (100% verificable con SHA-256). Todo lo demás es rescate parcial.
- **Sin memoria y sin snapshots, el techo realista está entre 9% y 65%**, y depende de dos cosas que se
  miden en minutos: si el cifrador escribió en el sitio o dejó extents viejos (CoW), y si el espacio libre
  no se ha reutilizado.
- **EXT4 es el peor escenario**: no hay copy-on-write, así que no hay bloques viejos que leer. El único
  caso abierto con esa configuración sigue sin resultado.
- Los porcentajes altos se miden por **tipo de archivo** y excluyen miniaturas. Un "65%" global con
  fotos al 97,9% cuenta una historia distinta a un 65% parejo.

## Caso con rescate por memoria (oct-2026)

Una víctima de esta ola recuperó la clave **suspendiendo el proceso y volcando su memoria**, y descifró con
ella. Es la única vía documentada que no pasa por pagar, y exige llegar antes que el reinicio: si el equipo
ya se reinició, la clave se fue con la RAM.

## Víctima ya parcheada contra SA-26:13 (28-oct-2026)

El equipo de respuesta **Solar** atendió un NAS que ya corría **DSM 7.4.1-90080 Update 1** —es decir, por
encima de los builds de SA-26:13— y estaba cifrado igual. El punto de entrada de ese caso sigue sin
resolver; se barajan un fallo nuevo, un paquete de terceros o credenciales filtradas. Consecuencia
práctica: "estoy al día" no es un argumento para descartar compromiso, y el parcheo no sustituye a sacar
la administración de internet.

## Caso btrfs con 65,4 % de recuperación (2-nov-2026, publicado en issues de soimy)

Volumen btrfs al 97 % de ocupación, ~206.000 archivos cifrados (1,03 TB), tres directorios de usuario.
Rendimiento medido por tipo, sin contar miniaturas:

| Tipo | Recuperado |
|---|---|
| Fotos originales (1-128 MB) | **97,9 %** |
| Vídeo (1-128 MB) | **99,4 %** |
| Vídeo grande (>128 MB) | 80,8 % |
| Miniaturas (<1 MB) | ~55 % |
| **Total sin miniaturas** | **65,4 %** |

Rendimiento por ruta: extents CoW viejos **92-100 %**, bookend de raíz vieja 30-60 %, costura de segmentos
63-89 %, carving de espacio libre 48-55 %. La fórmula de costura se generaliza a cualquier porcentaje:
`ln = (N // 100) * PF[pct]`, `gap = (N - 3*ln) // 2` — resuelve la limitación de crt106, que solo modela
`pct = 10`.

Dos trampas que costaron tiempo: `ffmpeg -xerror` es demasiado estricto (2-22 % de falsos negativos; basta
que decodifique 3 s) y el NAS se trabaja con `O_NOATIME` pasando los scripts por tubería SSH, sin dejar
archivos en él.

## Censo completo de un DS420+ (3-nov-2026): la marca de sesión, confirmada

DSM 7.2.1 Update 5, Btrfs, mismo binario `802ac85d`. Censó **380.836 archivos** de un share: todos con
marcador `4418882c` —distinto del `ce35a593` de otro incidente— y modo cripto `0x20`, cero anomalías.
Reparto: `0x25` 208.591 · `0x24` 143.905 · `0x26` 28.340.

Con su propia clave, extraída de memoria: **29 de 29 archivos descifrados con SHA-256 idéntico al original**,
incluidos cuatro que la reconstrucción por extents solo había recuperado en parte. Confirma dos cosas: la
marca es por sesión (no por muestra) y el nonce duplicado sirve de filtro real, no de debilidad.
