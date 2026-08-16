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
`013_storage_policies.sql`, que protege `storage.objects` cuando Supabase expone
esa tabla:

```sql
select id, name, public
from storage.buckets
where id = 'raw-saves';
```

En Supabase real deberia devolver una fila con `public = false`.

Nota operativa: el conector MCP de Supabase puede rechazar DDL sobre
`storage.objects` con `INVALID_ARGUMENT`. Si ocurre en una base ya creada, abre
el SQL Editor de Supabase y ejecuta manualmente
`supabase/v2/migrations/013_storage_policies.sql`. En una base vacia,
`bootstrap.sql` ya incluye ese bloque.

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

Despues de ejecutar `bootstrap.sql`, las tablas V2 ya tienen RLS activo y vistas
seguras con `security_invoker`, para que se aplique la RLS del usuario que
consulta.

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

Fase 8 todavia debe implementar las operaciones criticas API/RPC. No uses el
cliente de navegador para escribir compras, ledger, parsed saves o team locks
directamente.

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

Si cambia alguna migration 001-014, regenera el bootstrap:

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
