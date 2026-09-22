-- Fixed test identities; called only behind the local destructive-validator guard.
delete from public.activity_events where season_id='00000000-0000-4000-8000-000000008d10';
delete from public.coin_transactions where season_id='00000000-0000-4000-8000-000000008d10';
delete from public.purchases where season_id='00000000-0000-4000-8000-000000008d10';
delete from public.shop_promotions where season_id='00000000-0000-4000-8000-000000008d10';
delete from public.penalties where season_id='00000000-0000-4000-8000-000000008d10';
delete from public.trial_cases where season_id='00000000-0000-4000-8000-000000008d10';
delete from public.season_players where season_id='00000000-0000-4000-8000-000000008d10';
update public.seasons set current_matchday_id=null where id in ('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d11');
delete from public.matchdays where season_id in ('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d11');
delete from public.season_config_versions where season_id in ('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d11');
delete from public.seasons where id in ('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d11');
delete from public.trainers where id in ('00000000-0000-4000-8000-000000008d01','00000000-0000-4000-8000-000000008d02');
delete from public.shop_items where id in ('00000000-0000-4000-8000-000000008d60','00000000-0000-4000-8000-000000008d61');
drop schema pokeapp_shop_test cascade;
