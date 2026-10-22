begin;
create function public.account_admin_list(p_actor uuid,p_offset integer) returns jsonb
language plpgsql stable security invoker set search_path=public,pg_catalog as $$
declare result jsonb;
begin
 if not exists(select 1 from public.trainers where id=p_actor and globally_enabled and is_admin and auth_user_id is not null)
 then raise exception 'account_forbidden'; end if;
 if p_offset<0 or p_offset>100000 then raise exception 'invalid_account_offset'; end if;
 select coalesce(jsonb_agg(to_jsonb(q)),'[]'::jsonb) into result from (
   select id as trainer_id,display_name,globally_enabled,is_admin,profile_revision as revision,
     auth_user_id is not null as provisioned
   from public.trainers order by slug,id offset p_offset limit 50
 ) q;
 return jsonb_build_object('items',result,'offset',p_offset,'has_more',jsonb_array_length(result)=50);
end $$;

create function public.account_admin_status(p_actor uuid,p_target uuid,p_operation uuid,p_hash text,
 p_revision bigint,p_enabled boolean) returns jsonb
language plpgsql security invoker set search_path=public,pg_catalog as $$
declare a public.trainers; t public.trainers; c public.account_commands; result jsonb;
begin
 perform 1 from public.trainers where id in(p_actor,p_target) order by id for update;
 select * into strict a from public.trainers where id=p_actor;
 select * into strict t from public.trainers where id=p_target;
 if not a.globally_enabled or not a.is_admin or a.auth_user_id is null or p_actor=p_target
 then raise exception 'account_forbidden'; end if;
 select * into c from public.account_commands where operation_id=p_operation;
 if found then
   if c.actor_id<>p_actor or c.target_id<>p_target or c.kind<>'account_status' or c.request_hash<>p_hash
     then raise exception 'account_conflict'; end if;
   return c.result;
 end if;
 if t.profile_revision<>p_revision then raise exception 'account_stale'; end if;
 if t.auth_user_id is null then raise exception 'account_forbidden'; end if;
 -- A pending credential operation cannot be bypassed by re-enabling the account.
 if exists(select 1 from public.account_pin_changes where target_id=p_target and stage<>'complete')
 then raise exception 'account_conflict'; end if;
 update public.trainers set globally_enabled=p_enabled,profile_revision=profile_revision+1 where id=p_target returning * into t;
 insert into public.account_session_guards(trainer_id,blocked,minimum_iat)
 values(p_target,not p_enabled,floor(extract(epoch from clock_timestamp()))::bigint+1)
 on conflict(trainer_id) do update set blocked=excluded.blocked,minimum_iat=excluded.minimum_iat;
 result=jsonb_build_object('trainer_id',t.id,'revision',t.profile_revision,'globally_enabled',t.globally_enabled);
 insert into public.account_commands values(p_operation,p_actor,p_target,'account_status',p_hash,result,now());
 return result;
end $$;
revoke all on function public.account_admin_list(uuid,integer),
 public.account_admin_status(uuid,uuid,uuid,text,bigint,boolean) from public,anon,authenticated;
grant execute on function public.account_admin_list(uuid,integer),
 public.account_admin_status(uuid,uuid,uuid,text,bigint,boolean) to service_role;
commit;
