from fastapi import APIRouter, Depends, File, Query, UploadFile

from ..deps import require_admin
from ..schemas import UploadResponse
from ..storage import upload_media_file

router = APIRouter(prefix="/api/uploads", tags=["uploads"], dependencies=[Depends(require_admin)])

ALLOWED_FOLDERS = {"products", "hero"}
ALLOWED_WATERMARKS = {"fashion", "hair", "none"}


@router.post("/{folder}", response_model=UploadResponse)
async def upload_file(folder: str, file: UploadFile = File(...), watermark: str = Query("none")):
    if folder not in ALLOWED_FOLDERS:
        folder = "products"
    if watermark not in ALLOWED_WATERMARKS:
        watermark = "none"

    url = await upload_media_file(file, folder, watermark=None if watermark == "none" else watermark)
    return UploadResponse(url=url)
