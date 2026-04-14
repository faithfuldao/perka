from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StaffLocation(Base):
    """Association table: which staff members can operate at which locations."""

    __tablename__ = "staff_locations"

    staff_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True
    )


class Location(Base):
    """A physical coffee-shop location belonging to a Brand."""

    __tablename__ = "locations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Unique random token embedded in the QR code URL displayed at the counter
    qr_token: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────
    brand: Mapped["Brand"] = relationship("Brand", back_populates="locations")  # noqa: F821
    transactions: Mapped[List["Transaction"]] = relationship(  # noqa: F821
        "Transaction", back_populates="location"
    )
    staff_members: Mapped[List["Staff"]] = relationship(  # noqa: F821
        "Staff",
        secondary="staff_locations",
        back_populates="locations",
    )

    def __repr__(self) -> str:
        return f"<Location name={self.name!r} brand_id={self.brand_id}>"
