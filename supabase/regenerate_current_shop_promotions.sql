-- Regenera la tanda activa de promociones de la jornada actual.
-- Uso:
-- 1) Ejecutar en Supabase SQL Editor.
-- 2) Copiar el resultado final devuelto para anunciar la lista corregida.
--
-- No toca purchases ni inventarios. Solo desactiva la tanda activa actual de
-- shop_discounts y crea otra excluyendo cualquier objeto que aparezca alguna
-- vez en purchases.

begin;

drop table if exists _old_shop_promos;
drop table if exists _promo_context;
drop table if exists _shop_catalog;
drop table if exists _eligible_shop_promos;
drop table if exists _selected_shop_promos;
drop table if exists _new_shop_promos;

create temporary table _old_shop_promos on commit preserve rows as
select *
from public.shop_discounts
where active = true
  and jornada = (
    select max(jornada)
    from public.shop_discounts
    where active = true
  );

create temporary table _promo_context on commit preserve rows as
select
  coalesce((select max(jornada) from _old_shop_promos), 4)::integer as jornada,
  now() as announced_at,
  coalesce(
    (select max(activates_at) from _old_shop_promos),
    now() + interval '24 hours'
  ) as activates_at;

update public.shop_discounts
set active = false,
    exhausted_at = coalesce(exhausted_at, now())
where active = true
  and jornada = (select jornada from _promo_context);

create temporary table _shop_catalog (
  category text not null,
  item text not null,
  base_price integer not null
) on commit preserve rows;

insert into _shop_catalog(category, item, base_price) values
  ('comodines', 'Revivir Pokemon', 12),
  ('comodines', 'Robar Pokemon', 12),
  ('comodines', 'Captura Extra', 5),
  ('comodines', 'Blindar Pokemon', 12),
  ('comodines', 'Fosil', 5),
  ('competitivos', 'Gafas Elegidas', 8),
  ('competitivos', 'Cinta Elegida', 8),
  ('competitivos', 'Panuelo Elegido', 8),
  ('competitivos', 'Restos', 8),
  ('competitivos', 'Banda Focus', 7),
  ('competitivos', 'Vidasfera', 7),
  ('competitivos', 'Mineral Evolutivo', 8),
  ('competitivos', 'Casco Dentado', 7),
  ('competitivos', 'Globo Helio', 5),
  ('competitivos', 'Gemas Elementales', 6),
  ('competitivos', 'Boton Escape', 4),
  ('competitivos', 'Tarjeta Roja', 4),
  ('competitivos', 'Hierba Blanca', 5),
  ('competitivos', 'Roca del Rey', 5),
  ('competitivos', 'Periscopio', 5),
  ('competitivos', 'Lupa', 5),
  ('competitivos', 'Toxisfera', 5),
  ('competitivos', 'Llamasfera', 5),
  ('competitivos', 'Objeto Potenciador de Tipo', 4),
  ('crianza', 'Capsula Habilidad', 8),
  ('crianza', 'Chapa Dorada', 15),
  ('crianza', 'Chapa Plateada', 6),
  ('crianza', 'Menta de Naturaleza', 6),
  ('crianza', 'Objeto Evolutivo', 4);

create temporary table _eligible_shop_promos on commit preserve rows as
select c.*
from _shop_catalog c
where not exists (
    select 1
    from public.purchases p
    where lower(trim(p.item)) = lower(trim(c.item))
  )
  and c.item <> 'Chapa Dorada'
  and not exists (
    select 1
    from _old_shop_promos oldp
    where lower(trim(oldp.item)) = lower(trim(c.item))
  );

create temporary table _selected_shop_promos (
  category text not null,
  item text not null,
  base_price integer not null,
  discount_kind text not null
) on commit preserve rows;

insert into _selected_shop_promos(category, item, base_price, discount_kind)
select category, item, base_price, 'mega'
from (
  select e.*, row_number() over (order by random()) as rn
  from _eligible_shop_promos e
  where e.category = 'comodines'
    and e.base_price > 4
    and e.item <> 'Objeto Evolutivo'
) x
where rn <= 1;

insert into _selected_shop_promos(category, item, base_price, discount_kind)
select category, item, base_price, 'normal'
from (
  select e.*, row_number() over (order by random()) as rn
  from _eligible_shop_promos e
  where e.category = 'comodines'
    and not exists (
      select 1 from _selected_shop_promos s where s.item = e.item
    )
) x
where rn <= 1;

insert into _selected_shop_promos(category, item, base_price, discount_kind)
select category, item, base_price, 'mega'
from (
  select e.*, row_number() over (order by random()) as rn
  from _eligible_shop_promos e
  where e.category = 'competitivos'
    and e.base_price > 4
    and e.item <> 'Objeto Evolutivo'
) x
where rn <= 2;

insert into _selected_shop_promos(category, item, base_price, discount_kind)
select category, item, base_price, 'normal'
from (
  select e.*, row_number() over (order by random()) as rn
  from _eligible_shop_promos e
  where e.category = 'competitivos'
    and not exists (
      select 1 from _selected_shop_promos s where s.item = e.item
    )
) x
where rn <= 4;

insert into _selected_shop_promos(category, item, base_price, discount_kind)
select category, item, base_price, 'mega'
from (
  select e.*, row_number() over (order by random()) as rn
  from _eligible_shop_promos e
  where e.category = 'crianza'
    and e.base_price > 4
    and e.item <> 'Objeto Evolutivo'
) x
where rn <= 1;

insert into _selected_shop_promos(category, item, base_price, discount_kind)
select category, item, base_price, 'normal'
from (
  select e.*, row_number() over (order by random()) as rn
  from _eligible_shop_promos e
  where e.category = 'crianza'
    and not exists (
      select 1 from _selected_shop_promos s where s.item = e.item
    )
) x
where rn <= 1;

create temporary table _new_shop_promos on commit preserve rows as
with inserted as (
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
    s.item,
    s.category,
    s.base_price,
    case
      when s.discount_kind = 'mega' and s.base_price = 12 then 8
      when s.discount_kind = 'mega' then greatest(1, ceil(s.base_price * 0.5)::integer)
      when s.base_price >= 6 then s.base_price - 2
      else s.base_price - 1
    end as discount_price,
    case when s.discount_kind = 'mega' then 1 else 2 end as stock_total,
    0 as stock_used,
    s.discount_kind,
    ctx.jornada,
    true as active,
    now() as created_at,
    ctx.announced_at,
    ctx.activates_at,
    null::timestamptz as exhausted_at
  from _selected_shop_promos s
  cross join _promo_context ctx
  returning
    id,
    jornada,
    category,
    item,
    base_price,
    discount_price,
    stock_total,
    discount_kind,
    activates_at
)
select *
from inserted;

commit;

select
  jornada,
  category,
  discount_kind,
  item,
  base_price,
  discount_price,
  stock_total,
  activates_at
from _new_shop_promos
order by
  case category
    when 'comodines' then 1
    when 'competitivos' then 2
    when 'crianza' then 3
    else 9
  end,
  case discount_kind when 'normal' then 1 else 2 end,
  item;

