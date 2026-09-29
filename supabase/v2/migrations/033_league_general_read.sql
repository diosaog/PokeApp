-- Phase 10.5B: one coherent service-only GENERAL read. No competition mutation.
begin;

create function public.league_observed_dead_count(payload jsonb) returns integer
language plpgsql immutable security invoker set search_path=pg_catalog,public as $$
declare box jsonb; slot jsonb; seen integer[]='{}'; n integer; occupied integer=0;
begin
  if jsonb_typeof(payload->'boxes') is distinct from 'array' then return null; end if;
  if (select count(*) from jsonb_array_elements(payload->'boxes') b
      where b->'box_number'='8'::jsonb)<>1 then return null; end if;
  select b into box from jsonb_array_elements(payload->'boxes') b where b->'box_number'='8'::jsonb;
  if jsonb_typeof(box->'slots') is distinct from 'array' then return null; end if;
  if jsonb_array_length(box->'slots')<>30 then return null; end if;
  for slot in select * from jsonb_array_elements(box->'slots') loop
    if jsonb_typeof(slot->'slot_number') is distinct from 'number'
       or (slot->>'slot_number') !~ '^([1-9]|[12][0-9]|30)$'
       or not (slot ? 'pokemon') then return null; end if;
    n=(slot->>'slot_number')::integer;
    if n=any(seen) then return null; end if;
    seen=array_append(seen,n);
    if slot->'pokemon'<>'null'::jsonb then
      if jsonb_typeof(slot->'pokemon') is distinct from 'object'
         or jsonb_typeof(slot#>'{pokemon,species}') is distinct from 'string'
         or length(btrim(slot#>>'{pokemon,species}'))=0 then return null; end if;
      occupied=occupied+1;
    end if;
  end loop;
  return occupied;
end $$;

create function public.league_general_read(p_season_id uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare result jsonb;
begin
  -- Fail explicitly for unsupported history; do not turn ignored imports into zero.
  if exists(select 1 from public.matchday_snapshots where season_id=p_season_id
     and (snapshot_schema_version<>2 or snapshot->'schema_version' is distinct from '2'::jsonb
       or jsonb_typeof(snapshot->'standings') is distinct from 'array')) then
    raise sqlstate 'PT503' using message='unsupported_official_snapshot';
  end if;
  if exists(select 1 from public.matchday_snapshots s,
      jsonb_array_elements(s.snapshot->'standings') v where s.season_id=p_season_id
      and (jsonb_typeof(v->'trainer_id') is distinct from 'string'
        or jsonb_typeof(v->'points_awarded') is distinct from 'number')) then
    raise sqlstate 'PT503' using message='unsupported_official_standing';
  end if;
  if (select count(*) from public.season_players where season_id=p_season_id)>500 then
    raise sqlstate 'PT503' using message='read_capacity_exceeded';
  end if;
  with balances as (
    -- Judicial debts can exceed int32 although each individual movement fits it.
    select trainer_id,sum(amount) as balance from public.coin_transactions
    where season_id=p_season_id group by trainer_id
  ), roster as (
    select p.id as season_player_id,p.trainer_id,p.status,t.display_name,
      coalesce(points.sanctioned_points,0) as total_points,points.source_matchday_id,
      coalesce(coins.balance,0) as coin_balance,
      public.league_observed_dead_count(parsed.payload) as dead_count,parsed.parsed_at
    from public.season_players p
    join public.trainers t on t.id=p.trainer_id
    left join public.public_sanctioned_points points on points.season_id=p.season_id and points.season_player_id=p.id
    left join balances coins on coins.trainer_id=p.trainer_id
    left join public.save_files saved on saved.id=p.current_save_file_id
      and saved.season_id=p.season_id and saved.trainer_id=p.trainer_id
      and saved.deleted_at is null and saved.parser_status='parsed'
    left join public.pokemon_identity_revisions identity on identity.save_file_id=saved.id
      and identity.season_id=p.season_id and identity.trainer_id=p.trainer_id
    left join public.parsed_saves parsed on parsed.id=identity.parsed_save_id
      and parsed.save_file_id=saved.id and parsed.parser_version=saved.parser_version
      and parsed.status='parsed' and parsed.schema_version=1
      and (not (parsed.payload ? 'save_record_id') or parsed.payload->>'save_record_id'=saved.id::text)
      and (not (parsed.payload ? 'trainer_id') or parsed.payload->>'trainer_id'=p.trainer_id::text)
      and (not (parsed.payload ? 'source_hash') or parsed.payload->>'source_hash'=saved.sha256)
    where p.season_id=p_season_id
  )
  select jsonb_build_object(
    'season',jsonb_build_object('id',s.id,'name',s.name,'status',s.status,'current_matchday_id',s.current_matchday_id),
    'days',coalesce((select jsonb_agg(jsonb_build_object('id',d.id,'number',d.number,'status',d.status) order by d.number)
      from public.matchdays d where d.season_id=s.id and (d.status='closed' or d.id=s.current_matchday_id)),'[]'::jsonb),
    'rows',coalesce((select jsonb_agg(jsonb_build_object(
      'season_player_id',r.season_player_id,'trainer_id',r.trainer_id,'display_name',r.display_name,'status',r.status,
      'total_points',r.total_points::text,'points_source_matchday_id',r.source_matchday_id,
      'coin_balance',r.coin_balance::text,'dead_count',r.dead_count,
      'dead_count_source',case when r.dead_count is null then 'unknown' else 'observed_current_save' end,
      'dead_count_observed_at',case when r.dead_count is not null then r.parsed_at end
    ) order by r.total_points desc,lower(r.display_name) collate "C",r.trainer_id) from roster r),'[]'::jsonb)
  ) into result from public.seasons s where s.id=p_season_id and s.status<>'discarded';
  return result;
end $$;

revoke all on function public.league_observed_dead_count(jsonb),public.league_general_read(uuid) from public,anon,authenticated;
grant execute on function public.league_observed_dead_count(jsonb),public.league_general_read(uuid) to service_role;
comment on function public.league_general_read(uuid) is
  'Enabled JWT API only. Exact official totals; secondary order is presentation, never title resolution. Current coins and complete observed Box 8 counts do not rewrite history. No private save fields returned.';
commit;
