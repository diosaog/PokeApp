-- SEC-PIN-01. No passwords, PINs or peppers. No remote activation implied.
begin;
create table public.account_credential_policy (
 singleton boolean primary key default true check(singleton),
 legacy_deadline timestamptz not null,
 activated_at timestamptz not null default clock_timestamp()
);
-- Intentionally empty: an operator must choose the bounded window at rollout.
create table public.account_credentials (
 trainer_id uuid primary key references public.trainers(id),
 version integer not null check(version in (1,2)),
 reset_required boolean not null default false
);
-- These are bindings issued by the existing v1-only backend, not new identities.
insert into public.account_credentials(trainer_id,version)
 select id,1 from public.trainers where auth_user_id is not null;
create table public.account_renewal_grants (
 token_hash text primary key check(token_hash ~ '^[a-f0-9]{64}$'),
 trainer_id uuid not null references public.trainers(id), auth_user_id uuid not null,
 verification_reference text not null check(length(btrim(verification_reference)) between 1 and 200),
 expires_at timestamptz not null, operation_id uuid unique,
 created_at timestamptz not null default clock_timestamp()
);
alter table public.account_credentials enable row level security;
alter table public.account_credential_policy enable row level security;
alter table public.account_renewal_grants enable row level security;
revoke all on public.account_credentials,public.account_credential_policy,public.account_renewal_grants from public,anon,authenticated;
grant select,insert,update,delete on public.account_credentials,public.account_credential_policy,public.account_renewal_grants to service_role;

alter table public.account_registrations add column credential_version integer not null default 1 check(credential_version in(1,2));
alter table public.account_registrations add column fingerprint_version integer not null default 1 check(fingerprint_version in(1,2));
alter table public.account_registrations add column expires_at timestamptz;
alter table public.account_registrations add column request_context jsonb;
alter table public.account_pin_changes add column credential_version integer not null default 1 check(credential_version in(1,2));
alter table public.account_pin_changes add column fingerprint_version integer not null default 1 check(fingerprint_version in(1,2));
alter table public.account_pin_changes add column expires_at timestamptz;
alter table public.account_pin_changes add column auth_user_id uuid;
alter table public.account_pin_changes add column grant_hash text references public.account_renewal_grants(token_hash);

create function public.sec_pin_monotonic() returns trigger language plpgsql
security invoker set search_path=public,pg_catalog as $$ begin
 if new.trainer_id<>old.trainer_id or new.version<old.version then raise exception 'account_conflict'; end if;
 return new;
end $$;
create trigger credential_no_downgrade before update on public.account_credentials
 for each row execute function public.sec_pin_monotonic();
create function public.sec_pin_policy_monotonic() returns trigger language plpgsql
security invoker set search_path=public,pg_catalog as $$ begin
 if new.legacy_deadline>old.legacy_deadline or new.activated_at<>old.activated_at then raise exception 'account_conflict'; end if;
 return new;
end $$;
create trigger credential_policy_no_extension before update on public.account_credential_policy
 for each row execute function public.sec_pin_policy_monotonic();

create function public.sec_pin_context(p_trainer uuid) returns jsonb
language sql stable security invoker set search_path=public,pg_catalog as $$
 select jsonb_build_object('version',c.version,'reset_required',c.reset_required or
   (c.version=1 and clock_timestamp()>=p.legacy_deadline), 'legacy_deadline',p.legacy_deadline,
   'auth_user_id',t.auth_user_id,'globally_enabled',t.globally_enabled)
 from public.account_credentials c join public.trainers t on t.id=c.trainer_id
 cross join public.account_credential_policy p where c.trainer_id=p_trainer
$$;
create or replace function public.account_session_allowed(p_auth uuid,p_iat bigint) returns boolean
language sql stable security definer set search_path=public,pg_catalog as $$
 select exists(select 1 from public.trainers t join public.account_credentials c on c.trainer_id=t.id
 cross join public.account_credential_policy p left join public.account_session_guards g on g.trainer_id=t.id
 where t.auth_user_id=p_auth and t.globally_enabled and not c.reset_required
 and (c.version=2 or clock_timestamp()<p.legacy_deadline)
 and not coalesce(g.blocked,false) and coalesce(p_iat,0)>=coalesce(g.minimum_iat,0))
$$;

-- Counters keep one stable v2 key. Count old active attempts as well throughout
-- transition. Removing v1 before every possible old 48h window expires fails closed.
create function public.sec_pin_rate(p_key text,p_old text,p_limit integer,p_seconds integer)
returns boolean language plpgsql security invoker set search_path=public,pg_catalog as $$
declare p public.account_credential_policy; old_count integer:=0; n integer; allowed boolean;
begin
 select * into strict p from public.account_credential_policy;
 if p_seconds not between 1 and 172800 then raise exception 'account_forbidden'; end if;
 if p_old is null and clock_timestamp()<p.activated_at+interval '2 days'
   and exists(select 1 from public.account_rate_windows where started_at<=p.activated_at
     and started_at>=clock_timestamp()-interval '2 days') then raise exception 'account_transition_required'; end if;
 allowed:=public.account_rate_check(p_key,p_limit,p_seconds);
 select attempts into n from public.account_rate_windows where key_hash=p_key;
 select attempts into old_count from public.account_rate_windows where key_hash=p_old
   and started_at>=clock_timestamp()-make_interval(secs=>p_seconds);
 return allowed and n+coalesce(old_count,0)<=p_limit;
end $$;

create function public.sec_pin_registration_prepare(p_operation uuid,p_name text,p_slug text,p_hash text,p_expires timestamptz) returns jsonb
language plpgsql security invoker set search_path=public,pg_catalog as $$
declare r public.account_registrations; t uuid:=gen_random_uuid(); a uuid:=gen_random_uuid();
begin
 perform 1 from public.account_credential_policy;
 if not found then raise exception 'account_policy_required'; end if;
 if p_expires<=clock_timestamp() or p_expires>clock_timestamp()+interval '25 hours'
   or p_hash !~ '^[a-f0-9]{64}$' or p_hash=repeat('0',64) then raise exception 'account_conflict'; end if;
 perform pg_advisory_xact_lock(hashtextextended('account-register:'||p_operation::text,0));
 select * into r from public.account_registrations where operation_id=p_operation for update;
 if found then
   if r.credential_version<>2 or r.fingerprint_version<>2 or r.expires_at<=clock_timestamp()
     or r.request_context<>jsonb_build_array(p_name,p_slug) then raise exception 'account_reconciliation_required'; end if;
   return to_jsonb(r);
 end if;
 if length(p_name) not between 1 and 48 or p_slug !~ '^[a-z0-9][a-z0-9_-]{0,47}$' then raise exception 'account_forbidden'; end if;
 begin
 insert into public.trainers(id,display_name,slug,globally_enabled,is_admin) values(t,p_name,p_slug,false,false);
 exception when unique_violation then raise exception 'account_conflict'; end;
 insert into public.account_credentials values(t,2,true);
 insert into public.account_registrations(operation_id,request_hash,trainer_id,auth_user_id,credential_version,fingerprint_version,expires_at,request_context)
 values(p_operation,p_hash,t,a,2,2,p_expires,jsonb_build_array(p_name,p_slug)) returning * into r;
 return to_jsonb(r);
end $$;
create function public.sec_pin_bind(p_kind text,p_operation uuid,p_hash text) returns void
language plpgsql security invoker set search_path=public,pg_catalog as $$
declare n integer;
begin
 if p_hash !~ '^[a-f0-9]{64}$' or p_hash=repeat('0',64) then raise exception 'account_conflict'; end if;
 if p_kind='registration' then
   update public.account_registrations set request_hash=p_hash where operation_id=p_operation
     and fingerprint_version=2 and credential_version=2 and expires_at>clock_timestamp()
     and request_hash=p_hash;
 elsif p_kind='pin' then
   update public.account_pin_changes set request_hash=p_hash where operation_id=p_operation
     and fingerprint_version=2 and credential_version=2 and expires_at>clock_timestamp()
     and request_hash=p_hash;
 else raise exception 'account_conflict'; end if;
 get diagnostics n=row_count;
 if n<>1 then raise exception 'account_conflict'; end if;
 if p_kind='pin' then
   insert into public.account_session_guards(trainer_id,blocked)
     select target_id,true from public.account_pin_changes where operation_id=p_operation and stage<>'complete'
     on conflict(trainer_id) do update set blocked=true;
 end if;
end $$;
create function public.sec_pin_registration_complete(p_operation uuid,p_hash text,p_auth uuid) returns uuid
language plpgsql security invoker set search_path=public,pg_catalog as $$
declare r public.account_registrations; t public.trainers;
begin
 select * into strict r from public.account_registrations where operation_id=p_operation for update;
 if r.request_hash<>p_hash or r.auth_user_id<>p_auth or r.credential_version<>2 or r.expires_at<=clock_timestamp() then raise exception 'account_conflict'; end if;
 select * into strict t from public.trainers where id=r.trainer_id for update;
 if r.status='complete' then
   if t.auth_user_id is distinct from p_auth then raise exception 'account_conflict'; end if;
   return t.id;
 end if;
 if t.auth_user_id is not null or t.globally_enabled or t.is_admin then raise exception 'account_conflict'; end if;
 update public.trainers set auth_user_id=p_auth,globally_enabled=true where id=t.id;
 update public.account_credentials set version=2,reset_required=false where trainer_id=t.id;
 update public.account_registrations set status='complete' where operation_id=p_operation;
 return t.id;
end $$;

-- No HTTP route issues grants. This is an operator-only action AFTER independent
-- identity verification; the reference records that external decision, not a PIN.
create function public.sec_pin_authorize_renewal(p_hash text,p_target uuid,p_auth uuid,p_reference text,p_expires timestamptz)
returns void language plpgsql security invoker set search_path=public,pg_catalog as $$
begin
 perform 1 from public.trainers where id=p_target and auth_user_id=p_auth and globally_enabled for update;
 if not found or p_expires<=clock_timestamp() or p_expires>clock_timestamp()+interval '24 hours'
   or length(btrim(p_reference)) not between 1 and 200 then raise exception 'account_forbidden'; end if;
 insert into public.account_renewal_grants(token_hash,trainer_id,auth_user_id,verification_reference,expires_at)
 values(p_hash,p_target,p_auth,p_reference,p_expires);
end $$;
create function public.sec_pin_prepare(p_actor uuid,p_target uuid,p_operation uuid,p_grant text,p_hash text,p_expires timestamptz) returns jsonb
language plpgsql security invoker set search_path=public,pg_catalog as $$
declare r public.account_pin_changes; t public.trainers; g public.account_renewal_grants; c public.account_credentials;
begin
 perform 1 from public.account_credential_policy;
 if not found then raise exception 'account_policy_required'; end if;
 if p_expires<=clock_timestamp() or p_expires>clock_timestamp()+interval '25 hours'
   or p_hash !~ '^[a-f0-9]{64}$' or p_hash=repeat('0',64) then raise exception 'account_conflict'; end if;
 select * into strict t from public.trainers where id=p_target for update;
 if not t.globally_enabled or t.auth_user_id is null then raise exception 'account_forbidden'; end if;
 if p_actor<>p_target and not exists(select 1 from public.trainers
   where id=p_actor and globally_enabled and is_admin and auth_user_id is not null)
   then raise exception 'account_forbidden'; end if;
 select * into r from public.account_pin_changes where operation_id=p_operation;
 if found then
   if r.target_id<>p_target or r.actor_id<>p_actor or r.grant_hash is distinct from p_grant
     or r.credential_version<>2 or r.expires_at<=clock_timestamp() then raise exception 'account_conflict'; end if;
   return to_jsonb(r);
 end if;
 select * into c from public.account_credentials where trainer_id=p_target;
 if p_grant is null then
   if p_actor<>p_target or c.version is distinct from 2 or c.reset_required then raise exception 'account_renewal_required'; end if;
   if exists(select 1 from public.account_session_guards where trainer_id=p_target and blocked) then raise exception 'account_forbidden'; end if;
 else
   select * into strict g from public.account_renewal_grants where token_hash=p_grant for update;
   if g.trainer_id<>p_target or g.auth_user_id<>t.auth_user_id or g.expires_at<=clock_timestamp()
     or g.operation_id is not null or p_expires>g.expires_at then raise exception 'account_forbidden'; end if;
   update public.account_renewal_grants set operation_id=p_operation where token_hash=p_grant;
 end if;
 -- An unresolved older attempt is NOT overwritten or silently abandoned.
 insert into public.account_pin_changes(operation_id,actor_id,target_id,request_hash,stage,
   credential_version,fingerprint_version,expires_at,auth_user_id,grant_hash)
 values(p_operation,p_actor,p_target,p_hash,'prepared',2,2,p_expires,t.auth_user_id,p_grant) returning * into r;
 insert into public.account_session_guards(trainer_id,blocked) values(p_target,true)
   on conflict(trainer_id) do update set blocked=true;
 return to_jsonb(r);
exception when unique_violation then raise exception 'account_reconciliation_required';
end $$;
create function public.sec_pin_claim(p_operation uuid,p_hash text) returns boolean
language plpgsql security invoker set search_path=public,pg_catalog as $$
begin
 update public.account_pin_changes c set stage='updating' from public.trainers t
 where c.operation_id=p_operation and c.request_hash=p_hash and c.stage='prepared'
 and c.credential_version=2 and c.expires_at>clock_timestamp() and t.id=c.target_id
 and t.auth_user_id=c.auth_user_id and t.globally_enabled;
 return found;
end $$;
create function public.sec_pin_finish(p_operation uuid,p_hash text) returns jsonb
language plpgsql security invoker set search_path=public,pg_catalog as $$
declare c public.account_pin_changes; t public.trainers;
begin
 -- Same target-first lock order as prepare/admin status.
 select * into strict c from public.account_pin_changes where operation_id=p_operation;
 select * into strict t from public.trainers where id=c.target_id for update;
 select * into strict c from public.account_pin_changes where operation_id=p_operation for update;
 if c.request_hash<>p_hash or c.stage='prepared' or c.credential_version<>2 or c.expires_at<=clock_timestamp()
 or not t.globally_enabled or t.auth_user_id is distinct from c.auth_user_id then raise exception 'account_conflict'; end if;
 if c.stage<>'complete' then
   insert into public.account_credentials values(t.id,2,false)
     on conflict(trainer_id) do update set version=2,reset_required=false;
   update public.account_session_guards set blocked=false,
     minimum_iat=greatest(minimum_iat,floor(extract(epoch from clock_timestamp()))::bigint+1) where trainer_id=t.id;
   update public.account_pin_changes set stage='complete' where operation_id=p_operation;
 end if;
 return jsonb_build_object('status','changed','sign_in_required',true);
end $$;

-- Old APIs must not originate unversioned credentials or replay expired intents.
create or replace function public.account_registration_reserve(p_operation uuid,p_hash text,p_name text,p_slug text)
returns jsonb language plpgsql security invoker set search_path=public,pg_catalog as $$ begin raise exception 'account_legacy_intent_retired'; end $$;
create or replace function public.account_registration_complete(p_operation uuid,p_hash text,p_auth uuid)
returns uuid language plpgsql security invoker set search_path=public,pg_catalog as $$ begin raise exception 'account_legacy_intent_retired'; end $$;
create or replace function public.account_pin_begin(p_actor uuid,p_target uuid,p_operation uuid,p_hash text)
returns jsonb language plpgsql security invoker set search_path=public,pg_catalog as $$ begin raise exception 'account_legacy_intent_retired'; end $$;
create or replace function public.account_pin_claim(p_operation uuid,p_hash text)
returns boolean language plpgsql security invoker set search_path=public,pg_catalog as $$ begin raise exception 'account_legacy_intent_retired'; end $$;
create or replace function public.account_pin_finish(p_operation uuid,p_hash text)
returns jsonb language plpgsql security invoker set search_path=public,pg_catalog as $$ begin raise exception 'account_legacy_intent_retired'; end $$;
do $$ declare f regprocedure; begin
 for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname='public' and p.proname like 'sec_pin_%' loop
   execute format('revoke all on function %s from public,anon,authenticated',f);
   execute format('grant execute on function %s to service_role',f);
 end loop;
end $$;
commit;
