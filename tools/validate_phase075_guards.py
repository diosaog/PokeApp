"""Focused adversarial 075 guards; synthetic loopback PostgreSQL, always rollback."""

from copy import deepcopy
from decimal import Decimal

import psycopg
from psycopg.types.json import Jsonb

from app.application.daily_ranking import RankingDecisionRequired
from app.application.matchdays import plan_close
from tools.validate_phase075_league import (
    confirm, connect, initialize, open_and_results, prepare_close, request, rpc, value,
)


def footprint(conn, v):
    return value(conn, """select jsonb_build_object(
      'coins',(select coalesce(jsonb_agg(to_jsonb(c) order by c.id),'[]') from public.coin_transactions c where c.season_id=%s),
      'purchases',(select coalesce(jsonb_agg(to_jsonb(p) order by p.id),'[]') from public.purchases p where p.season_id=%s),
      'snapshots',(select coalesce(jsonb_agg(to_jsonb(s) order by s.id),'[]') from public.matchday_snapshots s where s.season_id=%s),
      'revisions',(select coalesce(jsonb_agg(to_jsonb(s) order by s.id),'[]') from public.matchday_snapshot_revisions s where s.season_id=%s),
      'receipts',(select coalesce(jsonb_agg(to_jsonb(r) order by r.id),'[]') from public.admin_operation_receipts r where r.season_id=%s),
      'title',(select coalesce(jsonb_agg(to_jsonb(f) order by f.id),'[]') from public.league_finalizations f where f.season_id=%s),
      'title_resolutions',(select coalesce(jsonb_agg(to_jsonb(r) order by r.id),'[]') from public.league_championship_resolutions r where r.season_id=%s),
      'season',(select to_jsonb(s) from public.seasons s where s.id=%s),
      'days',(select coalesce(jsonb_agg(to_jsonb(d) order by d.id),'[]') from public.matchdays d where d.season_id=%s))""",
      (v['sid'],)*9)


def rejects_atomically(conn, v, run, expected):
    before = footprint(conn, v)
    try:
        with conn.transaction():
            run()
    except psycopg.Error as exc:
        assert exc.sqlstate == 'PT409', (exc.sqlstate, str(exc))
        assert str(exc).splitlines()[0] in expected, str(exc)
    else:
        raise AssertionError('Unsafe operation was accepted')
    assert footprint(conn, v) == before, 'Rejected operation changed prizes, balances, receipts or official history'


def validate(pg):
    checks = []
    with connect(pg) as conn:
        try:
            v = initialize(conn, total=1)
            for index in range(5): confirm(conn, index, 0, 0)
            open_and_results(conn, v, v['day1'], 1, [4, 3, 2, 1, 0])
            envelope = prepare_close(conn, v, v['day1'], '075-guard-forged-scoring')
            for mode in ('double_wins', 'position_points'):
                forged = deepcopy(envelope)
                forged['request']['idempotency_key'] += '-'+mode
                for row in forged['plan']['standings']:
                    row['points_awarded'] = (2*row['metadata']['wins'] if mode == 'double_wins'
                                              else [10, 8, 6, 4, 2][row['position']-1])
                rejects_atomically(conn, v,
                    lambda: rpc(conn, 'api_admin_matchday', forged), {'invalid_results'})
                checks.append(mode+' rejected in authoritative SQL with exact transaction footprint unchanged')
        finally:
            conn.rollback()

    with connect(pg) as conn:
        try:
            v = initialize(conn, total=1)
            for index in range(5): confirm(conn, index, 0, 0)
            open_and_results(conn, v, v['day1'], 1, [3, 3, 2, 1, 1])
            revision = value(conn, 'select results_revision from public.matchdays where id=%s', (v['day1'],))
            req = request(v, v['day1'], '075-guard-unresolved', {'expected_results_revision': revision})
            context = rpc(conn, 'api_admin_matchday_context', {'operation': 'close', 'request': req})
            try:
                plan_close(context['context'])
            except RankingDecisionRequired as exc:
                assert exc.code == 'RANKING_TIE_UNRESOLVED'
                assert any('matchday_prize' in g['consequences'] for g in exc.review['groups'])
            else:
                raise AssertionError('Consequential tie was assigned an arbitrary order')
            envelope = prepare_close(conn, v, v['day1'], '075-guard-missing-1v1')
            missing = deepcopy(envelope)
            for order in missing['request']['body']['tie_resolution']['orders']:
                order.pop('battles', None)
            for order in missing['plan']['ranking']['resolutions']:
                order.pop('battles', None)
            rejects_atomically(conn, v,
                lambda: rpc(conn, 'api_admin_matchday', missing), {'invalid_tie_resolution'})
            unresolved = deepcopy(envelope)
            unresolved['request']['idempotency_key'] += '-unresolved'
            unresolved['request']['body'].pop('tie_resolution')
            unresolved['plan']['ranking']['resolutions'] = []
            rejects_atomically(conn, v,
                lambda: rpc(conn, 'api_admin_matchday', unresolved), {'ranking_tie_unresolved'})
            checks.append('first/last prize ties block Python planning and SQL closure without actual recorded 1v1 outcomes; no partial prizes')
        finally:
            conn.rollback()

    with connect(pg) as conn:
        try:
            v = initialize(conn, total=1)
            for index in range(5): confirm(conn, index, 10 if index == 0 else 0, 10 if index == 0 else 0)
            open_and_results(conn, v, v['day1'], 1, [4, 3, 2, 1, 0])
            envelope = prepare_close(conn, v, v['day1'], '075-guard-final-net-tie')
            rpc(conn, 'api_admin_matchday', envelope)
            snapshot = value(conn, 'select snapshot from public.matchday_snapshots where matchday_id=%s', (v['day1'],))
            title = value(conn, 'select public.championship_context(%s)', (v['sid'],))
            # 075 leaves the rule undefined; 076 supplies an explicit admin
            # choice. Neither version may assign a title without confirmation.
            assert title['state'] in ('owner_decision_required', 'tiebreak_required'), title
            assert title['champion_trainer_id'] is None and title['resolution_type'] is None, title
            assert title['blocking_reason'] in ('league_net_championship_tie_rule_required', 'championship_tiebreak_required')
            assert set(title['tied_player_ids']) == set(v['players'][:2])
            leaders = {p['season_player_id']: Decimal(p['total_points']) for p in title['players']}
            assert leaders[v['players'][0]] == leaders[v['players'][1]] == Decimal('3')
            for operation, expected in (('finish', 'championship_unresolved'),
                                        ('championship_bo3', 'championship_bo3_not_required')):
                body = dict(expected_revision=title['setup_revision'], input_hash=title['input_hash'])
                if operation == 'championship_bo3':
                    body.update(winner_season_player_id=v['players'][0], reason='Synthetic attempt cannot invent the new League title rule')
                lifecycle = dict(operation=operation, actor_trainer_id=v['tid'], season_id=v['sid'],
                                 idempotency_key='075-guard-'+operation, body=body)
                rejects_atomically(conn, v,
                    lambda: value(conn, 'select public.api_admin_season_lifecycle(%s::jsonb)', (Jsonb(lifecycle),)), {expected})
            value(conn, 'select pg_temp.observe_0(%s::integer[])', ([1],))
            assert value(conn, 'select snapshot from public.matchday_snapshots where matchday_id=%s', (v['day1'],)) == snapshot
            general = value(conn, 'select public.league_general_read(%s)', (v['sid'],))
            first = next(row for row in general['rows'] if row['season_player_id'] == v['players'][0])
            assert first['historical_deaths'] == 10 and Decimal(first['total_points']) == Decimal('3')
            assert first['points_provisional'] is False
            checks.append('4wins-1.0 equals3wins: champion staysnull; finish and legacyBO3 blocked; newer source cannot rewrite frozen deaths/net totals')
        finally:
            conn.rollback()
    return 'PASS: '+'; '.join(checks)
