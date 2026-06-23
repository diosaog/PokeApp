-- Elimina Chapa Dorada de las promociones activas de la jornada actual.
-- No toca el resto de rebajas.

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
