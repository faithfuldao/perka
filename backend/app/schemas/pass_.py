from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.pass_ import PassPlatform


class PassCreate(BaseModel):
    user_id: uuid.UUID
    brand_id: uuid.UUID
    platform: PassPlatform


class PassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    brand_id: uuid.UUID
    platform: PassPlatform
    platform_pass_id: Optional[str] = None
    points: int
    serial_number: str
    created_at: datetime
    updated_at: datetime


class AwardPointsRequest(BaseModel):
    """Body sent by a staff member when scanning a customer's pass QR."""
    location_id: uuid.UUID
    note: Optional[str] = None


class AwardPointsResponse(BaseModel):
    serial_number: str
    points_awarded: int
    total_points: int
    reward_earned: bool
    # Set when the pass is a Google Wallet pass and the update succeeded.
    # None for Apple passes or if the wallet push was skipped.
    save_url: Optional[str] = None


class RedeemRequest(BaseModel):
    location_id: uuid.UUID
    note: Optional[str] = None


class RedeemResponse(BaseModel):
    serial_number: str
    points_deducted: int
    total_points: int
