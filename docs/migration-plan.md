# PokeApp 2.0 Migration Plan

## Principios

- No empezar React hasta cerrar producto, visual y mecanicas base.
- No hacer megarefactor de Streamlit salvo que ayude a definir el producto final.
- Mantener Supabase al principio.
- Medir antes de optimizar.
- Mantener Streamlit como fallback durante el corte.

## Fase 0 - Base Verde

Objetivo:

- Tests verdes.
- Compilacion verde.
- Documentacion tecnica inicial.
- Inventario de modulos actual.

Salida:

- `py -m compileall -q .`
- `py -m unittest discover -s tests`
- docs iniciales creados.

## Fase 1 - Cierre Visual Streamlit

Terminar Streamlit como referencia visual 2.0:

- Team Preview
- Tienda
- Pokemon Inspector
- Entrenadores
- Liga
- Saves
- PIN
- limpieza visual legacy

Limite:

- No invertir en ingenieria compleja de Streamlit si el cambio solo mueve detalles
  cosmeticos menores.

## Fase 2 - Cierre Funcional

Cerrar mecanicas que afectan modelo:

- Temporada configurable definitiva.
- Hall of Fame automatico.
- Retirados, robados y abandonos.
- Notificaciones y tipos de evento.
- Panel admin de Anto.

Al terminar esta fase se declara feature freeze funcional para 2.0.

Auditoria base:

- `docs/phase2-functional-audit.md`

## Fase 3 - Contratos De Dominio

Definir contratos estables:

- Pokemon / PublicPokemon / PrivatePokemon
- Trainer
- Season
- SeasonVersion
- Division
- Matchday
- Match
- LeagueStanding
- ShopItem
- ShopPromotion
- Purchase
- ParsedSave
- TeamLock
- TrainerFlags
- ActivityEvent
- HallOfFameEntry
- Cup
- Trial / Case

## Fase 4 - Dominio Puro

Extraer funciones que no dependan de Streamlit:

- ranking y standings
- recompensas
- ascensos/descensos
- retirados
- rebajas y validacion de compra
- temporada
- team locks
- trainer flags

Debe poder ejecutarse desde tests, shell, Streamlit o API.

## Fase 5 - Repositories

Separar intencion de persistencia:

- `SeasonRepository`
- `LeagueRepository`
- `TrainerRepository`
- `ShopRepository`
- `SaveRepository`
- `ActivityRepository`

El dominio no debe llamar a `supabase.table(...)`.

## Fase 6 - Supabase V2

Disenar, no migrar todavia.

Modelo conceptual:

- `seasons`
- `season_versions`
- `season_players`
- `divisions`
- `division_players`
- `matchdays`
- `matches`
- `trainer_flags`
- `team_locks`
- `shop_items`
- `shop_promotions`
- `purchases`
- `redemptions`
- `saves`
- `activity_events`
- `hall_of_fame`
- `hall_of_fame_team`

`season_id` debe estar en todo dato competitivo relevante.

## Fase 7 - RLS Y Seguridad

Antes de React:

- Definir campos publicos y privados.
- IVs/EVs/naturaleza privada solo para propietario/admin.
- Admin solo Anto.
- Operaciones criticas solo API/RPC.

Regla:

- Si un usuario no debe verlo, tampoco debe poder pedirlo a la base.

## Fase 8 - API

API pequena para operaciones criticas:

- `POST /shop/purchase`
- `POST /team-lock`
- `POST /league/close-matchday`
- `POST /season/config`
- `POST /admin/trainer-flags`
- `POST /trials/...`
- `POST /hall-of-fame/finalize`

## Fase 9 - Parser De Saves

Tratar PKHeX/bridge como caja negra:

```text
.sav/.dsv -> parser -> ParsedSave
```

PokeApp consume `ParsedSave`, no detalles internos del bridge.

## Fase 10 - React / Cloudflare

Construir nuevo cliente:

1. Shell
2. Login
3. Normativa
4. Hall of Fame
5. Home
6. Liga lectura
7. Entrenadores
8. PC/Cajas
9. Inspector
10. Tienda
11. Team Preview
12. Saves
13. Copa
14. Juicios
15. Temporada

Cloudflare Pages encaja para frontend. Workers/API solo donde haga falta backend.

## Fase 11 - Migracion De Datos

Transformar JSON de `settings` a tablas V2 con scripts.

Validar equivalencia:

- ranking antes = ranking despues
- monedas antes = monedas despues
- locks antes = locks despues
- flags antes = flags despues

## Fase 12 - Shadow Mode

Durante unos dias:

- Streamlit y React leen los mismos datos.
- Admin compara resultados.
- No se borra Streamlit todavia.

## Fase 13 - Staging Con Datos Clonados

Simular:

- compras
- locks
- saves
- cierre de jornadas
- retiradas
- Hall of Fame
- resets

## Fase 14 - Performance

Medir:

- Home
- Liga
- PC/Cajas
- Team Preview
- Tienda
- save parsing

Optimizar solo con datos reales.

## Fase 15 - Cutover

- Nueva PokeApp como principal.
- Streamlit como fallback temporal.
- Archivo final de Streamlit cuando la nueva este estable.
