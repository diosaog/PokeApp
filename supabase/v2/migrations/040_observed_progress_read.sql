-- L: current save facts only. Reuse E/I validation; never settle rewards on reads.
begin;

create function public.observed_progress_read(p_season_id uuid, p_trainer_id uuid default null)
returns jsonb language plpgsql stable security invoker
set search_path=pg_catalog,public as $$
declare result jsonb;
begin
  if not exists(select 1 from public.seasons where id=p_season_id and status<>'discarded') then
    return null;
  end if;
  if (select count(*) from public.season_players where season_id=p_season_id)>500 then
    raise exception 'Progress read capacity exceeded';
  end if;
  -- One statement snapshot binds current pointer, latest accepted identity revision,
  -- owned source and parsed payload. A stale pointer is not current evidence.
  select coalesce(jsonb_agg(jsonb_build_object(
    'id',p.id,'trainer_id',p.trainer_id,
    'game',case when proof.progress is not null then parsed.payload#>>'{observed_progress,game}' end,
    'observed_at',case when proof.progress is not null then head.created_at end,
    'progress',proof.progress) order by p.id),'[]'::jsonb) into result
  from public.season_players p
  left join lateral (
    select i.* from public.pokemon_identity_revisions i
    where i.season_id=p.season_id and i.trainer_id=p.trainer_id
    order by i.revision_number desc limit 1
  ) head on head.save_file_id=p.current_save_file_id
  left join public.save_files saved on saved.id=head.save_file_id
    and saved.season_id=p.season_id and saved.trainer_id=p.trainer_id
  left join public.parsed_saves parsed on parsed.id=head.parsed_save_id
    and parsed.save_file_id=saved.id
  cross join lateral (select public.observed_save_progress(saved,parsed,p.trainer_id) as progress) proof
  where p.season_id=p_season_id and (p_trainer_id is null or p.trainer_id=p_trainer_id);
  return result;
end $$;
revoke all on function public.observed_progress_read(uuid,uuid) from public,anon,authenticated;
grant execute on function public.observed_progress_read(uuid,uuid) to service_role;

commit;
