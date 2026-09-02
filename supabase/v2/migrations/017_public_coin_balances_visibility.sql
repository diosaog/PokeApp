-- PokeApp Supabase V2 security layer.
-- 017_public_coin_balances_visibility: keep the public coin balance aggregate readable.

begin;

alter view public.public_coin_balances
set (security_invoker = false, security_barrier = true);

commit;
