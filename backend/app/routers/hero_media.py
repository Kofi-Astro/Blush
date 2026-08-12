from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import HeroMedia
from ..schemas import HeroMediaIn, HeroMediaOut

router = APIRouter(prefix="/api/hero-media", tags=["hero-media"])


@router.get("", response_model=list[HeroMediaOut])
def list_hero_media(db: Session = Depends(get_db)):
    """Public endpoint — active hero media in display order."""
    stmt = select(HeroMedia).where(HeroMedia.is_active.is_(True)).order_by(HeroMedia.sort_order, HeroMedia.id)
    return db.execute(stmt).scalars().all()


@router.get("/all", response_model=list[HeroMediaOut], dependencies=[Depends(require_admin)])
def list_all_hero_media(db: Session = Depends(get_db)):
    stmt = select(HeroMedia).order_by(HeroMedia.sort_order, HeroMedia.id)
    return db.execute(stmt).scalars().all()


@router.post("", response_model=HeroMediaOut, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def create_hero_media(payload: HeroMediaIn, db: Session = Depends(get_db)):
    item = HeroMedia(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=HeroMediaOut, dependencies=[Depends(require_admin)])
def update_hero_media(item_id: int, payload: HeroMediaIn, db: Session = Depends(get_db)):
    item = db.get(HeroMedia, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Hero media not found")

    for field, value in payload.model_dump().items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_hero_media(item_id: int, db: Session = Depends(get_db)):
    item = db.get(HeroMedia, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Hero media not found")

    db.delete(item)
    db.commit()
