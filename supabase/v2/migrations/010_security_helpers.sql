-- PokeApp Supabase V2 security layer.
-- 010_security_helpers: auth identity, admin flag and safe RLS helpers.

begin;

alter table public.trainers
  add column is_admin boolean not null default false;

comment on column public.trainers.is_admin is
  'Explicit administrative identity for V2 RLS. Do not infer admin from display_name or slug.';

create or replace function public.current_auth_uid()
returns uuid
language plpgsql
stable
set search_path = ''
as $$
declare
  auth_uid uuid;
  raw_sub text;
begin
  begin
    execute 'select auth.uid()' into auth_uid;
  exception
    when invalid_schema_name or undefined_function then
      auth_uid := null;
  end;

  if auth_uid is not null then
    return auth_uid;
  end if;

  raw_sub := nullif(pg_catalog.current_setting('request.jwt.claim.sub', true), '');
  if raw_sub is null then
    return null;
  end if;

  begin
    return raw_sub::uuid;
  exception
    when invalid_text_representation then
      return null;
  end;
end;
$$;

comment on function public.current_auth_uid() is
  'Returns Supabase auth.uid(). Plain PostgreSQL validation falls back to request.jwt.claim.sub.';

create or replace function public.current_trainer_id()
returns uuid
language sql
stable
security definer
set search_path = public, pg_catalog
as $$
  select t.id
  from public.trainers as t
  where t.auth_user_id = public.current_auth_uid()
    and t.globally_enabled = true
  limit 1
$$;

comment on function public.current_trainer_id() is
  'Resolves the authenticated Supabase user to the enabled PokeApp trainer id.';

create or replace function public.is_current_user_admin()
returns boolean
language sql
stable
security definer
set search_path = public, pg_catalog
as $$
  select coalesce(
    (
      select true
      from public.trainers as t
      where t.auth_user_id = public.current_auth_uid()
        and t.globally_enabled = true
        and t.is_admin = true
      limit 1
    ),
    false
  )
$$;

comment on function public.is_current_user_admin() is
  'Checks the explicit trainers.is_admin flag for the authenticated user.';

create or replace function public.current_user_owns_trainer(p_trainer_id uuid)
returns boolean
language sql
stable
security definer
set search_path = public, pg_catalog
as $$
  select p_trainer_id is not null
    and p_trainer_id = public.current_trainer_id()
$$;

comment on function public.current_user_owns_trainer(uuid) is
  'Small policy helper for trainer-owned rows.';

revoke all on function public.current_auth_uid() from public;
revoke all on function public.current_trainer_id() from public;
revoke all on function public.is_current_user_admin() from public;
revoke all on function public.current_user_owns_trainer(uuid) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    grant execute on function public.current_auth_uid() to authenticated;
    grant execute on function public.current_trainer_id() to authenticated;
    grant execute on function public.is_current_user_admin() to authenticated;
    grant execute on function public.current_user_owns_trainer(uuid) to authenticated;
  end if;

  if exists (select 1 from pg_roles where rolname = 'service_role') then
    grant execute on function public.current_auth_uid() to service_role;
    grant execute on function public.current_trainer_id() to service_role;
    grant execute on function public.is_current_user_admin() to service_role;
    grant execute on function public.current_user_owns_trainer(uuid) to service_role;
  end if;
end;
$$;

commit;
