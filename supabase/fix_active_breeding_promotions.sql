-- Corrige las promociones activas de Crianza de la jornada actual.
-- Regla actual:
-- - Chapa Dorada no puede aparecer ni en Rebaja ni en Mega Rebaja.
-- - Si no existe ya, Capsula Habilidad queda como Mega Rebaja: 8 -> 4.
--
-- Uso:
-- 1) Ejecutar en Supabase SQL Editor.
-- 2) Copiar el resultado final para verificar/anunciar la remesa corregida.

update public.shop_discounts
set active = false,
    exhausted_at = coalesce(exhausted_at, now())
where active = true
  and item = 'Chapa Dorada'
  and jornada = (
    select max(jornada)
    from public.shop_discounts
    where active = true
  );

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
from (
  select
    max(jornada)::integer as jornada,
    coalesce(max(announced_at), now()) as announced_at,
    coalesce(max(activates_at), now() + interval '24 hours') as activates_at
  from public.shop_discounts
  where active = true
) ctx
where ctx.jornada is not null
  and not exists (
    select 1
    from public.shop_discounts d
    where d.active = true
      and d.jornada = ctx.jornada
      and d.item = 'Capsula Habilidad'
  )
  and not exists (
    select 1
    from public.purchases p
    where lower(trim(p.item)) = lower('Capsula Habilidad')
  );

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
