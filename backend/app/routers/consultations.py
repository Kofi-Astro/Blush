# Booking/consultation requests: customers submit these from the site's
# booking form (public, no login needed); the admin views/manages them from
# the dashboard's Bookings tab (login required, via require_admin).

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import ConsultationRequest
from ..schemas import ConsultationCreate, ConsultationOut, ConsultationStatusUpdate

router = APIRouter(prefix="/api/consultations", tags=["consultations"])

VALID_STATUSES = {"pending", "confirmed", "in_progress", "completed", "cancelled"}


@router.post("", response_model=ConsultationOut, status_code=status.HTTP_201_CREATED)
def create_consultation(payload: ConsultationCreate, db: Session = Depends(get_db)):
    """Public endpoint — the site's booking form posts here."""
    # Spam bots fill out every field, including hidden ones a real visitor
    # never sees or fills. Any value here means it's not a real submission.
    if payload.website:
        raise HTTPException(status_code=400, detail="Invalid submission")

    # `exclude={"website"}` drops the honeypot field — it's not a real
    # database column, just a spam trap on the incoming request.
    consultation = ConsultationRequest(**payload.model_dump(exclude={"website"}))
    db.add(consultation)
    db.commit()
    db.refresh(consultation)
    return consultation


@router.get("", response_model=list[ConsultationOut], dependencies=[Depends(require_admin)])
def list_consultations(status_filter: str | None = None, db: Session = Depends(get_db)):
    """Admin-only — powers the dashboard's Bookings list, newest first, optionally filtered by status."""
    stmt = select(ConsultationRequest).order_by(ConsultationRequest.created_at.desc())
    if status_filter:
        stmt = stmt.where(ConsultationRequest.status == status_filter)
    return db.execute(stmt).scalars().all()


@router.patch("/{consultation_id}", response_model=ConsultationOut, dependencies=[Depends(require_admin)])
def update_consultation_status(consultation_id: uuid.UUID, payload: ConsultationStatusUpdate, db: Session = Depends(get_db)):
    """Admin-only — moves a booking through its workflow (pending → confirmed → ... → completed/cancelled)."""
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_STATUSES)}")

    consultation = db.get(ConsultationRequest, consultation_id)
    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")

    consultation.status = payload.status
    db.commit()
    db.refresh(consultation)
    return consultation


@router.delete("/{consultation_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_consultation(consultation_id: uuid.UUID, db: Session = Depends(get_db)):
    """Admin-only — permanently removes a booking request."""
    consultation = db.get(ConsultationRequest, consultation_id)
    if consultation is None:
        raise HTTPException(status_code=404, detail="Consultation not found")

    db.delete(consultation)
    db.commit()
