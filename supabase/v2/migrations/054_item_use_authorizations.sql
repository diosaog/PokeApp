-- Phase 23: explicit physical item-use authorization.
-- UNDEPLOYED: 23B hardens the original local draft. Client claims are not proof.
-- No runtime producer of trusted verification exists yet; production stays OFF.
begin;

create table public.item_use_authorizations (
  id uuid primary key default gen_random_uuid(),
  operation_id text not null unique check (length(operation_id) between 1 and 128 and operation_id ~ '^[!-~]+$'),
  idempotency_key text not null unique check (length(idempotency_key) between 1 and 128 and idempotency_key ~ '^[!-~]+$'),
  purchase_id uuid not null unique references public.purchases(id),
  season_id uuid not null,
  trainer_id uuid not null,
  target_pokemon_entity_id uuid not null,
  save_file_id uuid not null references public.save_files(id),
  save_sha256 text not null check (save_sha256 ~ '^[a-f0-9]{64}$'),
  identity_revision_id uuid not null references public.pokemon_identity_revisions(id),
  claim_id uuid,
  expires_at timestamptz not null default (clock_timestamp()+interval '15 minutes'),
  effect_code text not null check (effect_code in ('revive','steal')),
  status text not null default 'PREPARED' check (status in
    ('PREPARED','PENDING_APPLICATION','APPLIED_VERIFIED','FAILED_RECOVERABLE','RECOVERY_REQUIRED','BLOCKED_UNCERTAIN')),
  observed_sha256 text check (observed_sha256 is null or observed_sha256 ~ '^[a-f0-9]{64}$'),
  error_code text check (error_code is null or error_code ~ '^[A-Z0-9_]{1,64}$'),
  receipt jsonb check (receipt is null or jsonb_typeof(receipt)='object'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  applied_at timestamptz,
  foreign key (season_id,trainer_id) references public.season_players(season_id,trainer_id),
  foreign key (save_file_id,season_id,trainer_id) references public.save_files(id,season_id,trainer_id),
  foreign key (target_pokemon_entity_id,season_id) references public.pokemon_entities(id,season_id)
);
create index item_use_auth_trainer_status_idx on public.item_use_authorizations(trainer_id,status,updated_at);
comment on table public.item_use_authorizations is
  'Backend-only physical item authorization. PREPARED does not consume the purchase; APPLIED_VERIFIED is issued only after native readback.';

alter table public.item_use_authorizations enable row level security;
alter table public.item_use_authorizations force row level security;
revoke all on public.item_use_authorizations from public,anon,authenticated,service_role;
grant select,insert,update on public.item_use_authorizations to service_role;

-- Evidence may only be recorded by a trusted private verifier, NEVER by a
-- browser, Launcher DTO, or API service_role. The disposable harness uses
-- postgres after independently checking its local engine/native result.
-- There is deliberately no evidence-issuance HTTP endpoint or production writer.
create table public.item_use_verifications (
  authorization_id uuid primary key references public.item_use_authorizations(id),
  claim_id uuid not null,
  operation_id text not null,
  source_sha256 text not null check (source_sha256 ~ '^[a-f0-9]{64}$'),
  result_sha256 text not null check (result_sha256 ~ '^[a-f0-9]{64}$' and result_sha256<>source_sha256),
  target_pokemon_entity_id uuid not null,
  identity_revision_id uuid not null,
  native_operation_id uuid not null,
  plan_sha256 text not null check (plan_sha256 ~ '^[a-f0-9]{64}$'),
  verified_at timestamptz not null default clock_timestamp()
);
alter table public.item_use_verifications enable row level security;
alter table public.item_use_verifications force row level security;
revoke all on public.item_use_verifications from public,anon,authenticated,service_role;
grant select on public.item_use_verifications to service_role;

create function public.api_prepare_item_use(
  p_season_id uuid, p_trainer_id uuid, p_purchase_id uuid,
  p_pokemon_entity_id uuid, p_save_file_id uuid, p_save_sha256 text,
  p_idempotency_key text, p_operation_id text
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare
  v_player public.season_players;
  v_purchase public.purchases;
  v_entity public.pokemon_entities;
  v_head public.pokemon_identity_revisions;
  v_observation public.pokemon_observations;
  v_save public.save_files;
  v_code text;
  v_effect text;
  v_existing public.item_use_authorizations;
  v_row public.item_use_authorizations;
begin
  if p_season_id is null or p_trainer_id is null or p_purchase_id is null
     or p_pokemon_entity_id is null or p_save_file_id is null
     or p_save_sha256 is null or p_save_sha256 !~ '^[a-f0-9]{64}$'
     or p_idempotency_key is null or p_operation_id is null
     or length(p_idempotency_key) not between 1 and 128
     or length(p_operation_id) not between 1 and 128
     or p_idempotency_key !~ '^[!-~]+$' or p_operation_id !~ '^[!-~]+$' then
    raise sqlstate 'PT422' using message='invalid_item_use_request';
  end if;
  perform 1 from public.trainers where id=p_trainer_id and globally_enabled for share;
  if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
  perform 1 from public.seasons where id=p_season_id for no key update;
  if not found then raise sqlstate 'PT404' using message='season_not_found'; end if;
  select * into v_player from public.season_players
    where season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found or v_player.status<>'active' then
    raise sqlstate 'PT403' using message='participant_inactive'; end if;
  select * into v_existing from public.item_use_authorizations
    where purchase_id=p_purchase_id for update;
  if found then
    if v_existing.idempotency_key<>p_idempotency_key
       or v_existing.operation_id<>p_operation_id
       or v_existing.trainer_id<>p_trainer_id
       or v_existing.season_id<>p_season_id
       or v_existing.target_pokemon_entity_id<>p_pokemon_entity_id
       or v_existing.save_file_id<>p_save_file_id
       or v_existing.save_sha256<>p_save_sha256 then
      raise sqlstate 'PT409' using message='item_use_conflict';
    end if;
    return to_jsonb(v_existing)-'claim_id';
  end if;
  select * into v_purchase from public.purchases where id=p_purchase_id
    and season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found then raise sqlstate 'PT404' using message='purchase_not_found'; end if;
  if v_purchase.status<>'pending' or v_purchase.quantity<>1 then
    raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
  select code into v_code from public.shop_items where id=v_purchase.shop_item_id for share;
  v_effect:=case v_code when 'revivir_pokemon' then 'revive' when 'robar_pokemon' then 'steal' end;
  if v_effect is null then raise sqlstate 'PT409' using message='item_use_not_required'; end if;
  -- Two-save theft is a later unit; a one-save proof cannot authorize it.
  if v_effect='steal' then raise sqlstate 'PT409' using message='item_use_unavailable'; end if;
  select * into v_save from public.save_files where id=p_save_file_id
    and season_id=p_season_id and trainer_id=p_trainer_id and deleted_at is null;
  if not found or v_save.sha256<>p_save_sha256 or v_save.parser_status<>'parsed'
     or v_player.current_save_file_id is distinct from v_save.id then
    raise sqlstate 'PT409' using message='save_context_changed'; end if;
  select * into v_entity from public.pokemon_entities where id=p_pokemon_entity_id
    and season_id=p_season_id for share;
  if not found then raise sqlstate 'PT409' using message='pokemon_target_invalid'; end if;
  if v_effect='revive' and v_entity.owner_trainer_id<>p_trainer_id then
    raise sqlstate 'PT409' using message='pokemon_not_owned'; end if;
  if v_effect='steal' and v_entity.owner_trainer_id=p_trainer_id then
    raise sqlstate 'PT409' using message='steal_self_target'; end if;
  select * into v_head from public.pokemon_identity_revisions
    where season_id=p_season_id and trainer_id=v_entity.owner_trainer_id
    order by revision_number desc limit 1 for share;
  if not found or v_entity.identity_status<>'unambiguous' or v_head.save_file_id<>v_save.id then
    raise sqlstate 'PT409' using message='pokemon_identity_ambiguous'; end if;
  select * into v_observation from public.pokemon_observations
    where revision_id=v_head.id and pokemon_entity_id=v_entity.id
      and trainer_id=v_entity.owner_trainer_id and season_id=p_season_id
      and outcome in ('NEW','MATCHED') for share;
  if not found then raise sqlstate 'PT409' using message='pokemon_identity_ambiguous'; end if;
  if v_effect='revive' and not (v_observation.source='box' and v_observation.box_number=8) then
    raise sqlstate 'PT409' using message='pokemon_not_revivable'; end if;
  if v_effect='steal' and v_observation.source='box' and v_observation.box_number not between 1 and 7 then
    raise sqlstate 'PT409' using message='steal_target_ineligible'; end if;
  -- Do not let two entitlements authorize separate physical mutations of the
  -- same observation, including expired/uncertain attempts awaiting reconciliation.
  if exists(select 1 from public.item_use_authorizations where
    target_pokemon_entity_id=p_pokemon_entity_id and identity_revision_id=v_head.id) then
    raise sqlstate 'PT409' using message='item_use_conflict'; end if;
  insert into public.item_use_authorizations(
    operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,
    save_file_id,save_sha256,identity_revision_id,effect_code,status)
  values(p_operation_id,p_idempotency_key,p_purchase_id,p_season_id,p_trainer_id,
    p_pokemon_entity_id,p_save_file_id,p_save_sha256,v_head.id,v_effect,'PREPARED')
  returning * into v_row;
  return to_jsonb(v_row)-'claim_id';
exception when unique_violation then
  -- Exact replay was handled under the participant lock above. Never return
  -- an arbitrary row from an OR query after a key collision.
  raise sqlstate 'PT409' using message='item_use_conflict';
end $$;
revoke all on function public.api_prepare_item_use(uuid,uuid,uuid,uuid,uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.api_prepare_item_use(uuid,uuid,uuid,uuid,uuid,text,text,text) to service_role;

-- One claimant for an authorization; no lease takeover after an unknown outcome.
create function public.api_claim_item_use(p_authorization_id uuid,p_season_id uuid,
 p_trainer_id uuid,p_operation_id text,p_claim_id uuid) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare a public.item_use_authorizations; p public.season_players;
begin
 if p_claim_id is null or p_operation_id is null then
  raise sqlstate 'PT422' using message='invalid_item_use_request'; end if;
 perform 1 from public.trainers where id=p_trainer_id and globally_enabled for share;
 if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 perform 1 from public.seasons where id=p_season_id for no key update;
 select * into p from public.season_players where season_id=p_season_id and trainer_id=p_trainer_id for update;
 if not found or p.status<>'active' then raise sqlstate 'PT403' using message='participant_inactive'; end if;
 select * into a from public.item_use_authorizations where id=p_authorization_id for update;
 if not found then raise sqlstate 'PT404' using message='item_use_not_found'; end if;
 if a.season_id is distinct from p_season_id or a.trainer_id is distinct from p_trainer_id then
  raise sqlstate 'PT403' using message='item_use_forbidden'; end if;
 if a.operation_id<>p_operation_id or (a.claim_id is not null and a.claim_id<>p_claim_id) then
  raise sqlstate 'PT409' using message='item_use_conflict'; end if;
 if a.status='APPLIED_VERIFIED' then return to_jsonb(a)-'claim_id'; end if;
 if a.expires_at<=clock_timestamp() then raise sqlstate 'PT409' using message='item_use_expired'; end if;
 if p.current_save_file_id is distinct from a.save_file_id then
  raise sqlstate 'PT409' using message='save_context_changed'; end if;
 if a.claim_id is not null then return to_jsonb(a)-'claim_id'; end if;
 if a.status<>'PREPARED' then raise sqlstate 'PT409' using message='item_use_conflict'; end if;
 update public.item_use_authorizations set claim_id=p_claim_id,status='PENDING_APPLICATION',updated_at=now()
  where id=a.id returning * into a;
 return to_jsonb(a)-'claim_id';
end $$;
revoke all on function public.api_claim_item_use(uuid,uuid,uuid,text,uuid) from public,anon,authenticated;
grant execute on function public.api_claim_item_use(uuid,uuid,uuid,text,uuid) to service_role;

create function public.api_complete_item_use(
 p_authorization_id uuid,p_season_id uuid,p_trainer_id uuid,p_operation_id text,
 p_status text,p_claim_id uuid,p_observed_sha256 text default null,p_error_code text default null
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare
 a public.item_use_authorizations; p public.season_players;
 v public.item_use_verifications; result jsonb;
begin
 if p_authorization_id is null or p_season_id is null or p_trainer_id is null
  or p_claim_id is null or p_operation_id is null or p_status is null
  or p_status not in ('APPLIED_VERIFIED','FAILED_RECOVERABLE','RECOVERY_REQUIRED','BLOCKED_UNCERTAIN')
  or p_operation_id !~ '^[!-~]{1,128}$'
  or (p_error_code is not null and p_error_code !~ '^[A-Z0-9_]{1,64}$')
  or (p_observed_sha256 is not null and p_observed_sha256 !~ '^[a-f0-9]{64}$') then
  raise sqlstate 'PT422' using message='invalid_item_use_completion'; end if;
 perform 1 from public.trainers where id=p_trainer_id and globally_enabled for share;
 if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 -- Same season -> participant -> authorization order in prepare/claim/complete.
 perform 1 from public.seasons where id=p_season_id for no key update;
 select * into p from public.season_players where season_id=p_season_id and trainer_id=p_trainer_id for update;
 if not found or p.status<>'active' then raise sqlstate 'PT403' using message='participant_inactive'; end if;
 select * into a from public.item_use_authorizations where id=p_authorization_id for update;
 if not found then raise sqlstate 'PT404' using message='item_use_not_found'; end if;
 if a.season_id<>p_season_id or a.trainer_id<>p_trainer_id then
  raise sqlstate 'PT403' using message='item_use_forbidden'; end if;
 if a.operation_id<>p_operation_id or a.claim_id is distinct from p_claim_id then
  raise sqlstate 'PT409' using message='item_use_conflict'; end if;
 if a.status='APPLIED_VERIFIED' then
  if p_status<>'APPLIED_VERIFIED' or p_observed_sha256 is distinct from a.observed_sha256 then
   raise sqlstate 'PT409' using message='item_use_conflict'; end if;
  return to_jsonb(a)-'claim_id';
 end if;
 if p_status<>'APPLIED_VERIFIED' then
  -- A failure report can never clear prior uncertainty or release/reassign a claim.
  update public.item_use_authorizations set
   status=case when status in ('BLOCKED_UNCERTAIN','RECOVERY_REQUIRED') then status else p_status end,
   error_code=coalesce(error_code,p_error_code,'APPLICATION_NOT_VERIFIED'),updated_at=now()
   where id=a.id returning * into a;
  return to_jsonb(a)-'claim_id';
 end if;
 select * into v from public.item_use_verifications where authorization_id=a.id;
 if not found or v.claim_id<>a.claim_id or v.operation_id<>a.operation_id
  or v.source_sha256<>a.save_sha256 or v.result_sha256 is distinct from p_observed_sha256
  or v.target_pokemon_entity_id<>a.target_pokemon_entity_id
  or v.identity_revision_id<>a.identity_revision_id
  or v.verified_at<a.created_at or v.verified_at>a.expires_at
  or a.expires_at<=clock_timestamp() then
  update public.item_use_authorizations set status='BLOCKED_UNCERTAIN',error_code='VERIFICATION_REQUIRED',updated_at=now()
   where id=a.id returning * into a;
  return to_jsonb(a)-'claim_id';
 end if;
 if p.current_save_file_id is distinct from a.save_file_id or not exists (
  select 1 from public.save_files where id=a.save_file_id and sha256=a.save_sha256
   and deleted_at is null and parser_status='parsed') then
  update public.item_use_authorizations set status='BLOCKED_UNCERTAIN',error_code='SAVE_CONTEXT_CHANGED',updated_at=now()
   where id=a.id returning * into a;
  return to_jsonb(a)-'claim_id';
 end if;
 -- Known business conflicts after physical work are uncertainty, never a new apply.
 -- Unexpected SQL errors propagate and roll back the entire transaction.
 begin
  -- Uncommitted transition visible only to this transaction/trigger. An old
  -- redemption caller cannot borrow a proof before the completion checks.
  update public.item_use_authorizations set status='APPLIED_VERIFIED',
   observed_sha256=v.result_sha256 where id=a.id;
  result:=public.api_redeem_purchase(a.season_id,a.trainer_id,a.purchase_id,
   a.target_pokemon_entity_id,a.idempotency_key,a.identity_revision_id);
 exception when sqlstate 'PT409' or sqlstate 'PT403' or sqlstate 'PT404' then
  update public.item_use_authorizations set status='BLOCKED_UNCERTAIN',error_code='APPLICATION_RECONCILIATION_REQUIRED',updated_at=now()
   where id=a.id returning * into a;
  return to_jsonb(a)-'claim_id';
 end;
 update public.item_use_authorizations set status='APPLIED_VERIFIED',observed_sha256=v.result_sha256,
  receipt=result,applied_at=now(),updated_at=now(),error_code=null where id=a.id returning * into a;
 return to_jsonb(a)-'claim_id';
end $$;
revoke all on function public.api_complete_item_use(uuid,uuid,uuid,text,text,uuid,text,text) from public,anon,authenticated;
grant execute on function public.api_complete_item_use(uuid,uuid,uuid,text,text,uuid,text,text) to service_role;

-- Prevent the old redemption endpoint from consuming an unverified physical
-- entitlement. Shield and robbery-shield (internal flags only) are unchanged.
create function public.check_item_use_redemption() returns trigger
language plpgsql security invoker set search_path='' as $$
begin
 if new.effect_code in ('revive','steal') and not exists (
  select 1 from public.item_use_authorizations a join public.item_use_verifications v on v.authorization_id=a.id
  where a.purchase_id=new.purchase_id and a.season_id=new.season_id and a.trainer_id=new.trainer_id
   and a.idempotency_key=new.idempotency_key and a.target_pokemon_entity_id=new.target_pokemon_entity_id
   and a.identity_revision_id=new.identity_revision_id and a.effect_code=new.effect_code
   and a.claim_id=v.claim_id and a.operation_id=v.operation_id and a.save_sha256=v.source_sha256
   and a.status='APPLIED_VERIFIED' and a.observed_sha256=v.result_sha256
   and a.identity_revision_id=v.identity_revision_id and a.target_pokemon_entity_id=v.target_pokemon_entity_id
   and v.verified_at between a.created_at and a.expires_at and a.expires_at>clock_timestamp()
 ) then raise sqlstate 'PT409' using message='physical_verification_required'; end if;
 return new;
end $$;
revoke all on function public.check_item_use_redemption() from public,anon,authenticated;
grant execute on function public.check_item_use_redemption() to service_role;
create trigger item_use_redemption_guard before insert on public.redemptions
for each row execute function public.check_item_use_redemption();

create function public.api_list_item_uses(p_season_id uuid,p_trainer_id uuid)
returns jsonb language sql security invoker set search_path='' as $$
  select coalesce(jsonb_agg(to_jsonb(a)-'claim_id' order by a.updated_at desc),'[]'::jsonb)
  from public.item_use_authorizations a
  where a.season_id=p_season_id and a.trainer_id=p_trainer_id;
$$;
revoke all on function public.api_list_item_uses(uuid,uuid) from public,anon,authenticated;
grant execute on function public.api_list_item_uses(uuid,uuid) to service_role;

commit;
