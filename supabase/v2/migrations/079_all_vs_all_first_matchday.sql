-- 079: an all-vs-all League starts without an administrator (owner decision
-- 2026-11-04: ChampionsLocke is everyone against everyone, no A/B divisions).
--
-- * A single-league season (J1 config without B) no longer needs the observed
--   initial A/B assignment of 036/063. Any active participant prepares J1:
--   one «Liga» division with every participant, every pair scheduled once,
--   one audited initial snapshot (rule all_vs_all_v1). Idempotent by state
--   and serialized on the season row; the unique (season, number) index makes
--   a second J1 impossible.
-- * One read lists, before opening, the exact reasons the server would refuse
--   (save, badges, death history), per trainer.
-- * A trainer confirms their OWN observed death history (first baseline, or
--   the wipe counter they set themselves): only the server-observed values,
--   never a number chosen by the trainer, never another trainer's history.
--   Corrections, false deaths and every other case stay administrative.
--
-- Additive: no existing row is rewritten. Two-league seasons keep the observed
-- A/B assignment; opening still requires saves, the J1 badges and a known
-- death history; freezing, ranking, rewards and corrections are unchanged.
begin;

alter table public.initial_division_snapshots
  drop constraint initial_division_snapshots_rule_check,
  add constraint initial_division_snapshots_rule_check
    check (rule in ('observed_deaths_v1', 'all_vs_all_v1'));

-- One league (J1 config without B) of a modern season: everyone meets everyone.
create function public.league_all_vs_all(sid uuid) returns boolean
language sql stable security invoker set search_path=pg_catalog,public as $$
  select public.initial_assignment_modern(sid) and coalesce((select c.division_sizes is not null
      and not (c.division_sizes ? 'B') from public.season_config_versions c
    where c.season_id=sid and c.effective_from_matchday=1),false)
$$;

-- The observed A/B review does not apply to an all-vs-all League (unless one
-- was already recorded before 079, which keeps its historical answer).
alter function public.initial_assignment_inputs(uuid) rename to initial_assignment_inputs_v078;
create function public.initial_assignment_inputs(sid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare a public.season_admin_state;
begin
  if public.league_all_vs_all(sid) and not exists(select 1 from public.initial_division_snapshots
      where season_id=sid and rule='observed_deaths_v1') then
    if not exists(select 1 from public.seasons where id=sid and status<>'discarded') then
      perform public.admin_setup_fail('season_not_found',404); end if;
    select * into a from public.season_admin_state where season_id=sid;
    return jsonb_build_object('season_id',sid,'rule',null,'state','not_required','config_version_id',null,
      'division_sizes',null,'setup_revision',coalesce(a.setup_revision,0),'roster_revision',coalesce(a.roster_revision,0),
      'input_hash',encode(sha256(convert_to(sid::text||':all_vs_all_v1','UTF8')),'hex'),'ready',false,
      'blocking_reasons','["initial_assignment_not_required"]'::jsonb,'players','[]'::jsonb);
  end if;
  return public.initial_assignment_inputs_v078(sid);
end $$;

-- Structural checks of an all-vs-all J1, shared by preparation and readiness.
-- Returns the first reason it cannot be prepared, or null.
create function public.league_first_matchday_blocker(sid uuid) returns text
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare s public.seasons; a public.season_admin_state; cfg public.season_config_versions;
begin
  select * into s from public.seasons where id=sid;
  if s.id is null or s.status<>'active' then return 'season_not_active'; end if;
  if exists(select 1 from public.matchdays where season_id=sid) then return 'matchday_already_prepared'; end if;
  if not public.league_all_vs_all(sid) then return 'initial_assignment_required'; end if;
  if exists(select 1 from public.divisions where season_id=sid)
    or exists(select 1 from public.division_memberships where season_id=sid)
    or exists(select 1 from public.initial_division_snapshots where season_id=sid) then
    return 'initial_setup_locked'; end if;
  if exists(select 1 from public.season_players p join public.trainers t on t.id=p.trainer_id
      where p.season_id=sid and (p.status<>'active' or not t.globally_enabled)) then
    return 'invalid_roster'; end if;
  if (select count(*) from public.season_players where season_id=sid)<2 then return 'opponent_missing'; end if;
  select * into a from public.season_admin_state where season_id=sid;
  select * into cfg from public.season_config_versions where season_id=sid and effective_from_matchday=1;
  if a.season_id is null or cfg.id is null or cfg.roster_revision is distinct from a.roster_revision then
    return 'config_not_effective'; end if;
  begin
    -- The same validation the observed review applied (036 initial_assignment_inputs).
    perform public.admin_setup_validate_config(sid,jsonb_build_object('name',cfg.name,'division_sizes',cfg.division_sizes,
      'effective_from_matchday',1,'total_matchdays',cfg.total_matchdays,'movement_count',cfg.promotion_relegation_count,
      'scoring',cfg.scoring_json,'coin_rewards',cfg.coin_rewards_json,'rules',cfg.rules_json));
  exception when sqlstate 'PT409' then return 'config_not_effective'; end;
  return null;
end $$;

-- Prepare J1 of an all-vs-all League: any active participant, or an admin.
create function public.api_league_prepare_first_matchday(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare actor uuid; sid uuid; t public.trainers; s public.seasons; p public.season_players;
  d public.matchdays; a public.season_admin_state; cfg public.season_config_versions;
  blocker text; division uuid; day_id uuid; n integer; ids jsonb; inputs jsonb; hash text;
  uuid_re text='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
  if jsonb_typeof(p_request) is distinct from 'object' or p_request-array['actor_trainer_id','season_id']<>'{}'::jsonb
    or coalesce(p_request->>'actor_trainer_id','') !~ uuid_re or coalesce(p_request->>'season_id','') !~ uuid_re then
    perform public.admin_setup_fail('invalid_request',422); end if;
  actor=(p_request->>'actor_trainer_id')::uuid; sid=(p_request->>'season_id')::uuid;
  -- Lock order of every League operation: trainer, season, ordered roster.
  select * into t from public.trainers where id=actor for share;
  if not found or not t.globally_enabled then perform public.admin_setup_fail('trainer_disabled',403); end if;
  select * into s from public.seasons where id=sid for no key update;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  perform 1 from public.season_players where season_id=sid order by id for update;
  if not t.is_admin then
    select * into p from public.season_players where season_id=sid and trainer_id=actor;
    if not found then perform public.admin_setup_fail('participant_required',403); end if;
    if p.status<>'active' then perform public.admin_setup_fail('participant_inactive',403); end if;
  end if;
  -- Idempotent by state: whoever prepared it first, every caller gets the
  -- season's current matchday and never a second J1.
  select * into d from public.matchdays where id=s.current_matchday_id and season_id=sid;
  if d.id is null then select * into d from public.matchdays where season_id=sid order by number desc limit 1; end if;
  if d.id is not null then
    return jsonb_build_object('season_id',sid,'matchday_id',d.id,'number',d.number,'status',d.status,
      'revision',d.revision,'created',false);
  end if;
  select * into a from public.season_admin_state where season_id=sid for update;
  blocker=public.league_first_matchday_blocker(sid);
  if blocker is not null then perform public.admin_setup_fail(blocker); end if;
  select * into cfg from public.season_config_versions where season_id=sid and effective_from_matchday=1 for share;
  select count(*),jsonb_agg(to_jsonb(id) order by id) into n,ids from public.season_players where season_id=sid;
  insert into public.divisions(season_id,code,name,tier_order) values(sid,'A','Liga',1) returning id into division;
  insert into public.division_memberships(season_id,season_player_id,division_id,effective_from_matchday_number,reason)
    select sid,id,division,1,'initial' from public.season_players where season_id=sid order by id;
  insert into public.matchdays(season_id,number,season_config_version_id) values(sid,1,cfg.id) returning * into d;
  day_id=d.id;
  insert into public.matches(season_id,matchday_id,division_id,player_a_id,player_b_id)
    select sid,day_id,division,x.id,y.id from public.season_players x
    join public.season_players y on y.season_id=x.season_id and x.id<y.id
    where x.season_id=sid order by x.id,y.id;
  inputs=jsonb_build_object('season_id',sid,'rule','all_vs_all_v1','config_version_id',cfg.id,
    'division_sizes',cfg.division_sizes,'setup_revision',a.setup_revision,'roster_revision',a.roster_revision,
    'players',ids);
  hash=encode(sha256(convert_to(inputs::text,'UTF8')),'hex');
  insert into public.initial_division_snapshots(season_id,config_version_id,rule,input_hash,inputs,assignments,audit,actor_trainer_id)
    values(sid,cfg.id,'all_vs_all_v1',hash,inputs,jsonb_build_object('A',ids,'B','[]'::jsonb),
      jsonb_build_object('rule','all_vs_all_v1','input_hash',hash,'boundary_tie',null,'resolution',null,
        'reason','Todos contra todos: una sola Liga, sin reparto inicial.'),actor);
  update public.seasons set current_matchday_id=day_id where id=sid;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  insert into public.activity_events(season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(sid,'LEAGUE_FIRST_MATCHDAY_PREPARED',actor,'admin','league-first-matchday:'||sid::text,
      jsonb_build_object('matchday_id',day_id,'matchday_number',1,'rule','all_vs_all_v1',
        'participants',n,'matches',n*(n-1)/2,'input_hash',hash));
  return jsonb_build_object('season_id',sid,'matchday_id',day_id,'number',1,'status',d.status,
    'revision',d.revision,'created',true);
end $$;

-- The participant's own death-history facts and whether they may confirm them.
-- Self-service is limited to acknowledging what the server observed: the
-- first baseline (no pre-tracking offset) or the wipe counter the trainer set.
create function public.league_participant_death_state(pid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; s public.seasons; d public.matchdays; h public.league_death_history;
  totals jsonb; reason text; why text; recorded bigint; segment_recorded bigint; segment bigint; frozen bigint;
  actual bigint; wipes bigint; unmapped bigint;
begin
  select * into p from public.season_players where id=pid;
  select * into s from public.seasons where id=p.season_id;
  select * into d from public.matchdays where id=s.current_matchday_id and season_id=s.id;
  select * into h from public.league_death_history where season_player_id=pid;
  totals=public.league_death_totals(pid);
  reason=totals->>'blocking_reason';
  select count(*) into recorded from public.league_effective_death_events(pid);
  select count(*) into segment_recorded from public.league_effective_death_events(pid) e
    where (e.matchday_id=d.id and e.phase='progression') or (e.phase='preseason' and (d.number=1 or d.id is null));
  segment=case when d.id is null then segment_recorded+coalesce(case when h.segment_matchday_id is null then h.segment_offset end,0)
    else public.league_death_segment(pid,d.id) end;
  select segment_deaths into frozen from public.matchday_death_snapshots where season_player_id=pid and matchday_id=d.id;
  actual=coalesce(h.actual_offset,0)+recorded;
  wipes=(totals->>'wipe_counter')::bigint;
  unmapped=public.league_unmapped_revives(pid);
  why=case
    when (totals->>'known')::boolean then 'death_history_confirmed'
    when p.current_save_file_id is null then 'save_missing'
    when s.status<>'active' or coalesce(d.status,'scheduled') not in ('scheduled','open') then 'death_history_closed'
    -- Registration tracks every accepted save; a not-yet-tracked one is transient.
    when reason='death_history_source_changed' or ((totals->>'valid')::boolean and h.season_player_id is not null
      and h.last_identity_revision_id is distinct from (totals->>'identity_revision_id')::uuid) then 'death_history_pending_sync'
    when reason not in ('death_history_baseline_required','death_history_wipe_reconciliation_required') then 'death_history_admin_required'
    when h.season_player_id is null or h.blocking_reason is not null or h.dead_box_number<>p.dead_box_number then 'death_history_admin_required'
    when wipes is null or totals->>'wipe_revision' is null then 'death_history_admin_required'
    when unmapped<>coalesce(h.confirmed_unmapped_revives,0) then 'death_history_admin_required'
    when wipes>actual or segment>actual or segment<segment_recorded
      or (frozen is not null and frozen<>segment) then 'death_history_admin_required'
    else null end;
  return jsonb_build_object('season_id',p.season_id,'season_player_id',pid,'trainer_id',p.trainer_id,
    'revision',coalesce(h.revision,0),'known',(totals->>'known')::boolean,'blocking_reason',reason,
    'actual_deaths',totals->'actual_deaths','wipe_deaths',totals->'wipe_deaths',
    'segment_deaths',case when (totals->>'known')::boolean then to_jsonb(segment) end,
    'dead_box_number',p.dead_box_number,'source_sha256',case when (totals->>'valid')::boolean then totals->>'source_sha256' end,
    'confirmed_at',h.confirmed_at,'current_matchday_id',d.id,
    'can_confirm',why is null,'confirm_blocker',why,
    'proposed',case when why is null then jsonb_build_object('actual_deaths',actual,'wipe_deaths',wipes,
      'segment_deaths',segment) end);
end $$;

create function public.api_participant_death_history(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare op text=p_request->>'operation'; r jsonb=p_request->'request'; b jsonb=r->'body';
  actor uuid; sid uuid; k text=r->>'idempotency_key'; scope text; t public.trainers; s public.seasons;
  p public.season_players; d public.matchdays; h public.league_death_history; old public.admin_operation_receipts;
  state jsonb; before jsonb; src jsonb; proposed jsonb; result jsonb; recorded bigint; segment_recorded bigint;
  resolution_id uuid=gen_random_uuid(); oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid();
  uuid_re text='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
  if op is null or op not in ('state','confirm') or p_request-array['operation','request']<>'{}'::jsonb
    or jsonb_typeof(r) is distinct from 'object' or r-array['actor_trainer_id','season_id','body','idempotency_key']<>'{}'::jsonb
    or coalesce(r->>'actor_trainer_id','') !~ uuid_re or coalesce(r->>'season_id','') !~ uuid_re then
    perform public.admin_setup_fail('invalid_request',422); end if;
  actor=(r->>'actor_trainer_id')::uuid; sid=(r->>'season_id')::uuid;
  scope=public.admin_setup_scope('participant_death_history',r);
  if op='state' then
    if coalesce(b,'{}'::jsonb)<>'{}'::jsonb or k is not null then perform public.admin_setup_fail('invalid_request',422); end if;
  else
    if k is null or length(k) not between 1 and 128 or jsonb_typeof(b) is distinct from 'object'
      or b-array['expected_revision','source_sha256','actual_deaths','wipe_deaths','segment_deaths']<>'{}'::jsonb
      or exists(select 1 from unnest(array['expected_revision','actual_deaths','wipe_deaths','segment_deaths']) f
        where jsonb_typeof(b->f) is distinct from 'number' or (b->>f)!~'^(0|[1-9][0-9]{0,8})$')
      or jsonb_typeof(b->'source_sha256') is distinct from 'string' or (b->>'source_sha256')!~'^[a-f0-9]{64}$' then
      perform public.admin_setup_fail('death_history_evidence_required',422); end if;
  end if;
  select * into t from public.trainers where id=actor for share;
  if not found or not t.globally_enabled then perform public.admin_setup_fail('trainer_disabled',403); end if;
  if op='confirm' then perform pg_advisory_xact_lock(hashtextextended(actor::text||scope||':'||k,0)); end if;
  -- Same order as participant wipe revivals and results: season, ordered roster, own row.
  select * into s from public.seasons where id=sid for no key update;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  if op='confirm' then perform 1 from public.season_players where season_id=sid order by id for update; end if;
  -- Only the caller's own participation: no other trainer can be addressed.
  select * into p from public.season_players where season_id=sid and trainer_id=actor;
  if not found then perform public.admin_setup_fail('participant_required',403); end if;
  if op='state' then return public.league_participant_death_state(p.id)||'{"replayed":false}'::jsonb; end if;
  if p.status<>'active' then perform public.admin_setup_fail('participant_inactive',403); end if;
  select * into old from public.admin_operation_receipts where actor_trainer_id=actor and operation_scope=scope and idempotency_key=k;
  if found then
    if old.request_hash<>encode(sha256(convert_to(r::text,'UTF8')),'hex') then perform public.admin_setup_fail('idempotency_conflict'); end if;
    return old.response_json||'{"replayed":true}'::jsonb;
  end if;
  select * into d from public.matchdays where id=s.current_matchday_id and season_id=sid;
  state=public.league_participant_death_state(p.id);
  if (b->>'expected_revision')::bigint<>(state->>'revision')::bigint then
    perform public.admin_setup_fail('death_history_revision_conflict'); end if;
  -- Exactly the admin reconciliation's order: bring the event history up to the
  -- current accepted save first, then re-evaluate from that state.
  perform public.league_track_deaths(p.id);
  select * into h from public.league_death_history where season_player_id=p.id for update;
  state=public.league_participant_death_state(p.id);
  if (state->>'known')::boolean then perform public.admin_setup_fail('death_history_already_confirmed'); end if;
  if not (state->>'can_confirm')::boolean then
    perform public.admin_setup_fail(case state->>'confirm_blocker'
      when 'death_history_closed' then 'death_history_closed'
      when 'save_missing' then 'death_history_source_unavailable'
      when 'death_history_pending_sync' then 'death_history_source_changed'
      else 'death_history_admin_required' end); end if;
  src=public.league_death_source(p.id);
  if b->>'source_sha256' is distinct from src->>'source_sha256' then perform public.admin_setup_fail('death_history_source_changed'); end if;
  proposed=state->'proposed';
  -- What the trainer saw is exactly what is confirmed, or nothing is.
  if (b->>'actual_deaths')::bigint<>(proposed->>'actual_deaths')::bigint
    or (b->>'wipe_deaths')::bigint<>(proposed->>'wipe_deaths')::bigint
    or (b->>'segment_deaths')::bigint<>(proposed->>'segment_deaths')::bigint then
    perform public.admin_setup_fail('death_history_changed'); end if;
  before=public.league_death_admin_state(p.id);
  select count(*) into recorded from public.league_effective_death_events(p.id);
  select count(*) into segment_recorded from public.league_effective_death_events(p.id) e
    where (e.matchday_id=d.id and e.phase='progression') or (e.phase='preseason' and (d.number=1 or d.id is null));
  insert into public.league_death_resolutions(id,season_player_id,actor_trainer_id,source_save_id,source_sha256,
    identity_revision_id,history_revision,before_state,confirmed_counts,reason,evidence)
  values(resolution_id,p.id,actor,(src->>'source_save_id')::uuid,src->>'source_sha256',(src->>'identity_revision_id')::uuid,
    h.revision+1,before,proposed||jsonb_build_object('self_confirmed',true,'expected_revision',b->'expected_revision'),
    'Confirmación del propio entrenador del historial observado',
    format('Partida oficial %s (revisión %s): %s muertes registradas en la Caja %s, %s revividos tras wipe, %s muertes de progresión. Sin cifras elegidas por el entrenador.',
      left(src->>'source_sha256',12),src->>'revision_number',recorded,p.dead_box_number,
      proposed->>'wipe_deaths',proposed->>'segment_deaths'));
  update public.league_death_history set actual_offset=(proposed->>'actual_deaths')::bigint-recorded,
    confirmed_wipe_deaths=(proposed->>'wipe_deaths')::bigint,confirmed_wipe_revision=(before->>'wipe_revision')::bigint,
    confirmed_unmapped_revives=public.league_unmapped_revives(p.id),segment_matchday_id=d.id,
    segment_offset=(proposed->>'segment_deaths')::bigint-segment_recorded,
    revision=revision+1,confirmed_at=clock_timestamp(),updated_at=clock_timestamp() where season_player_id=p.id;
  result=public.league_participant_death_state(p.id)||jsonb_build_object('replayed',false,'resolution_id',resolution_id);
  if not (result->>'known')::boolean then perform public.admin_setup_fail('death_history_inconsistent'); end if;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,payload)
  values(eid,sid,'DEATH_HISTORY_RECONCILED',actor,actor,'admin','death-history:'||resolution_id::text,
    jsonb_build_object('resolution_id',resolution_id,'season_player_id',p.id,'self_confirmed',true,
      'before',before,'after',result));
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
  values(oid,actor,sid,scope,k,encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

-- Before opening: the reasons the server would refuse, per trainer. Mirrors
-- the open/freeze checks (matchday_validate, league_freeze_death_segment);
-- the open itself stays authoritative.
create function public.league_open_readiness(sid uuid,actor uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare s public.seasons; d public.matchdays; state text; structure text; first boolean;
  reasons jsonb='[]'; players jsonb='[]'; observations jsonb; o jsonb; p record; codes jsonb; facts jsonb;
  death text; blocker text; operate boolean;
begin
  select * into s from public.seasons where id=sid;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  select * into d from public.matchdays where id=s.current_matchday_id and season_id=sid;
  structure=case when public.league_all_vs_all(sid) then 'all_vs_all'
    when public.initial_assignment_modern(sid) then 'divisions' else 'legacy' end;
  state=case when s.status in ('finished','archived') then 'finished'
    when s.status<>'active' then 'unavailable'
    when d.id is null and not exists(select 1 from public.matchdays where season_id=sid) then 'unprepared'
    when d.id is null then 'unavailable'
    when d.status='open' then 'open'
    when d.status='scheduled' then 'scheduled'
    else 'completed' end;
  if state='unavailable' then reasons=reasons||to_jsonb(case when s.status='draft' then 'season_not_active' else 'matchday_unavailable' end); end if;
  operate=exists(select 1 from public.trainers t where t.id=actor and t.globally_enabled and (t.is_admin or exists(
    select 1 from public.season_players sp where sp.season_id=sid and sp.trainer_id=actor and sp.status='active'
      and (d.id is null or exists(select 1 from public.participant_memberships_at(sid,d.number) m where m.season_player_id=sp.id)))));
  if state in ('unprepared','scheduled') then
    first=state='unprepared' or d.number=1;
    if state='unprepared' then
      blocker=public.league_first_matchday_blocker(sid);
      if blocker is not null then reasons=reasons||to_jsonb(blocker); end if;
    end if;
    -- J1 of a modern season also needs the observed progression (036).
    if first and public.initial_assignment_modern(sid) then observations=public.initial_assignment_observations(sid); end if;
    for p in select sp.id,sp.trainer_id,sp.status,sp.current_save_file_id,t.display_name,t.globally_enabled
      from public.season_players sp join public.trainers t on t.id=sp.trainer_id
      where sp.season_id=sid and (state='unprepared' or exists(select 1 from public.participant_memberships_at(sid,d.number) m
        where m.season_player_id=sp.id)) order by t.display_name,sp.id loop
      codes='[]';
      if not p.globally_enabled then codes=codes||'"trainer_disabled"'::jsonb; end if;
      if p.current_save_file_id is null then codes=codes||'"save_missing"'::jsonb;
      elsif observations is not null then
        select value into o from jsonb_array_elements(observations) where value->>'id'=p.id::text;
        if o->>'progress_state' is distinct from 'observed' then codes=codes||'"progress_unobserved"'::jsonb;
        elsif o->'cap_reached' is distinct from 'true'::jsonb then codes=codes||'"badges_missing"'::jsonb; end if;
      end if;
      facts=public.league_death_totals(p.id);
      death=case when (facts->>'known')::boolean then null
        -- The opening itself first brings the history up to the newest save.
        when facts->>'blocking_reason'='death_history_source_changed' then null
        when p.current_save_file_id is null then
          case when exists(select 1 from public.league_death_history h where h.season_player_id=p.id and h.actual_offset is not null)
            then null else 'death_history_baseline_required' end
        else facts->>'blocking_reason' end;
      if death is not null then codes=codes||to_jsonb(death); end if;
      players=players||jsonb_build_array(jsonb_build_object('season_player_id',p.id,'trainer_id',p.trainer_id,
        'display_name',p.display_name,'reasons',codes,
        'self_confirmable',coalesce(death in ('death_history_baseline_required','death_history_wipe_reconciliation_required')
          and p.current_save_file_id is not null,false)));
    end loop;
  end if;
  return jsonb_build_object('season_id',sid,'state',state,'structure',structure,
    'matchday',case when d.id is not null then jsonb_build_object('id',d.id,'number',d.number,'status',d.status,'revision',d.revision) end,
    'next_number',case when state='unprepared' then 1 when state in ('scheduled','open') then d.number end,
    'can_prepare',state='unprepared' and reasons='[]'::jsonb,
    'can_open',state in ('unprepared','scheduled') and reasons='[]'::jsonb
      and not exists(select 1 from jsonb_array_elements(players) x where x->'reasons'<>'[]'::jsonb),
    'can_operate',operate,'reasons',reasons,'participants',players);
end $$;

create function public.api_league_readiness(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare uuid_re text='^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$';
begin
  if jsonb_typeof(p_request) is distinct from 'object' or p_request-array['actor_trainer_id','season_id']<>'{}'::jsonb
    or coalesce(p_request->>'actor_trainer_id','') !~ uuid_re or coalesce(p_request->>'season_id','') !~ uuid_re then
    perform public.admin_setup_fail('invalid_request',422); end if;
  if not exists(select 1 from public.trainers where id=(p_request->>'actor_trainer_id')::uuid and globally_enabled) then
    perform public.admin_setup_fail('trainer_disabled',403); end if;
  return public.league_open_readiness((p_request->>'season_id')::uuid,(p_request->>'actor_trainer_id')::uuid);
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.league_all_vs_all(uuid)'::regprocedure,
    'public.initial_assignment_inputs(uuid)'::regprocedure,'public.initial_assignment_inputs_v078(uuid)'::regprocedure,
    'public.league_first_matchday_blocker(uuid)'::regprocedure,
    'public.api_league_prepare_first_matchday(jsonb)'::regprocedure,
    'public.league_participant_death_state(uuid)'::regprocedure,
    'public.api_participant_death_history(jsonb)'::regprocedure,
    'public.league_open_readiness(uuid,uuid)'::regprocedure,
    'public.api_league_readiness(jsonb)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
