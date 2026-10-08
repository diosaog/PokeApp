-- Final 10.5: prospective live rewards, eligible normal League operations,
-- championship residual decisions and first-fix Team Lock evidence.
-- No historical backfill, repricing, owner fixture or Cup mutation.
begin;

create table public.season_reward_rule_revisions (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  revision bigint not null check(revision > 0),
  badge_reward_coins integer not null check(badge_reward_coins >= 0),
  game_completion_reward_coins integer not null check(game_completion_reward_coins >= 0),
  effective_at timestamptz not null default clock_timestamp(),
  actor_trainer_id uuid not null references public.trainers(id) on delete restrict,
  unique(season_id,revision), unique(id,season_id)
);
create index reward_rule_actor_idx on public.season_reward_rule_revisions(actor_trainer_id);
alter table public.season_reward_rule_revisions enable row level security;
revoke all on public.season_reward_rule_revisions from public,anon,authenticated,service_role;
grant select,insert,delete on public.season_reward_rule_revisions to service_role;
create trigger reward_rule_immutable before update on public.season_reward_rule_revisions
  for each row execute function public.lifecycle_artifact_immutable();
alter table public.progress_reward_claims add column reward_rule_revision_id uuid;
alter table public.progress_reward_claims add constraint progress_reward_rule_scope
  foreign key(reward_rule_revision_id,season_id) references public.season_reward_rule_revisions(id,season_id);
create index progress_reward_rule_idx on public.progress_reward_claims(reward_rule_revision_id,season_id);

create function public.live_reward_rules(sid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare s public.seasons; c public.season_config_versions; rules public.season_reward_rule_revisions;
  day_number integer;
begin
  select * into s from public.seasons where id=sid;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  select coalesce((select number from public.matchdays where id=s.current_matchday_id and season_id=sid),
    (select max(number) from public.matchdays where season_id=sid),1) into day_number;
  select * into c from public.season_config_versions where season_id=sid and effective_from_matchday<=day_number
    order by effective_from_matchday desc limit 1;
  select * into rules from public.season_reward_rule_revisions where season_id=sid order by revision desc limit 1;
  return jsonb_build_object('season_id',sid,'revision',coalesce(rules.revision,0),
    'config_revision',coalesce((select config_revision from public.season_admin_state where season_id=sid),0),
    'badge_reward_coins',coalesce(rules.badge_reward_coins,(c.rules_json->>'badge_reward_coins')::integer,4),
    'game_completion_reward_coins',coalesce(rules.game_completion_reward_coins,(c.rules_json->>'game_completion_reward_coins')::integer,12),
    'effective_at',rules.effective_at,'editable',s.status in ('draft','active'));
end $$;

create function public.api_admin_live_rules_read(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  perform public.admin_setup_principal((p_request->>'actor_trainer_id')::uuid);
  perform 1 from public.seasons where id=(p_request->>'season_id')::uuid for share;
  return public.live_reward_rules((p_request->>'season_id')::uuid);
end $$;

create function public.api_admin_live_rules_update(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare r jsonb=p_request; b jsonb=r->'body'; sid uuid=(r->>'season_id')::uuid;
  cached jsonb; before_rules jsonb; rid uuid; k text;
begin
  if jsonb_typeof(b) is distinct from 'object'
    or b-array['expected_revision','expected_config_revision','badge_reward_coins','game_completion_reward_coins']<>'{}'
    or not(b ?& array['expected_revision','expected_config_revision','badge_reward_coins','game_completion_reward_coins']) then
    perform public.admin_setup_fail('invalid_request',422); end if;
  foreach k in array array['expected_revision','expected_config_revision','badge_reward_coins','game_completion_reward_coins'] loop
    if jsonb_typeof(b->k) is distinct from 'number' or b->>k !~ '^(0|[1-9][0-9]*)$'
      or (b->>k)::numeric>2147483647 then perform public.admin_setup_fail('invalid_request',422); end if;
  end loop;
  -- Uses the existing season/ordered participant locks. Every observation reward
  -- batch also holds its participant lock, giving a single cutover without reprice.
  cached=public.admin_setup_begin('live_rules',r); if cached is not null then return cached; end if;
  before_rules=public.live_reward_rules(sid);
  if not (before_rules->>'editable')::boolean then perform public.admin_setup_fail('config_window_closed'); end if;
  if (b->>'expected_revision')::bigint<>(before_rules->>'revision')::bigint
    or (b->>'expected_config_revision')::bigint<>(before_rules->>'config_revision')::bigint then
    perform public.admin_setup_fail('stale_revision'); end if;
  insert into public.season_reward_rule_revisions(season_id,revision,badge_reward_coins,game_completion_reward_coins,actor_trainer_id)
    values(sid,(before_rules->>'revision')::bigint+1,(b->>'badge_reward_coins')::integer,
      (b->>'game_completion_reward_coins')::integer,(r->>'actor_trainer_id')::uuid) returning id into rid;
  update public.season_admin_state set config_revision=config_revision+1,setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('live_rules',r,sid,rid,
    jsonb_build_object('before',before_rules,'after',public.live_reward_rules(sid)));
end $$;

-- Only the normal operations are widened. Administrative/exceptional functions
-- retain their existing principal guard, including all old entry points.
create function public.league_operation_principal(actor uuid,sid uuid,did uuid default null) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare t public.trainers; s public.seasons; p public.season_players; d public.matchdays;
begin
  select * into t from public.trainers where id=actor for share;
  if not found or not t.globally_enabled then perform public.admin_setup_fail('trainer_disabled',403); end if;
  select * into s from public.seasons where id=sid for no key update;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  perform 1 from public.season_players where season_id=sid order by id for update;
  if t.is_admin then return; end if;
  select * into p from public.season_players where season_id=sid and trainer_id=actor;
  if not found then perform public.admin_setup_fail('participant_required',403); end if;
  if p.status<>'active' then perform public.admin_setup_fail('participant_inactive',403); end if;
  select * into d from public.matchdays where id=coalesce(did,s.current_matchday_id) and season_id=sid;
  if not found or not exists(select 1 from public.participant_memberships_at(sid,d.number) m where m.season_player_id=p.id) then
    perform public.admin_setup_fail('participant_ineligible',403); end if;
end $$;

alter function public.admin_setup_begin(text,jsonb) rename to admin_setup_begin_v040;
create function public.admin_setup_begin(op text,r jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare actor uuid=(r->>'actor_trainer_id')::uuid; sid uuid=(r->>'season_id')::uuid;
  t public.trainers; old public.admin_operation_receipts;
  scope text=public.admin_setup_scope(op,r); k text=r->>'idempotency_key';
begin
  if not coalesce(op in ('matchday_open','matchday_close') or (op='lifecycle' and r->>'operation'='finish'),false) then
    return public.admin_setup_begin_v040(op,r); end if;
  select * into t from public.trainers where id=actor for share;
  if not found or not t.globally_enabled then perform public.admin_setup_fail('trainer_disabled',403); end if;
  if t.is_admin then return public.admin_setup_begin_v040(op,r); end if;
  if op='matchday_close' and r#>'{body,tie_resolution}' is not null and r#>'{body,tie_resolution}'<>'null'::jsonb then
    perform public.admin_setup_fail('admin_required',403); end if;
  if k is null or length(k) not between 1 and 128 then perform public.admin_setup_fail('invalid_request',422); end if;
  perform pg_advisory_xact_lock(hashtextextended(actor::text||scope||':'||k,0));
  -- Check membership even for a receipt replay. A successful retry does not
  -- reopen history or authorize an inactive participant after withdrawal.
  perform public.league_operation_principal(actor,sid,(r->>'resource_id')::uuid);
  perform 1 from public.season_admin_state where season_id=sid;
  if not found then perform public.admin_setup_fail('setup_incomplete'); end if;
  select * into old from public.admin_operation_receipts where actor_trainer_id=actor and operation_scope=scope and idempotency_key=k;
  if found then
    if old.request_hash<>encode(sha256(convert_to(r::text,'UTF8')),'hex') then perform public.admin_setup_fail('idempotency_conflict'); end if;
    return old.response_json||'{"replayed":true}'::jsonb;
  end if;
  return null;
end $$;

create or replace function public.api_admin_championship_read(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare sid uuid=(p_request->>'season_id')::uuid;
begin
  perform public.league_operation_principal((p_request->>'actor_trainer_id')::uuid,sid);
  return public.championship_context(sid)-'_source_snapshot_revision_id'-'_resolution';
end $$;

-- The existing immutable resolution table now records either approved exception.
-- Its default preserves old BO3 rows and old receipt semantics without rewriting them.
alter table public.league_championship_resolutions add column resolution_type text not null default 'championship_bo3'
  check(resolution_type in ('championship_bo3','championship_residual'));

-- Remaining functions below preserve source validation and frozen certificates.

create or replace function public.settle_observed_progress_rewards(sid uuid,tid uuid) returns integer
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; saved public.save_files; parsed public.parsed_saves;
  ident public.pokemon_identity_revisions; c public.season_config_versions; progress jsonb;
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
  if progress is null then return 0; end if;
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

create or replace function public.championship_context(sid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare s public.seasons; source public.matchday_snapshot_revisions; frozen public.league_finalizations;
  resolution public.league_championship_resolutions; result jsonb; players jsonb; leaders jsonb; candidates jsonb;
  facts jsonb; fingerprint text; champion uuid; winner uuid; minimum_deaths bigint;
  mode text; state text; reason text; setup bigint; row jsonb;
begin
  select * into s from public.seasons where id=sid;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  select setup_revision into setup from public.season_admin_state where season_id=sid;
  result=jsonb_build_object('season_id',sid,'state','incomplete','setup_revision',coalesce(setup,0),
    'input_hash',null,'players','[]'::jsonb,'tied_player_ids','[]'::jsonb,'champion_trainer_id',null,
    'resolution_type',null,'finalist_status','OWNER_DECISION_REQUIRED','blocking_reason','competition_incomplete');
  select * into frozen from public.league_finalizations where season_id=sid;
  if found then
    return frozen.title||jsonb_build_object('state','frozen','setup_revision',setup);
  end if;
  if s.status in ('finished','archived') then
    return result||jsonb_build_object('state','legacy','blocking_reason','legacy_title_uncertified');
  end if;
  if s.status<>'active' then return result; end if;
  begin
    source=public.championship_final_source(sid);
  exception when sqlstate 'PT409' then
    if sqlerrm='competition_incomplete' then return result; end if;
    raise;
  end;
  -- Reject malformed captures instead of allowing the accumulated view's legacy
  -- COALESCEs to turn missing official penalties into zero.
  for row in select v from public.matchday_snapshots x,
    jsonb_array_elements(x.snapshot->'standings') v where x.season_id=sid loop
    if jsonb_typeof(row->'points_awarded') is distinct from 'number'
      or row->>'points_awarded' !~ '^[0-9]+$'
      or coalesce(row#>>'{penalties,points_reduction}','') !~ '^[0-9]+(\.[0-9]+)?$'
      or coalesce(row#>>'{penalties,dead_points_penalty}','') !~ '^[0-9]+(\.[0-9]+)?$' then
      perform public.admin_setup_fail('historical_source_invalid'); end if;
  end loop;
  -- Eligibility remains the official final-day membership, including irreversible
  -- participant exit cutoffs. GENERAL still retains every historical participant.
  select coalesce(jsonb_agg(jsonb_build_object('season_player_id',p.id,'trainer_id',p.trainer_id,
      'display_name',t.display_name,'total_points',points.sanctioned_points::text,
      'adjusted_deaths',case when jsonb_typeof(r#>'{penalties,dead_count}')='number'
        and r#>>'{penalties,dead_count}' ~ '^[0-9]+$'
        and r#>'{penalties,dead_count}'=inputs->'dead_count'
        then (r#>>'{penalties,dead_count}')::bigint end)
      order by points.sanctioned_points desc,p.id),'[]') into players
    from jsonb_array_elements(source.snapshot->'standings') r
    join public.season_players p on p.id=(r->>'trainer_id')::uuid and p.season_id=sid
    join public.trainers t on t.id=p.trainer_id
    left join public.public_sanctioned_points points on points.season_id=sid and points.season_player_id=p.id
    left join lateral (select x as inputs from jsonb_array_elements(source.snapshot#>'{inputs,players}') x
      where x->>'id'=p.id::text) i on true;
  if jsonb_array_length(players)=0 or jsonb_array_length(players)<>jsonb_array_length(source.snapshot->'standings')
    or exists(select 1 from jsonb_array_elements(players) p where p->>'total_points' is null
      or p->>'total_points' !~ '^-?[0-9]+(\.[0-9]+)?$') then
    perform public.admin_setup_fail('historical_source_invalid'); end if;
  -- Bind every official day/revision and full frozen inputs, not just the final
  -- day's score or a live setup revision. Names and rendering order cannot decide.
  select jsonb_agg(jsonb_build_object('id',h.id,'day_id',h.matchday_id,'revision',h.revision,
      'snapshot',h.snapshot) order by d.number) into facts
    from public.matchday_snapshots x join public.matchday_snapshot_revisions h
      on h.matchday_id=x.matchday_id and h.revision=x.revision
    join public.matchdays d on d.id=x.matchday_id where x.season_id=sid;
  fingerprint=encode(sha256(convert_to(jsonb_build_object('rule','final_accumulated_points_v1',
    'season_id',sid,'days',facts,'players',(select jsonb_agg(p-'display_name' order by p->>'season_player_id')
      from jsonb_array_elements(players) p))::text,'UTF8')),'hex');
  select jsonb_agg(p->'season_player_id' order by p->>'season_player_id') into leaders
    from jsonb_array_elements(players) p where (p->>'total_points')::numeric=(players->0->>'total_points')::numeric;
  if jsonb_array_length(leaders)>=3 then fingerprint=encode(sha256(convert_to(fingerprint||':3plus_adjusted_deaths_v2','UTF8')),'hex'); end if;
  state='ready';
  if jsonb_array_length(leaders)=1 then
    winner=(leaders->>0)::uuid; mode='unique_points';
  elsif jsonb_array_length(leaders)=2 then
    select * into resolution from public.league_championship_resolutions
      where season_id=sid and input_hash=fingerprint;
    if found then
      if resolution.resolution_type<>'championship_bo3' or not(leaders ? resolution.winner_season_player_id::text) then
        perform public.admin_setup_fail('historical_source_invalid'); end if;
      winner=resolution.winner_season_player_id; mode='championship_bo3';
    else state='bo3_required'; reason='championship_bo3_required'; end if;
  elsif jsonb_array_length(leaders)>=3 then
    if exists(select 1 from jsonb_array_elements(players) p where leaders ? (p->>'season_player_id')
      and p->'adjusted_deaths'='null'::jsonb) then
      state='owner_decision_required'; reason='championship_deaths_unavailable';
    else
      select min((p->>'adjusted_deaths')::bigint) into minimum_deaths from jsonb_array_elements(players) p
        where leaders ? (p->>'season_player_id');
      if (select count(*) from jsonb_array_elements(players) p where leaders ? (p->>'season_player_id')
        and (p->>'adjusted_deaths')::bigint=minimum_deaths)=1 then
        select (p->>'season_player_id')::uuid into winner from jsonb_array_elements(players) p
          where leaders ? (p->>'season_player_id') and (p->>'adjusted_deaths')::bigint=minimum_deaths;
        mode=case when jsonb_array_length(leaders)=3 then 'triple_adjusted_deaths' else 'multiple_adjusted_deaths' end;
      else
        select jsonb_agg(p->'season_player_id' order by p->>'season_player_id') into candidates
          from jsonb_array_elements(players) p where leaders ? (p->>'season_player_id')
            and (p->>'adjusted_deaths')::bigint=minimum_deaths;
        select * into resolution from public.league_championship_resolutions where season_id=sid and input_hash=fingerprint;
        if found then
          if resolution.resolution_type<>'championship_residual' or not(candidates ? resolution.winner_season_player_id::text) then
            perform public.admin_setup_fail('historical_source_invalid'); end if;
          winner=resolution.winner_season_player_id; mode='championship_residual';
        else state='residual_required'; reason='championship_residual_required'; end if;
      end if;
    end if;
  else state='owner_decision_required'; reason='championship_many_tied'; end if;
  select trainer_id into champion from public.season_players where id=winner and season_id=sid;
  return result||jsonb_build_object('state',state,'input_hash',fingerprint,'players',players,
    'tied_player_ids',coalesce(candidates,case when jsonb_array_length(leaders)>1 then leaders else '[]'::jsonb end),
    'champion_trainer_id',champion,'resolution_type',mode,'blocking_reason',reason,
    '_source_snapshot_revision_id',source.id,'_resolution',case when resolution.id is not null
      then jsonb_build_object('id',resolution.id,'type',resolution.resolution_type,'winner_season_player_id',winner,
        'reason',resolution.reason,'actor_trainer_id',resolution.actor_trainer_id,'created_at',resolution.created_at) end);
end $$;

create or replace function public.api_admin_season_lifecycle(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare r jsonb=p_request; b jsonb=r->'body'; op text=r->>'operation'; sid uuid=(r->>'season_id')::uuid;
  actor uuid=(r->>'actor_trainer_id')::uuid; s public.seasons; frozen public.league_finalizations;
  cached jsonb; review jsonb; result jsonb; artifact jsonb; stamp timestamptz; destination text;
  aid uuid; hid uuid; fid uuid; rid uuid; oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid(); label text;
begin
  if op='discard' then return public.api_admin_season_lifecycle_v036(r); end if;
  if op is null or op not in ('finish','archive','championship_bo3','championship_residual') or sid is null
    or jsonb_typeof(b) is distinct from 'object'
    or jsonb_typeof(b->'expected_revision') is distinct from 'number'
    or b->>'expected_revision' !~ '^[0-9]+$'
    or (op='finish' and (b-array['expected_revision','input_hash']<>'{}'
      or (b ? 'input_hash' and coalesce(b->>'input_hash','') !~ '^[a-f0-9]{64}$')))
    or (op in ('championship_bo3','championship_residual') and (b-array['expected_revision','input_hash','winner_season_player_id','reason']<>'{}'
      or coalesce(b->>'input_hash','') !~ '^[a-f0-9]{64}$'
      or coalesce(b->>'winner_season_player_id','') !~ '^[a-f0-9-]{36}$'
      or jsonb_typeof(b->'reason') is distinct from 'string' or length(btrim(b->>'reason')) not between 1 and 500))
    or (op='archive' and (b-array['expected_revision','label']<>'{}' or
      (b->'label' is not null and b->'label'<>'null' and (jsonb_typeof(b->'label')<>'string'
        or length(btrim(b->>'label')) not between 1 and 120)))) then
    perform public.admin_setup_fail('invalid_request',422); end if;
  -- Preserve historical finish/archive receipt replay. A missing finish hash can
  -- only recover an exact successful receipt; it never authorizes a new finish.
  cached=public.admin_setup_begin('lifecycle',r); if cached is not null then return cached; end if;
  if op='finish' and not(b ? 'input_hash') then perform public.admin_setup_fail('invalid_request',422); end if;
  select * into s from public.seasons where id=sid;
  if op in ('finish','championship_bo3','championship_residual') and s.status<>'active' then
    perform public.admin_setup_fail('season_not_active'); end if;
  if op='archive' and s.status<>'finished' then perform public.admin_setup_fail('season_not_finished'); end if;
  perform public.admin_setup_cas(sid,b);
  stamp=clock_timestamp();
  if op in ('finish','championship_bo3','championship_residual') then
    review=public.championship_context(sid);
    if review->>'state'='incomplete' then perform public.admin_setup_fail('competition_incomplete'); end if;
    if b->>'input_hash' is distinct from review->>'input_hash' then
      perform public.admin_setup_fail('championship_review_stale'); end if;
    if op in ('championship_bo3','championship_residual') then
      if (op='championship_bo3' and review->>'state'<>'bo3_required') or (op='championship_residual' and review->>'state'<>'residual_required') then
        perform public.admin_setup_fail(case when op='championship_bo3' then 'championship_bo3_not_required' else 'championship_resolution_not_required' end); end if;
      if not((review->'tied_player_ids') ? (b->>'winner_season_player_id')) then
        perform public.admin_setup_fail('invalid_championship_winner'); end if;
      insert into public.league_championship_resolutions(season_id,input_hash,winner_season_player_id,reason,actor_trainer_id,resolution_type)
        values(sid,review->>'input_hash',(b->>'winner_season_player_id')::uuid,btrim(b->>'reason'),actor,op) returning id into rid;
      destination='active';
    else
      if review->>'state'='bo3_required' then perform public.admin_setup_fail('championship_bo3_required'); end if;
      if review->>'state'<>'ready' or review->>'champion_trainer_id' is null then
        perform public.admin_setup_fail('championship_unresolved'); end if;
      artifact=public.championship_artifact(sid,review,stamp);
      insert into public.league_finalizations(season_id,source_snapshot_revision_id,input_hash,title,artifact,actor_trainer_id,created_at)
        values(sid,(review->>'_source_snapshot_revision_id')::uuid,review->>'input_hash',review,artifact,actor,stamp) returning id into fid;
      update public.seasons set status='finished',finished_at=stamp where id=sid;
      destination='finished';
    end if;
  else
    select * into frozen from public.league_finalizations where season_id=sid;
    if not found then perform public.admin_setup_fail('legacy_title_uncertified'); end if;
    if frozen.title->>'champion_trainer_id' is null or frozen.artifact#>>'{league,champion_trainer_id}'
      is distinct from frozen.title->>'champion_trainer_id' then perform public.admin_setup_fail('historical_source_invalid'); end if;
    if exists(select 1 from public.season_archive_snapshots where season_id=sid)
      or exists(select 1 from public.hall_of_fame_entries where season_id=sid and competition_type='league') then
      perform public.admin_setup_fail('historical_artifact_exists'); end if;
    label=coalesce(btrim(b->>'label'),frozen.artifact#>>'{season,name}'); aid=gen_random_uuid(); hid=gen_random_uuid();
    artifact=jsonb_set(jsonb_set(frozen.artifact,'{season,archived_at}',to_jsonb(stamp)),
      '{season,label}',to_jsonb(label));
    update public.seasons set status='archived',archived_at=stamp where id=sid;
    insert into public.season_archive_snapshots(id,season_id,snapshot_schema_version,snapshot,created_by_trainer_id,
      source_snapshot_revision_id,checksum,label,created_at)
      values(aid,sid,2,artifact,actor,frozen.source_snapshot_revision_id,
        encode(sha256(convert_to(artifact::text,'UTF8')),'hex'),label,stamp);
    insert into public.hall_of_fame_entries(id,season_id,competition_type,champion_trainer_id,finalist_trainer_id,
      finalized_at,team_snapshot,archive_snapshot_id,source_snapshot_revision_id,source_team_lock_id)
      values(hid,sid,'league',(frozen.title->>'champion_trainer_id')::uuid,null,stamp,
        artifact#>'{league,team}',aid,frozen.source_snapshot_revision_id,(artifact#>>'{league,source_team_lock_id}')::uuid);
    destination='archived'; fid=frozen.id;
  end if;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(eid,sid,case when op in ('championship_bo3','championship_residual') then 'LEAGUE_'||upper(op) else 'SEASON_'||upper(destination) end,
      actor,'admin','season-lifecycle:'||oid::text,jsonb_build_object('operation_id',oid,'before',s.status,'after',destination,
        'type',op,'reason',b->>'reason',
        'winner_season_player_id',b->>'winner_season_player_id','input_hash',b->>'input_hash',
        'finalization_id',fid,'resolution_id',rid,'archive_id',aid,'hall_id',hid));
  select jsonb_build_object('operation_id',oid,'event_id',eid,'season_id',sid,'operation',op,'state',destination,
    'actor_trainer_id',actor,'changed_at',stamp,'setup_revision',setup_revision,'current_matchday_id',s.current_matchday_id,
    'archive_id',aid,'hall_id',hid,'replayed',false) into result from public.season_admin_state where season_id=sid;
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,actor,sid,public.admin_setup_scope('lifecycle',r),r->>'idempotency_key',encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

-- First-event evidence is separate from replaceable current snapshots. Existing
-- matchdays/locks are not backfilled from an unreliable replacement timestamp.
create table public.matchday_start_evidence (
  matchday_id uuid primary key references public.matchdays(id) on delete cascade,
  first_started_at timestamptz
);
create table public.team_lock_first_fixations (
  lock_id uuid primary key references public.team_locks(id) on delete cascade,
  first_fixed_at timestamptz not null,
  timing_status text not null check(timing_status in ('on_time','late','unknown'))
);
alter table public.matchday_start_evidence enable row level security;
alter table public.team_lock_first_fixations enable row level security;
revoke all on public.matchday_start_evidence,public.team_lock_first_fixations from public,anon,authenticated,service_role;
grant select,insert,update,delete on public.matchday_start_evidence to service_role;
grant select,insert,delete on public.team_lock_first_fixations to service_role;
create trigger first_fixation_immutable before update on public.team_lock_first_fixations
  for each row execute function public.lifecycle_artifact_immutable();

create function public.first_start_immutable() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if new.matchday_id<>old.matchday_id or old.first_started_at is not null or new.first_started_at is null then
    perform public.admin_setup_fail('historical_artifact_immutable'); end if;
  return new;
end $$;
create trigger first_start_immutable before update on public.matchday_start_evidence
  for each row execute function public.first_start_immutable();

create function public.record_first_matchday_start() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if TG_OP='INSERT' then
    if new.status in ('scheduled','open') and new.closed_at is null then
      insert into public.matchday_start_evidence(matchday_id,first_started_at)
        values(new.id,case when new.status='open' then clock_timestamp() end);
    end if;
  elsif new.status='open' and old.status is distinct from 'open' then
    -- No row means a legacy/imported day whose first opening is not provable.
    update public.matchday_start_evidence set first_started_at=clock_timestamp()
      where matchday_id=new.id and first_started_at is null;
  end if;
  return new;
end $$;
create trigger record_first_matchday_start after insert or update of status on public.matchdays
  for each row execute function public.record_first_matchday_start();

create function public.lock_timing_at(did uuid,stamp timestamptz) returns text
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare evidence public.matchday_start_evidence; d public.matchdays;
begin
  select * into d from public.matchdays where id=did;
  select * into evidence from public.matchday_start_evidence where matchday_id=did;
  if found then
    if evidence.first_started_at is not null then
      return case when stamp<=evidence.first_started_at then 'on_time' else 'late' end;
    elsif d.status='scheduled' then return 'on_time'; end if;
  elsif d.status='open' then
    -- A genuinely NEW first fixation while already open is provably late even
    -- if the exact older first-opening boundary was not retained.
    return 'late';
  end if;
  return 'unknown';
end $$;

create function public.record_first_team_fixation() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  insert into public.team_lock_first_fixations(lock_id,first_fixed_at,timing_status)
    values(new.id,new.locked_at,public.lock_timing_at(new.matchday_id,new.locked_at));
  return new;
end $$;
create trigger record_first_team_fixation after insert on public.team_locks
  for each row execute function public.record_first_team_fixation();

create or replace view public.public_team_locks with(security_invoker=false,security_barrier=true) as
select l.id,l.season_id,l.matchday_id,l.trainer_id,l.season_player_id,l.locked_at,l.deadline_at,
  l.is_late,l.public_team_snapshot,l.created_at,l.updated_at,coalesce(f.timing_status,'unknown') as timing_status
from public.team_locks l left join public.team_lock_first_fixations f on f.lock_id=l.id;

create or replace function public.api_upsert_team_lock(
  p_season_id uuid,
  p_matchday_id uuid,
  p_trainer_id uuid,
  p_season_player_id uuid,
  p_save_file_id uuid,
  p_save_sha256 text,
  p_parsed_save_id uuid,
  p_parsed_payload jsonb,
  p_public_team_snapshot jsonb,
  p_private_team_snapshot jsonb
)
returns setof public.team_locks
language plpgsql
security invoker
set search_path = ''
as $$
declare
  trainer_row public.trainers%rowtype;
  season_row public.seasons%rowtype;
  matchday_row public.matchdays%rowtype;
  player_row public.season_players%rowtype;
  save_row public.save_files%rowtype;
  parsed_row public.parsed_saves%rowtype;
  lock_row public.team_locks%rowtype;
  locked_time timestamptz;
begin
  -- Hold eligibility/source rows stable until the lock and event commit together.
  select * into trainer_row from public.trainers where id = p_trainer_id for share;
  if not found or not trainer_row.globally_enabled then
    raise sqlstate 'PT403' using message = 'trainer_disabled';
  end if;
  select * into season_row from public.seasons where id = p_season_id for share;
  if not found then
    raise sqlstate 'PT404' using message = 'season_not_found';
  end if;
  if season_row.status <> 'active' then
    raise sqlstate 'PT409' using message = 'season_not_active';
  end if;
  select * into matchday_row from public.matchdays
    where id = p_matchday_id and season_id = p_season_id for share;
  if not found then
    raise sqlstate 'PT404' using message = 'matchday_not_found';
  end if;
  if matchday_row.status not in ('scheduled', 'open') or matchday_row.closed_at is not null then
    raise sqlstate 'PT409' using message = 'matchday_not_lockable';
  end if;
  select * into player_row from public.season_players
    where id = p_season_player_id and season_id = p_season_id and trainer_id = p_trainer_id for share;
  if not found then
    raise sqlstate 'PT404' using message = 'participation_not_found';
  end if;
  if player_row.status <> 'active' then
    raise sqlstate 'PT403' using message = 'participant_inactive';
  end if;
  select * into save_row from public.save_files
    where id = p_save_file_id and season_id = p_season_id and trainer_id = p_trainer_id for share;
  if not found then
    raise sqlstate 'PT404' using message = 'save_not_found';
  end if;
  if save_row.deleted_at is not null or save_row.parser_status <> 'parsed'
     or save_row.sha256 is distinct from p_save_sha256 then
    raise sqlstate 'PT409' using message = 'save_not_ready';
  end if;
  select * into parsed_row from public.parsed_saves
    where id = p_parsed_save_id and save_file_id = p_save_file_id
      and parser_version = save_row.parser_version for share;
  if not found then
    raise sqlstate 'PT409' using message = 'parsed_save_not_ready';
  end if;
  if parsed_row.status <> 'parsed' or parsed_row.schema_version <> 1
     or jsonb_typeof(parsed_row.payload) is distinct from 'object'
     or parsed_row.payload is distinct from p_parsed_payload then
    raise sqlstate 'PT409' using message = 'parsed_save_changed';
  end if;
  if jsonb_typeof(parsed_row.payload -> 'party') is distinct from 'array'
     or jsonb_typeof(p_public_team_snapshot) is distinct from 'array'
     or jsonb_typeof(p_private_team_snapshot) is distinct from 'array' then
    raise sqlstate 'PT409' using message = 'invalid_team_snapshot';
  end if;
  if jsonb_array_length(parsed_row.payload -> 'party') <> 6
     or jsonb_array_length(p_public_team_snapshot) <> 6
     or jsonb_array_length(p_private_team_snapshot) <> 6 then
    raise sqlstate 'PT409' using message = 'team_requires_six';
  end if;
  if exists (
    select 1 from jsonb_array_elements(p_public_team_snapshot || p_private_team_snapshot) as mon(value)
    where jsonb_typeof(value) is distinct from 'object'
       or jsonb_typeof(value -> 'species') is distinct from 'string'
       or length(btrim(value ->> 'species')) = 0
  ) then
    raise sqlstate 'PT409' using message = 'invalid_team_snapshot';
  end if;

  -- Preserve the first fixation on replacement; timing evidence is inserted only for a new row.
  locked_time := clock_timestamp();
  insert into public.team_locks (
    season_id, matchday_id, trainer_id, season_player_id, save_file_id, save_sha256,
    locked_at, deadline_at, is_late, public_team_snapshot, private_team_snapshot
  ) values (
    p_season_id, p_matchday_id, p_trainer_id, p_season_player_id, p_save_file_id, save_row.sha256,
    locked_time, null, public.lock_timing_at(p_matchday_id,locked_time)='late', p_public_team_snapshot, p_private_team_snapshot
  )
  on conflict on constraint uq_team_locks_matchday_trainer do update set
    season_player_id = excluded.season_player_id,
    save_file_id = excluded.save_file_id,
    save_sha256 = excluded.save_sha256,
    locked_at = excluded.locked_at,
    deadline_at = excluded.deadline_at,
    is_late = public.team_locks.is_late,
    public_team_snapshot = excluded.public_team_snapshot,
    private_team_snapshot = excluded.private_team_snapshot
  returning * into lock_row;

  insert into public.activity_events (
    season_id, type, actor_trainer_id, trainer_id, visibility, dedupe_key, context, payload, created_at
  ) values (
    p_season_id, 'TEAM_LOCKED', p_trainer_id, p_trainer_id, 'public',
    'TEAM_LOCKED:' || p_season_id::text || ':' || p_matchday_id::text || ':' || p_trainer_id::text,
    jsonb_build_object('season_id', p_season_id, 'matchday_id', p_matchday_id, 'matchday_number', matchday_row.number),
    jsonb_build_object(
      'lock_id', lock_row.id, 'matchday_number', matchday_row.number,
      'save_id', p_save_file_id, 'save_sha256', save_row.sha256, 'is_late', lock_row.is_late
    ), locked_time
  )
  on conflict (dedupe_key) where dedupe_key is not null and dedupe_key <> '' do nothing;

  return next lock_row;
end;
$$;

-- All new helpers and RPCs are backend-only, invoker, with fixed search paths.
do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and p.proname in ('live_reward_rules','api_admin_live_rules_read',
      'api_admin_live_rules_update','settle_observed_progress_rewards','league_operation_principal',
      'admin_setup_begin','admin_setup_begin_v040','api_admin_championship_read','championship_context',
      'api_admin_season_lifecycle','first_start_immutable','record_first_matchday_start',
      'lock_timing_at','record_first_team_fixation','api_upsert_team_lock') loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
    execute format('alter function %s security invoker',f);
    execute format('alter function %s set search_path=pg_catalog,public',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
