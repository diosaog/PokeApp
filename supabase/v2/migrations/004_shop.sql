-- PokeApp Supabase V2 greenfield schema.
-- 004_shop: catalog, promotions, purchases, redemptions and coin ledger.

begin;

create table public.shop_items (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  category text not null,
  description text not null default '',
  base_price integer not null,
  enabled boolean not null default true,
  image_key text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint shop_items_code_chk
    check (code = lower(code) and code ~ '^[a-z0-9][a-z0-9_-]*$'),
  constraint shop_items_name_chk
    check (length(btrim(name)) > 0),
  constraint shop_items_category_chk
    check (category in ('comodines', 'bayas', 'competitivos', 'crianza', 'other')),
  constraint shop_items_base_price_chk
    check (base_price >= 0)
);

create trigger shop_items_set_updated_at
before update on public.shop_items
for each row execute function public.set_updated_at();

comment on table public.shop_items is
  'Version-controlled seedable shop catalog. Visible names are not foreign keys.';

create table public.shop_promotions (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  matchday_id uuid references public.matchdays(id) on delete restrict,
  shop_item_id uuid not null references public.shop_items(id) on delete restrict,
  promotion_type text not null,
  status text not null default 'pending',
  base_price integer not null,
  effective_price integer not null,
  stock_total integer not null,
  stock_used integer not null default 0,
  announced_at timestamptz,
  activates_at timestamptz,
  ends_at timestamptz,
  exhausted_at timestamptz,
  dedupe_key text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint shop_promotions_type_chk
    check (promotion_type in ('normal', 'mega')),
  constraint shop_promotions_status_chk
    check (status in ('pending', 'active', 'ended', 'exhausted', 'cancelled')),
  constraint shop_promotions_prices_chk
    check (base_price >= 0 and effective_price >= 0 and effective_price <= base_price),
  constraint shop_promotions_stock_chk
    check (stock_total >= 0 and stock_used >= 0 and stock_used <= stock_total),
  constraint uq_shop_promotions_id_season
    unique (id, season_id),
  constraint fk_shop_promotions_matchday_same_season
    foreign key (matchday_id, season_id)
    references public.matchdays(id, season_id)
    on delete restrict
);

create trigger shop_promotions_set_updated_at
before update on public.shop_promotions
for each row execute function public.set_updated_at();

comment on table public.shop_promotions is
  'Rotating discounts. Future API/RPC must claim stock atomically before inserting purchases.';

create table public.purchases (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  trainer_id uuid not null,
  season_player_id uuid not null,
  shop_item_id uuid not null references public.shop_items(id) on delete restrict,
  promotion_id uuid,
  quantity integer not null default 1,
  unit_price integer not null,
  total_price integer generated always as (quantity * unit_price) stored,
  status text not null default 'pending',
  purchased_at timestamptz not null default now(),
  metadata jsonb not null default '{}'::jsonb,
  constraint purchases_quantity_chk
    check (quantity > 0),
  constraint purchases_unit_price_chk
    check (unit_price >= 0),
  constraint purchases_status_chk
    check (status in ('pending', 'used', 'cancelled', 'refunded')),
  constraint uq_purchases_id_season_trainer_item
    unique (id, season_id, trainer_id, shop_item_id),
  constraint fk_purchases_player_same_owner
    foreign key (season_player_id, season_id, trainer_id)
    references public.season_players(id, season_id, trainer_id)
    on delete restrict,
  constraint fk_purchases_promotion_same_season
    foreign key (promotion_id, season_id)
    references public.shop_promotions(id, season_id)
    on delete restrict
);

comment on table public.purchases is
  'Auditable single-item purchases. No purchase_lines until the product needs multi-item carts.';

create table public.redemptions (
  id uuid primary key default gen_random_uuid(),
  purchase_id uuid not null references public.purchases(id) on delete restrict,
  season_id uuid not null,
  trainer_id uuid not null,
  season_player_id uuid not null,
  shop_item_id uuid not null references public.shop_items(id) on delete restrict,
  redemption_type text not null default 'item_use',
  status text not null default 'applied',
  payload jsonb not null default '{}'::jsonb,
  redeemed_at timestamptz not null default now(),
  constraint redemptions_type_chk
    check (length(btrim(redemption_type)) > 0),
  constraint redemptions_status_chk
    check (status in ('applied', 'reverted', 'cancelled')),
  constraint fk_redemptions_purchase_same_owner_item
    foreign key (purchase_id, season_id, trainer_id, shop_item_id)
    references public.purchases(id, season_id, trainer_id, shop_item_id)
    on delete restrict,
  constraint fk_redemptions_player_same_owner
    foreign key (season_player_id, season_id, trainer_id)
    references public.season_players(id, season_id, trainer_id)
    on delete restrict
);

comment on table public.redemptions is
  'Purchase redemption/use audit. Purchase and redemption are intentionally separate.';

create table public.coin_transactions (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  trainer_id uuid not null,
  season_player_id uuid not null,
  amount integer not null,
  transaction_type text not null,
  reference_type text not null default '',
  reference_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_by_trainer_id uuid references public.trainers(id) on delete set null,
  created_at timestamptz not null default now(),
  constraint coin_transactions_amount_chk
    check (amount <> 0),
  constraint coin_transactions_type_chk
    check (transaction_type in ('matchday_reward', 'purchase', 'penalty', 'admin_adjustment', 'compensation')),
  constraint fk_coin_transactions_player_same_owner
    foreign key (season_player_id, season_id, trainer_id)
    references public.season_players(id, season_id, trainer_id)
    on delete restrict
);

comment on table public.coin_transactions is
  'Coin ledger. Balance is sum(amount); cached balances must be reconstructible from this table.';

commit;
