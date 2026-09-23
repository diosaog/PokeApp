from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import unittest

from tools.generate_supabase_v2_bootstrap import BOOTSTRAP_SQL, render_bootstrap
from tools.validate_supabase_v2_redemptions import WorkerClient


class RobberyContractTests(unittest.TestCase):
    def setUp(self):
        self.sql=Path('supabase/v2/migrations/025_robbery_voucher_and_redemption.sql').read_text(encoding='utf-8')

    def test_reward_constraints_and_unique_origin(self):
        for fragment in ("acquisition_mode='reward_only' and base_price=0 and not enabled",
                         "origin_redemption_id uuid unique references public.redemptions(id)",
                         "acquisition_type='paid' and unit_price>0",
                         "acquisition_type='reward' and unit_price=0 and quantity=1 and promotion_id is null",
                         "v_origin.gift_purchase_id is distinct from new.id"):
            self.assertIn(fragment,self.sql)

    def test_fixture_workers_keep_independent_sessions_without_retries(self):
        clients=[]
        def factory():
            client=object()
            clients.append(client)
            return client
        wrapper=WorkerClient(factory)
        barrier=Barrier(4)
        def call(_):
            first=wrapper.client()
            barrier.wait(timeout=5)
            self.assertIs(first,wrapper.client())
            return first
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(call,range(4)))
        self.assertEqual(len(clients),4)
        self.assertEqual(len({id(c) for c in results}),4)

    def test_lock_order_and_backend_only_cycle(self):
        body=self.sql.split('create or replace function public.api_redeem_purchase',1)[1]
        for first,second in (('for no key update','order by id for update'),
                             ('order by id for update','from public.purchases'),
                             ('from public.purchases','from public.pokemon_entities'),
                             ('from public.pokemon_entities','insert into public.robbery_cycles')):
            self.assertLess(body.index(first),body.index(second))
        self.assertIn('on public.redemptions(season_id,robbery_cycle_number,target_owner_trainer_id)',self.sql)
        self.assertIn('revoke all on public.robbery_cycles from public,anon,authenticated',self.sql)
        for forbidden in ('update public.pokemon_entities','coin_transactions','storage.objects','exception when'):
            self.assertNotIn(forbidden,body)

    def test_bootstrap_exact_and_one_canonical_seed_statement(self):
        self.assertEqual(BOOTSTRAP_SQL.read_text(encoding='utf-8'),render_bootstrap())
        self.assertEqual(self.sql.count("values('robbery_shield_voucher',"),1)


if __name__=='__main__': unittest.main()
