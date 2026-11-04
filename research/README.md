# Investigación — C3RB3R / `.L0CK3D`

Aquí se guarda **todo lo que vamos averiguando** sobre esta familia de ransomware: repositorios,
técnicas, casos publicados, fuentes y estafas. La idea es simple: cuando buscamos algo sobre
C3RB3R/Cerber, el resultado se anota acá en el momento, para no volver a investigar dos veces lo
mismo y para que otro pueda arrancar desde donde quedamos.

Se alimenta **a mano, al investigar**. No hay nada automático escribiendo en esta carpeta.

## Cómo se añade un hallazgo

1. **Buscar primero acá** (`hallazgos.csv`, `repositorios.md`, `fuentes.md`): si ya está, se cita y
   se actualiza el veredicto en vez de repetir la búsqueda.
2. **Una fila nueva** en `hallazgos.csv` con: fecha, tema, hallazgo en una línea, fuente y veredicto.
3. **Si es un repositorio o una fuente nueva**, se añade además su ficha en `repositorios.md` o
   `fuentes.md`, con qué aporta y si aplica al caso.
4. Commit con el tema: `research: <tema> — <hallazgo en 6 palabras>`.

## Veredictos que se usan

| Veredicto | Significa |
|---|---|
| `confirmado` | Lo probamos nosotros y funcionó (o falló) de forma reproducible |
| `referencia` | Viene de un caso publicado, con números, pero no lo hemos corrido |
| `teoria` | Plausible, sin evidencia de campo todavía |
| `descartado` | Se probó y no sirve (se deja escrito para no repetirlo) |
| `estafa` | Ofrece "rescate" y no lo es |

## Qué NO va aquí

Datos de la víctima: nombres, rutas, inventarios, documentos, fotos, marcadores de sesión del
ataque, tokens de víctima ni el enlace `.onion` completo. Los IOCs del malware (hash de la muestra,
IP del C2) sí van: son públicos y útiles.

## Archivos

- `hallazgos.csv` — registro cronológico, una línea por hallazgo.
- `repositorios.md` — catálogo de repositorios evaluados, con qué aportan y qué requisito piden.
- `fuentes.md` — foros, hilos, blogs, portales de descifradores y el criterio para detectar estafas.
- `../docs/references/` — las técnicas en detalle (formato, Btrfs, tallado, transporte, fotos).
