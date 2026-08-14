# Blush Closet

The site for Blush Closet — a fashion house and luxury hair studio in Afienya, Accra. Bridal, ready-to-wear, custom couture, and premium wigs & extensions, plus a small e-commerce layer for browsing and ordering.

Live at **[blushcloset.xyz](https://blushcloset.xyz)**.

## How it's put together

Two independently deployed pieces:

| Piece | What it is | Lives at | Deployed via |
|---|---|---|---|
| **Site** | [`index.html`](index.html) — single-file static HTML/CSS/JS | `blushcloset.xyz` | Cloudflare Workers (static assets), auto-deploys on push to `master` |
| **Backend** | [`backend/`](backend/) — FastAPI + admin dashboard | `blush-production.up.railway.app` | Railway, auto-deploys on push to `master` (Root Directory set to `backend`) |

The site works standalone — every API-dependent feature (products, hero media, site stats, order/consultation forms) falls back to static content already baked into `index.html` if the backend is unreachable. See `apiFetch()` near the bottom of `index.html`.

Data lives in Supabase (Postgres + Storage). Full backend setup, environment variables, and the API reference are in **[backend/README.md](backend/README.md)** — read that before touching the backend.

## The site (`index.html`)

Single file, no build step. Sections: hero (video/photo rotation), designer bio, category strip, shop grid (the product catalog — filterable, sortable, with a Quick View lightbox and an order-request modal), stats, contact/booking form, footer.

**Images and videos are auto-discovered, not hardcoded.** Drop a file in following one of these naming conventions and the site's JS finds it on load by probing sequentially until a number 404s — no code changes needed:

| Convention | Used for |
|---|---|
| `image1.jpg`, `image2.jpg`, ... (any of `.jpg`/`.jpeg`/`.png`/`.webp`, mixed extensions fine) | Hero photo fallback + the shop grid's file-probed fallback (only used if the API has no products) |
| `hero-reel-1.mp4`, `hero-reel-2.mp4`, ... | Hero video rotation |
| `look-video-1.mp4`, `look-video-2.mp4`, ... | Video entries in the shop grid's fallback |

In practice, most product photos now go through the admin dashboard instead (`/admin` → Products), which uploads to Supabase Storage and watermarks the image — see below. The `imageN.jpg` convention still matters for the hero fallback and as a no-JS-backend safety net.

**Filenames are case-sensitive in production.** macOS's filesystem isn't, so a mismatch (`Image1.JPG` referenced as `image1.jpg`) works locally and 404s on Cloudflare. Keep new files lowercase.

## Watermarking

Every photo or video uploaded through the admin dashboard (`/admin` → Products or Hero Media) gets a tiled, low-opacity watermark of the brand mark baked in server-side before it's stored — a deterrent against screenshots/downloads being reused without attribution. Fashion pieces (Ready-to-Wear, Bridal, Custom Atelier) get `logo.jpg`; Luxury Hair pieces get `hair-logo.jpg`. The product form picks the right one automatically from the selected category; the hero media form has an explicit Fashion/Hair selector since hero media has no category.

Implementation is in `backend/app/watermark.py`:

- **Photos** — Pillow masks each brand mark down to its circular badge, tiles it diagonally across the image, and composites it in-process.
- **Videos** — the same tiled pattern is rendered once as a transparent PNG sized to the video's own resolution (via `ffprobe`), then overlaid onto every frame with `ffmpeg` (`libx264`, audio stream copied untouched — no re-encode). Needs `ffmpeg`/`ffprobe` on `PATH`; `backend/railpack.json` tells Railway to install `ffmpeg` as an apt package at deploy time. A ~36s/6.8MB hero clip watermarks in under 2 seconds locally.

Both paths are wired into the upload endpoint in `backend/app/routers/uploads.py` / `backend/app/storage.py`.

## Admin dashboard (`backend/admin/index.html`)

Single-file, no build step, served by FastAPI at `/admin`. Login, then tabs for Consultations, Products, Orders, Hero Media, Site Settings. On phones (≤860px) the sidebar becomes an off-canvas drawer opened by a hamburger button, rather than permanently eating half the screen.

## Local development

```bash
# Site — any static server works, e.g.:
python3 -m http.server 5500

# Backend — see backend/README.md for the full setup (Python 3.12, .env, migrations)
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

The site's `API_BASE_URL` constant (near the bottom of `index.html`) points at the deployed Railway backend by default, so it talks to production data even when served locally. Point it at `http://127.0.0.1:8000` if you want to test against a local backend instead.

## Known gaps

- **No payments** — "Order This" captures a request for manual follow-up, not a transaction. Paystack is the natural fit if that changes (works well for GHS); see the note in `backend/README.md`.
- **A handful of loose `*.MP4` files at the repo root** (UUID filenames) aren't wired into the site — they don't match the `hero-reel-N.mp4` / `look-video-N.mp4` convention above, so the site never discovers them. Rename them into that convention if they're meant to be live.
