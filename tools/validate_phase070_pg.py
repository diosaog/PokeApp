"""Focused rollback-only checks for 070, on a disposable Supabase-shaped cluster.

Synthetic rows only. Proves: every participant keeps Box 8 unless an
administrator changes it (audited, idempotent, refused for others, invalid
boxes and finished seasons); the League counts the participant's own dead box
and nothing else; it shows ONE total that already includes deaths, wipe
revivals and sanctions; after a closing that total equals the official one,
so nothing is subtracted twice; the redefined rules no longer name Box 8; no
new browser privilege.
"""

import json

from tools.validate_phase21_native import PARSED, PLAYER, SAVE, SEASON, SHA, TRAINER
from tools.validate_phase21_native import sql as native_sql

ADMIN = "66666666-6666-6666-6666-666666666666"
OTHER = "77777777-7777-7777-7777-777777777777"
OTHER_PLAYER = "88888888-8888-8888-8888-888888888888"
REVISION = "99999999-9999-9999-9999-999999999999"
CONFIG = "aaaaaaaa-0000-4000-8000-000000000001"
DAY = "aaaaaaaa-0000-4000-8000-000000000002"


def _boxes():
    """Box 7 holds two Pokémon, Box 8 one: which box counts decides the total."""
    occupied = {7: (1, 2), 8: (1,)}
    return [
        {
            "box_number": number,
            "slots": [
                {
                    "slot_number": slot,
                    "pokemon": {"species": "Pikachu"} if slot in occupied.get(number, ()) else None,
                }
                for slot in range(1, 31)
            ],
        }
        for number in range(1, 9)
    ]


def _observations():
    rows = []
    for box, slots in ((7, (1, 2)), (8, (1,))):
        for slot in slots:
            key = f"{box:02d}{slot:02d}".ljust(64, "0")
            rows.append(
                f"('{REVISION}','{SEASON}','{TRAINER}','{SAVE}','box',{box},{slot},'AMBIGUOUS',"
                f"array[gen_random_uuid()],'{{}}'::jsonb,'{key}','{key}')"
            )
    return ",\n  ".join(rows)


def validate(pg):
    seed = native_sql().split("select case when public.observed_native_progress")[0]
    seed = seed.replace(
        "begin;",
        "begin; update public.seasons set status='draft' where status='active';",
    )
    boxes = json.dumps(_boxes()).replace("'", "''")
    checks = f"""
insert into public.trainers(id,display_name,slug,auth_user_id,is_admin) values
  ('{ADMIN}','Admin Fixture','admin-fixture',gen_random_uuid(),true),
  ('{OTHER}','Other Fixture','other-fixture',gen_random_uuid(),false);
insert into public.season_players(id,season_id,trainer_id,status) values ('{OTHER_PLAYER}','{SEASON}','{OTHER}','active');
insert into public.season_admin_state(season_id) values ('{SEASON}');
insert into public.season_config_versions(id,season_id,version_number,name,effective_from_matchday,total_matchdays,division_count)
  values ('{CONFIG}','{SEASON}',1,'070',1,4,1);
update public.parsed_saves set payload=jsonb_set(payload,'{{boxes}}','{boxes}'::jsonb) where id='{PARSED}';
insert into public.pokemon_identity_revisions(id,season_id,trainer_id,save_file_id,parsed_save_id,
  revision_number,capture_stream_id,capture_sequence,input_signature)
  values ('{REVISION}','{SEASON}','{TRAINER}','{SAVE}','{PARSED}',1,gen_random_uuid(),1,'{SHA}');
insert into public.pokemon_observations(revision_id,season_id,trainer_id,save_file_id,source,box_number,slot_number,
  outcome,candidate_entity_ids,evidence,candidate_key,observation_signature) values
  {_observations()};
insert into public.season_player_stats(season_player_id,season_id,trainer_id)
  values ('{PLAYER}','{SEASON}','{TRAINER}') on conflict (season_player_id) do nothing;
do $$ declare result jsonb; receipt jsonb; request jsonb; row jsonb; f text;
begin
  -- 1. Everyone keeps Box 8 unless an administrator says otherwise.
  assert (select dead_box_number from public.season_players where id='{PLAYER}')=8, 'default Box 8';
  result=public.league_general_read('{SEASON}');
  row=(select r from jsonb_array_elements(result->'rows') r where r->>'trainer_id'='{TRAINER}');
  assert (row->>'dead_count')::integer=1 and (row->>'dead_box_number')::integer=8, format('Box 8 occupants: %s',row);
  assert (row->>'total_points')::numeric=-0.2, format('one death is -0.2 at once: %s',row);
  assert row->>'official_points'='0' and not (row ? 'provisional_points'), format('one total only: %s',row);
  -- The participant with 0 points sorts above the one with -0.2.
  assert result#>>'{{rows,0,trainer_id}}'='{OTHER}', format('negative totals order: %s',result);

  -- 2. The administrator moves this participant's dead box to Box 7.
  request=jsonb_build_object('actor_trainer_id','{ADMIN}','season_id','{SEASON}','resource_id','{PLAYER}',
    'idempotency_key','070-box7','body',jsonb_build_object('dead_box_number',7));
  receipt=public.api_admin_set_dead_box(request);
  assert receipt->>'state'='active' and receipt->>'replayed'='false', format('receipt %s',receipt);
  assert public.api_admin_set_dead_box(request)->>'replayed'='true', 'replay';
  assert (select dead_box_number from public.season_players where id='{PLAYER}')=7, 'Box 7 stored';
  assert (select dead_box_number from public.season_players where id='{OTHER_PLAYER}')=8, 'others unchanged';
  assert (select payload#>>'{{evidence,before}}'||'>'||(payload#>>'{{evidence,after}}') from public.activity_events
    where type='SEASON_ADMIN_DEAD_BOX' and season_id='{SEASON}')='8>7', 'audited before/after';
  begin
    perform public.api_admin_set_dead_box(jsonb_set(jsonb_set(request,'{{actor_trainer_id}}','"{OTHER}"'),'{{idempotency_key}}','"070-other"'));
    raise exception 'non-admin changed a dead box';
  exception when sqlstate 'PT403' then null; end;
  begin
    perform public.api_admin_set_dead_box(jsonb_set(jsonb_set(request,'{{body,dead_box_number}}','33'),'{{idempotency_key}}','"070-33"'));
    raise exception 'Box 33 accepted';
  exception when sqlstate 'PT422' then null; end;

  -- 3. Only Box 7 counts now; Box 8's occupant is just another box.
  result=public.league_general_read('{SEASON}');
  row=(select r from jsonb_array_elements(result->'rows') r where r->>'trainer_id'='{TRAINER}');
  assert (row->>'dead_count')::integer=2 and (row->>'total_points')::numeric=-0.4, format('Box 7: %s',row);
  assert public.purchased_revive_overlap('{SEASON}','{TRAINER}','{SAVE}')=0, 'no revive overlap';
  -- A wipe revival counts two deaths, a sanction its points, at once.
  update public.season_player_stats set revived_after_wipe=1 where season_player_id='{PLAYER}';
  insert into public.penalties(season_id,trainer_id,penalty_type,amount,points_amount)
    values ('{SEASON}','{TRAINER}','points_reduction',0,1.5);
  result=public.league_general_read('{SEASON}');
  row=(select r from jsonb_array_elements(result->'rows') r where r->>'trainer_id'='{TRAINER}');
  assert (row->>'total_points')::numeric=-2.3, format('0 - 1.5 - 0.2*4: %s',row);

  -- 4. A closing records 3 points and the same cumulative deductions: the
  --    total is the official one; the closing subtracted nothing twice.
  perform set_config('session_replication_role','replica',true);
  insert into public.matchdays(id,season_id,number,status,season_config_version_id,closed_at)
    values ('{DAY}','{SEASON}',1,'closed','{CONFIG}',now());
  insert into public.matchday_snapshots(season_id,matchday_id,config_version_id,snapshot_schema_version,closed_at,snapshot)
    values ('{SEASON}','{DAY}','{CONFIG}',2,now(),jsonb_build_object('schema_version',2,'standings',jsonb_build_array(
      jsonb_build_object('trainer_id','{PLAYER}','points_awarded',3,'penalties',
        jsonb_build_object('points_reduction',1.5,'dead_points_penalty',0.8)),
      jsonb_build_object('trainer_id','{OTHER_PLAYER}','points_awarded',1,'penalties','{{}}'::jsonb))));
  perform set_config('session_replication_role','origin',true);
  -- Trials create sanctions without a matchday: every later closing keeps them.
  result=public.league_general_read('{SEASON}');
  row=(select r from jsonb_array_elements(result->'rows') r where r->>'trainer_id'='{TRAINER}');
  assert (row->>'official_points')::numeric=0.7 and (row->>'total_points')::numeric=0.7,
    format('3 - 1.5 - 0.8 once: %s',row);
  -- A new death after the closing counts at once, from the closed figure.
  insert into public.pokemon_observations(revision_id,season_id,trainer_id,save_file_id,source,box_number,slot_number,
    outcome,candidate_entity_ids,evidence,candidate_key,observation_signature)
    values ('{REVISION}','{SEASON}','{TRAINER}','{SAVE}','box',7,3,'AMBIGUOUS',array[gen_random_uuid()],'{{}}'::jsonb,
      repeat('7',64),repeat('7',64));
  result=public.league_general_read('{SEASON}');
  row=(select r from jsonb_array_elements(result->'rows') r where r->>'trainer_id'='{TRAINER}');
  assert (row->>'total_points')::numeric=0.5 and (row->>'official_points')::numeric=0.7,
    format('one more death: 3 - 1.5 - 0.2*5: %s',row);
  -- Finished seasons show the official figure only.
  update public.seasons set status='finished',finished_at=now() where id='{SEASON}';
  result=public.league_general_read('{SEASON}');
  row=(select r from jsonb_array_elements(result->'rows') r where r->>'trainer_id'='{TRAINER}');
  assert (row->>'total_points')::numeric=0.7, format('a finished season keeps the official total: %s',row);
  begin
    perform public.api_admin_set_dead_box(jsonb_set(request,'{{idempotency_key}}','"070-done"'));
    raise exception 'finished season changed';
  exception when sqlstate 'PT409' then assert sqlerrm='season_not_editable', sqlerrm; end;

  -- 5. No redefined rule names Box 8; nothing new for browsers.
  foreach f in array array['public.matchday_context_v034(text,jsonb)','public.purchased_revive_overlap(uuid,uuid,uuid)',
      'public.initial_assignment_observations_v067(uuid)','public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid)',
      'public.api_prepare_transfer(jsonb)','public.league_general_read(uuid)'] loop
    assert pg_get_functiondef(f::regprocedure) !~ 'box_number *(=|<>) *8|''8''::jsonb', format('%s still names Box 8',f);
  end loop;
  assert not has_function_privilege('authenticated','public.api_admin_set_dead_box(jsonb)','EXECUTE'), 'private command';
  assert not has_function_privilege('anon','public.participant_dead_box(uuid,uuid)','EXECUTE'), 'private helper';
  assert has_function_privilege('service_role','public.api_admin_set_dead_box(jsonb)','EXECUTE'), 'API command';
  assert not has_column_privilege('authenticated','public.season_players','dead_box_number','UPDATE'), 'no browser write';
end $$;
-- The API's own role runs the read and the command with its grants.
update public.seasons set status='active',finished_at=null where id='{SEASON}';
set local role service_role;
do $$ begin
  assert public.league_general_read('{SEASON}')#>>'{{rows,0,total_points}}' is not null, 'service_role read';
  assert public.api_admin_set_dead_box(jsonb_build_object('actor_trainer_id','{ADMIN}','season_id','{SEASON}',
    'resource_id','{OTHER_PLAYER}','idempotency_key','070-role','body',jsonb_build_object('dead_box_number',6)))->>'state'='active',
    'service_role command';
end $$;
reset role;
rollback;
"""
    pg.sql(seed + checks, user="supabase_admin")
    return (
        "PASS: Box 8 by default for everyone; admin-only audited change to Box 7 "
        "(replay, non-admin/invalid/finished refused); only the participant's dead box "
        "counts; one live total with deaths, wipe revivals and sanctions; after a "
        "closing it equals the official total (no double subtraction); finished "
        "seasons official only; no Box 8 left in the rules; no browser privilege"
    )
