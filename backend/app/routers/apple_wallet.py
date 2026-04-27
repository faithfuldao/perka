from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.apple_device_registration import AppleDeviceRegistration
from app.models.pass_ import Pass, PassPlatform

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Helper: verify ApplePass token ───────────────────────────────────────────

async def _verify_pass_token(
    serial_number: str, request: Request, db: AsyncSession
) -> Pass:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("ApplePass "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    token = auth[len("ApplePass "):]
    result = await db.execute(
        select(Pass).where(
            Pass.serial_number == serial_number,
            Pass.authentication_token == token,
        )
    )
    pass_obj = result.scalar_one_or_none()
    if pass_obj is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return pass_obj


# ── Apple Wallet Web Service endpoints ───────────────────────────────────────

@router.post(
    "/v1/devices/{device_library_identifier}/registrations/{pass_type_identifier}/{serial_number}",
    summary="Register device for pass updates (Apple Wallet web service)",
)
async def register_device(
    device_library_identifier: str,
    pass_type_identifier: str,
    serial_number: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    pass_obj = await _verify_pass_token(serial_number, request, db)

    body = await request.json()
    push_token: str = body.get("pushToken", "")
    if not push_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="pushToken required")

    existing_result = await db.execute(
        select(AppleDeviceRegistration).where(
            AppleDeviceRegistration.device_library_identifier == device_library_identifier,
            AppleDeviceRegistration.pass_serial_number == serial_number,
        )
    )
    reg = existing_result.scalar_one_or_none()

    if reg is None:
        db.add(AppleDeviceRegistration(
            device_library_identifier=device_library_identifier,
            push_token=push_token,
            pass_serial_number=serial_number,
            pass_type_identifier=pass_type_identifier,
        ))
        await db.flush()
        return Response(status_code=status.HTTP_201_CREATED)
    else:
        reg.push_token = push_token
        return Response(status_code=status.HTTP_200_OK)


@router.delete(
    "/v1/devices/{device_library_identifier}/registrations/{pass_type_identifier}/{serial_number}",
    summary="Unregister device for pass updates (Apple Wallet web service)",
)
async def unregister_device(
    device_library_identifier: str,
    pass_type_identifier: str,
    serial_number: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    await _verify_pass_token(serial_number, request, db)

    result = await db.execute(
        select(AppleDeviceRegistration).where(
            AppleDeviceRegistration.device_library_identifier == device_library_identifier,
            AppleDeviceRegistration.pass_serial_number == serial_number,
        )
    )
    reg = result.scalar_one_or_none()
    if reg:
        await db.delete(reg)
    return Response(status_code=status.HTTP_200_OK)


@router.get(
    "/v1/devices/{device_library_identifier}/registrations/{pass_type_identifier}",
    summary="Get updatable passes for device (Apple Wallet web service)",
)
async def get_updatable_passes(
    device_library_identifier: str,
    pass_type_identifier: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    passes_updated_since: str | None = request.query_params.get("passesUpdatedSince")

    regs_result = await db.execute(
        select(AppleDeviceRegistration).where(
            AppleDeviceRegistration.device_library_identifier == device_library_identifier,
            AppleDeviceRegistration.pass_type_identifier == pass_type_identifier,
        )
    )
    regs = regs_result.scalars().all()
    if not regs:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    serial_numbers = [r.pass_serial_number for r in regs]

    query = select(Pass).where(Pass.serial_number.in_(serial_numbers))
    if passes_updated_since:
        try:
            since_dt = datetime.fromisoformat(passes_updated_since)
            query = query.where(Pass.updated_at > since_dt)
        except ValueError:
            pass

    passes_result = await db.execute(query)
    updated_passes = passes_result.scalars().all()

    if not updated_passes:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    now_iso = datetime.now(timezone.utc).isoformat()
    return JSONResponse({
        "lastUpdated": now_iso,
        "serialNumbers": [p.serial_number for p in updated_passes],
    })


@router.get(
    "/v1/passes/{pass_type_identifier}/{serial_number}",
    summary="Get latest pass version (Apple Wallet web service)",
    response_class=Response,
)
async def get_latest_pass(
    pass_type_identifier: str,
    serial_number: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    pass_obj = await _verify_pass_token(serial_number, request, db)
    await db.refresh(pass_obj, ["brand", "user"])
    return await _build_pkpass_response(pass_obj, db, serial_number)


# ── Original download endpoint ────────────────────────────────────────────────

@router.get(
    "/passes/{serial_number}",
    summary="Download an Apple Wallet .pkpass file",
    response_class=Response,
)
async def download_pkpass(
    serial_number: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
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
    return await _build_pkpass_response(pass_obj, db, serial_number)


# ── Shared helper ─────────────────────────────────────────────────────────────

async def _build_pkpass_response(pass_obj: Pass, db: AsyncSession, serial_number: str) -> Response:
    from app.services.passes.apple import AppleWalletService

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
