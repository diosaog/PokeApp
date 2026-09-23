from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MIGRATIONS = sorted((ROOT / "supabase" / "v2" / "migrations").glob("*.sql"))
BOOTSTRAP_SQL = ROOT / "supabase" / "v2" / "bootstrap.sql"
RESET_SQL = ROOT / "supabase" / "v2" / "reset_dev.sql"
SEED_SQL = ROOT / "supabase" / "v2" / "migrations" / "009_seed.sql"


SUPABASE_ROLE_MOCK_SQL = r"""
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;

  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;

  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin bypassrls;
  else
    alter role service_role bypassrls;
  end if;
end;
$$;
"""


EXPECTED_TABLES = [
    "admin_operation_receipts",
    "season_admin_state",
    "activity_events",
    "app_settings",
    "coin_transactions",
    "cup_matches",
    "cup_participants",
    "cup_standings",
    "cups",
    "division_memberships",
    "divisions",
    "hall_of_fame_entries",
    "matchday_movements",
    "matchday_snapshots",
    "matchdays",
    "matches",
    "parsed_saves",
    "penalties",
    "pokemon_flags",
    "pokemon_entities",
    "pokemon_identity_revisions",
    "pokemon_observations",
    "pokemon_entity_flags",
    "purchases",
    "redemptions",
    "robbery_cycles",
    "save_files",
    "season_archive_snapshots",
    "season_config_versions",
    "season_player_stats",
    "season_players",
    "seasons",
    "shop_items",
    "shop_promotions",
    "team_locks",
    "trainer_flags",
    "trainers",
    "trial_cases",
    "trial_votes",
]


VALIDATION_SQL = r"""
\set ON_ERROR_STOP on

create or replace function public.__pokeapp_expect_failure(p_sql text, p_label text)
returns void
language plpgsql
as $$
begin
  execute p_sql;
  raise exception 'Expected failure did not happen: %', p_label;
exception
  when others then
    if sqlstate = 'P0001' and sqlerrm like 'Expected failure did not happen:%' then
      raise;
    end if;
end;
$$;

do $$
declare
  missing text[];
  missing_rls text[];
  actual_count integer;
begin
  select array_agg(t order by t)
  into missing
  from unnest(array[__EXPECTED_TABLES__]) as expected(t)
  where not exists (
    select 1
    from information_schema.tables
    where table_schema = 'public'
      and table_name = expected.t
  );

  if missing is not null then
    raise exception 'Missing V2 tables: %', missing;
  end if;

  select count(*)
  into actual_count
  from information_schema.tables
  where table_schema = 'public'
    and table_name = any(array[__EXPECTED_TABLES__]);

  if actual_count <> __EXPECTED_COUNT__ then
    raise exception 'Expected % V2 tables, found %', __EXPECTED_COUNT__, actual_count;
  end if;

  select array_agg(expected.t order by expected.t)
  into missing_rls
  from unnest(array[__EXPECTED_TABLES__]) as expected(t)
  where not exists (
    select 1
    from pg_class as c
    join pg_namespace as n
      on n.oid = c.relnamespace
    where n.nspname = 'public'
      and c.relname = expected.t
      and c.relkind = 'r'
      and c.relrowsecurity = true
  );

  if missing_rls is not null then
    raise exception 'V2 tables without RLS enabled: %', missing_rls;
  end if;
end;
$$;

do $$
declare
  missing text[];
begin
  select array_agg(c order by c)
  into missing
  from unnest(array[
    'uq_seasons_one_active',
    'uq_season_players_season_trainer',
    'uq_matchdays_season_number',
    'uq_team_locks_matchday_trainer',
    'uq_hall_of_fame_season_competition',
    'uq_activity_events_dedupe_key',
    'uq_parsed_saves_file_parser'
  ]) as expected(c)
  where not exists (
    select 1
    from pg_constraint
    where conname = expected.c
    union all
    select 1
    from pg_indexes
    where schemaname = 'public'
      and indexname = expected.c
  );

  if missing is not null then
    raise exception 'Missing critical constraints/indexes: %', missing;
  end if;
end;
$$;

do $$
declare
  bad text[];
begin
  select array_agg(table_name || '.' || column_name order by table_name, column_name)
  into bad
  from information_schema.columns
  where table_schema = 'public'
    and column_name in (
      'created_at',
      'updated_at',
      'started_at',
      'finished_at',
      'archived_at',
      'discarded_at',
      'opened_at',
      'closed_at',
      'locked_at',
      'deadline_at',
      'uploaded_at',
      'parsed_at',
      'finalized_at',
      'resolved_at',
      'redeemed_at',
      'purchased_at',
      'announced_at',
      'activates_at',
      'ends_at',
      'exhausted_at'
    )
    and data_type <> 'timestamp with time zone';

  if bad is not null then
    raise exception 'Non-timestamptz timestamp columns: %', bad;
  end if;
end;
$$;

do $fixture$
declare
  anto uuid;
  victor uuid;
  admin uuid;
  season uuid;
  season_two uuid;
  cfg uuid;
  division_a uuid;
  division_b uuid;
  sp_anto uuid;
  sp_victor uuid;
  matchday uuid;
  match_id uuid;
  save_anto uuid;
  save_victor uuid;
  shop_item uuid;
  promo uuid;
  purchase_id uuid;
  hall_id uuid;
  activity_id uuid;
  parsed_id uuid;
  balance integer;
  cnt integer;
  json_value text;
begin
  insert into public.trainers (display_name, slug, auth_user_id, is_admin)
  values
    ('Validation Anto', 'validation_anto', '00000000-0000-0000-0000-000000000101', false),
    ('Validation Victor', 'validation_victor', '00000000-0000-0000-0000-000000000102', false),
    ('Validation Admin', 'validation_admin', '00000000-0000-0000-0000-000000000103', true);

  select id into anto from public.trainers where slug = 'validation_anto';
  select id into victor from public.trainers where slug = 'validation_victor';
  select id into admin from public.trainers where slug = 'validation_admin';

  if anto is null or victor is null or admin is null then
    raise exception 'UUID default/insert failed for trainers';
  end if;

  perform public.__pokeapp_expect_failure(
    $$insert into public.trainers (display_name, slug, auth_user_id)
      values ('Dup Auth', 'dup_auth_validation', '00000000-0000-0000-0000-000000000101')$$,
    'trainers.auth_user_id unique'
  );

  insert into public.seasons (name, status, started_at, created_by_trainer_id)
  values ('Validation Season', 'active', now(), anto)
  returning id into season;

  perform public.__pokeapp_expect_failure(
    $$insert into public.seasons (name, status, started_at)
      values ('Second Active', 'active', now())$$,
    'one active season'
  );

  insert into public.seasons (name, status)
  values ('Validation Draft Season', 'draft')
  returning id into season_two;

  insert into public.season_players (season_id, trainer_id, seed_order)
  values
    (season, anto, 1),
    (season, victor, 2);

  select id into sp_anto from public.season_players where season_id = season and trainer_id = anto;
  select id into sp_victor from public.season_players where season_id = season and trainer_id = victor;

  perform public.__pokeapp_expect_failure(
    format('insert into public.season_players (season_id, trainer_id) values (%L, %L)', season, anto),
    'duplicate trainer in season'
  );

  insert into public.season_player_stats (season_player_id, season_id, trainer_id, badges_count)
  values (sp_anto, season, anto, 4);

  insert into public.trainer_flags (season_id, trainer_id, season_player_id, flag_type, payload)
  values (season, victor, sp_victor, 'robbed', '{"source": "validation"}'::jsonb);

  insert into public.pokemon_flags (season_id, trainer_id, season_player_id, fingerprint, flag_type, payload)
  values (season, anto, sp_anto, 'validation-pokemon-fingerprint', 'shielded', '{"reason": "validation"}'::jsonb);

  insert into public.season_config_versions (
    season_id,
    version_number,
    name,
    effective_from_matchday,
    total_matchdays,
    division_count,
    promotion_relegation_count,
    scoring_json,
    coin_rewards_json,
    rules_json,
    created_by_trainer_id
  )
  values (
    season,
    1,
    'Validation Config',
    1,
    4,
    2,
    1,
    '{"1": 9, "2": 8}'::jsonb,
    '{"1": 15, "2": 14}'::jsonb,
    '{"team_lock_required": true}'::jsonb,
    anto
  )
  returning id into cfg;

  insert into public.divisions (season_id, code, name, tier_order)
  values
    (season, 'A', 'Liga A', 1),
    (season, 'B', 'Liga B', 2);

  select id into division_a from public.divisions where season_id = season and code = 'A';
  select id into division_b from public.divisions where season_id = season and code = 'B';

  insert into public.matchdays (season_id, number, status, season_config_version_id, opened_at)
  values (season, 1, 'open', cfg, now())
  returning id into matchday;

  perform public.__pokeapp_expect_failure(
    format('insert into public.matchdays (season_id, number, status, season_config_version_id) values (%L, 1, ''scheduled'', %L)', season, cfg),
    'duplicate matchday number'
  );

  perform public.__pokeapp_expect_failure(
    format('insert into public.matchdays (season_id, number, status, season_config_version_id) values (%L, 0, ''scheduled'', %L)', season, cfg),
    'matchday number <= 0'
  );

  insert into public.division_memberships (
    season_id,
    season_player_id,
    division_id,
    effective_from_matchday_number,
    reason
  )
  values
    (season, sp_anto, division_a, 1, 'initial'),
    (season, sp_victor, division_b, 1, 'initial');

  insert into public.matches (season_id, matchday_id, division_id, player_a_id, player_b_id, winner_id, status)
  values (season, matchday, division_a, sp_anto, sp_victor, sp_anto, 'completed')
  returning id into match_id;

  perform public.__pokeapp_expect_failure(
    format(
      'insert into public.matches (season_id, matchday_id, division_id, player_a_id, player_b_id, winner_id, status)
       values (%L, %L, %L, %L, %L, gen_random_uuid(), ''completed'')',
      season, matchday, division_a, sp_anto, sp_victor
    ),
    'winner not one of players'
  );

  perform public.__pokeapp_expect_failure(
    format(
      'insert into public.matches (season_id, matchday_id, division_id, player_a_id, player_b_id, status)
       values (%L, %L, %L, %L, %L, ''nonsense'')',
      season, matchday, division_a, sp_anto, sp_victor
    ),
    'invalid match status'
  );

  insert into public.matchday_snapshots (
    season_id,
    matchday_id,
    config_version_id,
    closed_at,
    snapshot,
    created_by_trainer_id
  )
  values (
    season,
    matchday,
    cfg,
    now(),
    '{"schema_version": 1, "standings": [{"trainer": "Validation Anto", "points": 9}]}'::jsonb,
    anto
  );

  insert into public.matchday_movements (
    season_id,
    matchday_id,
    season_player_id,
    from_division_id,
    to_division_id,
    movement_type
  )
  values (season, matchday, sp_victor, division_b, division_a, 'promotion');

  insert into public.shop_items (code, name, category, description, base_price)
  values ('validation_item', 'Validation Item', 'competitivos', 'Fixture item', 5)
  returning id into shop_item;

  perform public.__pokeapp_expect_failure(
    $$insert into public.shop_items (code, name, category, base_price)
      values ('validation_negative_price', 'Bad Price', 'competitivos', -1)$$,
    'negative shop price'
  );

  insert into public.shop_promotions (
    season_id,
    matchday_id,
    shop_item_id,
    promotion_type,
    status,
    base_price,
    effective_price,
    stock_total,
    stock_used,
    dedupe_key,
    announced_at,
    activates_at
  )
  values (season, matchday, shop_item, 'normal', 'active', 5, 3, 2, 0, 'validation-promo-1', now(), now())
  returning id into promo;

  perform public.__pokeapp_expect_failure(
    format(
      'insert into public.shop_promotions (season_id, matchday_id, shop_item_id, promotion_type, base_price, effective_price, stock_total, stock_used)
       values (%L, %L, %L, ''normal'', 5, 3, 1, 2)',
      season, matchday, shop_item
    ),
    'stock_used > stock_total'
  );

  insert into public.purchases (season_id, trainer_id, season_player_id, shop_item_id, promotion_id, quantity, unit_price)
  values (season, anto, sp_anto, shop_item, promo, 1, 5)
  returning id into purchase_id;

  insert into public.purchases (season_id, trainer_id, season_player_id, shop_item_id, quantity, unit_price)
  values (season, victor, sp_victor, shop_item, 1, 5);

  perform public.__pokeapp_expect_failure(
    format(
      'insert into public.purchases (season_id, trainer_id, season_player_id, shop_item_id, quantity, unit_price)
       values (%L, %L, %L, %L, 0, 5)',
      season, anto, sp_anto, shop_item
    ),
    'purchase quantity <= 0'
  );

  insert into public.redemptions (purchase_id, season_id, trainer_id, season_player_id, shop_item_id, payload)
  values (purchase_id, season, anto, sp_anto, shop_item, '{"target": "fixture"}'::jsonb);

  insert into public.coin_transactions (season_id, trainer_id, season_player_id, amount, transaction_type, reference_type, reference_id)
  values
    (season, anto, sp_anto, 15, 'matchday_reward', 'matchday', matchday),
    (season, anto, sp_anto, -5, 'purchase', 'purchase', purchase_id),
    (season, anto, sp_anto, 2, 'admin_adjustment', 'manual', null);

  select coalesce(sum(amount), 0)
  into balance
  from public.coin_transactions
  where season_id = season
    and trainer_id = anto;

  if balance <> 12 then
    raise exception 'Coin ledger expected 12, got %', balance;
  end if;

  insert into public.save_files (season_id, trainer_id, storage_key, original_filename, sha256, parser_status, parser_version)
  values (
    season,
    anto,
    'validation/anto.sav',
    'anto.sav',
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    'parsed',
    'validator'
  )
  returning id into save_anto;

  insert into public.save_files (season_id, trainer_id, storage_key, original_filename, sha256, parser_status, parser_version)
  values (
    season,
    victor,
    'validation/victor.sav',
    'victor.sav',
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    'parsed',
    'validator'
  )
  returning id into save_victor;

  update public.season_players
  set current_save_file_id = save_anto
  where id = sp_anto;

  perform public.__pokeapp_expect_failure(
    format('update public.season_players set current_save_file_id = %L where id = %L', save_victor, sp_anto),
    'current save cannot point to another trainer'
  );

  insert into public.parsed_saves (save_file_id, parser_version, payload)
  values (save_anto, 'validator', '{"party": [{"species": "Milotic"}], "boxes": []}'::jsonb)
  returning id into parsed_id;

  insert into public.parsed_saves (save_file_id, parser_version, payload)
  values (save_victor, 'validator', '{"party": [{"species": "Crobat"}], "boxes": []}'::jsonb);

  perform public.__pokeapp_expect_failure(
    format('insert into public.parsed_saves (save_file_id, parser_version, payload) values (%L, ''validator'', ''{}''::jsonb)', save_anto),
    'parsed save duplicate parser version'
  );

  insert into public.team_locks (
    season_id,
    matchday_id,
    trainer_id,
    season_player_id,
    save_file_id,
    save_sha256,
    locked_at,
    deadline_at,
    public_team_snapshot,
    private_team_snapshot
  )
  values (
    season,
    matchday,
    anto,
    sp_anto,
    save_anto,
    'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    now(),
    now() + interval '1 day',
    '{"team": [{"species": "Milotic"}]}'::jsonb,
    '{"ivs": {"hp": 31}}'::jsonb
  );

  insert into public.team_locks (
    season_id,
    matchday_id,
    trainer_id,
    season_player_id,
    save_file_id,
    save_sha256,
    locked_at,
    deadline_at,
    public_team_snapshot,
    private_team_snapshot
  )
  values (
    season,
    matchday,
    victor,
    sp_victor,
    save_victor,
    'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    now(),
    now() + interval '1 day',
    '{"team": [{"species": "Crobat"}]}'::jsonb,
    '{"ivs": {"speed": 31}}'::jsonb
  );

  perform public.__pokeapp_expect_failure(
    format(
      'insert into public.team_locks (season_id, matchday_id, trainer_id, season_player_id, save_file_id, save_sha256, public_team_snapshot)
       values (%L, %L, %L, %L, %L, ''aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'', ''{}''::jsonb)',
      season, matchday, anto, sp_anto, save_anto
    ),
    'duplicate team lock'
  );

  insert into public.activity_events (season_id, type, actor_trainer_id, trainer_id, visibility, dedupe_key, context, payload)
  values (
    season,
    'SAVE_UPLOADED',
    anto,
    anto,
    'public',
    'validation-activity-1',
    '{"source": "validation"}'::jsonb,
    '{"save_file_id": "fixture"}'::jsonb
  )
  returning id into activity_id;

  perform public.__pokeapp_expect_failure(
    format(
      'insert into public.activity_events (season_id, type, dedupe_key) values (%L, ''SAVE_UPLOADED'', ''validation-activity-1'')',
      season
    ),
    'activity dedupe'
  );

  insert into public.hall_of_fame_entries (season_id, competition_type, champion_trainer_id, finalist_trainer_id, team_snapshot)
  values (season, 'league', anto, victor, '{"team": [{"species": "Milotic"}]}'::jsonb)
  returning id into hall_id;

  perform public.__pokeapp_expect_failure(
    format(
      'insert into public.hall_of_fame_entries (season_id, competition_type, champion_trainer_id, team_snapshot)
       values (%L, ''league'', %L, ''{}''::jsonb)',
      season, anto
    ),
    'duplicate Hall season competition'
  );

  insert into public.season_archive_snapshots (season_id, snapshot)
  values (season, '{"final": true, "source": "validation"}'::jsonb);

  insert into public.cups (season_id, name, competition_type, format, status)
  values (season, 'Validation Cup', 'cup', 'swiss', 'active');

  insert into public.trial_cases (season_id, matchday_id, accused_trainer_id, created_by_trainer_id, title, payload)
  values (season, matchday, victor, anto, 'Validation Case', '{"case": true}'::jsonb);

  insert into public.penalties (season_id, trainer_id, matchday_id, penalty_type, amount, payload, created_by_trainer_id)
  values (season, victor, matchday, 'points', -1, '{"reason": "validation"}'::jsonb, anto);

  update public.matchdays
  set status = 'closed',
      closed_at = now()
  where id = matchday;

  update public.seasons
  set status = 'finished',
      finished_at = now()
  where id = season;

  update public.seasons
  set status = 'archived',
      archived_at = now()
  where id = season;

  select count(*)
  into cnt
  from public.season_players
  where season_id = season;
  if cnt <> 2 then
    raise exception 'Archive lost season_players, count %', cnt;
  end if;

  select count(*)
  into cnt
  from public.matchday_snapshots
  where season_id = season;
  if cnt <> 1 then
    raise exception 'Archive lost snapshots, count %', cnt;
  end if;

  select payload ->> 'party'
  into json_value
  from public.parsed_saves
  where id = parsed_id;
  if json_value is null then
    raise exception 'Parsed save JSONB roundtrip failed';
  end if;

  perform public.__pokeapp_expect_failure(
    format('delete from public.trainers where id = %L', anto),
    'trainer delete restricted'
  );

  perform public.__pokeapp_expect_failure(
    format('delete from public.seasons where id = %L', season),
    'season delete restricted'
  );

  perform public.__pokeapp_expect_failure(
    format('delete from public.save_files where id = %L', save_anto),
    'referenced save delete restricted'
  );
end;
$fixture$;

do $$
declare
  seeded_trainers integer;
  seeded_items integer;
begin
  select count(*) into seeded_trainers from public.trainers where metadata ->> 'seeded' = 'true';
  select count(*) into seeded_items from public.shop_items where metadata ->> 'seeded' = 'true';

  if seeded_trainers <> 10 then
    raise exception 'Seed idempotence trainer count expected 10, got %', seeded_trainers;
  end if;

  if seeded_items <> 61 then
    raise exception 'Seed idempotence shop item count expected 61, got %', seeded_items;
  end if;
end;
$$;

do $$
begin
  if exists (select 1 from information_schema.schemata where schema_name = 'storage') then
    if not exists (
      select 1
      from storage.buckets
      where id = 'raw-saves'
        and public = false
    ) then
      raise exception 'Supabase storage.raw-saves bucket missing or public';
    end if;
  end if;
end;
$$;

drop function public.__pokeapp_expect_failure(text, text);
"""


RLS_VALIDATION_SQL = r"""
\set ON_ERROR_STOP on

create or replace function public.__pokeapp_rls_expect_failure(p_sql text, p_label text)
returns void
language plpgsql
as $$
begin
  execute p_sql;
  raise exception 'Expected RLS failure did not happen: %', p_label;
exception
  when others then
    if sqlstate = 'P0001' and sqlerrm like 'Expected RLS failure did not happen:%' then
      raise;
    end if;
end;
$$;

reset role;
set role authenticated;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000101';

do $$
declare
  expected_trainer uuid;
  visible_count integer;
  changed_count integer;
begin
  select id into expected_trainer
  from public.public_trainers
  where slug = 'validation_anto';

  if public.current_trainer_id() <> expected_trainer then
    raise exception 'Trainer A identity resolution failed';
  end if;

  if public.is_current_user_admin() then
    raise exception 'Trainer A must not be admin';
  end if;

  select count(*) into visible_count from public.parsed_saves;
  if visible_count <> 1 then
    raise exception 'Trainer A parsed_saves count expected 1, got %', visible_count;
  end if;

  select count(*) into visible_count from public.save_files;
  if visible_count <> 1 then
    raise exception 'Trainer A save_files count expected 1, got %', visible_count;
  end if;

  select count(*) into visible_count from public.team_locks;
  if visible_count <> 1 then
    raise exception 'Trainer A direct team_locks count expected 1, got %', visible_count;
  end if;

  select count(*) into visible_count from public.public_team_locks;
  if visible_count <> 2 then
    raise exception 'Trainer A public_team_locks count expected 2, got %', visible_count;
  end if;

  select count(*) into visible_count
  from public.current_team_locks
  where private_team_snapshot is not null;
  if visible_count <> 1 then
    raise exception 'Trainer A current_team_locks private count expected 1, got %', visible_count;
  end if;

  select count(*) into visible_count from public.purchases;
  if visible_count <> 1 then
    raise exception 'Trainer A purchases count expected 1, got %', visible_count;
  end if;

  select count(*) into visible_count from public.public_coin_balances;
  if visible_count < 1 then
    raise exception 'Trainer A should see public coin balance aggregates';
  end if;

  perform public.__pokeapp_rls_expect_failure(
    'update public.seasons set name=''RLS HACK''', '026 denies trainer setup writes');
end;
$$;

select public.__pokeapp_rls_expect_failure(
  $$insert into public.coin_transactions (season_id, trainer_id, season_player_id, amount, transaction_type)
    select season_id, trainer_id, id, 1, 'admin_adjustment'
    from public.season_players
    where trainer_id = public.current_trainer_id()
    limit 1$$,
  'Trainer A cannot insert coin ledger'
);

reset role;
set role authenticated;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000102';

do $$
declare
  expected_trainer uuid;
  visible_count integer;
begin
  select id into expected_trainer
  from public.public_trainers
  where slug = 'validation_victor';

  if public.current_trainer_id() <> expected_trainer then
    raise exception 'Trainer B identity resolution failed';
  end if;

  select count(*) into visible_count from public.parsed_saves;
  if visible_count <> 1 then
    raise exception 'Trainer B parsed_saves count expected 1, got %', visible_count;
  end if;

  select count(*) into visible_count from public.purchases;
  if visible_count <> 1 then
    raise exception 'Trainer B purchases count expected 1, got %', visible_count;
  end if;

  select count(*) into visible_count
  from public.current_team_locks
  where private_team_snapshot is not null;
  if visible_count <> 1 then
    raise exception 'Trainer B private team lock count expected 1, got %', visible_count;
  end if;
end;
$$;

reset role;
set role authenticated;
set request.jwt.claim.sub = '00000000-0000-0000-0000-000000000103';

do $$
declare
  visible_count integer;
  changed_count integer;
begin
  if not public.is_current_user_admin() then
    raise exception 'Validation admin identity failed';
  end if;

  select count(*) into visible_count from public.parsed_saves;
  if visible_count <> 2 then
    raise exception 'Admin parsed_saves count expected 2, got %', visible_count;
  end if;

  select count(*) into visible_count from public.purchases;
  if visible_count <> 2 then
    raise exception 'Admin purchases count expected 2, got %', visible_count;
  end if;

  perform public.__pokeapp_rls_expect_failure(
    'update public.seasons set name=name', '026 admin direct setup writes denied');
end;
$$;

select public.__pokeapp_rls_expect_failure(
  $$insert into public.coin_transactions (season_id, trainer_id, season_player_id, amount, transaction_type)
    select season_id, trainer_id, id, 1, 'admin_adjustment'
    from public.season_players
    limit 1$$,
  'Admin direct ledger insert remains server-only'
);

reset role;
set role anon;
set request.jwt.claim.sub = '';

select public.__pokeapp_rls_expect_failure(
  $$select count(*) from public.public_trainers$$,
  'Anon cannot read public app projections before login'
);

reset role;
set role service_role;
set request.jwt.claim.sub = '';

do $$
declare
  visible_count integer;
begin
  select count(*) into visible_count from public.parsed_saves;
  if visible_count <> 2 then
    raise exception 'service_role bypass expected 2 parsed_saves, got %', visible_count;
  end if;
end;
$$;

reset role;
drop function public.__pokeapp_rls_expect_failure(text, text);
"""


def _run(command: list[str], *, env: dict[str, str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def _psql(args: argparse.Namespace, sql_file: Path) -> None:
    env = os.environ.copy()
    if args.password:
        env["PGPASSWORD"] = args.password
    command = [
        args.psql,
        "-h",
        args.host,
        "-p",
        str(args.port),
        "-U",
        args.user,
        "-d",
        args.database,
        "-v",
        "ON_ERROR_STOP=1",
        "-f",
        str(sql_file),
    ]
    _run(command, env=env)


def _psql_text(args: argparse.Namespace, sql: str) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as tmp:
        tmp.write(sql)
        sql_path = Path(tmp.name)
    try:
        _psql(args, sql_path)
    finally:
        sql_path.unlink(missing_ok=True)


def _safe_database_name(name: str) -> None:
    if name.startswith("pokeapp_v2_validation"):
        return
    raise SystemExit(
        "Refusing destructive validation against database "
        f"{name!r}. Use a database named pokeapp_v2_validation*."
    )


def _validate_team_lock_api(args: argparse.Namespace) -> None:
    fixture_dir = ROOT / "tests" / "sql"
    setup = (fixture_dir / "team_lock_setup.sql").read_text(encoding="utf-8")
    checks = (fixture_dir / "team_lock_checks.sql").read_text(encoding="utf-8")
    cleanup = (fixture_dir / "team_lock_cleanup.sql").read_text(encoding="utf-8")
    print("== Team Lock RPC, roles, snapshots, replacement and rollback ==")
    _psql_text(args, "begin;\n" + setup + checks + "\nrollback;")
    print("== Team Lock concurrent first writes ==")
    _psql_text(args, "begin;\n" + setup + "\ncommit;")
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(_psql_text, args,
                "begin; set local role service_role; select id from pokeapp_team_lock_test.run(); select pg_sleep(0.2); commit;"
            ) for _ in range(4)]
            for future in futures:
                future.result()
        _psql_text(args, """
select pokeapp_team_lock_test.assert_true((select count(*)=1 from public.team_locks), 'concurrent unique lock');
select pokeapp_team_lock_test.assert_true((select count(*)=1 from public.activity_events), 'concurrent event dedupe');
""")
    finally:
        _psql_text(args, "begin;\n" + cleanup + "\ncommit;")


def _validate_purchase_api(args: argparse.Namespace) -> None:
    fixtures = ROOT / "tests/sql"
    setup = (fixtures / "shop_context_setup.sql").read_text(encoding="utf-8") + (fixtures / "purchase_setup.sql").read_text(encoding="utf-8")
    checks = (fixtures / "purchase_checks.sql").read_text(encoding="utf-8")
    cleanup = (fixtures / "purchase_cleanup.sql").read_text(encoding="utf-8")
    _psql_text(args, "begin;\n" + setup + checks + "\nrollback;")
    print("== Purchase concurrent double-spend and idempotent first writes ==")
    _psql_text(args, "begin;\n" + setup + "update public.coin_transactions set amount=10;\ncommit;")
    try:
        # Each successful RPC holds the wallet row until its session commits.
        for same_key in (False, True):
            if same_key:
                _psql_text(args, "delete from public.activity_events; delete from public.coin_transactions where transaction_type='purchase'; delete from public.purchases;")
            with ThreadPoolExecutor(max_workers=4) as pool:
                sql = """do $$ begin
                  perform pokeapp_shop_test.buy('%s'); perform pg_sleep(0.2);
                  exception when sqlstate 'PT409' then
                    if sqlerrm <> 'insufficient_funds' then raise; end if;
                  end; $$;"""
                if same_key:
                    sql = "select pokeapp_shop_test.buy('%s'); select pg_sleep(0.2);"
                futures = [pool.submit(_psql_text, args, "begin; set local role service_role; " +
                           (sql % ("retry" if same_key else f"race-{n}")) + " commit;") for n in range(4)]
                for future in futures:
                    future.result()
            _psql_text(args, """
select pokeapp_shop_test.assert_true((select count(*)=1 from public.purchases), 'P35 single purchase');
select pokeapp_shop_test.assert_true((select sum(amount)=0 from public.coin_transactions), 'P35 no double spend');
select pokeapp_shop_test.assert_true((select count(*)=1 from public.activity_events), 'P35 single event');
""")
    finally:
        _psql_text(args, "begin;\n" + cleanup + "\ncommit;")


def _apply_migrations(args: argparse.Namespace) -> None:
    for migration in MIGRATIONS:
        _psql(args, migration)


def _apply_bootstrap(args: argparse.Namespace) -> None:
    _psql(args, BOOTSTRAP_SQL)


def _build_schema(args: argparse.Namespace) -> None:
    if args.build_source == "bootstrap":
        _apply_bootstrap(args)
        return
    _apply_migrations(args)


def _prepare_supabase_role_mocks(args: argparse.Namespace) -> None:
    _psql_text(args, SUPABASE_ROLE_MOCK_SQL)


def _render_validation_sql() -> str:
    quoted_tables = ", ".join("'" + table + "'" for table in EXPECTED_TABLES)
    return (
        VALIDATION_SQL.replace("__EXPECTED_TABLES__", quoted_tables)
        .replace("__EXPECTED_COUNT__", str(len(EXPECTED_TABLES)))
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Supabase V2 SQL against a real Postgres database.")
    parser.add_argument("--psql", required=True, help="Path to psql executable.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default="5432")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", required=True)
    parser.add_argument(
        "--allow-destructive-reset",
        action="store_true",
        help="Required. Runs supabase/v2/reset_dev.sql against the target database.",
    )
    parser.add_argument(
        "--build-source",
        choices=["migrations", "bootstrap"],
        default="migrations",
        help="SQL source used after each reset. Defaults to separate migrations.",
    )
    args = parser.parse_args()

    if not args.allow_destructive_reset:
        raise SystemExit("--allow-destructive-reset is required for this validation.")
    _safe_database_name(args.database)
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Refusing schema reset outside a local validation server.")

    print("== Prepare Supabase role mocks ==")
    _prepare_supabase_role_mocks(args)

    print("== Reset empty V2 state ==")
    _psql(args, RESET_SQL)

    print(f"== First {args.build_source} build ==")
    _build_schema(args)

    print("== Seed idempotence check ==")
    _psql(args, SEED_SQL)

    print("== Reset after first build ==")
    _psql(args, RESET_SQL)

    print(f"== Second {args.build_source} build ==")
    _build_schema(args)

    print("== Team Lock migration idempotence ==")
    _psql(args, ROOT / "supabase/v2/migrations/019_team_lock_api.sql")
    _validate_team_lock_api(args)

    print("== Current jornada / store-ban contract ==")
    # Do not replay older grants over the final 026 hardening.
    _psql_text(args, "begin;\n" + (ROOT / "tests/sql/shop_context_setup.sql").read_text(encoding="utf-8")
               + (ROOT / "tests/sql/shop_context_checks.sql").read_text(encoding="utf-8") + "\nrollback;")

    print("== Normal purchase migration idempotence and atomic fixtures ==")
    _psql(args, ROOT / "supabase/v2/migrations/021_normal_purchase_api.sql")
    # Reapplying 021 restores the original function; 022 reattaches its replay guard.
    _psql(args, ROOT / "supabase/v2/migrations/022_promotional_purchase_api.sql")
    _validate_purchase_api(args)

    print("== Promotional purchase, stock, rollback and concurrency ==")
    from tools.validate_supabase_v2_promotional_sql import validate_promotional_purchase

    _psql(args, ROOT / "supabase/v2/migrations/022_promotional_purchase_api.sql")
    validate_promotional_purchase(args, _psql_text, ROOT)

    print("== Pokemon identity: RLS, clones, flags, chronology and concurrency ==")
    from tools.validate_supabase_v2_identity_sql import validate_identity
    validate_identity(args)

    print("== Redemption: private effects, identity, concurrency and rollback ==")
    from tools.validate_supabase_v2_redemption_sql import validate_redemptions
    validate_redemptions(args, _psql_text)

    print("== Robbery/voucher: cycle, provenance, concurrency and rollback ==")
    from tools.validate_supabase_v2_robbery_sql import validate_robbery
    validate_robbery(args, _psql_text)

    print("== Season admin setup, real concurrency and exact rollback ==", flush=True)
    from tools.validate_supabase_v2_season_admin_sql import validate_season_admin
    validate_season_admin(args, _psql_text)

    print("== Real schema fixtures and introspection ==")
    with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8") as tmp:
        tmp.write(_render_validation_sql())
        validation_path = Path(tmp.name)
    try:
        _psql(args, validation_path)
    finally:
        validation_path.unlink(missing_ok=True)

    print("== Real RLS/auth fixtures ==")
    _psql_text(args, RLS_VALIDATION_SQL)

    print("Supabase V2 schema validation completed against real Postgres.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
