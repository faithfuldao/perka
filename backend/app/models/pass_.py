from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PassPlatform(str, enum.Enum):
    apple = "apple"
    google = "google"


class Pass(Base):
    """A digital loyalty pass held by a User for a specific Brand."""

    __tablename__ = "passes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[PassPlatform] = mapped_column(
        Enum(PassPlatform, name="pass_platform"), nullable=False
    )
    # External ID returned by Apple/Google after pass creation
    platform_pass_id: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Unique UUID embedded in the QR code printed on the pass itself
    serial_number: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────
    user: Mapped["User"] = relationship("User", back_populates="passes")  # noqa: F821
    brand: Mapped["Brand"] = relationship("Brand", back_populates="passes")  # noqa: F821
    transactions: Mapped[List["Transaction"]] = relationship(  # noqa: F821
        "Transaction", back_populates="pass_"
    )

    def __repr__(self) -> str:
        return f"<Pass serial={self.serial_number!r} points={self.points}>"
