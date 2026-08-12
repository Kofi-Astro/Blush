# Blush Closet — Backend

FastAPI backend + admin dashboard for the Blush Closet site, backed by Supabase
(Postgres for data, Storage for uploaded photos, RLS as defense-in-depth).

## What this manages

- **Products** — every Lookbook item lives here now (`is_purchasable` decides
  whether it's just a styled look or something orderable).
- **Orders** — order requests placed against products. No payment collected
  yet — just captured for manual follow-up.
- **Consultations** — the site's contact form (same purpose the Formspree
  integration served before).
- **Hero media** — the homepage video/photo rotation.
- **Site settings** — small editable copy (stats numbers, etc).
- **Categories / service types** — fixed lookup data (Bridal, Luxury Hair,
  etc). Read-only via the API by design — add/edit these directly in
  Supabase's Table Editor rather than through `/admin`.

The public site (`../index.html`) calls the read endpoints below and falls
back to its original static content if the API is unreachable, so it's safe
to run this locally without breaking the live site.

## Architecture note: FastAPI + RLS together

Every table has Row Level Security enabled with policies like
`using (auth.role() = 'authenticated')` for admin-only access — that's
Supabase's own model, checked when something queries the database through
Supabase's REST/Storage API with a Supabase Auth session.

This backend instead connects straight to Postgres with the DB
superuser (via `DATABASE_URL`) and to Storage with the **service role /
secret key** — both bypass RLS entirely, by design. So the actual admin
check here is FastAPI's own single-admin JWT (`app/deps.py`,
`require_admin`), not the RLS policies. The RLS policies still matter as a
safety net (e.g. if the publishable/anon key were ever used to query
Supabase directly from a browser, public-read/public-insert is all it could
do), they just aren't the enforcement layer for admin writes in this setup.

## One-time setup

1. **Run the migrations**, in order, in Supabase SQL Editor → New query:
   - `supabase/migrations/0001_init.sql` — products, orders, consultations
   - `supabase/migrations/0002_hero_and_settings.sql` — hero media, site
     settings, and the public `media` storage bucket

2. **Create your `.env`.**
   ```bash
   cd backend
   cp .env.example .env
   ```
   Fill in:
   - `DATABASE_URL` — Supabase → Project Settings → Database → Connection
     string. **Use the pooler connection (Transaction or Session pooler,
     `*.pooler.supabase.com`), not "Direct connection"** — the direct host
     is IPv6-only on the free tier, which fails outright on any IPv4-only
     network.
   - `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` — Project Settings → API
     Keys. On newer projects the secret key looks like `sb_secret_...`
     rather than the older JWT format — either works, but you need
     `supabase-py >= 2.31` for the new format (already pinned in
     `requirements.txt`).
   - `JWT_SECRET_KEY` — any random string, e.g.
     `python -c "import secrets; print(secrets.token_hex(32))"`.
   - `ADMIN_USERNAME` / `ADMIN_PASSWORD_HASH` — whatever you want to log
     into `/admin` with. Generate the hash with:
     ```bash
     python scripts/hash_password.py
     ```
     This is a separate credential from Supabase Auth — the admin
     dashboard never talks to Supabase Auth, so no Supabase Auth user needs
     to exist for this to work.

3. **Install dependencies and run.** Use Python 3.12 — `pydantic-core`
   doesn't have a 3.14 wheel yet, and building it from source fails.
   ```bash
   /opt/homebrew/bin/python3.12 -m venv venv   # or wherever your 3.12 lives
   source venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
   API docs: http://127.0.0.1:8000/docs
   Admin dashboard: http://127.0.0.1:8000/admin

## API overview

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/login` | — | Get a JWT for the admin dashboard |
| GET | `/api/categories` | — | Public: product categories |
| GET | `/api/service-types` | — | Public: consultation service types |
| GET | `/api/products` | — | Public: all products (optionally `?category=slug`) |
| POST/PUT/DELETE | `/api/products...` | admin | Manage products |
| POST | `/api/orders` | — | Public: submit an order request |
| GET | `/api/orders` | admin | List orders (with nested items) |
| PATCH | `/api/orders/{id}` | admin | Update order status |
| DELETE | `/api/orders/{id}` | admin | Delete an order |
| POST | `/api/consultations` | — | Public: submit a consultation request |
| GET | `/api/consultations` | admin | List consultation requests |
| PATCH | `/api/consultations/{id}` | admin | Update status |
| DELETE | `/api/consultations/{id}` | admin | Delete a consultation request |
| GET | `/api/hero-media` | — | Public: active hero media |
| GET | `/api/hero-media/all` | admin | All hero media (incl. inactive) |
| POST/PUT/DELETE | `/api/hero-media...` | admin | Manage hero media |
| GET | `/api/settings` | — | Public: site copy/stats |
| PUT | `/api/settings/{key}` | admin | Update one setting |
| POST | `/api/uploads/{folder}` | admin | Upload a file to Storage (`folder` is `products` or `hero`), get back a URL |

Admin endpoints expect `Authorization: Bearer <token>` from `/api/auth/login`.

## Deploying (Railway)

This repo already has Railway's GitHub App connected — it auto-deploys on
every push to `master`. Since the FastAPI app lives in `backend/`, not the
repo root (the repo root is the static site), the Railway service needs to
be told that explicitly:

1. Railway dashboard → the service → Settings → **Root Directory** → `backend`.
2. Settings → **Variables** → add every key from your local `backend/.env`
   (Railway can't read that file — it's gitignored on purpose).
3. `Procfile` (`web: uvicorn app.main:app --host 0.0.0.0 --port $PORT`) and
   `.python-version` (pins 3.12, same reason as local dev) are already in
   `backend/` so the build should just work once the above two are set.
4. Once it's deployed, take the Railway-assigned URL (or a custom domain
   like `api.blushcloset.xyz` pointed at it) and:
   - Set `API_BASE_URL` near the bottom of `../index.html` to that URL.
   - Set `API_BASE_URL` near the top of `<script>` in `admin/index.html` to
     that URL (only needed if the admin dashboard is deployed standalone,
     e.g. to `admin.blushcloset.xyz` — see below).
   - Make sure `ALLOWED_ORIGINS` (in Railway's Variables) includes both
     `https://blushcloset.xyz` and, if applicable, `https://admin.blushcloset.xyz`.

## Deploying the admin dashboard standalone (optional)

`admin/index.html` has no build step and no server-side dependency beyond
the API, so it can be deployed as its own static site — e.g. a second
Cloudflare Pages project pointed at this same repo with **Build output
directory** set to `backend/admin`, with a custom domain like
`admin.blushcloset.xyz`. If you do this, set `API_BASE_URL` in that file (see
above) — same-origin relative paths only work while it's served by
FastAPI's own `/admin` mount.

## Known gap: no video products

`products.image_url` is image-only — there's no video field like
`hero_media` has. The live site's Lookbook "All" carousel still supports
videos via its original file-probing fallback (`look-video-1.mp4`, etc.),
which keeps working as long as `/api/products` doesn't fully replace it. If
you want video products later, add a nullable `video_url` (or a
`media_type`/`media_url` pair, mirroring `hero_media`) via a new migration
file and extend `ProductIn`/`ProductOut` and the admin form to match.

## Adding a new resource later (e.g. payments)

Everything here follows one pattern — copy it rather than inventing a new
shape:

1. **Migration**: add `supabase/migrations/000N_description.sql` with the
   new `create table` (+ RLS policies, for consistency), run it in the
   Supabase SQL editor.
2. **Model**: add a class to `app/models.py` mirroring the table.
3. **Schema**: add `...In`/`...Out` Pydantic models to `app/schemas.py`.
4. **Router**: add `app/routers/<name>.py` with the same
   public-GET-admin-writes shape as `products.py` or `orders.py`.
5. **Register it**: import and `app.include_router(...)` in `app/main.py`.
6. **Admin UI**: add a tab to `admin/index.html` following the existing
   tabs — each is just a fetch + a `<table>` render + a form.

For payments specifically: don't hand-roll card handling — integrate a
provider (Paystack and Stripe both support Ghana) via their hosted
checkout, and store the resulting payment reference on the existing
`orders` table (e.g. add a `payment_reference` column) rather than
building a separate payments table unless you need to track multiple
payment attempts per order.
