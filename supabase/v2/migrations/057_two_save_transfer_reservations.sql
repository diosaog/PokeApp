-- Phase24A LOCAL ONLY. Paired physical evidence, NOT competitive finalization.
-- No use consumption/ownership switch: foreign-OT accepted-save integration gated.
begin;
create table public.item_use_transfers (
 authorization_id uuid primary key references public.item_use_authorizations(id),
 donor_id uuid not null references public.trainers(id),
 plans jsonb,
 created_at timestamptz not null default clock_timestamp()
);
create table public.item_use_transfer_legs (
 authorization_id uuid not null references public.item_use_transfers(authorization_id),
 side text not null check(side in ('source','destination')),
 season_id uuid not null,
 trainer_id uuid not null,
 save_file_id uuid not null,
 identity_revision_id uuid not null references public.pokemon_identity_revisions(id),
 source_sha256 text not null check(source_sha256 ~ '^[0-9a-f]{64}$'),
 claim_id uuid,
 backup_sha256 text,
 apply_started boolean not null default false,
 result_sha256 text check(result_sha256 ~ '^[0-9a-f]{64}$' and result_sha256<>source_sha256),
 result_key text,
 result_url text,
 byte_size int check(byte_size in (415232,483328,441856,445440)),
 proof jsonb,
 primary key(authorization_id,side),
 unique(season_id,trainer_id), -- unresolved reservations never expire into reuse
 foreign key(save_file_id,season_id,trainer_id) references public.save_files(id,season_id,trainer_id),
 check((claim_id is null)=(backup_sha256 is null)),
 check(backup_sha256 is null or backup_sha256=source_sha256)
);
alter table public.item_use_transfers enable row level security;
alter table public.item_use_transfers force row level security;
alter table public.item_use_transfer_legs enable row level security;
alter table public.item_use_transfer_legs force row level security;
revoke all on public.item_use_transfers,public.item_use_transfer_legs from public,anon,authenticated,service_role,pokeapp_item_verifier;

create function public.transfer_context(p_id uuid) returns jsonb language sql security definer set search_path='' as $$
 select jsonb_build_object('authorization',to_jsonb(a),'entity',to_jsonb(e),'observation',to_jsonb(o),
  'purchase_pending',p.status='pending',
  'eligible',e.identity_status='unambiguous' and e.owner_trainer_id=x.donor_id
   and not exists(select 1 from public.pokemon_entity_flags f left join public.pokemon_flags lf on lf.id=f.legacy_flag_id
     where f.season_id=a.season_id and f.pokemon_entity_id=e.id and f.flag_type in('blindado','robado') and coalesce(f.flag_value,lf.flag_value,false)),
  'legs',(select jsonb_object_agg(l.side,jsonb_build_object(
   'trainer_id',l.trainer_id,'save',to_jsonb(s),'head_id',l.identity_revision_id,
   'current_save_id',sp.current_save_file_id,'trainer_enabled',t.globally_enabled,'participant_active',sp.status='active'))
   from public.item_use_transfer_legs l join public.save_files s on s.id=l.save_file_id
   join public.trainers t on t.id=l.trainer_id join public.season_players sp on sp.season_id=l.season_id and sp.trainer_id=l.trainer_id
   where l.authorization_id=a.id))
 from public.item_use_authorizations a join public.item_use_transfers x on x.authorization_id=a.id
 join public.purchases p on p.id=a.purchase_id join public.pokemon_entities e on e.id=a.target_pokemon_entity_id
 join public.pokemon_observations o on o.revision_id=a.identity_revision_id and o.pokemon_entity_id=e.id
 where a.id=p_id;
$$;
revoke all on function public.transfer_context(uuid) from public,anon,authenticated,service_role,pokeapp_item_verifier;

create function public.transfer_state(p_id uuid) returns text language sql security definer set search_path='' as $$
 select case
  when count(*)<>2 then 'BLOCKED_UNCERTAIN'
  when count(proof)=2 then 'BOTH_VERIFIED_PENDING_IDENTITY'
  when bool_or(side='destination' and apply_started) then 'VERIFYING_BOTH'
  when bool_or(side='source' and proof is not null) then 'PENDING_DESTINATION'
  when bool_or(side='source' and apply_started) then 'VERIFYING_SOURCE'
  when count(claim_id)=2 then 'PENDING_SOURCE'
  when count(claim_id)=1 then 'WAITING_OTHER'
  else 'PREPARING' end from public.item_use_transfer_legs where authorization_id=p_id;
$$;
revoke all on function public.transfer_state(uuid) from public,anon,authenticated,service_role,pokeapp_item_verifier;

create function public.api_prepare_transfer(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare sid uuid:=(p_request->>'season_id')::uuid; tid uuid:=(p_request->>'trainer_id')::uuid;
 pid uuid:=(p_request->>'purchase_id')::uuid; eid uuid:=(p_request->>'pokemon_entity_id')::uuid;
 op uuid:=(p_request->>'operation_id')::uuid; a public.item_use_authorizations; e public.pokemon_entities;
 donor public.season_players; receiver public.season_players; dhead public.pokemon_identity_revisions; rhead public.pokemon_identity_revisions;
 ds public.save_files; rs public.save_files; obs public.pokemon_observations; cyc bigint;
begin
 if op is null then raise sqlstate 'PT422' using message='invalid_transfer'; end if;
 perform 1 from public.trainers where id=tid and globally_enabled for share;
 if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 perform 1 from public.seasons where id=sid for no key update;
 perform 1 from public.season_players where season_id=sid order by id for update;
 select * into a from public.item_use_authorizations where purchase_id=pid for update;
 if found then
  if a.trainer_id is distinct from tid or a.season_id is distinct from sid or a.target_pokemon_entity_id is distinct from eid or a.operation_id is distinct from op::text
    or not exists(select 1 from public.item_use_transfers where authorization_id=a.id) then raise sqlstate 'PT409' using message='transfer_conflict'; end if;
  return jsonb_build_object('authorization_id',a.id,'status',public.transfer_state(a.id));
 end if;
 select * into e from public.pokemon_entities where id=eid and season_id=sid and identity_status='unambiguous' for update;
 if not found or e.owner_trainer_id=tid then raise sqlstate 'PT409' using message='transfer_target_invalid'; end if;
 select * into donor from public.season_players where season_id=sid and trainer_id=e.owner_trainer_id and status='active';
 select * into receiver from public.season_players where season_id=sid and trainer_id=tid and status='active';
 if donor.id is null or receiver.id is null or not exists(select 1 from public.trainers where id=e.owner_trainer_id and globally_enabled) then raise sqlstate 'PT409' using message='participant_inactive'; end if;
 perform 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id where p.id=pid and p.season_id=sid and p.trainer_id=tid and p.status='pending' and p.quantity=1 and i.code='robar_pokemon' for update of p;
 if not found then raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
 select * into dhead from public.pokemon_identity_revisions where season_id=sid and trainer_id=donor.trainer_id order by revision_number desc limit 1;
 select * into rhead from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid order by revision_number desc limit 1;
 select * into ds from public.save_files where id=donor.current_save_file_id and trainer_id=donor.trainer_id and season_id=sid and deleted_at is null and parser_status='parsed';
 select * into rs from public.save_files where id=receiver.current_save_file_id and trainer_id=tid and season_id=sid and deleted_at is null and parser_status='parsed';
 if ds.id is null or rs.id is null or dhead.id is null or rhead.id is null or dhead.save_file_id<>ds.id or rhead.save_file_id<>rs.id then raise sqlstate 'PT409' using message='save_context_changed'; end if;
 select * into obs from public.pokemon_observations where revision_id=dhead.id and pokemon_entity_id=eid and outcome in ('NEW','MATCHED');
 if not found or obs.source<>'box' or obs.box_number not between 1 and 7 then raise sqlstate 'PT409' using message='transfer_native_scope_unqualified'; end if;
 if exists(select 1 from public.pokemon_entity_flags f left join public.pokemon_flags l on l.id=f.legacy_flag_id where f.season_id=sid and f.pokemon_entity_id=eid and f.flag_type in ('blindado','robado') and coalesce(f.flag_value,l.flag_value,false)) then raise sqlstate 'PT409' using message='steal_target_shielded'; end if;
 select coalesce((select cycle_number from public.robbery_cycles where season_id=sid),1) into cyc;
 -- Match025 pre-check reset semantics, without changing the cursor before use.
 if not exists(select 1 from public.season_players sp join public.trainers t on t.id=sp.trainer_id where sp.season_id=sid and sp.status='active' and t.globally_enabled and not exists(select 1 from public.redemptions r where r.season_id=sid and r.robbery_cycle_number=cyc and r.target_owner_trainer_id=sp.trainer_id)) then cyc:=cyc+1; end if;
 if exists(select 1 from public.redemptions where season_id=sid and robbery_cycle_number=cyc and target_owner_trainer_id=donor.trainer_id) then raise sqlstate 'PT409' using message='steal_victim_already_robbed'; end if;
 if exists(select 1 from public.item_use_authorizations where season_id=sid and (target_pokemon_entity_id=eid or trainer_id in(tid,donor.trainer_id)) and status<>'APPLIED_VERIFIED') then raise sqlstate 'PT409' using message='transfer_reserved'; end if;
 insert into public.item_use_authorizations(operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,effect_code)
 values(op::text,op::text,pid,sid,tid,eid,rs.id,rs.sha256,dhead.id,'steal') returning * into a;
 insert into public.item_use_transfers(authorization_id,donor_id) values(a.id,donor.trainer_id);
 insert into public.item_use_transfer_legs(authorization_id,side,season_id,trainer_id,save_file_id,identity_revision_id,source_sha256) values
 (a.id,'source',sid,donor.trainer_id,ds.id,dhead.id,ds.sha256),(a.id,'destination',sid,tid,rs.id,rhead.id,rs.sha256);
 return jsonb_build_object('authorization_id',a.id,'status','PREPARING');
end $$;
revoke all on function public.api_prepare_transfer(jsonb) from public,anon,authenticated;
grant execute on function public.api_prepare_transfer(jsonb) to service_role;

create function public.api_transfer_leg(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare aid uuid:=(p_request->>'authorization_id')::uuid; op text:=p_request->>'operation';
 a public.item_use_authorizations; l public.item_use_transfer_legs; plans jsonb; state text;
begin
 select * into a from public.item_use_authorizations where id=aid;
 if not found then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
 perform 1 from public.seasons where id=a.season_id for no key update;
 select * into l from public.item_use_transfer_legs where authorization_id=aid and trainer_id=(p_request->>'trainer_id')::uuid and season_id=(p_request->>'season_id')::uuid for update;
 if not found or not exists(select 1 from public.trainers where id=l.trainer_id and globally_enabled) then raise sqlstate 'PT403' using message='transfer_not_owned'; end if;
 if op='ready' then
  if a.expires_at<=clock_timestamp() then raise sqlstate 'PT409' using message='transfer_expired'; end if;
  if p_request->>'backup_sha256' is distinct from l.source_sha256 or p_request->>'claim_id' is null or l.claim_id is not null and l.claim_id is distinct from (p_request->>'claim_id')::uuid then raise sqlstate 'PT409' using message='transfer_claim_conflict'; end if;
  update public.item_use_transfer_legs set claim_id=(p_request->>'claim_id')::uuid,backup_sha256=source_sha256 where authorization_id=aid and side=l.side returning * into l;
 elsif op in ('begin','reserve_result','queue_result') then
  if l.claim_id is null or l.claim_id is distinct from (p_request->>'claim_id')::uuid then raise sqlstate 'PT409' using message='transfer_claim_conflict'; end if;
  select x.plans into plans from public.item_use_transfers x where authorization_id=aid;
  if plans is null then raise sqlstate 'PT409' using message='transfer_not_planned'; end if;
  if op='begin' then
   if a.expires_at<=clock_timestamp() or (public.transfer_context(aid)->>'eligible')::boolean is not true
    or not exists(select 1 from public.purchases where id=a.purchase_id and status='pending')
    or exists(select 1 from public.item_use_transfer_legs l2 join public.season_players sp on sp.season_id=l2.season_id and sp.trainer_id=l2.trainer_id
      join public.trainers t on t.id=l2.trainer_id where l2.authorization_id=aid and (sp.status<>'active' or not t.globally_enabled or sp.current_save_file_id is distinct from l2.save_file_id))
    or exists(select 1 from public.item_use_transfer_legs where authorization_id=aid and claim_id is null)
    or l.side='destination' and not exists(select 1 from public.item_use_transfer_legs where authorization_id=aid and side='source' and proof is not null) then raise sqlstate 'PT409' using message='transfer_peer_pending'; end if;
   update public.item_use_transfer_legs set apply_started=true where authorization_id=aid and side=l.side returning * into l;
  else
   if not l.apply_started then raise sqlstate 'PT409' using message='transfer_not_started'; end if;
   if op='reserve_result' then
    if p_request->>'result_sha256' is distinct from plans->l.side->>'output_sha256' or l.result_sha256 is not null and l.result_sha256 is distinct from p_request->>'result_sha256' then raise sqlstate 'PT409' using message='transfer_result_conflict'; end if;
    update public.item_use_transfer_legs set result_sha256=p_request->>'result_sha256',byte_size=(p_request->>'byte_size')::int,
     result_key='item-use/'||aid::text||'/'||l.side||'/'||(p_request->>'result_sha256')||'.sav' where authorization_id=aid and side=l.side returning * into l;
   else
    if l.result_sha256 is null then raise sqlstate 'PT409' using message='transfer_not_reserved'; end if;
    if l.proof is null then update public.item_use_transfer_legs set result_url=p_request->>'result_url' where authorization_id=aid and side=l.side; end if;
   end if;
  end if;
 elsif op is distinct from 'get' then raise sqlstate 'PT422' using message='invalid_transfer_operation'; end if;
 state:=public.transfer_state(aid);
 return jsonb_build_object('authorization_id',aid,'side',l.side,'status',state,'source_sha256',l.source_sha256,
  'apply_started',l.apply_started,'result_sha256',l.result_sha256,'result_key',l.result_key,'verified',l.proof is not null);
end $$;
revoke all on function public.api_transfer_leg(jsonb) from public,anon,authenticated;
grant execute on function public.api_transfer_leg(jsonb) to service_role;

create function public.transfer_verifier(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare aid uuid:=(p_request->>'authorization_id')::uuid; op text:=p_request->>'operation'; c jsonb; plans jsonb;
 a public.item_use_authorizations; l public.item_use_transfer_legs; v_proof jsonb:=p_request->'proof'; v_side text:=p_request->>'side';
begin
 select * into a from public.item_use_authorizations where id=aid;
 if not found then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
 perform 1 from public.seasons where id=a.season_id for no key update;
 perform 1 from public.season_players where season_id=a.season_id order by id for update;
 perform 1 from public.item_use_transfer_legs where authorization_id=aid order by side for update;
 c:=public.transfer_context(aid);
 if c is null then raise sqlstate 'PT409' using message='transfer_context_missing'; end if;
 if op='context' then return c; end if;
 if op='artifact' then return (select to_jsonb(r) from public.item_use_transfer_legs r where authorization_id=aid and r.side=v_side); end if;
 if c is distinct from p_request->'context' or c->'purchase_pending'<>'true'::jsonb or c->'eligible' is distinct from 'true'::jsonb
   or exists(select 1 from jsonb_each(c->'legs') v where v.value->'trainer_enabled'<>'true'::jsonb or v.value->'participant_active'<>'true'::jsonb or v.value->>'current_save_id' is distinct from v.value->'save'->>'id')
 then raise sqlstate 'PT409' using message='transfer_context_changed'; end if;
 select x.plans into plans from public.item_use_transfers x where authorization_id=aid for update;
 if op='plan' then
  if plans is not null and plans is distinct from p_request->'plans' then raise sqlstate 'PT409' using message='transfer_plan_conflict'; end if;
  if jsonb_typeof(p_request->'plans') is distinct from 'object' or (select count(*) from jsonb_object_keys(p_request->'plans'))<>2
    or not(p_request->'plans' ?& array['source','destination']) then raise sqlstate 'PT422' using message='invalid_transfer_plan'; end if;
  update public.item_use_transfers set plans=p_request->'plans' where authorization_id=aid;
  return jsonb_build_object('status','PLANNED');
 elsif op='finish' then
  select * into l from public.item_use_transfer_legs r where authorization_id=aid and r.side=v_side;
  if l.claim_id is null or not l.apply_started or l.result_url is null or l.result_sha256 is null or plans is null
   or v_side='destination' and not exists(select 1 from public.item_use_transfer_legs where authorization_id=aid and item_use_transfer_legs.side='source' and item_use_transfer_legs.proof is not null)
   or v_proof is null or jsonb_typeof(v_proof)<>'object' or (select count(*) from jsonb_object_keys(v_proof))<>6
   or v_proof->>'authorization_id' is distinct from aid::text or v_proof->>'side' is distinct from v_side
   or v_proof->>'claim_id' is distinct from l.claim_id::text or v_proof->>'source_sha256' is distinct from l.source_sha256
   or v_proof->>'result_sha256' is distinct from l.result_sha256 or v_proof->>'plan_sha256' is distinct from plans->v_side->>'plan_sha256'
   or l.proof is not null and l.proof is distinct from v_proof then raise sqlstate 'PT409' using message='transfer_proof_conflict'; end if;
  update public.item_use_transfer_legs set proof=p_request->'proof' where authorization_id=aid and item_use_transfer_legs.side=v_side;
  return jsonb_build_object('status',public.transfer_state(aid));
 end if;
 raise sqlstate 'PT422' using message='invalid_transfer_operation';
end $$;
revoke all on function public.transfer_verifier(jsonb) from public,anon,authenticated,service_role;
grant execute on function public.transfer_verifier(jsonb) to pokeapp_item_verifier;

-- Incompatible ordinary sync and redemptions cannot overtake a reservation.
create function public.guard_transfer_reservation() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if tg_table_name in('redemptions','item_use_authorizations') then
  if exists(select 1 from public.item_use_transfer_legs l where l.season_id=new.season_id and
    (l.trainer_id=new.trainer_id or l.trainer_id in(select owner_trainer_id from public.pokemon_entities where id=new.target_pokemon_entity_id)))
  then raise sqlstate 'PT409' using message='transfer_reconciliation_required'; end if;
 else
  if exists(select 1 from public.item_use_transfer_legs l where l.season_id=new.season_id and l.trainer_id=new.trainer_id)
  then raise sqlstate 'PT409' using message='transfer_reconciliation_required'; end if;
 end if;
 return new;
end $$;
revoke all on function public.guard_transfer_reservation() from public,anon,authenticated,service_role,pokeapp_item_verifier;
create trigger transfer_no_save_advance before update of current_save_file_id on public.season_players
 for each row when(old.current_save_file_id is distinct from new.current_save_file_id) execute function public.guard_transfer_reservation();
create trigger transfer_no_identity_advance before insert on public.pokemon_identity_revisions for each row execute function public.guard_transfer_reservation();
create trigger transfer_no_redemption before insert on public.redemptions for each row execute function public.guard_transfer_reservation();
create trigger transfer_no_other_physical_use before insert on public.item_use_authorizations for each row execute function public.guard_transfer_reservation();
comment on table public.item_use_transfers is 'Local engineering paired evidence; BOTH_VERIFIED_PENDING_IDENTITY is NOT completion. No release/finalize path until trusted ownership and accepted saves are integrated.';
commit;
