# Privacidad

La app es local al navegador.

## Garantias implementadas

- Sin backend.
- Sin base de datos.
- Sin login.
- Sin cookies.
- Sin `localStorage`.
- Sin IndexedDB.
- Sin telemetria.
- Sin llamadas a APIs externas durante uso normal.

## Exportacion manual

El JSON exportado contiene configuracion, objetivo, inventario, Pokemon e historial opcional. No contiene datos de cuenta ni identificadores personales. La importacion se valida con Zod antes de restaurar el estado.
