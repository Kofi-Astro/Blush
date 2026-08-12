import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import Product, ProductCategory
from ..schemas import ProductIn, ProductOut

router = APIRouter(prefix="/api/products", tags=["products"])


def _to_out(product: Product, category: ProductCategory) -> ProductOut:
    out = ProductOut.model_validate(product)
    out.category_slug = category.slug
    out.category_name = category.name
    return out


@router.get("", response_model=list[ProductOut])
def list_products(category: str | None = None, db: Session = Depends(get_db)):
    """Public — every product (there's no draft/unpublished state in this schema)."""
    stmt = (
        select(Product, ProductCategory)
        .join(ProductCategory, Product.category_id == ProductCategory.id)
        .order_by(Product.display_order, Product.created_at)
    )
    if category:
        stmt = stmt.where(ProductCategory.slug == category)
    rows = db.execute(stmt).all()
    return [_to_out(product, cat) for product, cat in rows]


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_product(payload: ProductIn, db: Session = Depends(get_db)):
    category = db.get(ProductCategory, payload.category_id)
    if category is None:
        raise HTTPException(status_code=400, detail="Unknown category_id")

    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return _to_out(product, category)


@router.put("/{product_id}", response_model=ProductOut, dependencies=[Depends(require_admin)])
def update_product(product_id: uuid.UUID, payload: ProductIn, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    category = db.get(ProductCategory, payload.category_id)
    if category is None:
        raise HTTPException(status_code=400, detail="Unknown category_id")

    for field, value in payload.model_dump().items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return _to_out(product, category)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
