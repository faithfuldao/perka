from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    pass_id: uuid.UUID
    location_id: uuid.UUID
    staff_id: uuid.UUID
    delta: int = Field(..., description="Positive to award, negative to redeem.")
    note: Optional[str] = Field(None, max_length=500)


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pass_id: uuid.UUID
    location_id: Optional[uuid.UUID] = None
    staff_id: Optional[uuid.UUID] = None
    delta: int
    note: Optional[str] = None
    created_at: datetime
