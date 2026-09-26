from copy import deepcopy
import unittest
from uuid import uuid4
from app.domain.services.cup_engine import plan, standings, validate, swiss_pairs, CupRejected


def fixture(fmt='swiss', n=4, swiss_rounds=3):
    roster = [dict(id=str(uuid4()), trainer_id=str(uuid4()), display_name=f'Trainer {i}',globally_enabled=True) for i in range(n*(2 if fmt=='doubles' else 1))]
    size = 2 if fmt=='doubles' else 1
    body = dict(name='Small Cup',format=fmt,swiss_rounds=swiss_rounds,
                sides=[dict(name=f'Side {i}',trainer_ids=[p['trainer_id'] for p in roster[i*size:(i+1)*size]]) for i in range(n)])
    context = dict(roster=roster,cup=None)
    request = dict(operation='create',body=body,season_id=str(uuid4()))
    context['cup'] = plan(context, request)
    context['cup'] = plan(context, dict(operation='start',body={}))
    return context


def scores(r, reverse=False):
    return [dict(match_id=m['id'],winner_side_id=m['b'] if reverse else m['a']) if r['phase']=='swiss' else
            dict(match_id=m['id'],score_a=1 if reverse else 2,score_b=2 if reverse else 1)
            for m in r['matches'] if m['status'] in ('scheduled','completed')]


def play(context):
    r = context['cup']['rounds'][-1]
    if any(m['status']=='scheduled' for m in r['matches']):
        context['cup'] = plan(context, dict(operation='results', round_number=r['number'],body=dict(results=scores(r))))
    context['cup'] = plan(context, dict(operation='close', round_number=r['number'],body={}))


class CupEngineTests(unittest.TestCase):
    def finish(self, ctx):
        for _ in range(22):
            r = ctx['cup']['rounds'][-1]
            if r['phase']=='final' and r['status']=='closed':
                break
            play(ctx)
        else:
            self.fail('Tournament failed to terminate')
        return plan(ctx,dict(operation='finalize',body={}))

    def test_swiss_four_top_four_and_final(self):
        c = self.finish(fixture())
        self.assertEqual([r['phase'] for r in c['rounds']], ['swiss']*3+['semifinal','final'])
        self.assertEqual(c['champion_side_id'],c['rounds'][-1]['matches'][0]['winner'])
        self.assertNotEqual(c['champion_side_id'],c['finalist_side_id'])

    def test_odd_bye_rotation_and_no_self_or_duplicate(self):
        ctx = fixture(n=5)
        byes = []
        for _ in range(3):
            r = ctx['cup']['rounds'][-1]
            ids = [s for m in r['matches'] for s in (m['a'],m['b']) if s]
            self.assertEqual(len(ids),len(set(ids)))
            byes.extend(m['winner'] for m in r['matches'] if m['status']=='bye')
            play(ctx)
        self.assertEqual(len(set(byes)),3)
        self.finish(ctx)

    def test_easy_rematches_avoided(self):
        ctx=fixture(n=6); first={frozenset((m['a'],m['b'])) for m in ctx['cup']['rounds'][0]['matches']}
        play(ctx)
        second={frozenset((m['a'],m['b'])) for m in ctx['cup']['rounds'][1]['matches']}
        self.assertFalse(first & second)

    def test_unavoidable_rematch_does_not_block(self):
        ctx=fixture(n=4,swiss_rounds=5)
        self.finish(ctx)

    def test_standings_and_pairings_deterministic(self):
        ctx=fixture(n=5); play(ctx)
        self.assertEqual(standings(ctx['cup']),standings(deepcopy(ctx['cup'])))
        self.assertEqual(swiss_pairs(ctx['cup']),swiss_pairs(deepcopy(ctx['cup'])))

    def test_elimination_five_real_byes_and_bo3(self):
        c=self.finish(fixture('elimination',5))
        self.assertEqual([len(r['matches']) for r in c['rounds']],[4,2,1])
        self.assertEqual(sum(m['status']=='bye' for m in c['rounds'][0]['matches']),3)
        self.assertTrue(all((m['score_a'],m['score_b'])==(2,1) for r in c['rounds'] for m in r['matches'] if m['status']=='completed'))

    def test_invalid_bo3_scores_and_contradictory_winner(self):
        ctx=fixture('elimination',2); m=ctx['cup']['rounds'][0]['matches'][0]
        for a,b in ((2,0),(2,1),(1,2),(0,2)):
            c=plan(ctx,dict(operation='results',round_number=1,body=dict(results=[dict(match_id=m['id'],score_a=a,score_b=b)])))
            self.assertEqual(c['rounds'][0]['matches'][0]['winner'],m['a'] if a>b else m['b'])
        for a,b in ((0,0),(1,0),(1,1),(2,2),(3,0),(-1,2),(True,2)):
            with self.subTest(a=a,b=b),self.assertRaises(CupRejected):
                plan(ctx,dict(operation='results',round_number=1,body=dict(results=[dict(match_id=m['id'],score_a=a,score_b=b)])))
        with self.assertRaises(CupRejected):
            plan(ctx,dict(operation='results',round_number=1,body=dict(results=[dict(match_id=m['id'],score_a=2,score_b=0,winner_side_id=m['b'])])))

    def test_doubles_three_teams_round_robin_and_final(self):
        c=self.finish(fixture('doubles',3))
        self.assertEqual([r['phase'] for r in c['rounds']],['round_robin']*3+['final'])
        pairs=[frozenset((m['a'],m['b'])) for r in c['rounds'][:-1] for m in r['matches'] if m['a'] and m['b']]
        self.assertEqual(len(set(pairs)),3)
        champion=next(s for s in c['sides'] if s['id']==c['champion_side_id'])
        self.assertEqual(len(champion['members']),2)

    def test_doubles_two_way_tie_uses_head_to_head_before_seed(self):
        ctx=fixture('doubles',4); c=ctx['cup']; a,b,d,e=[s['id'] for s in c['sides']]
        c['rounds']=[dict(number=1,phase='round_robin',status='closed',matches=[
            dict(a=x,b=y,winner=x,status='completed',score_a=2,score_b=0)
            for x,y in ((b,a),(a,d),(a,e),(b,d),(e,b),(d,e))])]
        self.assertEqual([r['side_id'] for r in standings(c)],[b,a,d,e])

    def test_disabled_entrant_rechecked_at_start(self):
        ctx=fixture('elimination',2); ctx['cup'].update(status='draft',rounds=[])
        ctx['roster'][0]['globally_enabled']=False
        with self.assertRaisesRegex(CupRejected,'INVALID_ROSTER'): plan(ctx,dict(operation='start',body={}))

    def test_correction_rebuilds_unplayed_successor(self):
        ctx=fixture('elimination',4); play(ctx)
        before=deepcopy(ctx['cup']); old=before['rounds'][0]
        c=plan(ctx,dict(operation='correct',round_number=1,body=dict(reason='Review',results=scores(old,True))))
        self.assertNotEqual(c['rounds'][-1]['matches'][0]['a'],before['rounds'][-1]['matches'][0]['a'])
        self.assertEqual([m['id'] for m in c['rounds'][0]['matches']],[m['id'] for m in old['matches']])

    def test_correction_rejects_played_successor(self):
        ctx=fixture('elimination',4); play(ctx)
        r=ctx['cup']['rounds'][-1]
        ctx['cup']=plan(ctx,dict(operation='results',round_number=2,body=dict(results=scores(r))))
        with self.assertRaisesRegex(CupRejected,'PLAYED_RESULT_DEPENDENCY'):
            plan(ctx,dict(operation='correct',round_number=1,body=dict(results=scores(ctx['cup']['rounds'][0],True))))

    def test_dq_singles_opponent_advances_without_score(self):
        ctx=fixture('elimination',4); r=ctx['cup']['rounds'][0]; m=r['matches'][0]
        ctx['cup']=plan(ctx,dict(operation='disqualify',side_id=m['a'],body=dict(reason='DQ')))
        forfeited=ctx['cup']['rounds'][0]['matches'][0]
        self.assertEqual(forfeited['winner'],m['b']); self.assertIsNone(forfeited['score_a'])
        self.finish(ctx)

    def test_dq_swiss_three_qualifiers_keep_top_four_slots(self):
        ctx=fixture(); side=ctx['cup']['sides'][-1]['id']
        ctx['cup']=plan(ctx,dict(operation='disqualify',side_id=side,body=dict(reason='DQ')))
        c=self.finish(ctx)
        self.assertNotEqual(c['champion_side_id'],side)
        self.assertEqual(len(c['rounds'][-2]['matches']),2)

    def test_dq_doubles_preserves_both_members(self):
        ctx=fixture('doubles',3); side=ctx['cup']['sides'][-1]
        members=deepcopy(side['members'])
        ctx['cup']=plan(ctx,dict(operation='disqualify',side_id=side['id'],body=dict(reason='DQ')))
        c=self.finish(ctx)
        self.assertEqual(c['sides'][-1]['members'],members)

    def test_discard_preserves_results_and_blocks_finalize(self):
        ctx=fixture(); play(ctx); previous=deepcopy(ctx['cup']['rounds'])
        ctx['cup']=plan(ctx,dict(operation='discard',body=dict(reason='Cancel')))
        self.assertEqual(ctx['cup']['rounds'],previous)
        with self.assertRaises(CupRejected): plan(ctx,dict(operation='finalize',body={}))

    def test_certification_rejects_forged_advancement(self):
        c=self.finish(fixture('elimination',4))
        c['rounds'][-1]['matches'][0]['a']=c['rounds'][0]['matches'][0]['b']
        with self.assertRaisesRegex(CupRejected,'INVALID_ADVANCEMENT'): validate(c)

    def test_certification_rejects_forged_standings(self):
        c=self.finish(fixture()); c['standings'][0]['wins']+=1
        with self.assertRaisesRegex(CupRejected,'INVALID_STANDINGS'): validate(c)

    def test_certification_requires_explicit_final_close(self):
        ctx=fixture('elimination',2)
        with self.assertRaisesRegex(CupRejected,'COMPETITION_INCOMPLETE'): plan(ctx,dict(operation='finalize',body={}))

    def test_finished_cannot_be_corrected_or_discarded(self):
        ctx=fixture(); ctx['cup']=self.finish(ctx)
        for op in ('correct','discard','disqualify'):
            with self.assertRaises(CupRejected): plan(ctx,dict(operation=op,round_number=1,body={}))
