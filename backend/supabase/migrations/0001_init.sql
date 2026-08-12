-- ============================================================
-- BLUSH CLOSET — Supabase schema
-- Run this in: Supabase Dashboard -> SQL Editor -> New query -> Run
--
-- Covers three things:
--   1. Products (replaces the static image1.jpg-style Lookbook --
--      every item, purchasable or not, lives here now)
--   2. Orders (client purchase requests -- no online payment yet,
--      per your call to do that in a later phase)
--   3. Consultations (same purpose as the current Formspree form;
--      migrating the form itself to Supabase is a later step)
--
-- Row Level Security (RLS) is on for every table, since Supabase
-- exposes your database directly over a public API. The rule
-- throughout: anyone can READ products/categories and CREATE an
-- order/consultation (that's the public site's job); only a logged-in
-- admin (via Supabase Auth) can read orders/consultations or manage
-- products (that's the admin dashboard's job).
-- ============================================================

create extension if not exists pgcrypto;

create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- ============================================================
-- 1. LOOKUP TABLES
-- ============================================================
create table product_categories (
  id         smallserial primary key,
  name       varchar(60) not null unique,   -- e.g. 'Luxury Hair'
  slug       varchar(60) not null unique,   -- e.g. 'hair' (matches the site's lb-tabs filters)
  created_at timestamptz not null default now()
);

create table service_types (
  id         smallserial primary key,
  name       varchar(80) not null unique,   -- e.g. 'Bridal Couture'
  slug       varchar(60) not null unique,
  created_at timestamptz not null default now()
);

-- ============================================================
-- 2. PRODUCTS -- every Lookbook item now lives here, whether it's
--    purchasable or just a styled look. is_purchasable is what
--    decides whether an "Order" button shows on the storefront.
-- ============================================================
create table products (
  id              uuid primary key default gen_random_uuid(),
  title           varchar(150) not null,
  description     text,
  price           numeric(10,2),             -- null for made-to-order/POA items
  currency        varchar(3) not null default 'GHS',
  image_url       text not null,             -- Supabase Storage public URL
  look_number     smallint,
  category_id     smallint not null references product_categories(id) on delete restrict,
  is_purchasable  boolean not null default true,
  is_featured     boolean not null default false,
  stock_status    varchar(20) not null default 'made_to_order',
  display_order   integer not null default 0,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint chk_stock_status check (stock_status in ('made_to_order','in_stock','sold_out')),
  constraint chk_price_positive check (price is null or price >= 0)
);

create index idx_products_category on products(category_id);
create index idx_products_order on products(category_id, display_order);

create trigger trg_products_updated_at
  before update on products
  for each row execute function set_updated_at();

-- ============================================================
-- 3. ORDERS + ORDER ITEMS -- "order request" model: no payment
--    collected here, just captured for manual follow-up.
-- ============================================================
create table orders (
  id              uuid primary key default gen_random_uuid(),
  full_name       varchar(150) not null,
  email           varchar(255) not null,
  phone           varchar(30) not null,
  delivery_notes  text,                      -- address / pickup preference / anything client added
  status          varchar(20) not null default 'pending',
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),

  constraint chk_order_status check (status in ('pending','confirmed','processing','ready','completed','cancelled')),
  constraint chk_order_email_format check (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

create trigger trg_orders_updated_at
  before update on orders
  for each row execute function set_updated_at();

create table order_items (
  id                    uuid primary key default gen_random_uuid(),
  order_id              uuid not null references orders(id) on delete cascade,
  product_id            uuid references products(id) on delete set null,
  product_title_snapshot varchar(150) not null,   -- kept even if the product is later edited/removed
  quantity              integer not null default 1,
  price_at_order        numeric(10,2),
  notes                 text,                      -- e.g. "26 inch, bone straight" or "size M"

  constraint chk_quantity_positive check (quantity > 0)
);

create index idx_order_items_order on order_items(order_id);

-- ============================================================
-- 4. CONSULTATIONS -- same shape as before; the Formspree form can
--    be pointed here in a later step if you want bookings and
--    orders managed in one place.
-- ============================================================
create table consultation_requests (
  id                   uuid primary key default gen_random_uuid(),
  full_name            varchar(150) not null,
  email                varchar(255) not null,
  phone                varchar(30) not null,
  service_type_id      smallint references service_types(id) on delete set null,
  preferred_date       date,
  design_requirements  text,
  status               varchar(20) not null default 'pending',
  created_at           timestamptz not null default now(),
  updated_at           timestamptz not null default now(),

  constraint chk_consultation_status check (status in ('pending','confirmed','in_progress','completed','cancelled')),
  constraint chk_consultation_email_format check (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

create trigger trg_consultations_updated_at
  before update on consultation_requests
  for each row execute function set_updated_at();

-- ============================================================
-- 5. SEED DATA -- matches the categories/services already used on the site
-- ============================================================
insert into product_categories (name, slug) values
  ('Ready-to-Wear', 'fashion'),
  ('Bridal',        'bridal'),
  ('Luxury Hair',   'hair'),
  ('Custom Atelier','custom');

insert into service_types (name, slug) values
  ('Bridal Couture',            'bridal'),
  ('Ready-to-Wear',             'rtw'),
  ('Custom Atelier Commission', 'custom'),
  ('Luxury Hair',               'hair');

-- ============================================================
-- 6. ROW LEVEL SECURITY
-- ============================================================
alter table product_categories enable row level security;
alter table service_types      enable row level security;
alter table products           enable row level security;
alter table orders             enable row level security;
alter table order_items        enable row level security;
alter table consultation_requests enable row level security;

-- Public (anonymous) can read categories, service types, and products --
-- this is what the storefront/Lookbook uses.
create policy "public read categories" on product_categories for select using (true);
create policy "public read service types" on service_types for select using (true);
create policy "public read products" on products for select using (true);

-- Only a logged-in admin (any authenticated Supabase user -- this is a
-- single-admin setup, same spirit as the earlier FastAPI version) can
-- create/edit/delete products.
create policy "admin manage products" on products for all
  using (auth.role() = 'authenticated')
  with check (auth.role() = 'authenticated');

-- Public can submit an order (insert only -- they can't read other
-- clients' orders back). Only the admin can read/update them.
create policy "public create orders" on orders for insert with check (true);
create policy "admin read orders" on orders for select using (auth.role() = 'authenticated');
create policy "admin update orders" on orders for update using (auth.role() = 'authenticated');

create policy "public create order items" on order_items for insert with check (true);
create policy "admin read order items" on order_items for select using (auth.role() = 'authenticated');

-- Same pattern for consultations.
create policy "public create consultations" on consultation_requests for insert with check (true);
create policy "admin read consultations" on consultation_requests for select using (auth.role() = 'authenticated');
create policy "admin update consultations" on consultation_requests for update using (auth.role() = 'authenticated');
