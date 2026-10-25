-- Phase23D. Local only: private artifact queue and least-privilege proof issuer.
-- No credentials, data backfill, entitlement consumption or public capability.
begin;
do $$ begin
 if not exists(select 1 from pg_roles where rolname='pokeapp_item_verifier') then
  create role pokeapp_item_verifier nologin nosuperuser nocreatedb nocreaterole noinherit nobypassrls;
 end if;
 if exists(select 1 from pg_roles where rolname='pokeapp_item_verifier'
   and (rolcanlogin or rolsuper or rolbypassrls or rolcreaterole))
   or pg_has_role('service_role','pokeapp_item_verifier','member') then
  raise exception 'unexpected_verifier_role'; end if;
end $$;
grant usage on schema public to pokeapp_item_verifier;

create table public.item_use_artifacts (
 authorization_id uuid primary key references public.item_use_authorizations(id),
 claim_id uuid not null,
 result_sha256 text not null check(result_sha256 ~ '^[a-f0-9]{64}$'),
 byte_size integer not null check(byte_size in (415232,483328,441856,445440)),
 storage_key text not null unique,
 status text not null check(status in ('UPLOADING','QUEUED','VERIFYING','VERIFIED','REJECTED')),
 source_url text, result_url text,
 lease_id uuid, lease_until timestamptz,
 error_code text,
 created_at timestamptz not null default clock_timestamp(),
 updated_at timestamptz not null default clock_timestamp()
);
alter table public.item_use_artifacts enable row level security;
alter table public.item_use_artifacts force row level security;
revoke all on public.item_use_artifacts from public,anon,authenticated,service_role,pokeapp_item_verifier;
comment on table public.item_use_artifacts is 'Private durable result manifest. Signed read URLs are temporary secrets; never return/log them. Retain original/result objects for operator reconciliation; no automatic deletion.';

-- Existing private bucket, new server-only namespace. Browser admins also denied.
do $$ begin if to_regclass('storage.objects') is not null then
 execute $p$create policy item_artifacts_no_browser on storage.objects as restrictive
  for all to anon,authenticated using(bucket_id<>'raw-saves' or split_part(name,'/',1)<>'item-use')
  with check(bucket_id<>'raw-saves' or split_part(name,'/',1)<>'item-use')$p$;
end if; end $$;

create function public.api_item_use_artifact(p_request jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare a public.item_use_authorizations; j public.item_use_artifacts; s public.save_files;
 aid uuid:=(p_request->>'authorization_id')::uuid; op text:=p_request->>'operation';
begin
 if op is null or op not in ('reserve','queue','get') then raise sqlstate 'PT422' using message='invalid_item_use_request'; end if;
 select * into a from public.item_use_authorizations where id=aid;
 if not found or a.trainer_id is distinct from (p_request->>'trainer_id')::uuid
  or a.season_id is distinct from (p_request->>'season_id')::uuid then
  raise sqlstate 'PT404' using message='item_use_not_found'; end if;
 perform 1 from public.trainers where id=a.trainer_id and globally_enabled for share;
 if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 perform 1 from public.seasons where id=a.season_id for no key update;
 perform 1 from public.season_players where season_id=a.season_id and trainer_id=a.trainer_id and status='active' for update;
 if not found then raise sqlstate 'PT403' using message='participant_inactive'; end if;
 select * into a from public.item_use_authorizations where id=aid for update;
 if a.claim_id is null or a.claim_id is distinct from (p_request->>'claim_id')::uuid then
  raise sqlstate 'PT409' using message='item_use_conflict'; end if;
 select * into j from public.item_use_artifacts where authorization_id=aid for update;
 if op='get' then
  if j.authorization_id is null then return jsonb_build_object('authorization_id',aid,'status','NOT_SUBMITTED'); end if;
 else
  if j.authorization_id is not null and op='reserve' and (j.result_sha256 is distinct from p_request->>'result_sha256'
     or j.byte_size is distinct from (p_request->>'byte_size')::int) then
   raise sqlstate 'PT409' using message='item_use_conflict'; end if;
  if j.status in ('VERIFIED','REJECTED') then
   return jsonb_build_object('authorization_id',aid,'status',j.status,'result_sha256',j.result_sha256); end if;
  if a.expires_at<=clock_timestamp() then raise sqlstate 'PT409' using message='item_use_expired'; end if;
  if a.effect_code<>'revive' or a.status not in ('PENDING_APPLICATION','RECOVERY_REQUIRED','BLOCKED_UNCERTAIN')
    or not exists(select 1 from public.purchases where id=a.purchase_id and status='pending') then
   raise sqlstate 'PT409' using message='item_use_unavailable'; end if;
  select * into s from public.save_files where id=a.save_file_id and sha256=a.save_sha256 and deleted_at is null and parser_status='parsed';
  if not found or not exists(select 1 from public.season_players where season_id=a.season_id and trainer_id=a.trainer_id and current_save_file_id=s.id) then
   raise sqlstate 'PT409' using message='save_context_changed'; end if;
  if op='reserve' and j.authorization_id is null then
   if p_request->>'result_sha256' is null or p_request->>'result_sha256' !~ '^[a-f0-9]{64}$'
    or p_request->>'result_sha256'=a.save_sha256 or p_request->>'byte_size' is null
    or (p_request->>'byte_size')::int not in (415232,483328,441856,445440) then
    raise sqlstate 'PT422' using message='invalid_item_use_request'; end if;
   insert into public.item_use_artifacts(authorization_id,claim_id,result_sha256,byte_size,storage_key,status)
    values(aid,a.claim_id,p_request->>'result_sha256',(p_request->>'byte_size')::int,
    'item-use/'||a.trainer_id||'/'||aid||'/'||a.claim_id||'/'||(p_request->>'result_sha256')||'.sav','UPLOADING') returning * into j;
  elsif op='queue' then
   if j.authorization_id is null or j.result_sha256 is distinct from p_request->>'result_sha256'
    or length(p_request->>'source_url') not between 1 and 8192 or length(p_request->>'result_url') not between 1 and 8192
    or p_request->>'source_url' is null or p_request->>'result_url' is null then
    raise sqlstate 'PT422' using message='invalid_item_use_request'; end if;
   -- A worker with a live lease is never displaced; repeated submission refreshes
   -- read capabilities only after its lease expires or before it starts.
   if j.status<>'VERIFYING' or j.lease_until<=clock_timestamp() then
    update public.item_use_artifacts set status='QUEUED',source_url=p_request->>'source_url',result_url=p_request->>'result_url',
     lease_id=null,lease_until=null,error_code=null,updated_at=clock_timestamp() where authorization_id=aid returning * into j;
   end if;
  end if;
 end if;
 return jsonb_build_object('authorization_id',aid,'status',case
  when a.expires_at<=clock_timestamp() and j.status not in ('VERIFIED','REJECTED') then 'EXPIRED'
  when (j.status='VERIFYING' and j.lease_until<=clock_timestamp())
    or (j.status='QUEUED' and j.updated_at<clock_timestamp()-interval '2 minutes') then 'RETRY_REQUIRED'
  else j.status end,
  'result_sha256',j.result_sha256,'byte_size',j.byte_size,'storage_key',j.storage_key,'source_key',s.storage_key,
  'expires_at',a.expires_at);
end $$;
revoke all on function public.api_item_use_artifact(jsonb) from public,anon,authenticated,pokeapp_item_verifier;
grant execute on function public.api_item_use_artifact(jsonb) to service_role;

-- Atomic snapshot used for independent parsing and compared again before proof.
create function public.item_verifier_context(aid uuid) returns jsonb
language sql security definer set search_path='' as $$
 select jsonb_build_object('authorization',to_jsonb(a),'entity',to_jsonb(e),'observation',to_jsonb(o),'save',to_jsonb(s),
  'current_save_id',p.current_save_file_id,'head_id',h.id,'trainer_enabled',t.globally_enabled,
  'participant_active',p.status='active','purchase_pending',buy.status='pending','purchase_effect',
  case when i.code='revivir_pokemon' then 'revive' else 'unsupported' end)
 from public.item_use_authorizations a
 join public.season_players p on p.season_id=a.season_id and p.trainer_id=a.trainer_id
 join public.trainers t on t.id=a.trainer_id
 join public.purchases buy on buy.id=a.purchase_id join public.shop_items i on i.id=buy.shop_item_id
 join public.pokemon_entities e on e.id=a.target_pokemon_entity_id
 join public.pokemon_observations o on o.revision_id=a.identity_revision_id and o.pokemon_entity_id=e.id
 join public.save_files s on s.id=a.save_file_id
 cross join lateral(select r.id from public.pokemon_identity_revisions r where r.season_id=a.season_id and r.trainer_id=a.trainer_id order by capture_sequence desc limit 1) h
 where a.id=aid;
$$;
revoke all on function public.item_verifier_context(uuid) from public,anon,authenticated,service_role,pokeapp_item_verifier;

create function public.item_verifier_job(p_request jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare j public.item_use_artifacts; a public.item_use_authorizations; c jsonb; proof jsonb;
 aid uuid:=(p_request->>'authorization_id')::uuid; token uuid:=(p_request->>'lease_id')::uuid;
 op text:=p_request->>'operation';
begin
 if token is null or op is null or op not in ('lease','context','finish','reject') then
  raise sqlstate 'PT422' using message='invalid_verifier_request'; end if;
 if op='lease' then
  select q.* into j from public.item_use_artifacts q join public.item_use_authorizations au on au.id=q.authorization_id
   where (q.status='QUEUED' or (q.status='VERIFYING' and q.lease_until<=clock_timestamp()))
    and au.expires_at>clock_timestamp() and q.source_url is not null and q.result_url is not null
   order by q.created_at for update of q skip locked limit 1;
  if not found then return null; end if;
  update public.item_use_artifacts set status='VERIFYING',lease_id=token,lease_until=clock_timestamp()+interval '3 minutes',updated_at=clock_timestamp()
   where authorization_id=j.authorization_id returning * into j;
  return to_jsonb(j);
 end if;
 select * into a from public.item_use_authorizations where id=aid;
 if not found then raise sqlstate 'PT404' using message='item_use_not_found'; end if;
 -- Same order as registration and completion; then artifact lease.
 perform 1 from public.trainers where id=a.trainer_id for share;
 perform 1 from public.seasons where id=a.season_id for no key update;
 perform 1 from public.season_players where season_id=a.season_id and trainer_id=a.trainer_id for update;
 select * into a from public.item_use_authorizations where id=aid for update;
 select * into j from public.item_use_artifacts where authorization_id=aid for update;
 if not found or j.lease_id is distinct from token then raise sqlstate 'PT409' using message='verifier_lease_conflict'; end if;
 if op='finish' and j.status='VERIFIED' then
  if exists(select 1 from public.item_use_verifications v where v.authorization_id=aid and (to_jsonb(v)-'verified_at')=p_request->'proof') then
   return jsonb_build_object('status','VERIFIED'); end if;
  raise sqlstate 'PT409' using message='verification_conflict'; end if;
 if j.status<>'VERIFYING' or j.lease_until<=clock_timestamp() then raise sqlstate 'PT409' using message='verifier_lease_conflict'; end if;
 if op='reject' then
  update public.item_use_artifacts set status='REJECTED',error_code='RESULT_NOT_VERIFIED',source_url=null,result_url=null,updated_at=clock_timestamp() where authorization_id=aid;
  return jsonb_build_object('status','REJECTED');
 end if;
 c:=public.item_verifier_context(aid);
 if op='context' then return c; end if;
 proof:=p_request->'proof';
 if c is null or c is distinct from p_request->'context' or a.expires_at<=clock_timestamp()
  or a.effect_code<>'revive' or a.status not in ('PENDING_APPLICATION','RECOVERY_REQUIRED','BLOCKED_UNCERTAIN')
  or c->'trainer_enabled'<>'true'::jsonb or c->'participant_active'<>'true'::jsonb or c->'purchase_pending'<>'true'::jsonb
  or c->>'current_save_id'<>a.save_file_id::text or c->>'head_id'<>a.identity_revision_id::text
  or proof is null or jsonb_typeof(proof)<>'object'
  or (select count(*) from jsonb_object_keys(proof))<>9
  or (proof->>'authorization_id')::uuid is distinct from aid
  or (proof->>'claim_id')::uuid is distinct from a.claim_id or a.claim_id is distinct from j.claim_id
  or proof->>'operation_id' is distinct from a.operation_id
  or proof->>'source_sha256' is distinct from a.save_sha256
  or proof->>'result_sha256' is distinct from j.result_sha256
  or (proof->>'target_pokemon_entity_id')::uuid is distinct from a.target_pokemon_entity_id
  or (proof->>'identity_revision_id')::uuid is distinct from a.identity_revision_id then
  raise sqlstate 'PT409' using message='verification_context_changed'; end if;
 insert into public.item_use_verifications(authorization_id,claim_id,operation_id,source_sha256,result_sha256,target_pokemon_entity_id,identity_revision_id,native_operation_id,plan_sha256)
 select authorization_id,claim_id,operation_id,source_sha256,result_sha256,target_pokemon_entity_id,identity_revision_id,native_operation_id,plan_sha256
 from jsonb_populate_record(null::public.item_use_verifications,proof)
 on conflict(authorization_id) do nothing;
 if not exists(select 1 from public.item_use_verifications v where v.authorization_id=aid and (to_jsonb(v)-'verified_at')=proof) then
  raise sqlstate 'PT409' using message='verification_conflict'; end if;
 update public.item_use_artifacts set status='VERIFIED',source_url=null,result_url=null,error_code=null,updated_at=clock_timestamp() where authorization_id=aid;
 return jsonb_build_object('status','VERIFIED');
end $$;
revoke all on function public.item_verifier_job(jsonb) from public,anon,authenticated,service_role;
grant execute on function public.item_verifier_job(jsonb) to pokeapp_item_verifier;
commit;
