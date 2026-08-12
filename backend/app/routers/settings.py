from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import SiteSetting
from ..schemas import SiteSettingOut, SiteSettingUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=list[SiteSettingOut])
def list_settings(db: Session = Depends(get_db)):
    """Public endpoint — all site copy/stat settings, as key/value pairs."""
    return db.execute(select(SiteSetting)).scalars().all()


@router.put("/{key}", response_model=SiteSettingOut, dependencies=[Depends(require_admin)])
def upsert_setting(key: str, payload: SiteSettingUpdate, db: Session = Depends(get_db)):
    setting = db.get(SiteSetting, key)
    if setting is None:
        setting = SiteSetting(key=key, value=payload.value)
        db.add(setting)
    else:
        setting.value = payload.value

    db.commit()
    db.refresh(setting)
    return setting
