# The backend's entry point — this is what Railway actually runs. It wires
# together every router (one file per feature area, in routers/) into a
# single FastAPI app, sets up CORS (which frontend domains may call this
# API), and serves the admin dashboard's static files at /admin.

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .routers import (
    auth,
    categories,
    consultations,
    hero_media,
    orders,
    products,
    service_types,
    settings as settings_router,
    uploads,
)

settings = get_settings()

app = FastAPI(title="Blush Closet API")

# Lets the public site (blushcloset.xyz) and local dev servers call this API
# from the browser. `allowed_origins` is configured via an env var — see config.py.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Each of these adds one feature area's endpoints (e.g. products.router
# adds GET/POST/PUT/DELETE /api/products) — see routers/ for the actual logic.
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(service_types.router)
app.include_router(products.router)
app.include_router(orders.router)
app.include_router(consultations.router)
app.include_router(hero_media.router)
app.include_router(settings_router.router)
app.include_router(uploads.router)


@app.get("/api/health")
def health_check():
    """Simple uptime check — Railway/monitoring tools can hit this to confirm the server is alive."""
    return {"status": "ok"}


@app.get("/")
def root():
    # Lets a custom domain like admin.blushcloset.xyz land straight on the
    # dashboard instead of a bare 404 at the root path.
    return RedirectResponse(url="/admin")


# Serves backend/admin/index.html (and any other files in that folder) at
# /admin — this is the whole admin dashboard. It's a single static HTML
# file with its own CSS/JS inline, not a separate build/deploy step.
admin_dir = Path(__file__).resolve().parent.parent / "admin"
if admin_dir.exists():
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")
