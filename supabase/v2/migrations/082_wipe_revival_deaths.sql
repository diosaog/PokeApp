-- 082: a wipe revival is a genuine death of its own, charged 0.2 in total.
--
-- Approved rule (Package G, 075 NET): an ordinary death costs 0.1 and a death
-- revived through a wipe costs 0.2 instead (never both). The trainer-owned,
-- audited counter (038) is the only evidence of a wipe: the whiteout heals the
-- party in-game, so those Pokémon normally never reach the dead box. 081
-- treated the counter as a subset of the observed dead-box events, so a wipe
-- report either cost only +0.1 (enough other observed deaths) or made the whole
-- NET unknown (more wipe revivals than observed deaths).
--
-- Now: actual deaths = audited offset + effective observed events + counted
-- wipe deaths not already inside an audited baseline, minus observed deaths
-- that the wipe itself explains (the same Pokémon seen dead, then alive again
-- with no comodín or audited revival). Penalty tenths stay actual + wipe.
-- Matchday state is not an input. Source, gap, box, unmapped-revive and
-- inconsistency guards, 077 corrections and 080 entry exclusions are kept.
-- One read function only: no table, row, ACL, snapshot or ledger is changed.
-- Closed snapshots keep their frozen values. Owner approval required to apply.
begin;

do $$ begin
 if md5(replace(pg_get_functiondef('public.league_death_totals(uuid)'::regprocedure),chr(13),''))
    <> '5719f5f68cda5d7fb14d0f7923e61333' then
   raise exception 'unexpected league_death_totals definition before 082';
 end if;
end $$;

create or replace function public.league_death_totals(pid uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; h public.league_death_history; st public.season_player_stats;
 src jsonb; actual bigint; reason text; wipe_revision bigint; recorded bigint;
 folded bigint; unobserved bigint; explained bigint;
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
 -- An audited 075 baseline already counted its confirmed wipe deaths in actual_offset.
 folded=case when h.actual_offset is not null then coalesce(h.confirmed_wipe_deaths,0) else 0 end;
 unobserved=st.revived_after_wipe-folded;
 -- Never charge one death twice: a later observed death whose Pokémon is alive
 -- again without a comodín or an audited revival is taken as one of the wipe's.
 select count(distinct e.pokemon_entity_id) into explained from public.league_effective_death_events(pid) e
  where e.recorded_at>coalesce(h.confirmed_at,'-infinity'::timestamptz)
    and exists(select 1 from public.pokemon_observations o
      where o.revision_id=(src->>'identity_revision_id')::uuid and o.pokemon_entity_id=e.pokemon_entity_id
        and (o.source='party' or o.box_number<>p.dead_box_number))
    and not exists(select 1 from public.redemptions r where r.season_player_id=pid and r.effect_code='revive'
      and r.status='applied' and r.target_pokemon_entity_id=e.pokemon_entity_id)
    and not coalesce(h.revived_entities ? e.pokemon_entity_id::text,false);
 explained=least(explained,greatest(coalesce(unobserved,0),0));
 actual=coalesce(h.actual_offset,0)+recorded+unobserved-explained;
 reason=case when not (src->>'valid')::boolean then 'death_history_source_unavailable'
   when wipe_revision is null then 'death_history_wipe_state_unavailable'
   when h.season_player_id is null then 'death_history_source_unavailable'
   when h.dead_box_number<>p.dead_box_number then 'death_history_dead_box_changed'
   when h.blocking_reason is not null then h.blocking_reason
   when h.last_identity_revision_id is distinct from (src->>'identity_revision_id')::uuid then 'death_history_source_changed'
   when coalesce(h.confirmed_unmapped_revives,0) is distinct from public.league_unmapped_revives(pid) then 'death_history_unmapped_revival'
   when unobserved<0 or actual<0 or st.revived_after_wipe<0 or st.revived_after_wipe>actual then 'death_history_inconsistent' else null end;
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
