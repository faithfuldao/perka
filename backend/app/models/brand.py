from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Integer, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Brand(Base):
    """Tenant entity. Each coffee-shop brand is a tenant."""

    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)   # e.g. "#3B2F2F"
    secondary_color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    points_per_visit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reward_threshold: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    # Apple Wallet integration (nullable until configured)
    apple_pass_type_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    apple_cert_s3_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    apple_cert_password_encrypted: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Google Wallet integration
    google_issuer_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # The class name portion of the class ID, e.g. "Unusual_Loyalty"
    google_wallet_class_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Service account JSON stored as a dict (overrides the file-path fallback)
    google_service_account_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

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
    locations: Mapped[List["Location"]] = relationship(  # noqa: F821
        "Location", back_populates="brand", cascade="all, delete-orphan"
    )
    staff_members: Mapped[List["Staff"]] = relationship(  # noqa: F821
        "Staff", back_populates="brand", cascade="all, delete-orphan"
    )
    passes: Mapped[List["Pass"]] = relationship(  # noqa: F821
        "Pass", back_populates="brand", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Brand slug={self.slug!r}>"
