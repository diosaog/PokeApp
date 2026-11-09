-- 085: Robar y Revivir para toda la Liga (decisiones del propietario, 2026-11-09).
--
-- Robo: sin Team Lock ni jornadas; la víctima y el Pokémon salen de la última
-- partida oficial aceptada. Rotación global persistida en redemptions/robbery_cycles:
-- solo cuentan los robos adjudicados por el verificador (irreversibles); un intento
-- fallido, cancelado o caducado no marca a nadie. Los entrenadores que no pueden ser
-- víctimas (sin partida oficial, inactivos, sin ningún Pokémon robable) no bloquean
-- la ronda. Blindados y Pokémon con menos de 24 h desde su primera observación
-- verificable por el servidor quedan protegidos al preparar y al adjudicar.
-- Revivir: la caja de muertos de cada participante (Caja 7 en ChampionsLocke), con
-- la misma autorización, prueba independiente y consumo único. La muerte histórica
-- y su penalización NET no se tocan: league_death_events es inmutable.
-- Un comodín cuyo intento no llegó a aplicarse vuelve a poder usarse.
-- Sin cambios en filas de puntos, muertes, monedas, compras o Pokémon existentes.
begin;

-- 1. Un intento fallido no agota el comodín ----------------------------------
-- La autorización queda como historia (superseded_at) y la compra admite otra.
alter table public.item_use_authorizations add column superseded_at timestamptz;
alter table public.item_use_authorizations drop constraint item_use_authorizations_purchase_id_key;
create unique index item_use_authorizations_live_purchase
  on public.item_use_authorizations(purchase_id) where superseded_at is null;

-- 2. Caja de muertos oficial --------------------------------------------------
-- Solo para filas nuevas: quien ya participa conserva su valor.
alter table public.season_players alter column dead_box_number set default 7;
create or replace function public.participant_dead_box(sid uuid,tid uuid) returns smallint
language sql stable security invoker set search_path=pg_catalog,public as $$
  select coalesce((select dead_box_number from public.season_players
    where season_id=sid and trainer_id=tid),7::smallint)
$$;

-- 3. Quién y qué se puede robar -----------------------------------------------
-- Partida oficial: la actual, procesada, y la cabeza de identidad apunta a ella.
create function public.robbery_official_save(sid uuid,owner uuid) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.season_players p
   join public.save_files s on s.id=p.current_save_file_id and s.season_id=p.season_id
     and s.trainer_id=p.trainer_id and s.deleted_at is null and s.parser_status='parsed'
   where p.season_id=sid and p.trainer_id=owner
     and s.id=(select r.save_file_id from public.pokemon_identity_revisions r
       where r.season_id=sid and r.trainer_id=owner order by r.revision_number desc limit 1))
$$;

-- Equipo y cajas 1-7 sin la de muertos, en la última revisión oficial. El reloj
-- de 24 h es la primera observación que el servidor verificó: no se confía en la
-- fecha de captura del propio Pokémon (editable fuera del juego) y, si la captura
-- real fue anterior a la primera sincronización, la protección solo dura más.
create function public.robbery_candidates(sid uuid,owner uuid)
returns table(pokemon_entity_id uuid,source text,box_number integer,slot_number integer,
  first_observed_at timestamptz,available_at timestamptz,blocked text)
language sql stable security definer set search_path='' as $$
 with head as (select r.id from public.pokemon_identity_revisions r
    where r.season_id=sid and r.trainer_id=owner order by r.revision_number desc limit 1),
  player as (select p.dead_box_number from public.season_players p where p.season_id=sid and p.trainer_id=owner),
  party as (select count(*) n from public.pokemon_observations o join head on o.revision_id=head.id where o.source='party'),
  seen as (select o.pokemon_entity_id,o.source,o.box_number::integer,o.slot_number::integer,o.evidence,
      coalesce(least(e.created_at,(select min(x.created_at) from public.pokemon_observations x
        where x.pokemon_entity_id=o.pokemon_entity_id)),e.created_at) first_seen,
      exists(select 1 from public.pokemon_entity_flags f left join public.pokemon_flags l on l.id=f.legacy_flag_id
        where f.season_id=sid and f.pokemon_entity_id=e.id and f.flag_type in ('blindado','robado')
          and coalesce(f.flag_value,l.flag_value,false)) shielded
    from head join public.pokemon_observations o on o.revision_id=head.id
    join public.pokemon_entities e on e.id=o.pokemon_entity_id and e.season_id=sid
      and e.owner_trainer_id=owner and e.identity_status='unambiguous'
    cross join player
    where o.outcome in ('NEW','MATCHED')
      and (o.source='party' and o.slot_number between 1 and 6
        or o.source='box' and o.box_number between 1 and 7 and o.box_number<>player.dead_box_number))
 select s.pokemon_entity_id,s.source,s.box_number,s.slot_number,s.first_seen,s.first_seen+interval '24 hours',
   case when s.shielded then 'shielded'
     when coalesce((s.evidence->>'is_egg')::boolean,false) then 'egg'
     when not coalesce((s.evidence->>'source_trainer_match')::boolean,false) then 'foreign_trainer'
     when s.first_seen+interval '24 hours'>clock_timestamp() then 'recent_capture'
     when s.source='party' and (select n from party)<2 then 'last_party_member' end
 from seen s
$$;

-- Víctimas elegibles que faltan en una ronda. Quien no puede ser robado no cuenta.
create function public.robbery_open_victims(sid uuid,cycle bigint) returns bigint
language sql stable security definer set search_path='' as $$
 select count(*) from public.season_players p join public.trainers t on t.id=p.trainer_id
 where p.season_id=sid and p.status='active' and t.globally_enabled
   and public.robbery_official_save(sid,p.trainer_id)
   and exists(select 1 from public.robbery_candidates(sid,p.trainer_id) c where c.blocked is null)
   and not exists(select 1 from public.redemptions r where r.season_id=sid and r.effect_code='steal'
     and r.status='applied' and r.robbery_cycle_number=cycle and r.target_owner_trainer_id=p.trainer_id)
$$;

-- La ronda vigente sin escribir nada: la siguiente si ya no falta nadie.
create function public.robbery_round(sid uuid) returns bigint
language sql stable security definer set search_path='' as $$
 select case when public.robbery_open_victims(sid,c.n)=0 then c.n+1 else c.n end
 from (select coalesce((select cycle_number from public.robbery_cycles where season_id=sid),1::bigint) n) c
$$;

-- 4. Selector de víctima y Pokémon ---------------------------------------------
create function public.api_robbery_board(p_request jsonb) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare sid uuid:=(p_request->>'season_id')::uuid; tid uuid:=(p_request->>'trainer_id')::uuid;
 cyc bigint; voucher boolean; own_game text; rows jsonb;
begin
 if sid is null or tid is null then raise sqlstate 'PT422' using message='invalid_transfer'; end if;
 if not exists(select 1 from public.trainers where id=tid and globally_enabled) then
  raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 if not exists(select 1 from public.season_players where season_id=sid and trainer_id=tid and status='active') then
  raise sqlstate 'PT409' using message='participant_inactive'; end if;
 cyc:=public.robbery_round(sid);
 voucher:=exists(select 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id
   where p.season_id=sid and p.trainer_id=tid and p.status='pending' and p.quantity=1 and i.code='robar_pokemon');
 select s.metadata->'save_identity'->>'game' into own_game from public.season_players p
   join public.save_files s on s.id=p.current_save_file_id where p.season_id=sid and p.trainer_id=tid;
 select coalesce(jsonb_agg(z.item order by z.item->>'display_name'),'[]'::jsonb) into rows from (
  select jsonb_build_object('trainer_id',p.trainer_id,'display_name',t.display_name,'status',st.status,
    'targets',case when voucher and st.status in ('available','no_targets') then
      (select coalesce(jsonb_agg(jsonb_build_object('pokemon_entity_id',c.pokemon_entity_id,'source',c.source,
         'box_number',c.box_number,'slot_number',c.slot_number,'available_at',c.available_at,'blocked',c.blocked)
         order by c.source desc,c.box_number,c.slot_number),'[]'::jsonb)
       from public.robbery_candidates(sid,p.trainer_id) c where c.blocked is distinct from 'foreign_trainer' and c.blocked is distinct from 'egg')
      else '[]'::jsonb end) item
  from public.season_players p join public.trainers t on t.id=p.trainer_id
  cross join lateral (select case
    when not public.robbery_official_save(sid,p.trainer_id) then 'no_save'
    when own_game is not null and (select s.metadata->'save_identity'->>'game' from public.save_files s
      where s.id=p.current_save_file_id) is distinct from own_game then 'other_game'
    when exists(select 1 from public.redemptions r where r.season_id=sid and r.effect_code='steal' and r.status='applied'
      and r.robbery_cycle_number=cyc and r.target_owner_trainer_id=p.trainer_id) then 'already_robbed'
    when exists(select 1 from public.item_use_transfer_legs l where l.season_id=sid and l.trainer_id=p.trainer_id and not l.released) then 'reserved'
    when not exists(select 1 from public.robbery_candidates(sid,p.trainer_id) c where c.blocked is null) then 'no_targets'
    else 'available' end status) st
  where p.season_id=sid and p.trainer_id<>tid and p.status='active' and t.globally_enabled) z;
 return jsonb_build_object('round',cyc,'has_voucher',voucher,'own_official_save',public.robbery_official_save(sid,tid),
   'trainers',rows);
end $$;

-- 5. Preparación del robo ------------------------------------------------------
create function public.transfer_cancel_unstarted(p_aid uuid,p_code text) returns void
language plpgsql security definer set search_path='' as $$
begin
 -- Antes de la adjudicación ningún Launcher puede empezar a aplicar (061).
 update public.item_use_transfers set terminal='CANCELLED'
  where authorization_id=p_aid and terminal is null and adjudicated_at is null;
 if found then
  update public.item_use_transfer_legs set released=true where authorization_id=p_aid;
  update public.item_use_authorizations set status='FAILED_RECOVERABLE',error_code=p_code,updated_at=now() where id=p_aid;
 end if;
end $$;

create function public.transfer_release_expired(sid uuid) returns void
language plpgsql security definer set search_path='' as $$
declare r record;
begin
 for r in select x.authorization_id from public.item_use_transfers x
   join public.item_use_authorizations a on a.id=x.authorization_id
   where a.season_id=sid and x.terminal is null and x.adjudicated_at is null and a.expires_at<=clock_timestamp()
   order by x.authorization_id loop
  perform public.transfer_cancel_unstarted(r.authorization_id,'TRANSFER_EXPIRED');
 end loop;
end $$;

create or replace function public.api_prepare_transfer(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare sid uuid:=(p_request->>'season_id')::uuid; tid uuid:=(p_request->>'trainer_id')::uuid;
 pid uuid:=(p_request->>'purchase_id')::uuid; eid uuid:=(p_request->>'pokemon_entity_id')::uuid;
 op uuid:=(p_request->>'operation_id')::uuid; a public.item_use_authorizations; e public.pokemon_entities;
 donor public.season_players; receiver public.season_players; dhead public.pokemon_identity_revisions; rhead public.pokemon_identity_revisions;
 ds public.save_files; rs public.save_files; obs public.pokemon_observations; cyc bigint; x public.item_use_transfers;
 cand record;
begin
 if op is null then raise sqlstate 'PT422' using message='invalid_transfer'; end if;
 perform 1 from public.trainers where id=tid and globally_enabled for share;
 if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 perform 1 from public.seasons where id=sid for no key update;
 perform 1 from public.season_players where season_id=sid order by id for update;
 perform public.transfer_release_expired(sid);
 select * into a from public.item_use_authorizations where purchase_id=pid and superseded_at is null for update;
 if found then
  select * into x from public.item_use_transfers where authorization_id=a.id;
  if a.trainer_id is not distinct from tid and a.season_id is not distinct from sid and a.operation_id is not distinct from op::text then
   -- Reintento técnico exacto: el mismo recibo, nunca un segundo robo.
   if a.target_pokemon_entity_id is distinct from eid or x.authorization_id is null then
    raise sqlstate 'PT409' using message='transfer_conflict'; end if;
   return jsonb_build_object('authorization_id',a.id,'status',public.transfer_state(a.id));
  end if;
  -- Otro intento con el mismo comodín: solo si el anterior no llegó a nada.
  if a.trainer_id is distinct from tid or a.season_id is distinct from sid or x.terminal is distinct from 'CANCELLED' then
   raise sqlstate 'PT409' using message='transfer_conflict'; end if;
  update public.item_use_authorizations set superseded_at=clock_timestamp(),updated_at=now() where id=a.id;
 end if;
 select * into e from public.pokemon_entities where id=eid and season_id=sid and identity_status='unambiguous' for update;
 if not found then raise sqlstate 'PT409' using message='transfer_target_invalid'; end if;
 if e.owner_trainer_id=tid then raise sqlstate 'PT409' using message='steal_self_target'; end if;
 select * into donor from public.season_players where season_id=sid and trainer_id=e.owner_trainer_id and status='active';
 select * into receiver from public.season_players where season_id=sid and trainer_id=tid and status='active';
 if donor.id is null or receiver.id is null or not exists(select 1 from public.trainers where id=e.owner_trainer_id and globally_enabled) then raise sqlstate 'PT409' using message='participant_inactive'; end if;
 perform 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id where p.id=pid and p.season_id=sid and p.trainer_id=tid and p.status='pending' and p.quantity=1 and i.code='robar_pokemon' for update of p;
 if not found then raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
 if not public.robbery_official_save(sid,donor.trainer_id) then raise sqlstate 'PT409' using message='steal_victim_no_save'; end if;
 if not public.robbery_official_save(sid,tid) then raise sqlstate 'PT409' using message='steal_thief_no_save'; end if;
 select * into dhead from public.pokemon_identity_revisions where season_id=sid and trainer_id=donor.trainer_id order by revision_number desc limit 1;
 select * into rhead from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid order by revision_number desc limit 1;
 select * into ds from public.save_files where id=donor.current_save_file_id;
 select * into rs from public.save_files where id=receiver.current_save_file_id;
 if ds.metadata->'save_identity'->>'game' is distinct from rs.metadata->'save_identity'->>'game' then raise sqlstate 'PT409' using message='transfer_cross_title_forbidden'; end if;
 select * into obs from public.pokemon_observations where revision_id=dhead.id and pokemon_entity_id=eid and outcome in ('NEW','MATCHED');
 if not found then raise sqlstate 'PT409' using message='save_context_changed'; end if;
 select * into cand from public.robbery_candidates(sid,donor.trainer_id) c where c.pokemon_entity_id=eid;
 if not found then raise sqlstate 'PT409' using message='transfer_native_scope_unqualified'; end if;
 if cand.blocked='shielded' then raise sqlstate 'PT409' using message='steal_target_shielded'; end if;
 if cand.blocked='recent_capture' then raise sqlstate 'PT409' using message='steal_target_recent_capture'; end if;
 if cand.blocked='last_party_member' then raise sqlstate 'PT409' using message='steal_target_last_party_member'; end if;
 if cand.blocked is not null then raise sqlstate 'PT409' using message='transfer_target_invalid'; end if;
 cyc:=public.robbery_round(sid);
 if exists(select 1 from public.redemptions where season_id=sid and effect_code='steal' and status='applied'
   and robbery_cycle_number=cyc and target_owner_trainer_id=donor.trainer_id) then raise sqlstate 'PT409' using message='steal_victim_already_robbed'; end if;
 -- A decided robbery stops reserving its trainers once their own side is settled.
 if exists(select 1 from public.item_use_authorizations ia where ia.season_id=sid and ia.superseded_at is null and ia.status<>'APPLIED_VERIFIED'
    and (ia.target_pokemon_entity_id=eid or ia.trainer_id in(tid,donor.trainer_id))
    and ia.status<>'FAILED_RECOVERABLE'
    and not exists(select 1 from public.item_use_transfers tx where tx.authorization_id=ia.id and (tx.terminal='CANCELLED' or tx.adjudicated_at is not null)))
  or exists(select 1 from public.item_use_transfer_legs l where l.season_id=sid and l.trainer_id in(tid,donor.trainer_id) and not l.released)
 then raise sqlstate 'PT409' using message='transfer_reserved'; end if;
 insert into public.item_use_authorizations(operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,effect_code)
 values(op::text,op::text,pid,sid,tid,eid,rs.id,rs.sha256,dhead.id,'steal') returning * into a;
 insert into public.item_use_transfers(authorization_id,donor_id) values(a.id,donor.trainer_id);
 insert into public.item_use_transfer_legs(authorization_id,side,season_id,trainer_id,save_file_id,identity_revision_id,source_sha256) values
 (a.id,'source',sid,donor.trainer_id,ds.id,dhead.id,ds.sha256),(a.id,'destination',sid,tid,rs.id,rhead.id,rs.sha256);
 return jsonb_build_object('authorization_id',a.id,'status','REQUESTED');
end $$;

-- Las mismas comprobaciones al adjudicar: un blindaje posterior o las 24 h pesan.
create or replace function public.transfer_context(p_id uuid) returns jsonb language sql security definer set search_path='' as $$
 select jsonb_build_object('authorization',to_jsonb(a),'entity',to_jsonb(e),'observation',to_jsonb(o),
  'purchase_pending',p.status='pending',
  'eligible',e.identity_status='unambiguous' and e.owner_trainer_id=x.donor_id
   and not exists(select 1 from public.pokemon_entity_flags f left join public.pokemon_flags lf on lf.id=f.legacy_flag_id
     where f.season_id=a.season_id and f.pokemon_entity_id=e.id and f.flag_type in('blindado','robado') and coalesce(f.flag_value,lf.flag_value,false))
   and coalesce((select c.available_at<=clock_timestamp() from public.robbery_candidates(a.season_id,x.donor_id) c where c.pokemon_entity_id=e.id),false),
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

-- El verificador libera lo caducado y cierra lo que no puede planificarse: el
-- comodín no se consume y ambos entrenadores vuelven a sincronizar.
alter function public.transfer_verifier(jsonb) rename to transfer_verifier_v061;
revoke all on function public.transfer_verifier_v061(jsonb) from public,anon,authenticated,service_role,pokeapp_item_verifier;
create function public.transfer_verifier(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare op text:=p_request->>'operation'; aid uuid:=(p_request->>'authorization_id')::uuid;
 a public.item_use_authorizations; x public.item_use_transfers; s uuid; v_code text:=p_request->>'code';
begin
 if op='queue' then
  for s in select distinct ia.season_id from public.item_use_transfers tx
    join public.item_use_authorizations ia on ia.id=tx.authorization_id
    where tx.terminal is null and tx.adjudicated_at is null and ia.expires_at<=clock_timestamp() loop
   perform 1 from public.seasons where id=s for no key update;
   perform 1 from public.season_players where season_id=s order by id for update;
   perform public.transfer_release_expired(s);
  end loop;
 elsif op='reject_request' then
  select * into a from public.item_use_authorizations where id=aid;
  if a.id is null then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
  perform 1 from public.trainers where id in(a.trainer_id,(select donor_id from public.item_use_transfers where authorization_id=aid)) order by id for share;
  perform 1 from public.seasons where id=a.season_id for no key update;
  perform 1 from public.season_players where season_id=a.season_id order by id for update;
  select * into x from public.item_use_transfers where authorization_id=aid for update;
  if x.authorization_id is null then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
  perform public.transfer_cancel_unstarted(aid,case when v_code ~ '^[A-Z0-9_]{1,64}$' then v_code else 'TRANSFER_PLAN_REJECTED' end);
  return jsonb_build_object('status',public.transfer_state(aid));
 end if;
 return public.transfer_verifier_v061(p_request);
end $$;
revoke all on function public.transfer_verifier(jsonb) from public,anon,authenticated,service_role;
grant execute on function public.transfer_verifier(jsonb) to pokeapp_item_verifier;

-- Por qué se canceló, para explicarlo al entrenador.
create or replace function public.api_transfer_list(p_request jsonb) returns jsonb language plpgsql stable security definer set search_path='' as $$
declare sid uuid:=(p_request->>'season_id')::uuid; tid uuid:=(p_request->>'trainer_id')::uuid;
begin
 if sid is null or tid is null then raise sqlstate 'PT422' using message='invalid_transfer'; end if;
 if not exists(select 1 from public.trainers where id=tid and globally_enabled) then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 return coalesce((select jsonb_agg(q.item order by q.created_at desc) from (
  select a.created_at,jsonb_build_object(
   'authorization_id',a.id,'side',l.side,'status',public.transfer_state(a.id),
   'obligation',public.transfer_obligation(a.id,l.side),
   'purchase_id',case when l.side='destination' and a.superseded_at is null then a.purchase_id end,
   'pokemon_entity_id',a.target_pokemon_entity_id,'source_sha256',l.source_sha256,
   'claimed',l.claim_id is not null,'apply_started',l.apply_started,'result_sha256',l.result_sha256,
   'verified',l.proof is not null,'accepted_save_id',coalesce(l.settled_save_id::text,x.receipt->l.side->>'save_id'),
   'pair_id',x.plans->l.side->'intent'->'mutation'->>'pair_id',
   'intent',case when x.adjudicated_at is not null and l.obligation='PHYSICAL_PENDING' then x.plans->l.side->'intent' end,
   'reason',case when l.side='destination' then a.error_code end,
   'expires_at',a.expires_at,'created_at',a.created_at) item
  from public.item_use_transfer_legs l
  join public.item_use_authorizations a on a.id=l.authorization_id
  join public.item_use_transfers x on x.authorization_id=a.id
  where l.season_id=sid and l.trainer_id=tid
  order by a.created_at desc limit 20) q),'[]'::jsonb);
end $$;

-- 6. Consumo: la rotación ignora a quien no puede ser víctima --------------------
create or replace function public.api_redeem_purchase(
  p_season_id uuid, p_trainer_id uuid, p_purchase_id uuid, p_pokemon_entity_id uuid,
  p_idempotency_key text, p_expected_revision_id uuid
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare
  v_player public.season_players;
  v_victim public.season_players;
  v_purchase public.purchases;
  v_redemption public.redemptions;
  v_entity public.pokemon_entities;
  v_head public.pokemon_identity_revisions;
  v_observation public.pokemon_observations;
  v_cycle public.robbery_cycles;
  v_active uuid[];
  v_code text;
  v_effect text;
  v_physical text;
  v_gift uuid;
  v_voucher uuid;
  v_id uuid := gen_random_uuid();
  v_event uuid := gen_random_uuid();
  v_now timestamptz := transaction_timestamp();
  v_receipt jsonb;
begin
  if p_idempotency_key is null or length(p_idempotency_key) not between 1 and 128
    or p_idempotency_key !~ '^[!-~]+$' or p_pokemon_entity_id is null then
    raise sqlstate 'PT409' using message='invalid_redemption_request'; end if;
  perform 1 from public.trainers where id=p_trainer_id and globally_enabled for share;
  if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
  -- Serialize the cycle before any wallet lock. NO KEY UPDATE remains compatible
  -- with FK KEY SHARE locks taken by an in-flight identity reconciliation.
  perform 1 from public.seasons where id=p_season_id for no key update;
  if not found then raise sqlstate 'PT404' using message='season_not_found'; end if;
  v_active := array[]::uuid[];
  for v_player in select * from public.season_players where season_id=p_season_id order by id for update loop
    if v_player.status='active' then v_active:=array_append(v_active,v_player.trainer_id); end if;
  end loop;
  select * into v_player from public.season_players where season_id=p_season_id and trainer_id=p_trainer_id;
  if not found or v_player.status<>'active' then
    raise sqlstate 'PT403' using message='participant_inactive'; end if;
  select * into v_purchase from public.purchases where id=p_purchase_id
    and season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found then raise sqlstate 'PT404' using message='purchase_not_found'; end if;
  select * into v_redemption from public.redemptions where purchase_id=v_purchase.id;
  if found then
    if v_redemption.idempotency_key is distinct from p_idempotency_key then
      raise sqlstate 'PT409' using message='purchase_already_redeemed'; end if;
    if v_redemption.target_pokemon_entity_id is distinct from p_pokemon_entity_id then
      raise sqlstate 'PT409' using message='idempotency_conflict'; end if;
    return v_redemption.receipt;
  end if;
  if v_purchase.status<>'pending' or v_purchase.quantity<>1 then
    raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
  select code into v_code from public.shop_items where id=v_purchase.shop_item_id for share;
  v_effect := case v_code when 'blindar_pokemon' then 'shield' when 'revivir_pokemon' then 'revive'
    when 'robbery_shield_voucher' then 'robbery_shield' when 'robar_pokemon' then 'steal' end;
  if v_effect is null then raise sqlstate 'PT409' using message='redemption_not_supported'; end if;
  select * into v_entity from public.pokemon_entities where id=p_pokemon_entity_id
    and season_id=p_season_id for update;
  if not found then raise sqlstate 'PT409' using message='pokemon_not_owned'; end if;
  if v_effect='steal' then
    if v_entity.owner_trainer_id=p_trainer_id then
      raise sqlstate 'PT409' using message='steal_self_target'; end if;
    select * into v_victim from public.season_players
      where season_id=p_season_id and trainer_id=v_entity.owner_trainer_id;
    if not found or not (v_victim.trainer_id=any(v_active)) then
      raise sqlstate 'PT409' using message='steal_victim_ineligible'; end if;
  elsif v_entity.owner_trainer_id<>p_trainer_id then
    raise sqlstate 'PT409' using message='pokemon_not_owned';
  end if;
  select * into v_head from public.pokemon_identity_revisions
    where season_id=p_season_id and trainer_id=v_entity.owner_trainer_id
    order by revision_number desc limit 1 for share;
  if not found or v_entity.identity_status<>'unambiguous' then
    raise sqlstate 'PT409' using message='pokemon_identity_ambiguous'; end if;
  if v_head.id is distinct from p_expected_revision_id then
    raise sqlstate 'PT409' using message='pokemon_target_stale'; end if;
  select * into v_observation from public.pokemon_observations
    where revision_id=v_head.id and pokemon_entity_id=v_entity.id
      and trainer_id=v_entity.owner_trainer_id and season_id=p_season_id
      and outcome in ('NEW','MATCHED') for share;
  if not found then raise sqlstate 'PT409' using message='pokemon_identity_ambiguous'; end if;
  if v_effect='steal' and v_observation.source='box' and (v_observation.box_number not between 1 and 7
      or v_observation.box_number=public.participant_dead_box(p_season_id,v_observation.trainer_id)) then
    raise sqlstate 'PT409' using message='steal_target_ineligible'; end if;
  if v_observation.source='box' and v_observation.box_number not between 1 and greatest(8,public.participant_dead_box(p_season_id,v_observation.trainer_id)) then
    raise sqlstate 'PT409' using message='invalid_pokemon_target'; end if;
  if v_effect='revive' and not (v_observation.source='box' and v_observation.box_number=public.participant_dead_box(p_season_id,v_observation.trainer_id)) then
    raise sqlstate 'PT409' using message='pokemon_not_revivable'; end if;
  if v_effect='revive' and exists(select 1 from public.redemptions r
    join public.pokemon_identity_revisions used on used.id=r.identity_revision_id
    where r.season_id=p_season_id and r.trainer_id=p_trainer_id and r.effect_code='revive' and r.status='applied'
      and r.target_pokemon_entity_id=v_entity.id and not exists(
        select 1 from public.pokemon_observations alive join public.pokemon_identity_revisions later on later.id=alive.revision_id
        where alive.season_id=p_season_id and alive.trainer_id=p_trainer_id and alive.pokemon_entity_id=v_entity.id
          and later.revision_number>used.revision_number and later.revision_number<=v_head.revision_number
          and (alive.source='party' or (alive.source='box' and alive.box_number<>public.participant_dead_box(p_season_id,p_trainer_id))))) then
    raise sqlstate 'PT409' using message='pokemon_revive_pending'; end if;
  if v_effect<>'revive' and exists (
    select 1 from public.pokemon_entity_flags f left join public.pokemon_flags l on l.id=f.legacy_flag_id
    where f.season_id=p_season_id and f.pokemon_entity_id=v_entity.id and f.flag_type='blindado'
      and coalesce(f.flag_value,l.flag_value,false)
  ) then
    if v_effect='steal' then raise sqlstate 'PT409' using message='steal_target_shielded'; end if;
    raise sqlstate 'PT409' using message='pokemon_already_shielded';
  end if;
  if v_effect='steal' and not exists(select 1 from public.robbery_candidates(p_season_id,v_entity.owner_trainer_id) c
      where c.pokemon_entity_id=v_entity.id and c.available_at<=clock_timestamp()) then
    raise sqlstate 'PT409' using message='steal_target_recent_capture'; end if;

  if v_effect='steal' then
    insert into public.robbery_cycles(season_id) values(p_season_id) on conflict do nothing;
    select * into v_cycle from public.robbery_cycles where season_id=p_season_id for update;
    -- The round closes when no eligible victim is missing (085), also before use.
    if public.robbery_open_victims(p_season_id,v_cycle.cycle_number)=0 then
      update public.robbery_cycles set cycle_number=cycle_number+1,history_watermark_id=last_redemption_id
        where season_id=p_season_id returning * into v_cycle;
      update public.trainer_flags set flag_value=false,payload='{}' where season_id=p_season_id
        and flag_type='robbed' and trainer_id=any(v_active);
    end if;
    if exists (select 1 from public.redemptions where season_id=p_season_id
      and robbery_cycle_number=v_cycle.cycle_number and target_owner_trainer_id=v_entity.owner_trainer_id) then
      raise sqlstate 'PT409' using message='steal_victim_already_robbed'; end if;
    select id into v_voucher from public.shop_items where code='robbery_shield_voucher'
      and acquisition_mode='reward_only' for share;
    if not found then raise sqlstate 'PT409' using message='steal_cycle_conflict'; end if;
    v_gift:=gen_random_uuid();
  end if;
  v_physical := case when v_effect in ('revive','steal') then 'pending' else 'not_required' end;
  v_receipt := jsonb_build_object('redemption_id',v_id,'purchase_id',v_purchase.id,
    'season_id',p_season_id,'trainer_id',p_trainer_id,'shop_item_id',v_purchase.shop_item_id,
    'effect_code',v_effect,'target_pokemon_entity_id',v_entity.id,'target_owner_trainer_id',v_entity.owner_trainer_id,
    'purchase_status','used','redemption_status','applied','physical_effect_status',v_physical,
    'requested_at',v_now,'redeemed_at',v_now,'physical_effect_completed_at',null,
    'activity_event_id',v_event,'gift_purchase_id',v_gift);
  insert into public.redemptions(id,purchase_id,season_id,trainer_id,season_player_id,shop_item_id,
    redemption_type,status,payload,redeemed_at,idempotency_key,effect_code,target_pokemon_entity_id,
    target_owner_trainer_id,identity_revision_id,physical_effect_status,requested_at,activity_event_id,receipt,
    gift_purchase_id,robbery_cycle_number)
  values(v_id,v_purchase.id,p_season_id,p_trainer_id,v_player.id,v_purchase.shop_item_id,
    v_effect,'applied',jsonb_build_object('item_code',v_code,'effect_code',v_effect,
      'target_pokemon_entity_id',v_entity.id,'target_owner_trainer_id',v_entity.owner_trainer_id),v_now,
    p_idempotency_key,v_effect,v_entity.id,v_entity.owner_trainer_id,v_head.id,v_physical,v_now,v_event,v_receipt,
    v_gift,v_cycle.cycle_number);
  insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)
    values(p_season_id,v_entity.owner_trainer_id,v_entity.id,'blindado',true)
    on conflict(season_id,pokemon_entity_id,flag_type) do update
      set flag_value=true,legacy_flag_id=null,flag_timestamp=null,flag_trainer_id=null;
  if v_effect in ('revive','steal') then
    insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_timestamp)
      values(p_season_id,v_entity.owner_trainer_id,v_entity.id,
        case v_effect when 'revive' then 'revivido_at' else 'robado_at' end,v_now)
      on conflict(season_id,pokemon_entity_id,flag_type) do update
        set flag_timestamp=v_now,flag_value=null,legacy_flag_id=null,flag_trainer_id=null;
  end if;
  if v_effect in ('steal','robbery_shield') then
    insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)
      values(p_season_id,v_entity.owner_trainer_id,v_entity.id,
        case v_effect when 'steal' then 'robado' else 'blindaje_por_robo' end,true)
      on conflict(season_id,pokemon_entity_id,flag_type) do update
        set flag_value=true,legacy_flag_id=null,flag_timestamp=null,flag_trainer_id=null;
  end if;
  if v_effect='steal' then
    insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_trainer_id)
      values(p_season_id,v_entity.owner_trainer_id,v_entity.id,'robado_from',v_entity.owner_trainer_id)
      on conflict(season_id,pokemon_entity_id,flag_type) do update
        set flag_trainer_id=excluded.flag_trainer_id,flag_value=null,flag_timestamp=null,legacy_flag_id=null;
    insert into public.trainer_flags(season_id,trainer_id,season_player_id,flag_type,flag_value,payload)
      values(p_season_id,v_victim.trainer_id,v_victim.id,'robbed',true,
        jsonb_build_object('robbed_at',v_now,'robbed_by',p_trainer_id,'robbed_source','live',
          'redemption_id',v_id,'cycle_number',v_cycle.cycle_number))
      on conflict(season_id,trainer_id,flag_type) do update set flag_value=true,payload=excluded.payload;
    update public.robbery_cycles set last_redemption_id=v_id where season_id=p_season_id;
    if public.robbery_open_victims(p_season_id,v_cycle.cycle_number)=0 then
      update public.robbery_cycles set cycle_number=cycle_number+1,history_watermark_id=v_id where season_id=p_season_id;
      update public.trainer_flags set flag_value=false,payload='{}' where season_id=p_season_id
        and flag_type='robbed' and trainer_id=any(v_active);
    end if;
    insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,
      quantity,unit_price,status,acquisition_type,origin_redemption_id)
      values(v_gift,p_season_id,p_trainer_id,v_player.id,v_voucher,1,0,'pending','reward',v_id);
  end if;
  update public.purchases set status='used' where id=v_purchase.id;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,payload)
    values(v_event,p_season_id,'REDEMPTION_USED',p_trainer_id,p_trainer_id,'owner',
      'redemption_used:'||v_id::text,v_receipt);
  return v_receipt;
end $$;

-- 7. Revivir sobre la caja de muertos del participante ---------------------------
create or replace function public.api_prepare_item_use(
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
    where purchase_id=p_purchase_id and superseded_at is null for update;
  if found then
    if v_existing.trainer_id<>p_trainer_id or v_existing.season_id<>p_season_id then
      raise sqlstate 'PT409' using message='item_use_conflict'; end if;
    if v_existing.idempotency_key=p_idempotency_key and v_existing.operation_id=p_operation_id
       and v_existing.target_pokemon_entity_id=p_pokemon_entity_id
       and v_existing.save_file_id=p_save_file_id and v_existing.save_sha256=p_save_sha256 then
      return to_jsonb(v_existing)-'claim_id';
    end if;
    -- Otro intento con el mismo comodín: solo si el anterior no llegó a aplicarse
    -- o caducó. Nunca dos aplicaciones de un mismo objetivo sobre la misma partida:
    -- el nuevo exige los bytes exactos de la partida aceptada ahora.
    if v_existing.status='FAILED_RECOVERABLE' or (v_existing.status='PREPARED' and v_existing.claim_id is null)
       or (v_existing.status<>'APPLIED_VERIFIED' and v_existing.expires_at<=clock_timestamp()) then
      update public.item_use_authorizations set superseded_at=clock_timestamp(),status='FAILED_RECOVERABLE',
        error_code=coalesce(error_code,'ITEM_USE_SUPERSEDED'),updated_at=now() where id=v_existing.id;
    else
      raise sqlstate 'PT409' using message='item_use_in_progress';
    end if;
  end if;
  select * into v_purchase from public.purchases where id=p_purchase_id
    and season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found then raise sqlstate 'PT404' using message='purchase_not_found'; end if;
  if v_purchase.status<>'pending' or v_purchase.quantity<>1 then
    raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
  select code into v_code from public.shop_items where id=v_purchase.shop_item_id for share;
  v_effect:=case v_code when 'revivir_pokemon' then 'revive' when 'robar_pokemon' then 'steal' end;
  if v_effect is null then raise sqlstate 'PT409' using message='item_use_not_required'; end if;
  -- Theft has its own two-save flow (api_prepare_transfer).
  if v_effect='steal' then raise sqlstate 'PT409' using message='item_use_unavailable'; end if;
  select * into v_save from public.save_files where id=p_save_file_id
    and season_id=p_season_id and trainer_id=p_trainer_id and deleted_at is null;
  if not found or v_save.sha256<>p_save_sha256 or v_save.parser_status<>'parsed'
     or v_player.current_save_file_id is distinct from v_save.id then
    raise sqlstate 'PT409' using message='save_context_changed'; end if;
  select * into v_entity from public.pokemon_entities where id=p_pokemon_entity_id
    and season_id=p_season_id for share;
  if not found then raise sqlstate 'PT409' using message='pokemon_target_invalid'; end if;
  if v_entity.owner_trainer_id<>p_trainer_id then
    raise sqlstate 'PT409' using message='pokemon_not_owned'; end if;
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
  if not (v_observation.source='box' and v_observation.box_number=v_player.dead_box_number) then
    raise sqlstate 'PT409' using message='pokemon_not_revivable'; end if;
  -- Do not let two entitlements authorize separate physical mutations of the
  -- same observation, including expired/uncertain attempts awaiting reconciliation.
  if exists(select 1 from public.item_use_authorizations where superseded_at is null and
    target_pokemon_entity_id=p_pokemon_entity_id and identity_revision_id=v_head.id) then
    raise sqlstate 'PT409' using message='item_use_conflict'; end if;
  insert into public.item_use_authorizations(
    operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,
    save_file_id,save_sha256,identity_revision_id,effect_code,status,expires_at)
  values(p_operation_id,p_idempotency_key,p_purchase_id,p_season_id,p_trainer_id,
    p_pokemon_entity_id,p_save_file_id,p_save_sha256,v_head.id,v_effect,'PREPARED',
    clock_timestamp()+interval '24 hours')
  returning * into v_row;
  return to_jsonb(v_row)-'claim_id';
exception when unique_violation then
  raise sqlstate 'PT409' using message='item_use_conflict';
end $$;

create or replace function public.api_list_item_uses(p_season_id uuid,p_trainer_id uuid)
returns jsonb language sql security invoker set search_path='' as $$
  select coalesce(jsonb_agg(to_jsonb(a)-'claim_id' order by a.updated_at desc),'[]'::jsonb)
  from public.item_use_authorizations a
  where a.season_id=p_season_id and a.trainer_id=p_trainer_id and a.superseded_at is null;
$$;

-- El verificador deriva el plan de la caja de muertos del propio participante.
create or replace function public.item_verifier_context(aid uuid) returns jsonb
language sql security definer set search_path='' as $$
 select jsonb_build_object('authorization',to_jsonb(a),'entity',to_jsonb(e),'observation',to_jsonb(o),'save',to_jsonb(s),
  'current_save_id',p.current_save_file_id,'head_id',h.id,'trainer_enabled',t.globally_enabled,
  'participant_active',p.status='active','purchase_pending',buy.status='pending','purchase_effect',
  case when i.code='revivir_pokemon' then 'revive' else 'unsupported' end,'dead_box_number',p.dead_box_number)
 from public.item_use_authorizations a
 join public.season_players p on p.season_id=a.season_id and p.trainer_id=a.trainer_id
 join public.trainers t on t.id=a.trainer_id
 join public.purchases buy on buy.id=a.purchase_id join public.shop_items i on i.id=buy.shop_item_id
 join public.pokemon_entities e on e.id=a.target_pokemon_entity_id
 join public.pokemon_observations o on o.revision_id=a.identity_revision_id and o.pokemon_entity_id=e.id
 join public.save_files s on s.id=a.save_file_id
 cross join lateral(select r.id from public.pokemon_identity_revisions r where r.season_id=a.season_id and r.trainer_id=a.trainer_id order by capture_sequence desc limit 1) h
 where a.id=aid and a.superseded_at is null;
$$;

-- Lo que el Launcher necesita: compras, partida aceptada y muertos revividos.
create function public.api_revive_board(p_request jsonb) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare sid uuid:=(p_request->>'season_id')::uuid; tid uuid:=(p_request->>'trainer_id')::uuid;
 p public.season_players; s public.save_files; head public.pokemon_identity_revisions;
begin
 if sid is null or tid is null then raise sqlstate 'PT422' using message='invalid_item_use_request'; end if;
 if not exists(select 1 from public.trainers where id=tid and globally_enabled) then
  raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 select * into p from public.season_players where season_id=sid and trainer_id=tid;
 if not found or p.status<>'active' then raise sqlstate 'PT403' using message='participant_inactive'; end if;
 if public.robbery_official_save(sid,tid) then
  select * into s from public.save_files where id=p.current_save_file_id;
  select * into head from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid order by revision_number desc limit 1;
 end if;
 return jsonb_build_object('dead_box_number',p.dead_box_number,
  'save',case when s.id is null then null else jsonb_build_object('id',s.id,'sha256',s.sha256) end,
  'purchases',coalesce((select jsonb_agg(jsonb_build_object('id',b.id,'purchased_at',b.purchased_at,
     'authorization',(select jsonb_build_object('id',a.id,'status',a.status,'target_pokemon_entity_id',a.target_pokemon_entity_id,
        'operation_id',a.operation_id,'expires_at',a.expires_at)
       from public.item_use_authorizations a where a.purchase_id=b.id and a.superseded_at is null))
     order by b.purchased_at,b.id)
    from public.purchases b join public.shop_items i on i.id=b.shop_item_id
    where b.season_id=sid and b.trainer_id=tid and b.status='pending' and b.quantity=1 and i.code='revivir_pokemon'),'[]'::jsonb),
  'targets',coalesce((select jsonb_agg(jsonb_build_object('pokemon_entity_id',o.pokemon_entity_id,'slot_number',o.slot_number) order by o.slot_number)
    from public.pokemon_observations o join public.pokemon_entities e on e.id=o.pokemon_entity_id
    where head.id is not null and o.revision_id=head.id and o.source='box' and o.box_number=p.dead_box_number
      and o.outcome in ('NEW','MATCHED') and e.owner_trainer_id=tid and e.identity_status='unambiguous'
      and not coalesce((o.evidence->>'is_egg')::boolean,false)
      and not exists(select 1 from public.redemptions r join public.pokemon_identity_revisions used on used.id=r.identity_revision_id
        where r.season_id=sid and r.trainer_id=tid and r.effect_code='revive' and r.status='applied'
          and r.target_pokemon_entity_id=e.id and used.revision_number<=head.revision_number
          and not exists(select 1 from public.pokemon_observations alive join public.pokemon_identity_revisions later on later.id=alive.revision_id
            where alive.season_id=sid and alive.trainer_id=tid and alive.pokemon_entity_id=e.id
              and later.revision_number>used.revision_number and later.revision_number<=head.revision_number
              and (alive.source='party' or alive.box_number<>p.dead_box_number)))),'[]'::jsonb));
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.robbery_official_save(uuid,uuid)'::regprocedure,
    'public.robbery_candidates(uuid,uuid)'::regprocedure,
    'public.robbery_open_victims(uuid,bigint)'::regprocedure,
    'public.robbery_round(uuid)'::regprocedure,
    'public.api_robbery_board(jsonb)'::regprocedure,
    'public.api_revive_board(jsonb)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,pokeapp_item_verifier',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
  foreach f in array array[
    'public.transfer_cancel_unstarted(uuid,text)'::regprocedure,
    'public.transfer_release_expired(uuid)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role,pokeapp_item_verifier',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
