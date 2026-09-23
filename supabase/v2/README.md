# PokeApp Supabase V2

Este directorio contiene el schema SQL-first de PokeApp 2.0.

Las migrations separadas de `supabase/v2/migrations/` son la fuente de verdad.
`bootstrap.sql` es solo una comodidad para levantar V2 desde el SQL Editor de
Supabase sin copiar todos los archivos a mano.

## A) Crear V2 En Supabase Vacia

Usa esto solo en una base limpia de Supabase V2. No lo ejecutes sobre V1.

1. Entra en Supabase y abre el proyecto nuevo/limpio donde vas a preparar V2.
2. Ve a `SQL Editor`.
3. Pulsa `New query`.
4. Abre o copia el contenido de `supabase/v2/bootstrap.sql`.
5. Pegalo entero en la query.
6. Pulsa `Run`.

Resultado esperado:

- Se crea el schema publico V2 completo.
- Se crean las tablas, constraints, funciones, RLS, vistas seguras, storage
  policies, indexes y seeds iniciales.
- Aparecen 10 entrenadores base.
- Aparecen los objetos base de tienda.
- Si el proyecto es Supabase real, queda preparado el bucket privado `raw-saves`.

El archivo esta marcado como:

```sql
-- ONLY FOR EMPTY POKEAPP V2 DATABASE.
```

## B) Comprobar Que Funciono

Despues de ejecutar `bootstrap.sql`, en Supabase abre `Table Editor` y deberias
ver tablas como estas:

- `trainers`
- `seasons`
- `season_players`
- `season_config_versions`
- `divisions`
- `matchdays`
- `matches`
- `team_locks`
- `save_files`
- `parsed_saves`
- `shop_items`
- `shop_promotions`
- `purchases`
- `redemptions`
- `coin_transactions`
- `activity_events`
- `hall_of_fame_entries`
- `cups`
- `trial_cases`
- `penalties`

Comprobaciones rapidas desde `SQL Editor`:

```sql
select table_name
from information_schema.tables
where table_schema = 'public'
order by table_name;
```

```sql
select slug, display_name, globally_enabled
from public.trainers
order by slug;
```

```sql
select count(*) as trainers_seeded
from public.trainers
where metadata ->> 'seeded' = 'true';
```

```sql
select count(*) as shop_items_seeded
from public.shop_items
where metadata ->> 'seeded' = 'true';
```

```sql
select count(*) from public.seasons;
select count(*) from public.season_players;
select count(*) from public.matchdays;
select count(*) from public.purchases;
select count(*) from public.coin_transactions;
```

Es normal que `seasons`, `season_players`, `matchdays`, `purchases` y
`coin_transactions` esten a 0 justo despues del bootstrap. Las tablas existen,
pero la temporada real y sus datos los insertara la app cuando toque.

Comprobaciones de seguridad:

```sql
select relname, relrowsecurity
from pg_class
where relnamespace = 'public'::regnamespace
  and relkind = 'r'
order by relname;
```

Todas las tablas de aplicacion deben devolver `relrowsecurity = true`.

Tambien deberias ver vistas de lectura como:

```sql
select table_name
from information_schema.views
where table_schema = 'public'
  and (table_name like 'public_%' or table_name like 'current_%')
order by table_name;
```

## C) Storage

V2 usa un bucket privado llamado `raw-saves` para guardar los archivos `.sav`.
La tabla `save_files` guarda metadatos y rutas; los bytes reales van al bucket.

`bootstrap.sql` incluye el bloque Supabase de `009_seed.sql` que intenta crear o
actualizar el bucket si existe el schema `storage`. Tambien incluye
`013_storage_policies.sql`, que protege `storage.objects` con policies
compatibles con Supabase Cloud y no toca ownership ni el RLS base de Storage.
Las migrations `015_public_trainers_visibility.sql`,
`016_public_team_locks_visibility.sql`,
`017_public_coin_balances_visibility.sql` y
`018_public_views_visibility.sql` reabren de forma segura las proyecciones
públicas que el validador necesita:

```sql
select id, name, public
from storage.buckets
where id = 'raw-saves';
```

En Supabase real deberia devolver una fila con `public = false`.

Si Supabase bloquease esa insercion por permisos del proyecto, crea el bucket a
mano:

1. Ve a `Storage`.
2. Pulsa `New bucket`.
3. Nombre/id: `raw-saves`.
4. `Public bucket`: desactivado.
5. Guarda.

## D) Reset

`supabase/v2/reset_dev.sql` es DESTRUCTIVO.

Sirve solo para borrar el schema V2 en una base local, de desarrollo o staging y
volver a aplicar migrations. No esta incluido en `bootstrap.sql`.

No ejecutes `reset_dev.sql` sobre Supabase V1 ni sobre ninguna base que quieras
conservar.

## E) V1

No borres Supabase V1 todavia.

Primero levanta V2 en un entorno limpio, verifica tablas, seeds, storage y
comportamiento de la app. La migracion/cutover real se decidira mas adelante.

## F) RLS

Despues de ejecutar `bootstrap.sql`, las tablas V2 ya tienen RLS activo.
Las vistas privadas usan `security_invoker` y las proyecciones publicas se
mantienen legibles sin abrir las tablas privadas.

Modelo resumido:

- `anon` no tiene lecturas de app.
- `authenticated` usa vistas `public_*` y `current_*`.
- los datos privados de saves, parsed saves, team locks privados, compras,
  redenciones y ledger solo son owner/admin.
- admin se controla con `trainers.is_admin`.
- `service_role` queda solo para backend/API/parser.

Documento de detalle:

```text
docs/security-rls.md
```

Phase 8C implementa Team Lock + actividad via RPC backend-only (019), validada
localmente y en V2 staging. 020 (jornada/sanciones) tambien esta validada en staging.
021 compra normal atomica esta DONE local + staging (29 checks, cleanup PASS). No uses el
navegador para escribir compras, ledger, parsed saves o team locks directamente.
022 compra promocionada atomica DONE local + staging (27 checks, regresion 8D
29 checks y cleanup PASS). `stock_used` tambien es server-only. Compra queda
pending, sin redencion. Detalles: `docs/phase8e-promotional-purchases.md`.
Una base V2 existente necesita solo las migrations nuevas que falten, en orden,
con autorizacion y validacion, nunca bootstrap ni reset. No se ha desplegado la API.

## Migrations Y Bootstrap

Orden oficial de migrations:

1. `001_core.sql`
2. `002_seasons.sql`
3. `003_league.sql`
4. `004_shop.sql`
5. `005_saves.sql`
6. `006_activity_hall.sql`
7. `007_competitions.sql`
8. `008_indexes.sql`
9. `009_seed.sql`
10. `010_security_helpers.sql`
11. `011_rls_policies.sql`
12. `012_security_views.sql`
13. `013_storage_policies.sql`
14. `014_security_invoker_hardening.sql`
15. `015_public_trainers_visibility.sql`
16. `016_public_team_locks_visibility.sql`
17. `017_public_coin_balances_visibility.sql`
18. `018_public_views_visibility.sql`
19. `019_team_lock_api.sql`
20. `020_current_matchday_store_ban_contract.sql`
21. `021_normal_purchase_api.sql`
22. `022_promotional_purchase_api.sql`
23. `023_pokemon_identity.sql`
24. `024_redemption_effect_boundary.sql`
25. `025_robbery_voucher_and_redemption.sql`
26. `026_season_admin_setup_api.sql`
27. `027_competitive_matchdays.sql`
28. `028_participant_status_admin.sql`
29. `029_season_finalization_archive_hall.sql`

029 incorpora finish/archive/discard explicitos, archivo y Hall de Liga atomicos,
procedencia historica y visibilidad de borradores descartados. Bootstrap 001-029
es SOLO PARA BASE VACIA. [Contrato](../../docs/phase8j-season-finalization.md) e
[informe de validacion](../../docs/phase8j-completion-report.md). En Pokeapp 2.0
YA ESTA APLICADA la 029 de `5f77a48` como `20260923232516`, tras gates locales y
push. No repetir 029 ni reset/bootstrap. Validacion local y real completada:
431 tests, 19 grupos remotos, regresiones previas y limpieza independiente PASS.
No cambio de runtime ni borrado de V1. Hall de Copa pendiente de su propio contrato.

028 incorpora bajas competitivas permanentes y efectivas por jornada, conservando
historial, economia, saves y equipos fijados. En el checkpoint 8I bootstrap contenia
001-028, solo para BASE VACIA. En Pokeapp 2.0 YA ESTA APLICADA solo la 028 como
`20260923220301`, tras validacion local y push `baecb8a`. Validacion real y limpieza
independiente PASS. No repetir 028, migrations previas ni reset/bootstrap alli.
[Contrato](../../docs/phase8i-participant-status.md) y
[estado de validacion](../../docs/phase8i-completion-report.md).

027 anade apertura/resultados/cancelacion/cierre atomico de jornadas, historial
inmutable, recompensas y correccion acotada. [Contrato](../../docs/phase8h-matchday-operations.md)
e [informe/gates](../../docs/phase8h-completion-report.md). En ese checkpoint, bootstrap 001-027
solo para una base vacia. En Pokeapp 2.0 se aplico SOLO 027 como `20260923210625`
tras gates locales y push `bef5c4d`; validacion remota y limpieza independiente PASS.
No repetir 027, bootstrap/reset ni migrations previas en ese staging.

026 incorpora administracion inicial de temporada, revisiones/recibos, divisiones
A/B, primera jornada y activacion validada. Revoca las escrituras directas del
navegador sobre las ocho tablas de preparacion; las lecturas siguen disponibles.
DONE local + staging: [contrato](../../docs/phase8g1-season-admin-api.md) e
[informe de cierre](../../docs/phase8g1-completion-report.md).
En Pokeapp 2.0 ya se aplico SOLO 026 como `20260923192300`, despues de validacion
local y commit/push. Validacion remota y limpieza independiente PASS.
No repetir 026, bootstrap ni reset en ese staging.

025 anade el comodin canonico reward-only, origen unico de regalos y canje de robo
con ciclo persistente. [Contrato](../../docs/phase8f1-robbery-voucher.md).
En V2 existente con 024, aplicar SOLO 025 tras validacion local; nunca bootstrap/reset.
El [informe](../../docs/phase8f-completion-report.md) registra la version remota y gates.
En Pokeapp 2.0 ya esta aplicada como `20260923180416`, validada y limpiada;
no repetir 025 ni bootstrap. Fase 8F DONE: 17 grupos robo/comodin + 19 regresion PASS.

024 incorpora canjes atomicos de Blindar/Revivir con identidad autoritativa y
eventos privados. Robo y su comodin siguen pendientes de un contrato de catalogo.
No modifica saves ni ejecuta PKHeX. Para una V2 existente con 023, aplicar solo
024 cuando este validada y autorizada: nunca volver a ejecutar el bootstrap.
En el staging Pokeapp 2.0 ya se aplico como `20260923172957` y paso la validacion
de Blindar/Revivir: no repetirla alli. [Estado de 8F](../../docs/phase8f-redemption-effects.md).

023 incorpora identidad privada por individuo, observaciones, reconciliacion y
enlaces seguros de flags legacy. No implementa canjes ni conecta el runtime.
Su estado local/remoto y comandos estan en `docs/phase8f0-pokemon-identity.md`.

Al anadir una migration, regenera el bootstrap sin reescribir las ya aplicadas:

```powershell
py tools\generate_supabase_v2_bootstrap.py
```

## Validacion Real

Validar migrations contra PostgreSQL real:

```powershell
py tools\validate_supabase_v2_schema.py `
  --psql "C:\path\to\psql.exe" `
  --host 127.0.0.1 `
  --port 5432 `
  --user postgres `
  --database pokeapp_v2_validation `
  --allow-destructive-reset
```

Validar el bootstrap contra PostgreSQL real:

```powershell
py tools\validate_supabase_v2_schema.py `
  --psql "C:\path\to\psql.exe" `
  --host 127.0.0.1 `
  --port 5432 `
  --user postgres `
  --database pokeapp_v2_validation_bootstrap `
  --allow-destructive-reset `
  --build-source bootstrap
```

La base debe llamarse `pokeapp_v2_validation` o empezar por ese prefijo. El
validador se niega a usar otros nombres porque ejecuta el reset destructivo de
desarrollo.

## Validacion Real En Supabase Staging

Despues de crear una Supabase V2 limpia con `bootstrap.sql`, prepara un archivo
local no commiteado:

```powershell
Copy-Item .env.supabase-v2-rls.example .env.supabase-v2-rls.local
```

Rellena:

```text
POKEAPP_V2_SUPABASE_URL
POKEAPP_V2_SUPABASE_ANON_KEY
POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY
```

Ejecuta:

```powershell
py tools\validate_supabase_v2_rls.py --env-file .env.supabase-v2-rls.local
```

El script crea usuarios Auth temporales, fixtures de Trainer A/B/Admin, valida
JWT reales, vistas, RLS, escrituras bloqueadas y Storage `raw-saves`. Limpia los
fixtures al terminar salvo que uses `--keep-fixtures`.

No uses credenciales de V1. No pegues la service role key en frontend ni la
commitees.
