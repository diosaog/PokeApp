"""Focused rollback-only checks for 069, on a disposable Supabase-shaped cluster.

Synthetic rows only. Proves: Gen6 native badges and the champion pay the
existing rules exactly once; Gen7 island stamps pay nothing; an active season
with official activity can be cancelled (history kept) while an unfinished
robbery blocks it; the cancellation preview; account detail, session end,
personal-save unlink and deletion (anonymized stub, history kept).
"""

from tools.validate_phase21_native import PARSED, PLAYER, SAVE, SEASON, SHA, TRAINER
from tools.validate_phase21_native import sql as native_sql

ADMIN = "66666666-6666-6666-6666-666666666666"
OTHER = "77777777-7777-7777-7777-777777777777"


def validate(pg):
    seed = native_sql().split("select case when public.observed_native_progress")[0]
    # Only this fixture's season may be active.
    seed = seed.replace(
        "begin;",
        "begin; update public.seasons set status='draft' where status='active';",
    )
    checks = f"""
insert into public.trainers(id,display_name,slug,auth_user_id,is_admin) values
  ('{ADMIN}','Admin Fixture','admin-fixture',gen_random_uuid(),true),
  ('{OTHER}','Other Fixture','other-fixture',gen_random_uuid(),false);
insert into public.season_admin_state(season_id) values ('{SEASON}');
insert into public.season_config_versions(season_id,version_number,name,effective_from_matchday,total_matchdays,division_count,rules_json)
  values ('{SEASON}',1,'069',1,4,1,'{{"badge_reward_coins":4,"game_completion_reward_coins":12}}');
insert into public.pokemon_identity_revisions(season_id,trainer_id,save_file_id,parsed_save_id,
  revision_number,capture_stream_id,capture_sequence,input_signature)
  values ('{SEASON}','{TRAINER}','{SAVE}','{PARSED}',1,gen_random_uuid(),1,'{SHA}');
do $$ declare paid integer; preview jsonb; receipt jsonb; request jsonb; detail jsonb; result jsonb;
begin
  -- 1. Gen6 badges pay per badge, once.
  update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}',
    '[true,true,true,false,false,false,false,false]') where id='{PARSED}';
  paid=public.settle_observed_progress_rewards('{SEASON}','{TRAINER}');
  assert paid=3, format('three badges pay, got %s',paid);
  assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0, 'never paid twice';
  assert (select sum(amount) from public.coin_transactions where season_id='{SEASON}' and trainer_id='{TRAINER}')=12,
    'three badges at 4 coins';
  -- A regression of the save cannot take or repay anything.
  update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}',
    '[true,false,false,false,false,false,false,false]') where id='{PARSED}';
  assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0, 'regression pays nothing';
  -- The champion pays game completion once.
  update public.parsed_saves set payload=jsonb_set(jsonb_set(payload,'{{native_progress,badge_flags}}',
    '[true,true,true,true,true,true,true,true]'),'{{native_progress,champion_defeated}}','true') where id='{PARSED}';
  assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=6, 'five more badges and the champion';
  assert (select sum(amount) from public.coin_transactions where season_id='{SEASON}' and trainer_id='{TRAINER}')=4*8+12,
    'eight badges and the champion';
  assert (select count(*) from public.progress_reward_claims where season_id='{SEASON}' and trainer_id='{TRAINER}')=9,
    'one claim per reward';
  -- Malformed native evidence fails closed.
  update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}','[true]') where id='{PARSED}';
  assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0, 'malformed pays nothing';

  -- 1b. Preseason League: official points stay 0 (positions only), while the
  --     consequences the first closing will subtract are shown, read only.
  insert into public.season_player_stats(season_player_id,season_id,trainer_id,revived_after_wipe)
    values ('{PLAYER}','{SEASON}','{TRAINER}',1)
    on conflict (season_player_id) do update set revived_after_wipe=1;
  insert into public.penalties(season_id,trainer_id,penalty_type,amount,points_amount)
    values ('{SEASON}','{TRAINER}','points_reduction',0,1.5);
  result=public.league_general_read('{SEASON}');
  assert result#>>'{{rows,0,total_points}}'='0', format('official stays 0: %s',result);
  assert (result#>>'{{rows,0,provisional_dead_count}}')::integer=2, 'a wipe revival counts two deaths';
  assert (result#>>'{{rows,0,provisional_points_reduction}}')::numeric=1.5, 'the sanction is shown';
  assert (result#>>'{{rows,0,provisional_points}}')::numeric=-1.9, format('0 - 1.5 - 0.2*2: %s',result);
  assert (result#>>'{{rows,0,provisional_matchday_number}}')::integer=1, 'the first closing';
  assert (select sum(amount) from public.coin_transactions where season_id='{SEASON}' and trainer_id='{TRAINER}')=4*8+12,
    'reading pays nothing';
  assert not has_function_privilege('authenticated','public.league_general_read(uuid)','EXECUTE'), 'private read';
  assert has_function_privilege('service_role','public.league_general_read(uuid)','EXECUTE'), 'API read';
  delete from public.penalties where season_id='{SEASON}';

  -- 2. An active season WITH official activity can be cancelled; history stays.
  insert into public.matchdays(season_id,number,status,season_config_version_id)
    select '{SEASON}',1,'open',id from public.season_config_versions where season_id='{SEASON}';
  assert not public.lifecycle_precompetition_safe('{SEASON}'), 'the fixture has official activity';
  preview=public.api_admin_season_cancellation_preview(jsonb_build_object('actor_trainer_id','{ADMIN}','season_id','{SEASON}'));
  assert preview->>'allowed'='true' and preview->>'mode'='preserving', format('preview %s',preview);
  assert (preview->>'coin_transactions')::integer=9 and (preview->>'open_matchdays')::integer=1, 'preview counts';
  begin
    perform public.api_admin_season_cancellation_preview(jsonb_build_object('actor_trainer_id','{OTHER}','season_id','{SEASON}'));
    raise exception 'non-admin preview allowed';
  exception when sqlstate 'PT403' then null; end;
  request=jsonb_build_object('actor_trainer_id','{ADMIN}','season_id','{SEASON}','operation','discard',
    'idempotency_key','069-cancel','body',jsonb_build_object('expected_revision',0,'reason','Disposable proof','confirmation','DISCARD'));
  receipt=public.api_admin_season_lifecycle(request);
  assert receipt->>'state'='discarded', 'cancelled';
  assert public.api_admin_season_lifecycle(request)->>'replayed'='true', 'replay';
  assert (select count(*) from public.coin_transactions where season_id='{SEASON}')=9, 'coins kept for audit';
  assert (select count(*) from public.matchdays where season_id='{SEASON}')=1, 'matchday kept';
  assert (select current_save_file_id from public.season_players where id='{PLAYER}')='{SAVE}', 'save pointer kept';
  -- Another season can be activated afterwards: the one-active index is free.
  assert not exists(select 1 from public.seasons where status='active'), 'no active season left';
end $$;

-- 3. Account tools (the fixture season plays again, so its trainer is an
--    active participant).
update public.seasons set status='active',discarded_at=null where id='{SEASON}';
-- The API's own role can run the provisional read with its table grants.
set local role service_role;
do $$ begin
  assert public.league_general_read('{SEASON}')#>>'{{rows,0,provisional_points}}' is not null, 'service_role read';
end $$;
reset role;
insert into public.trainer_personal_saves(trainer_id,sha256,observation_digest,parser_version,game,payload,uploaded_at)
  values ('{OTHER}','{SHA}','{SHA}','pokeapp-reader/3;pkhex/24.11.11','Y','{{}}'::jsonb,now());
do $$ declare detail jsonb; result jsonb; op uuid=gen_random_uuid(); del uuid=gen_random_uuid();
begin
  detail=public.account_admin_detail('{ADMIN}','{OTHER}');
  assert detail#>>'{{personal_save,game}}'='Y', format('detail %s',detail);
  assert (detail#>>'{{history,seasons}}')::integer=0, 'no history';
  begin perform public.account_admin_detail('{OTHER}','{ADMIN}'); raise exception 'non-admin detail';
  exception when others then assert sqlerrm='account_forbidden', sqlerrm; end;
  result=public.account_admin_revoke_sessions('{ADMIN}','{OTHER}',op,repeat('b',64));
  assert result->>'trainer_id'='{OTHER}', 'revoke result';
  assert public.account_admin_revoke_sessions('{ADMIN}','{OTHER}',op,repeat('b',64))=result, 'revoke replay';
  assert (select minimum_iat from public.account_session_guards where trainer_id='{OTHER}')>0, 'tokens stop at once';
  begin perform public.account_admin_revoke_sessions('{ADMIN}','{ADMIN}',gen_random_uuid(),repeat('b',64));
    raise exception 'self revoke'; exception when others then assert sqlerrm='account_forbidden', sqlerrm; end;
  result=public.account_admin_unlink_personal_save('{ADMIN}','{OTHER}',gen_random_uuid(),repeat('c',64));
  assert result->>'removed'='true' and not exists(select 1 from public.trainer_personal_saves where trainer_id='{OTHER}'),
    'personal save unlinked';
  begin perform public.account_admin_delete('{ADMIN}','{OTHER}',del,repeat('d',64),'wrong name');
    raise exception 'unconfirmed delete'; exception when others then assert sqlerrm='account_confirmation_required', sqlerrm; end;
  begin perform public.account_admin_delete('{ADMIN}','{TRAINER}',gen_random_uuid(),repeat('d',64),'Native Fixture');
    raise exception 'active participant deleted';
  exception when others then assert sqlerrm='account_active_participant', sqlerrm; end;
  result=public.account_admin_delete('{ADMIN}','{OTHER}',del,repeat('d',64),'Other Fixture');
  assert result->>'deleted'='true' and result->>'auth_user_id' is not null, format('delete %s',result);
  assert public.account_admin_delete('{ADMIN}','{OTHER}',del,repeat('d',64),'Other Fixture')=result, 'delete replay';
  assert (select display_name like 'Entrenador eliminado %' and auth_user_id is null and not globally_enabled
    and metadata ? 'deleted_at' from public.trainers where id='{OTHER}'), 'anonymized stub';
  assert not exists(select 1 from public.account_credentials where trainer_id='{OTHER}'), 'credentials removed';
  assert not exists(select 1 from jsonb_array_elements(public.account_admin_list('{ADMIN}',0)->'items') i
    where i->>'trainer_id'='{OTHER}'), 'deleted account leaves the admin list';
  -- Privileges: nothing new for browsers.
  assert not has_function_privilege('authenticated','public.account_admin_delete(uuid,uuid,uuid,text,text)','EXECUTE'), 'private delete';
  assert not has_function_privilege('anon','public.api_admin_season_cancellation_preview(jsonb)','EXECUTE'), 'private preview';
  assert not has_function_privilege('authenticated','public.lifecycle_physical_counts(uuid)','EXECUTE'), 'private counts';
end $$;
rollback;
"""
    pg.sql(seed + checks)
    # An unfinished robbery leg (the only physical-integrity blocker). The
    # superuser skips foreign keys for this synthetic leg only, in a rollback.
    blocked = f"""
set local session_replication_role=replica;
insert into public.season_admin_state(season_id) values ('{SEASON}');
insert into public.item_use_transfer_legs(authorization_id,side,season_id,trainer_id,save_file_id,
  identity_revision_id,source_sha256) values (gen_random_uuid(),'source','{SEASON}','{TRAINER}','{SAVE}',
  gen_random_uuid(),'{SHA}');
set local session_replication_role=origin;
insert into public.trainers(id,display_name,slug,auth_user_id,is_admin) values
  ('{ADMIN}','Admin Fixture','admin-fixture',gen_random_uuid(),true);
do $$ declare preview jsonb; begin
  assert public.lifecycle_physical_open('{SEASON}'), 'an unreleased leg is open';
  preview=public.api_admin_season_cancellation_preview(jsonb_build_object('actor_trainer_id','{ADMIN}','season_id','{SEASON}'));
  assert preview->>'allowed'='false' and (preview->>'open_robberies')::integer=1, format('preview %s',preview);
  begin
    perform public.api_admin_season_lifecycle(jsonb_build_object('actor_trainer_id','{ADMIN}','season_id','{SEASON}',
      'operation','discard','idempotency_key','069-blocked','body',jsonb_build_object('expected_revision',0,
      'reason','Disposable proof','confirmation','DISCARD')));
    raise exception 'cancelled with an open robbery';
  exception when sqlstate 'PT409' then assert sqlerrm='discard_not_allowed', sqlerrm; end;
  assert (select status from public.seasons where id='{SEASON}')='active', 'still active';
end $$;
rollback;
"""
    pg.sql(seed + blocked, user="supabase_admin")
    return (
        "PASS: Gen6 badges/champion paid once (regression and malformed pay nothing), "
        "preseason provisional deaths/sanctions shown without writing, "
        "cancellation of an active season with activity keeps history and replays, "
        "non-admin preview refused, account detail/session end/unlink/delete (anonymized, "
        "confirmation, active participant refused), private functions"
    )
