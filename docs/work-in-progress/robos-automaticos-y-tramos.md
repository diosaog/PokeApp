# Robos automáticos, sincronización tras un robo y tramos nuevos

**PUBLICADO el 2026-11-18** con autorización del propietario. Código `fbaf4af`,
descarga `379eb56`. Rama `claude/net-friendship-discord`.

| Pieza | Estado | Rollback |
|---|---|---|
| Launcher | 0.26.16 en el canal estable: instalador `4046240f…`, 159 505 891 bytes, firma Ed25519 válida, mínimo 0.26.0 | Restaurar `updates/stable.json` de 0.26.15 y publicar una versión superior |
| Web Cloudflare | `3594521e` (`/launcher/download` sirve 0.26.16) | `165bfc7d` |
| Verificador | **Sin desplegar**: sigue `39181f7f` (imagen `777314cc`). El paquete está listo en `%LOCALAPPDATA%/PokeApp-builds/verifier-0.26.16-379eb56`; el despliegue lo bloqueó el control de permisos | — |
| API, SQL | Sin cambios (API `14ba5fa1`, DB 087) | — |

## Incidente: sincronización en pausa tras los dos robos

Síntomas (Anto, y los demás participantes de un robo): «Sincronización obligatoria» y
«Recuperación pendiente» en el Launcher, partida sin sincronizar desde el robo
(17-11 ~22:03 UTC) y actualizaciones aplazadas para siempre.

Causas, todas en el Launcher 0.26.15:

- El enlace local de un robo solo se liberaba en `COMMITTED`/`CANCELLED`; un lado ya
  probado por PokeApp (`DONOR_VERIFIED` / `RECIPIENT_VERIFIED`) seguía pausando lecturas y
  sincronización.
- El lado se aplica antes de que el verificador lo pruebe (ciclo de 60 s) y nada volvía a
  preguntar sin pulsar un botón.
- Para cerrar un lado probado se exigía además que la partida no hubiera cambiado desde el
  robo.
- Con la pausa, el paso de nube tampoco renovaba la sesión.
- `RECONCILED` (robo decidido y terminado) contaba como abierto en el aviso, en la
  comprobación de restaurar y en el actualizador (`TRANSFER_IN_PROGRESS`).

0.26.16: un lado probado es final (`LOCAL_FINAL`), el Launcher pregunta solo por la prueba
de lo que ya aplicó, la sesión se renueva aunque la partida esté en pausa, y un robo en
curso muestra un aviso tranquilo en vez de «Recuperación pendiente». Comprobado sobre una
copia del journal real de Anto: binding `fb176784` aplicado (`9eb93f11`, salida
`9da462d2…`) = resultado probado por el servidor → se cierra solo al abrir 0.26.16.

**Instalación manual una vez:** el 0.26.15 de Anto, STeeLAG, ByVisan02 y Aaron aplaza la
actualización indefinidamente («Esperando a que termine una recuperación pendiente / una
entrega de robo»). Deben instalar 0.26.16 desde «Descargar Launcher» con el Launcher
cerrado. Anto: instalado en su PC el 2026-11-18 (silencioso, sin abrir).

## Reglas del propietario aplicadas

- **Robo directo** (17-11): sin solicitud ni botón; cada Launcher aplica su lado en cuanto
  el juego está cerrado, por el mismo camino seguro. El robo en cola de ByVisan02 a Aaron
  (`febddd4b`, Haunter sin objeto) se aplicará solo cuando Aaron abra 0.26.16.
- **El objeto no se roba** (17-11): `held_item` en los dos planes; el ladrón recibe el mismo
  individuo con objeto 0 y la víctima recupera una unidad en la mochila (un cristal Z
  equipado de 7.ª gen. no va a la mochila: la víctima conserva su versión de objeto clave).
  **Solo se aplica a robos planificados por un verificador con el escritor nuevo.**
  Pendiente de decisión: la Volcarona robada a Anto el 17-11 llevaba Seguro Debilidad (639)
  y STeeLAG lo conserva.
- **Tramos** (17-11): J2 al 5.º gimnasio (Lem, nivel 44), J3 al 7.º (Astrid, nivel 58).
  Normativa III actualizada, fecha 18 de noviembre de 2026, reglas 6.12–6.13 nuevas.
- **Avisos que estorban** (18-11): Inventario oculta compras canceladas o retiradas (086/087)
  y los robos terminados; «Robos entre guardados» y el panel del Launcher solo listan robos
  en curso (un intento cancelado propio, 24 h).

## Comprobaciones

- Python 1566 OK (incluye `tests/test_robbery_auto_delivery.py`, con ficheros y journal
  reales), web 404, Node 59, smoke de interfaz del Launcher 0 FAIL.
- Nativo: robo en cajas 224, robo desde equipo 560, títulos cruzados 8, objetos rápidos 280,
  objetos de tienda 1776.
- `tools/validate_phase085_activation` con el parser empaquetado de 0.26.16 sobre 001–087:
  PASS 63 (necesita `PGCLIENTENCODING=UTF8 LC_MESSAGES=C` en este equipo: si no, psql
  devuelve los errores en WIN1252 y el validador los pierde).
- Feed público verificado (firma válida, 0.26.16); descarga web 0.26.16.
