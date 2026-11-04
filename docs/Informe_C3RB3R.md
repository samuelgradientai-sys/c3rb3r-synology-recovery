# Incidente ransomware C3RB3R (.L0CK3D) — NAS Synology
Resumen para el equipo de ciberseguridad · corte 30-oct-2026

## 1. Qué es
- **Familia:** C3RB3R (variante de Cerber sobre código filtrado de Conti v3). Dr.Web: `Trojan.Encoder.38200`.
- **Indicadores:** extensión `.L0CK3D` (con cero), nota `read-me3.txt` ("C3RB3R INSTRUCTIONS") en cada carpeta, footer de 588 B al final de cada archivo.
- **Proceso cifrador en DSM:** `libgld` (también visto como `libgittcb`, `qnetd`, `init-rsysd`). Muestra analizada por la comunidad: SHA-256 `802ac85d19dc6db2b1849bb3499877280544d04a0ae94d4c408b6c321669903d` (UPX).
- **Entrada reportada:** DSM sin parchear expuesto a internet. 360 atribuye CVE-2026-13639 / CVE-2026-13684 (Synology-SA-26:13, 18-sep); Synology cita SA-24:20 (CVE-2024-10441). También PHP2Shell (CVE-2026-109618/109619) en paquetes con PHP. Hay reportes sin confirmar con DSM 7.4.1 y solo QuickConnect.
- **Persistencia reportada por terceros:** entrada en cron como root y shell inverso a `208.87.128.140:4001` (dossier Benjamin-zlt). Tratar el NAS como comprometido.
- **Cifrado:** ChaCha8 por archivo + registro AES-256-CBC con una clave maestra de sesión de 48 B (solo en RAM del proceso) + RSA-2048 del atacante. RNG: `/dev/urandom` + Hash_DRBG (sin debilidad conocida).
- **Modos por tamaño:** <=1 MiB cifrado completo (0x24); 1–5 MiB primer MiB (0x26); >5 MiB tres tramos de ~4 % (0x25).
- **Rescate reportado:** ~0,037 BTC (~3.000 USD), se duplica a los 5 días.

## 2. Estado de la víctima
- Ataque: 28-oct ~20:32. Una sola sesión (marcador `<omitido>`) y un solo ID de víctima (57 notas idénticas).
- **El NAS se reinició** → la clave maestra en RAM se perdió.
- Muestras analizadas: 202 archivos (13 del cliente + 189 de otro expediente). 198 cifrados completos (<1 MB).

## 3. Qué se hizo (todo sobre copias, sin contacto con el atacante)
- Triage byte a byte: entropía ~7,95 en todos los archivos <1 MB → sin contenido recuperable.
- Prueba de la clave publicada (soimy/c3rb3r-rescue): rechazada en 2 pasadas (marcador distinto y *nonce check failed*). Confirma clave de otra víctima.
- **Rescate parcial sin clave** de archivos grandes (carving ZIP/PDF de zonas no cifradas):
  - un libro de tarifas (.xlsm, 9 MB): 10 hojas con datos (sin nombres de hoja ni macros).
  - un documento regulatorio (PDF, 17,6 MB): 10 de 13 páginas + 6 fotos.
  - dos anexos gráficos (PDF, 1,7 MB): página 2 de cada uno.
- Revisión de fuentes: GitHub (10 repos), Reddit (~20 hilos), BleepingComputer, No More Ransom, Emsisoft, Kaspersky, YouTube, foros en 7 idiomas. **No existe descifrador público.**
- Estafas identificadas: canal "un canal de "rescate"" (el canal de Telegram, el correo de contacto) y "All in one decryptor". Piden la nota de rescate para revender el rescate. No contactar.

## 4. Lo que funcionó en los casos de éxito publicados
| Escenario | Resultado | Requisito |
|---|---|---|
| Proceso `libgld` congelado (`kill -STOP`) + volcado de memoria | 100 % descifrado | NAS **sin reiniciar** y proceso vivo |
| Snapshots Btrfs | 100 % | Snapshots previos al ataque (son de solo lectura: el virus no los modifica) |
| Bloques viejos Btrfs (crt106/c3rb3r-btrfs-recovery) | Alto en archivos medianos/grandes | Discos del NAS, volumen Btrfs, sin escribir encima |
| Rescate parcial por archivo | Parcial, solo >1 MB | Solo los archivos |
| Clave de otra víctima / descifradores comerciales | 0 % | — |

## 5. Recomendaciones
**Recuperación (en este orden):**
1. Encender el NAS **sin internet** y revisar snapshots **carpeta por carpeta**, incluida la ruta oculta `/volume1/@sharesnap/<carpeta>/`. Un caso del 30-oct tenía `#snapshot` vacío en la interfaz pero 186 snapshots intactos ahí. Si existe uno anterior al 28-oct 20:32: **Clonar**, nunca Restaurar encima.
2. Si no hay snapshots: recuperación Btrfs por SSH en solo lectura (o clonando los discos). No reinstalar DSM, no crear/borrar grupos de almacenamiento, no sacar ni reordenar discos, no desfragmentar ni reparar el volumen.
3. **No borrar** los `.L0CK3D` ni vaciar la papelera (preservan bloques viejos y sirven si algún día se filtra la clave).
4. Copias externas: AutoRecuperación de Office en los PC (había lock files `~$` de *SODIMAC RESPUESTAS.docx* y *TARIFAS X KILO 2026.xlsx*: estaban abiertos durante el ataque), correos enviados, gestor de residuos (certificados RESPEL), ANLA/VITAL, clientes.
5. Pago / prueba gratuita del portal: decisión de la dirección. No se recomienda pagar. Si se usa la prueba gratis (1 archivo ≤1 MB, una vez por ID), hacerlo desde un equipo aislado y sin negociar.

**Contención y endurecimiento:**
- Tratar el NAS como comprometido: reinstalación limpia de DSM (reset modo 2) **después** de terminar la recuperación.
- Instalar a mano la última DSM del modelo (el actualizador puede decir "al día" sin estarlo). Mínimos según SA-26:13: 7.4-90075 / 7.3.2-86009-4 / 7.2.2-72806-9 / 7.2.1-69057-12. Actualizar PHP o desinstalar los paquetes que lo usan.
- Cero exposición a internet: apagar QuickConnect, quitar redirecciones de puertos (5000/5001/445), desactivar UPnP en el router; acceso remoto solo por VPN (WireGuard/Tailscale).
- Deshabilitar la cuenta `admin`, 2FA en todas las cuentas, bloqueo automático de IP, SSH apagado si no se usa.
- Cambiar todas las credenciales que tuvo el NAS (incluidas las de backups en la nube) y revisar los PC con unidades mapeadas.
- **Snapshots inmutables** (WORM) en todas las carpetas compartidas + copia 3-2-1 con una copia **desconectada**: en otros casos el disco USB de Hyper Backup que estaba conectado también se cifró.
- Plan de respuesta: ante archivos `.L0CK3D`, **no reiniciar ni apagar**: desconectar red, `kill -STOP` al proceso y volcar su memoria. Es la única vía de descifrado completo.

## 6. Archivos de soporte
`~/rescate_cliente/` — archivos rescatados, inventarios, hilos de Reddit/BleepingComputer guardados.
