-- 077: explicit audited correction of a falsely observed death. Immutable source
-- events and closed sporting snapshots are retained. Moving a Pokemon alone does
-- not invalidate a death; only a separately confirmed admin decision can do so.
begin;

create function public.league_effective_death_events(pid uuid)
returns setof public.league_death_events
language sql stable security invoker set search_path=pg_catalog,public as $$
 select e.* from public.league_death_events e where e.season_player_id=pid
 and not exists(select 1 from public.league_death_resolutions r,
   lateral jsonb_array_elements_text(coalesce(r.confirmed_counts->'invalidated_event_ids','[]'::jsonb)) invalid(id)
   where r.season_player_id=pid and invalid.id::uuid=e.id)
$$;
revoke all on function public.league_effective_death_events(uuid) from public,anon,authenticated,service_role;
grant execute on function public.league_effective_death_events(uuid) to service_role;
create or replace function public.league_track_deaths(pid uuid) returns void
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
   select e.* into previous from public.league_effective_death_events(pid) e join public.pokemon_identity_revisions r on r.id=e.identity_revision_id
     where e.season_player_id=pid and e.pokemon_entity_id=o.pokemon_entity_id order by r.revision_number desc,e.recorded_at desc limit 1;
   cycle='initial';
   rearm=h.revived_entities->o.pokemon_entity_id::text;
   -- A voided initial event retains its immutable uniqueness key. The explicit
   -- correction grants one fresh observation boundary, not a revive or wipe.
   if previous.id is null and rearm->>'token' like 'correction:%'
     and (rearm->>'after_revision_number')::bigint<(src->>'revision_number')::bigint then
     cycle=rearm->>'token';
   end if;
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

create or replace function public.league_death_totals(pid uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; h public.league_death_history; st public.season_player_stats;
 src jsonb; actual bigint; reason text; wipe_revision bigint; recorded bigint;
begin
 select * into p from public.season_players where id=pid;
 select * into h from public.league_death_history where season_player_id=pid;
 select * into st from public.season_player_stats where season_player_id=pid;
 src=public.league_death_source(pid);
 select count(*) into recorded from public.league_effective_death_events(pid);
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
   'wipe_counter',st.revived_after_wipe,'wipe_revision',wipe_revision,'recorded_deaths',recorded,
   'raw_recorded_deaths',(select count(*) from public.league_death_events where season_player_id=pid),
   'invalidated_event_ids',(select coalesce(jsonb_agg(e.id order by e.id),'[]'::jsonb)
     from public.league_death_events e where e.season_player_id=pid
       and not exists(select 1 from public.league_effective_death_events(pid) effective where effective.id=e.id)));
end $$;

create or replace function public.league_death_segment(pid uuid,did uuid) returns bigint
language sql stable security invoker set search_path=pg_catalog,public as $$
 select count(e.id)+coalesce((select segment_offset from public.league_death_history h
     where h.season_player_id=pid and h.segment_matchday_id is not distinct from did),
   case when (select number from public.matchdays where id=did)=1 then
     (select segment_offset from public.league_death_history where season_player_id=pid and segment_matchday_id is null) else 0 end,0)
 from public.league_effective_death_events(pid) e where e.season_player_id=pid
   and ((e.matchday_id=did and e.phase='progression') or
     (e.phase='preseason' and (select number from public.matchdays where id=did)=1))
$$;

create or replace function public.league_freeze_death_segment(sid uuid,did uuid,actor uuid) returns void
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
     array(select id from public.league_effective_death_events(p.id) order by id),
     array(select id from public.league_death_resolutions where season_player_id=p.id order by id),
     (facts->>'observed_at')::timestamptz,actor);
 end loop;
end $$;

create or replace function public.league_death_admin_state(pid uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare totals jsonb; p public.season_players; s public.seasons; d public.matchdays; segment bigint;
begin
 select * into p from public.season_players where id=pid;
 select * into s from public.seasons where id=p.season_id;
 select * into d from public.matchdays where id=s.current_matchday_id;
 totals=public.league_death_totals(pid);
 segment=case when d.id is null then (select count(*) from public.league_effective_death_events(pid) where phase='preseason')
   +coalesce((select segment_offset from public.league_death_history where season_player_id=pid and segment_matchday_id is null),0)
   else coalesce((select segment_deaths from public.matchday_death_snapshots where matchday_id=d.id and season_player_id=pid),public.league_death_segment(pid,d.id)) end;
 return totals||jsonb_build_object('current_matchday_id',d.id,'segment_deaths',case when (totals->>'known')::boolean then segment end,
   'can_reconcile',s.status in ('draft','active') and coalesce(d.status,'scheduled') in ('scheduled','open') and (totals->>'valid')::boolean,
   'observed_dead_entities',coalesce((select jsonb_agg(jsonb_build_object('pokemon_entity_id',o.pokemon_entity_id,
     'currently_dead',o.source='box' and o.box_number=p.dead_box_number,
     'has_recorded_death',exists(select 1 from public.league_effective_death_events(pid) e where e.pokemon_entity_id=o.pokemon_entity_id),
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

create or replace function public.api_admin_death_history(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare op text=p_request->>'operation'; r jsonb=p_request->'request'; b jsonb=r->'body';
 sid uuid=(r->>'season_id')::uuid; pid uuid=(r->>'resource_id')::uuid; actor uuid=(r->>'actor_trainer_id')::uuid;
 cached jsonb; before jsonb; result jsonb; src jsonb; h public.league_death_history; s public.seasons; d public.matchdays;
 actual bigint; wipes bigint; segment bigint; recorded bigint; segment_recorded bigint; frozen bigint;
 resolution_id uuid=gen_random_uuid(); oid uuid=gen_random_uuid(); event_id uuid=gen_random_uuid(); rearm jsonb; entity text;
 invalidated jsonb=coalesce(b->'invalidated_event_ids','[]'::jsonb); invalidated_count integer; invalidated_segment bigint;
 invalid_event record;
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
 if jsonb_typeof(b) is distinct from 'object' or b-array['actual_deaths','wipe_deaths','segment_deaths','source_sha256','expected_revision','reason','evidence','revived_entity_ids','invalidated_event_ids']<>'{}'::jsonb
   or exists(select 1 from unnest(array['actual_deaths','wipe_deaths','segment_deaths','expected_revision']) k
     where jsonb_typeof(b->k) is distinct from 'number' or (b->>k)!~'^(0|[1-9][0-9]{0,8})$')
   or jsonb_typeof(b->'source_sha256') is distinct from 'string' or (b->>'source_sha256')!~'^[a-f0-9]{64}$'
   or jsonb_typeof(b->'reason') is distinct from 'string' or length(btrim(b->>'reason')) not between 1 and 500
   or jsonb_typeof(b->'evidence') is distinct from 'string' or length(btrim(b->>'evidence')) not between 1 and 2000
   or jsonb_typeof(coalesce(b->'revived_entity_ids','[]')) is distinct from 'array' then
   perform public.admin_setup_fail('death_history_evidence_required',422); end if;
 if jsonb_typeof(invalidated) is distinct from 'array' then
   perform public.admin_setup_fail('death_history_evidence_required',422); end if;
 invalidated_count=jsonb_array_length(invalidated);
 if invalidated_count>500 or exists(select 1 from jsonb_array_elements(invalidated) id
     where jsonb_typeof(id) is distinct from 'string' or id#>>'{}' !~ '^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$') then
   perform public.admin_setup_fail('death_history_evidence_required',422); end if;
 if invalidated_count<>(select count(distinct selected.value::uuid) from jsonb_array_elements_text(invalidated) selected(value)) then
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
 if invalidated_count>0 then
   -- This is an explicit correction of an initial false observation, never an
   -- automatic pardon for moving/reviving a genuinely dead Pokemon.
   if not coalesce((before->>'known')::boolean,false) then
     perform public.admin_setup_fail('death_history_baseline_required'); end if;
   if (before->>'wipe_counter')::bigint<>0 or public.league_unmapped_revives(pid)<>0
     or jsonb_array_length(coalesce(b->'revived_entity_ids','[]'))<>0 then
     perform public.admin_setup_fail('death_history_event_not_correctable'); end if;
   if (select count(*) from public.league_effective_death_events(pid) e
       where e.id in (select selected.value::uuid from jsonb_array_elements_text(invalidated) selected(value)))<>invalidated_count then
     perform public.admin_setup_fail('death_history_event_not_correctable'); end if;
   for invalid_event in select e.*,r.revision_number as event_revision
     from public.league_effective_death_events(pid) e join public.pokemon_identity_revisions r on r.id=e.identity_revision_id
     where e.id in (select selected.value::uuid from jsonb_array_elements_text(invalidated) selected(value)) loop
     if invalid_event.event_revision>=(src->>'revision_number')::bigint
       or (invalid_event.cycle_key<>'initial' and invalid_event.cycle_key not like 'correction:%')
       or (rearm ? invalid_event.pokemon_entity_id::text and
           coalesce(rearm#>>array[invalid_event.pokemon_entity_id::text,'token'],'') not like 'correction:%')
       or exists(select 1 from public.redemptions red where red.season_player_id=pid and red.effect_code='revive'
           and red.status='applied' and red.target_pokemon_entity_id=invalid_event.pokemon_entity_id)
       or not exists(select 1 from public.pokemon_observations current_observation
           join public.pokemon_observations old_observation on old_observation.id=invalid_event.observation_id
           where current_observation.revision_id=(src->>'identity_revision_id')::uuid
             and current_observation.pokemon_entity_id=invalid_event.pokemon_entity_id
             and current_observation.outcome in ('NEW','MATCHED')
             and (current_observation.source='party' or current_observation.box_number<>(src->>'dead_box_number')::integer)
             and current_observation.evidence->'pid' is not distinct from old_observation.evidence->'pid'
             and current_observation.evidence->'encryption_constant' is not distinct from old_observation.evidence->'encryption_constant') then
       perform public.admin_setup_fail('death_history_event_not_correctable'); end if;
     if exists(select 1 from public.matchday_death_snapshots frozen_snapshot where frozen_snapshot.season_player_id=pid
         and (invalid_event.id=any(frozen_snapshot.event_ids) or invalid_event.recorded_at<=frozen_snapshot.confirmed_at)) then
       perform public.admin_setup_fail('death_history_event_frozen'); end if;
     rearm=rearm||jsonb_build_object(invalid_event.pokemon_entity_id::text,jsonb_build_object(
       'token','correction:'||resolution_id::text||':'||invalid_event.pokemon_entity_id::text,
       'after_revision_number',src->'revision_number'));
   end loop;
   select count(*) into invalidated_segment from public.league_effective_death_events(pid) e
     where e.id in (select selected.value::uuid from jsonb_array_elements_text(invalidated) selected(value))
       and ((e.matchday_id=d.id and e.phase='progression') or (e.phase='preseason' and (d.number=1 or d.id is null)));
   if actual<>(before->>'actual_deaths')::bigint-invalidated_count
     or segment<>(before->>'segment_deaths')::bigint-invalidated_segment then
     perform public.admin_setup_fail('death_history_inconsistent'); end if;
 end if;
 for entity in select jsonb_array_elements_text(coalesce(b->'revived_entity_ids','[]')) loop
   if entity!~'^[a-fA-F0-9-]{36}$' or not exists(select 1 from public.league_effective_death_events(pid) where pokemon_entity_id=entity::uuid)
     or not exists(select 1 from public.pokemon_observations o where o.revision_id=(src->>'identity_revision_id')::uuid
       and o.pokemon_entity_id=entity::uuid and (o.source='party' or o.box_number<>(src->>'dead_box_number')::integer)) then
     perform public.admin_setup_fail('death_history_inconsistent'); end if;
   rearm=rearm||jsonb_build_object(entity,jsonb_build_object('token','audit:'||resolution_id::text,'after_revision_number',src->'revision_number'));
 end loop;
 select count(*) into recorded from public.league_effective_death_events(pid)
   where id not in (select selected.value::uuid from jsonb_array_elements_text(invalidated) selected(value));
 select count(*) into segment_recorded from public.league_effective_death_events(pid) e where e.season_player_id=pid
   and e.id not in (select selected.value::uuid from jsonb_array_elements_text(invalidated) selected(value))
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

commit;
