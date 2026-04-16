from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import apple_wallet, auth, brands, enrollment, locations, passes, scan, staff

settings = get_settings()

app = FastAPI(
    title="Perka Loyalty API",
    description="Digital loyalty card platform for coffee shops.",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(brands.router, prefix="/brands", tags=["brands"])
app.include_router(locations.router, prefix="/brands/{brand_id}/locations", tags=["locations"])
app.include_router(staff.router, prefix="/brands/{brand_id}/staff", tags=["staff"])
app.include_router(enrollment.router, prefix="/enroll", tags=["enrollment"])
app.include_router(passes.router, prefix="/passes", tags=["passes"])
app.include_router(apple_wallet.router, prefix="/apple-wallet", tags=["apple-wallet"])
app.include_router(scan.router, prefix="/scan", tags=["scan"])


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
