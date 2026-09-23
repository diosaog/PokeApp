-- Phase 8G.1: backend-only season preparation. No competitive close or rewards.
begin;

create table public.season_admin_state (
  season_id uuid primary key references public.seasons(id) on delete restrict,
  setup_revision bigint not null default 0 check (setup_revision >= 0),
  roster_revision bigint not null default 0 check (roster_revision >= 0),
  config_revision bigint not null default 0 check (config_revision >= 0)
);
create table public.admin_operation_receipts (
  id uuid primary key default gen_random_uuid(),
  actor_trainer_id uuid not null references public.trainers(id) on delete restrict,
  season_id uuid not null references public.seasons(id) on delete restrict,
  operation_scope text not null,
  idempotency_key text not null check (length(idempotency_key) between 1 and 128),
  request_hash text not null,
  response_json jsonb not null check (jsonb_typeof(response_json) = 'object'),
  created_at timestamptz not null default now(),
  unique (actor_trainer_id, operation_scope, idempotency_key)
);
alter table public.season_admin_state enable row level security;
alter table public.admin_operation_receipts enable row level security;
revoke all on public.season_admin_state, public.admin_operation_receipts from public, anon, authenticated;
grant all on public.season_admin_state, public.admin_operation_receipts to service_role;

-- NULL identifies pre-026 fixtures/imports, never a validated admin configuration.
alter table public.season_config_versions
  add column division_sizes jsonb,
  add column roster_revision bigint check (roster_revision >= 0),
  add constraint config_division_sizes_shape check (division_sizes is null or
    (jsonb_typeof(division_sizes) = 'object' and division_sizes ?& array['A','B']
     and division_sizes - 'A' - 'B' = '{}'::jsonb
     and (division_sizes->>'A')::integer > 0 and (division_sizes->>'B')::integer > 0));
create unique index uq_matches_unordered_pair on public.matches
  (matchday_id, least(player_a_id,player_b_id), greatest(player_a_id,player_b_id));

-- Table revocation alone does not remove the column grants introduced by 020.
revoke insert, update, delete on public.seasons, public.season_players,
  public.season_player_stats, public.season_config_versions, public.divisions,
  public.division_memberships, public.matchdays, public.matches from public, anon, authenticated;
do $$ declare t text; c text; begin
  foreach t in array array['seasons','season_players','season_player_stats',
    'season_config_versions','divisions','division_memberships','matchdays','matches'] loop
    select string_agg(quote_ident(attname), ',') into c from pg_attribute
      where attrelid=('public.'||t)::regclass and attnum>0 and not attisdropped;
    execute format('revoke insert (%s), update (%s) on public.%I from public, anon, authenticated',c,c,t);
  end loop;
end $$;

create function public.admin_setup_fail(code text, status integer default 409)
returns void language plpgsql set search_path = pg_catalog, public as $$
begin raise exception using errcode='PT'||status::text, message=code; end $$;

create function public.admin_setup_principal(actor uuid) returns void
language plpgsql set search_path = pg_catalog, public as $$
declare t public.trainers;
begin
  select * into t from public.trainers where id=actor for share;
  if not found or not t.globally_enabled then perform public.admin_setup_fail('trainer_disabled',403); end if;
  if not t.is_admin then perform public.admin_setup_fail('admin_required',403); end if;
end $$;

create function public.admin_setup_receipt_immutable() returns trigger
language plpgsql set search_path = pg_catalog, public as $$
begin
  if new is distinct from old then perform public.admin_setup_fail('idempotency_conflict'); end if;
  return new;
end $$;
create trigger admin_receipt_immutable before update on public.admin_operation_receipts
  for each row execute function public.admin_setup_receipt_immutable();

create function public.admin_setup_scope(op text, r jsonb) returns text
language sql immutable set search_path = pg_catalog as $$
  select op||':'||coalesce(r->>'season_id','new')||':'||coalesce(r->>'resource_id','')
$$;

create function public.admin_setup_begin(op text, r jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare old public.admin_operation_receipts; sid uuid=(r->>'season_id')::uuid;
  scope text=public.admin_setup_scope(op,r); k text=r->>'idempotency_key';
begin
  perform public.admin_setup_principal((r->>'actor_trainer_id')::uuid);
  if k is null or length(k) not between 1 and 128 then
    perform public.admin_setup_fail('invalid_request',422);
  end if;
  -- Receipts serialize retries even before a season exists. All operations use
  -- this order: principal, receipt key, season, participant UUIDs, specific rows.
  perform pg_advisory_xact_lock(hashtextextended((r->>'actor_trainer_id')||scope||':'||k,0));
  select * into old from public.admin_operation_receipts
    where actor_trainer_id=(r->>'actor_trainer_id')::uuid and operation_scope=scope and idempotency_key=k;
  if found then
    if old.request_hash <> encode(sha256(convert_to(r::text,'UTF8')),'hex') then
      if op='rename' then perform public.admin_setup_fail('stale_revision'); end if;
      perform public.admin_setup_fail('idempotency_conflict');
    end if;
    return old.response_json || '{"replayed":true}'::jsonb;
  end if;
  if sid is not null then
    perform 1 from public.seasons where id=sid for no key update;
    if not found then perform public.admin_setup_fail('season_not_found',404); end if;
    perform 1 from public.season_admin_state where season_id=sid;
    if not found then perform public.admin_setup_fail('setup_incomplete'); end if;
    perform 1 from public.season_players where season_id=sid order by id for update;
  end if;
  return null;
end $$;

create function public.admin_setup_finish(op text,r jsonb,sid uuid,resource uuid,evidence jsonb default '{}')
returns jsonb language plpgsql set search_path = pg_catalog, public as $$
declare oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid(); result jsonb;
begin
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(eid,sid,'SEASON_ADMIN_'||upper(op),(r->>'actor_trainer_id')::uuid,'admin',
      'season-admin:'||oid::text,jsonb_build_object('operation_id',oid,'resource_id',resource,'evidence',evidence));
  select jsonb_build_object('operation_id',oid,'resource_id',resource,'season_id',sid,
    'event_id',eid,'replayed',false,'state',s.status,'setup_revision',a.setup_revision,
    'roster_revision',a.roster_revision,'config_revision',a.config_revision) into result
    from public.seasons s join public.season_admin_state a on a.season_id=s.id where s.id=sid;
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,(r->>'actor_trainer_id')::uuid,sid,public.admin_setup_scope(op,r),r->>'idempotency_key',
      encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

create function public.admin_setup_draft(sid uuid) returns void
language plpgsql set search_path = pg_catalog, public as $$
begin
  if not exists(select 1 from public.seasons where id=sid and status='draft') then
    perform public.admin_setup_fail('season_not_draft');
  end if;
end $$;

create function public.admin_setup_cas(sid uuid,b jsonb) returns void
language plpgsql set search_path = pg_catalog, public as $$
declare a public.season_admin_state;
begin
  select * into strict a from public.season_admin_state where season_id=sid;
  if (b ? 'expected_revision' and (b->>'expected_revision')::bigint<>a.setup_revision)
    or (b ? 'expected_setup_revision' and (b->>'expected_setup_revision')::bigint<>a.setup_revision)
    or (b ? 'expected_roster_revision' and (b->>'expected_roster_revision')::bigint<>a.roster_revision)
    or (b ? 'expected_config_revision' and (b->>'expected_config_revision')::bigint<>a.config_revision) then
    perform public.admin_setup_fail('stale_revision');
  end if;
end $$;

create function public.admin_setup_config_used(cid uuid) returns boolean
language sql stable set search_path = pg_catalog, public as $$
  select exists(select 1 from public.matchdays where season_config_version_id=cid)
    or exists(select 1 from public.matchday_snapshots where config_version_id=cid)
$$;
create function public.admin_setup_protect_config() returns trigger
language plpgsql set search_path = pg_catalog, public as $$
begin
  if public.admin_setup_config_used(old.id) and new is distinct from old then
    perform public.admin_setup_fail('config_already_used');
  end if;
  return new;
end $$;
create trigger config_used_immutable before update on public.season_config_versions
  for each row execute function public.admin_setup_protect_config();

create function public.admin_setup_validate_config(sid uuid,b jsonb) returns void
language plpgsql set search_path = pg_catalog, public as $$
declare n integer; a integer; z integer; effective integer; total integer; k text; rewards jsonb; v jsonb;
begin
  select count(*) into n from public.season_players where season_id=sid;
  if n=0 or exists(select 1 from public.season_players where season_id=sid and status<>'active') then
    perform public.admin_setup_fail('invalid_roster');
  end if;
  if jsonb_typeof(b->'division_sizes') is distinct from 'object'
     or not (b->'division_sizes' ?& array['A','B']) or (b->'division_sizes')-'A'-'B'<>'{}'::jsonb then
    perform public.admin_setup_fail('invalid_config');
  end if;
  a=(b->'division_sizes'->>'A')::integer; z=(b->'division_sizes'->>'B')::integer;
  effective=(b->>'effective_from_matchday')::integer; total=(b->>'total_matchdays')::integer;
  if a<=0 or z<=0 or a+z<>n or (b->>'movement_count')::integer not between 0 and least(a,z)
    or total<1 or effective not between 1 and total or length(btrim(b->>'name')) not between 1 and 120 then
    perform public.admin_setup_fail('invalid_config');
  end if;
  foreach k in array array['scoring','coin_rewards'] loop
    rewards=b->k;
    if jsonb_typeof(rewards) is distinct from 'object'
      or (select count(*) from jsonb_object_keys(rewards))<>n then
      perform public.admin_setup_fail('invalid_rewards');
    end if;
    for i in 1..n loop
      v=rewards->i::text;
      if jsonb_typeof(v) is distinct from 'number' or v::text !~ '^[0-9]+$' then
        perform public.admin_setup_fail('invalid_rewards');
      end if;
    end loop;
  end loop;
  if jsonb_typeof(b->'rules') is distinct from 'object' or
    (b->'rules')-'team_lock_required'-'last_b_gets_steal'<>'{}'::jsonb or
    jsonb_typeof(b->'rules'->'team_lock_required') is distinct from 'boolean' or
    jsonb_typeof(b->'rules'->'last_b_gets_steal') is distinct from 'boolean' then
    perform public.admin_setup_fail('invalid_config');
  end if;
end $$;

create function public.admin_setup_config_window(sid uuid,b jsonb) returns void
language plpgsql set search_path = pg_catalog, public as $$
begin
  if not exists(select 1 from public.seasons where id=sid and status in ('draft','active'))
    or (b->>'effective_from_matchday')::integer <= coalesce((select max(number) from public.matchdays where season_id=sid),0) then
    perform public.admin_setup_fail('config_window_closed');
  end if;
end $$;

create function public.api_admin_create_season(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid; b jsonb=p_request->'body';
begin
  cached=public.admin_setup_begin('create',p_request); if cached is not null then return cached; end if;
  if length(btrim(b->>'name')) not between 1 and 120 then perform public.admin_setup_fail('invalid_request',422); end if;
  insert into public.seasons(name,status,created_by_trainer_id)
    values(b->>'name','draft',(p_request->>'actor_trainer_id')::uuid) returning id into sid;
  insert into public.season_admin_state(season_id) values(sid);
  return public.admin_setup_finish('create',p_request,sid,sid);
end $$;

create function public.api_admin_rename_season(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; b jsonb=p_request->'body'; old_name text;
begin
  cached=public.admin_setup_begin('rename',p_request); if cached is not null then return cached; end if;
  perform public.admin_setup_draft(sid); perform public.admin_setup_cas(sid,b);
  if length(btrim(b->>'name')) not between 1 and 120 then perform public.admin_setup_fail('invalid_request',422); end if;
  select name into old_name from public.seasons where id=sid;
  update public.seasons set name=b->>'name' where id=sid;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('rename',p_request,sid,sid,jsonb_build_object('before',old_name,'after',b->>'name'));
end $$;

create function public.api_admin_add_participant(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; b jsonb=p_request->'body'; pid uuid; tid uuid=(b->>'trainer_id')::uuid;
begin
  cached=public.admin_setup_begin('add_participant',p_request); if cached is not null then return cached; end if;
  perform public.admin_setup_draft(sid); perform public.admin_setup_cas(sid,b);
  if exists(select 1 from public.division_memberships where season_id=sid) or exists(select 1 from public.matchdays where season_id=sid) then
    perform public.admin_setup_fail('initial_setup_locked'); end if;
  if not exists(select 1 from public.trainers where id=tid and globally_enabled) then
    perform public.admin_setup_fail('trainer_unavailable'); end if;
  if exists(select 1 from public.season_players where season_id=sid and trainer_id=tid) then
    perform public.admin_setup_fail('participant_exists'); end if;
  insert into public.season_players(season_id,trainer_id,seed_order) values(sid,tid,(b->>'seed_order')::integer) returning id into pid;
  insert into public.season_player_stats(season_player_id,season_id,trainer_id) values(pid,sid,tid);
  update public.season_admin_state set roster_revision=roster_revision+1,setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('add_participant',p_request,sid,pid);
end $$;

create function public.api_admin_remove_participant(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; pid uuid=(p_request->>'resource_id')::uuid;
  b jsonb=p_request->'body'; ref record; referenced boolean;
begin
  cached=public.admin_setup_begin('remove_participant',p_request); if cached is not null then return cached; end if;
  perform public.admin_setup_draft(sid); perform public.admin_setup_cas(sid,b);
  if not exists(select 1 from public.season_players where id=pid and season_id=sid) then
    perform public.admin_setup_fail('participant_not_found',404); end if;
  if length(btrim(b->>'reason')) not between 1 and 500 then perform public.admin_setup_fail('invalid_request',422); end if;
  if exists(select 1 from public.season_config_versions where season_id=sid)
    or exists(select 1 from public.divisions where season_id=sid)
    or exists(select 1 from public.matchdays where season_id=sid)
    or exists(select 1 from public.season_players where id=pid and (current_save_file_id is not null or metadata<>'{}'::jsonb))
    or exists(select 1 from public.season_player_stats where season_player_id=pid and (badges_count<>0 or metadata<>'{}'::jsonb)) then
    perform public.admin_setup_fail('participant_referenced'); end if;
  -- Inspect every real FK to participant identity, including later additive tables.
  for ref in
    select c.conrelid::regclass as tbl,a.attname from pg_constraint c
    cross join lateral unnest(c.conkey,c.confkey) as cols(src,dst)
    join pg_attribute a on a.attrelid=c.conrelid and a.attnum=cols.src
    join pg_attribute target on target.attrelid=c.confrelid and target.attnum=cols.dst
    where c.contype='f' and c.confrelid='public.season_players'::regclass and target.attname='id'
      and c.conrelid<>'public.season_player_stats'::regclass
  loop
    execute format('select exists(select 1 from %s where %I=$1)',ref.tbl,ref.attname) into referenced using pid;
    if referenced then perform public.admin_setup_fail('participant_referenced'); end if;
  end loop;
  delete from public.season_player_stats where season_player_id=pid;
  delete from public.season_players where id=pid;
  update public.season_admin_state set roster_revision=roster_revision+1,setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('remove_participant',p_request,sid,pid,jsonb_build_object('reason',b->>'reason'));
exception when foreign_key_violation then perform public.admin_setup_fail('participant_referenced');
end $$;

create function public.api_admin_create_config(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; b jsonb=p_request->'body'; cid uuid;
begin
  cached=public.admin_setup_begin('create_config',p_request); if cached is not null then return cached; end if;
  perform public.admin_setup_cas(sid,b); perform public.admin_setup_validate_config(sid,b); perform public.admin_setup_config_window(sid,b);
  if exists(select 1 from public.season_config_versions where season_id=sid and effective_from_matchday=(b->>'effective_from_matchday')::integer) then
    perform public.admin_setup_fail('effective_round_exists'); end if;
  insert into public.season_config_versions(season_id,version_number,name,effective_from_matchday,total_matchdays,
    division_count,promotion_relegation_count,scoring_json,coin_rewards_json,rules_json,division_sizes,roster_revision,created_by_trainer_id)
    values(sid,(select coalesce(max(version_number),0)+1 from public.season_config_versions where season_id=sid),
      b->>'name',(b->>'effective_from_matchday')::integer,(b->>'total_matchdays')::integer,2,(b->>'movement_count')::integer,
      b->'scoring',b->'coin_rewards',b->'rules',b->'division_sizes',(b->>'expected_roster_revision')::bigint,(p_request->>'actor_trainer_id')::uuid)
    returning id into cid;
  update public.season_admin_state set config_revision=config_revision+1,setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('create_config',p_request,sid,cid);
end $$;

create function public.api_admin_replace_config(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; b jsonb=p_request->'body'; cid uuid=(p_request->>'resource_id')::uuid; old public.season_config_versions;
begin
  cached=public.admin_setup_begin('replace_config',p_request); if cached is not null then return cached; end if;
  select * into old from public.season_config_versions where id=cid and season_id=sid for update;
  if not found then perform public.admin_setup_fail('config_not_found',404); end if;
  if public.admin_setup_config_used(cid) then perform public.admin_setup_fail('config_already_used'); end if;
  perform public.admin_setup_cas(sid,b); perform public.admin_setup_validate_config(sid,b); perform public.admin_setup_config_window(sid,b);
  if old.effective_from_matchday<>(b->>'effective_from_matchday')::integer or length(btrim(b->>'reason')) not between 1 and 500 then
    perform public.admin_setup_fail('invalid_config'); end if;
  if old.effective_from_matchday=1 and exists(select 1 from public.division_memberships where season_id=sid)
    and old.division_sizes is distinct from b->'division_sizes' then perform public.admin_setup_fail('initial_setup_locked'); end if;
  update public.season_config_versions set name=b->>'name',total_matchdays=(b->>'total_matchdays')::integer,
    promotion_relegation_count=(b->>'movement_count')::integer,scoring_json=b->'scoring',coin_rewards_json=b->'coin_rewards',
    rules_json=b->'rules',division_sizes=b->'division_sizes',roster_revision=(b->>'expected_roster_revision')::bigint where id=cid;
  update public.season_admin_state set config_revision=config_revision+1,setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('replace_config',p_request,sid,cid,
    jsonb_build_object('reason',b->>'reason','before',to_jsonb(old),'after',b));
end $$;

create function public.api_admin_initial_divisions(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; b jsonb=p_request->'body'; cfg public.season_config_versions;
  division_code text; did uuid; pid text; all_ids uuid[]; n integer;
begin
  cached=public.admin_setup_begin('initial_divisions',p_request); if cached is not null then return cached; end if;
  perform public.admin_setup_draft(sid); perform public.admin_setup_cas(sid,b);
  if exists(select 1 from public.division_memberships where season_id=sid) or exists(select 1 from public.matchdays where season_id=sid) then
    perform public.admin_setup_fail('initial_setup_locked'); end if;
  select * into cfg from public.season_config_versions where id=(b->>'config_version_id')::uuid and season_id=sid;
  if not found or cfg.effective_from_matchday<>1 or cfg.division_sizes is null or cfg.roster_revision<>(b->>'expected_roster_revision')::bigint then
    perform public.admin_setup_fail('config_not_effective'); end if;
  if jsonb_typeof(b->'assignments') is distinct from 'object' or not(b->'assignments' ?& array['A','B'])
    or (b->'assignments')-'A'-'B'<>'{}'::jsonb then perform public.admin_setup_fail('invalid_roster'); end if;
  select array_agg(value::uuid) into all_ids from jsonb_array_elements_text((b->'assignments'->'A')||(b->'assignments'->'B'));
  select count(*) into n from public.season_players where season_id=sid and status='active';
  if cardinality(all_ids) is distinct from n or (select count(distinct x) from unnest(all_ids) x)<>n
    or exists(select 1 from unnest(all_ids) x where not exists(select 1 from public.season_players where id=x and season_id=sid and status='active')) then
    perform public.admin_setup_fail('invalid_roster'); end if;
  foreach division_code in array array['A','B'] loop
    if jsonb_array_length(b->'assignments'->division_code)<>(cfg.division_sizes->>division_code)::integer then
      perform public.admin_setup_fail('division_capacity_mismatch'); end if;
    insert into public.divisions(season_id,code,name,tier_order) values(sid,division_code,'Division '||division_code,case division_code when 'A' then 1 else 2 end)
      on conflict(season_id,code) do nothing;
    select id into did from public.divisions d where d.season_id=sid and d.code=division_code and tier_order=case division_code when 'A' then 1 else 2 end;
    if did is null then perform public.admin_setup_fail('initial_setup_locked'); end if;
    for pid in select jsonb_array_elements_text(b->'assignments'->division_code) loop
      insert into public.division_memberships(season_id,season_player_id,division_id,effective_from_matchday_number,reason)
        values(sid,pid::uuid,did,1,'initial');
    end loop;
  end loop;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('initial_divisions',p_request,sid,sid);
end $$;

create function public.admin_setup_readiness(sid uuid) returns jsonb
language plpgsql stable set search_path = pg_catalog, public as $$
declare s public.seasons; a public.season_admin_state; cfg public.season_config_versions; day public.matchdays;
  n integer; okcfg boolean=false; members boolean=false; pairs boolean=false; divok boolean=false; checks jsonb; reasons jsonb;
begin
  select * into s from public.seasons where id=sid;
  select * into a from public.season_admin_state where season_id=sid;
  select count(*) into n from public.season_players where season_id=sid;
  select * into cfg from public.season_config_versions where season_id=sid and effective_from_matchday=1;
  if cfg.id is not null and cfg.roster_revision=a.roster_revision and cfg.division_sizes is not null then
    begin
      perform public.admin_setup_validate_config(sid,jsonb_build_object('name',cfg.name,'division_sizes',cfg.division_sizes,
        'effective_from_matchday',1,'total_matchdays',cfg.total_matchdays,'movement_count',cfg.promotion_relegation_count,
        'scoring',cfg.scoring_json,'coin_rewards',cfg.coin_rewards_json,'rules',cfg.rules_json));
      okcfg=true;
    exception when sqlstate 'PT409' then okcfg=false; end;
  end if;
  divok=(select count(*)=2 and bool_and((code='A' and tier_order=1) or (code='B' and tier_order=2)) from public.divisions where season_id=sid);
  members=divok and okcfg and (select count(*)=n from public.division_memberships where season_id=sid)
    and not exists(select 1 from public.division_memberships where season_id=sid and
      (effective_from_matchday_number<>1 or effective_to_matchday_number is not null or source_matchday_id is not null or reason<>'initial'))
    and not exists(select 1 from public.divisions d where d.season_id=sid and
      (select count(*) from public.division_memberships m where m.division_id=d.id)<>(cfg.division_sizes->>d.code)::integer);
  select * into day from public.matchdays where season_id=sid and number=1;
  if members and day.id is not null then
    with expected as (
      select m.division_id,m.season_player_id a,x.season_player_id b from public.division_memberships m
      join public.division_memberships x on x.division_id=m.division_id and m.season_player_id<x.season_player_id
      where m.season_id=sid
    ), actual as (
      select division_id,least(player_a_id,player_b_id) a,greatest(player_a_id,player_b_id) b
      from public.matches where matchday_id=day.id
    ) select not exists((select * from expected except select * from actual) union all
      (select * from actual except select * from expected)) into pairs;
    pairs=pairs and not exists(select 1 from public.matches where matchday_id=day.id and
      (status<>'scheduled' or winner_id is not null or result_code<>''));
  end if;
  checks=jsonb_build_object('has_roster',n>0 and not exists(select 1 from public.season_players p
      left join public.season_player_stats st on st.season_player_id=p.id where p.season_id=sid and (p.status<>'active' or st.season_player_id is null)),
    'has_valid_config',okcfg,'has_initial_divisions',divok,'memberships_complete',members,
    'first_matchday_prepared',day.id is not null and day.status='scheduled' and day.opened_at is null and day.closed_at is null
       and day.season_config_version_id=cfg.id and (select count(*)=1 from public.matchdays where season_id=sid),
    'match_pairs_complete',pairs,'pointer_valid',coalesce(s.current_matchday_id=day.id,false),
    'no_other_active_season',not exists(select 1 from public.seasons where status='active' and id<>sid),
    'is_draft',s.status='draft');
  select coalesce(jsonb_agg(key order by key),'[]'::jsonb) into reasons from jsonb_each(checks) where value is distinct from 'true'::jsonb;
  return jsonb_build_object('checks',checks,'blocking_reasons',reasons,'can_activate',reasons='[]'::jsonb);
end $$;

create function public.api_admin_prepare_first_matchday(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; b jsonb=p_request->'body'; ready jsonb; cid uuid; did uuid;
begin
  cached=public.admin_setup_begin('prepare',p_request); if cached is not null then return cached; end if;
  perform public.admin_setup_draft(sid);
  if exists(select 1 from public.matchdays where season_id=sid) then perform public.admin_setup_fail('matchday_already_prepared'); end if;
  perform public.admin_setup_cas(sid,b);
  ready=public.admin_setup_readiness(sid)->'checks';
  if not ((ready->>'has_roster')::boolean and (ready->>'has_valid_config')::boolean and (ready->>'memberships_complete')::boolean) then
    perform public.admin_setup_fail('setup_incomplete'); end if;
  select id into cid from public.season_config_versions where season_id=sid and effective_from_matchday=1;
  insert into public.matchdays(season_id,number,season_config_version_id) values(sid,1,cid) returning id into did;
  insert into public.matches(season_id,matchday_id,division_id,player_a_id,player_b_id)
    select sid,did,m.division_id,m.season_player_id,x.season_player_id from public.division_memberships m
    join public.division_memberships x on x.division_id=m.division_id and m.season_player_id<x.season_player_id
    where m.season_id=sid order by m.division_id,m.season_player_id,x.season_player_id;
  update public.seasons set current_matchday_id=did where id=sid;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('prepare',p_request,sid,did);
end $$;

create function public.api_admin_activate_season(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; b jsonb=p_request->'body';
begin
  cached=public.admin_setup_begin('activate',p_request); if cached is not null then return cached; end if;
  perform public.admin_setup_draft(sid); perform public.admin_setup_cas(sid,b);
  if exists(select 1 from public.seasons where status='active' and id<>sid) then perform public.admin_setup_fail('active_season_exists'); end if;
  if not (public.admin_setup_readiness(sid)->>'can_activate')::boolean then perform public.admin_setup_fail('setup_incomplete'); end if;
  begin
    update public.seasons set status='active',started_at=clock_timestamp() where id=sid;
  exception when unique_violation then perform public.admin_setup_fail('active_season_exists'); end;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('activate',p_request,sid,sid);
end $$;

create function public.api_admin_get_setup(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare sid uuid=(p_request->>'season_id')::uuid; result jsonb;
begin
  perform public.admin_setup_principal((p_request->>'actor_trainer_id')::uuid);
  -- SHARE holds a coherent multi-query read against every admin mutation.
  perform 1 from public.seasons where id=sid for share;
  if not found then perform public.admin_setup_fail('season_not_found',404); end if;
  select jsonb_build_object('season',jsonb_build_object('id',s.id,'name',s.name,'status',s.status,'started_at',s.started_at),
    'setup_revision',coalesce(a.setup_revision,0),'roster_revision',coalesce(a.roster_revision,0),'config_revision',coalesce(a.config_revision,0),
    'current_matchday_id',s.current_matchday_id,'readiness',public.admin_setup_readiness(sid),
    'participants',(select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'trainer_id',p.trainer_id,'display_name',t.display_name,
      'status',p.status,'seed_order',p.seed_order,'stats_ready',st.season_player_id is not null) order by p.id),'[]'::jsonb)
      from public.season_players p join public.trainers t on t.id=p.trainer_id
      left join public.season_player_stats st on st.season_player_id=p.id where p.season_id=sid),
    'config_versions',(select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'name',c.name,'version_number',c.version_number,
      'effective_from_matchday',c.effective_from_matchday,'total_matchdays',c.total_matchdays,'division_sizes',c.division_sizes,
      'movement_count',c.promotion_relegation_count,'scoring',c.scoring_json,'coin_rewards',c.coin_rewards_json,'rules',c.rules_json,
      'roster_revision',c.roster_revision,'used',public.admin_setup_config_used(c.id),
      'is_current',coalesce(c.id=(select x.id from public.season_config_versions x where x.season_id=sid
        and x.effective_from_matchday<=coalesce((select number from public.matchdays where id=s.current_matchday_id),1)
        order by x.effective_from_matchday desc limit 1),false)) order by c.effective_from_matchday),'[]'::jsonb)
      from public.season_config_versions c where c.season_id=sid),
    'divisions',(select coalesce(jsonb_agg(jsonb_build_object('id',d.id,'code',d.code,'tier_order',d.tier_order) order by d.tier_order),'[]'::jsonb) from public.divisions d where d.season_id=sid),
    'memberships',(select coalesce(jsonb_agg(jsonb_build_object('season_player_id',m.season_player_id,'division_id',m.division_id,
      'effective_from_matchday',m.effective_from_matchday_number,'effective_to_matchday',m.effective_to_matchday_number,'reason',m.reason) order by m.season_player_id),'[]'::jsonb) from public.division_memberships m where m.season_id=sid),
    'first_matchday',(select jsonb_build_object('id',d.id,'number',d.number,'status',d.status,'config_version_id',d.season_config_version_id,
      'match_count',(select count(*) from public.matches where matchday_id=d.id)) from public.matchdays d where d.season_id=sid and number=1)) into result
    from public.seasons s left join public.season_admin_state a on a.season_id=s.id where s.id=sid;
  return result;
end $$;

do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and (p.proname like 'admin_setup_%' or p.proname like 'api_admin_%') loop
    execute format('revoke all on function %s from public, anon, authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst, 'reload schema';
commit;
