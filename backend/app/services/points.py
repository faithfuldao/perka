from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pass_ import Pass
from app.models.staff import Staff
from app.models.transaction import Transaction


async def award_points(
    db: AsyncSession,
    *,
    serial_number: str,
    location_id: uuid.UUID,
    staff: Staff,
) -> tuple[Pass, Transaction]:
    """
    Award ``brand.points_per_visit`` points to the pass identified by
    *serial_number* and record a Transaction.

    Returns the updated Pass and the new Transaction.
    Raises HTTP 404 if the pass does not exist.
    Raises HTTP 403 if the staff member's brand does not match the pass's brand.
    """
    result = await db.execute(
        select(Pass).where(Pass.serial_number == serial_number)
    )
    loyalty_pass = result.scalar_one_or_none()
    if loyalty_pass is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pass not found.",
        )
    if loyalty_pass.brand_id != staff.brand_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pass does not belong to your brand.",
        )

    # Load the brand to read points_per_visit
    await db.refresh(loyalty_pass, ["brand"])
    delta = loyalty_pass.brand.points_per_visit

    loyalty_pass.points += delta

    transaction = Transaction(
        pass_id=loyalty_pass.id,
        location_id=location_id,
        staff_id=staff.id,
        delta=delta,
        note="Visit award",
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(loyalty_pass)
    return loyalty_pass, transaction


async def redeem_reward(
    db: AsyncSession,
    *,
    serial_number: str,
    staff: Staff,
    location_id: uuid.UUID,
    note: str | None = None,
) -> tuple[Pass, Transaction]:
    """
    Deduct ``brand.reward_threshold`` points from the pass when a reward
    is redeemed.

    Raises HTTP 400 if the pass does not have enough points.
    """
    result = await db.execute(
        select(Pass).where(Pass.serial_number == serial_number)
    )
    loyalty_pass = result.scalar_one_or_none()
    if loyalty_pass is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pass not found.",
        )
    if loyalty_pass.brand_id != staff.brand_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pass does not belong to your brand.",
        )

    await db.refresh(loyalty_pass, ["brand"])
    threshold = loyalty_pass.brand.reward_threshold

    if loyalty_pass.points < threshold:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough points. Need {threshold}, have {loyalty_pass.points}.",
        )

    delta = -threshold
    loyalty_pass.points += delta

    transaction = Transaction(
        pass_id=loyalty_pass.id,
        location_id=location_id,
        staff_id=staff.id,
        delta=delta,
        note=note or "Reward redeemed",
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(loyalty_pass)
    return loyalty_pass, transaction
