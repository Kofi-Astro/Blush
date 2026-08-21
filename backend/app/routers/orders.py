# Customer orders: submitted from the site's "order this" form (public, no
# login needed), then tracked through fulfillment from the admin dashboard's
# Orders tab (login required). There is no payment processor here — an
# order is just a structured "please contact me, I want this" request.

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import require_admin
from ..models import Order, OrderItem, Product
from ..schemas import OrderCreate, OrderOut, OrderStatusUpdate

router = APIRouter(prefix="/api/orders", tags=["orders"])

VALID_STATUSES = {"pending", "confirmed", "processing", "ready", "completed", "cancelled"}


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_db)):
    """Public — an order request, not a payment. Product title/price are snapshotted
    server-side from the current product record so they can't be spoofed by the client."""
    # Honeypot spam check — see the matching comment in consultations.py.
    if payload.website:
        raise HTTPException(status_code=400, detail="Invalid submission")

    order = Order(
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        delivery_notes=payload.delivery_notes,
    )
    db.add(order)
    db.flush()  # assigns order.id without fully committing yet, so items below can reference it

    for item in payload.items:
        product = db.get(Product, item.product_id) if item.product_id else None
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id if product else None,
                product_title_snapshot=product.title if product else "Custom item",
                quantity=item.quantity,
                price_at_order=product.price if product else None,
                notes=item.notes,
            )
        )

    db.commit()
    return _get_with_items(db, order.id)


@router.get("", response_model=list[OrderOut], dependencies=[Depends(require_admin)])
def list_orders(status_filter: str | None = None, db: Session = Depends(get_db)):
    """Admin-only — powers the dashboard's Orders list, newest first, optionally filtered by status."""
    stmt = select(Order).options(selectinload(Order.items)).order_by(Order.created_at.desc())
    if status_filter:
        stmt = stmt.where(Order.status == status_filter)
    return db.execute(stmt).scalars().all()


@router.patch("/{order_id}", response_model=OrderOut, dependencies=[Depends(require_admin)])
def update_order_status(order_id: uuid.UUID, payload: OrderStatusUpdate, db: Session = Depends(get_db)):
    """Admin-only — moves an order through fulfillment (pending → confirmed → processing → ready → completed/cancelled)."""
    if payload.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(VALID_STATUSES)}")

    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = payload.status
    db.commit()
    return _get_with_items(db, order_id)


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def delete_order(order_id: uuid.UUID, db: Session = Depends(get_db)):
    """Admin-only — permanently removes an order and its line items."""
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(order)
    db.commit()


def _get_with_items(db: Session, order_id: uuid.UUID) -> Order:
    """Re-fetches an order with its line items attached, for returning in API responses."""
    return db.execute(
        select(Order).options(selectinload(Order.items)).where(Order.id == order_id)
    ).scalar_one()
