# Lists booking/consultation service options for the site's booking form
# dropdown. Read-only from the API — service types are added/edited
# directly in Supabase, not here (same pattern as categories.py).

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ServiceType
from ..schemas import ServiceTypeOut

router = APIRouter(prefix="/api/service-types", tags=["service-types"])


@router.get("", response_model=list[ServiceTypeOut])
def list_service_types(db: Session = Depends(get_db)):
    """Public, read-only. Service types are seed/lookup data managed directly in Supabase."""
    return db.execute(select(ServiceType).order_by(ServiceType.id)).scalars().all()
