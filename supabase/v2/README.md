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
