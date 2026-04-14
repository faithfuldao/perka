from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """End-consumer who holds loyalty passes."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # At least one of email or phone must be provided at application level.
    email: Mapped[Optional[str]] = mapped_column(
        String(254), unique=True, nullable=True, index=True
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(30), unique=True, nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────
    passes: Mapped[List["Pass"]] = relationship(  # noqa: F821
        "Pass", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User email={self.email!r} phone={self.phone!r}>"
