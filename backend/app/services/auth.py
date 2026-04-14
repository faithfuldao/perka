from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.models.staff import Staff


async def authenticate_staff(
    db: AsyncSession,
    email: str,
    password: str,
) -> Staff | None:
    """
    Return the Staff record if credentials are valid, otherwise None.

    We always run ``verify_password`` even when the user is not found to
    prevent timing-based user enumeration.
    """
    result = await db.execute(select(Staff).where(Staff.email == email))
    staff = result.scalar_one_or_none()

    # Verify against a dummy hash when staff not found to maintain constant time.
    _dummy = "$2b$12$KIXmM5j3E5j2E5j2E5j2Eug5VKJ5VKJ5VKJ5VKJ5VKJ5VKJ5VKJ5"
    if staff is None:
        verify_password(password, _dummy)
        return None

    if not verify_password(password, staff.hashed_password):
        return None

    if not staff.is_active:
        return None

    return staff
