from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PassBuildContext:
    """
    All brand/pass data required to build a platform-specific pass payload.

    Both Apple and Google builders receive this same context object so the
    router does not need to know about platform-specific fields.
    """
    serial_number: str
    brand_name: str
    brand_slug: str
    logo_url: str | None
    primary_color: str | None       # hex, e.g. "#3B2F2F"
    secondary_color: str | None
    points: int
    reward_threshold: int
    # Apple-specific (may be None if not configured)
    apple_pass_type_id: str | None
    apple_cert_s3_key: str | None
    apple_cert_password_encrypted: str | None
    # Google-specific
    google_issuer_id: str | None


class PassBuilder(ABC):
    """Abstract base for platform wallet pass builders."""

    @abstractmethod
    async def build(self, ctx: PassBuildContext) -> str:
        """
        Build the pass and return a URL (or serialized payload) the client
        can use to add the pass to their wallet.
        """
        ...
