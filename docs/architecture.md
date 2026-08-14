# PokeApp Architecture

Este documento es la fuente tecnica viva para la migracion 2.0. La regla base es
conservadora: no tirar la app actual, sino separar el cerebro util que ya existe
del cuerpo de Streamlit.

## Estado Actual

PokeApp es una app Streamlit con logica de liga, tienda, saves, entrenadores,
copa, juicios y Discord. La entrada principal esta en `main.py`, que aplica CSS,
abre login/sidebar/topbar y enruta cada seccion.

La persistencia actual es mixta:

- Supabase es la fuente remota principal cuando esta configurado.
- SQLite local existe como fallback/desarrollo.
- `settings` guarda varios estados agregados en JSON.
- Los saves se guardan como metadatos en tabla y bytes en storage/local.

Tablas detectadas en el modelo actual:

- `saves`
- `settings`
- `purchases`
- `redemptions`
- `pokemon_flags`
- `shop_discounts`
- `team_locks`

Claves importantes guardadas en `settings`:

- `league_state`
- `season_config_v2`
- `trainer_flags`
- `trainer_snapshot:*`
- `pin:*`
- `badges_count:*`
- marcadores de avisos, promociones y recompensas

Desde Fase 2.1, `league_state` incluye `round_snapshots` para jornadas cerradas.
Estos snapshots congelan config aplicada, divisiones, standings, puntos y monedas
otorgadas. Es una solucion compatible con la arquitectura actual, previa a tablas
Supabase V2.

## Problema Principal

La deuda mas importante no es Supabase. Es que entidades centrales de competicion
viven como JSON grandes dentro de `settings` o como estado de Streamlit.

Esto funciona en Streamlit con pocos usuarios, pero para React/API/Cloudflare se
necesitan consultas directas y permisos por entidad:

- temporada activa
- jugadores de temporada
- jornada actual
- clasificacion
- equipo fijado
- promociones vigentes
- flags de entrenador
- actividad reciente

## Arquitectura Objetivo

Flujo objetivo:

```text
UI
  -> Service
  -> Domain
  -> Repository
  -> Supabase / Storage / external parser
```

Reglas:

- El dominio no sabe que Supabase existe.
- La UI no decide reglas oficiales.
- Las operaciones criticas se validan en backend/API.
- El parser de saves se trata como caja negra.
- Las lecturas publicas pueden ir directas si RLS lo permite.

## Source Of Truth

Hay que decidir y documentar una fuente de verdad por dato:

- Liga oficial: backend/repositorio, no `st.session_state`.
- Compras y promociones: transaccion server-side/RPC o API.
- Saves: metadatos en DB, bytes en storage.
- Snapshots: derivados cacheables, nunca sustituyen al save.
- Hall of Fame: derivado al finalizar temporada/copa, persistido como historico.
- Flags de entrenador: entidad propia, no texto decorativo.

## Criterios De Salida Por Fase

Ninguna fase debe terminar con la suite previamente verde en rojo.

Minimo antes de avanzar:

- `py -m compileall -q .`
- `py -m unittest discover -s tests`
