from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Path, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.database import get_db
from app.models.staff import Staff, StaffRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/staff/login")


async def get_current_staff(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """
    Decode the Bearer JWT and return the authenticated Staff row.

    Raises HTTP 401 on any token problem and HTTP 403 if the account is inactive.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        staff_id_str: str | None = payload.get("sub")
        if staff_id_str is None:
            raise credentials_exception
        staff_id = uuid.UUID(staff_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(Staff).where(Staff.id == staff_id))
    staff = result.scalar_one_or_none()
    if staff is None:
        raise credentials_exception
    if not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff account is inactive.",
        )
    return staff


def get_current_brand_admin(
    current_staff: Staff = Depends(get_current_staff),
) -> Staff:
    """
    Assert that the authenticated staff member has the ``admin`` role.

    Returns the same Staff object so it can be used as a dependency in routes.
    """
    if current_staff.role != StaffRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required.",
        )
    return current_staff


def get_staff_for_brand(brand_id: uuid.UUID = Path(...)) -> ...:
    """
    Returns a dependency factory that checks the authenticated staff member
    belongs to the brand identified by the ``brand_id`` path parameter.

    Usage::

        @router.get("/{brand_id}/something")
        async def handler(staff: Staff = Depends(get_staff_for_brand)):
            ...
    """
    async def _inner(
        current_staff: Staff = Depends(get_current_staff),
        _brand_id: uuid.UUID = Depends(lambda: brand_id),
    ) -> Staff:
        if current_staff.brand_id != brand_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Staff does not belong to this brand.",
            )
        return current_staff

    return _inner


def require_staff_for_brand(
    brand_id: uuid.UUID = Path(...),
    current_staff: Staff = Depends(get_current_staff),
) -> Staff:
    """
    Inline dependency (no factory) — use directly in route signatures where the
    path already exposes ``brand_id``.
    """
    if current_staff.brand_id != brand_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff does not belong to this brand.",
        )
    return current_staff


def require_admin_for_brand(
    brand_id: uuid.UUID = Path(...),
    current_staff: Staff = Depends(get_current_staff),
) -> Staff:
    """Require admin role AND brand membership."""
    if current_staff.brand_id != brand_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff does not belong to this brand.",
        )
    if current_staff.role != StaffRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required.",
        )
    return current_staff
