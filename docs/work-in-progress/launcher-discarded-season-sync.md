# Partida que no llega a la Liga: cola atascada por una temporada descartada

**CORRECCIÓN PUBLICADA el 2026-11-10; pendiente de confirmar con el propio entrenador.**
Commit `bdff9a8`, API Railway `4af3e38a` (rollback `909765eb`). Solo API: sin SQL, sin
Launcher nuevo, sin datos modificados.

## Identidad

Ningún registro de producción se llama Víctor (nombre visible, metadatos ni cuenta).
`ByVisan02` es una **inferencia**: es el único de los seis participantes sin partida en
ChampionsLocke, y el único con partidas solo en temporadas descartadas. Pendiente de
confirmar por el propietario.

## Causa

`trusted_save_outbox` entrega siempre la fila no verificada más antigua. Una fila de la
temporada «Prueba2» (`0b31a44d`, descartada el 2026-10-29 20:47 UTC) estaba aceptada por el
servidor pero sin relectura confirmada:

1. `GET /saves/receipt` respondía 200.
2. `GET /v1/read/seasons/0b31a44d/pc` respondía 404, porque una temporada descartada no se lee.
3. `_refusal` convierte ese 404 en `BACKEND_UNAVAILABLE`, así que `_deliver_pending` relanza
   el error y la interfaz indica «Sin conexión».

La fila no terminaba nunca y las copias de la Liga y personal, detrás de ella, no se enviaban.

## Evidencia (2026-11-09, solo lectura)

- Registros HTTP de la API: un cliente con Launcher 0.26.13, con la renovación de sesión a
  las 22:24:10, la misma que `auth.sessions.updated_at` de ByVisan02.
- De 22:24 a 22:32: 25 pares receipt 200 / pc 404 sobre `0b31a44d`, y ninguna subida.
- Última partida de esa cuenta: 2026-10-29, todas procesadas sin error.
- `launcher_observations` está vacía: el Launcher no envía errores locales al servidor.

## Núcleo y empaquetado (0.26.13)

Descartados como causa de ese episodio: el núcleo respondía peticiones esa noche.

- `PokeApp.Core.exe` llega a READY y responde desde la carpeta empaquetada, con perfil aislado.
- `PokeApp.Parser.exe` lee una partida Y de prueba desde esa carpeta.
- `python314.dll`, `VCRUNTIME140*.dll` y `ucrtbase.dll` van incluidas; las importaciones
  restantes son del sistema. No se ha probado en un equipo Windows 10 real.
- El texto literal «El núcleo ha fallado» no existe en el Launcher.

## Corrección

`GET /v1/seasons/{id}/saves/receipt` responde 404 si la temporada está descartada. El
Launcher ya instalado cierra entonces esa fila (`blocked=1`, sin bytes) y continúa con las
siguientes. El guardado local no se toca.

Pruebas: `tests/test_phase077_launcher_sync.py` reproduce el atasco y su salida;
`tests/test_phase16d_save_sync.py` cubre la ruta. 51 pruebas de sincronización correctas.

## Pendiente

- Confirmar que la partida llega: `saves/receipt` 404 sobre `0b31a44d` seguido de
  `PUT /v1/seasons/40ab0910/saves/raw` y una partida actual en ChampionsLocke.
- No hay evidencia sobre el archivo actual del entrenador. Si sigue fallando, hacen falta el
  mensaje exacto y «Copiar diagnóstico».
- Un 404 inesperado de la API se sigue mostrando como «Sin conexión». Corregirlo exige una
  versión nueva del Launcher; no se ha hecho.
