# The database tables, one Python class per table (SQLAlchemy ORM models).
# Each class here mirrors a table that already exists in Supabase Postgres —
# these classes don't create the tables, they just describe their shape so
# the rest of the backend can read/write rows as normal Python objects
# instead of writing raw SQL everywhere.

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ProductCategory(Base):
    """A shop category, e.g. "Fashion", "Hair", "Bridal". Seeded directly in
    Supabase — there's no admin UI to add/edit categories, only to assign
    products to one."""

    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    slug: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ServiceType(Base):
    """A consultation/booking service, e.g. "Custom Fitting", "Hair
    Styling" — shown as options on the site's booking form."""

    __tablename__ = "service_types"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Product(Base):
    """One item in the shop — a garment, hair piece, or featured customer
    photo. `image_url` points at the (already-watermarked) file in Supabase
    Storage. `is_featured` items are the "customer already received this"
    showcase photos; `is_purchasable` controls whether an order button shows."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="GHS")
    image_url: Mapped[str] = mapped_column(Text)
    look_number: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    category_id: Mapped[int] = mapped_column(SmallInteger, ForeignKey("product_categories.id"))
    is_purchasable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_status: Mapped[str] = mapped_column(String(20), default="made_to_order")
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    """A customer order request submitted from the site's order form. This
    is a request to be contacted/paid offline, not a live payment — there's
    no payment processor wired up yet."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(30))
    delivery_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """One line item within an Order. `product_title_snapshot` and
    `price_at_order` freeze the product's title/price at the moment of
    ordering, so editing or even deleting the product later doesn't change
    what a past order says was bought."""

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    order_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"))
    order: Mapped["Order"] = relationship(back_populates="items")
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    product_title_snapshot: Mapped[str] = mapped_column(String(150))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    price_at_order: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ConsultationRequest(Base):
    """A booking/consultation request submitted from the site's booking form
    (separate from a product Order — this is for "come measure/style me",
    not "sell me this specific item")."""

    __tablename__ = "consultation_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(30))
    service_type_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("service_types.id"), nullable=True)
    preferred_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    design_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HeroMedia(Base):
    """A photo or video shown in the site's rotating hero banner up top.
    `media_type` is "photo" or "video"; `sort_order` controls the sequence;
    `is_active` lets the admin hide an item without deleting it."""

    __tablename__ = "hero_media"

    id: Mapped[int] = mapped_column(primary_key=True)
    media_type: Mapped[str] = mapped_column(String(10))
    media_url: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SiteSetting(Base):
    """A simple key/value store for small bits of editable site copy or
    stats (e.g. "years_experience": "8") that the admin can tweak without
    a developer touching the code."""

    __tablename__ = "site_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
