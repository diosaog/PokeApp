-- Phase 8K.1: Discord decisions recorded manually, never an application jury.
begin;

alter table public.trial_cases
  add column authority_version integer check (authority_version=1),
  add column case_number bigint check (case_number>0),
  add column revision bigint not null default 0 check (revision>=0),
  add column verdict text check (verdict in ('guilty','not_guilty')),
  add column decision_revision_id uuid,
  add constraint trial_case_number_unique unique(season_id,case_number),
  add constraint trial_authoritative_identity check (authority_version is null or
    (season_id is not null and case_number is not null and created_by_trainer_id is not null and accused_trainer_id is not null));

create table public.trial_case_counters (
  season_id uuid primary key references public.seasons(id) on delete restrict,
  next_number bigint not null default 1 check(next_number>0)
);
create table public.trial_case_revisions (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.trial_cases(id) on delete restrict,
  season_id uuid not null references public.seasons(id) on delete restrict,
  revision bigint not null check(revision>0),
  operation text not null check(operation in ('create','proposal','resolve','cancel','correct')),
  actor_trainer_id uuid not null references public.trainers(id) on delete restrict,
  previous_decision_id uuid,
  details jsonb not null check(jsonb_typeof(details)='object'),
  verdict text check(verdict in ('guilty','not_guilty')),
  decision_summary text not null default '',
  reason text not null default '',
  sanctions jsonb not null default '[]' check(jsonb_typeof(sanctions)='array'),
  created_at timestamptz not null default clock_timestamp(),
  unique(case_id,revision), unique(id,case_id,season_id),
  foreign key(previous_decision_id,case_id,season_id) references public.trial_case_revisions(id,case_id,season_id),
  constraint trial_decision_explicit check ((operation in ('resolve','correct'))=(verdict is not null)),
  constraint trial_correction_source check ((operation='correct')=(previous_decision_id is not null))
);
alter table public.penalties
  add column trial_revision_id uuid,
  add column points_amount numeric(12,2) check(points_amount>0),
  add column duration_matchdays integer check(duration_matchdays between 1 and 1000),
  add column effective_from_matchday_number integer check(effective_from_matchday_number>0),
  add constraint trial_penalty_source foreign key(trial_revision_id,trial_case_id,season_id)
    references public.trial_case_revisions(id,case_id,season_id),
  add constraint trial_penalty_identity unique(id,season_id,trainer_id),
  add constraint trial_penalty_once unique(trial_revision_id,penalty_type),
  add constraint trial_penalty_shape check(trial_revision_id is null or
    (trial_case_id is not null and created_by_trainer_id is not null and (
      (penalty_type='coins_reduction' and amount>0 and points_amount is null and duration_matchdays is null)
      or (penalty_type='points_reduction' and amount=0 and points_amount is not null and duration_matchdays is null and effective_from_matchday_number is not null)
      or (penalty_type='store_ban' and amount=0 and points_amount is null and duration_matchdays is not null
          and start_matchday_number is not null and end_matchday_number=start_matchday_number+duration_matchdays-1)
      or (penalty_type in ('pokemon_release','other') and amount=0 and points_amount is null and duration_matchdays is null)
    )));
alter table public.coin_transactions
  add column trial_case_id uuid,
  add column trial_revision_id uuid,
  add column trial_penalty_id uuid,
  add column trial_previous_penalty_id uuid,
  add constraint trial_ledger_source foreign key(trial_revision_id,trial_case_id,season_id)
    references public.trial_case_revisions(id,case_id,season_id),
  add constraint trial_ledger_penalty foreign key(trial_penalty_id,season_id,trainer_id)
    references public.penalties(id,season_id,trainer_id),
  add constraint trial_ledger_previous_penalty foreign key(trial_previous_penalty_id,season_id,trainer_id)
    references public.penalties(id,season_id,trainer_id),
  add constraint trial_ledger_once unique(trial_revision_id),
  add constraint trial_ledger_provenance check ((trial_revision_id is null and trial_case_id is null and trial_penalty_id is null and trial_previous_penalty_id is null)
    or (trial_revision_id is not null and trial_case_id is not null and (trial_penalty_id is not null or trial_previous_penalty_id is not null)
      and transaction_type in ('penalty','compensation')));

alter table public.trial_case_counters enable row level security;
alter table public.trial_case_revisions enable row level security;
revoke all on public.trial_case_counters,public.trial_case_revisions from public,anon,authenticated;
grant all on public.trial_case_counters,public.trial_case_revisions to service_role;
grant select on public.trial_case_revisions to authenticated;
create policy trial_history_parties_read on public.trial_case_revisions for select using (
  public.is_current_user_admin() or exists(select 1 from public.trial_cases c where c.id=case_id and
    (c.created_by_trainer_id=public.current_trainer_id() or c.accused_trainer_id=public.current_trainer_id())));
revoke insert,update,delete on public.trial_cases,public.trial_votes,public.penalties from public,anon,authenticated;
do $$ declare t text; cols text; begin
  foreach t in array array['trial_cases','trial_votes','penalties','trial_case_counters','trial_case_revisions','coin_transactions'] loop
    select string_agg(quote_ident(attname),',') into cols from pg_attribute
      where attrelid=('public.'||t)::regclass and attnum>0 and not attisdropped;
    execute format('revoke insert (%s),update (%s) on public.%I from public,anon,authenticated',cols,cols,t);
  end loop;
end $$;

create function public.trials_immutable() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if tg_table_name='trial_case_revisions' or to_jsonb(old)->>'trial_revision_id' is not null then
    if new is distinct from old then perform public.admin_setup_fail('historical_artifact_immutable'); end if;
  end if;
  return new;
end $$;
create trigger trial_revision_immutable before update on public.trial_case_revisions for each row execute function public.trials_immutable();
create trigger trial_penalty_immutable before update on public.penalties for each row execute function public.trials_immutable();
create trigger trial_ledger_immutable before update on public.coin_transactions for each row execute function public.trials_immutable();

create function public.trials_case_guard() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if old.authority_version=1 and (
    (new.id,new.season_id,new.created_by_trainer_id,new.accused_trainer_id,new.case_number,new.created_at,new.authority_version)
      is distinct from (old.id,old.season_id,old.created_by_trainer_id,old.accused_trainer_id,old.case_number,old.created_at,old.authority_version)
    or new.revision<>old.revision+1 or not exists(select 1 from public.trial_case_revisions h
      where h.case_id=new.id and h.season_id=new.season_id and h.revision=new.revision)
    or (new.decision_revision_id is not null and not exists(select 1 from public.trial_case_revisions h
      where h.id=new.decision_revision_id and h.case_id=new.id and h.season_id=new.season_id and h.verdict=new.verdict))
  ) then perform public.admin_setup_fail('historical_artifact_immutable'); end if;
  return new;
end $$;
create trigger trial_case_authority before update on public.trial_cases for each row execute function public.trials_case_guard();

create function public.trials_penalty_current(p public.penalties) returns boolean
language sql stable security invoker set search_path=pg_catalog,public as $$
  select p.trial_revision_id is null or exists(select 1 from public.trial_cases c
    where c.id=p.trial_case_id and c.decision_revision_id=p.trial_revision_id and c.verdict='guilty')
$$;

-- Old rows retain 020 inclusive/NULL semantics. New bans expire on the last
-- sanctioned round's official close, including a final CLOSED pointer.
create or replace function public.api_is_store_banned(p_season_id uuid,p_trainer_id uuid,p_matchday_number integer)
returns boolean language sql security invoker set search_path='' as $$
  select exists(select 1 from public.penalties p join public.trial_cases c on c.id=p.trial_case_id
    where p.season_id=p_season_id and p.trainer_id=p_trainer_id and p.penalty_type='store_ban'
      and c.status='resolved' and c.accused_trainer_id=p_trainer_id and (c.season_id is null or c.season_id=p_season_id)
      and public.trials_penalty_current(p)
      and (p.start_matchday_number is null or p.end_matchday_number is null
        or p_matchday_number between p.start_matchday_number and p.end_matchday_number)
      and (p.trial_revision_id is null or not exists(select 1 from public.matchdays d
        where d.season_id=p_season_id and d.number=p.end_matchday_number and d.status='closed')))
$$;

create function public.trials_validate_body(op text,b jsonb) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare allowed text[]; p jsonb; kinds text[]='{}'; typ text;
begin
  allowed=case op when 'create' then array['title','description','is_public','evidence','accused_trainer_id']
    when 'proposal' then array['title','description','is_public','evidence','expected_case_revision']
    when 'resolve' then array['expected_case_revision','verdict','decision_summary','sanctions']
    when 'correct' then array['expected_case_revision','verdict','decision_summary','sanctions','reason']
    when 'cancel' then array['expected_case_revision','reason'] end;
  if allowed is null or b is null or jsonb_typeof(b)<>'object' or b-allowed<>'{}' then
    perform public.admin_setup_fail('invalid_request',422); end if;
  if op<>'create' and (jsonb_typeof(b->'expected_case_revision') is distinct from 'number'
    or (b->>'expected_case_revision')!~'^[0-9]+$') then perform public.admin_setup_fail('invalid_request',422); end if;
  if op in ('create','proposal') then
    if jsonb_typeof(b->'title') is distinct from 'string' or length(btrim(b->>'title')) not between 1 and 120
      or jsonb_typeof(b->'description') is distinct from 'string' or length(btrim(b->>'description')) not between 1 and 2000
      or jsonb_typeof(b->'is_public') is distinct from 'boolean'
      or jsonb_typeof(b->'evidence') is distinct from 'string' or length(b->>'evidence')>10000 then
      perform public.admin_setup_fail('invalid_request',422); end if;
  end if;
  if op='create' and (jsonb_typeof(b->'accused_trainer_id') is distinct from 'string'
    or (b->>'accused_trainer_id')!~*'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$') then
    perform public.admin_setup_fail('invalid_request',422); end if;
  if op in ('cancel','correct') and (jsonb_typeof(b->'reason') is distinct from 'string'
    or length(btrim(b->>'reason')) not between 1 and 500) then perform public.admin_setup_fail('invalid_request',422); end if;
  if op not in ('resolve','correct') then return; end if;
  if b->>'verdict' is null or b->>'verdict' not in ('guilty','not_guilty')
    or jsonb_typeof(b->'decision_summary') is distinct from 'string' or length(btrim(b->>'decision_summary')) not between 1 and 2000
    or jsonb_typeof(b->'sanctions') is distinct from 'array' or jsonb_array_length(b->'sanctions')>5 then
    perform public.admin_setup_fail('invalid_request',422); end if;
  for p in select value from jsonb_array_elements(b->'sanctions') loop
    typ=p->>'type';
    if jsonb_typeof(p)<>'object' or typ is null or typ=any(kinds) then perform public.admin_setup_fail('invalid_request',422); end if;
    kinds=array_append(kinds,typ);
    if typ='store_ban' then
      if p-array['type','duration_matchdays']<>'{}' or jsonb_typeof(p->'duration_matchdays') is distinct from 'number'
        or (p->>'duration_matchdays')!~'^[0-9]+$' or (p->>'duration_matchdays')::numeric not between 1 and 1000 then
        perform public.admin_setup_fail('invalid_request',422); end if;
    elsif typ='coins_reduction' then
      if p-array['type','amount']<>'{}' or jsonb_typeof(p->'amount') is distinct from 'number'
        or (p->>'amount')!~'^[0-9]+$' or (p->>'amount')::numeric not between 1 and 2147483647 then
        perform public.admin_setup_fail('invalid_request',422); end if;
    elsif typ='points_reduction' then
      if p-array['type','amount']<>'{}' or jsonb_typeof(p->'amount') not in ('string','number') or p->>'amount' is null
        or (p->>'amount')!~'^[0-9]+(\.[0-9]{1,2})?$' or (p->>'amount')::numeric<=0 or (p->>'amount')::numeric>9999999999.99 then
        perform public.admin_setup_fail('invalid_request',422); end if;
    elsif typ in ('pokemon_release','other') then
      if p-array['type','text']<>'{}' or jsonb_typeof(p->'text') is distinct from 'string'
        or length(btrim(p->>'text')) not between 1 and 2000 then perform public.admin_setup_fail('invalid_request',422); end if;
    else perform public.admin_setup_fail('invalid_request',422); end if;
    if b->>'verdict'='not_guilty' and typ in ('store_ban','coins_reduction','points_reduction') then
      perform public.admin_setup_fail('invalid_request',422); end if;
  end loop;
end $$;

-- Future configuration cannot remove a round required by an outstanding ban.
create function public.trials_config_guard() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if exists(select 1 from public.penalties p where p.season_id=new.season_id
    and p.trial_revision_id is not null and p.penalty_type='store_ban' and public.trials_penalty_current(p)
    and p.end_matchday_number>new.total_matchdays and p.end_matchday_number>=new.effective_from_matchday
    and not exists(select 1 from public.matchdays d where d.season_id=p.season_id and d.number=p.end_matchday_number and d.status='closed')) then
    perform public.admin_setup_fail('invalid_config');
  end if;
  return new;
end $$;
create trigger trial_ban_config_boundary before insert or update on public.season_config_versions
  for each row execute function public.trials_config_guard();

create function public.api_trial_mutate(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare r jsonb=p_request; b jsonb=r->'body'; op text=r->>'operation'; actor uuid=(r->>'actor_trainer_id')::uuid;
  sid uuid=(r->>'season_id')::uuid; cid uuid=(r->>'resource_id')::uuid; k text=r->>'idempotency_key';
  scope text; prior public.admin_operation_receipts; t public.trainers; s public.seasons;
  c public.trial_cases; player public.season_players; d public.matchdays; oldban public.penalties;
  oldpoints public.penalties; oldcoins public.penalties; p jsonb; typ text;
  oldcoin integer=0; newcoin integer=0; oldpoint numeric=0; newpoint numeric=0;
  newduration integer=0; oldduration integer=0; first_round integer; last_round integer; total integer;
  effective integer; h uuid=gen_random_uuid(); peid uuid; coinid uuid; nr bigint; number bigint;
  oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid(); stamp timestamptz; result jsonb; details jsonb;
begin
  perform public.trials_validate_body(op,b);
  select * into t from public.trainers where id=actor for share;
  if not found or not t.globally_enabled then perform public.admin_setup_fail('trainer_disabled',403); end if;
  if sid is null or k is null or k!~'^[!-~]{1,128}$' then perform public.admin_setup_fail('invalid_request',422); end if;
  scope=public.admin_setup_scope('trial_'||op,r);
  perform pg_advisory_xact_lock(hashtextextended(actor::text||scope||':'||k,0));
  select * into prior from public.admin_operation_receipts where actor_trainer_id=actor and operation_scope=scope and idempotency_key=k;
  if found then
    if prior.request_hash<>encode(sha256(convert_to(r::text,'UTF8')),'hex') then perform public.admin_setup_fail('idempotency_conflict'); end if;
    return prior.response_json||'{"replayed":true}'::jsonb;
  end if;
  select * into s from public.seasons where id=sid for no key update;
  if not found then perform public.admin_setup_fail('season_not_found',404); end if;
  perform 1 from public.season_players where season_id=sid order by id for update;
  if not exists(select 1 from public.season_players where season_id=sid and trainer_id=actor and status='active') then
    perform public.admin_setup_fail('participant_inactive',403); end if;
  if s.status not in ('active','finished','archived') then perform public.admin_setup_fail('season_unavailable'); end if;
  select * into d from public.matchdays where id=s.current_matchday_id and season_id=sid for update;
  if op='create' then
    select * into player from public.season_players where season_id=sid and trainer_id=(b->>'accused_trainer_id')::uuid;
    if not found then perform public.admin_setup_fail('accused_not_found',404); end if;
    insert into public.trial_case_counters(season_id) values(sid) on conflict do nothing;
    update public.trial_case_counters set next_number=next_number+1 where season_id=sid returning next_number-1 into number;
    cid=gen_random_uuid();
    insert into public.trial_cases(id,season_id,accused_trainer_id,created_by_trainer_id,title,description,payload,authority_version,case_number)
      values(cid,sid,player.trainer_id,actor,b->>'title',b->>'description',jsonb_build_object('is_public',b->'is_public','evidence',b->'evidence'),1,number)
      returning * into c;
  else
    select * into c from public.trial_cases where id=cid and season_id=sid for update;
    if not found then perform public.admin_setup_fail('trial_not_found',404); end if;
    if c.authority_version is distinct from 1 then perform public.admin_setup_fail('trial_source_unsupported'); end if;
    if c.revision<>(b->>'expected_case_revision')::bigint then perform public.admin_setup_fail('stale_revision'); end if;
    if op in ('proposal','cancel') and actor<>c.created_by_trainer_id then perform public.admin_setup_fail('creator_required',403); end if;
    if op in ('proposal','cancel','resolve') and (c.status<>'open' or c.decision_revision_id is not null) then
      perform public.admin_setup_fail('trial_not_open'); end if;
    if op='correct' and (c.status not in ('resolved','dismissed') or c.decision_revision_id is null) then
      perform public.admin_setup_fail('trial_not_resolved'); end if;
    select * into player from public.season_players where season_id=sid and trainer_id=c.accused_trainer_id;
    if not found then perform public.admin_setup_fail('accused_not_found',404); end if;
  end if;
  nr=c.revision+1; stamp=clock_timestamp();
  if op in ('create','proposal') then
    details=jsonb_build_object('title',b->'title','description',b->'description','is_public',b->'is_public','evidence',b->'evidence');
  else
    details=jsonb_build_object('title',c.title,'description',c.description,'is_public',c.payload->'is_public','evidence',c.payload->'evidence');
  end if;
  if op in ('resolve','correct') then
    select * into oldcoins from public.penalties where trial_revision_id=c.decision_revision_id and penalty_type='coins_reduction';
    select * into oldpoints from public.penalties where trial_revision_id=c.decision_revision_id and penalty_type='points_reduction';
    select * into oldban from public.penalties where trial_revision_id=c.decision_revision_id and penalty_type='store_ban';
    oldcoin=coalesce(oldcoins.amount,0); oldpoint=coalesce(oldpoints.points_amount,0); oldduration=coalesce(oldban.duration_matchdays,0);
    select coalesce((value->>'amount')::integer,0) into newcoin from jsonb_array_elements(b->'sanctions') where value->>'type'='coins_reduction';
    select coalesce((value->>'amount')::numeric,0) into newpoint from jsonb_array_elements(b->'sanctions') where value->>'type'='points_reduction';
    select coalesce((value->>'duration_matchdays')::integer,0) into newduration from jsonb_array_elements(b->'sanctions') where value->>'type'='store_ban';
    newcoin=coalesce(newcoin,0); newpoint=coalesce(newpoint,0); newduration=coalesce(newduration,0);
    if s.status<>'active' and (newcoin>oldcoin or newpoint>oldpoint or newduration>oldduration) then
      perform public.admin_setup_fail('season_not_active'); end if;
    if newpoint>oldpoint then
      if d.id is null or d.status not in ('scheduled','open') or not exists(select 1 from public.participant_memberships_at(sid,d.number)
        where season_player_id=player.id) then perform public.admin_setup_fail('no_future_points_capture'); end if;
      select total_matchdays into total from public.season_config_versions where id=d.season_config_version_id;
      if total is null or d.number>total then perform public.admin_setup_fail('no_future_points_capture'); end if;
    end if;
    effective=coalesce(oldpoints.effective_from_matchday_number,d.number);
    if newduration>0 then
      first_round=coalesce(oldban.start_matchday_number,d.number); last_round=first_round+newduration-1;
      if newduration>oldduration then
        select total_matchdays into total from public.season_config_versions where id=d.season_config_version_id;
        if d.id is null or d.status not in ('scheduled','open') or total is null or last_round<d.number or last_round>total
          or exists(select 1 from public.season_config_versions cfg where cfg.season_id=sid
            and cfg.effective_from_matchday<=last_round and cfg.effective_from_matchday>d.number and cfg.total_matchdays<last_round) then
          perform public.admin_setup_fail('store_ban_rounds_unavailable'); end if;
      end if;
    end if;
  end if;
  insert into public.trial_case_revisions(id,case_id,season_id,revision,operation,actor_trainer_id,previous_decision_id,
    details,verdict,decision_summary,reason,sanctions,created_at)
    values(h,cid,sid,nr,op,actor,case when op='correct' then c.decision_revision_id end,details,
      case when op in ('resolve','correct') then b->>'verdict' end,coalesce(b->>'decision_summary',''),
      coalesce(b->>'reason',''),coalesce(b->'sanctions','[]'),stamp);
  if op in ('resolve','correct') then
    for p in select value from jsonb_array_elements(b->'sanctions') order by value->>'type' loop
      typ=p->>'type'; peid=gen_random_uuid();
      insert into public.penalties(id,season_id,trainer_id,trial_case_id,trial_revision_id,penalty_type,amount,points_amount,
        duration_matchdays,start_matchday_number,end_matchday_number,effective_from_matchday_number,payload,created_by_trainer_id,created_at)
        values(peid,sid,player.trainer_id,cid,h,typ,case when typ='coins_reduction' then newcoin else 0 end,
          case when typ='points_reduction' then newpoint end,case when typ='store_ban' then newduration end,
          case when typ='store_ban' then first_round end,case when typ='store_ban' then last_round end,
          case when typ='points_reduction' then effective end,
          case when typ in ('pokemon_release','other') then jsonb_build_object('text',p->>'text') else '{}'::jsonb end,actor,stamp);
      if typ='coins_reduction' then coinid=peid; end if;
    end loop;
    if newcoin<>oldcoin then
      insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type,reference_type,reference_id,
        created_by_trainer_id,created_at,trial_case_id,trial_revision_id,trial_penalty_id,trial_previous_penalty_id)
        values(sid,player.trainer_id,player.id,oldcoin-newcoin,case when newcoin>oldcoin then 'penalty' else 'compensation' end,
          'trial_decision',h,actor,stamp,cid,h,coinid,oldcoins.id);
    end if;
  end if;
  update public.trial_cases set revision=nr,title=details->>'title',description=details->>'description',
    payload=jsonb_build_object('is_public',details->'is_public','evidence',details->'evidence'),
    status=case when op='cancel' then 'cancelled' when op in ('resolve','correct') then
      case when b->>'verdict'='guilty' then 'resolved' else 'dismissed' end else 'open' end,
    verdict=case when op in ('resolve','correct') then b->>'verdict' else verdict end,
    decision_revision_id=case when op in ('resolve','correct') then h else decision_revision_id end,
    resolved_at=case when op in ('resolve','correct') then stamp else resolved_at end
    where id=cid returning * into c;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,payload,created_at)
    values(eid,sid,case op when 'create' then 'TRIAL_CREATED' when 'proposal' then 'TRIAL_UPDATED'
      when 'resolve' then 'TRIAL_RESOLVED' when 'cancel' then 'TRIAL_CANCELLED' else 'TRIAL_CORRECTED' end,
      actor,c.accused_trainer_id,'admin','trial:'||oid::text,jsonb_build_object('case_id',cid,'revision_id',h,'operation_id',oid),stamp);
  result=jsonb_build_object('operation_id',oid,'event_id',eid,'season_id',sid,'case_id',cid,'case_number',c.case_number,
    'case_revision',nr,'operation',op,'status',c.status,'verdict',c.verdict,'decision_revision_id',c.decision_revision_id,
    'actor_trainer_id',actor,'changed_at',stamp,'replayed',false);
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,actor,sid,scope,k,encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

create function public.api_trials_read(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare actor uuid=(p_request->>'actor_trainer_id')::uuid; sid uuid=(p_request->>'season_id')::uuid;
  cid uuid=(p_request->>'resource_id')::uuid; t public.trainers; s public.seasons; c public.trial_cases;
  result jsonb='[]'; item jsonb; priv boolean; pub boolean; history jsonb; sanctions jsonb;
begin
  select * into t from public.trainers where id=actor;
  if not found or not t.globally_enabled then perform public.admin_setup_fail('trainer_disabled',403); end if;
  select * into s from public.seasons where id=sid;
  if not found then perform public.admin_setup_fail('season_not_found',404); end if;
  for c in select * from public.trial_cases where season_id=sid and (cid is null or id=cid) order by case_number desc nulls last,id loop
    priv=coalesce(t.is_admin or actor in (c.created_by_trainer_id,c.accused_trainer_id),false);
    pub=coalesce(lower(c.payload->>'is_public'),'true') not in ('false','0','no') and c.status<>'cancelled' and s.status<>'discarded';
    if not priv and not pub then continue; end if;
    select coalesce(jsonb_agg(jsonb_strip_nulls(jsonb_build_object('id',p.id,'type',p.penalty_type,
      'amount',case when p.penalty_type='points_reduction' then coalesce(p.points_amount,p.amount::numeric)
        when p.penalty_type='coins_reduction' then p.amount::numeric end,
      'duration_matchdays',p.duration_matchdays,'start_matchday_number',p.start_matchday_number,'end_matchday_number',p.end_matchday_number)) order by p.penalty_type),'[]')
      into sanctions from public.penalties p where p.trial_case_id=c.id and p.trial_revision_id=c.decision_revision_id;
    select coalesce(jsonb_agg(jsonb_build_object('id',h.id,'revision',h.revision,'operation',h.operation,'actor_trainer_id',h.actor_trainer_id,
      'created_at',h.created_at,'previous_decision_id',h.previous_decision_id,'details',h.details,'verdict',h.verdict,
      'decision_summary',h.decision_summary,'reason',h.reason,'sanctions',h.sanctions) order by h.revision),'[]') into history
      from public.trial_case_revisions h where h.case_id=c.id and priv;
    item=jsonb_build_object('id',c.id,'season_id',sid,'case_number',c.case_number,'revision',c.revision,'title',c.title,
      'description',c.description,'status',c.status,'verdict',c.verdict,'is_public',coalesce(lower(c.payload->>'is_public'),'true') not in ('false','0','no'),
      'created_at',c.created_at,'updated_at',c.updated_at,'resolved_at',c.resolved_at,'sanctions',sanctions,
      'detail',case when priv then jsonb_build_object('evidence',coalesce(c.payload->>'evidence',''),'history',history) end);
    result=result||jsonb_build_array(item);
  end loop;
  if cid is not null then
    if jsonb_array_length(result)=0 then perform public.admin_setup_fail('trial_not_found',404); end if;
    return result->0;
  end if;
  return jsonb_build_object('season_id',sid,'cases',result);
end $$;

-- Current public columns are retained; only explicitly safe evidence is added.
create or replace view public.public_trial_cases as
select c.id,c.season_id,c.matchday_id,c.accused_trainer_id,c.created_by_trainer_id,c.title,c.description,c.status,
  c.created_at,c.resolved_at,c.updated_at,c.case_number,c.revision,c.verdict
from public.trial_cases c left join public.seasons s on s.id=c.season_id
where c.status<>'cancelled' and (c.payload->>'is_public' is null or lower(c.payload->>'is_public') not in ('false','0','no'))
  and (c.season_id is null or s.status<>'discarded');

create or replace view public.public_penalties as
select p.id,p.season_id,p.trainer_id,p.matchday_id,p.trial_case_id,p.penalty_type,p.amount,p.created_at,p.resolved_at,
  p.points_amount,p.duration_matchdays,p.start_matchday_number,p.end_matchday_number,p.effective_from_matchday_number,p.trial_revision_id
from public.penalties p join public.seasons s on s.id=p.season_id
where s.status<>'discarded' and (p.trial_revision_id is null or exists(select 1 from public.trial_cases c
  where c.id=p.trial_case_id and c.decision_revision_id=p.trial_revision_id))
  and (p.trial_case_id is null or exists(select 1 from public.trial_cases c where c.id=p.trial_case_id
    and c.status<>'cancelled' and coalesce(lower(c.payload->>'is_public'),'true') not in ('false','0','no')));

-- Public accumulated points come ONLY from official frozen captures. A correction
-- after finish never changes this projection, rewards, positions or League Hall.
create view public.public_sanctioned_points with(security_invoker=true,security_barrier=true) as
with captures as (
  select s.season_id,s.matchday_id,d.number,(v->>'trainer_id')::uuid as season_player_id,
    (v->>'points_awarded')::numeric as points_awarded,
    coalesce((v#>>'{penalties,points_reduction}')::numeric,0) as points_reduction,
    coalesce((v#>>'{penalties,dead_points_penalty}')::numeric,0) as dead_points_penalty
  from public.public_matchday_snapshots s join public.public_matchdays d on d.id=s.matchday_id
    cross join lateral jsonb_array_elements(s.snapshot->'standings') v
  where s.snapshot_schema_version=2
), sums as (
  select season_id,season_player_id,sum(points_awarded) as earned_points from captures group by season_id,season_player_id
), latest as (
  select distinct on(season_id,season_player_id) * from captures order by season_id,season_player_id,number desc
)
select a.season_id,a.season_player_id,a.earned_points,b.points_reduction,b.dead_points_penalty,
  a.earned_points-b.points_reduction-b.dead_points_penalty as sanctioned_points,b.matchday_id as source_matchday_id
from sums a join latest b using(season_id,season_player_id);
revoke all on public.public_sanctioned_points from public,anon;
grant select on public.public_sanctioned_points to authenticated,service_role;

create or replace function public.matchday_context(op text,r jsonb) returns jsonb
language plpgsql set search_path=pg_catalog,public as $$
declare sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid;
  d public.matchdays; c public.season_config_versions; inputs jsonb; players jsonb; matches jsonb; result jsonb;
begin
  select * into d from public.matchdays where id=did;
  select * into c from public.season_config_versions where id=d.season_config_version_id;
  if (c.rules_json->>'last_b_gets_steal')::boolean and exists (
    select 1 from public.participant_memberships_at(sid,d.number) m join public.divisions v on v.id=m.division_id where v.code='B'
  ) and not exists (
    select 1 from public.shop_items where code='robar_pokemon' and acquisition_mode='purchasable'
  ) then perform public.admin_setup_fail('reward_item_unavailable'); end if;
  if op='correct' then
    select snapshot->'inputs' into inputs from public.matchday_snapshots where matchday_id=did;
  else
    if exists(select 1 from public.season_players p where p.season_id=sid and (p.status='active' or d.number<p.status_effective_matchday_number) and p.current_save_file_id is not null
      and not exists(select 1 from public.pokemon_identity_revisions i where i.save_file_id=p.current_save_file_id)) then
      perform public.admin_setup_fail('ranking_inputs_unavailable'); end if;
    select jsonb_agg(jsonb_build_object('id',p.id,'trainer_id',p.trainer_id,'ranking_key',t.slug,'division',v.code,
      'dead_count',(select count(*) from public.pokemon_observations o where o.save_file_id=p.current_save_file_id and o.source='box' and o.box_number=8)
        +greatest((select count(*) from public.redemptions e where e.season_id=sid and e.trainer_id=p.trainer_id and e.effect_code='revive' and e.status='applied'),
          (select count(*) from public.purchases u join public.shop_items i on i.id=u.shop_item_id where u.season_player_id=p.id and u.status='used' and i.code='revivir_pokemon'))
        +2*st.revived_after_wipe,
      'points_reduction',coalesce((select sum(greatest(coalesce(points_amount,amount::numeric),0)) from public.penalties pe where pe.season_id=sid and pe.trainer_id=p.trainer_id
        and public.trials_penalty_current(pe) and (pe.effective_from_matchday_number is null or pe.effective_from_matchday_number<=d.number)
        and pe.penalty_type='points_reduction' and (pe.matchday_id is null or pe.matchday_id=did)
        and (pe.trial_case_id is null or exists(select 1 from public.trial_cases tc where tc.id=pe.trial_case_id and tc.status='resolved'
          and tc.accused_trainer_id=p.trainer_id and (tc.season_id is null or tc.season_id=sid)))),0)::text,
      'coins_reduction',coalesce((select sum(greatest(amount,0)) from public.penalties pe where pe.season_id=sid and pe.trainer_id=p.trainer_id
        and public.trials_penalty_current(pe) and pe.penalty_type='coins_reduction' and (pe.matchday_id is null or pe.matchday_id=did)
        and (pe.trial_case_id is null or exists(select 1 from public.trial_cases tc where tc.id=pe.trial_case_id and tc.status='resolved'
          and tc.accused_trainer_id=p.trainer_id and (tc.season_id is null or tc.season_id=sid)))) ,0)) order by p.id) into players
      from public.season_players p join public.trainers t on t.id=p.trainer_id
      join public.season_player_stats st on st.season_player_id=p.id
      join public.participant_memberships_at(sid,d.number) m on m.season_player_id=p.id and m.effective_from_matchday_number<=d.number
        and coalesce(m.effective_to_matchday_number,d.number)>=d.number
      join public.divisions v on v.id=m.division_id where p.season_id=sid;
    select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'player_a_id',x.player_a_id,'player_b_id',x.player_b_id,
      'winner_id',x.winner_id,'division',v.code) order by x.id),'[]'::jsonb) into matches
      from public.matches x join public.divisions v on v.id=x.division_id where x.matchday_id=did;
    inputs=jsonb_build_object('season_id',sid,'day_id',did,'number',d.number,'results_revision',d.results_revision,
      'config',jsonb_build_object('id',c.id,'name',c.name,'effective_from_matchday',c.effective_from_matchday,
        'total_matchdays',c.total_matchdays,'division_sizes',c.division_sizes,'promotion_relegation_count',c.promotion_relegation_count,
        'scoring_json',c.scoring_json,'coin_rewards_json',c.coin_rewards_json,'rules_json',c.rules_json),
      'players',coalesce(players,'[]'::jsonb),'matches',matches);
  end if;
  result=jsonb_build_object('inputs',inputs,'external_facts',public.matchday_external_facts(sid),
    'snapshot_revision',coalesce((select revision from public.matchday_snapshots where matchday_id=did),0),
    'next_config',(select to_jsonb(x) from public.season_config_versions x where x.season_id=sid and x.effective_from_matchday<=d.number+1
      order by x.effective_from_matchday desc limit 1),
    'existing_next_promotions',exists(select 1 from public.shop_promotions p join public.matchdays md on md.id=p.matchday_id
      where p.season_id=sid and md.number=d.number+1),
    'catalog',(select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'code',i.code,'name',i.name,'category',i.category,'base_price',i.base_price,'enabled',i.enabled) order by i.id),'[]'::jsonb)
      from public.shop_items i where i.acquisition_mode='purchasable'),
    'purchase_history',(select coalesce(jsonb_agg(jsonb_build_object('name',i.name,'number',coalesce(md.number,0),'quantity',p.quantity) order by p.id),'[]'::jsonb)
      from public.purchases p join public.shop_items i on i.id=p.shop_item_id left join public.matchdays md
      on md.id=coalesce((p.metadata#>>'{normal_purchase,matchday_id}')::uuid,(p.metadata#>>'{promotional_purchase,matchday_id}')::uuid,p.origin_matchday_id)
      where p.season_id=sid and p.status not in ('cancelled','refunded')),
    'promotion_history',(select coalesce(jsonb_agg(jsonb_build_object('item',i.name,'jornada',md.number) order by p.id),'[]'::jsonb)
      from public.shop_promotions p join public.shop_items i on i.id=p.shop_item_id join public.matchdays md on md.id=p.matchday_id where p.season_id=sid));
  return result;
end $$;


do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and (p.proname like 'trials_%' or p.proname in ('api_trial_mutate','api_trials_read')) loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
commit;
