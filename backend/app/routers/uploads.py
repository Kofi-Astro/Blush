# The one endpoint the admin dashboard's file picker/drag-and-drop calls
# whenever a photo or video is selected — before a product or hero item is
# even created. It uploads (and optionally watermarks, via storage.py) the
# file, then hands back a URL to save onto the product/hero_media record.
# Entire router requires admin login (see `dependencies=` on the router).

from fastapi import APIRouter, Depends, File, Query, UploadFile

from ..deps import require_admin
from ..schemas import UploadResponse
from ..storage import upload_media_file

router = APIRouter(prefix="/api/uploads", tags=["uploads"], dependencies=[Depends(require_admin)])

ALLOWED_FOLDERS = {"products", "hero"}
ALLOWED_WATERMARKS = {"fashion", "hair", "none"}


@router.post("/{folder}", response_model=UploadResponse)
async def upload_file(folder: str, file: UploadFile = File(...), watermark: str = Query("none")):
    """POST /api/uploads/products or /api/uploads/hero, with ?watermark=fashion|hair|none."""
    # Unrecognized folder/watermark values silently fall back to a safe
    # default instead of erroring — keeps the admin UI simple to build against.
    if folder not in ALLOWED_FOLDERS:
        folder = "products"
    if watermark not in ALLOWED_WATERMARKS:
        watermark = "none"

    url = await upload_media_file(file, folder, watermark=None if watermark == "none" else watermark)
    return UploadResponse(url=url)
