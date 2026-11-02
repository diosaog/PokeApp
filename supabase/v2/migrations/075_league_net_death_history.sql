-- 075: prospective official net League scoring and auditable actual-death history.
-- Existing configuration, closed snapshots, saves, purchases and ledgers are not rewritten.
begin;

-- Actual deaths are append-only observed events, never current occupancy plus
-- revival counters. Unknown pre-tracking history needs an explicit audited
-- baseline; this migration deliberately inserts no historical rows.
create table public.league_death_history (
  season_player_id uuid primary key references public.season_players(id) on delete restrict,
  revision bigint not null default 0 check(revision>=0),
  last_identity_revision_id uuid references public.pokemon_identity_revisions(id),
  dead_box_number smallint not null check(dead_box_number between 1 and 32),
  actual_offset bigint check(actual_offset>=0),
  confirmed_wipe_deaths bigint,
  confirmed_wipe_revision bigint,
  confirmed_unmapped_revives bigint,
  segment_matchday_id uuid references public.matchdays(id),
  segment_offset bigint not null default 0,
  revived_entities jsonb not null default '{}' check(jsonb_typeof(revived_entities)='object'),
  blocking_reason text,
  confirmed_at timestamptz,
  updated_at timestamptz not null default clock_timestamp()
);
create table public.league_death_events (
  id uuid primary key default gen_random_uuid(),
  season_player_id uuid not null references public.season_players(id) on delete restrict,
  pokemon_entity_id uuid not null references public.pokemon_entities(id) on delete restrict,
  identity_revision_id uuid not null references public.pokemon_identity_revisions(id) on delete restrict,
  observation_id uuid not null references public.pokemon_observations(id) on delete restrict,
  source_save_id uuid not null references public.save_files(id) on delete restrict,
  source_sha256 text not null check(source_sha256 ~ '^[a-f0-9]{64}$'),
  dead_box_number smallint not null check(dead_box_number between 1 and 32),
  cycle_key text not null,
  matchday_id uuid references public.matchdays(id) on delete restrict,
  phase text not null check(phase in ('preseason','progression','battle','postseason')),
  observed_at timestamptz not null,
  recorded_at timestamptz not null default clock_timestamp(),
  unique(season_player_id,pokemon_entity_id,cycle_key),
  unique(season_player_id,observation_id)
);
create index league_death_events_player_idx on public.league_death_events(season_player_id,recorded_at);
create table public.league_death_resolutions (
  id uuid primary key default gen_random_uuid(),
  season_player_id uuid not null references public.season_players(id) on delete restrict,
  actor_trainer_id uuid not null references public.trainers(id) on delete restrict,
  source_save_id uuid not null references public.save_files(id) on delete restrict,
  source_sha256 text not null check(source_sha256 ~ '^[a-f0-9]{64}$'),
  identity_revision_id uuid not null references public.pokemon_identity_revisions(id) on delete restrict,
  history_revision bigint not null,
  before_state jsonb not null,
  confirmed_counts jsonb not null,
  reason text not null check(length(btrim(reason)) between 1 and 500),
  evidence text not null check(length(btrim(evidence)) between 1 and 2000),
  confirmed_at timestamptz not null default clock_timestamp(),
  unique(season_player_id,history_revision)
);
create table public.matchday_death_snapshots (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  matchday_id uuid not null references public.matchdays(id) on delete restrict,
  season_player_id uuid not null references public.season_players(id) on delete restrict,
  starting_actual_deaths bigint not null check(starting_actual_deaths>=0),
  ending_actual_deaths bigint not null check(ending_actual_deaths>=starting_actual_deaths),
  segment_deaths bigint not null check(segment_deaths=ending_actual_deaths-starting_actual_deaths),
  wipe_deaths bigint not null check(wipe_deaths between 0 and ending_actual_deaths),
  source_save_id uuid not null references public.save_files(id) on delete restrict,
  source_sha256 text not null check(source_sha256 ~ '^[a-f0-9]{64}$'),
  identity_revision_id uuid not null references public.pokemon_identity_revisions(id) on delete restrict,
  history_revision bigint not null,
  wipe_revision bigint not null,
  event_ids uuid[] not null,
  resolution_ids uuid[] not null,
  source_observed_at timestamptz not null,
  confirmed_at timestamptz not null default clock_timestamp(),
  confirmed_by_trainer_id uuid not null references public.trainers(id) on delete restrict,
  unique(matchday_id,season_player_id)
);

-- Immutable history is retained even if a later authorized resolution changes
-- the live baseline. Browser roles have no read or write access to these rows.
do $$ declare t text; begin
  foreach t in array array['league_death_history','league_death_events','league_death_resolutions','matchday_death_snapshots'] loop
    execute format('alter table public.%I enable row level security',t);
    execute format('alter table public.%I force row level security',t);
    execute format('revoke all on public.%I from public,anon,authenticated,service_role',t);
    execute format('grant select,insert on public.%I to service_role',t);
  end loop;
end $$;
grant update on public.league_death_history to service_role;
create trigger league_death_event_immutable before update or delete on public.league_death_events
  for each row execute function public.lifecycle_artifact_immutable();
create trigger league_death_resolution_immutable before update or delete on public.league_death_resolutions
  for each row execute function public.lifecycle_artifact_immutable();
create trigger matchday_death_snapshot_immutable before update or delete on public.matchday_death_snapshots
  for each row execute function public.lifecycle_artifact_immutable();

-- Complete, owned, current accepted source; no timestamp or empty partial box
-- can stand in for an authoritative observation. An ambiguous entity is unknown.
create function public.league_death_source(pid uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; s public.save_files; r public.pokemon_identity_revisions;
  parsed public.parsed_saves; occupied integer; valid boolean=false;
begin
 select * into p from public.season_players where id=pid;
 select * into s from public.save_files where id=p.current_save_file_id and season_id=p.season_id and trainer_id=p.trainer_id;
 select * into r from public.pokemon_identity_revisions where season_id=p.season_id and trainer_id=p.trainer_id order by revision_number desc limit 1;
 select * into parsed from public.parsed_saves where id=r.parsed_save_id and save_file_id=s.id;
 occupied=public.league_observed_dead_count(parsed.payload,p.dead_box_number);
 if r.id is not null and r.save_file_id=s.id and occupied is not null
   and public.observed_save_source_valid(s,parsed,p.trainer_id) then
   valid=not exists(select 1 from public.pokemon_observations o where o.revision_id=r.id
       and (o.pokemon_entity_id is null or o.outcome='AMBIGUOUS'))
     and occupied=(select count(*) from public.pokemon_observations o
       where o.revision_id=r.id and o.source='box' and o.box_number=p.dead_box_number)
     and not exists(
       (select (slot->>'slot_number')::integer,slot#>'{pokemon,identity_evidence}'
        from jsonb_array_elements(parsed.payload->'boxes') b,lateral jsonb_array_elements(b->'slots') slot
        where b->'box_number'=to_jsonb(p.dead_box_number) and slot->'pokemon'<>'null'::jsonb
        except select slot_number,evidence from public.pokemon_observations
        where revision_id=r.id and source='box' and box_number=p.dead_box_number)
       union all
       (select slot_number,evidence from public.pokemon_observations
        where revision_id=r.id and source='box' and box_number=p.dead_box_number
        except select (slot->>'slot_number')::integer,slot#>'{pokemon,identity_evidence}'
        from jsonb_array_elements(parsed.payload->'boxes') b,lateral jsonb_array_elements(b->'slots') slot
        where b->'box_number'=to_jsonb(p.dead_box_number) and slot->'pokemon'<>'null'::jsonb));
 end if;
 return jsonb_build_object('valid',coalesce(valid,false),'source_save_id',s.id,'source_sha256',s.sha256,
   'identity_revision_id',r.id,'revision_number',r.revision_number,'predecessor_id',r.predecessor_id,
   'observed_at',r.created_at,'dead_box_number',p.dead_box_number,'occupied',occupied);
end $$;

create function public.league_unmapped_revives(pid uuid) returns bigint
language sql stable security invoker set search_path=pg_catalog,public as $$
 select greatest((select count(*) from public.redemptions r where r.season_player_id=pid and r.effect_code='revive' and r.status='applied'),
   (select count(*) from public.purchases p join public.shop_items i on i.id=p.shop_item_id
    where p.season_player_id=pid and p.status='used' and i.code='revivir_pokemon'))
   -(select count(*) from public.redemptions r where r.season_player_id=pid and r.effect_code='revive'
     and r.status='applied' and r.target_pokemon_entity_id is not null and r.identity_revision_id is not null)
$$;

create function public.league_track_deaths(pid uuid) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; h public.league_death_history; src jsonb; o public.pokemon_observations;
  previous public.league_death_events; token text; rearm jsonb; d public.matchdays;
  phase text; last_number bigint; cycle text;
begin
 select * into p from public.season_players where id=pid for update;
 if not found then return; end if;
 insert into public.league_death_history(season_player_id,dead_box_number)
   values(pid,p.dead_box_number) on conflict do nothing;
 select * into h from public.league_death_history where season_player_id=pid for update;
 src=public.league_death_source(pid);
 if not (src->>'valid')::boolean then
   update public.league_death_history set blocking_reason='death_history_source_unavailable',updated_at=clock_timestamp() where season_player_id=pid;
   return;
 end if;
 if h.last_identity_revision_id=(src->>'identity_revision_id')::uuid and h.dead_box_number=p.dead_box_number then return; end if;
 if h.dead_box_number<>p.dead_box_number then
   update public.league_death_history set dead_box_number=p.dead_box_number,blocking_reason='death_history_dead_box_changed',
     revision=revision+1,last_identity_revision_id=(src->>'identity_revision_id')::uuid,updated_at=clock_timestamp() where season_player_id=pid;
   return;
 end if;
 -- An interrupted observation chain or changed box has no trustworthy event
 -- boundary. Keep its source current for explicit reconciliation, but do not
 -- manufacture new events while that uncertainty is unresolved.
 if h.blocking_reason is not null then
   update public.league_death_history set revision=revision+1,
     last_identity_revision_id=(src->>'identity_revision_id')::uuid,updated_at=clock_timestamp() where season_player_id=pid;
   return;
 end if;
 if h.last_identity_revision_id is not null and h.last_identity_revision_id is distinct from (src->>'predecessor_id')::uuid then
   update public.league_death_history set blocking_reason='death_history_observation_gap',
     revision=revision+1,last_identity_revision_id=(src->>'identity_revision_id')::uuid,updated_at=clock_timestamp() where season_player_id=pid;
   return;
 end if;
 select m.* into d from public.seasons s join public.matchdays m on m.id=s.current_matchday_id where s.id=p.season_id;
 phase=case when d.status='open' or (d.status='scheduled' and exists(select 1 from public.matchday_start_evidence
     where matchday_id=d.id and first_started_at is not null)) then 'battle' when d.status='scheduled' then 'progression'
   when d.id is null and not exists(select 1 from public.matchdays where season_id=p.season_id) then 'preseason' else 'postseason' end;
 for o in select * from public.pokemon_observations where revision_id=(src->>'identity_revision_id')::uuid
   and source='box' and box_number=p.dead_box_number order by id loop
   select e.* into previous from public.league_death_events e join public.pokemon_identity_revisions r on r.id=e.identity_revision_id
     where e.season_player_id=pid and e.pokemon_entity_id=o.pokemon_entity_id order by r.revision_number desc,e.recorded_at desc limit 1;
   cycle='initial';
   if previous.id is not null then
     cycle=null;
     -- A normal revive is a life-cycle boundary only after a later accepted
     -- living observation. Moving a dead PKM to another box is not a revive.
     select 'normal:'||e.id::text into cycle from public.redemptions e
       join public.pokemon_identity_revisions used on used.id=e.identity_revision_id
       join public.pokemon_identity_revisions died on died.id=previous.identity_revision_id
       where e.season_player_id=pid and e.status='applied' and e.effect_code='revive'
         and e.target_pokemon_entity_id=o.pokemon_entity_id and used.revision_number>=died.revision_number
         and exists(select 1 from public.pokemon_observations alive join public.pokemon_identity_revisions r on r.id=alive.revision_id
           where alive.season_id=p.season_id and alive.trainer_id=p.trainer_id and alive.pokemon_entity_id=o.pokemon_entity_id
             and r.revision_number>used.revision_number and r.revision_number<(src->>'revision_number')::bigint
             and (alive.source='party' or alive.box_number<>p.dead_box_number))
       order by used.revision_number desc,e.redeemed_at desc,e.id desc limit 1;
     rearm=h.revived_entities->o.pokemon_entity_id::text;
     if rearm is not null and (rearm->>'after_revision_number')::bigint<(src->>'revision_number')::bigint
       and (select revision_number from public.pokemon_identity_revisions where id=previous.identity_revision_id)<(rearm->>'after_revision_number')::bigint then
       cycle=rearm->>'token';
     end if;
   end if;
   if cycle is not null then
     insert into public.league_death_events(season_player_id,pokemon_entity_id,identity_revision_id,observation_id,
       source_save_id,source_sha256,dead_box_number,cycle_key,matchday_id,phase,observed_at)
       values(pid,o.pokemon_entity_id,o.revision_id,o.id,o.save_file_id,src->>'source_sha256',p.dead_box_number,cycle,d.id,phase,(src->>'observed_at')::timestamptz)
       on conflict do nothing;
   end if;
 end loop;
 update public.league_death_history set last_identity_revision_id=(src->>'identity_revision_id')::uuid,
   revision=revision+1,updated_at=clock_timestamp() where season_player_id=pid;
end $$;

create function public.league_death_tracking_trigger() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
 if new.current_save_file_id is distinct from old.current_save_file_id or new.dead_box_number is distinct from old.dead_box_number then
   perform public.league_track_deaths(new.id);
 end if;
 return new;
end $$;
create trigger league_track_current_save after update of current_save_file_id,dead_box_number on public.season_players
  for each row execute function public.league_death_tracking_trigger();

create function public.league_death_totals(pid uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; h public.league_death_history; st public.season_player_stats;
 src jsonb; actual bigint; reason text; wipe_revision bigint; recorded bigint;
begin
 select * into p from public.season_players where id=pid;
 select * into h from public.league_death_history where season_player_id=pid;
 select * into st from public.season_player_stats where season_player_id=pid;
 src=public.league_death_source(pid);
 select count(*) into recorded from public.league_death_events where season_player_id=pid;
 if st.season_player_id is not null and jsonb_typeof(st.metadata)='object'
   and (not (st.metadata ? 'wipe_revision') or (jsonb_typeof(st.metadata->'wipe_revision')='number'
     and st.metadata->>'wipe_revision' ~ '^(0|[1-9][0-9]{0,15})$')) then
   wipe_revision=coalesce((st.metadata->>'wipe_revision')::bigint,0);
 end if;
 actual=h.actual_offset+recorded;
 reason=case when not (src->>'valid')::boolean then 'death_history_source_unavailable'
   when wipe_revision is null then 'death_history_wipe_state_unavailable'
   when h.season_player_id is null or h.actual_offset is null then 'death_history_baseline_required'
   when h.dead_box_number<>p.dead_box_number then 'death_history_dead_box_changed'
   when h.blocking_reason is not null then h.blocking_reason
   when h.last_identity_revision_id is distinct from (src->>'identity_revision_id')::uuid then 'death_history_source_changed'
   when h.confirmed_wipe_deaths is distinct from st.revived_after_wipe::bigint
     or h.confirmed_wipe_revision is distinct from wipe_revision then 'death_history_wipe_reconciliation_required'
   when h.confirmed_unmapped_revives is distinct from public.league_unmapped_revives(pid) then 'death_history_unmapped_revival'
   when actual<0 or h.confirmed_wipe_deaths>actual then 'death_history_inconsistent' else null end;
 return src||jsonb_build_object('known',reason is null,'blocking_reason',reason,
   'season_id',p.season_id,'season_player_id',pid,'trainer_id',p.trainer_id,'revision',coalesce(h.revision,0),
   'actual_deaths',case when reason is null then actual end,
   'wipe_deaths',case when reason is null then h.confirmed_wipe_deaths end,
   'death_penalty_tenths',case when reason is null then actual+h.confirmed_wipe_deaths end,
   'wipe_counter',st.revived_after_wipe,'wipe_revision',wipe_revision,'recorded_deaths',recorded);
end $$;

create function public.league_death_segment(pid uuid,did uuid) returns bigint
language sql stable security invoker set search_path=pg_catalog,public as $$
 select count(e.id)+coalesce((select segment_offset from public.league_death_history h
     where h.season_player_id=pid and h.segment_matchday_id is not distinct from did),
   case when (select number from public.matchdays where id=did)=1 then
     (select segment_offset from public.league_death_history where season_player_id=pid and segment_matchday_id is null) else 0 end,0)
 from public.league_death_events e where e.season_player_id=pid
   and ((e.matchday_id=did and e.phase='progression') or
     (e.phase='preseason' and (select number from public.matchdays where id=did)=1))
$$;

create function public.league_death_snapshot(pid uuid,did uuid) returns jsonb
language sql stable security invoker set search_path=pg_catalog,public as $$
 select jsonb_build_object('death_snapshot_id',id,'segment_deaths',segment_deaths,
   'starting_actual_deaths',starting_actual_deaths,'actual_deaths',ending_actual_deaths,
   'wipe_deaths',wipe_deaths,'death_penalty_tenths',ending_actual_deaths+wipe_deaths,
   'source_save_id',source_save_id,'source_sha256',source_sha256,'identity_revision_id',identity_revision_id,
   'history_revision',history_revision,'confirmed_at',confirmed_at)
 from public.matchday_death_snapshots where matchday_id=did and season_player_id=pid
$$;

create function public.league_freeze_death_segment(sid uuid,did uuid,actor uuid) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; d public.matchdays; facts jsonb; segment bigint;
begin
 perform public.league_operation_principal(actor,sid,did);
 select * into d from public.matchdays where id=did and season_id=sid for update;
 if d.id is null or d.status<>'scheduled' then perform public.admin_setup_fail('death_history_start_unproven'); end if;
 if exists(select 1 from public.matchday_start_evidence where matchday_id=did and first_started_at is not null) then
   -- Cancel editing and reopen preserve the first official progression boundary.
   -- A changed roster or imported start without its snapshots is not fabricated.
   if exists((select m.season_player_id from public.participant_memberships_at(sid,d.number) m
      except select season_player_id from public.matchday_death_snapshots where matchday_id=did and season_id=sid)
     union all
     (select season_player_id from public.matchday_death_snapshots where matchday_id=did and season_id=sid
      except select m.season_player_id from public.participant_memberships_at(sid,d.number) m)) then
     perform public.admin_setup_fail('death_history_start_unproven'); end if;
   return;
 end if;
 if not exists(select 1 from public.matchday_start_evidence where matchday_id=did and first_started_at is null) then
   perform public.admin_setup_fail('death_history_start_unproven'); end if;
 for p in select sp.* from public.season_players sp join public.participant_memberships_at(sid,d.number) m
   on m.season_player_id=sp.id where sp.season_id=sid order by sp.id loop
   perform public.league_track_deaths(p.id);
   facts=public.league_death_totals(p.id);
   if not (facts->>'known')::boolean then perform public.admin_setup_fail(facts->>'blocking_reason'); end if;
   segment=public.league_death_segment(p.id,did);
   if segment<0 or segment>(facts->>'actual_deaths')::bigint then perform public.admin_setup_fail('death_history_inconsistent'); end if;
   if exists(select 1 from public.matchday_death_snapshots where matchday_id=did and season_player_id=p.id) then
     perform public.admin_setup_fail('death_history_segment_frozen'); end if;
   insert into public.matchday_death_snapshots(season_id,matchday_id,season_player_id,starting_actual_deaths,
     ending_actual_deaths,segment_deaths,wipe_deaths,source_save_id,source_sha256,identity_revision_id,
     history_revision,wipe_revision,event_ids,resolution_ids,source_observed_at,confirmed_by_trainer_id)
   values(sid,did,p.id,(facts->>'actual_deaths')::bigint-segment,(facts->>'actual_deaths')::bigint,segment,
     (facts->>'wipe_deaths')::bigint,(facts->>'source_save_id')::uuid,facts->>'source_sha256',
     (facts->>'identity_revision_id')::uuid,(facts->>'revision')::bigint,(facts->>'wipe_revision')::bigint,
     array(select id from public.league_death_events where season_player_id=p.id order by id),
     array(select id from public.league_death_resolutions where season_player_id=p.id order by id),
     (facts->>'observed_at')::timestamptz,actor);
 end loop;
end $$;

create function public.league_death_admin_state(pid uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare totals jsonb; p public.season_players; s public.seasons; d public.matchdays; segment bigint;
begin
 select * into p from public.season_players where id=pid;
 select * into s from public.seasons where id=p.season_id;
 select * into d from public.matchdays where id=s.current_matchday_id;
 totals=public.league_death_totals(pid);
 segment=case when d.id is null then (select count(*) from public.league_death_events where season_player_id=pid and phase='preseason')
   +coalesce((select segment_offset from public.league_death_history where season_player_id=pid and segment_matchday_id is null),0)
   else coalesce((select segment_deaths from public.matchday_death_snapshots where matchday_id=d.id and season_player_id=pid),public.league_death_segment(pid,d.id)) end;
 return totals||jsonb_build_object('current_matchday_id',d.id,'segment_deaths',case when (totals->>'known')::boolean then segment end,
   'can_reconcile',s.status in ('draft','active') and coalesce(d.status,'scheduled') in ('scheduled','open') and (totals->>'valid')::boolean,
   'observed_dead_entities',coalesce((select jsonb_agg(jsonb_build_object('pokemon_entity_id',o.pokemon_entity_id,
     'currently_dead',o.source='box' and o.box_number=p.dead_box_number,
     'has_recorded_death',exists(select 1 from public.league_death_events e where e.season_player_id=pid and e.pokemon_entity_id=o.pokemon_entity_id),
     'display_name',coalesce(nullif(pokemon.value->>'nickname',''),pokemon.value->>'species','Pokemon'),
     'species',pokemon.value->>'species','nickname',pokemon.value->>'nickname') order by o.id)
     from public.pokemon_observations o join public.pokemon_identity_revisions ident on ident.id=o.revision_id
     join public.parsed_saves parsed on parsed.id=ident.parsed_save_id and parsed.save_file_id=o.save_file_id
     cross join lateral (select case when o.source='party' then
       (select slot->'pokemon' from jsonb_array_elements(parsed.payload->'party') slot where (slot->>'slot_number')::integer=o.slot_number)
       else (select slot->'pokemon' from jsonb_array_elements(parsed.payload->'boxes') b,lateral jsonb_array_elements(b->'slots') slot
         where (b->>'box_number')::integer=o.box_number and (slot->>'slot_number')::integer=o.slot_number) end value) pokemon
     where o.revision_id=(totals->>'identity_revision_id')::uuid and o.pokemon_entity_id is not null),'[]'::jsonb));
end $$;

create function public.api_admin_death_history(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare op text=p_request->>'operation'; r jsonb=p_request->'request'; b jsonb=r->'body';
 sid uuid=(r->>'season_id')::uuid; pid uuid=(r->>'resource_id')::uuid; actor uuid=(r->>'actor_trainer_id')::uuid;
 cached jsonb; before jsonb; result jsonb; src jsonb; h public.league_death_history; s public.seasons; d public.matchdays;
 actual bigint; wipes bigint; segment bigint; recorded bigint; segment_recorded bigint; frozen bigint;
 resolution_id uuid=gen_random_uuid(); oid uuid=gen_random_uuid(); event_id uuid=gen_random_uuid(); rearm jsonb; entity text;
begin
 if op is null or op not in ('state','reconcile') or p_request-array['operation','request']<>'{}'::jsonb
   or jsonb_typeof(r) is distinct from 'object' or r-array['actor_trainer_id','season_id','resource_id','body','idempotency_key']<>'{}'::jsonb then
   perform public.admin_setup_fail('invalid_request',422); end if;
 perform public.admin_setup_principal(actor);
 if op='state' then
   if coalesce(b,'{}'::jsonb)<>'{}'::jsonb then perform public.admin_setup_fail('invalid_request',422); end if;
   if not exists(select 1 from public.season_players where id=pid and season_id=sid) then perform public.admin_setup_fail('participant_not_found',404); end if;
   return public.league_death_admin_state(pid)||jsonb_build_object('replayed',false);
 end if;
 cached=public.admin_setup_begin('death_history',r); if cached is not null then return cached; end if;
 if jsonb_typeof(b) is distinct from 'object' or b-array['actual_deaths','wipe_deaths','segment_deaths','source_sha256','expected_revision','reason','evidence','revived_entity_ids']<>'{}'::jsonb
   or exists(select 1 from unnest(array['actual_deaths','wipe_deaths','segment_deaths','expected_revision']) k
     where jsonb_typeof(b->k) is distinct from 'number' or (b->>k)!~'^(0|[1-9][0-9]{0,8})$')
   or jsonb_typeof(b->'source_sha256') is distinct from 'string' or (b->>'source_sha256')!~'^[a-f0-9]{64}$'
   or jsonb_typeof(b->'reason') is distinct from 'string' or length(btrim(b->>'reason')) not between 1 and 500
   or jsonb_typeof(b->'evidence') is distinct from 'string' or length(btrim(b->>'evidence')) not between 1 and 2000
   or jsonb_typeof(coalesce(b->'revived_entity_ids','[]')) is distinct from 'array' then
   perform public.admin_setup_fail('death_history_evidence_required',422); end if;
 select * into s from public.seasons where id=sid;
 select * into d from public.matchdays where id=s.current_matchday_id;
 if s.status not in ('draft','active') or coalesce(d.status,'scheduled') not in ('scheduled','open') then
   perform public.admin_setup_fail('death_history_closed'); end if;
 if not exists(select 1 from public.season_players where id=pid and season_id=sid) then perform public.admin_setup_fail('participant_not_found',404); end if;
 before=public.league_death_admin_state(pid);
 if (b->>'expected_revision')::bigint<>(before->>'revision')::bigint then perform public.admin_setup_fail('death_history_revision_conflict'); end if;
 perform public.league_track_deaths(pid);
 select * into h from public.league_death_history where season_player_id=pid for update;
 before=public.league_death_admin_state(pid); src=public.league_death_source(pid);
 if not (src->>'valid')::boolean then perform public.admin_setup_fail('death_history_source_unavailable'); end if;
 if before->>'wipe_revision' is null or before->>'wipe_counter' is null then perform public.admin_setup_fail('death_history_wipe_state_unavailable'); end if;
 if b->>'source_sha256' is distinct from src->>'source_sha256' then perform public.admin_setup_fail('death_history_source_changed'); end if;
 actual=(b->>'actual_deaths')::bigint; wipes=(b->>'wipe_deaths')::bigint; segment=(b->>'segment_deaths')::bigint;
 if wipes<>(before->>'wipe_counter')::bigint or wipes>actual or segment>actual or actual<(src->>'occupied')::integer then
   perform public.admin_setup_fail('death_history_inconsistent'); end if;
 select segment_deaths into frozen from public.matchday_death_snapshots where season_player_id=pid and matchday_id=d.id;
 if frozen is not null and segment<>frozen then perform public.admin_setup_fail('death_history_segment_frozen'); end if;
 rearm=h.revived_entities;
 for entity in select jsonb_array_elements_text(coalesce(b->'revived_entity_ids','[]')) loop
   if entity!~'^[a-fA-F0-9-]{36}$' or not exists(select 1 from public.league_death_events where season_player_id=pid and pokemon_entity_id=entity::uuid)
     or not exists(select 1 from public.pokemon_observations o where o.revision_id=(src->>'identity_revision_id')::uuid
       and o.pokemon_entity_id=entity::uuid and (o.source='party' or o.box_number<>(src->>'dead_box_number')::integer)) then
     perform public.admin_setup_fail('death_history_inconsistent'); end if;
   rearm=rearm||jsonb_build_object(entity,jsonb_build_object('token','audit:'||resolution_id::text,'after_revision_number',src->'revision_number'));
 end loop;
 select count(*) into recorded from public.league_death_events where season_player_id=pid;
 select count(*) into segment_recorded from public.league_death_events e where e.season_player_id=pid
   and ((e.matchday_id=d.id and e.phase='progression') or (e.phase='preseason' and (d.number=1 or d.id is null)));
 if actual<recorded or actual<coalesce((select max(ending_actual_deaths) from public.matchday_death_snapshots where season_player_id=pid),0)
   or segment<segment_recorded then perform public.admin_setup_fail('death_history_inconsistent'); end if;
 insert into public.league_death_resolutions(id,season_player_id,actor_trainer_id,source_save_id,source_sha256,
   identity_revision_id,history_revision,before_state,confirmed_counts,reason,evidence)
 values(resolution_id,pid,actor,(src->>'source_save_id')::uuid,src->>'source_sha256',(src->>'identity_revision_id')::uuid,
   h.revision+1,before,b,btrim(b->>'reason'),btrim(b->>'evidence'));
 update public.league_death_history set actual_offset=actual-recorded,confirmed_wipe_deaths=wipes,
   confirmed_wipe_revision=(before->>'wipe_revision')::bigint,confirmed_unmapped_revives=public.league_unmapped_revives(pid),
   segment_matchday_id=d.id,segment_offset=segment-segment_recorded,blocking_reason=null,revived_entities=rearm,
   revision=revision+1,confirmed_at=clock_timestamp(),updated_at=clock_timestamp() where season_player_id=pid;
 result=public.league_death_admin_state(pid)||jsonb_build_object('replayed',false,'resolution_id',resolution_id);
 insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
 values(event_id,sid,'DEATH_HISTORY_RECONCILED',actor,'admin','death-history:'||resolution_id::text,
   jsonb_build_object('resolution_id',resolution_id,'season_player_id',pid,'before',before,'after',result));
 insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
 values(oid,actor,sid,public.admin_setup_scope('death_history',r),r->>'idempotency_key',encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
 return result;
end $$;

do $$ declare f regprocedure; begin
 foreach f in array array[
   'public.league_death_source(uuid)'::regprocedure,'public.league_unmapped_revives(uuid)'::regprocedure,
   'public.league_track_deaths(uuid)'::regprocedure,'public.league_death_tracking_trigger()'::regprocedure,
   'public.league_death_totals(uuid)'::regprocedure,'public.league_death_segment(uuid,uuid)'::regprocedure,
   'public.league_death_snapshot(uuid,uuid)'::regprocedure,'public.league_freeze_death_segment(uuid,uuid,uuid)'::regprocedure,
   'public.league_death_admin_state(uuid)'::regprocedure,'public.api_admin_death_history(jsonb)'::regprocedure
 ] loop
   execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
   execute format('grant execute on function %s to service_role',f);
 end loop;
end $$;

create function public.league_net_season(sid uuid) returns boolean
language sql stable security invoker set search_path=pg_catalog,public as $$
  select not exists(select 1 from public.matchday_snapshots s where s.season_id=sid
    and s.snapshot#>>'{inputs,config,scoring_mode}' is distinct from 'league_net_v1')
$$;

create function public.league_net_day(did uuid) returns boolean
language sql stable security invoker set search_path=pg_catalog,public as $$
  select case when s.id is not null then s.snapshot#>>'{inputs,config,scoring_mode}'='league_net_v1'
    else public.league_net_season(d.season_id) end
  from public.matchdays d left join public.matchday_snapshots s on s.matchday_id=d.id where d.id=did
$$;

alter function public.admin_setup_validate_config(uuid,jsonb) rename to admin_setup_validate_config_v074;
create function public.admin_setup_validate_config(sid uuid,b jsonb) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  perform public.admin_setup_validate_config_v074(sid,b);
  if public.league_net_season(sid) then
    perform public.single_league_common_coins(b->'coin_rewards');
  end if;
end $$;

-- All normal participants meet once, independently of the division used for movement.
-- This only fills missing scheduled pairs at an authorized opening; no existing result is removed.
create function public.league_prepare_round_robin(sid uuid,did uuid) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare n integer;
begin
  if exists(select 1 from public.matches where matchday_id=did and (status<>'scheduled' or winner_id is not null)) then
    perform public.admin_setup_fail('invalid_results'); end if;
  select number into n from public.matchdays where id=did and season_id=sid;
  insert into public.matches(season_id,matchday_id,division_id,player_a_id,player_b_id)
    select sid,did,a.division_id,a.season_player_id,b.season_player_id
    from public.participant_memberships_at(sid,n) a cross join public.participant_memberships_at(sid,n) b
    where a.season_player_id<b.season_player_id and not exists(select 1 from public.matches m
      where m.matchday_id=did and least(m.player_a_id,m.player_b_id)=a.season_player_id
        and greatest(m.player_a_id,m.player_b_id)=b.season_player_id);
end $$;

alter function public.matchday_validate_v035(uuid,uuid,boolean) rename to matchday_validate_pre075;
create function public.matchday_validate_v035(sid uuid,did uuid,complete boolean) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare d public.matchdays; c public.season_config_versions; n integer; division_code text;
begin
  if not coalesce(public.league_net_day(did),false) then
    perform public.matchday_validate_pre075(sid,did,complete); return; end if;
  select * into d from public.matchdays where id=did and season_id=sid;
  if not found then perform public.admin_setup_fail('matchday_not_found',404); end if;
  select * into c from public.season_config_versions where season_id=sid and effective_from_matchday<=d.number
    order by effective_from_matchday desc limit 1;
  if c.id is distinct from d.season_config_version_id or d.number>c.total_matchdays or c.division_sizes is null then
    perform public.admin_setup_fail('config_mismatch'); end if;
  perform public.single_league_common_coins(c.coin_rewards_json);
  if exists(select 1 from public.season_players where season_id=sid and status<>'active' and status_effective_matchday_number is null)
    or exists(select 1 from public.season_players p where p.season_id=sid
      and (p.status='active' or d.number<p.status_effective_matchday_number)
      and (select count(*) from public.participant_memberships_at(sid,d.number) m where m.season_player_id=p.id)<>1) then
    perform public.admin_setup_fail('invalid_roster'); end if;
  foreach division_code in array array['A','B'] loop
    if (select count(*) from public.participant_memberships_at(sid,d.number) m join public.divisions v on v.id=m.division_id
       where v.code=division_code)>coalesce((c.division_sizes->>division_code)::integer,0) then
      perform public.admin_setup_fail('invalid_roster'); end if;
  end loop;
  select count(*) into n from public.participant_memberships_at(sid,d.number);
  if n<2 or (select count(*) from public.matches where matchday_id=did)<>n*(n-1)/2
    or (select count(distinct (least(player_a_id,player_b_id),greatest(player_a_id,player_b_id))) from public.matches where matchday_id=did)<>n*(n-1)/2
    or exists(select 1 from public.matches m where m.matchday_id=did and
      (m.season_id<>sid or m.player_a_id=m.player_b_id or m.status not in ('scheduled','completed')
       or (m.winner_id is null)<>(m.status='scheduled') or (m.winner_id is not null and m.winner_id not in(m.player_a_id,m.player_b_id))
       or not exists(select 1 from public.participant_memberships_at(sid,d.number) a where a.season_player_id=m.player_a_id)
       or not exists(select 1 from public.participant_memberships_at(sid,d.number) b where b.season_player_id=m.player_b_id)
       or not exists(select 1 from public.divisions v where v.id=m.division_id and v.season_id=sid))) then
    perform public.admin_setup_fail('invalid_results'); end if;
  if complete and exists(select 1 from public.matches where matchday_id=did and status<>'completed') then
    perform public.admin_setup_fail('results_incomplete'); end if;
end $$;

alter function public.matchday_lock(text,jsonb) rename to matchday_lock_v074;
create function public.matchday_lock(op text,r jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare cached jsonb; sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid;
begin
  cached=public.admin_setup_begin('matchday_'||op,r);
  if cached is not null then return cached; end if;
  if op in ('open','close') and not public.league_net_season(sid) then
    perform public.admin_setup_fail('legacy_scoring_migration_required'); end if;
  if op='open' then
    -- Principal, receipt, season and roster locks were acquired above, before any write.
    perform 1 from public.matchdays where id=did and season_id=sid and status='scheduled' for update;
    if found then perform public.league_prepare_round_robin(sid,did); end if;
  end if;
  cached=public.matchday_lock_v074(op,r);
  if cached is not null then return cached; end if;
  if op='open' then
    perform public.league_freeze_death_segment(sid,did,(r->>'actor_trainer_id')::uuid);
  end if;
  return null;
end $$;

alter function public.matchday_commit_close(text,jsonb,jsonb,jsonb) rename to matchday_commit_close_v074;
create function public.matchday_commit_close(op text,r jsonb,ctx jsonb,plan jsonb) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid;
  row jsonb; input_player jsonb; other jsonb; decision jsonb; battle jsonb; group_ids jsonb;
  n integer; wins integer; allocation integer; group_size integer; prior_units bigint;
  deduction numeric; positions jsonb; pair_a text; pair_b text; winner text;
  moving integer; division_size integer; cut integer; tied_division_size integer;
begin
  if ctx#>>'{inputs,config,scoring_mode}' is distinct from 'league_net_v1' then
    perform public.matchday_commit_close_v074(op,r,ctx,plan); return; end if;
  if op not in ('close','correct') or ctx->>'ranking_rule' is distinct from 'wins_segment_deaths_v2'
    or plan#>>'{ranking,rule}' is distinct from 'wins_segment_deaths_v2'
    or jsonb_typeof(plan->'standings') is distinct from 'array'
    or jsonb_typeof(plan#>'{ranking,resolutions}') is distinct from 'array'
    or jsonb_typeof(plan#>'{ranking,groups}') is distinct from 'array'
    or coalesce(plan#>>'{ranking,input_hash}','') !~ '^[a-f0-9]{64}$' then
    perform public.admin_setup_fail('invalid_results'); end if;
  if op='correct' then perform public.matchday_results(did,r#>'{body,results}',true); end if;
  perform public.matchday_validate(sid,did,true);
  n=jsonb_array_length(ctx#>'{inputs,players}');
  moving=case when (ctx#>>'{inputs,number}')::integer=(ctx#>>'{inputs,config,total_matchdays}')::integer then 0 else
    least((ctx#>>'{inputs,config,promotion_relegation_count}')::integer,
      (select count(*) from jsonb_array_elements(ctx#>'{inputs,players}') p where p->>'division'='A'),
      (select count(*) from jsonb_array_elements(ctx#>'{inputs,players}') p where p->>'division'='B')) end;
  if jsonb_array_length(plan->'standings')<>n
    or (select count(distinct x->>'trainer_id') from jsonb_array_elements(plan->'standings') x)<>n
    or (select count(distinct (x#>>'{metadata,allocation_position}')::integer)
        from jsonb_array_elements(plan->'standings') x
        where (x#>>'{metadata,allocation_position}')::integer between 1 and n)<>n then
    perform public.admin_setup_fail('invalid_results'); end if;
  if jsonb_array_length(plan#>'{ranking,resolutions}')>0 then
    if r#>>'{body,tie_resolution,input_hash}' is distinct from plan#>>'{ranking,input_hash}'
      or r#>'{body,tie_resolution,orders}' is distinct from plan#>'{ranking,resolutions}' then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
  elsif r#>'{body,tie_resolution}' is not null and r#>'{body,tie_resolution}'<>'null'::jsonb then
    perform public.admin_setup_fail('invalid_tie_resolution'); end if;
  for row in select value from jsonb_array_elements(plan->'standings') loop
    select value into input_player from jsonb_array_elements(ctx#>'{inputs,players}') where value->>'id'=row->>'trainer_id';
    select count(*) into wins from public.matches where matchday_id=did and status='completed' and winner_id=(row->>'trainer_id')::uuid;
    allocation=(row#>>'{metadata,allocation_position}')::integer;
    prior_units=(input_player->>'prior_death_penalty_tenths')::bigint;
    deduction=((input_player->>'death_penalty_tenths')::numeric-prior_units)/10
      +(input_player->>'points_reduction')::numeric-(input_player->>'prior_points_reduction')::numeric;
    if input_player is null or input_player->>'death_snapshot_id' is null
      or input_player->>'death_penalty_tenths' is null
      or (input_player->>'death_penalty_tenths')::bigint is distinct from
        (input_player->>'actual_deaths')::bigint+(input_player->>'wipe_deaths')::bigint
      or (input_player->>'actual_deaths')::bigint<(input_player->>'wipe_deaths')::bigint
      or row->>'division_id' is distinct from input_player->>'division'
      or (row->>'division_position')::integer is distinct from 1+(select count(*) from jsonb_array_elements(plan->'standings') x
        where x->>'division_id'=row->>'division_id' and (x#>>'{metadata,allocation_position}')::integer<allocation
          and (row#>>'{metadata,tie_status}' is distinct from 'unresolved_neutral'
            or x#>'{metadata,wins}' is distinct from row#>'{metadata,wins}'
            or x#>'{metadata,actual_segment_deaths}' is distinct from row#>'{metadata,actual_segment_deaths}'))
      or (row->>'points_awarded')::integer is distinct from wins
      or (row#>>'{metadata,wins}')::integer is distinct from wins
      or (row#>>'{metadata,losses}')::integer is distinct from n-1-wins
      or row#>>'{metadata,ranking_rule}' is distinct from 'wins_segment_deaths_v2'
      or row#>>'{metadata,death_snapshot_id}' is distinct from input_player->>'death_snapshot_id'
      or (row#>>'{metadata,actual_segment_deaths}')::bigint is distinct from (input_player->>'segment_deaths')::bigint
      or (row#>>'{metadata,actual_deaths}')::bigint is distinct from (input_player->>'actual_deaths')::bigint
      or (row#>>'{metadata,wipe_deaths}')::bigint is distinct from (input_player->>'wipe_deaths')::bigint
      or (row#>>'{penalties,dead_count}')::bigint is distinct from (input_player->>'death_penalty_tenths')::bigint
      or (row#>>'{penalties,dead_points_penalty}')::numeric is distinct from (input_player->>'death_penalty_tenths')::numeric/10
      or (row#>>'{penalties,points_reduction}')::numeric is distinct from (input_player->>'points_reduction')::numeric
      or (row#>>'{metadata,point_penalties}')::numeric is distinct from deduction
      or (row#>>'{metadata,net_points}')::numeric is distinct from wins-deduction
      or row#>'{metadata,placement_rewards}' is distinct from (case
        when (row->>'position')::integer=1 then '["blindar_pokemon"]'::jsonb
        when (row->>'position')::integer=n then '["robar_pokemon"]'::jsonb else '[]'::jsonb end)
      or (row->>'position')::integer<1 or (row#>>'{metadata,position_end}')::integer>n
      or allocation not between (row->>'position')::integer and (row#>>'{metadata,position_end}')::integer then
      perform public.admin_setup_fail('invalid_results'); end if;
    for other in select value from jsonb_array_elements(plan->'standings') where value->>'trainer_id'<>row->>'trainer_id' loop
      if ((row#>>'{metadata,wins}')::integer>(other#>>'{metadata,wins}')::integer
        or ((row#>>'{metadata,wins}')::integer=(other#>>'{metadata,wins}')::integer
          and (row#>>'{metadata,actual_segment_deaths}')::bigint<(other#>>'{metadata,actual_segment_deaths}')::bigint))
        and allocation>=(other#>>'{metadata,allocation_position}')::integer then
        perform public.admin_setup_fail('invalid_results'); end if;
    end loop;
    select jsonb_agg(x->'trainer_id') into group_ids from jsonb_array_elements(plan->'standings') x
      where x#>'{metadata,wins}'=row#>'{metadata,wins}' and x#>'{metadata,actual_segment_deaths}'=row#>'{metadata,actual_segment_deaths}';
    group_size=jsonb_array_length(group_ids);
    if group_size>1 then
      select x into decision from jsonb_array_elements(plan#>'{ranking,resolutions}') x
        where (select array_agg(v order by v) from jsonb_array_elements_text(x->'player_ids') v)
          =(select array_agg(v order by v) from jsonb_array_elements_text(group_ids) v);
      if decision is null then
        if row#>>'{metadata,tie_status}' is distinct from 'unresolved_neutral'
          or (row->>'position')::integer<=3 or (row#>>'{metadata,position_end}')::integer=n
          or (row#>>'{metadata,tie_size}')::integer is distinct from group_size
          or (row#>>'{metadata,position_end}')::integer-(row->>'position')::integer+1<>group_size then
          perform public.admin_setup_fail('ranking_tie_unresolved'); end if;
        if moving>0 then
          select count(*) into division_size from jsonb_array_elements(ctx#>'{inputs,players}') p where p->>'division'=row->>'division_id';
          select count(*) into tied_division_size from jsonb_array_elements(plan->'standings') x where
            group_ids ? (x->>'trainer_id') and x->>'division_id'=row->>'division_id';
          cut=case when row->>'division_id'='A' then division_size-moving else moving end;
          if (row->>'division_position')::integer<=cut and (row->>'division_position')::integer+tied_division_size-1>cut then
            perform public.admin_setup_fail('ranking_tie_unresolved'); end if;
        end if;
      elsif row#>>'{metadata,tie_status}' is distinct from 'externally_resolved' then
        perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    elsif row#>>'{metadata,tie_status}' is distinct from 'unique' then
      perform public.admin_setup_fail('invalid_results'); end if;
  end loop;
  for decision in select value from jsonb_array_elements(plan#>'{ranking,resolutions}') loop
    group_ids=decision->'player_ids';group_size=jsonb_array_length(group_ids);
    select x into row from jsonb_array_elements(plan->'standings') x where x->>'trainer_id'=group_ids->>0;
    if row is null or (select count(*) from jsonb_array_elements(plan->'standings') x where group_ids ? (x->>'trainer_id'))<>group_size
      or (select count(*) from jsonb_array_elements(plan->'standings') x where
        x#>'{metadata,wins}'=row#>'{metadata,wins}' and x#>'{metadata,actual_segment_deaths}'=row#>'{metadata,actual_segment_deaths}')<>group_size
      or exists(select 1 from jsonb_array_elements(plan->'standings') x where group_ids ? (x->>'trainer_id')
        and (x#>'{metadata,wins}' is distinct from row#>'{metadata,wins}' or x#>'{metadata,actual_segment_deaths}' is distinct from row#>'{metadata,actual_segment_deaths}')) then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    if group_size<2 or (select count(distinct value) from jsonb_array_elements(group_ids))<>group_size
      or jsonb_typeof(decision->'battles') is distinct from 'array'
      or jsonb_array_length(decision->'battles')<>group_size*(group_size-1)/2
      or jsonb_typeof(decision->'reason') is distinct from 'string'
      or length(btrim(decision->>'reason')) not between 1 and 500
      or (select count(distinct (least(x->>'player_a_id',x->>'player_b_id'),greatest(x->>'player_a_id',x->>'player_b_id')))
        from jsonb_array_elements(decision->'battles') x)<>group_size*(group_size-1)/2 then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    for battle in select value from jsonb_array_elements(decision->'battles') loop
      pair_a=battle->>'player_a_id';pair_b=battle->>'player_b_id';winner=battle->>'winner_id';
      if pair_a is null or pair_b is null or pair_a=pair_b or not(group_ids ? pair_a) or not(group_ids ? pair_b)
        or winner is null or winner not in(pair_a,pair_b)
        or jsonb_typeof(battle->'evidence') is distinct from 'string'
        or length(btrim(battle->>'evidence')) not between 1 and 500
        or jsonb_typeof(battle->'played_at') is distinct from 'string'
        or coalesce(battle->>'played_at','') !~ '(Z|[+-][0-9]{2}:[0-9]{2})$'
        or (battle->>'played_at')::timestamptz>clock_timestamp()
        or (select ord from jsonb_array_elements_text(group_ids) with ordinality a(v,ord) where v=winner)
          >(select ord from jsonb_array_elements_text(group_ids) with ordinality a(v,ord) where v=case when winner=pair_a then pair_b else pair_a end) then
        perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    end loop;
    if exists(select 1 from jsonb_array_elements_text(group_ids) with ordinality g(pid,ord)
      join lateral (select x from jsonb_array_elements(plan->'standings') x where x->>'trainer_id'=g.pid) s on true
      where (s.x#>>'{metadata,allocation_position}')::integer<>ord+
        (select min((minimum_row.value#>>'{metadata,allocation_position}')::integer)-1
          from jsonb_array_elements(plan->'standings') minimum_row(value)
          where group_ids ? (minimum_row.value->>'trainer_id'))) then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
  end loop;
  perform public.matchday_commit_close_v034(op,r,jsonb_set(ctx,'{inputs,ranking}',plan->'ranking'),plan);
end $$;

create function public.league_points_reduction(sid uuid,pid uuid,day_number integer) returns numeric
language sql stable security invoker set search_path=pg_catalog,public as $$
  select coalesce(sum(greatest(coalesce(pe.points_amount,pe.amount::numeric),0)),0)
    from public.penalties pe join public.season_players p on p.id=pid and p.season_id=sid and p.trainer_id=pe.trainer_id
    left join public.matchdays d on d.id=pe.matchday_id
    where pe.season_id=sid and public.trials_penalty_current(pe) and pe.penalty_type='points_reduction'
      and (pe.effective_from_matchday_number is null or pe.effective_from_matchday_number<=day_number)
      and (pe.matchday_id is null or (d.season_id=sid and d.number<=day_number))
      and (pe.trial_case_id is null or exists(select 1 from public.trial_cases tc where tc.id=pe.trial_case_id
        and tc.status='resolved' and tc.accused_trainer_id=p.trainer_id and (tc.season_id is null or tc.season_id=sid)))
$$;

alter function public.matchday_context(text,jsonb) rename to matchday_context_v074;
create function public.matchday_context(op text,r jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare ctx jsonb; sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid;
  players jsonb='[]'; p jsonb; totals jsonb; frozen jsonb; prior jsonb; day_number integer;
begin
  if op='correct' and not coalesce(public.league_net_day(did),false) then
    return public.matchday_context_v074(op,r); end if;
  if not public.league_net_season(sid) then perform public.admin_setup_fail('legacy_scoring_migration_required'); end if;
  ctx=public.matchday_context_v034(op,r);
  if op='correct' then
    return ctx||jsonb_build_object('ranking_rule','wins_segment_deaths_v2'); end if;
  day_number=(ctx#>>'{inputs,number}')::integer;
  perform public.single_league_common_coins(ctx#>'{inputs,config,coin_rewards_json}');
  for p in select value from jsonb_array_elements(ctx#>'{inputs,players}') loop
    totals=public.league_death_totals((p->>'id')::uuid);
    frozen=public.league_death_snapshot((p->>'id')::uuid,did);
    if totals->>'known' is distinct from 'true' or frozen->>'death_snapshot_id' is null then
      perform public.admin_setup_fail('death_history_confirmation_required'); end if;
    select row into prior from public.matchday_snapshots s join public.matchdays d on d.id=s.matchday_id,
      jsonb_array_elements(s.snapshot->'standings') row where s.season_id=sid and d.number<day_number
      and row->>'trainer_id'=p->>'id' order by d.number desc limit 1;
    players=players||jsonb_build_array(p||totals||jsonb_build_object(
      'segment_deaths',frozen->'segment_deaths','death_snapshot_id',frozen->'death_snapshot_id',
      'dead_count',totals->'death_penalty_tenths',
      'points_reduction',public.league_points_reduction(sid,(p->>'id')::uuid,day_number)::text,
      'prior_death_penalty_tenths',coalesce((prior#>>'{penalties,dead_count}')::bigint,0),
      'prior_points_reduction',coalesce(prior#>>'{penalties,points_reduction}','0')));
  end loop;
  ctx=jsonb_set(ctx,'{inputs,players}',players);
  ctx=jsonb_set(ctx,'{inputs,config}',(ctx#>'{inputs,config}')||jsonb_build_object('scoring_mode','league_net_v1','death_penalty_per_mon','0.1'));
  return ctx||jsonb_build_object('ranking_rule','wins_segment_deaths_v2');
end $$;

-- Public reads preserve frozen history and distinguish incomplete live evidence.

create function public.league_live_matchday_scores(sid uuid,did uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare d public.matchdays; p record; totals jsonb; frozen jsonb; prior jsonb;
  rows jsonb='[]'; wins integer; losses integer; deduction numeric; reduction numeric; known boolean;
begin
  select * into d from public.matchdays where id=did and season_id=sid;
  if not found or d.status='closed' then return '[]'; end if;
  for p in select sp.*,v.code from public.participant_memberships_at(sid,d.number) m
    join public.season_players sp on sp.id=m.season_player_id join public.divisions v on v.id=m.division_id order by sp.id loop
    totals=public.league_death_totals(p.id); frozen=public.league_death_snapshot(p.id,did);
    known=totals->>'known'='true' and frozen->>'death_snapshot_id' is not null;
    select row into prior from public.matchday_snapshots s join public.matchdays md on md.id=s.matchday_id,
      jsonb_array_elements(s.snapshot->'standings') row where s.season_id=sid and md.number<d.number
      and row->>'trainer_id'=p.id::text order by md.number desc limit 1;
    select count(*) filter(where winner_id=p.id),count(*) filter(where winner_id<>p.id) into wins,losses
      from public.matches where matchday_id=did and status='completed' and p.id in(player_a_id,player_b_id);
    reduction=public.league_points_reduction(sid,p.id,d.number);
    deduction=case when known then ((totals->>'death_penalty_tenths')::numeric
      -coalesce((prior#>>'{penalties,dead_count}')::numeric,0))/10
      +reduction-coalesce((prior#>>'{penalties,points_reduction}')::numeric,0) end;
    rows=rows||jsonb_build_array(jsonb_build_object('season_player_id',p.id,'division',p.code,
      'position',null,'division_position',null,'position_end',null,'tie_status',null,
      'points_awarded',wins,'score',case when known then (wins-deduction)::text end,
      'wins',wins,'losses',losses,'actual_segment_deaths',frozen->'segment_deaths',
      'point_penalties',deduction::text,'net_points',case when known then (wins-deduction)::text end,
      'placement_rewards','[]'::jsonb));
  end loop;
  if not exists(select 1 from jsonb_array_elements(rows) x where x->>'actual_segment_deaths' is null) then
    select jsonb_agg(x||jsonb_build_object(
      'position',1+(select count(*) from jsonb_array_elements(rows) y where (y->>'wins')::integer>(x->>'wins')::integer
        or (y->>'wins'=x->>'wins' and (y->>'actual_segment_deaths')::bigint<(x->>'actual_segment_deaths')::bigint)),
      'division_position',1+(select count(*) from jsonb_array_elements(rows) y where y->>'division'=x->>'division' and
        ((y->>'wins')::integer>(x->>'wins')::integer or (y->>'wins'=x->>'wins' and (y->>'actual_segment_deaths')::bigint<(x->>'actual_segment_deaths')::bigint)))
      ) order by (x->>'wins')::integer desc,(x->>'actual_segment_deaths')::bigint) into rows from jsonb_array_elements(rows) x;
  end if;
  return jsonb_build_array(jsonb_build_object('matchday_id',did,'standings',rows,'provisional',true));
end $$;

alter function public.league_general_read(uuid) rename to league_general_read_v074;
create function public.league_general_read(p_season_id uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare result jsonb; row jsonb; item jsonb; rows jsonb='[]'; totals jsonb; last_row jsonb;
  pid uuid; nextday public.matchdays; cfg public.season_config_versions; official numeric; earned numeric;
  deduction numeric; net numeric; wins bigint; units bigint; actual bigint; reduction numeric;
  live boolean; known boolean; net_contract boolean;
begin
  result=public.league_general_read_v074(p_season_id);
  if result is null then return null; end if;
  net_contract=public.league_net_season(p_season_id);
  select * into cfg from public.season_config_versions where season_id=p_season_id order by effective_from_matchday desc limit 1;
  select * into nextday from public.matchdays where season_id=p_season_id and status<>'closed' order by number limit 1;
  live=result#>>'{season,status}' in ('draft','active') and not exists(select 1 from public.matchdays
    where season_id=p_season_id and number=cfg.total_matchdays and status='closed');
  for row in select value from jsonb_array_elements(result->'rows') loop
    pid=(row->>'season_player_id')::uuid;
    totals=public.league_death_totals(pid);
    select x into last_row from public.matchday_snapshots s join public.matchdays d on d.id=s.matchday_id,
      jsonb_array_elements(s.snapshot->'standings') x where s.season_id=p_season_id and x->>'trainer_id'=pid::text
      order by d.number desc limit 1;
    select count(*) into wins from public.matches m join public.matchdays d on d.id=m.matchday_id
      where d.season_id=p_season_id and m.status='completed' and m.winner_id=pid
        and (d.status='closed' or (live and d.status='open'));
    official=coalesce((select sanctioned_points from public.public_sanctioned_points
      where season_id=p_season_id and season_player_id=pid),0);
    if not net_contract then
      -- Legacy official scoring is unchanged. Its current box occupancy is not historical proof.
      item=row||jsonb_build_object('normal_wins',wins,'total_penalties',null,
        'historical_deaths',null,'historical_deaths_status','unknown',
        'historical_deaths_source','legacy_history_unconfirmed','points_provisional',live);
    else
      known=case when live then totals->>'known'='true' else last_row#>>'{metadata,actual_deaths}' is not null end;
      actual=case when live then (totals->>'actual_deaths')::bigint else (last_row#>>'{metadata,actual_deaths}')::bigint end;
      units=case when live then (totals->>'death_penalty_tenths')::bigint else (last_row#>>'{penalties,dead_count}')::bigint end;
      reduction=case when live then public.league_points_reduction(p_season_id,pid,coalesce(nextday.number,cfg.total_matchdays,1))
        else (last_row#>>'{penalties,points_reduction}')::numeric end;
      deduction=case when known then units::numeric/10+reduction end;
      net=case when not live then official when known then wins-deduction end;
      item=row||jsonb_build_object('official_points',official::text,'total_points',net::text,
        'normal_wins',wins,'total_penalties',deduction::text,
        'historical_deaths',case when known then actual end,
        'historical_deaths_status',case when known then 'known' when totals->>'valid'='true' then 'incomplete' else 'unknown' end,
        'historical_deaths_source',case when not live then 'frozen_official_snapshot' when known then 'audited_event_history' else totals->>'blocking_reason' end,
        'points_provisional',live);
    end if;
    rows=rows||jsonb_build_array(item);
  end loop;
  select coalesce(jsonb_agg(x order by (x->>'total_points')::numeric desc nulls last,
    lower(x->>'display_name') collate "C",x->>'trainer_id'),'[]'::jsonb) into rows from jsonb_array_elements(rows) x;
  return jsonb_set(result,'{rows}',rows)||jsonb_build_object('scoring_contract',case when net_contract then 'league_net_v1' else 'legacy_frozen' end,
    'matchday_scores',case when net_contract and live and nextday.id is not null then public.league_live_matchday_scores(p_season_id,nextday.id) else '[]'::jsonb end);
end $$;

-- Reuse the established atomic snapshot, reward and next-matchday pipeline.
create or replace function public.matchday_commit_close_v034(op text,r jsonb,ctx jsonb,plan jsonb) returns void
language plpgsql set search_path=pg_catalog,public as $$
declare sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid; actor uuid=(r->>'actor_trainer_id')::uuid;
  d public.matchdays; cfg public.season_config_versions; nxtcfg public.season_config_versions;
  old public.matchday_snapshots; v_snapshot jsonb; rev integer; final boolean; nextid uuid; divisionid uuid;
  pid uuid; tid uuid; gift uuid; giftplayer uuid; oldgift public.purchases; row jsonb; divcode text;
  v_amount integer; prior integer; stamp timestamptz=clock_timestamp();
  net boolean=ctx#>>'{inputs,config,scoring_mode}'='league_net_v1';
  rr boolean=ctx#>>'{inputs,config,scoring_mode}' in ('single_round_robin_v1','league_net_v1');
  common_coins integer; prize jsonb; prizes jsonb; expected_points integer;
begin
  select * into d from public.matchdays where id=did;
  select * into cfg from public.season_config_versions where id=d.season_config_version_id;
  select * into old from public.matchday_snapshots where matchday_id=did;
  rev=coalesce(old.revision,0)+1; final=d.number=cfg.total_matchdays;
  if op='correct' then
    perform public.matchday_results(did,r->'body'->'results',true);
    perform public.matchday_validate(sid,did,true);
  end if;
  if jsonb_typeof(plan->'standings') is distinct from 'array' or jsonb_array_length(plan->'standings')<>
    (select count(*) from public.participant_memberships_at(sid,d.number))
    or (select count(distinct value->>'trainer_id') from jsonb_array_elements(plan->'standings'))<>jsonb_array_length(plan->'standings') then
    perform public.admin_setup_fail('invalid_results'); end if;
  if rr then
    if not net and (cfg.total_matchdays<>1 or not public.single_round_robin_config(cfg)) then
      perform public.admin_setup_fail('config_mismatch'); end if;
    common_coins=public.single_league_common_coins(ctx#>'{inputs,config,coin_rewards_json}');
    if jsonb_typeof(plan->'single_league_rewards') is distinct from 'array'
      or jsonb_array_length(plan->'single_league_rewards')<>2 then
      perform public.admin_setup_fail('invalid_results'); end if;
    prizes=jsonb_build_array(
      jsonb_build_object('code','blindar_pokemon','season_player_id',
        (select x->>'trainer_id' from jsonb_array_elements(plan->'standings') x where (x->>'position')::integer=1)),
      jsonb_build_object('code','robar_pokemon','season_player_id',
        (select x->>'trainer_id' from jsonb_array_elements(plan->'standings') x where
          (x->>'position')::integer=jsonb_array_length(plan->'standings'))));
    if plan->'single_league_rewards' is distinct from prizes then
      perform public.admin_setup_fail('invalid_results'); end if;
    for prize in select value from jsonb_array_elements(prizes) loop
      if prize->>'season_player_id' is null or not exists(select 1 from public.shop_items
        where code=prize->>'code' and acquisition_mode='purchasable') then
        perform public.admin_setup_fail('reward_item_unavailable'); end if;
    end loop;
  elsif plan ? 'single_league_rewards' then perform public.admin_setup_fail('invalid_results'); end if;
  for row in select value from jsonb_array_elements(plan->'standings') loop
    if rr then
      select (case when net then 1 else 2 end)*count(*) into expected_points from public.matches m where m.matchday_id=did
        and m.status='completed' and m.winner_id=(row->>'trainer_id')::uuid;
    else expected_points=(cfg.scoring_json->>(row->>'position'))::integer; end if;
    if not exists(select 1 from public.season_players where id=(row->>'trainer_id')::uuid and season_id=sid
      and (status='active' or d.number<status_effective_matchday_number))
      or (row->>'coins_awarded')::integer is distinct from (case when rr then common_coins else (cfg.coin_rewards_json->>(row->>'position'))::integer end)
      or (row->>'points_awarded')::integer is distinct from expected_points then
      perform public.admin_setup_fail('invalid_results'); end if;
  end loop;
  giftplayer=(plan->>'last_b_player_id')::uuid;
  if not coalesce(net,false) and (cfg.rules_json->>'last_b_gets_steal')::boolean and exists (
    select 1 from public.participant_memberships_at(sid,d.number) m join public.divisions v on v.id=m.division_id where v.code='B'
  ) then
    select id into gift from public.shop_items where code='robar_pokemon' and acquisition_mode='purchasable' for share;
    if gift is null or giftplayer is null then perform public.admin_setup_fail('reward_item_unavailable'); end if;
  elsif giftplayer is not null then perform public.admin_setup_fail('invalid_results'); end if;
  v_snapshot=jsonb_build_object('schema_version',2,'revision',rev,'closed_at',stamp,'inputs',
    jsonb_set(ctx->'inputs','{matches}',plan->'matches'),'standings',plan->'standings',
    'new_divisions',plan->'new_divisions','last_b_player_id',giftplayer,'external_facts',ctx->'external_facts',
    'single_league_rewards',coalesce(prizes,'[]'::jsonb),'final',final,'reason',case when op='correct' then r->'body'->>'reason' else 'close' end);
  insert into public.matchday_snapshot_revisions(season_id,matchday_id,revision,snapshot,reason,created_by_trainer_id)
    values(sid,did,rev,v_snapshot,v_snapshot->>'reason',actor);
  if old.id is null then
    insert into public.matchday_snapshots(season_id,matchday_id,config_version_id,revision,snapshot_schema_version,closed_at,snapshot,created_by_trainer_id)
      values(sid,did,cfg.id,rev,2,stamp,v_snapshot,actor);
  else
    update public.matchday_snapshots set revision=rev,snapshot=v_snapshot,closed_at=stamp,created_by_trainer_id=actor where id=old.id;
  end if;
  for row in select value from jsonb_array_elements(plan->'standings') loop
    pid=(row->>'trainer_id')::uuid;
    select trainer_id into tid from public.season_players where id=pid;
    prior=0;
    if old.id is not null then select (x->>'coins_awarded')::integer into prior from jsonb_array_elements(old.snapshot->'standings') x where x->>'trainer_id'=pid::text; end if;
    v_amount=(row->>'coins_awarded')::integer-coalesce(prior,0);
    if v_amount<0 and (select coalesce(sum(amount),0) from public.coin_transactions where season_player_id=pid)+v_amount<0 then
      perform public.admin_setup_fail('correction_window_closed'); end if;
    if v_amount<>0 then
      insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type,reference_type,reference_id,
        reward_matchday_id,reward_revision,created_by_trainer_id,metadata)
        values(sid,tid,pid,v_amount,case when op='close' then 'matchday_reward' else 'compensation' end,
          'matchday_snapshot_revision',(select id from public.matchday_snapshot_revisions where matchday_id=did and revision=rev),
          did,rev,actor,jsonb_build_object('reason',v_snapshot->>'reason','previous_revision',rev-1));
    end if;
  end loop;
  if rr then
    -- Existing rewards remain valid when a correction leaves their recipient in place.
    -- The outer correction lock already refuses a spent reward or a redemption.
    for oldgift in select * from public.purchases where origin_matchday_id=did
      and status='pending' order by id for update loop
      if not exists(select 1 from jsonb_array_elements(prizes) q join public.shop_items i
        on i.code=q->>'code' where i.id=oldgift.shop_item_id
        and q->>'season_player_id'=oldgift.season_player_id::text) then
        update public.purchases set status='cancelled',metadata=metadata||
          jsonb_build_object('cancelled_by_revision',rev,'reason',v_snapshot->>'reason') where id=oldgift.id;
      end if;
    end loop;
    for prize in select value from jsonb_array_elements(prizes) loop
      pid=(prize->>'season_player_id')::uuid;
      select id into gift from public.shop_items where code=prize->>'code' and acquisition_mode='purchasable' for share;
      if not exists(select 1 from public.purchases where origin_matchday_id=did and
        season_player_id=pid and shop_item_id=gift and status='pending') then
        select trainer_id into tid from public.season_players where id=pid;
        insert into public.purchases(season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,status,
          acquisition_type,origin_matchday_id,origin_snapshot_revision)
          values(sid,tid,pid,gift,1,0,'pending','reward',did,rev);
      end if;
    end loop;
  else
  select * into oldgift from public.purchases where origin_matchday_id=did and status='pending' order by origin_snapshot_revision desc limit 1 for update;
  if oldgift.id is not null and oldgift.season_player_id is distinct from giftplayer then
    update public.purchases set status='cancelled',metadata=metadata||jsonb_build_object('cancelled_by_revision',rev,'reason',v_snapshot->>'reason') where id=oldgift.id;
  end if;
  if giftplayer is not null and (oldgift.id is null or oldgift.season_player_id<>giftplayer) then
    select trainer_id into tid from public.season_players where id=giftplayer;
    insert into public.purchases(season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,status,
      acquisition_type,origin_matchday_id,origin_snapshot_revision)
      values(sid,tid,giftplayer,gift,1,0,'pending','reward',did,rev);
  end if;
  end if;
  if not final then
    select * into nxtcfg from public.season_config_versions where season_id=sid and effective_from_matchday<=d.number+1
      order by effective_from_matchday desc limit 1;
    if nxtcfg.total_matchdays<d.number+1 or nxtcfg.division_sizes<>cfg.division_sizes then
      perform public.admin_setup_fail('config_mismatch'); end if;
    select id into nextid from public.matchdays where season_id=sid and number=d.number+1;
    if op='close' and nextid is not null then perform public.admin_setup_fail('dependent_data_exists'); end if;
    if op='correct' then
      delete from public.matchday_movements where matchday_id=did;
      delete from public.matches where matchday_id=nextid;
      delete from public.division_memberships where source_matchday_id=did;
    end if;
    update public.division_memberships set effective_to_matchday_number=d.number where season_id=sid
      and effective_from_matchday_number<=d.number and coalesce(effective_to_matchday_number,d.number)>=d.number
      and (eligibility_ends_before_matchday_number is null or d.number<eligibility_ends_before_matchday_number);
    foreach divcode in array array['A','B'] loop
      select id into divisionid from public.divisions where season_id=sid and code=divcode;
      for pid in select value::uuid from jsonb_array_elements_text(plan->'new_divisions'->divcode) loop
        insert into public.matchday_movements(season_id,matchday_id,season_player_id,from_division_id,to_division_id,movement_type,metadata)
          select sid,did,pid,m.division_id,divisionid,case when m.division_id=divisionid then 'stay' when divcode='A' then 'promotion' else 'relegation' end,
            jsonb_build_object('snapshot_revision',rev) from public.division_memberships m where m.season_player_id=pid
            and m.effective_from_matchday_number<=d.number and m.effective_to_matchday_number=d.number;
        insert into public.division_memberships(season_id,season_player_id,division_id,effective_from_matchday_number,source_matchday_id,reason)
          select sid,pid,divisionid,d.number+1,did,case when movement_type='stay' then 'initial' else movement_type end
            from public.matchday_movements where matchday_id=did and season_player_id=pid;
      end loop;
    end loop;
    if nextid is null then
      insert into public.matchdays(season_id,number,season_config_version_id) values(sid,d.number+1,nxtcfg.id) returning id into nextid;
    end if;
    insert into public.matches(season_id,matchday_id,division_id,player_a_id,player_b_id)
      select sid,nextid,a.division_id,a.season_player_id,b.season_player_id from public.division_memberships a
      join public.division_memberships b on (coalesce(net,false) or a.division_id=b.division_id) and a.season_player_id<b.season_player_id
      where a.season_id=sid and a.effective_from_matchday_number=d.number+1 and b.effective_from_matchday_number=d.number+1;
    perform public.matchday_validate(sid,nextid,false);
    if op='close' then
      for row in select value from jsonb_array_elements(plan->'promotions') loop
        insert into public.shop_promotions(season_id,matchday_id,shop_item_id,promotion_type,status,base_price,effective_price,stock_total,
          announced_at,activates_at,dedupe_key,metadata)
          values(sid,nextid,(row->>'shop_item_id')::uuid,row->>'promotion_type','pending',(row->>'base_price')::integer,
            (row->>'effective_price')::integer,(row->>'stock_total')::integer,stamp,stamp+interval '24 hours',
            'matchday:'||did::text||':'||(row->>'shop_item_id'),jsonb_build_object('source_matchday_id',did));
      end loop;
    end if;
    update public.seasons set current_matchday_id=nextid where id=sid;
  end if;
  if op='close' then
    update public.shop_promotions set status='ended',ends_at=stamp where season_id=sid and status in ('pending','active','exhausted')
      and matchday_id in (select id from public.matchdays where season_id=sid and number<=d.number);
  end if;
  update public.matchdays set status='closed',closed_at=coalesce(closed_at,stamp),revision=revision+1,results_revision=results_revision+1 where id=did;
end $$;

create or replace function public.check_purchase_acquisition() returns trigger
language plpgsql security invoker set search_path='' as $$
declare v_item public.shop_items; v_origin public.redemptions;
begin
  select * into v_item from public.shop_items where id=new.shop_item_id for share;
  if new.acquisition_type='paid' and v_item.acquisition_mode<>'purchasable' then
    raise sqlstate 'PT409' using message='item_unavailable'; end if;
  if new.acquisition_type='reward' and new.origin_matchday_id is not null then
    if v_item.acquisition_mode<>'purchasable' or not exists (
      select 1 from public.matchday_snapshot_revisions r join public.season_players p
        on p.id=new.season_player_id and p.season_id=r.season_id
      where r.matchday_id=new.origin_matchday_id and r.revision=new.origin_snapshot_revision
        and r.season_id=new.season_id and p.trainer_id=new.trainer_id and (
          (v_item.code='robar_pokemon' and r.snapshot->>'last_b_player_id'=p.id::text)
          or (r.snapshot#>>'{inputs,config,scoring_mode}' in ('single_round_robin_v1','league_net_v1')
            and v_item.code in ('blindar_pokemon','robar_pokemon') and exists(
              select 1 from jsonb_array_elements(r.snapshot->'single_league_rewards') prize
              where prize->>'season_player_id'=p.id::text and prize->>'code'=v_item.code)))
    ) then raise sqlstate 'PT409' using message='invalid_reward_origin'; end if;
  elsif new.acquisition_type='reward' then
    select * into v_origin from public.redemptions where id=new.origin_redemption_id;
    if not found or v_item.code<>'robbery_shield_voucher' or v_item.acquisition_mode<>'reward_only'
      or v_origin.effect_code is distinct from 'steal' or v_origin.status<>'applied'
      or v_origin.season_id<>new.season_id or v_origin.trainer_id<>new.trainer_id
      or v_origin.season_player_id<>new.season_player_id or v_origin.gift_purchase_id is distinct from new.id then
      raise sqlstate 'PT409' using message='invalid_reward_origin'; end if;
  end if;
  return new;
end $$;

create or replace function public.admin_setup_begin(op text,r jsonb) returns jsonb
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
  if op='matchday_close' and not coalesce(public.league_net_day((r->>'resource_id')::uuid),false) and r#>'{body,tie_resolution}' is not null and r#>'{body,tie_resolution}'<>'null'::jsonb then
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

-- Keep complete final-source checks, including allocation slots for the new ranking rule.
create or replace function public.championship_final_source(sid uuid) returns public.matchday_snapshot_revisions
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare finalday public.matchdays; cfg public.season_config_versions; d public.matchdays;
  snap public.matchday_snapshots; history public.matchday_snapshot_revisions; result public.matchday_snapshot_revisions;
  row jsonb; n integer;
begin
  if public.initial_assignment_modern(sid) and not exists(
    select 1 from public.initial_division_snapshots where season_id=sid
  ) then perform public.admin_setup_fail('historical_source_invalid'); end if;
  select md.* into finalday from public.matchdays md join public.seasons s on s.current_matchday_id=md.id
    where s.id=sid and md.season_id=sid;
  select * into cfg from public.season_config_versions where id=finalday.season_config_version_id;
  if finalday.id is null or finalday.status<>'closed' or finalday.number is distinct from cfg.total_matchdays
    or cfg.division_sizes is null or exists(select 1 from public.matchdays where season_id=sid and status<>'closed')
    or exists(select 1 from public.season_config_versions where season_id=sid and effective_from_matchday>finalday.number)
    or (select count(*) from public.matchdays where season_id=sid)<>finalday.number
    or (select min(number) from public.matchdays where season_id=sid)<>1
    or (select max(number) from public.matchdays where season_id=sid)<>finalday.number then
    perform public.admin_setup_fail('competition_incomplete'); end if;
  for d in select * from public.matchdays where season_id=sid order by number for update loop
    perform 1 from public.matches where matchday_id=d.id order by id for update;
    perform public.matchday_validate_v035(sid,d.id,true);
    select * into snap from public.matchday_snapshots where matchday_id=d.id for share;
    select * into history from public.matchday_snapshot_revisions where matchday_id=d.id and revision=snap.revision for share;
    if snap.id is null or history.id is null or snap.snapshot_schema_version<>2 or snap.config_version_id<>d.season_config_version_id
      or history.snapshot is distinct from snap.snapshot or history.season_id<>sid
      or snap.revision<>(select max(revision) from public.matchday_snapshot_revisions where matchday_id=d.id)
      or (history.snapshot->>'final')::boolean is distinct from (d.id=finalday.id)
      or history.snapshot#>>'{inputs,season_id}' is distinct from sid::text
      or history.snapshot#>>'{inputs,day_id}' is distinct from d.id::text
      or history.snapshot#>>'{inputs,config,id}' is distinct from d.season_config_version_id::text
      or jsonb_typeof(history.snapshot->'standings') is distinct from 'array' then
      perform public.admin_setup_fail('historical_source_invalid'); end if;
    if (select coalesce(jsonb_agg(jsonb_build_object('id',m.id,'player_a_id',m.player_a_id,'player_b_id',m.player_b_id,
        'winner_id',m.winner_id,'division',v.code) order by m.id),'[]') from public.matches m join public.divisions v on v.id=m.division_id
        where m.matchday_id=d.id) is distinct from
      (select coalesce(jsonb_agg(value order by (value->>'id')::uuid),'[]') from jsonb_array_elements(history.snapshot#>'{inputs,matches}')) then
      perform public.admin_setup_fail('historical_source_invalid'); end if;
    n=jsonb_array_length(history.snapshot->'standings');
    if n<>(select count(*) from public.participant_memberships_at(sid,d.number))
      or n<>(select count(distinct r->>'trainer_id') from jsonb_array_elements(history.snapshot->'standings') r)
      or n<>(select count(distinct case when history.snapshot#>>'{inputs,ranking,rule}' in ('wins_adjusted_deaths_v1','wins_segment_deaths_v2')
          then (r#>>'{metadata,allocation_position}')::integer else (r->>'position')::integer end)
        from jsonb_array_elements(history.snapshot->'standings') r
        where (case when history.snapshot#>>'{inputs,ranking,rule}' in ('wins_adjusted_deaths_v1','wins_segment_deaths_v2')
          then (r#>>'{metadata,allocation_position}')::integer else (r->>'position')::integer end) between 1 and n) then perform public.admin_setup_fail('historical_source_invalid'); end if;
    for row in select value from jsonb_array_elements(history.snapshot->'standings') loop
      if not exists(select 1 from public.participant_memberships_at(sid,d.number) where season_player_id=(row->>'trainer_id')::uuid)
        or (row->>'coins_awarded')::integer is distinct from (select coalesce(sum(amount),0) from public.coin_transactions
          where reward_matchday_id=d.id and season_player_id=(row->>'trainer_id')::uuid) then
        perform public.admin_setup_fail('historical_source_invalid'); end if;
    end loop;
    if history.snapshot->>'last_b_player_id' is not null and not exists (
      select 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id
      where p.origin_matchday_id=d.id and p.season_player_id=(history.snapshot->>'last_b_player_id')::uuid
        and p.acquisition_type='reward' and p.unit_price=0 and p.status not in ('cancelled','refunded') and i.code='robar_pokemon'
    ) then perform public.admin_setup_fail('historical_source_invalid'); end if;
    if d.id=finalday.id then result=history; end if;
  end loop;
  return result;
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
  if public.league_net_season(sid) and jsonb_array_length(leaders)>1 then
    -- No championship tiebreak has been authorized for the new NET contract.
    -- Old BO3/death rules and old manual resolutions cannot decide a new title.
    return result||jsonb_build_object('state','owner_decision_required','input_hash',fingerprint,
      'players',players,'tied_player_ids',leaders,'champion_trainer_id',null,
      'resolution_type',null,'blocking_reason','league_net_championship_tie_rule_required',
      '_source_snapshot_revision_id',source.id);
  end if;
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

-- Include immutable history/counter/source revisions in the existing correction fingerprint.
alter function public.matchday_external_facts(uuid) rename to matchday_external_facts_v074;
create function public.matchday_external_facts(sid uuid) returns text
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare original text; facts jsonb;
begin
  original=public.matchday_external_facts_v074(sid);
  if not public.league_net_season(sid) then return original; end if;
  select jsonb_agg(public.league_death_totals(p.id) order by p.id) into facts from public.season_players p where p.season_id=sid;
  return encode(sha256(convert_to(original||coalesce(facts::text,'[]'),'UTF8')),'hex');
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.league_net_season(uuid)'::regprocedure,'public.league_net_day(uuid)'::regprocedure,
    'public.league_prepare_round_robin(uuid,uuid)'::regprocedure,'public.league_points_reduction(uuid,uuid,integer)'::regprocedure,
    'public.league_live_matchday_scores(uuid,uuid)'::regprocedure,
    'public.matchday_validate_v035(uuid,uuid,boolean)'::regprocedure,'public.matchday_validate_pre075(uuid,uuid,boolean)'::regprocedure,
    'public.matchday_context(text,jsonb)'::regprocedure,'public.matchday_context_v074(text,jsonb)'::regprocedure,
    'public.matchday_commit_close(text,jsonb,jsonb,jsonb)'::regprocedure,'public.matchday_commit_close_v074(text,jsonb,jsonb,jsonb)'::regprocedure,
    'public.matchday_commit_close_v034(text,jsonb,jsonb,jsonb)'::regprocedure,
    'public.matchday_lock(text,jsonb)'::regprocedure,'public.matchday_lock_v074(text,jsonb)'::regprocedure,
    'public.matchday_external_facts(uuid)'::regprocedure,'public.matchday_external_facts_v074(uuid)'::regprocedure,
    'public.league_general_read(uuid)'::regprocedure,'public.league_general_read_v074(uuid)'::regprocedure,
    'public.admin_setup_validate_config(uuid,jsonb)'::regprocedure,'public.admin_setup_validate_config_v074(uuid,jsonb)'::regprocedure,
    'public.admin_setup_begin(text,jsonb)'::regprocedure,'public.check_purchase_acquisition()'::regprocedure,
    'public.championship_final_source(uuid)'::regprocedure,'public.championship_context(uuid)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
