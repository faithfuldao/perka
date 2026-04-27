from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deps import require_admin_for_brand
from app.core.security import hash_password
from app.database import get_db
from app.models.location import Location
from app.models.staff import Staff
from app.schemas.location import LocationRead
from app.schemas.staff import StaffCreate, StaffRead

router = APIRouter()


@router.get(
    "/",
    response_model=List[StaffRead],
    summary="List staff for a brand (admin only)",
)
async def list_staff(
    brand_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin_for_brand),
) -> List[Staff]:
    result = await db.execute(
        select(Staff).where(Staff.brand_id == brand_id).order_by(Staff.email)
    )
    return list(result.scalars().all())


@router.post(
    "/",
    response_model=StaffRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a staff member (admin only)",
)
async def create_staff(
    brand_id: uuid.UUID,
    body: StaffCreate,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin_for_brand),
) -> Staff:
    # Ensure email is globally unique
    existing = await db.execute(select(Staff).where(Staff.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{body.email}' is already registered.",
        )
    member = Staff(
        brand_id=brand_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


@router.get(
    "/{staff_id}",
    response_model=StaffRead,
    summary="Get a staff member (admin only)",
)
async def get_staff_member(
    brand_id: uuid.UUID,
    staff_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin_for_brand),
) -> Staff:
    return await _get_or_404(db, brand_id, staff_id)


@router.delete(
    "/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a staff member (admin only)",
)
async def delete_staff_member(
    brand_id: uuid.UUID,
    staff_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_staff: Staff = Depends(require_admin_for_brand),
) -> None:
    member = await _get_or_404(db, brand_id, staff_id)
    if member.id == current_staff.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account.",
        )
    await db.delete(member)


@router.put(
    "/{staff_id}/locations",
    response_model=List[LocationRead],
    summary="Set locations for a staff member (admin only)",
)
async def set_staff_locations(
    brand_id: uuid.UUID,
    staff_id: uuid.UUID,
    body: _LocationIds,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin_for_brand),
) -> List[Location]:
    member = await db.execute(
        select(Staff)
        .where(Staff.id == staff_id, Staff.brand_id == brand_id)
        .options(selectinload(Staff.locations))
    )
    staff = member.scalar_one_or_none()
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff member not found.")

    locs_result = await db.execute(
        select(Location).where(
            Location.id.in_(body.location_ids),
            Location.brand_id == brand_id,
        )
    )
    locations = list(locs_result.scalars().all())
    if len(locations) != len(body.location_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more location IDs are invalid or do not belong to this brand.",
        )
    staff.locations = locations
    await db.flush()
    return locations


# ── Helpers ───────────────────────────────────────────────────────────────────


class _LocationIds(BaseModel):
    location_ids: List[uuid.UUID]

async def _get_or_404(
    db: AsyncSession, brand_id: uuid.UUID, staff_id: uuid.UUID
) -> Staff:
    result = await db.execute(
        select(Staff).where(
            Staff.id == staff_id,
            Staff.brand_id == brand_id,
        )
    )
    member = result.scalar_one_or_none()
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found.",
        )
    return member
