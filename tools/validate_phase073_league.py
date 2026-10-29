"""Rollback-only 073 acceptance on the caller's isolated PostgreSQL.

Uses the actual close RPC, authoritative context, frozen snapshots, ledger,
purchase origin trigger and general read. No remote connection or save bytes.
"""

from copy import deepcopy
import json
from uuid import UUID

from app.application.matchdays import plan_close
from tools.validate_phase21_native import PARSED, PLAYER, SAVE, SEASON, SHA, TRAINER
from tools.validate_phase21_native import sql as native_sql

CONFIG = "aaaaaaaa-0073-4000-8000-000000000001"
DAY = "aaaaaaaa-0073-4000-8000-000000000002"
DIVISION = "aaaaaaaa-0073-4000-8000-000000000003"
REVISION = "aaaaaaaa-0073-4000-8000-000000000004"


def literal(value):
    return "'" + json.dumps(value, separators=(",", ":")).replace("'", "''") + "'::jsonb"


def fixture(total=1):
    ids = [PLAYER] + [str(UUID(int=0x73000000000040008000000000000000 + i)) for i in range(2, 7)]
    trainers = [TRAINER] + [str(UUID(int=0x74000000000040008000000000000000 + i)) for i in range(2, 7)]
    config = dict(id=CONFIG, name="073 fixture", effective_from_matchday=1, total_matchdays=total,
                  division_sizes={"A": 6}, promotion_relegation_count=0,
                  scoring_json={str(i): 7-i for i in range(1, 7)},
                  coin_rewards_json={str(i): 17 if total == 1 else 31-2*i for i in range(1, 7)},
                  rules_json=dict(team_lock_required=False, last_b_gets_steal=False),
                  scoring_mode="single_round_robin_v1" if total == 1 else "position_v1", death_penalty_per_mon="0.1")
    players = [dict(id=pid, trainer_id=tid, ranking_key="fixture-"+str(i), division="A",
                    dead_count=5 if i == 0 else 0, points_reduction="0", coins_reduction=0)
               for i, (pid, tid) in enumerate(zip(ids, trainers))]
    matches = [dict(id=str(UUID(int=0x75000000000040008000000000000000 + 10*i+j)),
                    player_a_id=a, player_b_id=b, winner_id=a, division="A")
               for i, a in enumerate(ids) for j, b in enumerate(ids) if j > i]
    context = dict(inputs=dict(season_id=SEASON, day_id=DAY, number=1, results_revision=0,
                              config=config, players=players, matches=matches),
                   ranking_rule="wins_adjusted_deaths_v1", existing_next_promotions=False,
                   catalog=[], purchase_history=[], promotion_history=[])
    boxes = [dict(box_number=b, slots=[dict(slot_number=s, pokemon={"species":"Pikachu"}
                   if (b == 7 and s <= 3) or (b == 8 and s == 1) else None) for s in range(1,31)])
             for b in range(1,9)]
    seed = native_sql().split("select case when public.observed_native_progress")[0]
    seed = seed.replace("begin;", "begin; update public.seasons set status='draft' where status='active';")
    seed += f"\nupdate public.trainers set is_admin=true where id='{TRAINER}';\n"
    for i, tid in enumerate(trainers[1:], 1):
        seed += f"insert into public.trainers(id,display_name,slug) values('{tid}','073 Fixture {i}','073-fixture-{i}');\n"
    for pid, tid in zip(ids[1:], trainers[1:]):
        seed += f"insert into public.season_players(id,season_id,trainer_id,status) values('{pid}','{SEASON}','{tid}','active');\n"
    seed += f"""
insert into public.season_player_stats(season_player_id,season_id,trainer_id)
  select id,season_id,trainer_id from public.season_players where season_id='{SEASON}' on conflict do nothing;
update public.season_player_stats set revived_after_wipe=1 where season_player_id='{PLAYER}';
update public.season_players set dead_box_number=7 where id='{PLAYER}';
update public.parsed_saves set payload=jsonb_set(payload,'{{boxes}}',{literal(boxes)}) where id='{PARSED}';
insert into public.pokemon_identity_revisions(id,season_id,trainer_id,save_file_id,parsed_save_id,
  revision_number,capture_stream_id,capture_sequence,input_signature)
  values('{REVISION}','{SEASON}','{TRAINER}','{SAVE}','{PARSED}',1,gen_random_uuid(),1,'{SHA}');
insert into public.pokemon_observations(revision_id,season_id,trainer_id,save_file_id,source,box_number,slot_number,
  outcome,candidate_entity_ids,evidence,candidate_key,observation_signature)
  select '{REVISION}','{SEASON}','{TRAINER}','{SAVE}','box',b,s,'AMBIGUOUS',array[gen_random_uuid()],
    '{{}}'::jsonb,lpad(b::text||s::text,64,'0'),lpad(b::text||s::text,64,'0') from (values(7,1),(7,2),(7,3),(8,1)) v(b,s);
insert into public.season_config_versions(id,season_id,version_number,name,effective_from_matchday,total_matchdays,
  division_count,division_sizes,scoring_json,coin_rewards_json,rules_json)
  values('{CONFIG}','{SEASON}',1,'073 fixture',1,{total},1,'{{"A":6}}',
    {literal(config['scoring_json'])},{literal(config['coin_rewards_json'])},{literal(config['rules_json'])});
insert into public.divisions(id,season_id,code,name,tier_order) values('{DIVISION}','{SEASON}','A','Liga',1);
insert into public.division_memberships(season_id,season_player_id,division_id,effective_from_matchday_number)
  select season_id,id,'{DIVISION}',1 from public.season_players where season_id='{SEASON}';
insert into public.matchdays(id,season_id,number,status,season_config_version_id,opened_at)
  values('{DAY}','{SEASON}',1,'open','{CONFIG}',now());
update public.seasons set current_matchday_id='{DAY}' where id='{SEASON}';
insert into public.season_admin_state(season_id) values('{SEASON}');
"""
    for m in matches:
        seed += f"insert into public.matches(id,season_id,matchday_id,division_id,player_a_id,player_b_id,winner_id,status) values('{m['id']}','{SEASON}','{DAY}','{DIVISION}','{m['player_a_id']}','{m['player_b_id']}','{m['winner_id']}','completed');\n"
    return seed, context, ids


def validate(pg):
    seed, context, ids = fixture()
    plan = plan_close(context)
    old_context = deepcopy(context)
    old_context['inputs']['config'].pop('scoring_mode')
    old_context['inputs']['config'].pop('death_penalty_per_mon')
    old_plan = plan_close(old_context)
    multi_seed, multi_context, _ = fixture(total=2)
    multi_plan = plan_close(multi_context)
    corrected = deepcopy(context)
    for match in corrected['inputs']['matches']:
        match['winner_id'] = match['player_b_id']
    corrected_plan = plan_close(corrected)
    changes = [dict(match_id=m['id'], winner_season_player_id=m['winner_id']) for m in corrected['inputs']['matches']]
    request = dict(actor_trainer_id=TRAINER, season_id=SEASON, resource_id=DAY,
                   idempotency_key='073-close', body=dict(expected_results_revision=0))
    checks = f"""
do $$ declare r jsonb; ctx jsonb; envelope jsonb; first_receipt jsonb; row jsonb;
begin
  begin
    perform public.single_league_common_coins('{{"1":100,"2":90}}');
    raise exception 'unequal coins accepted';
  exception when sqlstate 'PT409' then assert sqlerrm='single_league_common_coins_required',sqlerrm; end;
  assert public.single_league_common_coins('{{"1":17,"2":17}}')=17,'configured amount';
  r=public.league_general_read('{SEASON}');
  row=(select x from jsonb_array_elements(r->'rows') x where x->>'season_player_id'='{ids[2]}');
  assert (row->>'total_points')::numeric=6,format('3 wins/2 losses: %s',row);
  row=(select x from jsonb_array_elements(r->'rows') x where x->>'season_player_id'='{PLAYER}');
  assert (row->>'dead_count')::integer=3 and (row->>'dead_box_number')::integer=7,format('only Box7: %s',row);
  assert (row->>'total_points')::numeric=9.5,format('5 wins less3deaths+wipe: %s',row);
  assert not(row ? 'provisional_points'),'one direct total';
  -- A scheduled result does not contribute to live points.
  update public.matches set status='scheduled',winner_id=null where id='{context['inputs']['matches'][0]['id']}';
  row=(select x from jsonb_array_elements(public.league_general_read('{SEASON}')->'rows') x where x->>'season_player_id'='{PLAYER}');
  assert (row->>'total_points')::numeric=7.5,format('only confirmed: %s',row);
  update public.matches set status='completed',winner_id='{PLAYER}' where id='{context['inputs']['matches'][0]['id']}';
end $$;
-- First prove a pre073 frozen capture keeps its old position/death rules.
savepoint old_history;
select public.matchday_commit_close('close',{literal(request)},
  public.matchday_context_v034('close',{literal(request)})||jsonb_build_object('ranking_rule','wins_adjusted_deaths_v1'),{literal(old_plan)});
do $$ declare ctx jsonb; row jsonb; begin
  ctx=public.matchday_context('correct',{literal(request)});
  assert not(ctx#>'{{inputs,config}}' ? 'death_penalty_per_mon'),'legacy rate remains absent/frozen';
  assert not(ctx#>'{{inputs,config}}' ? 'scoring_mode'),'legacy positions remain frozen';
  row=(select x from jsonb_array_elements((select snapshot->'standings' from public.matchday_snapshots where matchday_id='{DAY}')) x where x->>'trainer_id'='{PLAYER}');
  assert (row#>>'{{penalties,dead_points_penalty}}')::numeric=1.0,format('legacy0.2: %s',row);
end $$;
rollback to savepoint old_history;
-- Actual current RPC: lock, fingerprint, validate, snapshot, ledger and rewards.
set local role service_role;
do $$ declare request jsonb={literal(request)}; ctx jsonb; envelope jsonb; receipt jsonb; row jsonb;
begin
  ctx=public.api_admin_matchday_context(jsonb_build_object('operation','close','request',request));
  assert ctx#>>'{{context,inputs,config,death_penalty_per_mon}}'='0.1','new rate frozen';
  assert ctx#>>'{{context,inputs,config,scoring_mode}}'='single_round_robin_v1','RR server mode';
  envelope=jsonb_build_object('operation','close','request',request,'input_hash',ctx->'input_hash','plan',{literal(plan)});
  receipt=public.api_admin_matchday(envelope);
  assert receipt->>'state'='closed','closed';
  assert public.api_admin_matchday(envelope)->>'replayed'='true','same receipt replay';
  assert (select count(*) from public.matchday_snapshot_revisions where matchday_id='{DAY}')=1,'one frozen revision';
  assert (select count(*) from public.coin_transactions where reward_matchday_id='{DAY}')=6,'one common reward each';
  assert (select sum(amount) from public.coin_transactions where reward_matchday_id='{DAY}')=102,'6times configured17';
  assert (select count(*) from public.purchases where origin_matchday_id='{DAY}' and status='pending')=2,'exactly2prizes';
  assert exists(select 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id
    where p.origin_matchday_id='{DAY}' and p.season_player_id='{ids[0]}' and i.code='blindar_pokemon' and p.unit_price=0),'firstshield';
  assert exists(select 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id
    where p.origin_matchday_id='{DAY}' and p.season_player_id='{ids[-1]}' and i.code='robar_pokemon' and p.unit_price=0),'laststeal';
  row=(select x from jsonb_array_elements(public.league_general_read('{SEASON}')->'rows') x where x->>'season_player_id'='{ids[2]}');
  assert (row->>'total_points')::numeric=6,format('no double add on close: %s',row);
  row=(select x from jsonb_array_elements(public.league_general_read('{SEASON}')->'rows') x where x->>'season_player_id'='{PLAYER}');
  assert (row->>'total_points')::numeric=9.5,format('no double penalty: %s',row);
end $$;
reset role;
-- Explicit audited correction swaps both prize owners without a second payout.
do $$ declare request jsonb; ctx jsonb; envelope jsonb; receipt jsonb; original jsonb;
begin
  select snapshot into original from public.matchday_snapshot_revisions where matchday_id='{DAY}' and revision=1;
  request=jsonb_build_object('actor_trainer_id','{TRAINER}','season_id','{SEASON}','resource_id','{DAY}',
    'idempotency_key','073-correct','body',jsonb_build_object('expected_snapshot_revision',1,
      'reason','Synthetic audited correction','results',{literal(changes)}));
  ctx=public.api_admin_matchday_context(jsonb_build_object('operation','correct','request',request));
  envelope=jsonb_build_object('operation','correct','request',request,'input_hash',ctx->'input_hash','plan',{literal(corrected_plan)});
  receipt=public.api_admin_matchday(envelope);
  assert public.api_admin_matchday(envelope)->>'replayed'='true','correction replay';
  assert (select count(*) from public.coin_transactions where reward_matchday_id='{DAY}')=6,'no second payout';
  assert (select count(*) from public.purchases where origin_matchday_id='{DAY}' and status='pending')=2,'two current prizes';
  assert (select count(*) from public.purchases where origin_matchday_id='{DAY}' and status='cancelled')=2,'prior prizes audited cancelled';
  assert (select snapshot from public.matchday_snapshot_revisions where matchday_id='{DAY}' and revision=1)=original,'original history immutable';
  assert not has_function_privilege('authenticated','public.matchday_commit_close(text,jsonb,jsonb,jsonb)','EXECUTE'),'no browser commit';
  assert not has_function_privilege('anon','public.single_league_common_coins(jsonb)','EXECUTE'),'no anon helper';
end $$;
rollback;
"""
    pg.sql(seed + checks, user="supabase_admin")
    multi_checks = f"""
-- Multiple matchdays retain positional points and positional coin rewards.
do $$ declare ctx jsonb; row jsonb; request jsonb={literal(request)}; begin
  ctx=public.api_admin_matchday_context(jsonb_build_object('operation','close','request',request));
  assert ctx#>>'{{context,inputs,config,scoring_mode}}'='position_v1','multiday position mode';
  perform public.api_admin_matchday(jsonb_build_object('operation','close','request',request,
    'input_hash',ctx->'input_hash','plan',{literal(multi_plan)}));
  row=(select x from jsonb_array_elements((select snapshot->'standings' from public.matchday_snapshots where matchday_id='{DAY}')) x
    where x->>'trainer_id'='{PLAYER}');
  assert (row->>'points_awarded')::integer=6 and (row->>'coins_awarded')::integer=29,format('position awards: %s',row);
  assert (row#>>'{{penalties,dead_points_penalty}}')::numeric=0.5,'prospective0.1 for multiday';
  assert (select count(*) from public.matchdays where season_id='{SEASON}')=2,'next day preserved';
  assert not exists(select 1 from public.purchases where origin_matchday_id='{DAY}'),'no single-day prizes';
end $$;
rollback;
"""
    pg.sql(multi_seed + multi_checks, user="supabase_admin")
    return ("PASS: RR confirmed live points (3 wins=6), participant Box7, 3deaths+1wipe=-0.5; multiday positional points/coins; "
            "legacy frozen0.2; new rate/mode server-owned; actual close/replay exactly one common configured "
            "coin payout and two audited prize purchases; no double points/penalties; explicit correction/replay "
            "preserves first revision and compensates prizes without repayment; no browser grants")
