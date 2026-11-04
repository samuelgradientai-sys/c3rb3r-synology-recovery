# Fuentes y veredictos

Dónde se busca, qué responde de verdad y qué es humo. Actualizado: 3-nov-2026.

## Descifradores: la respuesta corta

**No existe descifrador público para C3RB3R.** Comprobado fuente por fuente:

| Fuente | Qué dice |
|---|---|
| No More Ransom | Solo tiene **CERBER V1** (2016): otra familia, con otra criptografía. |
| Emsisoft, Avast, Dr.Web, Kaspersky, ID Ransomware | No lo tienen. Dr.Web solo lo clasifica (`Trojan.Encoder.38200`). |
| ransomware.live | Ni registra el grupo. |
| Portales `.onion` del atacante | Venden el rescate (~0,037 BTC, se duplica a los 5 días). No es un descifrador. |

Trampa frecuente: que exista una página de herramienta **no** significa descifrador gratis. La de
DeadBolt en Emsisoft, por ejemplo, exige la llave que dan los atacantes después de pagar.

## Foros y prensa

| Fuente | Cómo se lee |
|---|---|
| Reddit r/synology | `www.reddit.com/r/synology/new.rss` funciona con User-Agent propio; el JSON da 403 y ráfagas dan 429. Dos lecturas con 20 s entre ellas. |
| BleepingComputer (hilos 780618 y 819759) | Por HTTP; los ids van con comilla simple (`id='post_id_N'`). Si el fetch directo falla, `https://r.jina.ai/<url>` devuelve el markdown completo. |
| nashub.vn, l0ck3d.com | Bitácoras de casos en vivo; útiles para cifras de recuperación. |
| linux.do, v2ex | 403 a clientes automáticos. Discord no es indexable. |
| Guías tipo `howtoremove.guide` | Publicidad de SpyHunter. No instalar nada de ahí. |

## Estafas: la regla que no falla

**Si la solución llega por Telegram, WhatsApp, Instagram o Gmail y no por un enlace público con hash,
es estafa.** Lo primero que piden es la nota de rescate, porque con el token de víctima entran al
portal del atacante y revenden el rescate.

Señales concretas vistas en este caso:
- Videos "SOLVED || ransomware removal and decryption" que remiten a un chat privado.
- Canales que piden adjuntar la nota o un archivo de muestra "para comprobar compatibilidad".
- "Descifrado gratis de 1 archivo": aplica justo a los archivos pequeños, que son los irrecuperables.
  Es cebo comercial, no una concesión.

**Nunca** se comparte la nota, el token de víctima ni el enlace `.onion` completo. Un GET a ese portal
puede quedar registrado: leer no significa ser invisible.

## Búsquedas que rinden

- GitHub: `https://api.github.com/search/repositories?q=c3rb3r&sort=updated` (sin auth, con pausas) y,
  mejor aún, `search/issues?q=L0CK3D created:>FECHA` — los issues de los repos activos avisan antes
  que los repos nuevos.
- Chino: `群晖 L0CK3D 勒索 恢复 工具 github`, `C3RB3R 群晖 勒索 解密器 私钥`. Fuentes: 看雪 (bbs.kanxue.com),
  360 (bbs.360.cn), v2ex.
- Verificar que la página cargó de verdad antes de concluir "no hay nada": un captcha devuelve 0
  resultados y parece una búsqueda vacía.
