from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
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
            logger.exception(
                "Apple Wallet rebuild failed for pass %s; points were still awarded.",
                serial_number,
            )
        # Send APNs push to all registered devices (best-effort)
        await _push_apple_pass_update(db, loyalty_pass)

    return AwardPointsResponse(
        serial_number=loyalty_pass.serial_number,
        points_awarded=transaction.delta,
        total_points=loyalty_pass.points,
        reward_earned=reward_earned,
        save_url=save_url,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _push_apple_pass_update(db: AsyncSession, loyalty_pass: Pass) -> None:
    """Send APNs push notifications to all devices registered for this pass."""
    from app.models.apple_device_registration import AppleDeviceRegistration

    settings = get_settings()
    if not settings.APPLE_APNS_KEY_PATH or not settings.APPLE_APNS_KEY_ID:
        return  # APNs not configured, skip

    regs_result = await db.execute(
        select(AppleDeviceRegistration).where(
            AppleDeviceRegistration.pass_serial_number == loyalty_pass.serial_number
        )
    )
    registrations = regs_result.scalars().all()
    if not registrations:
        return

    # Build APNs JWT
    try:
        with open(settings.APPLE_APNS_KEY_PATH, "r") as f:
            apns_key = f.read()
        from jose import jwt as jose_jwt
        import time as _time
        payload = {"iss": settings.APPLE_TEAM_ID, "iat": int(_time.time())}
        headers = {"alg": "ES256", "kid": settings.APPLE_APNS_KEY_ID}
        apns_token = jose_jwt.encode(payload, apns_key, algorithm="ES256", headers=headers)
    except Exception:
        logger.exception("Failed to build APNs JWT; skipping push for pass %s", loyalty_pass.serial_number)
        return

    apns_host = "api.sandbox.push.apple.com" if not settings.is_production else "api.push.apple.com"
    pass_type_id = loyalty_pass.brand.apple_pass_type_id or ""

    async with httpx.AsyncClient(http2=True, timeout=10) as client:
        for reg in registrations:
            try:
                resp = await client.post(
                    f"https://{apns_host}/3/device/{reg.push_token}",
                    json={"aps": {}},
                    headers={
                        "Authorization": f"Bearer {apns_token}",
                        "apns-topic": pass_type_id,
                        "apns-push-type": "background",
                        "apns-priority": "5",
                    },
                )
                if resp.status_code not in (200, 201):
                    logger.warning("APNs push failed for device %s: %s", reg.device_library_identifier, resp.text)
            except Exception:
                logger.exception("APNs push exception for device %s", reg.device_library_identifier)


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
