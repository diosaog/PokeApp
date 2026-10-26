-- Phase26B: owner decision — team Pokémon can be stolen. LOCAL ONLY.
-- Same function as 058 with the origin scope widened from boxes 1-7 to also
-- party slots 1-6; every other rule (shield, robbed, cycle, purchase) unchanged.
begin;
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
 select * into obs from public.pokemon_observations where revision_id=dhead.id and pokemon_entity_id=eid and outcome in ('NEW','MATCHED');
 if not found or not (obs.source='box' and obs.box_number between 1 and 7 or obs.source='party' and obs.slot_number between 1 and 6) then raise sqlstate 'PT409' using message='transfer_native_scope_unqualified'; end if;
 if exists(select 1 from public.pokemon_entity_flags f left join public.pokemon_flags l on l.id=f.legacy_flag_id where f.season_id=sid and f.pokemon_entity_id=eid and f.flag_type in ('blindado','robado') and coalesce(f.flag_value,l.flag_value,false)) then raise sqlstate 'PT409' using message='steal_target_shielded'; end if;
 select coalesce((select cycle_number from public.robbery_cycles where season_id=sid),1) into cyc;
 -- Match025 pre-check reset semantics, without changing the cursor before use.
 if not exists(select 1 from public.season_players sp join public.trainers t on t.id=sp.trainer_id where sp.season_id=sid and sp.status='active' and t.globally_enabled and not exists(select 1 from public.redemptions r where r.season_id=sid and r.robbery_cycle_number=cyc and r.target_owner_trainer_id=sp.trainer_id)) then cyc:=cyc+1; end if;
 if exists(select 1 from public.redemptions where season_id=sid and robbery_cycle_number=cyc and target_owner_trainer_id=donor.trainer_id) then raise sqlstate 'PT409' using message='steal_victim_already_robbed'; end if;
 if exists(select 1 from public.item_use_authorizations where season_id=sid and (target_pokemon_entity_id=eid or trainer_id in(tid,donor.trainer_id)) and status<>'APPLIED_VERIFIED' and not exists(select 1 from public.item_use_transfers x where x.authorization_id=item_use_authorizations.id and x.terminal='CANCELLED')) then raise sqlstate 'PT409' using message='transfer_reserved'; end if;
 insert into public.item_use_authorizations(operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,effect_code)
 values(op::text,op::text,pid,sid,tid,eid,rs.id,rs.sha256,dhead.id,'steal') returning * into a;
 insert into public.item_use_transfers(authorization_id,donor_id) values(a.id,donor.trainer_id);
 insert into public.item_use_transfer_legs(authorization_id,side,season_id,trainer_id,save_file_id,identity_revision_id,source_sha256) values
 (a.id,'source',sid,donor.trainer_id,ds.id,dhead.id,ds.sha256),(a.id,'destination',sid,tid,rs.id,rhead.id,rs.sha256);
 return jsonb_build_object('authorization_id',a.id,'status','PREPARING');
end $$;
commit;
