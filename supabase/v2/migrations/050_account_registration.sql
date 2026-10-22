-- Local-first account provisioning. Never enrolls a season or rewrites history.
begin;

create table public.account_registrations (
  operation_id uuid primary key,
  request_hash text not null check (request_hash ~ '^[a-f0-9]{64}$'),
  trainer_id uuid not null unique references public.trainers(id),
  auth_user_id uuid not null unique,
  status text not null default 'pending' check (status in ('pending','complete')),
  created_at timestamptz not null default now()
);
create table public.account_rate_windows (
  key_hash text primary key check (key_hash ~ '^[a-f0-9]{64}$'),
  started_at timestamptz not null,
  attempts integer not null check (attempts > 0)
);
alter table public.account_registrations enable row level security;
alter table public.account_rate_windows enable row level security;
revoke all on public.account_registrations, public.account_rate_windows from public, anon, authenticated;
grant select, insert, update, delete on public.account_registrations, public.account_rate_windows to service_role;
-- Accounts can only be provisioned/edited through the verified backend.
revoke insert, update, delete, truncate, references, trigger on public.trainers from anon, authenticated;
revoke insert, update, delete on public.public_trainers, public.current_trainer_profile from anon, authenticated;

create function public.account_rate_check(p_key text, p_limit integer, p_seconds integer)
returns boolean language plpgsql security invoker set search_path = public, pg_catalog as $$
declare v_count integer;
begin
  if p_limit < 1 or p_seconds < 1 then raise exception 'invalid_rate_policy'; end if;
  insert into public.account_rate_windows(key_hash,started_at,attempts)
  values(p_key,clock_timestamp(),1)
  on conflict(key_hash) do update set
    started_at=case when account_rate_windows.started_at < clock_timestamp()-make_interval(secs=>p_seconds)
      then clock_timestamp() else account_rate_windows.started_at end,
    attempts=case when account_rate_windows.started_at < clock_timestamp()-make_interval(secs=>p_seconds)
      then 1 else least(account_rate_windows.attempts+1,p_limit+1) end
  returning attempts into v_count;
  delete from public.account_rate_windows where started_at < clock_timestamp()-interval '2 days';
  return v_count <= p_limit;
end $$;

create function public.account_registration_reserve(p_operation uuid,p_hash text,p_name text,p_slug text)
returns jsonb language plpgsql security invoker set search_path = public, pg_catalog as $$
declare r public.account_registrations; t uuid; a uuid;
begin
  perform pg_advisory_xact_lock(hashtextextended('account-register:'||p_operation::text,0));
  select * into r from public.account_registrations where operation_id=p_operation for update;
  if found then
    if r.request_hash <> p_hash then raise exception 'account_conflict'; end if;
    return to_jsonb(r);
  end if;
  if length(p_name) not between 1 and 48 or p_name<>btrim(p_name)
    or p_slug !~ '^[a-z0-9][a-z0-9_-]{0,47}$' then raise exception 'invalid_account_name'; end if;
  t:=gen_random_uuid(); a:=gen_random_uuid();
  begin
    insert into public.trainers(id,display_name,slug,globally_enabled,is_admin)
    values(t,p_name,p_slug,false,false);
  exception when unique_violation then raise exception 'account_conflict'; end;
  insert into public.account_registrations(operation_id,request_hash,trainer_id,auth_user_id)
  values(p_operation,p_hash,t,a) returning * into r;
  return to_jsonb(r);
end $$;

create function public.account_registration_complete(p_operation uuid,p_hash text,p_auth uuid)
returns uuid language plpgsql security invoker set search_path = public, pg_catalog as $$
declare r public.account_registrations; t public.trainers;
begin
  select * into strict r from public.account_registrations where operation_id=p_operation for update;
  if r.request_hash<>p_hash or r.auth_user_id<>p_auth then raise exception 'account_conflict'; end if;
  select * into strict t from public.trainers where id=r.trainer_id for update;
  if r.status='complete' then
    if t.auth_user_id is distinct from p_auth then raise exception 'account_identity_mismatch'; end if;
    return t.id; -- Never re-enable an account on replay.
  end if;
  if t.auth_user_id is not null or t.globally_enabled or t.is_admin then
    raise exception 'account_identity_mismatch';
  end if;
  update public.trainers set auth_user_id=p_auth,globally_enabled=true where id=t.id;
  update public.account_registrations set status='complete' where operation_id=p_operation;
  return t.id;
end $$;

revoke all on function public.account_rate_check(text,integer,integer),
  public.account_registration_reserve(uuid,text,text,text),
  public.account_registration_complete(uuid,text,uuid) from public,anon,authenticated;
grant execute on function public.account_rate_check(text,integer,integer),
  public.account_registration_reserve(uuid,text,text,text),
  public.account_registration_complete(uuid,text,uuid) to service_role;
commit;
