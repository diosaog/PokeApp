"""Focused rollback-only checks, called on the disposable production restore."""

from tools.validate_phase21_native import (
    sql as native_sql,
    TRAINER,
    SEASON,
    PLAYER,
    SAVE,
    PARSED,
    SHA,
)


def validate(pg):
    # Same synthetic native envelope as the retained 049 projection gate. This
    # validates SQL routing, not parsing or authentic-game compatibility.
    seed = native_sql().split("select case when public.observed_native_progress")[0]
    seed = seed.replace(
        "begin;",
        "begin; update public.seasons set status='draft' where status='active';",
    )
    checks = f"""
update public.trainers set is_admin=true where id='{TRAINER}';
update public.seasons set metadata='{{"initial_assignment_rule":"observed_deaths_v1"}}' where id='{SEASON}';
insert into public.season_admin_state(season_id) values ('{SEASON}');
insert into public.season_player_stats(season_player_id,season_id,trainer_id,revived_after_wipe)
values ('{PLAYER}','{SEASON}','{TRAINER}',0);
insert into public.pokemon_identity_revisions(season_id,trainer_id,save_file_id,parsed_save_id,
revision_number,capture_stream_id,capture_sequence,input_signature)
values ('{SEASON}','{TRAINER}','{SAVE}','{PARSED}',1,gen_random_uuid(),1,'{SHA}');
update public.parsed_saves set payload=jsonb_set(payload,'{{boxes}}',jsonb_build_array(jsonb_build_object(
'box_number',8,'slots',(select jsonb_agg(jsonb_build_object('slot_number',n,'pokemon',null)) from generate_series(1,30) n)))) where id='{PARSED}';
do $$ declare ctx jsonb; before_save text; receipt jsonb; request jsonb;
begin
  ctx=public.initial_assignment_inputs('{SEASON}');
  assert ctx->'ready'='false' and ctx->'blocking_reasons' ? 'opponent_missing', 'solo readiness';
  assert ctx#>>'{{players,0,observed_badges}}'='1' and ctx#>>'{{players,0,adjusted_deaths}}'='0', 'native badge/death observation';
  assert ctx#>>'{{players,0,cap_reached}}'='false', 'one badge is not two';
  update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}','[true,true,false,false,false,false,false,false]') where id='{PARSED}';
  ctx=public.initial_assignment_inputs('{SEASON}');
  assert ctx#>>'{{players,0,cap_reached}}'='true', 'native cap';
  assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0, 'native rewards stay blocked';
  update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}','[true]') where id='{PARSED}';
  ctx=public.initial_assignment_inputs('{SEASON}');
  assert ctx#>>'{{players,0,progress_state}}'='unknown', 'malformed evidence fails closed';
  begin
    perform public.championship_final_source('{SEASON}');
    raise exception 'championship unexpectedly finalized';
  exception when sqlstate 'PT409' then assert sqlerrm='competition_incomplete', 'preparation is not corrupt history'; end;
  assert public.lifecycle_precompetition_safe('{SEASON}'), 'saved preparation cancellable';
  select md5(to_jsonb(s)::text) into before_save from public.save_files s where id='{SAVE}';
  request=jsonb_build_object('actor_trainer_id','{TRAINER}','season_id','{SEASON}','operation','discard',
    'idempotency_key','synthetic-cancel','body',jsonb_build_object('expected_revision',0,'reason','Disposable proof','confirmation','DISCARD'));
  receipt=public.api_admin_season_lifecycle(request);
  assert receipt->>'state'='discarded', 'cancel result';
  assert public.api_admin_season_lifecycle(request)->>'replayed'='true', 'cancel replay';
  assert (select md5(to_jsonb(s)::text) from public.save_files s where id='{SAVE}')=before_save, 'save retained';
  assert (select current_save_file_id from public.season_players where id='{PLAYER}')='{SAVE}', 'pointer retained';
end $$;
-- Unknown events/syncs never announce; first fact is deduplicated transactionally.
insert into public.activity_events(season_id,type,visibility,payload) values
('{SEASON}','SAVE_REGISTERED','owner','{{}}'),
('{SEASON}','SEASON_ADMIN_ACTIVATE','public','{{}}'),
('{SEASON}','SEASON_ADMIN_ACTIVATE','public','{{}}');
do $$ begin
  assert (select count(*) from public.discord_announcements where season_id='{SEASON}')=1, 'event dedupe';
  assert not has_table_privilege('authenticated','public.discord_announcements','SELECT'), 'private outbox';
  assert not has_table_privilege('service_role','public.discord_announcements','INSERT'), 'trigger-only outbox';
  assert not has_function_privilege('authenticated','public.lifecycle_precompetition_safe(uuid)','EXECUTE'), 'private helper';
end $$;
rollback;
"""
    pg.sql(seed + checks)
    return "PASS: native readiness/unknown/reward denial, solo preparation, precompetition cancellation/replay/preservation, Discord dedupe/privacy"
