from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {"status": "ok"}


admin_dir = Path(__file__).resolve().parent.parent / "admin"
if admin_dir.exists():
    app.mount("/admin", StaticFiles(directory=admin_dir, html=True), name="admin")
