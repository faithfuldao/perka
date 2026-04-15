from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BrandBase(BaseModel):
    slug: str = Field(..., min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    name: str = Field(..., min_length=1, max_length=200)
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    points_per_visit: int = Field(default=1, ge=1)
    reward_threshold: int = Field(default=10, ge=1)
    apple_pass_type_id: Optional[str] = None
    google_issuer_id: Optional[str] = None
    google_hero_image_url: Optional[str] = None


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    """All fields optional for partial updates."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    points_per_visit: Optional[int] = Field(None, ge=1)
    reward_threshold: Optional[int] = Field(None, ge=1)
    apple_pass_type_id: Optional[str] = None
    google_issuer_id: Optional[str] = None
    google_hero_image_url: Optional[str] = None


class BrandRead(BrandBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
