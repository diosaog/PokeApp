-- 081: calculate official NET directly from valid observed history.
-- Owner-authorized 2026-11-04. No player confirmation, backfill or balance write.
-- Existing audited offsets, effective events (077/080), gaps and source guards
-- remain authoritative. CREATE OR REPLACE preserves owner and existing ACLs.
begin;

do $$ begin
 if md5(replace(pg_get_functiondef('public.league_death_totals(uuid)'::regprocedure),chr(13),''))
    <> '650e4b005b4f233244d390d81a114893' then
   raise exception 'unexpected league_death_totals definition before 081';
 end if;
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
 actual=coalesce(h.actual_offset,0)+recorded;
 reason=case when not (src->>'valid')::boolean then 'death_history_source_unavailable'
   when wipe_revision is null then 'death_history_wipe_state_unavailable'
   when h.season_player_id is null then 'death_history_source_unavailable'
   when h.dead_box_number<>p.dead_box_number then 'death_history_dead_box_changed'
   when h.blocking_reason is not null then h.blocking_reason
   when h.last_identity_revision_id is distinct from (src->>'identity_revision_id')::uuid then 'death_history_source_changed'
   when coalesce(h.confirmed_unmapped_revives,0) is distinct from public.league_unmapped_revives(pid) then 'death_history_unmapped_revival'
   when actual<0 or st.revived_after_wipe<0 or st.revived_after_wipe>actual then 'death_history_inconsistent' else null end;
 return src||jsonb_build_object('known',reason is null,'blocking_reason',reason,
   'season_id',p.season_id,'season_player_id',pid,'trainer_id',p.trainer_id,'revision',coalesce(h.revision,0),
   'actual_deaths',case when reason is null then actual end,
   'wipe_deaths',case when reason is null then st.revived_after_wipe end,
   'death_penalty_tenths',case when reason is null then actual+st.revived_after_wipe end,
   'wipe_counter',st.revived_after_wipe,'wipe_revision',wipe_revision,'recorded_deaths',recorded,
   'raw_recorded_deaths',(select count(*) from public.league_death_events where season_player_id=pid),
   'invalidated_event_ids',(select coalesce(jsonb_agg(e.id order by e.id),'[]'::jsonb)
     from public.league_death_events e where e.season_player_id=pid
       and not exists(select 1 from public.league_effective_death_events(pid) effective where effective.id=e.id)));
end $$;

commit;
