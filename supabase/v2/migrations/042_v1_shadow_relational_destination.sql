-- Phase 11: isolated relational V1 source destination for Shadow.
-- This schema is deliberately outside the public competitive lifecycle. It preserves
-- legacy evidence and mapped facts without changing public V2 seasons or histories.
begin;

create schema if not exists v1_shadow;
revoke all on schema v1_shadow from public, anon, authenticated, service_role;

create table v1_shadow.runs (
  id uuid primary key,
  source_ref text not null,
  capture_hash text not null check (capture_hash ~ '^[0-9a-f]{64}$'),
  mapping_version text not null,
  plan_hash text not null check (plan_hash ~ '^[0-9a-f]{64}$'),
  captured_at timestamptz not null,
  manifest jsonb not null check (jsonb_typeof(manifest) = 'object'),
  status text not null check (status in ('prepared','reconciled','failed'))
);

create table v1_shadow.batches (
  run_id uuid not null references v1_shadow.runs(id) on delete restrict,
  ordinal integer not null check (ordinal >= 0),
  batch_hash text not null check (batch_hash ~ '^[0-9a-f]{64}$'),
  completed_at timestamptz,
  row_counts jsonb not null default '{}'::jsonb check (jsonb_typeof(row_counts) = 'object'),
  primary key (run_id, ordinal)
);

create table v1_shadow.records (
  run_id uuid not null references v1_shadow.runs(id) on delete restrict,
  id uuid not null,
  source_table text not null,
  source_key text not null,
  payload jsonb not null,
  primary key (run_id, id),
  unique (run_id, source_table, source_key)
);

create table v1_shadow.identities (
  run_id uuid not null references v1_shadow.runs(id) on delete restrict,
  id uuid not null,
  entity_type text not null,
  source_key text not null,
  target_table text not null,
  target_id uuid,
  primary key (run_id, id),
  unique (run_id, entity_type, source_key)
);

create table v1_shadow.trainers (
  run_id uuid not null references v1_shadow.runs(id) on delete restrict,
  id uuid not null,
  name text not null,
  v2_candidate_id uuid,
  primary key (run_id, id),
  unique (run_id, name)
);

create table v1_shadow.seasons (
  run_id uuid not null references v1_shadow.runs(id) on delete restrict,
  id uuid not null,
  source_key text not null,
  effective_status text,
  status_provenance text not null,
  started_at timestamptz,
  current_day integer check (current_day is null or current_day >= 1),
  day_open boolean,
  configuration jsonb not null default '{}'::jsonb check (jsonb_typeof(configuration) = 'object'),
  primary key (run_id, id),
  unique (run_id, source_key)
);

create table v1_shadow.participants (
  run_id uuid not null,
  id uuid not null,
  season_id uuid not null,
  trainer_id uuid not null,
  division text,
  seed_order integer check (seed_order is null or seed_order >= 0),
  flags jsonb not null default '{}'::jsonb check (jsonb_typeof(flags) = 'object'),
  primary key (run_id, id),
  unique (run_id, season_id, trainer_id),
  foreign key (run_id, season_id) references v1_shadow.seasons(run_id, id) on delete restrict,
  foreign key (run_id, trainer_id) references v1_shadow.trainers(run_id, id) on delete restrict
);

create table v1_shadow.saves (
  run_id uuid not null,
  id uuid not null,
  trainer_id uuid,
  source_save_id text not null,
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  filename text,
  source_created_at text,
  content bytea not null,
  parsed jsonb not null default '{}'::jsonb check (jsonb_typeof(parsed) = 'object'),
  primary key (run_id, id),
  unique (run_id, source_save_id),
  unique (run_id, id, trainer_id),
  foreign key (run_id, trainer_id) references v1_shadow.trainers(run_id, id) on delete restrict,
  constraint saves_content_hash check (encode(pg_catalog.sha256(content), 'hex') = sha256)
);

create table v1_shadow.progress (
  run_id uuid not null,
  id uuid not null,
  season_id uuid not null,
  trainer_id uuid not null,
  save_id uuid,
  badge_count integer check (badge_count is null or badge_count >= 0),
  champion_defeated boolean,
  visible_deaths integer check (visible_deaths is null or visible_deaths >= 0),
  source_kind text not null,
  primary key (run_id, id),
  unique (run_id, season_id, trainer_id),
  foreign key (run_id, season_id) references v1_shadow.seasons(run_id, id) on delete restrict,
  foreign key (run_id, trainer_id) references v1_shadow.trainers(run_id, id) on delete restrict,
  foreign key (run_id, season_id, trainer_id) references v1_shadow.participants(run_id, season_id, trainer_id) on delete restrict,
  foreign key (run_id, save_id, trainer_id) references v1_shadow.saves(run_id, id, trainer_id) on delete restrict,
  constraint progress_observation_requires_save check (
    save_id is not null or (badge_count is null and champion_defeated is null and visible_deaths is null)
  )
);

create table v1_shadow.wallets (
  run_id uuid not null,
  id uuid not null,
  season_id uuid not null,
  trainer_id uuid not null,
  badge_earnings numeric check (badge_earnings >= 0 and badge_earnings not in ('NaN'::numeric, 'Infinity'::numeric)),
  league_earnings numeric check (league_earnings >= 0 and league_earnings not in ('NaN'::numeric, 'Infinity'::numeric)),
  completion_earnings numeric check (completion_earnings >= 0 and completion_earnings not in ('NaN'::numeric, 'Infinity'::numeric)),
  spend numeric check (spend >= 0 and spend not in ('NaN'::numeric, 'Infinity'::numeric)),
  sanctions numeric check (sanctions >= 0 and sanctions not in ('NaN'::numeric, 'Infinity'::numeric)),
  balance numeric check (balance >= 0 and balance not in ('NaN'::numeric, 'Infinity'::numeric)),
  known boolean not null default false,
  badge_high_water integer,
  primary key (run_id, id),
  unique (run_id, season_id, trainer_id),
  foreign key (run_id, season_id) references v1_shadow.seasons(run_id, id) on delete restrict,
  foreign key (run_id, trainer_id) references v1_shadow.trainers(run_id, id) on delete restrict,
  foreign key (run_id, season_id, trainer_id) references v1_shadow.participants(run_id, season_id, trainer_id) on delete restrict,
  constraint wallet_known_consistency check (
    (not known and balance is null)
    or (known and badge_earnings is not null and league_earnings is not null
      and completion_earnings is not null and spend is not null and sanctions is not null
      and balance is not null
      and balance = greatest(0::numeric, badge_earnings + league_earnings + completion_earnings - spend - sanctions))
  ),
  constraint wallet_badge_high_water_nonnegative check (badge_high_water is null or badge_high_water >= 0)
);

create table v1_shadow.purchases (
  run_id uuid not null,
  id uuid not null,
  season_id uuid,
  trainer_id uuid,
  source_purchase_id text not null,
  item text not null,
  price numeric not null,
  status text not null,
  day_number integer,
  source_created_at text,
  primary key (run_id, id),
  unique (run_id, source_purchase_id),
  foreign key (run_id, season_id) references v1_shadow.seasons(run_id, id) on delete restrict,
  foreign key (run_id, trainer_id) references v1_shadow.trainers(run_id, id) on delete restrict,
  constraint purchase_price_nonnegative check (price >= 0 and price not in ('NaN'::numeric, 'Infinity'::numeric))
);

create table v1_shadow.cups (
  run_id uuid not null,
  id uuid not null,
  season_id uuid,
  source_key text not null,
  format text,
  round integer check (round is null or round >= 1),
  max_rounds integer check (max_rounds is null or max_rounds >= 1),
  rules_version text,
  source_state jsonb not null default '{}'::jsonb check (jsonb_typeof(source_state) = 'object'),
  primary key (run_id, id),
  unique (run_id, source_key),
  constraint cup_round_bound check (round is null or max_rounds is null or round <= max_rounds),
  foreign key (run_id, season_id) references v1_shadow.seasons(run_id, id) on delete restrict
);

create table v1_shadow.cup_participants (
  run_id uuid not null,
  id uuid not null,
  cup_id uuid not null,
  trainer_id uuid not null,
  seed_order integer check (seed_order is null or seed_order >= 0),
  wins integer not null default 0 check (wins >= 0),
  losses integer not null default 0 check (losses >= 0),
  byes integer not null default 0 check (byes >= 0),
  primary key (run_id, id),
  unique (run_id, cup_id, trainer_id),
  foreign key (run_id, cup_id) references v1_shadow.cups(run_id, id) on delete restrict,
  foreign key (run_id, trainer_id) references v1_shadow.trainers(run_id, id) on delete restrict
);

create table v1_shadow.cup_matches (
  run_id uuid not null,
  id uuid not null,
  cup_id uuid not null,
  round integer not null check (round >= 1),
  position integer not null check (position >= 0),
  first_trainer_id uuid,
  second_trainer_id uuid,
  winner_id uuid,
  primary key (run_id, id),
  unique (run_id, cup_id, round, position),
  foreign key (run_id, cup_id) references v1_shadow.cups(run_id, id) on delete restrict,
  foreign key (run_id, cup_id, first_trainer_id) references v1_shadow.cup_participants(run_id, cup_id, trainer_id) on delete restrict,
  foreign key (run_id, cup_id, second_trainer_id) references v1_shadow.cup_participants(run_id, cup_id, trainer_id) on delete restrict,
  foreign key (run_id, cup_id, winner_id) references v1_shadow.cup_participants(run_id, cup_id, trainer_id) on delete restrict,
  constraint cup_match_has_player check (first_trainer_id is not null or second_trainer_id is not null),
  constraint cup_match_distinct_players check (first_trainer_id is null or second_trainer_id is null or first_trainer_id <> second_trainer_id),
  constraint cup_match_winner_is_player check (
    winner_id is null or winner_id is not distinct from first_trainer_id or winner_id is not distinct from second_trainer_id
  )
);

create table v1_shadow.exclusions (
  run_id uuid not null references v1_shadow.runs(id) on delete restrict,
  id uuid not null,
  source_key text not null,
  reason text not null,
  payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
  primary key (run_id, id),
  unique (run_id, source_key)
);

-- The migration runner uses the database owner over a single transaction. Browser
-- roles receive neither schema usage nor table privileges; no RPC is exposed.
do $$
declare t text;
begin
  foreach t in array array['runs','batches','records','identities','trainers','seasons','participants','saves','progress','wallets','purchases','cups','cup_participants','cup_matches','exclusions'] loop
    execute format('alter table v1_shadow.%I enable row level security', t);
    execute format('alter table v1_shadow.%I force row level security', t);
    execute format('revoke all on v1_shadow.%I from public, anon, authenticated, service_role', t);
  end loop;
end $$;

commit;
