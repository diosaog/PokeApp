-- Phase 23: explicit physical item-use authorization.
-- Preparation never consumes a purchase. Completion consumes it only after the
-- Launcher reports a verified native result for the same current save.
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
  identity_revision_id uuid,
  effect_code text not null check (effect_code in ('revive','steal')),
  status text not null default 'PREPARED' check (status in
    ('PREPARED','APPLIED_VERIFIED','FAILED_RECOVERABLE','RECOVERY_REQUIRED','BLOCKED_UNCERTAIN')),
  observed_sha256 text check (observed_sha256 is null or observed_sha256 ~ '^[a-f0-9]{64}$'),
  error_code text check (error_code is null or error_code ~ '^[A-Z0-9_]{1,64}$'),
  receipt jsonb check (receipt is null or jsonb_typeof(receipt)='object'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  applied_at timestamptz,
  foreign key (season_id,trainer_id) references public.season_players(season_id,trainer_id)
);
create index item_use_auth_trainer_status_idx on public.item_use_authorizations(trainer_id,status,updated_at);
comment on table public.item_use_authorizations is
  'Backend-only physical item authorization. PREPARED does not consume the purchase; APPLIED_VERIFIED is issued only after native readback.';

alter table public.item_use_authorizations enable row level security;
alter table public.item_use_authorizations force row level security;
revoke all on public.item_use_authorizations from public,anon,authenticated,service_role;
grant select,insert,update on public.item_use_authorizations to service_role;

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
       or v_existing.target_pokemon_entity_id<>p_pokemon_entity_id
       or v_existing.save_file_id<>p_save_file_id
       or v_existing.save_sha256<>p_save_sha256 then
      raise sqlstate 'PT409' using message='item_use_conflict';
    end if;
    return to_jsonb(v_existing);
  end if;
  select * into v_purchase from public.purchases where id=p_purchase_id
    and season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found then raise sqlstate 'PT404' using message='purchase_not_found'; end if;
  if v_purchase.status<>'pending' or v_purchase.quantity<>1 then
    raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
  select code into v_code from public.shop_items where id=v_purchase.shop_item_id for share;
  v_effect:=case v_code when 'revivir_pokemon' then 'revive' when 'robar_pokemon' then 'steal' end;
  if v_effect is null then raise sqlstate 'PT409' using message='item_use_not_required'; end if;
  select * into v_save from public.save_files where id=p_save_file_id
    and season_id=p_season_id and trainer_id=p_trainer_id and deleted_at is null;
  if not found or v_save.sha256<>p_save_sha256 or v_save.parser_status<>'parsed'
     or v_player.current_save_file_id<>v_save.id then
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
  if not found or v_entity.identity_status<>'unambiguous' then
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
  insert into public.item_use_authorizations(
    operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,
    save_file_id,save_sha256,identity_revision_id,effect_code,status)
  values(p_operation_id,p_idempotency_key,p_purchase_id,p_season_id,p_trainer_id,
    p_pokemon_entity_id,p_save_file_id,p_save_sha256,v_head.id,v_effect,'PREPARED')
  returning * into v_row;
  return to_jsonb(v_row);
exception when unique_violation then
  select * into v_existing from public.item_use_authorizations
    where idempotency_key=p_idempotency_key or operation_id=p_operation_id or purchase_id=p_purchase_id;
  if v_existing.id is null then raise; end if;
  if v_existing.trainer_id<>p_trainer_id or v_existing.purchase_id<>p_purchase_id
     or v_existing.target_pokemon_entity_id<>p_pokemon_entity_id then
    raise sqlstate 'PT409' using message='item_use_conflict';
  end if;
  return to_jsonb(v_existing);
end $$;
revoke all on function public.api_prepare_item_use(uuid,uuid,uuid,uuid,uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.api_prepare_item_use(uuid,uuid,uuid,uuid,uuid,text,text,text) to service_role;

create function public.api_complete_item_use(
  p_authorization_id uuid, p_season_id uuid, p_trainer_id uuid,
  p_operation_id text, p_status text,
  p_observed_sha256 text default null, p_error_code text default null
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare
  v_auth public.item_use_authorizations;
  v_player public.season_players;
  v_save public.save_files;
  v_receipt jsonb;
begin
  if p_authorization_id is null or p_operation_id is null or p_status is null
     or p_status not in ('APPLIED_VERIFIED','FAILED_RECOVERABLE','RECOVERY_REQUIRED','BLOCKED_UNCERTAIN')
     or p_operation_id !~ '^[!-~]{1,128}$'
     or (p_observed_sha256 is not null and p_observed_sha256 !~ '^[a-f0-9]{64}$') then
    raise sqlstate 'PT422' using message='invalid_item_use_completion';
  end if;
  -- Read scope before taking locks, then use the same season -> participant ->
  -- authorization order as the robbery redemption RPC. This prevents two
  -- concurrent Launcher completions from holding different participant locks.
  select * into v_auth from public.item_use_authorizations where id=p_authorization_id;
  if not found then raise sqlstate 'PT404' using message='item_use_not_found'; end if;
  if v_auth.season_id<>p_season_id or v_auth.trainer_id<>p_trainer_id then
    raise sqlstate 'PT403' using message='item_use_forbidden'; end if;
  if v_auth.operation_id<>p_operation_id then raise sqlstate 'PT409' using message='item_use_conflict'; end if;
  if v_auth.status='APPLIED_VERIFIED' then return to_jsonb(v_auth); end if;
  perform 1 from public.seasons where id=v_auth.season_id for no key update;
  if not found then raise sqlstate 'PT404' using message='season_not_found'; end if;
  select * into v_player from public.season_players where season_id=v_auth.season_id
    and trainer_id=v_auth.trainer_id for update;
  select * into v_auth from public.item_use_authorizations where id=p_authorization_id for update;
  if v_auth.season_id<>p_season_id or v_auth.trainer_id<>p_trainer_id
     or v_auth.operation_id<>p_operation_id then
    raise sqlstate 'PT409' using message='item_use_conflict'; end if;
  if v_auth.status='APPLIED_VERIFIED' then return to_jsonb(v_auth); end if;
  if p_status<>'APPLIED_VERIFIED' then
    update public.item_use_authorizations set status=p_status,error_code=coalesce(p_error_code,'APPLICATION_NOT_VERIFIED'),
      observed_sha256=p_observed_sha256,updated_at=now() where id=v_auth.id returning * into v_auth;
    return to_jsonb(v_auth);
  end if;
  if p_observed_sha256 is distinct from v_auth.save_sha256 then
    update public.item_use_authorizations set status='BLOCKED_UNCERTAIN',error_code='RESULT_HASH_MISMATCH',
      observed_sha256=p_observed_sha256,updated_at=now() where id=v_auth.id returning * into v_auth;
    return to_jsonb(v_auth);
  end if;
  select * into v_save from public.save_files where id=v_auth.save_file_id and deleted_at is null;
  if v_player.current_save_file_id is distinct from v_auth.save_file_id or v_save.sha256 is distinct from v_auth.save_sha256 then
    update public.item_use_authorizations set status='BLOCKED_UNCERTAIN',error_code='SAVE_CONTEXT_CHANGED',updated_at=now()
      where id=v_auth.id returning * into v_auth;
    return to_jsonb(v_auth);
  end if;
  begin
    v_receipt:=public.api_redeem_purchase(v_auth.season_id,v_auth.trainer_id,v_auth.purchase_id,
      v_auth.target_pokemon_entity_id,v_auth.idempotency_key,v_auth.identity_revision_id);
  exception when others then
    update public.item_use_authorizations set status='FAILED_RECOVERABLE',error_code='APPLICATION_REJECTED',updated_at=now()
      where id=v_auth.id returning * into v_auth;
    return to_jsonb(v_auth)||jsonb_build_object('receipt',null);
  end;
  update public.item_use_authorizations set status='APPLIED_VERIFIED',observed_sha256=p_observed_sha256,
    receipt=v_receipt,applied_at=now(),updated_at=now() where id=v_auth.id returning * into v_auth;
  return to_jsonb(v_auth)||jsonb_build_object('receipt',v_receipt);
end $$;
revoke all on function public.api_complete_item_use(uuid,uuid,uuid,text,text,text,text) from public,anon,authenticated;
grant execute on function public.api_complete_item_use(uuid,uuid,uuid,text,text,text,text) to service_role;

create function public.api_list_item_uses(p_season_id uuid,p_trainer_id uuid)
returns jsonb language sql security invoker set search_path='' as $$
  select coalesce(jsonb_agg(to_jsonb(a) order by a.updated_at desc),'[]'::jsonb)
  from public.item_use_authorizations a
  where a.season_id=p_season_id and a.trainer_id=p_trainer_id;
$$;
revoke all on function public.api_list_item_uses(uuid,uuid) from public,anon,authenticated;
grant execute on function public.api_list_item_uses(uuid,uuid) to service_role;

commit;
