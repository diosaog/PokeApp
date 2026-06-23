-- Recoloca las promociones activas de Crianza de la jornada actual.
-- Resultado deseado:
-- - Chapa Dorada como Rebaja normal: 15 -> 13, stock 2.
-- - Capsula Habilidad como Mega Rebaja: 8 -> 4, stock 1.
--
-- Uso:
-- 1) Ejecutar en Supabase SQL Editor.
-- 2) Copiar el resultado final para verificar/anunciar la remesa corregida.

begin;

create temporary table _current_shop_round on commit drop as
select
  max(jornada)::integer as jornada,
  coalesce(max(announced_at), now()) as announced_at,
  coalesce(max(activates_at), now() + interval '24 hours') as activates_at
from public.shop_discounts
where active = true;

update public.shop_discounts
set active = false,
    exhausted_at = coalesce(exhausted_at, now())
where active = true
  and category = 'crianza'
  and jornada = (select jornada from _current_shop_round);

insert into public.shop_discounts (
  item,
  category,
  base_price,
  discount_price,
  stock_total,
  stock_used,
  discount_kind,
  jornada,
  active,
  created_at,
  announced_at,
  activates_at,
  exhausted_at
)
select
  'Chapa Dorada',
  'crianza',
  15,
  13,
  2,
  0,
  'normal',
  jornada,
  true,
  now(),
  announced_at,
  activates_at,
  null::timestamptz
from _current_shop_round
where jornada is not null;

insert into public.shop_discounts (
  item,
  category,
  base_price,
  discount_price,
  stock_total,
  stock_used,
  discount_kind,
  jornada,
  active,
  created_at,
  announced_at,
  activates_at,
  exhausted_at
)
select
  'Capsula Habilidad',
  'crianza',
  8,
  4,
  1,
  0,
  'mega',
  jornada,
  true,
  now(),
  announced_at,
  activates_at,
  null::timestamptz
from _current_shop_round
where jornada is not null;

commit;

select
  jornada,
  category,
  discount_kind,
  item,
  base_price,
  discount_price,
  stock_total,
  stock_used,
  activates_at
from public.shop_discounts
where active = true
  and jornada = (
    select max(jornada)
    from public.shop_discounts
    where active = true
  )
order by
  case category
    when 'comodines' then 1
    when 'competitivos' then 2
    when 'crianza' then 3
    else 9
  end,
  case discount_kind when 'normal' then 1 else 2 end,
  item;
