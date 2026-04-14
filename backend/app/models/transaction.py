from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Transaction(Base):
    """Immutable ledger record: points awarded (+) or redeemed (-) on a Pass."""

    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pass_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("passes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("locations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    staff_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("staff.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Positive = award points, negative = redeem points
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────
    pass_: Mapped["Pass"] = relationship("Pass", back_populates="transactions")  # noqa: F821
    location: Mapped[Optional["Location"]] = relationship(  # noqa: F821
        "Location", back_populates="transactions"
    )
    staff: Mapped[Optional["Staff"]] = relationship(  # noqa: F821
        "Staff", back_populates="transactions"
    )

    def __repr__(self) -> str:
        return f"<Transaction pass_id={self.pass_id} delta={self.delta:+d}>"
