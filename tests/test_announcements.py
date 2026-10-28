"""Frozen public facts render without private save fields or invented results."""
import json
import unittest
from copy import deepcopy
from app.application.announcements import gather, render, Skip


class FactsTests(unittest.TestCase):
    def setUp(self):
        self.tables = {
            'seasons':[dict(id='s', name='Fixture league', status='active')],
            'season_players':[dict(id='p1',trainer_id='t1',status='active'),dict(id='p2',trainer_id='t2',status='active')],
            'trainers':[dict(id='t1',display_name='One'),dict(id='t2',display_name='Two')],
            'divisions':[dict(id='d',code='A')],
            'season_config_versions':[dict(version_number=1,effective_from_matchday=1,total_matchdays=2)],
            'division_memberships':[],
        }

    def read(self, table, columns, **filters):
        rows=deepcopy(self.tables.get(table,[]))
        for key,value in filters.items():
            rows=[r for r in rows if key not in r or r[key] in value] if isinstance(value,list) else [r for r in rows if key not in r or r[key]==value]
        return rows

    def test_activation_before_round_does_not_invent_divisions(self):
        facts=gather('season_started',{'season_id':'s'},self.read)
        self.assertEqual((facts['players'],facts['leagues']),(2,{}))
        self.assertIn('Fixture league',str(render(facts)))

    def test_closed_day_points_coins_and_zero_are_from_snapshot(self):
        snapshot=dict(schema_version=2, closed_at='2026-10-28T10:00:00Z', final=False,
                      standings=[dict(trainer_id='p1',division_id='A',position=1,division_position=1,points_awarded=3,coins_awarded=0)],
                      inputs={'matches':[dict(player_a_id='p1',player_b_id='p2',winner_id='p1',division='A')]})
        self.tables.update(matchdays=[dict(id='day',season_id='s',number=1)],
                           matchday_snapshots=[dict(matchday_id='day',revision=1,snapshot=snapshot)],
                           matchday_snapshot_revisions=[dict(matchday_id='day',revision=1,snapshot=snapshot)],
                           coin_transactions=[dict(season_player_id='p1',amount=4)])
        facts=gather('matchday_closed',{'matchday_id':'day','revision':1},self.read)
        self.assertEqual(facts['rows'][0]['coins'],0)
        self.assertEqual(facts['rows'][0]['balance'],4)
        self.assertEqual(facts['results'],{'A':[('One','Two')]})
        body=json.dumps(render(facts),ensure_ascii=False)
        self.assertIn('One',body)
        self.assertIn('0',body)
        self.tables['matchday_snapshots'][0]['revision']=2
        with self.assertRaises(Skip):
            gather('matchday_closed',{'matchday_id':'day','revision':1},self.read)

    def test_cup_round_and_certificate_use_frozen_sides(self):
        snapshot=dict(season_id='s',name='Fixture Cup',format='singles',sides=[dict(id='a',name='One'),dict(id='b',name='Two')],
                      rounds=[dict(number=1,status='closed',phase='final',matches=[dict(a='a',b='b',winner='b',score_a=1,score_b=2)])], standings=[])
        self.tables.update(cup_history=[dict(cup_id='cup',revision=1,snapshot=snapshot,created_at=None)],
                           cup_certificates=[dict(cup_id='cup',season_id='s',champion_side_id='b',finalist_side_id='a',snapshot=snapshot,certified_at=None)])
        for kind in ['cup_round_closed','cup_finished']:
            facts=gather(kind,{'cup_id':'cup','revision':1},self.read)
            self.assertIn('Two',str(render(facts)))
        self.assertEqual(facts['score'],'2-1')

    def test_finished_league_uses_certificate_not_live_points(self):
        self.tables['league_finalizations']=[dict(id='final',season_id='s',created_at=None,
            title=dict(champion_trainer_id='t1',players=[dict(trainer_id='t1',season_player_id='p1',display_name='Frozen One',total_points=3)]),
            artifact=dict(roster=[dict(id='p1',display_name='Frozen One',status='active')],rounds=[dict(id='day',number=1,standings=[dict(season_player_id='p1',coins_awarded=0)])],standings=[]))]
        facts=gather('season_finished',{'finalization_id':'final'},self.read)
        self.assertEqual(facts['champion'],'Frozen One')
        self.assertEqual(facts['standings'][0]['coins'],0)
        self.assertIn('Frozen One',str(render(facts)))


if __name__=='__main__':
    unittest.main()
