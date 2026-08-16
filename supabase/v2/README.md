# PokeApp Supabase V2

This folder contains the greenfield SQL-first schema for PokeApp 2.0.

Use it only on an empty development/staging Supabase/Postgres database until the
cutover is explicitly approved.

## Apply Order

Run the files in `migrations/` lexicographic order:

1. `001_core.sql`
2. `002_seasons.sql`
3. `003_league.sql`
4. `004_shop.sql`
5. `005_saves.sql`
6. `006_activity_hall.sql`
7. `007_competitions.sql`
8. `008_indexes.sql`
9. `009_seed.sql`

## Development Reset

`reset_dev.sql` is destructive. It drops V2 tables/functions so the migrations
can be reapplied from scratch in development/staging.

Do not run it against production or the current V1 database.

## Runtime Status

The current Streamlit runtime does not use these tables yet. V2 repositories,
RLS, API and cutover are later phases.

## Real Validation

`tools/validate_supabase_v2_schema.py` can validate these migrations against a
real isolated PostgreSQL database through `psql`:

```powershell
py tools\validate_supabase_v2_schema.py `
  --psql "C:\path\to\psql.exe" `
  --host 127.0.0.1 `
  --port 5432 `
  --user postgres `
  --database pokeapp_v2_validation `
  --allow-destructive-reset
```

The database name must be `pokeapp_v2_validation` or start with that prefix. The
script intentionally refuses arbitrary database names because it runs the
destructive V2 development reset.
