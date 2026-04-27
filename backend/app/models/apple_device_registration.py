from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppleDeviceRegistration(Base):
    """Stores APNs push tokens for registered Apple Wallet devices."""

    __tablename__ = "apple_device_registrations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    device_library_identifier: Mapped[str] = mapped_column(String(200), nullable=False)
    push_token: Mapped[str] = mapped_column(String(200), nullable=False)
    pass_serial_number: Mapped[str] = mapped_column(
        String(36), ForeignKey("passes.serial_number", ondelete="CASCADE"), nullable=False
    )
    pass_type_identifier: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "device_library_identifier", "pass_serial_number", name="uq_device_pass"
        ),
    )
