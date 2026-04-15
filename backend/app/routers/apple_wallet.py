from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.pass_ import Pass, PassPlatform
from app.services.passes.apple import AppleWalletService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/passes/{serial_number}",
    summary="Download an Apple Wallet .pkpass file",
    response_class=Response,
)
async def download_pkpass(
    serial_number: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Build and stream the .pkpass bundle for the given serial number.

    iOS opens this URL and automatically adds the pass to Wallet when it
    receives a response with Content-Type: application/vnd.apple.pkpass.
    """
    result = await db.execute(
        select(Pass).where(
            Pass.serial_number == serial_number,
            Pass.platform == PassPlatform.apple,
        )
    )
    pass_obj = result.scalar_one_or_none()
    if pass_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pass not found.")

    await db.refresh(pass_obj, ["brand", "user"])

    icon_bytes: bytes | None = None
    strip_bytes: bytes | None = None

    async with httpx.AsyncClient(timeout=5) as client:
        logo_url = pass_obj.brand.logo_url
        if logo_url:
            try:
                r = await client.get(logo_url)
                if r.status_code == 200:
                    icon_bytes = r.content
            except Exception:
                logger.warning("Could not fetch brand logo from %s", logo_url)

        hero_url = pass_obj.brand.google_hero_image_url
        if hero_url:
            try:
                r = await client.get(hero_url)
                if r.status_code == 200:
                    strip_bytes = r.content
            except Exception:
                logger.warning("Could not fetch hero image from %s", hero_url)

    svc = AppleWalletService(pass_obj.brand)
    pkpass_bytes = svc.build_pkpass_bytes(
        pass_obj, pass_obj.user, icon_bytes=icon_bytes, strip_bytes=strip_bytes
    )

    return Response(
        content=pkpass_bytes,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f'attachment; filename="{serial_number}.pkpass"'},
    )
