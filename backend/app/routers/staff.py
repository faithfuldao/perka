from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin_for_brand
from app.core.security import hash_password
from app.database import get_db
from app.models.staff import Staff
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


# ── Helpers ───────────────────────────────────────────────────────────────────

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
