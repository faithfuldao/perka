#!/usr/bin/env python3
"""
Bootstrap script — creates the first Brand, admin Staff, and Location.

Run from the backend/ directory:
  python seed.py
  python seed.py "Shodai Coffee" shodai admin@shodai.com mypassword "Shodai Shibuya"

Positional args (all optional, defaults shown):
  brand_name      "My Coffee Shop"
  brand_slug      "my-coffee-shop"
  admin_email     "admin@example.com"
  admin_password  "changeme123"
  location_name   "Main Location"
"""
from __future__ import annotations

import asyncio
import sys


async def main(
    brand_name: str = "My Coffee Shop",
    brand_slug: str = "my-coffee-shop",
    admin_email: str = "admin@example.com",
    admin_password: str = "changeme123",
    location_name: str = "Main Location",
) -> None:
    import app.models  # noqa: F401 — registers all mapped classes
    from app.config import get_settings
    from app.core.security import hash_password
    from app.database import AsyncSessionLocal
    from app.models.brand import Brand
    from app.models.location import Location
    from app.models.staff import Staff, StaffRole

    settings = get_settings()

    async with AsyncSessionLocal() as session:
        async with session.begin():
            brand = Brand(name=brand_name, slug=brand_slug)
            session.add(brand)
            await session.flush()
            await session.refresh(brand)

            admin = Staff(
                brand_id=brand.id,
                email=admin_email,
                hashed_password=hash_password(admin_password),
                role=StaffRole.admin,
                is_active=True,
            )
            session.add(admin)

            location = Location(brand_id=brand.id, name=location_name)
            session.add(location)
            await session.flush()
            await session.refresh(location)

    enroll_url = f"{settings.API_BASE_URL.rstrip('/')}/enroll/{location.qr_token}"

    print(f"\nBrand    : {brand.name!r}  (id={brand.id}  slug={brand.slug!r})")
    print(f"Admin    : {admin.email!r}  password={admin_password!r}")
    print(f"Location : {location.name!r}  (id={location.id})")
    print(f"QR token : {location.qr_token}")
    print(f"Enroll   : {enroll_url}")
    print("\nLogin via  POST /auth/staff/login  with the credentials above.")


if __name__ == "__main__":
    args = sys.argv[1:]
    asyncio.run(main(*args))
