-- 080: admin-only, audited enrollment into an active modern all-vs-all League.
-- Closed history, used configurations and existing competitors are never rewritten.
begin;

create table public.league_enrollments (
  id uuid not null unique default gen_random_uuid(),
  season_player_id uuid primary key,
  season_id uuid not null,
  trainer_id uuid not null,
  actor_trainer_id uuid not null references public.trainers(id),
  first_matchday_number integer not null check(first_matchday_number>0),
  roster_revision bigint not null check(roster_revision>0),
  initial_coins integer not null check(initial_coins>=0),
  closed_days jsonb not null check(jsonb_typeof(closed_days)='array'),
  enrolled_at timestamptz not null default clock_timestamp(),
  death_baseline jsonb,
  baseline_event_ids uuid[] not null default '{}',
  progress_baseline jsonb,
  foreign key(season_player_id,season_id,trainer_id) references public.season_players(id,season_id,trainer_id),
  check(death_baseline is null or jsonb_typeof(death_baseline)='object'),
  check(death_baseline is not null or cardinality(baseline_event_ids)=0),
  check(progress_baseline is null or jsonb_typeof(progress_baseline)='object')
);
alter table public.league_enrollments enable row level security;
alter table public.league_enrollments force row level security;
revoke all on public.league_enrollments from public,anon,authenticated,service_role;
grant select,insert,update on public.league_enrollments to service_role;
create function public.league_enrollment_immutable() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if (to_jsonb(new)-array['death_baseline','baseline_event_ids','progress_baseline']) is distinct from
     (to_jsonb(old)-array['death_baseline','baseline_event_ids','progress_baseline'])
    or (old.death_baseline is not null and (new.death_baseline,new.baseline_event_ids) is distinct from
      (old.death_baseline,old.baseline_event_ids))
    or (old.progress_baseline is not null and new.progress_baseline is distinct from old.progress_baseline) then
    perform public.admin_setup_fail('historical_artifact_immutable'); end if;
  return new;
end $$;
create trigger league_enrollment_immutable before update on public.league_enrollments
for each row execute function public.league_enrollment_immutable();
alter table public.coin_transactions drop constraint coin_transactions_type_chk;
alter table public.coin_transactions add constraint coin_transactions_type_chk check(transaction_type in
 ('matchday_reward','purchase','penalty','admin_adjustment','compensation','badge_reward','game_completion_reward','enrollment_credit'));
create unique index enrollment_credit_once on public.coin_transactions(reference_id)
  where transaction_type='enrollment_credit';

-- A derived configuration for this round, not an update of the frozen source.
-- The original common coin amount and sporting rules are retained; the extra
-- positions exist only for entrants eligible in this round.
create function public.league_enrollment_config(cid uuid, round_number integer)
returns public.season_config_versions
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare c public.season_config_versions; n integer; coins integer;
begin
  select * into c from public.season_config_versions where id=cid;
  if public.league_all_vs_all(c.season_id) and exists(select 1 from public.league_enrollments
      where season_id=c.season_id and first_matchday_number<=round_number) then
    select count(*) into n from public.season_players p where p.season_id=c.season_id
      and (p.status='active' or round_number<p.status_effective_matchday_number)
      and not exists(select 1 from public.league_enrollments e where e.season_player_id=p.id
        and e.first_matchday_number>round_number);
    coins=public.single_league_common_coins(c.coin_rewards_json);
    c.division_sizes=jsonb_build_object('A',n);
    select jsonb_object_agg(i::text,0),jsonb_object_agg(i::text,coins)
      into c.scoring_json,c.coin_rewards_json from generate_series(1,n) i;
    select roster_revision into c.roster_revision from public.season_admin_state where season_id=c.season_id;
  end if;
  return c;
end $$;

-- Reuse the complete existing validation and J1 preparation, replacing only
-- their config projection and the roster's explicit joining boundary.
do $$ declare definition text; original text; replacement text;
begin
  foreach original in array array['league_first_matchday_blocker(uuid)','api_league_prepare_first_matchday(jsonb)'] loop
    select pg_get_functiondef(('public.'||original)::regprocedure) into definition;
    replacement='select * into cfg from public.season_config_versions where season_id=sid and effective_from_matchday=1';
    if position(replacement in definition)=0 then raise exception 'unexpected 079 config contract: %',original; end if;
    definition=replace(definition,replacement,
      'select projected.* into cfg from public.season_config_versions source cross join lateral public.league_enrollment_config(source.id,1) projected where source.season_id=sid and source.effective_from_matchday=1');
    -- A projected composite cannot be row-locked. The season lock protects enrollment.
    definition=replace(definition,'source.effective_from_matchday=1 for share;','source.effective_from_matchday=1;');
    execute definition;
  end loop;
  select pg_get_functiondef('public.matchday_validate_v035(uuid,uuid,boolean)'::regprocedure) into definition;
  original='select * into c from public.season_config_versions where season_id=sid and effective_from_matchday<=d.number';
  if position(original in definition)=0 then raise exception 'unexpected 075 validator config'; end if;
  definition=replace(definition,original,
    'select projected.* into c from public.season_config_versions source cross join lateral public.league_enrollment_config(source.id,d.number) projected where source.season_id=sid and source.effective_from_matchday<=d.number');
  definition=replace(definition,'order by effective_from_matchday desc limit 1;','order by source.effective_from_matchday desc limit 1;');
  original='and (p.status=''active'' or d.number<p.status_effective_matchday_number)';
  if position(original in definition)=0 then raise exception 'unexpected 075 eligibility'; end if;
  definition=replace(definition,original,original||' and not exists(select 1 from public.league_enrollments e where e.season_player_id=p.id and e.first_matchday_number>d.number)');
  execute definition;
  select pg_get_functiondef('public.matchday_validate(uuid,uuid,boolean)'::regprocedure) into definition;
  original='where (p#>>''{_source,status}''=''active''';
  if position(original in definition)=0 then raise exception 'unexpected initial readiness eligibility'; end if;
  definition=replace(definition,original,
    'where not exists(select 1 from public.league_enrollments e where e.season_player_id=(p->>''id'')::uuid and e.first_matchday_number>1) and (p#>>''{_source,status}''=''active''');
  execute definition;
end $$;

alter function public.matchday_context(text,jsonb) rename to matchday_context_v079;
create function public.matchday_context(op text,r jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare ctx jsonb; c public.season_config_versions; n integer;
begin
  ctx=public.matchday_context_v079(op,r);
  -- Correction inputs already come from their immutable closing snapshot.
  if op<>'correct' and ctx#>>'{inputs,config,scoring_mode}'='league_net_v1' then
    n=(ctx#>>'{inputs,number}')::integer;
    c=public.league_enrollment_config((ctx#>>'{inputs,config,id}')::uuid,n);
    ctx=jsonb_set(ctx,'{inputs,config}',(ctx#>'{inputs,config}')||jsonb_build_object(
      'division_sizes',c.division_sizes,'scoring_json',c.scoring_json,'coin_rewards_json',c.coin_rewards_json));
  end if;
  return ctx;
end $$;

-- Initial observed occupants remain immutable evidence but are not invented
-- post-enrollment deaths. Lifecycle detection still sees those source events,
-- so merely syncing/moving an already dead Pokémon cannot charge it again.
alter function public.league_effective_death_events(uuid) rename to league_effective_death_events_v079;
create function public.league_effective_death_events(pid uuid) returns setof public.league_death_events
language sql stable security invoker set search_path=pg_catalog,public as $$
 select e.* from public.league_effective_death_events_v079(pid) e
 where not exists(select 1 from public.league_enrollments n where n.season_player_id=pid and e.id=any(n.baseline_event_ids))
$$;
create function public.league_enrollment_occupied(pid uuid, occupied integer) returns integer
language sql stable security invoker set search_path=pg_catalog,public as $$
 select occupied-count(distinct old.pokemon_entity_id)::integer
 from public.league_enrollments n join public.league_death_events old on old.id=any(n.baseline_event_ids)
 join public.pokemon_observations o on o.pokemon_entity_id=old.pokemon_entity_id
 join public.league_death_history h on h.last_identity_revision_id=o.revision_id and h.season_player_id=pid
 where n.season_player_id=pid and o.source='box' and o.box_number=h.dead_box_number
 and not exists(select 1 from public.league_effective_death_events(pid) current_event where current_event.pokemon_entity_id=old.pokemon_entity_id)
$$;
do $$ declare definition text; old_condition text='actual<(src->>''occupied'')::integer';
begin
 select pg_get_functiondef('public.api_admin_death_history(jsonb)'::regprocedure) into definition;
 if position(old_condition in definition)=0 then raise exception 'unexpected death reconciliation occupancy floor'; end if;
 execute replace(definition,old_condition,'actual<public.league_enrollment_occupied(pid,(src->>''occupied'')::integer)');
end $$;
alter function public.league_track_deaths(uuid) rename to league_track_deaths_v079;
do $$ declare definition text;
begin
 select pg_get_functiondef('public.league_track_deaths_v079(uuid)'::regprocedure) into definition;
 if position('public.league_effective_death_events(pid) e' in definition)=0 then raise exception 'unexpected death lifecycle contract'; end if;
 execute replace(definition,'public.league_effective_death_events(pid) e','public.league_effective_death_events_v079(pid) e');
end $$;
create function public.league_track_deaths(pid uuid) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare e public.league_enrollments; p public.season_players; src jsonb; facts jsonb; d public.matchdays;
begin
 select * into p from public.season_players where id=pid for update;
 select * into e from public.league_enrollments where season_player_id=pid for update;
 if e.season_player_id is null then perform public.league_track_deaths_v079(pid); return; end if;
 if e.death_baseline is null then
   src=public.league_death_source(pid);
   if src->>'valid' is distinct from 'true' then return; end if;
   -- The first accepted complete official source is an explicit observation
   -- boundary, not a claim that unobserved earlier deaths never happened.
   update public.league_death_history set last_identity_revision_id=null,blocking_reason=null where season_player_id=pid;
   perform public.league_track_deaths_v079(pid);
   update public.league_enrollments set death_baseline=src,
     baseline_event_ids=array(select id from public.league_effective_death_events_v079(pid) order by id)
     where season_player_id=pid returning * into e;
   update public.league_death_history h set actual_offset=0,segment_offset=0,
     confirmed_wipe_deaths=st.revived_after_wipe,confirmed_wipe_revision=coalesce((st.metadata->>'wipe_revision')::bigint,0),
     confirmed_unmapped_revives=public.league_unmapped_revives(pid),confirmed_at=clock_timestamp(),revision=h.revision+1
     from public.season_player_stats st where h.season_player_id=pid and st.season_player_id=pid;
   insert into public.activity_events(season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
     values(e.season_id,'LEAGUE_ENROLLMENT_DEATH_BASELINE',e.actor_trainer_id,'admin','enrollment-death:'||e.id,
       jsonb_build_object('enrollment_id',e.id,'season_player_id',pid,'source',src,'observed_before_baseline_event_ids',e.baseline_event_ids,
         'initial_net_points',0,'reason','First accepted official observation; earlier events retained for administrative review.'));
 else
   perform public.league_track_deaths_v079(pid);
 end if;
 -- An entrant into a day already in progress gets their OWN additional
 -- boundary. Existing participants' frozen periods and snapshots stay intact.
 select m.* into d from public.matchdays m where m.season_id=e.season_id and m.number=e.first_matchday_number;
 if d.status in ('open','scheduled') and exists(select 1 from public.matchday_start_evidence
     where matchday_id=d.id and first_started_at is not null)
   and not exists(select 1 from public.matchday_death_snapshots where matchday_id=d.id and season_player_id=pid) then
   facts=public.league_death_totals(pid);
   if facts->>'known' is distinct from 'true' then return; end if;
   insert into public.matchday_death_snapshots(season_id,matchday_id,season_player_id,starting_actual_deaths,
     ending_actual_deaths,segment_deaths,wipe_deaths,source_save_id,source_sha256,identity_revision_id,
     history_revision,wipe_revision,event_ids,resolution_ids,source_observed_at,confirmed_by_trainer_id)
   values(e.season_id,d.id,pid,0,0,0,0,(e.death_baseline->>'source_save_id')::uuid,e.death_baseline->>'source_sha256',
     (e.death_baseline->>'identity_revision_id')::uuid,(facts->>'revision')::bigint,(facts->>'wipe_revision')::bigint,
     '{}','{}',(e.death_baseline->>'observed_at')::timestamptz,e.actor_trainer_id);
 end if;
end $$;

-- Mark badges/completion already present in the first trustworthy official
-- observation as settled for ZERO. Subsequent new milestones use the exact
-- existing rewards/claims function. Other participants never enter this branch.
alter function public.settle_observed_progress_rewards(uuid,uuid) rename to settle_observed_progress_rewards_v079;
create function public.settle_observed_progress_rewards(sid uuid,tid uuid) returns integer
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare e public.league_enrollments; p public.season_players; ident public.pokemon_identity_revisions;
 saved public.save_files; parsed public.parsed_saves; progress jsonb; native jsonb; c public.season_config_versions;
 badge_count integer; key text;
begin
 select * into p from public.season_players where season_id=sid and trainer_id=tid for update;
 select * into e from public.league_enrollments where season_player_id=p.id for update;
 if e.season_player_id is not null and e.progress_baseline is null then
   select * into ident from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid order by revision_number desc limit 1;
   if ident.id is null or ident.save_file_id is distinct from p.current_save_file_id then return 0; end if;
   select * into saved from public.save_files where id=ident.save_file_id and season_id=sid and trainer_id=tid;
   select * into parsed from public.parsed_saves where id=ident.parsed_save_id and save_file_id=saved.id;
   progress=public.observed_save_progress(saved,parsed,tid);
   if progress is null then
     native=public.observed_native_progress(saved,parsed,tid);
     if native is null then return 0; end if;
     progress=jsonb_build_object('regions',case when native->>'model'='gym_badges' then
       jsonb_build_array(jsonb_build_object('badge_flags',native->'badge_flags')) else '[]'::jsonb end,
       'champion_defeated',native->'champion_defeated');
   end if;
   select * into c from public.season_config_versions where season_id=sid and effective_from_matchday<=e.first_matchday_number
     order by effective_from_matchday desc limit 1;
   if c.id is null then return 0; end if;
   select count(*) into badge_count from jsonb_array_elements(progress->'regions') r,
     lateral jsonb_array_elements(r->'badge_flags') f where f='true'::jsonb;
   for key in select 'badge:'||i from generate_series(1,badge_count) i
     union all select 'game_completion' where progress->'champion_defeated'='true'::jsonb loop
     insert into public.progress_reward_claims(season_id,trainer_id,season_player_id,reward_key,amount,
       config_version_id,identity_revision_id,source_hash,observed_progress)
       values(sid,tid,p.id,key,0,c.id,ident.id,saved.sha256,progress) on conflict do nothing;
   end loop;
   update public.league_enrollments set progress_baseline=jsonb_build_object('identity_revision_id',ident.id,
     'source_hash',saved.sha256,'observed_progress',progress) where season_player_id=p.id;
   insert into public.activity_events(season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
     values(sid,'LEAGUE_ENROLLMENT_PROGRESS_BASELINE',e.actor_trainer_id,'admin','enrollment-progress:'||e.id,
       jsonb_build_object('enrollment_id',e.id,'season_player_id',p.id,'identity_revision_id',ident.id,'source_hash',saved.sha256,
         'badges',badge_count,'coins',0,'reason','Observed milestones before the enrollment progression boundary; no retrospective rewards.'));
 end if;
 return public.settle_observed_progress_rewards_v079(sid,tid);
end $$;

-- All authoritative inputs affecting the preview are included in its hash.
create function public.league_enrollment_preview(sid uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare s public.seasons; d public.matchdays; c public.season_config_versions; days jsonb; candidates jsonb;
 total bigint; n integer; next_number integer; result jsonb; state jsonb;
begin
 select * into s from public.seasons where id=sid;
 if s.id is null or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
 if s.status<>'active' then perform public.admin_setup_fail('season_not_active'); end if;
 if not public.league_all_vs_all(sid) or not public.league_net_season(sid) then
   perform public.admin_setup_fail('enrollment_not_supported'); end if;
 select * into d from public.matchdays where season_id=sid and status in ('open','scheduled') order by number limit 1;
 if exists(select 1 from public.matchdays where season_id=sid and status='cancelled') then
   perform public.admin_setup_fail('enrollment_history_unproven'); end if;
 if exists(select 1 from public.matchdays m where m.season_id=sid and m.status='closed'
     and not exists(select 1 from public.matchday_snapshots snap where snap.matchday_id=m.id)) then
   perform public.admin_setup_fail('enrollment_history_unproven'); end if;
 next_number=coalesce(d.number,(select max(number)+1 from public.matchdays where season_id=sid and status='closed'),1);
 select * into c from public.season_config_versions where season_id=sid and effective_from_matchday<=next_number
   order by effective_from_matchday desc limit 1;
 if c.id is null or next_number>c.total_matchdays then perform public.admin_setup_fail('enrollment_championship_closed'); end if;
 select coalesce(jsonb_agg(jsonb_build_object('matchday_id',m.id,'number',m.number,'snapshot_revision',snap.revision,
     'coins',public.single_league_common_coins(snap.snapshot#>'{inputs,config,coin_rewards_json}')) order by m.number),'[]'::jsonb)
   into days from public.matchdays m join public.matchday_snapshots snap on snap.matchday_id=m.id
   where m.season_id=sid and m.status='closed';
 select coalesce(sum((x->>'coins')::bigint),0) into total from jsonb_array_elements(days) x;
 if total>2147483647 then perform public.admin_setup_fail('invalid_rewards'); end if;
 if d.id is null and not exists(select 1 from public.divisions where season_id=sid) then
   select count(*) into n from public.season_players where season_id=sid and status='active';
 else select count(*) into n from public.participant_memberships_at(sid,next_number); end if;
 select coalesce(jsonb_agg(jsonb_build_object('id',t.id,'display_name',t.display_name) order by t.id),'[]'::jsonb)
   into candidates from public.trainers t where t.globally_enabled and t.auth_user_id is not null
   and not exists(select 1 from public.season_players p where p.season_id=sid and p.trainer_id=t.id);
 result=jsonb_build_object('season_id',sid,'season_name',s.name,'eligible_trainers',candidates,
   'first_matchday_number',next_number,'matchday_id',d.id,'matchday_status',d.status,'closed_matchdays',jsonb_array_length(days),
   'initial_coins',total,'initial_points','0','new_matchups',n);
 state=result||jsonb_build_object('closed_days',days,'external_facts',public.matchday_external_facts(sid),
   'admin_state',(select to_jsonb(a) from public.season_admin_state a where season_id=sid),
   'days',(select jsonb_agg(to_jsonb(m) order by number) from public.matchdays m where season_id=sid),
   'config',to_jsonb(c));
 return result||jsonb_build_object('preview_hash',encode(sha256(convert_to(state::text,'UTF8')),'hex'),'closed_days',days);
end $$;
create function public.api_admin_league_enrollment(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare op text=p_request->>'operation'; r jsonb=p_request->'request'; b jsonb=r->'body';
 sid uuid; actor uuid; tid uuid; pid uuid; division uuid; e public.league_enrollments; preview jsonb;
 cached jsonb; result jsonb; n integer; did uuid;
begin
 if op is null or op not in ('preview','confirm') or jsonb_typeof(r) is distinct from 'object'
   or r-array['actor_trainer_id','season_id','body','idempotency_key']<>'{}'::jsonb then
   perform public.admin_setup_fail('invalid_request',422); end if;
 begin sid=(r->>'season_id')::uuid;actor=(r->>'actor_trainer_id')::uuid;
 exception when invalid_text_representation then perform public.admin_setup_fail('invalid_request',422); end;
 if sid is null or actor is null then perform public.admin_setup_fail('invalid_request',422); end if;
 if op='preview' then
   perform public.admin_setup_principal(actor);
   return public.league_enrollment_preview(sid)-'closed_days';
 end if;
 if jsonb_typeof(b) is distinct from 'object' or b-array['trainer_id','preview_hash']<>'{}'::jsonb
   or coalesce(b->>'preview_hash','') !~ '^[a-f0-9]{64}$' then perform public.admin_setup_fail('invalid_request',422); end if;
 begin tid=(b->>'trainer_id')::uuid;
 exception when invalid_text_representation then perform public.admin_setup_fail('invalid_request',422); end;
 if tid is null then perform public.admin_setup_fail('invalid_request',422); end if;
 cached=public.admin_setup_begin('enroll_participant',r); if cached is not null then return cached; end if;
 if exists(select 1 from public.season_players where season_id=sid and trainer_id=tid) then
   perform public.admin_setup_fail('participant_exists'); end if;
 perform 1 from public.trainers where id=tid and globally_enabled and auth_user_id is not null for share;
 if not found then perform public.admin_setup_fail('trainer_unavailable'); end if;
 preview=public.league_enrollment_preview(sid);
 if b->>'preview_hash' is distinct from preview->>'preview_hash' then perform public.admin_setup_fail('enrollment_preview_stale'); end if;
 n=(preview->>'first_matchday_number')::integer;did=(preview->>'matchday_id')::uuid;
 insert into public.season_players(season_id,trainer_id) values(sid,tid) returning id into pid;
 insert into public.season_player_stats(season_player_id,season_id,trainer_id) values(pid,sid,tid);
 update public.season_admin_state set roster_revision=roster_revision+1,setup_revision=setup_revision+1 where season_id=sid;
 insert into public.league_enrollments(season_player_id,season_id,trainer_id,actor_trainer_id,first_matchday_number,
     roster_revision,initial_coins,closed_days)
   select pid,sid,tid,actor,n,roster_revision,(preview->>'initial_coins')::integer,preview->'closed_days'
   from public.season_admin_state where season_id=sid returning * into e;
 if e.initial_coins>0 then
   insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type,
       reference_type,reference_id,created_by_trainer_id,metadata)
     values(sid,tid,pid,e.initial_coins,'enrollment_credit','league_enrollment',e.id,actor,
       jsonb_build_object('closed_days',e.closed_days,'initial_net_points',0));
 end if;
 select id into division from public.divisions where season_id=sid and code='A';
 if division is not null then
   insert into public.division_memberships(season_id,season_player_id,division_id,effective_from_matchday_number,reason,metadata)
     values(sid,pid,division,n,'admin',jsonb_build_object('enrollment_id',e.id));
   if did is not null then
     insert into public.matches(season_id,matchday_id,division_id,player_a_id,player_b_id)
       select sid,did,division,least(pid,m.season_player_id),greatest(pid,m.season_player_id)
       from public.participant_memberships_at(sid,n) m where m.season_player_id<>pid;
     -- Invalidate outstanding open/close/result previews, preserving every old match.
     update public.matchdays set revision=revision+1,results_revision=results_revision+1 where id=did;
     -- Structural pairing validation only. Opening/playing still uses the full
     -- save/badge/death readiness checks after the entrant registers a save.
     perform public.matchday_validate_v035(sid,did,false);
   end if;
 end if;
 result=public.admin_setup_finish('enroll_participant',r,sid,pid,
   jsonb_build_object('enrollment_id',e.id,'preview',preview-'eligible_trainers','new_matchups',preview->'new_matchups'));
 return result;
end $$;

-- Explicit join boundaries and pending baseline changes invalidate competing
-- previews. The prior external-facts hash continues protecting all old inputs.
alter function public.matchday_external_facts(uuid) rename to matchday_external_facts_v079;
create function public.matchday_external_facts(sid uuid) returns text
language sql stable security invoker set search_path=pg_catalog,public as $$
 select encode(sha256(convert_to(public.matchday_external_facts_v079(sid)||coalesce((
   select jsonb_agg(to_jsonb(e) order by e.season_player_id)::text from public.league_enrollments e where e.season_id=sid),'[]'),'UTF8')),'hex')
$$;

do $$ declare f regprocedure;
begin
 foreach f in array array[
 'public.league_enrollment_immutable()'::regprocedure,'public.league_enrollment_config(uuid,integer)'::regprocedure,
 'public.matchday_context(text,jsonb)'::regprocedure,'public.matchday_context_v079(text,jsonb)'::regprocedure,
 'public.league_effective_death_events(uuid)'::regprocedure,'public.league_effective_death_events_v079(uuid)'::regprocedure,
 'public.league_enrollment_occupied(uuid,integer)'::regprocedure,
 'public.league_track_deaths(uuid)'::regprocedure,'public.league_track_deaths_v079(uuid)'::regprocedure,
 'public.settle_observed_progress_rewards(uuid,uuid)'::regprocedure,'public.settle_observed_progress_rewards_v079(uuid,uuid)'::regprocedure,
 'public.league_enrollment_preview(uuid)'::regprocedure,'public.api_admin_league_enrollment(jsonb)'::regprocedure,
 'public.matchday_external_facts(uuid)'::regprocedure,'public.matchday_external_facts_v079(uuid)'::regprocedure] loop
   execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
   execute format('grant execute on function %s to service_role',f);
 end loop;
end $$;
commit;
