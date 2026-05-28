from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.location import Location
from app.models.pass_ import Pass, PassPlatform
from app.models.user import User
from app.schemas.brand import BrandRead
from app.services.passes.apple import AppleWalletService
from app.services.passes.google import GoogleWalletService

logger = logging.getLogger(__name__)

router = APIRouter()


class EnrollmentInfo(BaseModel):
    """Response for GET /enroll/{qr_token} — brand info shown before enrolling."""
    brand: BrandRead
    location_name: str
    apple_add_url: Optional[str] = None
    google_add_url: Optional[str] = None


class EnrollRequest(BaseModel):
    platform: PassPlatform = PassPlatform.google
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None


class EnrollResponse(BaseModel):
    save_url: str


@router.get(
    "/{qr_token}",
    response_model=EnrollmentInfo,
    summary="Get enrollment info for a location's QR token",
)
async def get_enrollment_info(
    qr_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> EnrollmentInfo:
    """
    Called when a customer scans the counter QR code.
    Returns brand branding info and wallet add URLs.
    """
    location = await _get_location_by_token(db, qr_token)
    brand = location.brand

    base = str(request.base_url).rstrip("/")

    return EnrollmentInfo(
        brand=BrandRead.model_validate(brand),
        location_name=location.name,
        apple_add_url=f"{base}/passes/apple/{qr_token}/enroll" if brand.apple_pass_type_id else None,
        google_add_url=f"{base}/passes/google/{qr_token}/enroll" if brand.google_issuer_id else None,
    )


@router.post(
    "/{qr_token}",
    response_model=EnrollResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a customer and get a Save-to-Wallet URL",
)
async def enroll(
    qr_token: str,
    body: EnrollRequest,
    db: AsyncSession = Depends(get_db),
) -> EnrollResponse:
    """
    Create (or retrieve) a User and issue a new loyalty Pass for this brand,
    then return a platform-specific "Save to Wallet" URL.

    If the user already has a pass for this brand + platform combination,
    a fresh save URL is generated for the existing pass.
    """
    location = await _get_location_by_token(db, qr_token)
    brand = location.brand

    if body.platform == PassPlatform.google and not brand.google_issuer_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This brand is not configured for Google Wallet.",
        )

    if body.platform == PassPlatform.apple and not brand.apple_pass_type_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This brand is not configured for Apple Wallet.",
        )

    # Require at least one contact identifier
    if not body.email and not body.phone:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one of email or phone is required.",
        )

    # Find or create the User
    user = await _find_or_create_user(db, email=body.email, phone=body.phone)

    # Check for an existing pass to avoid duplicate enrollment
    existing_result = await db.execute(
        select(Pass).where(
            Pass.user_id == user.id,
            Pass.brand_id == brand.id,
            Pass.platform == body.platform,
        )
    )
    existing_pass = existing_result.scalar_one_or_none()

    if existing_pass:
        if body.platform == PassPlatform.google:
            svc = GoogleWalletService(brand)
            save_url = svc.build_save_url(existing_pass)
        else:
            svc = AppleWalletService(brand)
            save_url = await svc.create_pass(existing_pass, user)
        return EnrollResponse(save_url=save_url)

    # Create a new Pass record
    new_pass = Pass(
        user_id=user.id,
        brand_id=brand.id,
        platform=body.platform,
        points=0,
    )
    db.add(new_pass)
    await db.flush()
    await db.refresh(new_pass)

    # Create the wallet object and get the save URL
    if body.platform == PassPlatform.google:
        svc = GoogleWalletService(brand)
        save_url = await svc.create_pass(new_pass, user)
        # Persist the Google object ID so we can PATCH it later
        new_pass.platform_pass_id = svc.object_id(new_pass)
        await db.flush()
    else:
        svc = AppleWalletService(brand)
        save_url = await svc.create_pass(new_pass, user)

    return EnrollResponse(save_url=save_url)


@router.get(
    "/{qr_token}/apple",
    summary="Scan QR → direct Apple Wallet pass (no form required)",
    response_class=Response,
    responses={200: {"content": {"application/vnd.apple.pkpass": {}}}},
)
async def direct_apple_enrollment(
    qr_token: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Called when a customer scans the counter QR code on iPhone.
    Creates an anonymous pass and returns the .pkpass file directly.
    iOS detects application/vnd.apple.pkpass and adds it to Wallet automatically.
    """
    location = await _get_location_by_token(db, qr_token)
    brand = location.brand

    if not brand.apple_pass_type_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This brand is not configured for Apple Wallet.",
        )

    user = User(phone=f"anon_{uuid.uuid4().hex[:12]}")
    db.add(user)
    await db.flush()
    await db.refresh(user)

    new_pass = Pass(
        user_id=user.id,
        brand_id=brand.id,
        platform=PassPlatform.apple,
        points=0,
    )
    db.add(new_pass)
    await db.flush()
    await db.refresh(new_pass)
    await db.refresh(new_pass, ["brand"])

    svc = AppleWalletService(brand)
    pkpass_bytes = svc.build_pkpass_bytes(new_pass, user)

    return Response(
        content=pkpass_bytes,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f"attachment; filename={new_pass.serial_number}.pkpass"},
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_location_by_token(db: AsyncSession, qr_token: str) -> Location:
    result = await db.execute(
        select(Location).where(Location.qr_token == qr_token)
    )
    location = result.scalar_one_or_none()
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid QR token.",
        )
    await db.refresh(location, ["brand"])
    return location


async def _find_or_create_user(
    db: AsyncSession,
    email: Optional[str],
    phone: Optional[str],
) -> User:
    """
    Look up a User by email or phone. Create one if not found.
    If both are provided, email takes precedence for the lookup.
    """
    if email:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user:
            return user

    if phone:
        result = await db.execute(select(User).where(User.phone == phone))
        user = result.scalar_one_or_none()
        if user:
            return user

    user = User(email=email, phone=phone)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

