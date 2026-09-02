-- PokeApp Supabase V2 security layer.
-- 015_public_trainers_visibility: keep the public trainer listing readable.

begin;

alter view public.public_trainers
set (security_invoker = false, security_barrier = true);

commit;
