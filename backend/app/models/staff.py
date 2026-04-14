from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import List

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StaffRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"


class Staff(Base):
    """Staff member (barista or brand admin) who belongs to a single Brand."""

    __tablename__ = "staff"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("brands.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[StaffRole] = mapped_column(
        Enum(StaffRole, name="staff_role"), nullable=False, default=StaffRole.staff
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────
    brand: Mapped["Brand"] = relationship("Brand", back_populates="staff_members")  # noqa: F821
    locations: Mapped[List["Location"]] = relationship(  # noqa: F821
        "Location",
        secondary="staff_locations",
        back_populates="staff_members",
    )
    transactions: Mapped[List["Transaction"]] = relationship(  # noqa: F821
        "Transaction", back_populates="staff"
    )

    def __repr__(self) -> str:
        return f"<Staff email={self.email!r} role={self.role}>"
