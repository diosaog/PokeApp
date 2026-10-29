-- 069: corrections from the real tests between two players (2026-10-28).
-- 1) Gen6/7 progress pays the existing medal/champion rules (preseason too).
-- 2) An administrator can cancel a draft or active season at any stage; only
--    an unfinished physical robbery/revive blocks it. History is preserved.
-- 3) Account repair tools: detail, end sessions, unlink the personal save and
--    delete an account (personal data and login removed, history anonymized).
-- 4) The League shows, as provisional figures, the death and sanction points
--    the next closing will subtract (preseason included).
begin;

-- 1. Progress rewards -------------------------------------------------------
-- Same function as 041 plus one fallback: when no Gen3-5 evidence exists, the
-- native Gen6/7 facts read by the same trusted server parser from the same
-- accepted save (observed_native_progress, 049) are used. X/Y/ORAS badges pay
-- per badge; the Gen6/7 champion pays game completion. Gen7 island stamps are
-- not badges and pay nothing. Claims stay unique per (season, trainer, key):
-- nothing is ever paid twice.
create or replace function public.settle_observed_progress_rewards(sid uuid,tid uuid) returns integer
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; saved public.save_files; parsed public.parsed_saves;
  ident public.pokemon_identity_revisions; c public.season_config_versions; progress jsonb; native jsonb;
  live public.season_reward_rule_revisions; badge_amount integer; champion_amount integer;
  badge_count integer; reward record; claim uuid; ledger uuid; paid integer=0; day_number integer;
begin
  select * into p from public.season_players where season_id=sid and trainer_id=tid for update;
  if not found or p.status<>'active' or not exists(select 1 from public.trainers where id=tid and globally_enabled)
    or not exists(select 1 from public.seasons where id=sid and status in ('active','finished','archived')) then return 0; end if;
  select * into ident from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid
    order by revision_number desc limit 1;
  if ident.id is null or ident.save_file_id is distinct from p.current_save_file_id then return 0; end if;
  select * into saved from public.save_files where id=ident.save_file_id and season_id=sid and trainer_id=tid for share;
  select * into parsed from public.parsed_saves where id=ident.parsed_save_id and save_file_id=saved.id for share;
  progress=public.observed_save_progress(saved,parsed,tid);
  if progress is null then
    native=public.observed_native_progress(saved,parsed,tid);
    if native is null then return 0; end if;
    progress=jsonb_build_object('schema_version',1,'source','native_progress','model',native->>'model',
      'regions',case when native->>'model'='gym_badges' then jsonb_build_array(jsonb_build_object(
        'region',case when parsed.payload->>'game' in ('X','Y') then 'kalos' else 'hoenn' end,
        'badge_flags',native->'badge_flags')) else '[]'::jsonb end,
      'champion_defeated',coalesce(native->'champion_defeated','null'::jsonb));
  end if;
  -- A pre-J1 save uses config 1. Later saves use the current/latest real League
  -- day, including after archive; a future config never takes effect early.
  select coalesce((select number from public.matchdays where id=s.current_matchday_id and season_id=sid),
    (select max(number) from public.matchdays where season_id=sid),1) into day_number
    from public.seasons s where id=sid;
  select * into c from public.season_config_versions where season_id=sid and effective_from_matchday<=day_number
    order by effective_from_matchday desc limit 1;
  if c.id is null then return 0; end if;
  select * into live from public.season_reward_rule_revisions where season_id=sid order by revision desc limit 1;
  badge_amount=coalesce(live.badge_reward_coins,(c.rules_json->>'badge_reward_coins')::integer,4);
  champion_amount=coalesce(live.game_completion_reward_coins,(c.rules_json->>'game_completion_reward_coins')::integer,12);
  select count(*) into badge_count from jsonb_array_elements(progress->'regions') r,
    lateral jsonb_array_elements(r->'badge_flags') f where f='true'::jsonb;
  -- Ordinal high-water marks: a regression or a different observed region cannot
  -- pay the same N badges twice. HGSS can prove up to sixteen distinct badges.
  for reward in
    select 'badge:'||n key,badge_amount amount,'badge_reward' kind
      from generate_series(1,badge_count) n
    union all
    select 'game_completion',champion_amount,'game_completion_reward'
      where progress->'champion_defeated'='true'::jsonb
  loop
    if exists(select 1 from public.progress_reward_claims where season_id=sid and trainer_id=tid and reward_key=reward.key) then continue; end if;
    claim=gen_random_uuid(); ledger=null;
    if reward.amount>0 then
      ledger=gen_random_uuid();
      insert into public.coin_transactions(id,season_id,trainer_id,season_player_id,amount,transaction_type,reference_type,reference_id,metadata)
        values(ledger,sid,tid,p.id,reward.amount,reward.kind,'progress_reward',claim,
          jsonb_build_object('reward_key',reward.key,'config_version_id',c.id,'identity_revision_id',ident.id,
            'save_file_id',saved.id,'source_hash',saved.sha256,'reward_rule_revision_id',live.id));
    end if;
    insert into public.progress_reward_claims(id,season_id,trainer_id,season_player_id,reward_key,amount,
      config_version_id,identity_revision_id,source_hash,observed_progress,coin_transaction_id,reward_rule_revision_id)
      values(claim,sid,tid,p.id,reward.key,reward.amount,c.id,ident.id,saved.sha256,progress,ledger,live.id);
    paid=paid+1;
  end loop;
  return paid;
end $$;

-- Saves already accepted in ACTIVE seasons get the same settlement once, as a
-- new accepted save would trigger it. Idempotent; finished history untouched;
-- coin rewards create no activity event, so nothing is announced on Discord.
do $$ declare r record; begin
  for r in select p.season_id,p.trainer_id from public.season_players p
      join public.seasons s on s.id=p.season_id
      where s.status='active' and p.status='active' order by p.season_id,p.trainer_id loop
    perform public.settle_observed_progress_rewards(r.season_id,r.trainer_id);
  end loop;
end $$;

-- 2. Cancellation at any stage ---------------------------------------------
-- The one real reason not to cancel: a Pokémon in the middle of a physical
-- robbery or revive between saves would be left duplicated or lost.
create function public.lifecycle_physical_counts(sid uuid) returns jsonb
language sql stable security definer set search_path='' as $$
  select jsonb_build_object(
    'open_robberies',(select count(distinct l.authorization_id) from public.item_use_transfer_legs l
      where l.season_id=sid and not l.released),
    'open_item_uses',(select count(*) from public.item_use_authorizations a where a.season_id=sid
      and a.status in ('PENDING_APPLICATION','RECOVERY_REQUIRED','BLOCKED_UNCERTAIN')))
$$;
create function public.lifecycle_physical_open(sid uuid) returns boolean
language sql stable security invoker set search_path=pg_catalog,public as $$
  select (c->>'open_robberies')::integer+(c->>'open_item_uses')::integer>0
  from (select public.lifecycle_physical_counts(sid) c) x
$$;

-- Extend the retained discard (cancellation) operation, keeping its principal,
-- locks, CAS, typed confirmation, reason, receipt and audit. A cancelled season
-- keeps every row; it is hidden from players and blocks every operation, since
-- all of them require an active season.
do $$ declare definition text; old_condition text;
begin
  select pg_get_functiondef('public.api_admin_season_lifecycle_v036(jsonb)'::regprocedure) into definition;
  old_condition='(not ((s.status=''draft'' and public.lifecycle_draft_safe(sid)) or (s.status=''active'' and public.lifecycle_precompetition_safe(sid))))';
  if position(old_condition in definition)=0 or position('if op is distinct from ''discard''' in definition)=0 then
    raise exception 'unexpected retained discard contract'; end if;
  definition=replace(definition,old_condition,
    '(s.status not in (''draft'',''active'') or public.lifecycle_physical_open(sid))');
  execute definition;
end $$;

create or replace function public.api_admin_get_setup(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare result jsonb; sid uuid=(p_request->>'season_id')::uuid; state text; clean boolean;
begin
  result=public.api_admin_get_setup_v067(p_request);
  state=result#>>'{season,status}';
  clean=case state when 'draft' then public.lifecycle_draft_safe(sid)
    when 'active' then public.lifecycle_precompetition_safe(sid) else false end;
  return result||jsonb_build_object(
    'can_discard',state in ('draft','active') and not public.lifecycle_physical_open(sid),
    'cancellation_mode',case when state not in ('draft','active') then 'unavailable'
      when clean then 'clean' else 'preserving' end);
end $$;

-- What a cancellation would leave behind, before anyone confirms it.
create function public.api_admin_season_cancellation_preview(p_request jsonb) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare sid uuid=(p_request->>'season_id')::uuid; s public.seasons; physical jsonb; clean boolean;
begin
  if not exists(select 1 from public.trainers where id=(p_request->>'actor_trainer_id')::uuid
      and globally_enabled and is_admin) then perform public.admin_setup_fail('admin_required',403); end if;
  select * into s from public.seasons where id=sid;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  physical=public.lifecycle_physical_counts(sid);
  clean=case s.status when 'draft' then public.lifecycle_draft_safe(sid)
    when 'active' then public.lifecycle_precompetition_safe(sid) else false end;
  return jsonb_build_object(
    'season_id',s.id,'name',s.name,'status',s.status,
    'allowed',s.status in ('draft','active') and (physical->>'open_robberies')::integer=0
      and (physical->>'open_item_uses')::integer=0,
    'mode',case when s.status not in ('draft','active') then 'unavailable' when clean then 'clean' else 'preserving' end,
    'open_robberies',(physical->>'open_robberies')::integer,
    'open_item_uses',(physical->>'open_item_uses')::integer,
    'participants',(select count(*) from public.season_players where season_id=sid),
    'matchdays',(select count(*) from public.matchdays where season_id=sid),
    'closed_matchdays',(select count(*) from public.matchdays where season_id=sid and status='closed'),
    'open_matchdays',(select count(*) from public.matchdays where season_id=sid and status='open'),
    'results',(select count(*) from public.matches where season_id=sid and status<>'scheduled'),
    'team_locks',(select count(*) from public.team_locks where season_id=sid),
    'purchases',(select count(*) from public.purchases where season_id=sid),
    'pending_purchases',(select count(*) from public.purchases where season_id=sid and status='pending'),
    'coin_transactions',(select count(*) from public.coin_transactions where season_id=sid),
    'coins_awarded',(select coalesce(sum(amount),0) from public.coin_transactions where season_id=sid and amount>0)::text,
    'progress_rewards',(select count(*) from public.progress_reward_claims where season_id=sid),
    'saves',(select count(*) from public.save_files where season_id=sid),
    'cups',(select count(*) from public.cups where season_id=sid and status in ('draft','active')),
    'penalties',(select count(*) from public.penalties where season_id=sid),
    'trials',(select count(*) from public.trial_cases where season_id=sid));
end $$;

-- 3. Account repair tools --------------------------------------------------
create function public.account_admin_guard(p_actor uuid) returns void
language plpgsql stable security invoker set search_path=public,pg_catalog as $$
begin
  if not exists(select 1 from public.trainers where id=p_actor and globally_enabled and is_admin
      and auth_user_id is not null) then raise exception 'account_forbidden'; end if;
end $$;

-- Deleted accounts (anonymized stubs kept for history) leave the admin list.
create or replace function public.account_admin_list(p_actor uuid,p_offset integer) returns jsonb
language plpgsql stable security invoker set search_path=public,pg_catalog as $$
declare result jsonb;
begin
 if not exists(select 1 from public.trainers where id=p_actor and globally_enabled and is_admin and auth_user_id is not null)
 then raise exception 'account_forbidden'; end if;
 if p_offset<0 or p_offset>100000 then raise exception 'invalid_account_offset'; end if;
 select coalesce(jsonb_agg(to_jsonb(q)),'[]'::jsonb) into result from (
   select id as trainer_id,display_name,globally_enabled,is_admin,profile_revision as revision,
     auth_user_id is not null as provisioned
   from public.trainers where not (metadata ? 'deleted_at') order by slug,id offset p_offset limit 50
 ) q;
 return jsonb_build_object('items',result,'offset',p_offset,'has_more',jsonb_array_length(result)=50);
end $$;

-- Everything an administrator needs to see to repair an account. The personal
-- save read is SECURITY DEFINER (066 left service_role without DELETE, not
-- without SELECT) only for the deletion counterpart below.
create function public.account_admin_detail(p_actor uuid,p_target uuid) returns jsonb
language plpgsql stable security invoker set search_path=public,pg_catalog as $$
declare t public.trainers; result jsonb;
begin
  perform public.account_admin_guard(p_actor);
  select * into t from public.trainers where id=p_target;
  if not found then raise exception 'account_not_found'; end if;
  select jsonb_build_object(
    'trainer_id',t.id,'display_name',t.display_name,'globally_enabled',t.globally_enabled,
    'is_admin',t.is_admin,'provisioned',t.auth_user_id is not null,'revision',t.profile_revision,
    'deleted',t.metadata ? 'deleted_at','created_at',t.created_at,
    'credential',(select jsonb_build_object('version',c.version,'reset_required',c.reset_required)
      from public.account_credentials c where c.trainer_id=t.id),
    'session_guard',(select jsonb_build_object('blocked',g.blocked,'sessions_valid_from',
      case when g.minimum_iat>0 then to_timestamp(g.minimum_iat) end) from public.account_session_guards g where g.trainer_id=t.id),
    'pin_change_pending',exists(select 1 from public.account_pin_changes where target_id=t.id and stage<>'complete'),
    'personal_save',(select jsonb_build_object('game',ps.game,'uploaded_at',ps.uploaded_at)
      from public.trainer_personal_saves ps where ps.trainer_id=t.id),
    'seasons',coalesce((select jsonb_agg(jsonb_build_object(
        'season_id',s.id,'name',s.name,'status',s.status,'participant_status',p.status,
        'bound_game',sf.metadata#>>'{save_identity,game}','save_uploaded_at',sf.uploaded_at,
        'coin_balance',(select coalesce(sum(amount),0) from public.coin_transactions x
          where x.season_id=s.id and x.trainer_id=t.id)::text)
      order by s.created_at desc)
      from public.season_players p join public.seasons s on s.id=p.season_id
      left join public.save_files sf on sf.id=p.current_save_file_id
      where p.trainer_id=t.id and s.status<>'discarded'),'[]'::jsonb),
    'history',public.account_history_counts(t.id)
  ) into result;
  return result;
end $$;

-- Rows that make an account part of the competition's history.
create function public.account_history_counts(p_target uuid) returns jsonb
language sql stable security definer set search_path='' as $$
  select jsonb_build_object(
    'seasons',(select count(*) from public.season_players where trainer_id=p_target),
    'coin_transactions',(select count(*) from public.coin_transactions where trainer_id=p_target),
    'saves',(select count(*) from public.save_files where trainer_id=p_target),
    'pokemon',(select count(*) from public.pokemon_entities where owner_trainer_id=p_target),
    'hall_of_fame',(select count(*) from public.hall_of_fame_entries
      where champion_trainer_id=p_target or finalist_trainer_id=p_target),
    'cups',(select count(*) from public.cup_participants where trainer_id=p_target),
    'trials',(select count(*) from public.trial_cases where accused_trainer_id=p_target or created_by_trainer_id=p_target),
    'robberies',(select count(*) from public.item_use_transfers where donor_id=p_target))
$$;

-- End every session of an account on every device: access tokens stop at once
-- (minimum_iat) and the Supabase refresh sessions are deleted, so no device can
-- renew. Idempotent per operation id.
create function public.account_admin_revoke_sessions(p_actor uuid,p_target uuid,p_operation uuid,p_hash text) returns jsonb
language plpgsql security definer set search_path=public,pg_catalog as $$
declare t public.trainers; c public.account_commands; result jsonb; ended integer=0;
begin
  perform public.account_admin_guard(p_actor);
  select * into c from public.account_commands where operation_id=p_operation;
  if found then
    if c.actor_id<>p_actor or c.target_id<>p_target or c.kind<>'revoke_sessions' or c.request_hash<>p_hash
      then raise exception 'account_conflict'; end if;
    return c.result;
  end if;
  select * into t from public.trainers where id=p_target for update;
  if not found then raise exception 'account_not_found'; end if;
  if p_actor=p_target then raise exception 'account_forbidden'; end if;
  insert into public.account_session_guards(trainer_id,blocked,minimum_iat)
    values(p_target,not t.globally_enabled,floor(extract(epoch from clock_timestamp()))::bigint+1)
    on conflict(trainer_id) do update set minimum_iat=excluded.minimum_iat;
  if t.auth_user_id is not null and to_regclass('auth.sessions') is not null then
    execute 'delete from auth.sessions where user_id=$1' using t.auth_user_id;
    get diagnostics ended=row_count;
  end if;
  result=jsonb_build_object('trainer_id',t.id,'sessions_ended',ended,
    'refresh_revoked',to_regclass('auth.sessions') is not null);
  insert into public.account_commands values(p_operation,p_actor,p_target,'revoke_sessions',p_hash,result,now());
  return result;
end $$;

-- Remove a wrong personal-save association ("Mi PC" and the active game). The
-- trainer's Launcher sends the save it has selected again on its next sync.
create function public.account_admin_unlink_personal_save(p_actor uuid,p_target uuid,p_operation uuid,p_hash text) returns jsonb
language plpgsql security definer set search_path=public,pg_catalog as $$
declare c public.account_commands; result jsonb; removed integer;
begin
  perform public.account_admin_guard(p_actor);
  select * into c from public.account_commands where operation_id=p_operation;
  if found then
    if c.actor_id<>p_actor or c.target_id<>p_target or c.kind<>'unlink_personal_save' or c.request_hash<>p_hash
      then raise exception 'account_conflict'; end if;
    return c.result;
  end if;
  if not exists(select 1 from public.trainers where id=p_target) then raise exception 'account_not_found'; end if;
  delete from public.trainer_personal_saves where trainer_id=p_target;
  get diagnostics removed=row_count;
  result=jsonb_build_object('trainer_id',p_target,'removed',removed>0);
  insert into public.account_commands values(p_operation,p_actor,p_target,'unlink_personal_save',p_hash,result,now());
  return result;
end $$;

-- Delete an account. Login, credentials, sessions, photo and personal save are
-- removed; the trainer row stays as an anonymous stub so seasons, results,
-- coins and audit keep a consistent reference. An active participant must be
-- withdrawn from the season first; an administrator cannot be deleted here.
create function public.account_admin_delete(p_actor uuid,p_target uuid,p_operation uuid,p_hash text,p_confirmation text) returns jsonb
language plpgsql security definer set search_path=public,pg_catalog as $$
declare t public.trainers; c public.account_commands; result jsonb; tag text; sessions integer=0;
begin
  perform public.account_admin_guard(p_actor);
  select * into c from public.account_commands where operation_id=p_operation;
  if found then
    if c.actor_id<>p_actor or c.target_id<>p_target or c.kind<>'delete_account' or c.request_hash<>p_hash
      then raise exception 'account_conflict'; end if;
    return c.result;
  end if;
  select * into t from public.trainers where id=p_target for update;
  if not found or t.metadata ? 'deleted_at' then raise exception 'account_not_found'; end if;
  if p_actor=p_target or t.is_admin then raise exception 'account_forbidden'; end if;
  if p_confirmation is distinct from t.display_name then raise exception 'account_confirmation_required'; end if;
  if exists(select 1 from public.account_pin_changes where target_id=p_target and stage<>'complete')
    then raise exception 'account_conflict'; end if;
  if exists(select 1 from public.season_players p join public.seasons s on s.id=p.season_id
      where p.trainer_id=p_target and p.status='active' and s.status='active')
    then raise exception 'account_active_participant'; end if;
  tag=left(replace(p_target::text,'-',''),8);
  if t.auth_user_id is not null and to_regclass('auth.sessions') is not null then
    execute 'delete from auth.sessions where user_id=$1' using t.auth_user_id;
    get diagnostics sessions=row_count;
  end if;
  delete from public.trainer_personal_saves where trainer_id=p_target;
  delete from public.account_credentials where trainer_id=p_target;
  delete from public.account_renewal_grants where trainer_id=p_target;
  insert into public.account_session_guards(trainer_id,blocked,minimum_iat)
    values(p_target,true,floor(extract(epoch from clock_timestamp()))::bigint+1)
    on conflict(trainer_id) do update set blocked=true,minimum_iat=excluded.minimum_iat;
  update public.trainers set display_name='Entrenador eliminado '||tag,slug='eliminado-'||tag,
    auth_user_id=null,photo_key=null,globally_enabled=false,is_admin=false,
    profile_revision=profile_revision+1,
    metadata=metadata||jsonb_build_object('deleted_at',clock_timestamp(),'deleted_by',p_actor)
    where id=p_target;
  -- The login identity and the photo live outside SQL: the API removes them
  -- with these references, and a replay returns them again for a retry.
  result=jsonb_build_object('trainer_id',p_target,'deleted',true,'sessions_ended',sessions,
    'auth_user_id',t.auth_user_id,'photo_key',t.photo_key,
    'history_kept',public.account_history_counts(p_target));
  insert into public.account_commands values(p_operation,p_actor,p_target,'delete_account',p_hash,result,now());
  return result;
end $$;

-- 4. Provisional League figures ---------------------------------------------
-- Points come only from matchday positions. Each closing also subtracts, as
-- cumulative figures, 0.2 per adjusted death and the resolved points sanctions
-- (matchday_context, 039). Deaths and sanctions before a closing - the whole
-- preseason - were never lost, only invisible until it. The general read now
-- adds what the next closing would subtract, from the same inputs, beside the
-- untouched official total. Read only: nothing is written, paid or penalized.
alter function public.league_general_read(uuid) rename to league_general_read_v068;
create function public.league_general_read(p_season_id uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare result jsonb; next_number integer; next_id uuid; rows jsonb;
begin
  result=public.league_general_read_v068(p_season_id);
  if result is null or result#>>'{season,status}' is distinct from 'active' then return result; end if;
  select id,number into next_id,next_number from public.matchdays
    where season_id=p_season_id and status<>'closed' order by number limit 1;
  if next_number is null then
    select coalesce(max(number),0)+1 into next_number from public.matchdays where season_id=p_season_id;
  end if;
  select jsonb_agg(x.r||jsonb_build_object(
      'provisional_matchday_number',next_number,
      'provisional_dead_count',f.deaths,
      'provisional_points_reduction',f.reduction::text,
      'provisional_points',case when f.deaths is not null then (f.earned-f.reduction-0.2*f.deaths)::text end)
    order by x.ord) into rows
  from jsonb_array_elements(result->'rows') with ordinality x(r,ord)
  join public.season_players p on p.id=(x.r->>'season_player_id')::uuid and p.season_id=p_season_id
  left join public.season_player_stats st on st.season_player_id=p.id
  cross join lateral (select
    coalesce((select sp.earned_points from public.public_sanctioned_points sp
      where sp.season_id=p_season_id and sp.season_player_id=p.id),0) as earned,
    -- A save the closing could not read yet (no identity) is unknown, never 0.
    case when p.current_save_file_id is null or exists(select 1 from public.pokemon_identity_revisions i
        where i.save_file_id=p.current_save_file_id) then
      (select count(*) from public.pokemon_observations o where o.save_file_id=p.current_save_file_id
        and o.source='box' and o.box_number=8)
      +greatest((select count(*) from public.redemptions e where e.season_id=p_season_id and e.trainer_id=p.trainer_id
          and e.effect_code='revive' and e.status='applied'),
        (select count(*) from public.purchases u join public.shop_items i on i.id=u.shop_item_id
          where u.season_player_id=p.id and u.status='used' and i.code='revivir_pokemon'))
      -public.purchased_revive_overlap(p_season_id,p.trainer_id,p.current_save_file_id)
      +2::bigint*coalesce(st.revived_after_wipe,0) end as deaths,
    coalesce((select sum(greatest(coalesce(points_amount,amount::numeric),0)) from public.penalties pe
      where pe.season_id=p_season_id and pe.trainer_id=p.trainer_id and public.trials_penalty_current(pe)
        and (pe.effective_from_matchday_number is null or pe.effective_from_matchday_number<=next_number)
        and pe.penalty_type='points_reduction' and (pe.matchday_id is null or pe.matchday_id=next_id)
        and (pe.trial_case_id is null or exists(select 1 from public.trial_cases tc where tc.id=pe.trial_case_id
          and tc.status='resolved' and tc.accused_trainer_id=p.trainer_id
          and (tc.season_id is null or tc.season_id=p_season_id)))),0) as reduction) f;
  -- Every official row keeps its place; a mismatch keeps the 068 read as is.
  if jsonb_array_length(coalesce(rows,'[]'::jsonb))<>jsonb_array_length(result->'rows') then return result; end if;
  return jsonb_set(result,'{rows}',coalesce(rows,'[]'::jsonb));
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.lifecycle_physical_counts(uuid)'::regprocedure,
    'public.lifecycle_physical_open(uuid)'::regprocedure,
    'public.api_admin_season_cancellation_preview(jsonb)'::regprocedure,
    'public.account_admin_guard(uuid)'::regprocedure,
    'public.account_admin_detail(uuid,uuid)'::regprocedure,
    'public.account_history_counts(uuid)'::regprocedure,
    'public.account_admin_revoke_sessions(uuid,uuid,uuid,text)'::regprocedure,
    'public.account_admin_unlink_personal_save(uuid,uuid,uuid,text)'::regprocedure,
    'public.account_admin_delete(uuid,uuid,uuid,text,text)'::regprocedure,
    'public.league_general_read(uuid)'::regprocedure,
    'public.league_general_read_v068(uuid)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
commit;
