from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=30)

    @model_validator(mode="after")
    def require_email_or_phone(self) -> "UserCreate":
        if not self.email and not self.phone:
            raise ValueError("At least one of email or phone is required.")
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime
