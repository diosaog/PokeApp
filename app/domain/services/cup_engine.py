"""Small deterministic Cup engine. No I/O, League state, random draw or UI.

The service adapter supplies a database snapshot, never a client-provided graph.
SQL compares that snapshot under the shared season/player locks before committing.
"""
from copy import deepcopy
from itertools import groupby
from uuid import uuid4

RULES_VERSION = 1
BO3 = {(2, 0), (2, 1), (1, 2), (0, 2)}


class CupRejected(ValueError):
    pass


def require(value, code):
    if not value:
        raise CupRejected(code)


def active(cup):
    return [s for s in cup['sides'] if s['status'] == 'active']


def standings(cup):
    rows = {s['id']: dict(side_id=s['id'], seed=s['seed'], status=s['status'], wins=0,
        losses=0, byes=0, buchholz=0, games_won=0, games_lost=0) for s in cup['sides']}
    meetings = []
    for r in cup['rounds']:
        if r['status'] != 'closed' or r['phase'] not in ('swiss', 'round_robin'):
            continue
        for m in r['matches']:
            a, b, w = m['a'], m['b'], m['winner']
            if not a or not b:
                if w and r['phase'] == 'swiss':
                    rows[w]['wins'] += 1
                    rows[w]['byes'] += 1
                continue
            if not w:
                continue
            loser = b if w == a else a
            rows[w]['wins'] += 1
            rows[loser]['losses'] += 1
            meetings.append((a, b, w))
            if m['status'] == 'completed' and m['score_a'] is not None:
                for side, won, lost in ((a, m['score_a'], m['score_b']), (b, m['score_b'], m['score_a'])):
                    rows[side]['games_won'] += won
                    rows[side]['games_lost'] += lost
    for a, b, _ in meetings:
        rows[a]['buchholz'] += rows[b]['wins']
        rows[b]['buchholz'] += rows[a]['wins']
    def key(row):
        if cup['format'] == 'doubles':
            return (-row['wins'], -(row['games_won'] - row['games_lost']), -row['games_won'])
        return (-row['wins'], -row['buchholz'])
    ranked = sorted(rows.values(), key=lambda x: (*key(x), x['seed'], x['side_id']))
    if cup['format'] == 'doubles':
        ordered = []
        for _, group in groupby(ranked, key=key):
            tied = list(group)
            if len(tied) == 2:
                winners = [w for a, b, w in meetings if {a, b} == {x['side_id'] for x in tied}]
                if len(winners) == 1:
                    tied.sort(key=lambda x: x['side_id'] != winners[0])
            ordered.extend(tied)
        ranked = ordered
    return [dict(row, position=i) for i, row in enumerate(ranked, 1)]


def swiss_pairs(cup):
    ranking = standings(cup)
    pool = [r['side_id'] for r in ranking if r['status'] == 'active']
    pairs = []
    if len(pool) % 2:
        # Lowest-ranked among the fewest previous byes. Never blocks a small Cup.
        bye = min((r for r in ranking if r['side_id'] in pool), key=lambda r: (r['byes'], -r['position']))['side_id']
        pool.remove(bye)
        pairs.append((bye, None))
    met = {frozenset((m['a'], m['b'])) for r in cup['rounds'] for m in r['matches'] if m['a'] and m['b']}
    played_pairs = []
    while pool:
        a = pool.pop(0)
        b = next((p for p in pool if frozenset((a, p)) not in met), pool[0])
        pool.remove(b)
        played_pairs.append((a, b))
    # A single local swap fixes the common greedy last-pair rematch, no solver.
    for i, (a, b) in enumerate(played_pairs):
        if frozenset((a, b)) not in met:
            continue
        for j in range(i):
            c, d = played_pairs[j]
            choices = [((a, c), (b, d)), ((a, d), (b, c))]
            replacement = next((p for p in choices if all(frozenset(x) not in met for x in p)), None)
            if replacement:
                played_pairs[i], played_pairs[j] = replacement
                break
    return played_pairs + pairs


def round_robin_pairs(cup, number):
    ids = [s['id'] for s in sorted(cup['sides'], key=lambda s: s['seed'])]
    if len(ids) % 2:
        ids.append(None)
    for _ in range(number - 1):
        ids = [ids[0], ids[-1], *ids[1:-1]]
    return list(zip(ids[:len(ids)//2], reversed(ids[len(ids)//2:])))


def elimination_pairs(ids):
    size = 2
    while size < len(ids):
        size *= 2
    seeds = [1, 2]
    while len(seeds) < size:
        seeds = [v for s in seeds for v in (s, len(seeds)*2 + 1 - s)]
    slots = [ids[s-1] if s <= len(ids) else None for s in seeds]
    return list(zip(slots[::2], slots[1::2]))


def automatic(cup, match):
    eligible = {s['id'] for s in active(cup)}
    a, b = match['a'], match['b']
    live = [s for s in (a, b) if s in eligible]
    match.update(winner=None, score_a=None, score_b=None)
    if a is not None and b is not None and len(live) == 2:
        match['status'] = 'scheduled'
    elif len(live) == 1:
        match.update(winner=live[0], status='bye' if a is None or b is None else 'forfeit')
    else:
        match['status'] = 'void'


def make_round(cup, phase, pairs):
    r = dict(number=len(cup['rounds'])+1, phase=phase, status='open', matches=[])
    for position, (a, b) in enumerate(pairs, 1):
        require(a is None or a != b, 'INVALID_PAIRING')
        m = dict(id=str(uuid4()), position=position, a=a, b=b)
        automatic(cup, m)
        r['matches'].append(m)
    require(r['matches'], 'INSUFFICIENT_PARTICIPANTS')
    return r


def next_round(cup):
    rounds = cup['rounds']
    if not rounds:
        ids = [s['id'] for s in sorted(active(cup), key=lambda s: s['seed'])]
        if cup['format'] == 'swiss':
            return make_round(cup, 'swiss', swiss_pairs(cup))
        if cup['format'] == 'doubles':
            return make_round(cup, 'round_robin', round_robin_pairs(cup, 1))
        pairs = elimination_pairs(ids)
        return make_round(cup, 'final' if len(pairs) == 1 else 'elimination', pairs)
    last = rounds[-1]
    require(last['status'] == 'closed', 'ROUND_NOT_CLOSED')
    if last['phase'] == 'final':
        return None
    if last['phase'] == 'swiss' and last['number'] < cup['swiss_rounds']:
        return make_round(cup, 'swiss', swiss_pairs(cup))
    if last['phase'] in ('swiss', 'round_robin'):
        if last['phase'] == 'round_robin':
            total = len(cup['sides']) - (1 if len(cup['sides']) % 2 == 0 else 0)
            if last['number'] < total:
                return make_round(cup, 'round_robin', round_robin_pairs(cup, last['number']+1))
        ranking = [r['side_id'] for r in standings(cup) if r['status'] == 'active']
        count = 4 if last['phase'] == 'swiss' else 2
        require(len(ranking) >= 2, 'INSUFFICIENT_TOP_CUT')
        ranking += [None] * max(0, count-len(ranking))
        pairs = [(ranking[0], ranking[3]), (ranking[1], ranking[2])] if count == 4 else [(ranking[0], ranking[1])]
        return make_round(cup, 'semifinal' if count == 4 else 'final', pairs)
    winners = [m['winner'] for m in last['matches']]
    pairs = list(zip(winners[::2], winners[1::2]))
    return make_round(cup, 'final' if len(pairs) == 1 else 'elimination', pairs)


def record(cup, r, results, correcting=False):
    require(results and len({x['match_id'] for x in results}) == len(results), 'INVALID_RESULTS')
    matches = {m['id']: m for m in r['matches']}
    for result in results:
        m = matches.get(result['match_id'])
        require(m is not None, 'MATCH_NOT_FOUND')
        require(m['status'] == ('completed' if correcting else 'scheduled'), 'RESULT_NOT_EDITABLE')
        require(m['a'] and m['b'], 'INVALID_RESULTS')
        if r['phase'] == 'swiss':
            winner = result.get('winner_side_id')
            require(winner in (m['a'], m['b']) and result.get('score_a') is None and result.get('score_b') is None, 'INVALID_RESULTS')
            a = b = None
        else:
            a, b = result.get('score_a'), result.get('score_b')
            require(type(a) is int and type(b) is int and (a, b) in BO3 and result.get('winner_side_id') is None, 'INVALID_BO3')
            winner = m['a'] if a > b else m['b']
        m.update(winner=winner, score_a=a, score_b=b, status='completed')


def validate(cup):
    """Recheck persisted results and reproduce every generated round before certification.

    DQ timing is frozen per round as eligible_side_ids. This preserves completed
    scores and pre-DQ rankings while proving that every subsequent draw was legal.
    """
    require(cup['rules_version'] == RULES_VERSION, 'UNSUPPORTED_RULES')
    sides = cup['sides']
    members = [m['trainer_id'] for s in sides for m in s['members']]
    require(len(members) == len(set(members)), 'INVALID_ROSTER')
    require(len({s['id'] for s in sides}) == len(sides) and len({s['seed'] for s in sides}) == len(sides), 'INVALID_ROSTER')
    require(all(len(s['members']) == (2 if cup['format'] == 'doubles' else 1) for s in sides), 'INVALID_ROSTER')
    working = deepcopy(cup)
    working['rounds'] = []
    eligible = {s['id'] for s in sides}
    for i, r in enumerate(cup['rounds'], 1):
        require(r['number'] == i and r['status'] == 'closed', 'COMPETITION_INCOMPLETE')
        next_eligible = set(r['eligible_side_ids'])
        require(next_eligible <= eligible and len(next_eligible)==len(r['eligible_side_ids']), 'INVALID_ROSTER')
        eligible = next_eligible
        for s in working['sides']:
            s['status'] = 'active' if s['id'] in r['eligible_side_ids'] else 'disqualified'
        expected = next_round(working)
        require(expected is not None and expected['phase'] == r['phase'], 'INVALID_ADVANCEMENT')
        require([(m['a'], m['b'], m['position']) for m in expected['matches']] ==
                [(m['a'], m['b'], m['position']) for m in r['matches']], 'INVALID_ADVANCEMENT')
        for m in r['matches']:
            require(m['status'] in ('completed', 'bye', 'forfeit', 'void'), 'COMPETITION_INCOMPLETE')
            if m['status'] == 'completed':
                test = dict(r, matches=[dict(m)])
                result = dict(match_id=m['id'], winner_side_id=m['winner'] if r['phase']=='swiss' else None,
                              score_a=m['score_a'], score_b=m['score_b'])
                record(cup, test, [result], True)
                require(test['matches'][0] == m, 'INVALID_RESULTS')
            else:
                require(m['score_a'] is None and m['score_b'] is None, 'INVALID_RESULTS')
                require(m['winner'] in (m['a'], m['b']) if m['status'] != 'void' else m['winner'] is None, 'INVALID_RESULTS')
                require(m['status'] != 'bye' or ((m['a'] is None) != (m['b'] is None)), 'INVALID_RESULTS')
                require(m['status'] != 'bye' or m['winner'] in next_eligible, 'INVALID_RESULTS')
                require(m['status'] != 'forfeit' or (m['a'] and m['b'] and any(s['id'] in (m['a'],m['b']) and s['id']!=m['winner'] and s['status']=='disqualified' for s in sides)), 'INVALID_RESULTS')
                require(m['status'] != 'void' or not any(s['id'] in (m['a'],m['b']) and s['status']=='active' for s in sides), 'INVALID_RESULTS')
        working['rounds'].append(deepcopy(r))
    require(cup['rounds'] and cup['rounds'][-1]['phase'] == 'final', 'COMPETITION_INCOMPLETE')
    final = cup['rounds'][-1]['matches']
    require(len(final) == 1 and final[0]['winner'] in {s['id'] for s in active(cup)}, 'INVALID_FINAL')
    m = final[0]
    require(m['a'] and m['b'] and m['a'] != m['b'], 'INVALID_FINAL')
    require(cup['standings'] == standings(cup), 'INVALID_STANDINGS')
    return m['winner'], m['b'] if m['winner'] == m['a'] else m['a']


def append_next(cup):
    r = next_round(cup)
    if r:
        r['eligible_side_ids'] = sorted(s['id'] for s in active(cup))
        cup['rounds'].append(r)


def plan(context, request):
    op, body = request['operation'], request['body']
    cup = deepcopy(context.get('cup'))
    if op in ('create', 'setup'):
        require(op == 'create' or cup['status'] == 'draft', 'CUP_NOT_DRAFT')
        roster = {p['trainer_id']: p for p in context['roster'] if p['globally_enabled']}
        sides = []
        for seed, side in enumerate(body['sides'], 1):
            members = []
            for tid in sorted(side['trainer_ids']):
                require(tid in roster, 'INVALID_ROSTER')
                p = roster[tid]
                members.append(dict(trainer_id=tid, season_player_id=p['id'], display_name=p['display_name']))
            sides.append(dict(id=str(uuid4()), name=side['name'], seed=seed, status='active', members=members))
        cup = dict(id=cup['id'] if cup else str(uuid4()), season_id=request['season_id'], name=body['name'],
            format=body['format'], status='draft', revision=cup['revision'] if cup else 0,
            rules_version=RULES_VERSION, swiss_rounds=body['swiss_rounds'], sides=sides, rounds=[], standings=[])
        require(len(sides) >= (4 if cup['format'] == 'swiss' else 2), 'INVALID_ROSTER')
        require(len(sides) <= (16 if cup['format'] == 'doubles' else 64), 'INVALID_ROSTER')
        require(all(len(s['members']) == (2 if cup['format']=='doubles' else 1) for s in sides), 'INVALID_ROSTER')
        tids = [m['trainer_id'] for s in sides for m in s['members']]
        require(len(tids) == len(set(tids)), 'INVALID_ROSTER')
    elif op == 'start':
        require(cup['status'] == 'draft', 'CUP_NOT_DRAFT')
        # A draft DQ excludes the side; identity/history remains available.
        require(len(active(cup)) >= (4 if cup['format']=='swiss' else 2), 'INVALID_ROSTER')
        enabled = {p['trainer_id'] for p in context['roster'] if p['globally_enabled']}
        require(all(m['trainer_id'] in enabled for s in active(cup) for m in s['members']), 'INVALID_ROSTER')
        cup['status'] = 'active'
        append_next(cup)
    elif op == 'discard':
        require(cup['status'] in ('draft', 'active'), 'CUP_TERMINAL')
        cup['status'] = 'discarded'
    elif op == 'disqualify':
        require(cup['status'] in ('draft', 'active'), 'CUP_TERMINAL')
        side = next((s for s in cup['sides'] if s['id']==request['side_id']), None)
        require(side is not None and side['status']=='active', 'SIDE_NOT_ACTIVE')
        # A played final cannot be undone by DQ. Correct its result first.
        require(not any(r['phase']=='final' and m['status']=='completed' and m['winner']==side['id']
                        for r in cup['rounds'] for m in r['matches']), 'PLAYED_RESULT_DEPENDENCY')
        side['status'] = 'disqualified'
        for r in cup['rounds']:
            if r['status']=='open':
                for m in r['matches']:
                    if m['status'] in ('scheduled','bye','forfeit','void') and side['id'] in (m['a'],m['b']):
                        automatic(cup, m)
    else:
        require(cup['status'] == 'active', 'CUP_NOT_ACTIVE')
        if op == 'finalize':
            identities = {(p['id'], p['trainer_id']) for p in context['roster']}
            require(all((m['season_player_id'],m['trainer_id']) in identities for s in cup['sides'] for m in s['members']), 'INVALID_ROSTER')
            champion, finalist = validate(cup)
            cup.update(status='finished', champion_side_id=champion, finalist_side_id=finalist)
        else:
            r = next((r for r in cup['rounds'] if r['number']==request['round_number']), None)
            require(r is not None, 'ROUND_NOT_FOUND')
            if op == 'results':
                require(r['status']=='open', 'ROUND_NOT_OPEN')
                record(cup, r, body['results'])
            elif op == 'close':
                require(r['status']=='open' and r is cup['rounds'][-1], 'ROUND_NOT_OPEN')
                require(all(m['status']!='scheduled' for m in r['matches']), 'RESULTS_INCOMPLETE')
                r['status'] = 'closed'
                append_next(cup)
            elif op == 'correct':
                require(not any(m['status']=='completed' for later in cup['rounds'] if later['number']>r['number']
                                for m in later['matches']), 'PLAYED_RESULT_DEPENDENCY')
                record(cup, r, body['results'], True)
                cup['rounds'] = cup['rounds'][:r['number']]
                if r['status']=='closed':
                    append_next(cup)
            else:
                raise CupRejected('INVALID_REQUEST')
    cup['standings'] = standings(cup)
    cup['revision'] += 1
    return cup
