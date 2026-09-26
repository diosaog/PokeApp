-- Phase 8L: modest Cup engine, typed sides/rounds and per-Cup certification.
-- Historical migrations and imported/ambiguous Cups are not reinterpreted.
begin;

alter table public.cups add column revision bigint not null default 0 check(revision>=0),
  add column rules_version integer check(rules_version=1),
  add column swiss_rounds integer check(swiss_rounds between 1 and 10),
  add constraint cup_season_scope unique(id,season_id),
  add constraint cup_engine_scope check(rules_version is null or (season_id is not null and format<>'manual' and swiss_rounds is not null));
alter table public.cup_participants add constraint cup_side_scope unique(id,cup_id);
alter table public.season_players add constraint cup_player_identity unique(id,season_id,trainer_id);
create table public.cup_side_members (
  cup_id uuid not null references public.cups(id),
  side_id uuid not null,
  season_id uuid not null references public.seasons(id),
  season_player_id uuid not null,
  trainer_id uuid not null references public.trainers(id),
  display_name text not null,
  primary key(cup_id,trainer_id),
  foreign key(cup_id,season_id) references public.cups(id,season_id),
  foreign key(side_id,cup_id) references public.cup_participants(id,cup_id),
  foreign key(season_player_id,season_id,trainer_id) references public.season_players(id,season_id,trainer_id)
);
create table public.cup_rounds (
  cup_id uuid not null references public.cups(id),
  number integer not null check(number>0),
  phase text not null check(phase in ('swiss','elimination','semifinal','round_robin','final')),
  status text not null check(status in ('open','closed')),
  eligible_side_ids uuid[] not null,
  primary key(cup_id,number)
);
alter table public.cup_matches add column engine_round_number integer,
  add column score_a integer, add column score_b integer,
  add constraint cup_match_round foreign key(cup_id,engine_round_number) references public.cup_rounds(cup_id,number),
  add constraint cup_match_a_scope foreign key(participant_a_id,cup_id) references public.cup_participants(id,cup_id) not valid,
  add constraint cup_match_b_scope foreign key(participant_b_id,cup_id) references public.cup_participants(id,cup_id) not valid,
  add constraint cup_match_winner_scope foreign key(winner_participant_id,cup_id) references public.cup_participants(id,cup_id) not valid,
  add constraint cup_engine_match_shape check(engine_round_number is null or (
    engine_round_number=round_number and bracket_position is not null
    and (participant_a_id is null or participant_b_id is null or participant_a_id<>participant_b_id)
    and (winner_participant_id is null or coalesce(winner_participant_id=participant_a_id,false) or coalesce(winner_participant_id=participant_b_id,false))
    and ((score_a is null and score_b is null) or (score_a is not null and score_b is not null and (score_a,score_b) in ((2,0),(2,1),(1,2),(0,2))))
    and (status<>'completed' or (participant_a_id is not null and participant_b_id is not null and winner_participant_id is not null))
    and (status='completed' or (score_a is null and score_b is null))
    and (status not in ('scheduled','void') or winner_participant_id is null)));
create unique index cup_engine_match_position on public.cup_matches(cup_id,engine_round_number,bracket_position)
  where engine_round_number is not null;
alter table public.cup_standings add column byes integer not null default 0,
  add column buchholz integer not null default 0,
  add column games_won integer not null default 0,
  add column games_lost integer not null default 0,
  add constraint cup_standing_scope foreign key(participant_id,cup_id) references public.cup_participants(id,cup_id) not valid;
create table public.cup_history (
  cup_id uuid not null references public.cups(id),
  revision bigint not null,
  operation text not null,
  actor_trainer_id uuid not null references public.trainers(id),
  reason text,
  snapshot jsonb not null,
  created_at timestamptz not null default now(),
  primary key(cup_id,revision)
);
create table public.cup_certificates (
  id uuid primary key default gen_random_uuid(),
  cup_id uuid not null unique references public.cups(id),
  season_id uuid not null references public.seasons(id),
  revision bigint not null,
  schema_version integer not null default 1 check(schema_version=1),
  champion_side_id uuid not null,
  finalist_side_id uuid not null,
  snapshot jsonb not null,
  checksum text not null check(checksum ~ '^[0-9a-f]{64}$'),
  actor_trainer_id uuid not null references public.trainers(id),
  certified_at timestamptz not null default now(),
  unique(id,cup_id),
  foreign key(cup_id,season_id) references public.cups(id,season_id),
  check(champion_side_id<>finalist_side_id),
  foreign key(champion_side_id,cup_id) references public.cup_participants(id,cup_id),
  foreign key(finalist_side_id,cup_id) references public.cup_participants(id,cup_id)
);
alter table public.hall_of_fame_entries
  alter column champion_trainer_id drop not null,
  drop constraint uq_hall_of_fame_season_competition,
  add column cup_id uuid references public.cups(id),
  add column cup_certificate_id uuid,
  add column champion_side_id uuid,
  add column finalist_side_id uuid,
  add constraint hall_cup_season foreign key(cup_id,season_id) references public.cups(id,season_id),
  add constraint hall_cup_certificate foreign key(cup_certificate_id,cup_id) references public.cup_certificates(id,cup_id),
  add constraint hall_cup_champion foreign key(champion_side_id,cup_id) references public.cup_participants(id,cup_id),
  add constraint hall_cup_finalist foreign key(finalist_side_id,cup_id) references public.cup_participants(id,cup_id),
  add constraint hall_cup_provenance check (
    (cup_id is null and cup_certificate_id is null and champion_side_id is null and finalist_side_id is null and champion_trainer_id is not null)
    or (cup_id is not null and cup_certificate_id is not null and champion_side_id is not null and finalist_side_id is not null
        and competition_type<>'league' and source_snapshot_revision_id is null and archive_snapshot_id is null and source_team_lock_id is null and team_snapshot='[]'::jsonb));
create unique index uq_hall_of_fame_season_competition on public.hall_of_fame_entries(season_id,competition_type) where cup_id is null;
create unique index uq_hall_cup on public.hall_of_fame_entries(cup_id) where cup_id is not null;

create trigger cup_history_immutable before update on public.cup_history for each row execute function public.lifecycle_artifact_immutable();
create trigger cup_certificate_immutable before update on public.cup_certificates for each row execute function public.lifecycle_artifact_immutable();
create function public.cup_protect_certified() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare cid uuid;
begin
  cid=(to_jsonb(old)->>(case when tg_table_name='cups' then 'id' else 'cup_id' end))::uuid;
  if exists(select 1 from public.cup_certificates where cup_id=cid) and new is distinct from old then
    perform public.admin_setup_fail('historical_artifact_immutable');
  end if;
  return new;
end $$;
do $$ declare t text; begin
  foreach t in array array['cups','cup_participants','cup_side_members','cup_rounds','cup_matches','cup_standings'] loop
    execute format('create trigger cup_certified_immutable before update on public.%I for each row execute function public.cup_protect_certified()',t);
  end loop;
end $$;

-- One explicit, safe graph is also the planning fingerprint source. No arbitrary
-- metadata, receipts, reasons, Auth data, saves or private League locks.
create function public.cup_document(cid uuid) returns jsonb
language sql stable security invoker set search_path=pg_catalog,public as $$
select jsonb_build_object('id',c.id,'season_id',c.season_id,'name',c.name,'format',c.format,'status',c.status,
 'revision',c.revision,'rules_version',c.rules_version,'swiss_rounds',c.swiss_rounds,
 'sides',coalesce((select jsonb_agg(jsonb_build_object('id',s.id,'name',s.display_name,'seed',s.seed_order,'status',s.status,
   'members',coalesce((select jsonb_agg(jsonb_build_object('trainer_id',m.trainer_id,'season_player_id',m.season_player_id,
      'display_name',m.display_name) order by m.trainer_id) from public.cup_side_members m where m.cup_id=cid and m.side_id=s.id),'[]'::jsonb)) order by s.seed_order,s.id)
   from public.cup_participants s where s.cup_id=cid),'[]'::jsonb),
 'rounds',coalesce((select jsonb_agg(jsonb_build_object('number',r.number,'phase',r.phase,'status',r.status,'eligible_side_ids',to_jsonb(r.eligible_side_ids),
   'matches',coalesce((select jsonb_agg(jsonb_build_object('id',m.id,'position',m.bracket_position,'a',m.participant_a_id,'b',m.participant_b_id,
      'winner',m.winner_participant_id,'status',m.status,'score_a',m.score_a,'score_b',m.score_b) order by m.bracket_position)
      from public.cup_matches m where m.cup_id=cid and m.engine_round_number=r.number),'[]'::jsonb)) order by r.number)
   from public.cup_rounds r where r.cup_id=cid),'[]'::jsonb),
 'standings',coalesce((select jsonb_agg(jsonb_build_object('side_id',s.participant_id,'seed',p.seed_order,'status',p.status,
   'position',s.position,'wins',s.wins,'losses',s.losses,'byes',s.byes,'buchholz',s.buchholz,'games_won',s.games_won,'games_lost',s.games_lost) order by s.position)
   from public.cup_standings s join public.cup_participants p on p.id=s.participant_id where s.cup_id=cid),'[]'::jsonb),
 'certificate_id',cert.id,'champion_side_id',cert.champion_side_id,'finalist_side_id',cert.finalist_side_id,'checksum',cert.checksum)
from public.cups c left join public.cup_certificates cert on cert.cup_id=c.id where c.id=cid
$$;

create function public.cup_context(r jsonb) returns jsonb
language sql stable security invoker set search_path=pg_catalog,public as $$
select jsonb_build_object('season_status',s.status,'cup',public.cup_document((r->>'resource_id')::uuid),
 'roster',coalesce((select jsonb_agg(jsonb_build_object('id',p.id,'trainer_id',p.trainer_id,'display_name',t.display_name,
    'globally_enabled',t.globally_enabled) order by p.id) from public.season_players p join public.trainers t on t.id=p.trainer_id
    where p.season_id=s.id),'[]'::jsonb)) from public.seasons s where s.id=(r->>'season_id')::uuid
$$;

create function public.cup_begin(r jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare cached jsonb; c public.cups; sid uuid=(r->>'season_id')::uuid; op text=r->>'operation';
begin
  if op not in ('create','setup','start','results','close','correct','disqualify','discard','finalize') then
    perform public.admin_setup_fail('invalid_request',422);
  end if;
  cached=public.admin_setup_begin('cup_'||op,r);
  if cached is not null then return cached; end if;
  if not exists(select 1 from public.seasons where id=sid and status in ('active','finished','archived')) then
    perform public.admin_setup_fail('season_not_eligible');
  end if;
  perform 1 from public.trainers t where exists(select 1 from public.season_players p where p.season_id=sid and p.trainer_id=t.id)
    order by t.id for share;
  if op<>'create' then
    select * into c from public.cups where id=(r->>'resource_id')::uuid and season_id=sid for update;
    if not found then perform public.admin_setup_fail('cup_not_found',404); end if;
    if c.rules_version is null then perform public.admin_setup_fail('legacy_cup_unsupported'); end if;
    if c.revision is distinct from (r->'body'->>'expected_revision')::bigint then perform public.admin_setup_fail('stale_revision'); end if;
    if c.status not in ('draft','active') then perform public.admin_setup_fail('cup_terminal'); end if;
    perform 1 from public.cup_participants where cup_id=c.id order by id for update;
    perform 1 from public.cup_side_members where cup_id=c.id order by trainer_id for update;
    perform 1 from public.cup_rounds where cup_id=c.id order by number for update;
    perform 1 from public.cup_matches where cup_id=c.id order by round_number,bracket_position,id for update;
    perform 1 from public.cup_standings where cup_id=c.id order by participant_id for update;
  end if;
  return null;
end $$;

create function public.api_cup_context(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare cached jsonb; ctx jsonb;
begin
  cached=public.cup_begin(p_request);
  if cached is not null then return jsonb_build_object('receipt',cached); end if;
  ctx=public.cup_context(p_request);
  return jsonb_build_object('context',ctx,'fingerprint',encode(sha256(convert_to(ctx::text,'UTF8')),'hex'));
end $$;

create function public.api_admin_cup(p_request jsonb,p_fingerprint text,p_plan jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare cached jsonb; ctx jsonb; cid uuid=(p_plan->>'id')::uuid; sid uuid=(p_request->>'season_id')::uuid;
  op text=p_request->>'operation'; actor uuid=(p_request->>'actor_trainer_id')::uuid; b jsonb=p_request->'body';
  s jsonb; m jsonb; r jsonb; st jsonb; member jsonb; old public.cups; snapshot jsonb; result jsonb;
  cert uuid; hid uuid; oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid(); champion uuid; finalist uuid;
begin
  cached=public.cup_begin(p_request); if cached is not null then return cached; end if;
  ctx=public.cup_context(p_request);
  if p_fingerprint is distinct from encode(sha256(convert_to(ctx::text,'UTF8')),'hex') then perform public.admin_setup_fail('stale_inputs'); end if;
  select * into old from public.cups where id=(p_request->>'resource_id')::uuid;
  if cid is null or (p_plan->>'season_id')::uuid is distinct from sid or (p_plan->>'rules_version')::integer is distinct from 1
    or (op<>'create' and cid is distinct from old.id)
    or (p_plan->>'revision')::bigint is distinct from coalesce(old.revision,0)+1
    or (op in ('setup','start') and old.status<>'draft')
    or (op in ('results','close','correct','finalize') and old.status<>'active') then perform public.admin_setup_fail('invalid_plan'); end if;
  if op in ('create','setup') then
    if op='create' then
      insert into public.cups(id,season_id,name,format,competition_type,rules_version,swiss_rounds)
        values(cid,sid,p_plan->>'name',p_plan->>'format',case when p_plan->>'format'='doubles' then 'doubles_cup' else 'cup' end,1,(p_plan->>'swiss_rounds')::int);
    else
      delete from public.cup_standings where cup_id=cid;
      delete from public.cup_side_members where cup_id=cid;
      delete from public.cup_participants where cup_id=cid;
      update public.cups set name=p_plan->>'name',format=p_plan->>'format',competition_type=case when p_plan->>'format'='doubles' then 'doubles_cup' else 'cup' end,
        swiss_rounds=(p_plan->>'swiss_rounds')::int where id=cid;
    end if;
    for s in select value from jsonb_array_elements(p_plan->'sides') loop
      if jsonb_array_length(s->'members')<>(case when p_plan->>'format'='doubles' then 2 else 1 end) then perform public.admin_setup_fail('invalid_roster'); end if;
      insert into public.cup_participants(id,cup_id,trainer_id,display_name,seed_order)
        values((s->>'id')::uuid,cid,case when p_plan->>'format'<>'doubles' then (s->'members'->0->>'trainer_id')::uuid end,s->>'name',(s->>'seed')::int);
      for member in select value from jsonb_array_elements(s->'members') loop
        if not exists(select 1 from public.season_players p join public.trainers t on t.id=p.trainer_id
          where p.id=(member->>'season_player_id')::uuid and p.season_id=sid and p.trainer_id=(member->>'trainer_id')::uuid and t.globally_enabled) then
          perform public.admin_setup_fail('invalid_roster'); end if;
        insert into public.cup_side_members(cup_id,side_id,season_id,season_player_id,trainer_id,display_name)
          values(cid,(s->>'id')::uuid,sid,(member->>'season_player_id')::uuid,(member->>'trainer_id')::uuid,member->>'display_name');
      end loop;
    end loop;
  else
    -- Frozen identity/rules are never replaced once the draw begins.
    if (p_plan-'revision'-'status'-'rounds'-'standings'-'champion_side_id'-'finalist_side_id'-'certificate_id'-'checksum'-'sides') is distinct from
       ((ctx->'cup')-'revision'-'status'-'rounds'-'standings'-'champion_side_id'-'finalist_side_id'-'certificate_id'-'checksum'-'sides') then perform public.admin_setup_fail('invalid_plan'); end if;
    if jsonb_array_length(p_plan->'sides')<>(select count(*) from public.cup_participants where cup_id=cid) then perform public.admin_setup_fail('invalid_plan'); end if;
    for s in select value from jsonb_array_elements(p_plan->'sides') loop
      if not exists(select 1 from jsonb_array_elements(ctx->'cup'->'sides') x where x.value-'status'=s-'status') then perform public.admin_setup_fail('invalid_plan'); end if;
      update public.cup_participants set status=s->>'status' where id=(s->>'id')::uuid and cup_id=cid and status is distinct from s->>'status';
    end loop;
  end if;
  if op='start' and exists(select 1 from public.cup_side_members m join public.cup_participants s on s.id=m.side_id
    join public.trainers t on t.id=m.trainer_id where m.cup_id=cid and s.status='active' and not t.globally_enabled) then perform public.admin_setup_fail('invalid_roster'); end if;
  -- Safe correction may remove only prepared, unplayed successors. Played rows
  -- must retain IDs; earlier result values remain in append-only command history.
  if exists(select 1 from public.cup_matches m where m.cup_id=cid and m.status='completed' and not exists(
      select 1 from jsonb_array_elements(p_plan->'rounds') r,jsonb_array_elements(r.value->'matches') x where (x.value->>'id')::uuid=m.id)) then perform public.admin_setup_fail('invalid_plan'); end if;
  delete from public.cup_matches m where m.cup_id=cid and not exists(
    select 1 from jsonb_array_elements(p_plan->'rounds') r,jsonb_array_elements(r.value->'matches') x where (x.value->>'id')::uuid=m.id);
  delete from public.cup_rounds r where r.cup_id=cid and not exists(select 1 from jsonb_array_elements(p_plan->'rounds') x where (x.value->>'number')::int=r.number);
  for r in select value from jsonb_array_elements(p_plan->'rounds') loop
    insert into public.cup_rounds(cup_id,number,phase,status,eligible_side_ids)
      values(cid,(r->>'number')::int,r->>'phase',r->>'status',array(select value::uuid from jsonb_array_elements_text(r->'eligible_side_ids')))
      on conflict(cup_id,number) do update set status=excluded.status,eligible_side_ids=excluded.eligible_side_ids,phase=excluded.phase;
    for m in select value from jsonb_array_elements(r->'matches') loop
      insert into public.cup_matches(id,cup_id,round_number,engine_round_number,bracket_position,participant_a_id,participant_b_id,winner_participant_id,status,score_a,score_b,score)
        values((m->>'id')::uuid,cid,(r->>'number')::int,(r->>'number')::int,(m->>'position')::int,(m->>'a')::uuid,(m->>'b')::uuid,(m->>'winner')::uuid,m->>'status',
          (m->>'score_a')::int,(m->>'score_b')::int,coalesce((m->>'score_a')||'-'||(m->>'score_b'),''))
        on conflict(id) do update set winner_participant_id=excluded.winner_participant_id,status=excluded.status,score_a=excluded.score_a,score_b=excluded.score_b,score=excluded.score
        where public.cup_matches.cup_id=cid and (public.cup_matches.winner_participant_id,public.cup_matches.status,public.cup_matches.score_a,public.cup_matches.score_b)
          is distinct from (excluded.winner_participant_id,excluded.status,excluded.score_a,excluded.score_b);
    end loop;
  end loop;
  for st in select value from jsonb_array_elements(p_plan->'standings') loop
    insert into public.cup_standings(cup_id,participant_id,position,wins,losses,points,byes,buchholz,games_won,games_lost)
      values(cid,(st->>'side_id')::uuid,(st->>'position')::int,(st->>'wins')::int,(st->>'losses')::int,(st->>'wins')::int,
        (st->>'byes')::int,(st->>'buchholz')::int,(st->>'games_won')::int,(st->>'games_lost')::int)
      on conflict(cup_id,participant_id) do update set position=excluded.position,wins=excluded.wins,losses=excluded.losses,points=excluded.points,
        byes=excluded.byes,buchholz=excluded.buchholz,games_won=excluded.games_won,games_lost=excluded.games_lost;
  end loop;
  update public.cups set status=p_plan->>'status',revision=(p_plan->>'revision')::bigint,
    started_at=case when op='start' then now() else started_at end,finished_at=case when op='finalize' then now() else finished_at end where id=cid;
  snapshot=public.cup_document(cid)-'certificate_id'-'checksum'-'champion_side_id'-'finalist_side_id';
  if op='finalize' then
    champion=(p_plan->>'champion_side_id')::uuid; finalist=(p_plan->>'finalist_side_id')::uuid;
    if not exists(select 1 from public.cup_rounds r join public.cup_matches m on m.cup_id=r.cup_id and m.engine_round_number=r.number
      where r.cup_id=cid and r.phase='final' and r.status='closed' and m.winner_participant_id=champion
      and ((m.participant_a_id=champion and m.participant_b_id=finalist) or (m.participant_b_id=champion and m.participant_a_id=finalist)))
      or exists(select 1 from public.cup_rounds where cup_id=cid and status<>'closed') then perform public.admin_setup_fail('invalid_plan'); end if;
    cert=gen_random_uuid(); hid=gen_random_uuid();
    snapshot=snapshot||jsonb_build_object('schema_version',1,'champion_side_id',champion,'finalist_side_id',finalist,'certified_at',now(),'team_snapshot','[]'::jsonb);
    insert into public.cup_certificates(id,cup_id,season_id,revision,champion_side_id,finalist_side_id,snapshot,checksum,actor_trainer_id)
      values(cert,cid,sid,(p_plan->>'revision')::bigint,champion,finalist,snapshot,encode(sha256(convert_to(snapshot::text,'UTF8')),'hex'),actor);
    insert into public.hall_of_fame_entries(id,season_id,competition_type,champion_trainer_id,finalist_trainer_id,team_snapshot,cup_id,cup_certificate_id,champion_side_id,finalist_side_id)
      select hid,sid,c.competition_type,a.trainer_id,b.trainer_id,'[]'::jsonb,cid,cert,champion,finalist
      from public.cups c join public.cup_participants a on a.id=champion join public.cup_participants b on b.id=finalist where c.id=cid;
  end if;
  insert into public.cup_history(cup_id,revision,operation,actor_trainer_id,reason,snapshot)
    values(cid,(p_plan->>'revision')::bigint,op,actor,b->>'reason',snapshot);
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(eid,sid,'CUP_'||upper(op),actor,'admin','cup:'||oid::text,jsonb_build_object('cup_id',cid,'revision',p_plan->'revision','reason',b->>'reason'));
  result=jsonb_build_object('operation_id',oid,'event_id',eid,'cup_id',cid,'season_id',sid,'operation',op,'revision',p_plan->'revision',
    'state',p_plan->>'status','certificate_id',cert,'hall_id',hid,'actor_trainer_id',actor,'changed_at',now(),'replayed',false);
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,actor,sid,public.admin_setup_scope('cup_'||op,p_request),p_request->>'idempotency_key',encode(sha256(convert_to(p_request::text,'UTF8')),'hex'),result);
  return result;
end $$;

create function public.api_cup_read(p_request jsonb) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare actor public.trainers; cid uuid=(p_request->>'resource_id')::uuid; sid uuid=(p_request->>'season_id')::uuid; result jsonb;
begin
  select * into actor from public.trainers where id=(p_request->>'actor_trainer_id')::uuid and globally_enabled;
  if not found then perform public.admin_setup_fail('trainer_disabled',403); end if;
  if cid is not null then
    select public.cup_document(c.id) into result from public.cups c join public.seasons s on s.id=c.season_id
      where c.id=cid and c.season_id=sid and c.rules_version=1 and (actor.is_admin or (c.status<>'discarded' and s.status<>'discarded'));
    if result is null then perform public.admin_setup_fail('cup_not_found',404); end if;
    return jsonb_build_object('cup',result);
  end if;
  select coalesce(jsonb_agg(public.cup_document(c.id)-'sides'-'rounds'-'standings' order by c.created_at,c.id),'[]'::jsonb) into result
    from public.cups c join public.seasons s on s.id=c.season_id where c.season_id=sid and c.rules_version=1
    and (actor.is_admin or (c.status<>'discarded' and s.status<>'discarded'));
  return jsonb_build_object('cups',result);
end $$;

alter table public.cup_side_members enable row level security;
alter table public.cup_rounds enable row level security;
alter table public.cup_history enable row level security;
alter table public.cup_certificates enable row level security;
-- Safe new tables are read through the typed backend API. No browser bypass.
revoke all on public.cup_side_members,public.cup_rounds,public.cup_history,public.cup_certificates from public,anon,authenticated;
grant all on public.cup_side_members,public.cup_rounds,public.cup_history,public.cup_certificates to service_role;
revoke insert,update,delete,truncate on public.cups,public.cup_participants,public.cup_matches,public.cup_standings,public.hall_of_fame_entries from public,anon,authenticated;
do $$ declare t text; cols text; f regprocedure; begin
  foreach t in array array['cups','cup_participants','cup_matches','cup_standings','cup_side_members','cup_rounds','cup_history','cup_certificates','hall_of_fame_entries'] loop
    select string_agg(quote_ident(attname),',') into cols from pg_attribute where attrelid=('public.'||t)::regclass and attnum>0 and not attisdropped;
    execute format('revoke insert (%s),update (%s) on public.%I from public,anon,authenticated',cols,cols,t);
  end loop;
  foreach t in array array['public_cups','public_cup_participants','public_cup_matches','public_cup_standings','public_hall_of_fame'] loop
    execute format('revoke insert,update,delete,truncate on public.%I from public,anon,authenticated',t);
    select string_agg(quote_ident(attname),',') into cols from pg_attribute where attrelid=('public.'||t)::regclass and attnum>0 and not attisdropped;
    execute format('revoke insert (%s),update (%s) on public.%I from public,anon,authenticated',cols,cols,t);
  end loop;
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and (p.proname like 'cup_%' or p.proname like 'api_cup_%' or p.proname='api_admin_cup') loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
-- Extend the existing Hall projection without changing its historical rows or
-- existing columns. Member identities are frozen in the public certificate.
do $$ declare definition text; begin
  definition=pg_get_viewdef('public.public_hall_of_fame'::regclass,true);
  execute format('create or replace view public.public_hall_of_fame with(security_invoker=false,security_barrier=true) as
    select v.*,h.cup_id,h.cup_certificate_id,h.champion_side_id,h.finalist_side_id,
      c.snapshot->''sides'' as cup_sides,c.checksum as cup_checksum
    from (%s) v join public.hall_of_fame_entries h on h.id=v.id
      left join public.cup_certificates c on c.id=h.cup_certificate_id',rtrim(definition,'; '||chr(10)));
end $$;
notify pgrst,'reload schema';
commit;
