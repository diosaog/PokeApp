-- Only fixture identities in the disposable validation database.
delete from public.activity_events where season_id='00000000-0000-4000-8000-000000008c10';
delete from public.team_locks where season_id='00000000-0000-4000-8000-000000008c10';
delete from public.parsed_saves where id in ('00000000-0000-4000-8000-000000008c30','00000000-0000-4000-8000-000000008c31');
delete from public.save_files where season_id='00000000-0000-4000-8000-000000008c10';
delete from public.matchdays where season_id='00000000-0000-4000-8000-000000008c10';
delete from public.season_config_versions where season_id='00000000-0000-4000-8000-000000008c10';
delete from public.season_players where season_id='00000000-0000-4000-8000-000000008c10';
delete from public.seasons where id='00000000-0000-4000-8000-000000008c10';
delete from public.trainers where id in ('00000000-0000-4000-8000-000000008c01','00000000-0000-4000-8000-000000008c04');
drop schema pokeapp_team_lock_test cascade;
