"""Synthetic actual-RPC League acceptance, no remote connections or save writes.

validate() always rolls back. validate_concurrency() requires a separate pristine
disposable cluster because its synthetic fixture must be visible to two clients.
"""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from itertools import combinations, product
import json
import re
from threading import Barrier
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from app.api.matchday_models import CloseDayBody
from app.application.daily_ranking import RankingDecisionRequired
from app.application.matchdays import plan_close
from tools.validate_phase075_deaths import seed as death_seed


def fixture(total=4, two_divisions=False):
    sql, v = death_seed()
    original = sql
    players = [v['pid']] + [str(uuid4()) for _ in range(4)]
    trainers = [v['tid']] + [str(uuid4()) for _ in range(4)]
    division = re.search(r"insert into public.divisions.*?values\('([^']+)'", sql, re.S).group(1)
    sql = sql.replace("1,4,1,'{\"A\":1}','{\"1\":0}','{\"1\":4}'",
        f"1,{total},1,'{{\"A\":5}}','"+json.dumps({str(i):0 for i in range(1,6)})+"','"+
        json.dumps({str(i):17 for i in range(1,6)})+"'")
    sql = sql.replace(f",('{v['day2']}','{v['sid']}',2,'{v['config']}'),('{v['day3']}','{v['sid']}',3,'{v['config']}')", "")
    sql = sql.replace('pg_temp.observe(', 'pg_temp.observe_0(').replace('pg_temp.confirm(', 'pg_temp.confirm_0(')
    observe = re.search(r'create or replace function pg_temp.observe\(.*?end \$observe\$;', original, re.S).group(0)
    confirm = re.search(r'create or replace function pg_temp.confirm\(.*?end \$confirm\$;', original, re.S).group(0)
    for index in range(1, 5):
        pid, tid = players[index], trainers[index]
        entities = [str(uuid4()) for _ in v['entities']]
        ids = ','.join(f"'{ent}'::uuid" for ent in entities)
        sql += f"""
insert into public.trainers(id,display_name,slug,is_admin,auth_user_id)
 values('{tid}','075 Player {index}','075-player-{tid}',false,gen_random_uuid());
insert into public.season_players(id,season_id,trainer_id,status,dead_box_number)
 values('{pid}','{v['sid']}','{tid}','active',7);
insert into public.season_player_stats(season_player_id,season_id,trainer_id)
 values('{pid}','{v['sid']}','{tid}') on conflict do nothing;
insert into public.division_memberships(season_id,season_player_id,division_id,effective_from_matchday_number)
 values('{v['sid']}','{pid}','{division}',1);
insert into public.pokemon_entities(id,season_id,owner_trainer_id,identity_status,identity_schema_version,candidate_key,initial_evidence)
 select e,'{v['sid']}','{tid}','unambiguous',1,lpad(n::text,64,'0'),jsonb_build_object('fixture',n)
 from unnest(array[{ids}]) with ordinality x(e,n);
"""
        for function, name in ((observe, 'observe'), (confirm, 'confirm')):
            function = function.replace(v['pid'], pid).replace(v['tid'], tid)
            if name == 'confirm':
                function = function.replace(f"'actor_trainer_id','{tid}'", f"'actor_trainer_id','{v['tid']}'")
            for before, after in zip(v['entities'], entities): function = function.replace(before, after)
            sql += function.replace('pg_temp.'+name+'(', f'pg_temp.{name}_{index}(')+'\n'
    if two_divisions:
        division_b=str(uuid4())
        sql=sql.replace('division_count,division_sizes,scoring_json',
                        'division_count,division_sizes,promotion_relegation_count,scoring_json')
        sql=sql.replace(f"1,{total},1,'{{\"A\":5}}',",f"1,{total},2,'{{\"A\":3,\"B\":2}}',1,")
        sql+=f"""
insert into public.divisions(id,season_id,code,name,tier_order) values('{division_b}','{v['sid']}','B','B',2);
update public.division_memberships set division_id='{division_b}' where season_id='{v['sid']}'
 and season_player_id in ('{players[0]}','{players[1]}');
"""
    return sql.removeprefix('\nbegin;'), dict(v, players=players, trainers=trainers)


def connect(pg):
    return psycopg.connect(host='127.0.0.1', port=pg.port, user='supabase_admin', dbname=pg.database)


def value(conn, sql, args=()):
    return conn.execute(sql, args).fetchone()[0]


def rpc(conn, name, body):
    assert name in ('api_admin_matchday', 'api_admin_matchday_context')
    return value(conn, f'select public.{name}(%s::jsonb)', (Jsonb(body),))


def request(v, day, key, body):
    return dict(actor_trainer_id=v['tid'], season_id=v['sid'], resource_id=day,
                idempotency_key=key, body=body)


def confirm(conn, index, actual, segment):
    return value(conn, f'select pg_temp.confirm_{index}(%s,0,%s)', (actual, segment))


def initialize(conn, total=4, two_divisions=False):
    sql, v = fixture(total,two_divisions)
    conn.execute(sql)
    conn.execute('set local role service_role')
    for index in range(5): value(conn, f"select pg_temp.observe_{index}('{{}}'::integer[])")
    return v


def winners(players, target):
    pairs = list(combinations(players, 2))
    for bits in product((0, 1), repeat=len(pairs)):
        won = [pair[bit] for pair, bit in zip(pairs, bits)]
        if [won.count(pid) for pid in players] == target:
            return {frozenset(pair): winner for pair, winner in zip(pairs, won)}
    raise AssertionError('Impossible synthetic tournament')


def open_and_results(conn, v, day, number, target):
    revision = value(conn, 'select revision from public.matchdays where id=%s', (day,))
    req = request(v, day, f'075-open-{number}', dict(expected_revision=revision))
    opened = rpc(conn, 'api_admin_matchday', dict(operation='open', request=req))
    assert opened['state'] == 'open'
    matches = conn.execute('select id,player_a_id,player_b_id from public.matches where matchday_id=%s order by id', (day,)).fetchall()
    assert len(matches) == 10
    expected = winners(v['players'], target)
    req = request(v, day, f'075-results-{number}', dict(expected_results_revision=opened['results_revision'],
        results=[dict(match_id=str(mid), winner_season_player_id=expected[frozenset((str(a),str(b)))]) for mid,a,b in matches]))
    rpc(conn, 'api_admin_matchday', dict(operation='results', request=req))


def prepare_close(conn, v, day, key, corrections=None):
    revision = value(conn, 'select results_revision from public.matchdays where id=%s', (day,))
    operation='correct' if corrections is not None else 'close'
    body=dict(expected_results_revision=revision)
    if corrections is not None:
        snapshot_revision=value(conn,'select revision from public.matchday_snapshots where matchday_id=%s',(day,))
        body=dict(expected_snapshot_revision=snapshot_revision,reason='Isolated audited result correction',results=corrections)
    req = request(v, day, key, body)
    context = rpc(conn, 'api_admin_matchday_context', dict(operation=operation, request=req))
    try:
        plan = plan_close(context['context'], corrections)
    except RankingDecisionRequired as exc:
        now = (datetime.now(timezone.utc)-timedelta(seconds=2)).isoformat()
        decisions = [dict(player_ids=g['player_ids'], reason='Isolated recorded extra battle fixture',
            battles=[dict(player_a_id=a,player_b_id=b,winner_id=a,played_at=now,
                          evidence='Synthetic witnessed extra 1v1 result')
                     for a,b in combinations(g['player_ids'],2)])
            for g in exc.review['groups'] if g['consequences']]
        req['body']['tie_resolution'] = dict(input_hash=exc.review['input_hash'], orders=decisions)
        from app.api.matchday_models import CorrectDayBody
        model=CorrectDayBody if corrections is not None else CloseDayBody
        req['body'] = model.model_validate(req['body']).model_dump(mode='json')
        plan = plan_close(context['context'], corrections, tie_resolution=req['body']['tie_resolution'])
    return dict(operation=operation, request=req, input_hash=context['input_hash'], plan=plan)


def validate(pg):
    checks=[]
    with connect(pg) as conn:
        try:
            v=initialize(conn)
            counts=[[1,7,12,20],[0,1,3,5],[0,1,2,3],[0,0,0,0],[0,2,3,4]]
            previous=[0]*5
            frozen=[]
            for number in range(1,5):
                day=str(value(conn,'select current_matchday_id from public.seasons where id=%s',(v['sid'],)))
                for i in range(5):
                    confirm(conn,i,counts[i][number-1],counts[i][number-1]-previous[i])
                    previous[i]=counts[i][number-1]
                target=[3,3,2,1,1] if number<4 else [3,2,3,1,1]
                open_and_results(conn,v,day,number,target)
                envelope=prepare_close(conn,v,day,f'075-close-{number}')
                if number==1:
                    forged=deepcopy(envelope);forged['plan']['standings'][0]['points_awarded']+=1
                    try:
                        with conn.transaction():
                            try:
                                rpc(conn,'api_admin_matchday',forged)
                                raise AssertionError('Forged win points accepted')
                            except psycopg.Error as exc:
                                assert exc.sqlstate=='PT409'
                                raise _ExpectedRollback()
                    except _ExpectedRollback:
                        pass
                receipt=rpc(conn,'api_admin_matchday',envelope)
                assert receipt['state']=='closed'
                assert rpc(conn,'api_admin_matchday',envelope)['replayed'] is True
                assert value(conn,'select count(*) from public.coin_transactions where reward_matchday_id=%s',(day,))==5
                assert value(conn,'select sum(amount) from public.coin_transactions where reward_matchday_id=%s',(day,))==85
                assert value(conn,"select count(*) from public.purchases where origin_matchday_id=%s and status='pending'",(day,))==2
                assert value(conn,'select count(*) from public.matchday_snapshot_revisions where matchday_id=%s',(day,))==1
                frozen.append(value(conn,'select snapshot from public.matchday_snapshots where matchday_id=%s',(day,)))
                general=value(conn,'select public.league_general_read(%s)',(v['sid'],))
                if number==2:
                    first=next(r for r in general['rows'] if r['season_player_id']==v['players'][0])
                    assert first['historical_deaths']==7
                    first_segment=next(r for r in frozen[0]['standings'] if r['trainer_id']==v['players'][0])
                    second_segment=next(r for r in frozen[1]['standings'] if r['trainer_id']==v['players'][0])
                    assert first_segment['metadata']['actual_segment_deaths']==1
                    assert second_segment['metadata']['actual_segment_deaths']==6
                checks.append(f'J{number}: global10matches +1wins exact5coinpayouts/2prizes close/replay')
            general=value(conn,'select public.league_general_read(%s)',(v['sid'],))
            rows={r['season_player_id']:r for r in general['rows']}
            assert rows[v['players'][0]]['normal_wins']==12 and Decimal(rows[v['players'][0]]['total_points'])==Decimal('10.0')
            assert rows[v['players'][1]]['normal_wins']==11 and Decimal(rows[v['players'][1]]['total_points'])==Decimal('10.5')
            title=value(conn,'select public.championship_context(%s)',(v['sid'],))
            assert title['champion_trainer_id']==v['trainers'][1],title
            for index,snapshot in enumerate(frozen):
                assert value(conn,'select s.snapshot from public.matchday_snapshots s join public.matchdays d on d.id=s.matchday_id where s.season_id=%s order by d.number offset %s limit 1',(v['sid'],index))==snapshot
            checks.append('12wins-2.0=10.0 loses championship to11wins-0.5=10.5; cumulativepenalties notduplicated; snapshotsstable')
            matches=conn.execute('select id,player_a_id,player_b_id,winner_id from public.matches where matchday_id=%s',(day,)).fetchall()
            changes=[dict(match_id=str(mid),winner_season_player_id=str(b if w==a else a)) for mid,a,b,w in matches]
            correction=prepare_close(conn,v,day,'075-correct-final',changes)
            rpc(conn,'api_admin_matchday',correction)
            assert rpc(conn,'api_admin_matchday',correction)['replayed'] is True
            assert value(conn,'select count(*) from public.coin_transactions where reward_matchday_id=%s',(day,))==5
            assert value(conn,"select count(*) from public.purchases where origin_matchday_id=%s and status='pending'",(day,))==2
            assert value(conn,'select snapshot from public.matchday_snapshot_revisions where matchday_id=%s and revision=1',(day,))==frozen[-1]
            checks.append('auditedcorrect/replay keepsoriginalrevision, equalcoinpayoutnotrepeated, twoactiveprizes')
        finally:
            conn.rollback()
    return 'PASS: '+'; '.join(checks)


def validate_two_divisions(pg):
    with connect(pg) as conn:
        try:
            v=initialize(conn,total=2,two_divisions=True)
            for i in range(5): confirm(conn,i,0,0)
            open_and_results(conn,v,v['day1'],1,[4,3,2,1,0])
            envelope=prepare_close(conn,v,v['day1'],'075-two-divisions')
            plan=envelope['plan']
            assert plan['single_league_rewards'][0]['season_player_id']==v['players'][0]
            assert next(r for r in plan['standings'] if r['trainer_id']==v['players'][0])['division_id']=='B'
            assert plan['single_league_rewards'][1]['season_player_id']==v['players'][-1]
            rpc(conn,'api_admin_matchday',envelope)
            nextday=value(conn,'select current_matchday_id from public.seasons where id=%s',(v['sid'],))
            assert value(conn,'select count(*) from public.matches where matchday_id=%s',(nextday,))==10
            assert value(conn,"select count(*) from public.participant_memberships_at(%s,2) m join public.divisions d on d.id=m.division_id where d.code='A'",(v['sid'],))==3
            assert value(conn,"select count(*) from public.participant_memberships_at(%s,2) m join public.divisions d on d.id=m.division_id where d.code='B'",(v['sid'],))==2
        finally:
            conn.rollback()
    return 'PASS: 2divisions retain3A/2B andmovements; globalRR10pairs; globalwinnerB/lastA prizes; nextday10pairs'


def validate_legacy(pg):
    from tools.validate_phase073_league import fixture as old_fixture, DAY, SEASON, TRAINER
    seed, _, players=old_fixture()
    with connect(pg) as conn:
        try:
            conn.execute(seed.removeprefix('\nbegin;').removeprefix('begin;'))
            req=dict(actor_trainer_id=TRAINER,season_id=SEASON,resource_id=DAY,
                     idempotency_key='075-historical-capture',body=dict(expected_results_revision=0))
            old=value(conn,"select public.matchday_context_v074('close',%s::jsonb)",(Jsonb(req),))
            old['external_facts']=value(conn,'select public.matchday_external_facts_v074(%s)',(SEASON,))
            plan=plan_close(old)
            value(conn,"select public.matchday_commit_close_v074('close',%s::jsonb,%s::jsonb,%s::jsonb)",
                  (Jsonb(req),Jsonb(old),Jsonb(plan)))
            snapshot=value(conn,'select snapshot from public.matchday_snapshots where matchday_id=%s',(DAY,))
            corrected=value(conn,"select public.matchday_context('correct',%s::jsonb)",(Jsonb(req),))
            assert corrected['inputs']['config']['scoring_mode']=='single_round_robin_v1'
            assert corrected['inputs']['config']['death_penalty_per_mon']=='0.1'
            legacy_plan=plan_close(corrected)
            assert next(r for r in legacy_plan['standings'] if r['trainer_id']==players[2])['points_awarded']==6
            assert legacy_plan['standings']==plan['standings']
            for operation in ('open','close'):
                try:
                    with conn.transaction():
                        try:
                            value(conn,'select public.matchday_lock(%s,%s::jsonb)',(operation,Jsonb(req)))
                            raise AssertionError('Legacy season silently entered new scoring')
                        except psycopg.Error as exc:
                            assert exc.sqlstate=='PT409' and str(exc).splitlines()[0]=='legacy_scoring_migration_required'
                            raise _ExpectedRollback()
                except _ExpectedRollback:
                    pass
            assert value(conn,'select snapshot from public.matchday_snapshots where matchday_id=%s',(DAY,))==snapshot
        finally:
            conn.rollback()
    return 'PASS: pre075closed073 +2/rate0.1 snapshot/correctioncontractunchanged; newopen/closeblockedexplicitlegacydecision'


class _ExpectedRollback(Exception):
    pass


def validate_concurrency(pg):
    """Call only on a dedicated disposable DB: commits synthetic fixture rows."""
    with connect(pg) as conn:
        v=initialize(conn,total=1)
        for i in range(5): confirm(conn,i,0,0)
        open_and_results(conn,v,v['day1'],1,[4,3,2,1,0])
        envelope=prepare_close(conn,v,v['day1'],'075-concurrent-close')
    barrier=Barrier(2)
    def close():
        with connect(pg) as conn:
            conn.execute('set local role service_role')
            barrier.wait(timeout=15)
            return rpc(conn,'api_admin_matchday',envelope)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:close(),range(2)))
    assert sorted(r['replayed'] for r in results)==[False,True],results
    with connect(pg) as conn:
        assert value(conn,'select count(*) from public.coin_transactions where reward_matchday_id=%s',(v['day1'],))==5
        assert value(conn,"select count(*) from public.purchases where origin_matchday_id=%s and status='pending'",(v['day1'],))==2
        assert value(conn,'select count(*) from public.matchday_snapshot_revisions where matchday_id=%s',(v['day1'],))==1
    return 'PASS: 2 concurrent actualRPC closes; onecommit/onereplay; exactly5coinpayouts/2prizes/1snapshot'
