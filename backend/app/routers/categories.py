from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ProductCategory
from ..schemas import ProductCategoryOut

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[ProductCategoryOut])
def list_categories(db: Session = Depends(get_db)):
    """Public, read-only. Categories are seed/lookup data managed directly in Supabase."""
    return db.execute(select(ProductCategory).order_by(ProductCategory.id)).scalars().all()
