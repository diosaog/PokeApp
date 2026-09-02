-- PokeApp Supabase V2 security layer.
-- 016_public_team_locks_visibility: keep the public team lock listing readable.

begin;

alter view public.public_team_locks
set (security_invoker = false, security_barrier = true);

commit;
