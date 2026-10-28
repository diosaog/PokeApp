-- 066_personal_saves_least_privilege: what 065 meant for service_role.
--
-- 065 granted service_role select, insert and update on
-- trainer_personal_saves, but Supabase's default privileges had already
-- given it every privilege on the new public table, so that grant added
-- nothing. Take the rest back: the API reads and upserts a personal save and
-- never deletes or truncates one.
begin;

revoke all on public.trainer_personal_saves from service_role;
grant select, insert, update on public.trainer_personal_saves to service_role;

commit;
