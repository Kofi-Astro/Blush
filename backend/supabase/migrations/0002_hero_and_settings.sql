-- ============================================================
-- BLUSH CLOSET — hero media + site settings
-- Adds what 0001_init.sql doesn't cover: the homepage hero video/photo
-- rotation, and small editable copy (stat numbers, etc).
-- Run this in: Supabase Dashboard -> SQL Editor -> New query -> Run
-- (after 0001_init.sql)
-- ============================================================

-- ── hero_media: the homepage hero video/photo rotation ──
create table if not exists hero_media (
  id bigint generated always as identity primary key,
  media_type text not null check (media_type in ('video', 'photo')),
  media_url text not null,
  sort_order integer not null default 0,
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists hero_media_active_idx on hero_media (is_active, sort_order);

alter table hero_media enable row level security;
create policy "public read hero media" on hero_media for select using (true);
create policy "admin manage hero media" on hero_media for all
  using (auth.role() = 'authenticated')
  with check (auth.role() = 'authenticated');

-- ── site_settings: small editable copy (stats, about text, contact) ──
create table if not exists site_settings (
  key text primary key,
  value text,
  updated_at timestamptz not null default now()
);

create trigger site_settings_set_updated_at
  before update on site_settings
  for each row execute function set_updated_at();

insert into site_settings (key, value) values
  ('stats_clients', '200+'),
  ('stats_collections', '24'),
  ('stats_years', '5+'),
  ('stats_product_lines', '2')
on conflict (key) do nothing;

alter table site_settings enable row level security;
create policy "public read site settings" on site_settings for select using (true);
create policy "admin manage site settings" on site_settings for all
  using (auth.role() = 'authenticated')
  with check (auth.role() = 'authenticated');

-- ── storage bucket for product/hero media uploads ──
insert into storage.buckets (id, name, public)
values ('media', 'media', true)
on conflict (id) do nothing;

drop policy if exists "Public read access for media bucket" on storage.objects;
create policy "Public read access for media bucket"
  on storage.objects for select
  using (bucket_id = 'media');
