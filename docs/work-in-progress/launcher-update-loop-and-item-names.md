# Bucle de actualización del Launcher y objetos «sin identificar»

**PUBLICADO el 2026-11-11 con autorización del propietario.** Commit `259a9e3`.

| Pieza | Publicado | Rollback |
|---|---|---|
| API Railway | `010a6546`, 139 rutas | `4af3e38a` |
| Web Cloudflare | `5e241403` | versión anterior en Cloudflare |
| Launcher | 0.26.14 en el canal estable, instalador `b5c7a4e6…`, 159 493 828 bytes, firma Ed25519 válida, mínimo 0.26.0 | Restaurar `updates/stable.json` anterior y publicar una versión superior |

No hay SQL, no se modificaron datos y el verificador no cambia (`39181f7f`).

## 1. Bucle de actualización (Iker)

**Síntoma:** instala la actualización, al abrir vuelve a salir y, pulse lo que pulse, el
Launcher se cierra. Así una y otra vez.

**Causa:** la actualización silenciosa de NSIS (`/S --updated --force-run`) abandona sin
avisar cuando no puede mover un archivo antiguo, por ejemplo uno bloqueado por un
antivirus. Mientras reintenta, cierra a la fuerza cualquier proceso de la carpeta de
instalación, incluido un Launcher recién abierto. Después, el Launcher antiguo volvía a
ofrecer la misma instalación silenciosa, sin recordar el fallo.

**Corrección (0.26.14):**

- Antes de lanzar el instalador se escribe `updates/attempt.json` con la versión, el modo
  y la hora.
- Si al arrancar sigue la versión antigua, el siguiente intento abre el instalador con su
  ventana (`--updated`, sin `/S`), con el botón «Instalar con asistente».
- El Launcher solo se cierra después del evento `spawn`. Si el instalador no llega a
  arrancar, se muestra `INSTALLER_BLOCKED` y se remite a «Descargar Launcher».
- Si el Launcher se abre mientras el instalador sigue en marcha, lo detecta (EBUSY sobre
  el instalador y un intento de menos de 15 minutos), lo avisa y no arranca el núcleo.
- Los pasos de la actualización quedan en `launcher.log`.

**Pendiente:** el Launcher que tiene Iker es anterior y conserva la lógica vieja. Tiene que
instalar a mano una vez desde «Descargar Launcher». A partir de 0.26.14 se aplica lo nuevo.

## 2. «Objeto sin identificar (falta el juego)»

**Causa:** 292 números de objeto significan una cosa en la 3.ª generación y otra a partir
de la 4.ª. Entre ellos están Garra Rápida (#217), Baya Zidra (#158), los objetos Elección,
Vidasfera, Banda Focus, Lazo Destino y las piedras evolutivas. La web solo nombra el
objeto si sabe la tabla. Los Team Lock no la guardaban y Avisos no pasaba el juego.

**Corrección:**

- Los Team Lock nuevos guardan `item_generation`.
- A los ya fijados se les asigna al leerlos (Batallas, Team Preview, «Equipo oficial»),
  tomándola del juego de la partida de Liga del participante, que es público en el
  resumen de la Liga. No se toca ningún dato guardado.
- Avisos usa el juego del propio aviso.

**Comprobación pendiente:** el propietario recarga Batallas y ve los nombres de su Team
Lock del 9 de noviembre. La lectura de producción para comprobarlo desde aquí fue
denegada por permisos.
