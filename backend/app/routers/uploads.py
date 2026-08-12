from fastapi import APIRouter, Depends, File, UploadFile

from ..deps import require_admin
from ..schemas import UploadResponse
from ..storage import upload_media_file

router = APIRouter(prefix="/api/uploads", tags=["uploads"], dependencies=[Depends(require_admin)])

ALLOWED_FOLDERS = {"products", "hero"}


@router.post("/{folder}", response_model=UploadResponse)
async def upload_file(folder: str, file: UploadFile = File(...)):
    if folder not in ALLOWED_FOLDERS:
        folder = "products"

    url = await upload_media_file(file, folder)
    return UploadResponse(url=url)
