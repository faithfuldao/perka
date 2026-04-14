from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_staff
from app.database import get_db
from app.models.pass_ import Pass, PassPlatform
from app.models.staff import Staff
from app.schemas.pass_ import AwardPointsRequest, AwardPointsResponse, PassRead
from app.services.passes.apple import AppleWalletService
from app.services.passes.google import GoogleWalletService
from app.services.points import award_points

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{serial_number}",
    response_model=PassRead,
    summary="Get loyalty pass info by serial number",
)
async def get_pass(
    serial_number: str,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
) -> Pass:
    """
    Return the loyalty pass identified by *serial_number*.

    Staff can only view passes that belong to their brand.
    """
    loyalty_pass = await _get_pass_or_404(db, serial_number)

    if loyalty_pass.brand_id != current_staff.brand_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pass does not belong to your brand.",
        )
    return loyalty_pass


@router.post(
    "/{serial_number}/award",
    response_model=AwardPointsResponse,
    summary="Award points to a loyalty pass",
)
async def award_visit_points(
    serial_number: str,
    body: AwardPointsRequest,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(get_current_staff),
) -> AwardPointsResponse:
    """
    Scan a customer's pass QR code and award points for a visit.

    The number of points awarded equals ``brand.points_per_visit``.
    If the resulting total meets or exceeds ``brand.reward_threshold``,
    ``reward_earned`` is set to ``true`` in the response.

    For Google Wallet passes the loyalty object is PATCHed on Google's side
    so the customer sees the updated balance without re-adding the pass.
    The PATCH is best-effort: a failure is logged but does not roll back the
    database transaction.

    The staff member must belong to the same brand as the pass.
    """
    loyalty_pass, transaction = await award_points(
        db,
        serial_number=serial_number,
        location_id=body.location_id,
        staff=current_staff,
    )

    # Reload brand and user to read credentials and rebuild Apple pass.json
    await db.refresh(loyalty_pass, ["brand", "user"])
    reward_earned = loyalty_pass.points >= loyalty_pass.brand.reward_threshold

    save_url: str | None = None

    if loyalty_pass.platform == PassPlatform.google:
        try:
            svc = GoogleWalletService(loyalty_pass.brand)
            await svc.update_pass_points(loyalty_pass)
            save_url = svc.build_save_url(loyalty_pass)
        except Exception:
            # Log but do not fail the request — points are already committed.
            logger.exception(
                "Google Wallet PATCH failed for pass %s; points were still awarded.",
                serial_number,
            )

    elif loyalty_pass.platform == PassPlatform.apple:
        try:
            svc = AppleWalletService(loyalty_pass.brand)
            await svc.update_pass_points(loyalty_pass, loyalty_pass.user)
        except Exception:
            # Best-effort: points are committed; pass will sync on next open.
            logger.exception(
                "Apple Wallet rebuild failed for pass %s; points were still awarded.",
                serial_number,
            )

    return AwardPointsResponse(
        serial_number=loyalty_pass.serial_number,
        points_awarded=transaction.delta,
        total_points=loyalty_pass.points,
        reward_earned=reward_earned,
        save_url=save_url,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_pass_or_404(db: AsyncSession, serial_number: str) -> Pass:
    result = await db.execute(
        select(Pass).where(Pass.serial_number == serial_number)
    )
    loyalty_pass = result.scalar_one_or_none()
    if loyalty_pass is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pass not found.",
        )
    return loyalty_pass
