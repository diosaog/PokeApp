-- Promociones rotativas del Poke Mart.
-- Ejecutar una sola vez en el SQL Editor de Supabase antes de cerrar la
-- siguiente jornada con esta version desplegada.

create table if not exists public.shop_discounts (
  id bigserial primary key,
  item text not null,
  category text not null default '',
  base_price integer not null,
  discount_price integer not null,
  stock_total integer not null,
  stock_used integer not null default 0,
  discount_kind text not null default 'normal',
  jornada integer not null,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  announced_at timestamptz,
  activates_at timestamptz,
  exhausted_at timestamptz
);

alter table public.shop_discounts
  add column if not exists category text not null default '';
alter table public.shop_discounts
  add column if not exists announced_at timestamptz;
alter table public.shop_discounts
  add column if not exists activates_at timestamptz;

alter table public.purchases
  add column if not exists discount_id bigint;
alter table public.purchases
  add column if not exists base_price integer;
alter table public.purchases
  add column if not exists jornada integer;

update public.shop_discounts
set announced_at = coalesce(announced_at, created_at),
    activates_at = coalesce(activates_at, created_at)
where announced_at is null or activates_at is null;

create index if not exists idx_shop_discounts_active_item
  on public.shop_discounts (active, item);
create index if not exists idx_shop_discounts_jornada
  on public.shop_discounts (jornada);
create index if not exists idx_shop_discounts_activation
  on public.shop_discounts (active, activates_at);
create index if not exists idx_purchases_user_discount
  on public.purchases ("user", discount_id);

create or replace function public.rpc_purchase_shop_discount(
  p_discount_id bigint,
  p_user text,
  p_jornada integer
)
returns table (
  purchased boolean,
  reason text,
  purchase_id bigint,
  discount_id bigint,
  item text,
  base_price integer,
  discount_price integer,
  stock_total integer,
  stock_used integer,
  discount_kind text
)
language plpgsql
security definer
set search_path = public
as $$
declare
  promo public.shop_discounts%rowtype;
  new_purchase_id bigint;
  next_stock integer;
  is_exhausted boolean;
begin
  select sd.*
  into promo
  from public.shop_discounts as sd
  where sd.id = p_discount_id
  for update;

  if not found then
    return query select
      false, 'unavailable', null::bigint, p_discount_id,
      ''::text, 0, 0, 0, 0, 'normal'::text;
    return;
  end if;

  if promo.jornada <> p_jornada then
    return query select
      false, 'expired', null::bigint, promo.id, promo.item,
      promo.base_price, promo.discount_price, promo.stock_total,
      promo.stock_used, promo.discount_kind;
    return;
  end if;

  if now() < coalesce(promo.activates_at, promo.created_at) then
    return query select
      false, 'pending', null::bigint, promo.id, promo.item,
      promo.base_price, promo.discount_price, promo.stock_total,
      promo.stock_used, promo.discount_kind;
    return;
  end if;

  if not promo.active or promo.stock_used >= promo.stock_total then
    return query select
      false, 'exhausted', null::bigint, promo.id, promo.item,
      promo.base_price, promo.discount_price, promo.stock_total,
      promo.stock_used, promo.discount_kind;
    return;
  end if;

  if exists (
    select 1
    from public.purchases as p
    where p."user" = p_user
      and p.discount_id = promo.id
  ) then
    return query select
      false, 'already_claimed', null::bigint, promo.id, promo.item,
      promo.base_price, promo.discount_price, promo.stock_total,
      promo.stock_used, promo.discount_kind;
    return;
  end if;

  insert into public.purchases (
    "user", item, price, status, created_at, redeemed_at,
    discount_id, base_price, jornada
  ) values (
    p_user, promo.item, promo.discount_price, 'pending', now(), null,
    promo.id, promo.base_price, p_jornada
  )
  returning id into new_purchase_id;

  next_stock := promo.stock_used + 1;
  is_exhausted := next_stock >= promo.stock_total;

  update public.shop_discounts as sd
  set stock_used = next_stock,
      active = not is_exhausted,
      exhausted_at = case when is_exhausted then now() else null end
  where sd.id = promo.id;

  return query select
    true, 'ok', new_purchase_id, promo.id, promo.item,
    promo.base_price, promo.discount_price, promo.stock_total,
    next_stock, promo.discount_kind;
end;
$$;

grant execute on function public.rpc_purchase_shop_discount(bigint, text, integer)
to anon, authenticated, service_role;

select pg_notify('pgrst', 'reload schema');
