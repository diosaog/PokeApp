-- Explicit competitive round and typed inclusive penalty windows. No backfill.
begin;

alter table public.seasons add column if not exists current_matchday_id uuid;
alter table public.penalties add column if not exists start_matchday_number integer;
alter table public.penalties add column if not exists end_matchday_number integer;
do $$
begin
  if not exists (select 1 from pg_constraint where conrelid='public.seasons'::regclass and conname='fk_seasons_current_matchday_same_season') then
    alter table public.seasons add constraint fk_seasons_current_matchday_same_season
      foreign key (current_matchday_id, id) references public.matchdays(id, season_id) on delete restrict;
  end if;
  if not exists (select 1 from pg_constraint where conrelid='public.penalties'::regclass and conname='penalties_window_chk') then
    alter table public.penalties add constraint penalties_window_chk check (
      (start_matchday_number is null or start_matchday_number > 0)
      and (end_matchday_number is null or end_matchday_number > 0)
      and (start_matchday_number is null or end_matchday_number is null or start_matchday_number <= end_matchday_number)
    );
  end if;
end;
$$;

comment on column public.seasons.current_matchday_id is
  'Server-owned competitive jornada, not inferred from status/order. Future season creation and close/advance operations maintain this pointer transactionally.';
comment on column public.penalties.start_matchday_number is
  'Inclusive store-ban start. If either boundary is NULL, preserve legacy active no-window compatibility.';
comment on column public.penalties.end_matchday_number is
  'Inclusive store-ban end. resolved_at alone does not cancel a store ban.';

-- Preserve prior admin column rights, but the new pointer is backend-owned.
do $$
declare prior_columns text;
begin
  select string_agg(quote_ident(attname), ', ' order by attnum) into prior_columns
  from pg_attribute where attrelid='public.seasons'::regclass
    and attnum > 0 and not attisdropped and attname <> 'current_matchday_id';
  revoke insert, update on public.seasons from authenticated;
  execute format('grant insert (%s), update (%s) on public.seasons to authenticated', prior_columns, prior_columns);
end;
$$;

create or replace function public.api_resolve_current_matchday(p_season_id uuid)
returns setof public.matchdays
language plpgsql security invoker set search_path = '' as $$
declare
  season_row public.seasons%rowtype;
  day_row public.matchdays%rowtype;
begin
  select * into season_row from public.seasons where id=p_season_id for share;
  if not found then raise sqlstate 'PT404' using message='season_not_found'; end if;
  if season_row.current_matchday_id is null then
    raise sqlstate 'PT409' using message='current_matchday_required';
  end if;
  select * into day_row from public.matchdays
    where id=season_row.current_matchday_id and season_id=p_season_id for share;
  if not found or day_row.status='cancelled' then
    raise sqlstate 'PT409' using message='current_matchday_invalid';
  end if;
  -- A closed pointer is authoritative until the future advance transaction moves it.
  return next day_row;
end;
$$;

create or replace function public.api_is_store_banned(p_season_id uuid, p_trainer_id uuid, p_matchday_number integer)
returns boolean
language sql security invoker set search_path = '' as $$
  select exists (
    select 1 from public.penalties p join public.trial_cases c on c.id=p.trial_case_id
    where p.season_id=p_season_id and p.trainer_id=p_trainer_id
      and p.penalty_type='store_ban' and c.status='resolved'
      and c.accused_trainer_id=p_trainer_id and (c.season_id is null or c.season_id=p_season_id)
      and (p.start_matchday_number is null or p.end_matchday_number is null
           or p_matchday_number between p.start_matchday_number and p.end_matchday_number)
  );
$$;

revoke all on function public.api_resolve_current_matchday(uuid) from public, anon, authenticated;
revoke all on function public.api_is_store_banned(uuid, uuid, integer) from public, anon, authenticated;
grant execute on function public.api_resolve_current_matchday(uuid) to service_role;
grant execute on function public.api_is_store_banned(uuid, uuid, integer) to service_role;
commit;
