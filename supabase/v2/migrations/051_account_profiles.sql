begin;
create function public.account_name_key(p_name text) returns text
language sql immutable strict set search_path=pg_catalog as $$
 select lower(regexp_replace(regexp_replace(normalize(btrim(p_name),NFKD),U&'[\0300-\036f]','','g'),'[[:space:]]+','-','g'))
$$;
-- A legacy display name may differ from its login slug; both namespaces matter.
-- Fail migration rather than silently merge any pre-existing collision.
create unique index trainers_unique_display_identity on public.trainers(public.account_name_key(display_name));
revoke all on function public.account_name_key(text) from public,anon;
grant execute on function public.account_name_key(text) to authenticated,service_role;
alter table public.trainers add column profile_revision bigint not null default 0;
alter table public.trainers add column photo_key text;
alter table public.trainers add constraint trainers_photo_key_chk check
 (photo_key is null or photo_key ~ ('^portraits/'||id::text||'/[a-f0-9]{64}\.jpg$'));
create table public.account_commands (
 operation_id uuid primary key, actor_id uuid not null references public.trainers(id),
 target_id uuid not null references public.trainers(id), kind text not null,
 request_hash text not null check(request_hash ~ '^[a-f0-9]{64}$'),
 result jsonb not null, created_at timestamptz not null default now()
);
create table public.account_pin_changes (
 operation_id uuid primary key, actor_id uuid not null references public.trainers(id),
 target_id uuid not null references public.trainers(id),
 request_hash text not null check(request_hash ~ '^[a-f0-9]{64}$'),
 stage text not null check(stage in ('prepared','updating','complete')),
 created_at timestamptz not null default now()
);
create unique index account_pin_one_pending on public.account_pin_changes(target_id) where stage<>'complete';
create table public.account_session_guards (
 trainer_id uuid primary key references public.trainers(id),
 blocked boolean not null default false, minimum_iat bigint not null default 0
);
alter table public.account_commands enable row level security;
alter table public.account_pin_changes enable row level security;
alter table public.account_session_guards enable row level security;
revoke all on public.account_commands,public.account_pin_changes,public.account_session_guards from public,anon,authenticated;
grant select,insert,update,delete on public.account_commands,public.account_pin_changes,public.account_session_guards to service_role;

create function public.account_profile_update(p_actor uuid,p_operation uuid,p_hash text,
 p_revision bigint,p_name text,p_slug text,p_photo text) returns jsonb
language plpgsql security invoker set search_path=public,pg_catalog as $$
declare t public.trainers; c public.account_commands; result jsonb;
begin
 select * into strict t from public.trainers where id=p_actor for update;
 if not t.globally_enabled or t.auth_user_id is null then raise exception 'account_forbidden'; end if;
 select * into c from public.account_commands where operation_id=p_operation;
 if found then
   if c.actor_id<>p_actor or c.kind<>'profile' or c.request_hash<>p_hash then raise exception 'account_conflict'; end if;
   return c.result;
 end if;
 if t.profile_revision<>p_revision then raise exception 'account_stale'; end if;
 if (p_name is null)=(p_photo is null) then raise exception 'invalid_account_update'; end if;
 if p_name is not null and (length(p_name) not between 1 and 48 or p_slug is null
   or p_slug !~ '^[a-z0-9][a-z0-9_-]{0,47}$') then raise exception 'invalid_account_name'; end if;
 begin
 update public.trainers set display_name=coalesce(p_name,display_name),slug=coalesce(p_slug,slug),
   photo_key=coalesce(p_photo,photo_key),profile_revision=profile_revision+1 where id=p_actor
   returning * into t;
 exception when unique_violation then raise exception 'account_conflict'; end;
 result=jsonb_build_object('trainer_id',t.id,'revision',t.profile_revision);
 insert into public.account_commands values(p_operation,p_actor,p_actor,'profile',p_hash,result,now());
 return result;
end $$;

create function public.account_pin_begin(p_actor uuid,p_target uuid,p_operation uuid,p_hash text)
returns jsonb language plpgsql security invoker set search_path=public,pg_catalog as $$
declare a public.trainers; t public.trainers; c public.account_pin_changes;
begin
 perform 1 from public.trainers where id in(p_actor,p_target) order by id for update;
 select * into strict a from public.trainers where id=p_actor;
 select * into strict t from public.trainers where id=p_target;
 if not a.globally_enabled or a.auth_user_id is null or t.auth_user_id is null or not t.globally_enabled
   or (p_actor<>p_target and not a.is_admin) then raise exception 'account_forbidden'; end if;
 select * into c from public.account_pin_changes where operation_id=p_operation;
 if found then
   if c.actor_id<>p_actor or c.target_id<>p_target or c.request_hash<>p_hash then raise exception 'account_conflict'; end if;
   return to_jsonb(c);
 end if;
 insert into public.account_pin_changes values(p_operation,p_actor,p_target,p_hash,'prepared',now()) returning * into c;
 insert into public.account_session_guards(trainer_id,blocked) values(p_target,true)
   on conflict(trainer_id) do update set blocked=true;
 return to_jsonb(c);
end $$;

create function public.account_pin_claim(p_operation uuid,p_hash text) returns boolean
language plpgsql security invoker set search_path=public,pg_catalog as $$
begin
 update public.account_pin_changes set stage='updating'
 where operation_id=p_operation and request_hash=p_hash and stage='prepared';
 return found;
end $$;

create function public.account_pin_finish(p_operation uuid,p_hash text) returns jsonb
language plpgsql security invoker set search_path=public,pg_catalog as $$
declare c public.account_pin_changes;
begin
 select * into strict c from public.account_pin_changes where operation_id=p_operation for update;
 if c.request_hash<>p_hash or c.stage='prepared' then raise exception 'account_conflict'; end if;
 if c.stage<>'complete' then
   update public.account_session_guards set blocked=false,
     minimum_iat=floor(extract(epoch from clock_timestamp()))::bigint+1 where trainer_id=c.target_id;
   update public.account_pin_changes set stage='complete' where operation_id=p_operation;
 end if;
 return jsonb_build_object('status','changed','sign_in_required',true);
end $$;

create function public.account_session_allowed(p_auth uuid,p_iat bigint) returns boolean
language sql stable security definer set search_path=public,pg_catalog as $$
 select not exists(select 1 from public.account_session_guards g join public.trainers t on t.id=g.trainer_id
   where t.auth_user_id=p_auth and (g.blocked or coalesce(p_iat,0)<g.minimum_iat))
$$;
-- Same identity helper; add immediate revocation for the affected account only.
create or replace function public.current_auth_uid() returns uuid
language plpgsql stable set search_path='' as $$
declare uid uuid; claims jsonb; iat bigint;
begin
 begin execute 'select auth.uid()' into uid;
 exception when invalid_schema_name or undefined_function then uid:=null; end;
 if uid is null then uid:=nullif(current_setting('request.jwt.claim.sub',true),'')::uuid; end if;
 claims:=nullif(current_setting('request.jwt.claims',true),'')::jsonb;
 iat:=coalesce((claims->>'iat')::bigint,0);
 if uid is not null and public.account_session_allowed(uid,iat) then return uid; end if;
 return null;
exception when invalid_text_representation or numeric_value_out_of_range then return null;
end $$;

revoke all on function public.account_profile_update(uuid,uuid,text,bigint,text,text,text),
 public.account_pin_begin(uuid,uuid,uuid,text),public.account_pin_claim(uuid,text),
 public.account_pin_finish(uuid,text),public.account_session_allowed(uuid,bigint) from public,anon,authenticated;
grant execute on function public.account_profile_update(uuid,uuid,text,bigint,text,text,text),
 public.account_pin_begin(uuid,uuid,uuid,text),public.account_pin_claim(uuid,text),
 public.account_pin_finish(uuid,text),public.account_session_allowed(uuid,bigint) to service_role;
-- Identity helpers must be callable by RLS, but the session guard leaks no rows.
grant execute on function public.account_session_allowed(uuid,bigint) to authenticated;

do $$ begin
 if to_regclass('storage.buckets') is not null then
   insert into storage.buckets(id,name,public,file_size_limit,allowed_mime_types)
   values('trainer-photos','trainer-photos',false,5242880,array['image/jpeg'])
   on conflict(id) do nothing;
 end if;
 if to_regclass('storage.objects') is not null then
   -- RESTRICTIVE denies also defeat a future broad permissive browser policy.
   execute 'create policy trainer_photos_no_browser_insert on storage.objects as restrictive for insert to authenticated with check (bucket_id <> ''trainer-photos'')';
   execute 'create policy trainer_photos_no_browser_update on storage.objects as restrictive for update to authenticated using (bucket_id <> ''trainer-photos'') with check (bucket_id <> ''trainer-photos'')';
   execute 'create policy trainer_photos_no_browser_delete on storage.objects as restrictive for delete to authenticated using (bucket_id <> ''trainer-photos'')';
 end if;
end $$;
commit;
