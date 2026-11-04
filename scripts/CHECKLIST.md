# Checklist — primer acceso al NAS de la víctima

Objetivo de la primera sesión: **saber si los datos se pueden recuperar y por cuál de las tres vías**, sin destruir ninguna prueba. Tiempo estimado: 20–40 min.

---

## Antes de tocar nada

- [ ] **Desconectar el NAS de internet** (cable de red al router). Se sigue administrando por la red local, pero sin salida.
- [ ] Anotar **quién entra, a qué hora y cómo** (SSH, Telnet o consola física).
- [ ] Confirmar **no** reiniciar, **no** actualizar DSM, **no** resetear.
- [ ] Copiar los scripts a `/tmp` (partición de sistema) o a un USB. **Nunca** dentro de `/volume1`.

> Por qué tanto cuidado: el método de carving recupera bytes que están en el espacio libre. Cada archivo que se escriba en ese volumen destruye candidatos para siempre.

---

## Paso 0 — Evidencia (5 min, solo lectura)

```
sh /tmp/paso0_evidencia.sh > /tmp/evidencia_cliente.txt 2>&1
```

Buscar en la salida:

| Sección | Qué se busca | Por qué importa |
|---|---|---|
| 2 | **espacio libre** en el volumen de los shares | el carving necesita hueco libre real |
| 3 | `/volume1/@sharesnap/` **con fechas anteriores al 28-oct 20:32** | si hay snapshots, los archivos pequeños vuelven completos |
| 4 | shares, cantidad de `.L0CK3D`, bytes | saber qué tan grande es el problema |
| 6 | `libgld` vivo | si sigue vivo, **no matarlo**: hay que volcar la memoria antes (otra vía, la mejor) |
| 7 | conexión a `208.87.128.140:4001` | confirma si sigue hablando con el atacante |
| 8 | tareas en `/etc/crontab` y `/etc/cron.d` | persistencia: hay que quitarla, pero **después** de rescatar |
| 10 | `python3 -V` | la herramienta pide Python 3.6+ |

**Decisión:** si en el paso 3 hay snapshots con fecha previa al ataque → **parar aquí**. Esa es la vía buena y hay que restaurar desde ahí, no desde el carving.

> **Truco confirmado por una víctima (DS1621+, 28-oct):** si `@sharesnap` te aparece vacío por SSH, no concluyas que no hay snapshots. En **File Station** activa *Configuración → "Make snapshot visible"* (hacer visible la carpeta de snapshots) en cada share y mira la carpeta **`#snapshot`**. Él recuperó 4 de 12 shares así **después de que el propio ransomware reseteara la configuración de DSM** ("Welcome Back! … DSM has been reset" / "Configuration lost"): los snapshots sobrevivieron al reset y a la reinstalación, pero la lista de Snapshot Replication mostraba "No data". Se copian los archivos con File Station, no con Clone/Restore.

---

## Paso 1 — Preflight (2 min)

```
cd /tmp/kit_nas/scripts
python3 c3r_btrfs.py preflight /volume1/<share>/<cualquier-archivo>.L0CK3D
```

Comprueba: Btrfs montado, acceso al árbol de extents, permisos, versión de Python y que el footer del `.L0CK3D` se lea bien. Si falla, no seguir: mandar la salida.

---

## Paso 2 — Survey (10–30 min, solo lectura)

```
python3 c3r_btrfs.py survey /volume1/<share1> /volume1/<share2> > /tmp/survey.jsonl.gz
```

Luego, en el computador (no en el NAS):

```
python3 c3r_local.py report survey.jsonl.gz --depth 4
```

Estados que importan:

- **`exact` / `needs_inference`** → los datos viejos siguen en el árbol de extents: se recuperan con `extract`.
- **`partial`** → parte sí, parte no (los documentos grandes, como nuestro Excel).
- **`no_candidate`** → cifrado entero, sin rastro en el árbol → **esta es la población del carving**.

---

## Paso 3 — Carving del espacio libre (solo si hace falta)

```
python3 c3r_carve.py freemap
```

Dice cuánto espacio libre hay por chunk. **Si el volumen está casi lleno, este método no sirve** y hay que decirlo sin adornos.

Generar la lista de objetivos, aquí en el computador:

```
python3 targets_desde_survey.py survey.jsonl.gz --detalle > targets.tsv
```

y lanzar el escaneo (lee **solo** el espacio libre, puede tardar horas en un HDD):

```
python3 c3r_carve.py scan --targets /tmp/targets.tsv > /tmp/cands.jsonl.gz
```

Cada candidato trae **MD5 y SHA-256**. No se declara recuperado nada sin comprobarlo contra el original, un checksum de la aplicación o la vecindad en disco (ver `references/free-space-carving.md`).

Extraer los elegidos:

```
printf '%s\t%s\t%s\n' <addr> <len> <nombre> > /tmp/picks.tsv
python3 c3r_carve.py extract --picks /tmp/picks.tsv > /tmp/elegidos.tar
```

---

## Lo que NO se hace (repetido a propósito)

- No borrar `.L0CK3D` ni la nota `read-me3.txt`.
- No vaciar `#recycle` ni la papelera de DSM.
- No `scrub`, `balance` ni `defrag`.
- No actualizar DSM ni reiniciar "para ver si arranca".
- No aceptar la sugerencia de soporte de "reinstalar DSM": los discos no están vacíos y la reinstalación borra la memoria y los metadatos que hacen falta.
- No pagar ni contactar al atacante.

---

## Qué guardar y mandar

1. `/tmp/evidencia_cliente.txt`
2. La salida de `preflight`
3. `survey.jsonl.gz`
4. Si se llegó: `cands.jsonl.gz`, `freemap` y los `md5` de lo extraído

Con eso se decide, con números y no con promesas, cuánto se salvó y por qué vía.
