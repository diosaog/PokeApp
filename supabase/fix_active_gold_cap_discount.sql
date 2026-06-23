-- Corrige la Mega Rebaja activa de Chapa Dorada a 12 monedas.
-- Uso:
-- 1) Ejecutar en Supabase SQL Editor.
-- 2) Copiar el resultado final si quieres verificarlo.

update public.shop_discounts
set discount_price = 12
where active = true
  and item = 'Chapa Dorada'
  and discount_kind = 'mega'
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
