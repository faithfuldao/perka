#!/usr/bin/env python3
"""
Import a brand from pass_brands.json into the database.

Usage (from backend/ directory):
  python import_brand.py shodai
  python import_brand.py unusual
  python import_brand.py shodai1

Creates the Brand, one admin Staff, and one Location.
Prints credentials + enrollment URL at the end.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


async def main(brand_key: str) -> None:
    brands_file = Path(__file__).parent.parent / "pass_brands.json"
    data = json.loads(brands_file.read_text(encoding="utf-8"))

    if brand_key not in data:
        print(f"Brand '{brand_key}' not found in pass_brands.json.")
        print(f"Available: {', '.join(data.keys())}")
        sys.exit(1)

    cfg = data[brand_key]
    g = cfg["google"]

    import app.models  # noqa: F401
    from app.config import get_settings
    from app.core.security import hash_password
    from app.database import AsyncSessionLocal
    from app.models.brand import Brand
    from app.models.location import Location
    from app.models.staff import Staff, StaffRole
    from sqlalchemy import select

    settings = get_settings()
    admin_email = f"admin@{brand_key}.perka"
    admin_password = "changeme123"

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Check if brand already exists
            existing = await session.execute(
                select(Brand).where(Brand.slug == brand_key)
            )
            brand = existing.scalar_one_or_none()

            if brand:
                print(f"Brand '{brand_key}' already exists — updating Google config.")
                brand.google_issuer_id = g["issuer_id"]
                brand.google_wallet_class_id = g["class_suffix"]
                brand.logo_url = cfg.get("logo_url")
                brand.primary_color = cfg.get("primary_color")
                brand.google_hero_image_url = cfg.get("hero_url")
                brand.google_stamp_image_url = cfg.get("stamp_image_url")
                brand.google_card_title = cfg["name"]
                brand.reward_threshold = cfg.get("reward_threshold", 10)
                await session.flush()
                await session.refresh(brand)
            else:
                brand = Brand(
                    slug=brand_key,
                    name=cfg["name"],
                    primary_color=cfg.get("primary_color"),
                    secondary_color=cfg.get("secondary_color"),
                    logo_url=cfg.get("logo_url"),
                    reward_threshold=cfg.get("reward_threshold", 10),
                    google_issuer_id=g["issuer_id"],
                    google_wallet_class_id=g["class_suffix"],
                    google_hero_image_url=cfg.get("hero_url"),
                    google_stamp_image_url=cfg.get("stamp_image_url"),
                    google_card_title=cfg["name"],
                )
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

                location = Location(brand_id=brand.id, name=f"{cfg['name']} - Main")
                session.add(location)
                await session.flush()
                await session.refresh(location)

    # Re-fetch location for qr_token (may have been created above)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Location).where(Location.brand_id == brand.id)
        )
        location = result.scalars().first()

    enroll_url = f"{settings.API_BASE_URL.rstrip('/')}/enroll/{location.qr_token}"

    print(f"\nBrand    : {brand.name!r}  (id={brand.id}  slug={brand.slug!r})")
    print(f"Issuer ID: {brand.google_issuer_id}")
    print(f"Class ID : {brand.google_wallet_class_id}")
    print(f"Admin    : {admin_email!r}  password={admin_password!r}")
    print(f"Location : {location.name!r}  (qr_token={location.qr_token})")
    print(f"Enroll   : {enroll_url}")
    print("\nNext step: POST /enroll/{qr_token} with your email to get the Google Wallet save URL.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_brand.py <brand_key>")
        print("       e.g.: python import_brand.py shodai")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
