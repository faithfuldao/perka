from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin_for_brand, require_staff_for_brand
from app.database import get_db
from app.models.location import Location
from app.models.staff import Staff
from app.schemas.location import LocationCreate, LocationRead, LocationUpdate

router = APIRouter()


@router.get(
    "/",
    response_model=List[LocationRead],
    summary="List locations for a brand",
)
async def list_locations(
    brand_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_staff_for_brand),
) -> List[Location]:
    result = await db.execute(
        select(Location).where(Location.brand_id == brand_id).order_by(Location.name)
    )
    return list(result.scalars().all())


@router.post(
    "/",
    response_model=LocationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a location (admin only)",
)
async def create_location(
    brand_id: uuid.UUID,
    body: LocationCreate,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin_for_brand),
) -> Location:
    location = Location(brand_id=brand_id, **body.model_dump())
    db.add(location)
    await db.flush()
    await db.refresh(location)
    return location


@router.get(
    "/{location_id}",
    response_model=LocationRead,
    summary="Get a location",
)
async def get_location(
    brand_id: uuid.UUID,
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_staff_for_brand),
) -> Location:
    return await _get_or_404(db, brand_id, location_id)


@router.patch(
    "/{location_id}",
    response_model=LocationRead,
    summary="Update a location (admin only)",
)
async def update_location(
    brand_id: uuid.UUID,
    location_id: uuid.UUID,
    body: LocationUpdate,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin_for_brand),
) -> Location:
    location = await _get_or_404(db, brand_id, location_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(location, field, value)
    await db.flush()
    await db.refresh(location)
    return location


@router.delete(
    "/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a location (admin only)",
)
async def delete_location(
    brand_id: uuid.UUID,
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin_for_brand),
) -> None:
    location = await _get_or_404(db, brand_id, location_id)
    await db.delete(location)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(
    db: AsyncSession, brand_id: uuid.UUID, location_id: uuid.UUID
) -> Location:
    result = await db.execute(
        select(Location).where(
            Location.id == location_id,
            Location.brand_id == brand_id,
        )
    )
    location = result.scalar_one_or_none()
    if location is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found.",
        )
    return location
