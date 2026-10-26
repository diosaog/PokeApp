-- Phase27A. LOCAL ONLY: not applied to production, no public writer capability.
-- Server-authoritative robbery. The competitive decision (consumption, ownership,
-- flags, voucher) is taken once by the restricted verifier from the server-held
-- accepted saves, without waiting for the victim. Each side then carries its own
-- physical obligation, settled only by an independently verified artifact.
begin;

alter table public.item_use_transfers add column adjudicated_at timestamptz;
alter table public.item_use_transfers add column adjudication jsonb;
alter table public.item_use_transfers add column plan_history jsonb not null default '[]'::jsonb;
alter table public.item_use_transfer_legs add column obligation text
 check(obligation in ('PHYSICAL_PENDING','RECOVERY_REQUIRED','VERIFIED','ABSENT_VERIFIED','INCIDENT'));
alter table public.item_use_transfer_legs add column candidate_sha256 text check(candidate_sha256 ~ '^[0-9a-f]{64}$');
alter table public.item_use_transfer_legs add column candidate_key text;
alter table public.item_use_transfer_legs add column candidate_url text;
alter table public.item_use_transfer_legs add column candidate_size int check(candidate_size in (415232,483328,441856,445440));
alter table public.item_use_transfer_legs add column basis_key text;
alter table public.item_use_transfer_legs add column incident text;
alter table public.item_use_transfer_legs add column settled_save_id uuid references public.save_files(id);

create or replace function public.transfer_state(p_id uuid) returns text language sql security definer set search_path='' as $$
 select case
  when x.terminal='CANCELLED' then 'CANCELLED'
  when x.terminal='COMMITTED' then case when x.adjudicated_at is null then 'COMMITTED' else 'RECONCILED' end
  when (select count(*) from public.item_use_transfer_legs l where l.authorization_id=p_id)<>2 then 'BLOCKED_UNCERTAIN'
  when x.adjudicated_at is not null then case when exists(select 1 from public.item_use_transfer_legs l
    where l.authorization_id=p_id and l.obligation='INCIDENT') then 'BLOCKED_UNCERTAIN' else 'COMPETITIVELY_ADJUDICATED' end
  when x.plans is null then 'REQUESTED'
  else 'ELIGIBILITY_VERIFIED' end
 from public.item_use_transfers x where x.authorization_id=p_id;
$$;

-- Per-side physical state, never conflated with the competitive decision.
create function public.transfer_obligation(p_id uuid,p_side text) returns text language sql stable security definer set search_path='' as $$
 select case when x.adjudicated_at is null then null else
  (case l.side when 'source' then 'DONOR_' else 'RECIPIENT_' end)||case l.obligation
   when 'PHYSICAL_PENDING' then 'PHYSICAL_PENDING' when 'RECOVERY_REQUIRED' then 'RECOVERY_REQUIRED'
   when 'VERIFIED' then 'VERIFIED' when 'ABSENT_VERIFIED' then 'ABSENT_VERIFIED' else 'BLOCKED_UNCERTAIN' end end
 from public.item_use_transfer_legs l join public.item_use_transfers x on x.authorization_id=l.authorization_id
 where l.authorization_id=p_id and l.side=p_side;
$$;
revoke all on function public.transfer_obligation(uuid,text) from public,anon,authenticated,service_role,pokeapp_item_verifier;

create function public.transfer_leg_view(p_id uuid,p_side text) returns jsonb language sql stable security definer set search_path='' as $$
 select jsonb_build_object('authorization_id',l.authorization_id,'side',l.side,'status',public.transfer_state(p_id),
  'obligation',public.transfer_obligation(p_id,p_side),'source_sha256',l.source_sha256,'apply_started',l.apply_started,
  'result_sha256',l.result_sha256,'result_key',l.result_key,'verified',l.proof is not null,
  'candidate_sha256',l.candidate_sha256,'candidate_key',l.candidate_key,
  'pair_id',x.plans->l.side->'intent'->'mutation'->>'pair_id',
  'accepted_save_id',coalesce(l.settled_save_id::text,x.receipt->l.side->>'save_id'))
 from public.item_use_transfer_legs l join public.item_use_transfers x on x.authorization_id=l.authorization_id
 where l.authorization_id=p_id and l.side=p_side;
$$;
revoke all on function public.transfer_leg_view(uuid,text) from public,anon,authenticated,service_role,pokeapp_item_verifier;

-- A stolen identity is proven for the robber from the competitive decision on.
create or replace function public.transfer_identity_proven(p_entity uuid,p_trainer uuid,p_evidence jsonb) returns boolean
language sql security definer set search_path='' as $$
 select exists(select 1 from public.transfer_provenance p join public.pokemon_entities e on e.id=p.pokemon_entity_id
 join public.item_use_transfers x on x.authorization_id=p.authorization_id
 where e.id=p_entity and e.owner_trainer_id=p_trainer and p.recipient_id=p_trainer
 and e.initial_evidence=p.evidence and (p.evidence-'source_trainer_match')=(p_evidence-'source_trainer_match')
 and (x.terminal='COMMITTED' or x.adjudicated_at is not null
  or exists(select 1 from public.transfer_commit_permits c where c.txid=txid_current() and c.authorization_id=p.authorization_id)));
$$;

-- Canonical 025 redemption runs inside the adjudication transaction only.
create or replace function public.check_item_use_redemption() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if new.effect_code='steal' and exists(
  select 1 from public.transfer_commit_permits c join public.item_use_authorizations a on a.id=c.authorization_id
  join public.item_use_transfers x on x.authorization_id=a.id
  where c.txid=txid_current() and a.purchase_id=new.purchase_id and a.season_id=new.season_id
   and a.trainer_id=new.trainer_id and a.target_pokemon_entity_id=new.target_pokemon_entity_id
   and a.identity_revision_id=new.identity_revision_id and a.idempotency_key=new.idempotency_key
   and x.plans is not null and x.adjudicated_at is null and x.terminal is null
 ) then return new; end if;
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

-- Owner decision B: cross-title robbery is refused at reservation, before any work.
create or replace function public.api_prepare_transfer(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
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
 if ds.metadata->'save_identity'->>'game' is distinct from rs.metadata->'save_identity'->>'game' then raise sqlstate 'PT409' using message='transfer_cross_title_forbidden'; end if;
 select * into obs from public.pokemon_observations where revision_id=dhead.id and pokemon_entity_id=eid and outcome in ('NEW','MATCHED');
 if not found or not (obs.source='box' and obs.box_number between 1 and 7 or obs.source='party' and obs.slot_number between 1 and 6) then raise sqlstate 'PT409' using message='transfer_native_scope_unqualified'; end if;
 if exists(select 1 from public.pokemon_entity_flags f left join public.pokemon_flags l on l.id=f.legacy_flag_id where f.season_id=sid and f.pokemon_entity_id=eid and f.flag_type in ('blindado','robado') and coalesce(f.flag_value,l.flag_value,false)) then raise sqlstate 'PT409' using message='steal_target_shielded'; end if;
 select coalesce((select cycle_number from public.robbery_cycles where season_id=sid),1) into cyc;
 -- Match025 pre-check reset semantics, without changing the cursor before use.
 if not exists(select 1 from public.season_players sp join public.trainers t on t.id=sp.trainer_id where sp.season_id=sid and sp.status='active' and t.globally_enabled and not exists(select 1 from public.redemptions r where r.season_id=sid and r.robbery_cycle_number=cyc and r.target_owner_trainer_id=sp.trainer_id)) then cyc:=cyc+1; end if;
 if exists(select 1 from public.redemptions where season_id=sid and robbery_cycle_number=cyc and target_owner_trainer_id=donor.trainer_id) then raise sqlstate 'PT409' using message='steal_victim_already_robbed'; end if;
 -- A decided robbery stops reserving its trainers once their own side is settled.
 if exists(select 1 from public.item_use_authorizations ia where ia.season_id=sid and ia.status<>'APPLIED_VERIFIED'
    and (ia.target_pokemon_entity_id=eid or ia.trainer_id in(tid,donor.trainer_id))
    and not exists(select 1 from public.item_use_transfers x where x.authorization_id=ia.id and (x.terminal='CANCELLED' or x.adjudicated_at is not null)))
  or exists(select 1 from public.item_use_transfer_legs l where l.season_id=sid and l.trainer_id in(tid,donor.trainer_id) and not l.released)
 then raise sqlstate 'PT409' using message='transfer_reserved'; end if;
 insert into public.item_use_authorizations(operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,effect_code)
 values(op::text,op::text,pid,sid,tid,eid,rs.id,rs.sha256,dhead.id,'steal') returning * into a;
 insert into public.item_use_transfers(authorization_id,donor_id) values(a.id,donor.trainer_id);
 insert into public.item_use_transfer_legs(authorization_id,side,season_id,trainer_id,save_file_id,identity_revision_id,source_sha256) values
 (a.id,'source',sid,donor.trainer_id,ds.id,dhead.id,ds.sha256),(a.id,'destination',sid,tid,rs.id,rhead.id,rs.sha256);
 return jsonb_build_object('authorization_id',a.id,'status','REQUESTED');
end $$;

-- Participants: before the decision only reservation/cancel; after it only their
-- own physical obligation. Nobody can veto or undo an adjudicated robbery.
alter function public.api_transfer_leg(jsonb) rename to transfer_leg_v058;
revoke all on function public.transfer_leg_v058(jsonb) from public,anon,authenticated,service_role,pokeapp_item_verifier;
create function public.api_transfer_leg(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare a public.item_use_authorizations; x public.item_use_transfers; l public.item_use_transfer_legs; op text:=p_request->>'operation';
 v_sha text:=p_request->>'candidate_sha256';
begin
 select * into a from public.item_use_authorizations where id=(p_request->>'authorization_id')::uuid;
 if a.id is null then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
 perform 1 from public.seasons where id=a.season_id for no key update;
 select * into x from public.item_use_transfers where authorization_id=a.id for update;
 select * into l from public.item_use_transfer_legs where authorization_id=a.id and trainer_id=(p_request->>'trainer_id')::uuid and season_id=(p_request->>'season_id')::uuid for update;
 if l.side is null or not exists(select 1 from public.trainers where id=l.trainer_id and globally_enabled) then raise sqlstate 'PT403' using message='transfer_not_owned'; end if;
 if x.adjudicated_at is null then
  -- No physical change can start before the competitive decision.
  if op in ('begin','reserve_result','queue_result','reserve_candidate','queue_candidate') then raise sqlstate 'PT409' using message='transfer_not_adjudicated'; end if;
  return public.transfer_leg_v058(p_request)||public.transfer_leg_view(a.id,l.side);
 end if;
 if op='cancel' then raise sqlstate 'PT409' using message='transfer_adjudicated'; end if;
 if op is distinct from 'get' then
  if x.terminal is not null or l.obligation not in ('PHYSICAL_PENDING','RECOVERY_REQUIRED') then raise sqlstate 'PT409' using message='transfer_leg_settled'; end if;
  if op='ready' then
   if l.obligation<>'PHYSICAL_PENDING' or p_request->>'backup_sha256' is distinct from l.source_sha256 or p_request->>'claim_id' is null
    or l.claim_id is not null and l.claim_id is distinct from (p_request->>'claim_id')::uuid then raise sqlstate 'PT409' using message='transfer_claim_conflict'; end if;
   update public.item_use_transfer_legs set claim_id=(p_request->>'claim_id')::uuid,backup_sha256=source_sha256 where authorization_id=a.id and side=l.side;
  elsif op='begin' then
   if l.obligation<>'PHYSICAL_PENDING' or l.claim_id is null or l.claim_id is distinct from (p_request->>'claim_id')::uuid or x.plans->l.side is null
    then raise sqlstate 'PT409' using message='transfer_claim_conflict'; end if;
   update public.item_use_transfer_legs set apply_started=true where authorization_id=a.id and side=l.side;
  elsif op in ('reserve_result','queue_result') then
   perform public.transfer_leg_v057(p_request);
  elsif op='reserve_candidate' then
   -- The current file differs from the plan: the verifier re-plans on it (or,
   -- for the victim, proves the Pokémon is no longer there). Never a decision.
   if l.proof is not null or v_sha is null or v_sha !~ '^[0-9a-f]{64}$'
    or (p_request->>'byte_size')::int not in (415232,483328,441856,445440)
    or l.candidate_sha256 is not null and l.candidate_sha256<>v_sha then raise sqlstate 'PT409' using message='transfer_candidate_conflict'; end if;
   update public.item_use_transfer_legs set candidate_sha256=v_sha,candidate_size=(p_request->>'byte_size')::int,
    candidate_key='item-use/'||a.id::text||'/'||l.side||'/candidate/'||v_sha||'.sav' where authorization_id=a.id and side=l.side;
  elsif op='queue_candidate' then
   if l.candidate_sha256 is null then raise sqlstate 'PT409' using message='transfer_not_reserved'; end if;
   update public.item_use_transfer_legs set candidate_url=p_request->>'candidate_url' where authorization_id=a.id and side=l.side;
  else raise sqlstate 'PT422' using message='invalid_transfer_operation';
  end if;
 end if;
 return public.transfer_leg_view(a.id,l.side);
end $$;
revoke all on function public.api_transfer_leg(jsonb) from public,anon,authenticated,pokeapp_item_verifier;
grant execute on function public.api_transfer_leg(jsonb) to service_role;

create or replace function public.api_transfer_list(p_request jsonb) returns jsonb language plpgsql stable security definer set search_path='' as $$
declare sid uuid:=(p_request->>'season_id')::uuid; tid uuid:=(p_request->>'trainer_id')::uuid;
begin
 if sid is null or tid is null then raise sqlstate 'PT422' using message='invalid_transfer'; end if;
 if not exists(select 1 from public.trainers where id=tid and globally_enabled) then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 return coalesce((select jsonb_agg(q.item order by q.created_at desc) from (
  select a.created_at,jsonb_build_object(
   'authorization_id',a.id,'side',l.side,'status',public.transfer_state(a.id),
   'obligation',public.transfer_obligation(a.id,l.side),
   'purchase_id',case when l.side='destination' then a.purchase_id end,
   'pokemon_entity_id',a.target_pokemon_entity_id,'source_sha256',l.source_sha256,
   'claimed',l.claim_id is not null,'apply_started',l.apply_started,'result_sha256',l.result_sha256,
   'verified',l.proof is not null,'accepted_save_id',coalesce(l.settled_save_id::text,x.receipt->l.side->>'save_id'),
   'pair_id',x.plans->l.side->'intent'->'mutation'->>'pair_id',
   'intent',case when x.adjudicated_at is not null and l.obligation='PHYSICAL_PENDING' then x.plans->l.side->'intent' end,
   'expires_at',a.expires_at,'created_at',a.created_at) item
  from public.item_use_transfer_legs l
  join public.item_use_authorizations a on a.id=l.authorization_id
  join public.item_use_transfers x on x.authorization_id=a.id
  where l.season_id=sid and l.trainer_id=tid
  order by a.created_at desc limit 20) q),'[]'::jsonb);
end $$;

alter function public.transfer_verifier(jsonb) rename to transfer_verifier_v059;
revoke all on function public.transfer_verifier_v059(jsonb) from public,anon,authenticated,service_role,pokeapp_item_verifier;
create function public.transfer_verifier(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare aid uuid:=(p_request->>'authorization_id')::uuid; op text:=p_request->>'operation'; v_side text:=p_request->>'side';
 a public.item_use_authorizations; x public.item_use_transfers; l public.item_use_transfer_legs;
 c jsonb; req jsonb; redemption jsonb; registered jsonb; rev uuid; v_proof jsonb:=p_request->'proof'; v_plan jsonb:=p_request->'plan';
 snapshot jsonb; v_mode text:=p_request->>'mode'; v_kind text;
begin
 if op='queue' then
  -- Discovery only. Every action re-derives and rechecks its full context.
  return coalesce((select jsonb_agg(jsonb_build_object('authorization_id',w.aid,'action',w.action,'side',w.side) order by w.created_at,w.aid,w.side)
   from (select * from (
    select tx.authorization_id aid,ia.created_at,'plan' action,null::text side from public.item_use_transfers tx
     join public.item_use_authorizations ia on ia.id=tx.authorization_id
     where tx.terminal is null and tx.plans is null and ia.expires_at>clock_timestamp()
    union all
    select tx.authorization_id,ia.created_at,'adjudicate',null from public.item_use_transfers tx
     join public.item_use_authorizations ia on ia.id=tx.authorization_id
     where tx.terminal is null and tx.plans is not null and tx.adjudicated_at is null and ia.expires_at>clock_timestamp()
    union all
    select tl.authorization_id,ia.created_at,'rebase',tl.side from public.item_use_transfer_legs tl
     join public.item_use_transfers tx on tx.authorization_id=tl.authorization_id
     join public.item_use_authorizations ia on ia.id=tl.authorization_id
     where tx.terminal is null and tx.adjudicated_at is not null and tl.candidate_url is not null and tl.proof is null
      and tl.obligation in ('PHYSICAL_PENDING','RECOVERY_REQUIRED')
    union all
    select tl.authorization_id,ia.created_at,'verify',tl.side from public.item_use_transfer_legs tl
     join public.item_use_transfers tx on tx.authorization_id=tl.authorization_id
     join public.item_use_authorizations ia on ia.id=tl.authorization_id
     where tx.terminal is null and tx.adjudicated_at is not null and tl.apply_started and tl.result_url is not null
      and tl.proof is null and tl.obligation='PHYSICAL_PENDING'
    union all
    select tl.authorization_id,ia.created_at,'settle',tl.side from public.item_use_transfer_legs tl
     join public.item_use_transfers tx on tx.authorization_id=tl.authorization_id
     join public.item_use_authorizations ia on ia.id=tl.authorization_id
     where tx.terminal is null and tx.adjudicated_at is not null and tl.proof is not null and tl.obligation='PHYSICAL_PENDING'
   ) j order by created_at limit 20) w),'[]'::jsonb);
 end if;
 select * into a from public.item_use_authorizations where id=aid;
 if a.id is null then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
 -- Match025's actor -> season -> ordered participants.
 perform 1 from public.trainers where id in(a.trainer_id,(select donor_id from public.item_use_transfers where authorization_id=aid)) order by id for share;
 perform 1 from public.seasons where id=a.season_id for no key update;
 perform 1 from public.season_players where season_id=a.season_id order by id for update;
 select * into x from public.item_use_transfers where authorization_id=aid for update;
 if x.authorization_id is null then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
 if op='status' then
  return jsonb_build_object('status',public.transfer_state(aid),'receipt',x.receipt,'adjudicated',x.adjudicated_at is not null);
 end if;
 if x.adjudicated_at is null then
  if op in ('finalize','finish','settle','settle_context','rebase','reject_candidate','adjudicated_context') then
   -- The two-proof completion is superseded: nothing physical before the decision.
   raise sqlstate 'PT409' using message='transfer_not_adjudicated'; end if;
  if op<>'adjudicate' then return public.transfer_verifier_v059(p_request); end if;
  if x.terminal is not null then raise sqlstate 'PT409' using message='transfer_terminal'; end if;
  perform 1 from public.item_use_transfer_legs where authorization_id=aid order by side for update;
  c:=public.transfer_context(aid);
  if c is null or c is distinct from p_request->'context' or c->'eligible' is distinct from 'true'::jsonb
   or c->'purchase_pending' is distinct from 'true'::jsonb or a.expires_at<=clock_timestamp()
   or exists(select 1 from jsonb_each(c->'legs') v where v.value->'trainer_enabled' is distinct from 'true'::jsonb
    or v.value->'participant_active' is distinct from 'true'::jsonb or v.value->>'current_save_id' is distinct from v.value->'save'->>'id')
   then raise sqlstate 'PT409' using message='transfer_context_changed'; end if;
  if c->'legs'->'source'->'save'->'metadata'->'save_identity'->>'game'
   is distinct from c->'legs'->'destination'->'save'->'metadata'->'save_identity'->>'game' then
   raise sqlstate 'PT409' using message='transfer_cross_title_forbidden'; end if;
  if x.plans is null or x.plans is distinct from p_request->'plans' then raise sqlstate 'PT409' using message='transfer_plan_conflict'; end if;
  insert into public.transfer_commit_permits values(txid_current(),aid);
  -- Canonical 025 effects while donor ownership/head still match the authorized target.
  redemption:=public.api_redeem_purchase(a.season_id,a.trainer_id,a.purchase_id,a.target_pokemon_entity_id,a.idempotency_key,a.identity_revision_id);
  insert into public.transfer_provenance(authorization_id,pokemon_entity_id,season_id,donor_id,recipient_id,evidence,originals,results,proofs,original_flags)
  values(aid,a.target_pokemon_entity_id,a.season_id,x.donor_id,a.trainer_id,c->'entity'->'initial_evidence',c->'legs','{}'::jsonb,'{}'::jsonb,
   coalesce((select jsonb_agg(to_jsonb(f)) from public.pokemon_entity_flags f where pokemon_entity_id=a.target_pokemon_entity_id),'[]'::jsonb));
  update public.pokemon_entities set owner_trainer_id=a.trainer_id,updated_at=now() where id=a.target_pokemon_entity_id;
  update public.pokemon_entity_flags set trainer_id=a.trainer_id where pokemon_entity_id=a.target_pokemon_entity_id;
  update public.item_use_transfers set adjudicated_at=clock_timestamp(),
   adjudication=jsonb_build_object('context',c,'plans',x.plans,'redemption',redemption) where authorization_id=aid;
  update public.item_use_transfer_legs set obligation='PHYSICAL_PENDING' where authorization_id=aid;
  delete from public.transfer_commit_permits where txid=txid_current();
  return jsonb_build_object('status',public.transfer_state(aid),'redemption',redemption);
 end if;
 if op='adjudicate' then return jsonb_build_object('status',public.transfer_state(aid),'redemption',x.adjudication->'redemption'); end if;
 if op='adjudicated_context' then
  return jsonb_build_object('adjudication',x.adjudication,'plans',x.plans,'plan_history',x.plan_history,
   'legs',(select jsonb_object_agg(r.side,to_jsonb(r)-'proof'||jsonb_build_object('verified',r.proof is not null))
    from public.item_use_transfer_legs r where r.authorization_id=aid));
 end if;
 if op='artifact' then return (select to_jsonb(r) from public.item_use_transfer_legs r where authorization_id=aid and r.side=v_side); end if;
 if x.terminal is not null then raise sqlstate 'PT409' using message='transfer_terminal'; end if;
 select * into l from public.item_use_transfer_legs r where r.authorization_id=aid and r.side=v_side for update;
 if l.side is null then raise sqlstate 'PT422' using message='invalid_transfer_operation'; end if;
 snapshot:=x.adjudication->'context';
 v_kind:=case v_side when 'source' then 'transfer_remove' else 'transfer_insert' end;
 if op='finish' then
  if l.obligation<>'PHYSICAL_PENDING' or l.claim_id is null or not l.apply_started or l.result_url is null or l.result_sha256 is null
   or v_proof is null or jsonb_typeof(v_proof)<>'object' or (select count(*) from jsonb_object_keys(v_proof))<>6
   or v_proof->>'authorization_id' is distinct from aid::text or v_proof->>'side' is distinct from v_side
   or v_proof->>'claim_id' is distinct from l.claim_id::text or v_proof->>'source_sha256' is distinct from l.source_sha256
   or v_proof->>'result_sha256' is distinct from l.result_sha256 or v_proof->>'plan_sha256' is distinct from x.plans->v_side->>'plan_sha256'
   or l.proof is not null and l.proof is distinct from v_proof then raise sqlstate 'PT409' using message='transfer_proof_conflict'; end if;
  update public.item_use_transfer_legs set proof=v_proof where authorization_id=aid and side=v_side;
  return public.transfer_leg_view(aid,v_side);
 elsif op='rebase' then
  if l.proof is not null or l.obligation not in ('PHYSICAL_PENDING','RECOVERY_REQUIRED') or l.candidate_sha256 is null
   or p_request->>'candidate_sha256' is distinct from l.candidate_sha256 or p_request->>'basis_key' is null
   or jsonb_typeof(v_plan) is distinct from 'object' or (select count(*) from jsonb_object_keys(v_plan))<>3
   or v_plan->'intent'->>'expected_sha256' is distinct from l.candidate_sha256
   or v_plan->'intent'->'mutation'->>'kind' is distinct from v_kind
   or v_plan->'intent'->'mutation'->>'pair_id' is distinct from p_request->>'pair_id'
   or exists(select 1 from jsonb_array_elements(x.plan_history) h where h->'plan'->'intent'->'mutation'->>'pair_id'=p_request->>'pair_id')
   or x.plans->v_side->'intent'->'mutation'->>'pair_id'=p_request->>'pair_id'
   then raise sqlstate 'PT409' using message='transfer_rebase_conflict'; end if;
  update public.item_use_transfers set plan_history=plan_history||jsonb_build_array(jsonb_build_object('side',v_side,
    'plan',x.plans->v_side,'source_sha256',l.source_sha256,'replaced_at',clock_timestamp())),
   plans=jsonb_set(plans,array[v_side],v_plan) where authorization_id=aid;
  update public.item_use_transfer_legs set source_sha256=l.candidate_sha256,claim_id=null,backup_sha256=null,apply_started=false,
   result_sha256=null,result_key=null,result_url=null,byte_size=null,basis_key=p_request->>'basis_key',
   candidate_sha256=null,candidate_key=null,candidate_url=null,candidate_size=null,obligation='PHYSICAL_PENDING',incident=null
   where authorization_id=aid and side=v_side;
  return public.transfer_leg_view(aid,v_side);
 elsif op='reject_candidate' then
  if l.proof is not null or l.obligation not in ('PHYSICAL_PENDING','RECOVERY_REQUIRED') or p_request->>'code' !~ '^[A-Z_]{3,64}$'
   then raise sqlstate 'PT409' using message='transfer_leg_settled'; end if;
  update public.item_use_transfer_legs set candidate_sha256=null,candidate_key=null,candidate_url=null,candidate_size=null,
   incident=p_request->>'code',obligation=case when (p_request->'blocking')='true'::jsonb then 'INCIDENT' else 'RECOVERY_REQUIRED' end
   where authorization_id=aid and side=v_side;
  return public.transfer_leg_view(aid,v_side);
 elsif op='settle_context' then
  return jsonb_build_object('leg',to_jsonb(l)-'proof','registration',
   public.api_register_save(jsonb_build_object('operation','context','season_id',l.season_id,'trainer_id',l.trainer_id)));
 elsif op='settle' then
  req:=p_request->'request';
  if l.obligation<>'PHYSICAL_PENDING' or req is null or v_mode not in ('proof','absent')
   or v_mode='proof' and (l.proof is null or req->>'sha256' is distinct from l.result_sha256 or l.proof->>'result_sha256' is distinct from l.result_sha256)
   or v_mode='absent' and (v_side<>'source' or l.proof is not null or l.candidate_sha256 is null or req->>'sha256' is distinct from l.candidate_sha256)
   or req->>'season_id' is distinct from l.season_id::text or req->>'trainer_id' is distinct from l.trainer_id::text
   or req->>'expected_save_id' is distinct from l.save_file_id::text
   or req->'identity_plan'->>'expected_predecessor_id' is distinct from l.identity_revision_id::text
   or req->'save_identity' is distinct from snapshot->'legs'->v_side->'save'->'metadata'->'save_identity'
   then raise sqlstate 'PT409' using message='transfer_registration_mismatch'; end if;
  insert into public.transfer_commit_permits values(txid_current(),aid);
  registered:=public.api_register_save(req||jsonb_build_object('operation','register'));
  select id into rev from public.pokemon_identity_revisions where save_file_id=(registered->>'save_id')::uuid;
  if rev is null or not exists(select 1 from public.season_players where season_id=l.season_id and trainer_id=l.trainer_id and current_save_file_id=(registered->>'save_id')::uuid)
   or v_side='source' and exists(select 1 from public.pokemon_observations where revision_id=rev and pokemon_entity_id=a.target_pokemon_entity_id)
   or v_side='destination' and (select count(*) from public.pokemon_observations where revision_id=rev and pokemon_entity_id=a.target_pokemon_entity_id and outcome='MATCHED')<>1
   then raise sqlstate 'PT409' using message='transfer_identity_not_accepted'; end if;
  update public.item_use_transfer_legs set obligation=case v_mode when 'absent' then 'ABSENT_VERIFIED' else 'VERIFIED' end,
   settled_save_id=(registered->>'save_id')::uuid,released=true,
   candidate_sha256=null,candidate_key=null,candidate_url=null,candidate_size=null where authorization_id=aid and side=v_side;
  if not exists(select 1 from public.item_use_transfer_legs where authorization_id=aid and obligation not in ('VERIFIED','ABSENT_VERIFIED')) then
   update public.item_use_transfers set terminal='COMMITTED',receipt=(select jsonb_object_agg(side,jsonb_build_object('save_id',settled_save_id,'obligation',obligation))
    from public.item_use_transfer_legs where authorization_id=aid)||jsonb_build_object('redemption',x.adjudication->'redemption','pokemon_entity_id',a.target_pokemon_entity_id)
    where authorization_id=aid;
   update public.item_use_authorizations set status='APPLIED_VERIFIED',
    observed_sha256=(select result_sha256 from public.item_use_transfer_legs where authorization_id=aid and side='destination'),
    receipt=(select receipt from public.item_use_transfers where authorization_id=aid),applied_at=now(),updated_at=now(),error_code=null where id=aid;
  end if;
  delete from public.transfer_commit_permits where txid=txid_current();
  return public.transfer_leg_view(aid,v_side);
 end if;
 raise sqlstate 'PT422' using message='invalid_transfer_operation';
end $$;
revoke all on function public.transfer_verifier(jsonb) from public,anon,authenticated,service_role;
grant execute on function public.transfer_verifier(jsonb) to pokeapp_item_verifier;

-- The victim cannot field an adjudicated Pokémon: no team lock while its removal
-- is pending, and never from a save that still holds another trainer's Pokémon.
create function public.guard_team_lock_robbery() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if exists(select 1 from public.item_use_transfer_legs l join public.item_use_transfers x on x.authorization_id=l.authorization_id
   where l.season_id=new.season_id and l.trainer_id=new.trainer_id and l.side='source' and x.adjudicated_at is not null and not l.released)
 then raise sqlstate 'PT409' using message='transfer_removal_pending'; end if;
 -- A kept copy is either bound to the robber's entity or left AMBIGUOUS by the
 -- foreign-collision rule; neither may be fielded from the team.
 if exists(select 1 from public.pokemon_identity_revisions r join public.pokemon_observations o on o.revision_id=r.id
   left join public.pokemon_entities e on e.id=o.pokemon_entity_id
   where r.save_file_id=new.save_file_id and (e.owner_trainer_id<>new.trainer_id
    or o.pokemon_entity_id is null and o.source='party' and public.transfer_foreign_collision(new.season_id,new.trainer_id,o.evidence)))
 then raise sqlstate 'PT409' using message='team_contains_robbed_pokemon'; end if;
 return new;
end $$;
revoke all on function public.guard_team_lock_robbery() from public,anon,authenticated,service_role,pokeapp_item_verifier;
create trigger team_lock_robbery_guard before insert or update of save_file_id on public.team_locks
 for each row execute function public.guard_team_lock_robbery();

comment on column public.item_use_transfers.adjudicated_at is 'Competitive decision (consumption, ownership, flags, voucher). Physical delivery is tracked per leg.';
comment on column public.item_use_transfer_legs.obligation is 'Physical obligation after adjudication; settled only by an independently verified artifact or verified absence.';
commit;
