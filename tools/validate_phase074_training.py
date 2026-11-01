"""Rollback-only virtual training SQL acceptance in an isolated caller cluster.

Uses synthetic parsed observations. The independently verified native-byte
matrix and HTTP proof boundary are separate gates, never impersonated here.
"""

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
from uuid import uuid4

from app.application.save_ingestion import registration_request
from app.domain.pokemon_identity import digest, trusted_native_identity


def literal(value):
    return "'" + json.dumps(value, separators=(",", ":")).replace("'", "''") + "'::jsonb"


def validate(pg, *, capture_only=False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from test_phase074_training import observation, VERSION

    sid, oldsid, tid, pid, purchase, operation, released = (str(uuid4()) for _ in range(7))
    source_hash, output_hash, future_hash = "a" * 64, "b" * 64, "c" * 64
    source, output = observation(), observation(ivs=(31, 2, 3, 4, 5, 6))
    initial = registration_request(sid, tid, source_hash, None, source, VERSION, {"head": None, "entities": []})
    entity = initial["identity_plan"]["bindings"][0]["pokemon_entity_id"]
    before = initial["identity_plan"]["bindings"][0]["evidence"]
    after = asdict(trusted_native_identity(output.party[0].identity, trainer=output.trainer, is_egg=False))
    context = {"head": {"id": str(uuid4()), "capture_stream_id": initial["identity_plan"]["capture_stream_id"], "capture_sequence": 1},
        "entities": [{"id": entity, "identity_status": "unambiguous", "initial_evidence": after}]}
    result = registration_request(sid, tid, output_hash, initial["save_id"], output, VERSION, context)
    future_context = deepcopy(context)
    future_context["head"]["capture_sequence"] = 2
    future = registration_request(sid, tid, future_hash, result["save_id"], output, VERSION, future_context)
    mutation = {"kind": "virtual_training", "item_code": "chapa_plateada", "attempt": operation, "location": "party", "box_index": None,
        "slot_index": 0, "expected_pokemon_sha256": "d" * 64, "expected_nature": 0,
        "expected_ivs": [17, 2, 3, 4, 5, 6], "nature_id": None, "stat": "hp"}
    intent = {"game": "Y", "trainer_key": "d" * 64, "expected_sha256": source_hash, "mutation": mutation}
    request = {"operation": "reserve", "season_id": sid, "trainer_id": tid, "operation_id": operation,
        "purchase_id": purchase, "pokemon_entity_id": entity, "save_file_id": initial["save_id"],
        "request_hash": "e" * 64, "intent": intent}
    complete = {"operation": "complete", "season_id": sid, "trainer_id": tid, "operation_id": operation,
        "output_sha256": output_hash, "before_evidence": before, "after_evidence": after,
        "observed_evidence": after, "observed_candidate_key": digest(after),
        "after_candidate_key": digest(after), "registration": result, "result": {"native_verified": True}}
    sql = f"""
begin;
-- Fixtures never commit; existing real-copy rows remain untouched.
update public.seasons set status='draft' where status='active';
insert into public.trainers(id,display_name,slug,is_admin,auth_user_id) values('{tid}','074 Fixture','074-'||'{tid}',true,gen_random_uuid());
insert into public.seasons(id,name,status,started_at,created_by_trainer_id,discarded_at)
 values('{oldsid}','074 original discarded','discarded',now(),'{tid}',now()),('{sid}','074 current Y','active',now(),'{tid}',null);
insert into public.season_players(id,season_id,trainer_id,status)
 values('{pid}','{sid}','{tid}','active'),(gen_random_uuid(),'{oldsid}','{tid}','active');
insert into public.season_player_stats(season_player_id,season_id,trainer_id)
 select id,season_id,trainer_id from public.season_players where trainer_id='{tid}' on conflict do nothing;
insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type)
 select season_id,trainer_id,id,100,'admin_adjustment' from public.season_players where trainer_id='{tid}';
insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,acquisition_type,status)
 select '{purchase}','{oldsid}','{tid}',p.id,i.id,1,6,'paid','pending' from public.season_players p
 cross join public.shop_items i where p.season_id='{oldsid}' and p.trainer_id='{tid}' and i.code='chapa_plateada';
select public.api_register_save({literal(initial)}||jsonb_build_object('operation','register'));
set local role service_role;
do $$ declare ctx jsonb; r jsonb; reservation jsonb; completion jsonb; head uuid; receipt jsonb; original jsonb; oldbag uuid=gen_random_uuid();
begin
 ctx=public.api_training_operation(jsonb_build_object('operation','context','season_id','{sid}','trainer_id','{tid}'));
 assert jsonb_array_length(ctx->'observations')=1,'one eligible own non-egg target';
 assert ctx#>>'{{purchases,0,purchase_season_id}}'='{oldsid}','old discarded purchase remains usable in current Y';
 assert ctx#>>'{{purchases,0,purchase_id}}'='{purchase}','same old paidpurchase';
 head=(ctx#>>'{{revision,id}}')::uuid;
 reservation={literal(request)}||jsonb_build_object('identity_revision_id',head);
 insert into public.item_deliveries(purchase_id,season_id,trainer_id,operation_id,kind,item_code,game_item_id,game,status)
  values('{purchase}','{oldsid}','{tid}',oldbag,'bag','bottle_cap',795,'US','RESERVED');
 begin
  perform public.api_training_operation(reservation);
  raise exception 'legacy uncertain bag reservation bypassed';
 exception when sqlstate 'PT409' then assert sqlerrm='training_save_busy',sqlerrm; end;
 perform public.api_release_item_delivery('{oldsid}','{tid}',oldbag);
 r=public.api_training_operation(reservation);
 assert r->>'status'='RESERVED' and r->>'season_id'='{sid}' and r->>'purchase_season_id'='{oldsid}','bound target and source purchase seasons';
 assert (select status from public.purchases where id='{purchase}')='pending','reservation spends nothing';
 assert public.lifecycle_physical_open('{sid}'),'existing lifecycle guard includes training';
 begin
  update public.season_players set dead_box_number=7 where id='{pid}';
  raise exception 'dead-box context changed during pending write';
 exception when sqlstate 'PT409' then assert sqlerrm='training_save_busy',sqlerrm; end;
 begin
  update public.season_players set status='retired',status_effective_matchday_number=2 where id='{pid}';
  raise exception 'participant retired during pending write';
 exception when sqlstate 'PT409' then assert sqlerrm='training_save_busy',sqlerrm; end;
 begin
  update public.seasons set status='discarded',discarded_at=now() where id='{sid}';
  raise exception 'season cancelled during pending write';
 exception when sqlstate 'PT409' then assert sqlerrm='training_save_busy',sqlerrm; end;
 assert public.api_training_operation(reservation)=r,'exact reserve replay';
 begin
  perform public.api_training_operation(jsonb_set(reservation,'{{request_hash}}',to_jsonb(repeat('f',64))));
  raise exception 'changed choice replay accepted';
 exception when sqlstate 'PT409' then assert sqlerrm='training_idempotency_conflict',sqlerrm; end;
 begin
  perform public.api_register_save({literal(future)}||jsonb_build_object('operation','register'));
  raise exception 'ordinary sync bypassed reservation';
 exception when sqlstate 'PT409' then assert sqlerrm='training_reconciliation_required',sqlerrm; end;
 begin
  perform public.admin_purchase_resolve('{tid}','{oldsid}','{purchase}','purchase_cancel',gen_random_uuid(),repeat('f',64),'Synthetic cancellation blocked');
  raise exception 'cancelled reserved purchase';
 exception when others then assert sqlerrm='purchase_linked_to_save_operation',sqlerrm; end;
 begin
  perform public.api_reserve_item_delivery('{oldsid}','{tid}','{purchase}',gen_random_uuid(),'bottle_cap',795,'Y');
  raise exception 'virtualcap delivered to bag';
 exception when sqlstate 'PT409' then assert sqlerrm='delivery_not_supported',sqlerrm; end;
 original=(select to_jsonb(o) from public.pokemon_observations o where revision_id=head and pokemon_entity_id='{entity}');
 completion={literal(complete)};
 completion=jsonb_set(completion,'{{registration,identity_plan,expected_predecessor_id}}',to_jsonb(head));
 receipt=public.api_training_operation(completion);
 assert receipt->>'status'='APPLIED','verified native result atomically applied';
 assert (select status from public.purchases where id='{purchase}')='used','purchase spent once';
 assert (select season_id from public.purchases where id='{purchase}')='{oldsid}','original purchase season never remapped';
 assert (select current_save_file_id from public.season_players where id='{pid}')='{result['save_id']}','new parsed save current';
 assert (select initial_evidence from public.pokemon_entities where id='{entity}')={literal(after)},'authorized current identity';
 assert (select count(*) from public.pokemon_entities where season_id='{sid}' and owner_trainer_id='{tid}')=1,'no duplicate entity';
 assert (select count(*) from public.pokemon_observations where season_id='{sid}' and pokemon_entity_id='{entity}')=2,'same UUID before and after';
 assert (select to_jsonb(o) from public.pokemon_observations o where revision_id=head and pokemon_entity_id='{entity}')=original,'old observation immutable';
 assert (select before_evidence from public.training_operations where operation_id='{operation}')={literal(before)},'original identity retained in audit';
 assert public.api_training_operation(completion)=receipt,'lost answer replay does not consume twice';
 assert (select count(*) from public.activity_events where dedupe_key='virtual_training:{operation}')=1,'one audited application';
 assert (select sum(amount) from public.coin_transactions where trainer_id='{tid}')=200,'training makes no coin/refund movement';
 begin
  perform public.api_training_operation(jsonb_set(completion,'{{output_sha256}}',to_jsonb(repeat('c',64))));
  raise exception 'different output replay accepted';
 exception when sqlstate 'PT409' then assert sqlerrm='training_idempotency_conflict',sqlerrm; end;
 begin
  perform public.api_training_operation(jsonb_build_object('operation','release','operation_id','{operation}','season_id','{sid}','trainer_id','{tid}'));
  raise exception 'applied operation released';
 exception when sqlstate 'PT409' then assert sqlerrm='training_already_applied',sqlerrm; end;
 -- A later regular synchronization retains the trained identity and UUID.
 ctx=public.api_register_save(jsonb_build_object('operation','context','season_id','{sid}','trainer_id','{tid}'));
 r={literal(future)}||jsonb_build_object('operation','register');
 r=jsonb_set(r,'{{identity_plan,expected_predecessor_id}}',ctx#>'{{head,id}}');
 perform public.api_register_save(r);
 assert (select count(*) from public.pokemon_entities where season_id='{sid}')=1,'next auto-sync does not duplicate trained entity';
 assert (select count(*) from public.pokemon_observations where season_id='{sid}' and outcome='AMBIGUOUS')=0,'no illegitimate identity ambiguity';
 assert not has_table_privilege('authenticated','public.training_operations','SELECT'),'no browser operation reads';
 assert not has_function_privilege('anon','public.api_training_operation(jsonb)','EXECUTE'),'no browser training RPC';
end $$;
rollback;
"""
    if capture_only:
        return {"seed_sql": sql.split("set local role service_role;")[0].strip().removeprefix("begin;"),
                "season_id": sid, "purchase_season_id": oldsid, "trainer_id": tid,
                "season_player_id": pid, "purchase_id": purchase, "operation_id": operation,
                "pokemon_entity_id": entity, "reserve": request, "complete": complete,
                "future_register": future, "initial_register": initial, "full_sql": sql}
    pg.sql(sql, user="supabase_admin")
    return "PASS: old paid cap from discarded season usable on current Y; reserve/replay/stale/sync/cancel/bag guards; independent-proof boundary SQLcommit; output+identity+purchase atomic; same entity UUID next sync; old observations retained; no coins/refund; service-only/RLS. Synthetic fixture rolled back."
