-- Phase24B integration reads. LOCAL ONLY: no public route or production writer capability.
-- Participants discover their own legs (with ONLY their own native plan); the
-- restricted verifier discovers pending plan/verify/finalize work. No new writes.
begin;

create function public.api_transfer_list(p_request jsonb) returns jsonb language plpgsql stable security definer set search_path='' as $$
declare sid uuid:=(p_request->>'season_id')::uuid; tid uuid:=(p_request->>'trainer_id')::uuid;
begin
 if sid is null or tid is null then raise sqlstate 'PT422' using message='invalid_transfer'; end if;
 if not exists(select 1 from public.trainers where id=tid and globally_enabled) then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 return coalesce((select jsonb_agg(q.item order by q.created_at desc) from (
  select a.created_at,jsonb_build_object(
   'authorization_id',a.id,'side',l.side,'status',public.transfer_state(a.id),
   'purchase_id',case when l.side='destination' then a.purchase_id end,
   'pokemon_entity_id',a.target_pokemon_entity_id,'source_sha256',l.source_sha256,
   'claimed',l.claim_id is not null,'apply_started',l.apply_started,'result_sha256',l.result_sha256,
   'verified',l.proof is not null,'accepted_save_id',x.receipt->l.side->>'save_id',
   'intent',case when x.terminal is null then x.plans->l.side->'intent' end,
   'expires_at',a.expires_at,'created_at',a.created_at) item
  from public.item_use_transfer_legs l
  join public.item_use_authorizations a on a.id=l.authorization_id
  join public.item_use_transfers x on x.authorization_id=a.id
  where l.season_id=sid and l.trainer_id=tid
  order by a.created_at desc limit 20) q),'[]'::jsonb);
end $$;
revoke all on function public.api_transfer_list(jsonb) from public,anon,authenticated,pokeapp_item_verifier;
grant execute on function public.api_transfer_list(jsonb) to service_role;

alter function public.transfer_verifier(jsonb) rename to transfer_verifier_v058;
revoke all on function public.transfer_verifier_v058(jsonb) from public,anon,authenticated,service_role,pokeapp_item_verifier;
create function public.transfer_verifier(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
begin
 if p_request->>'operation' is distinct from 'queue' then return public.transfer_verifier_v058(p_request); end if;
 -- Discovery only. Every action re-derives and rechecks its full context.
 return coalesce((select jsonb_agg(jsonb_build_object('authorization_id',w.aid,'action',w.action,'side',w.side) order by w.created_at,w.aid,w.side)
  from (select * from (
   select x.authorization_id aid,a.created_at,'plan' action,null::text side from public.item_use_transfers x
    join public.item_use_authorizations a on a.id=x.authorization_id
    where x.terminal is null and x.plans is null and a.expires_at>clock_timestamp()
   union all
   select l.authorization_id,a.created_at,'verify',l.side from public.item_use_transfer_legs l
    join public.item_use_transfers x on x.authorization_id=l.authorization_id
    join public.item_use_authorizations a on a.id=l.authorization_id
    where x.terminal is null and l.apply_started and l.result_url is not null and l.proof is null
     and (l.side='source' or exists(select 1 from public.item_use_transfer_legs s where s.authorization_id=l.authorization_id and s.side='source' and s.proof is not null))
   union all
   select x.authorization_id,a.created_at,'finalize',null from public.item_use_transfers x
    join public.item_use_authorizations a on a.id=x.authorization_id
    where x.terminal is null and (select count(proof) from public.item_use_transfer_legs l where l.authorization_id=x.authorization_id)=2
  ) j order by created_at limit 20) w),'[]'::jsonb);
end $$;
revoke all on function public.transfer_verifier(jsonb) from public,anon,authenticated,service_role;
grant execute on function public.transfer_verifier(jsonb) to pokeapp_item_verifier;
commit;
