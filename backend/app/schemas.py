# The "shape" of data coming in and out of the API — separate from the
# database models in models.py. Splitting these apart means the API can
# validate/reject bad input (e.g. a missing email) and hide internal-only
# database fields, without that logic leaking into the database layer.
# "...In" classes are what the admin dashboard sends when creating/editing
# something; "...Out" classes are what the API sends back to any caller.

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# ── auth ──


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── lookup tables (read-only via the API; managed directly in Supabase) ──


class ProductCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class ServiceTypeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


# ── products ──


class ProductIn(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = None
    price: Decimal | None = None
    currency: str = "GHS"
    image_url: str
    look_number: int | None = None
    category_id: int
    is_purchasable: bool = True
    is_featured: bool = False
    stock_status: str = "made_to_order"
    display_order: int = 0


class ProductOut(ProductIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    category_slug: str | None = None
    category_name: str | None = None


# ── orders ──


class OrderItemIn(BaseModel):
    product_id: uuid.UUID | None = None
    quantity: int = Field(default=1, gt=0)
    notes: str | None = None


class OrderCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=30)
    delivery_notes: str | None = None
    items: list[OrderItemIn] = Field(min_length=1)
    website: str | None = None  # honeypot — real visitors never see or fill this field


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID | None
    product_title_snapshot: str
    quantity: int
    price_at_order: Decimal | None
    notes: str | None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    phone: str
    delivery_notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut] = []


class OrderStatusUpdate(BaseModel):
    status: str


# ── consultations ──


class ConsultationCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=30)
    service_type_id: int | None = None
    preferred_date: date | None = None
    design_requirements: str | None = None
    website: str | None = None  # honeypot — real visitors never see or fill this field


class ConsultationStatusUpdate(BaseModel):
    status: str


class ConsultationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    phone: str
    service_type_id: int | None
    preferred_date: date | None
    design_requirements: str | None
    status: str
    created_at: datetime
    updated_at: datetime


# ── hero media ──


class HeroMediaIn(BaseModel):
    media_type: str
    media_url: str
    sort_order: int = 0
    is_active: bool = True


class HeroMediaOut(HeroMediaIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ── site settings ──


class SiteSettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: str | None
    updated_at: datetime


class SiteSettingUpdate(BaseModel):
    value: str | None = None


# ── uploads ──


class UploadResponse(BaseModel):
    url: str
