from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.database import get_db
from app.schemas.staff import LoginRequest, TokenResponse
from app.services.auth import authenticate_staff

router = APIRouter()


@router.post(
    "/staff/login",
    response_model=TokenResponse,
    summary="Staff login",
    description="Authenticate a staff member and return a Bearer JWT.",
)
async def staff_login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    staff = await authenticate_staff(db, email=body.email, password=body.password)
    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": str(staff.id)})
    return TokenResponse(access_token=token)
