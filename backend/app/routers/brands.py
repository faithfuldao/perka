from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_brand_admin, get_current_staff
from app.core.security import hash_password
from app.database import get_db
from app.models.brand import Brand
from app.models.staff import Staff, StaffRole
from app.schemas.brand import BrandCreate, BrandRead, BrandUpdate
from app.schemas.staff import StaffCreate, StaffRead

router = APIRouter()


@router.get(
    "/",
    response_model=List[BrandRead],
    summary="List all brands",
)
async def list_brands(
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_staff),  # any authenticated staff
) -> List[Brand]:
    result = await db.execute(select(Brand).order_by(Brand.name))
    return list(result.scalars().all())


@router.post(
    "/",
    response_model=BrandRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a brand",
)
async def create_brand(
    body: BrandCreate,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_brand_admin),
) -> Brand:
    # Check slug uniqueness
    existing = await db.execute(select(Brand).where(Brand.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Brand slug '{body.slug}' already exists.",
        )
    brand = Brand(**body.model_dump())
    db.add(brand)
    await db.flush()
    await db.refresh(brand)
    return brand


@router.get(
    "/{brand_id}",
    response_model=BrandRead,
    summary="Get a brand",
)
async def get_brand(
    brand_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_staff),
) -> Brand:
    brand = await _get_or_404(db, brand_id)
    return brand


@router.patch(
    "/{brand_id}",
    response_model=BrandRead,
    summary="Update a brand (admin only)",
)
async def update_brand(
    brand_id: uuid.UUID,
    body: BrandUpdate,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_brand_admin),
) -> Brand:
    brand = await _get_or_404(db, brand_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(brand, field, value)
    await db.flush()
    await db.refresh(brand)
    return brand


@router.delete(
    "/{brand_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a brand (admin only)",
)
async def delete_brand(
    brand_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: Staff = Depends(get_current_brand_admin),
) -> None:
    brand = await _get_or_404(db, brand_id)
    await db.delete(brand)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(db: AsyncSession, brand_id: uuid.UUID) -> Brand:
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found.")
    return brand
