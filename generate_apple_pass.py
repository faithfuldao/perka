"""
Generate a test Apple Wallet .pkpass for any brand configured in pass_brands.json.

Usage:
    python generate_apple_pass.py --brand unusual
    python generate_apple_pass.py --brand newshop

Add new brands by editing pass_brands.json — no Python changes needed.

Requires per brand:
  - A .p12 signing cert (path set in pass_brands.json under "cert_p12_path")
  - backend/AppleWWDRCAG4.cer  (shared Apple intermediate cert)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid

# Allow importing the backend app without installing it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# Point pydantic-settings at the backend .env file
os.environ.setdefault("ENV_FILE", os.path.join(os.path.dirname(__file__), "backend", ".env"))

import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

# ── CLI ───────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Generate a .pkpass for a brand.")
parser.add_argument("--brand", required=True, help="Brand slug as defined in pass_brands.json")
args = parser.parse_args()

# ── Load brand config ─────────────────────────────────────────────────────────

config_path = os.path.join(os.path.dirname(__file__), "pass_brands.json")
with open(config_path) as fh:
    all_brands = json.load(fh)

if args.brand not in all_brands:
    available = ", ".join(all_brands.keys())
    sys.exit(f"Brand '{args.brand}' not found in pass_brands.json. Available: {available}")

cfg = all_brands[args.brand]

# ── Override cert paths to absolute so the script works from any directory ────

repo_root = os.path.dirname(__file__)

cert_p12_path = cfg["cert_p12_path"]
if not os.path.isabs(cert_p12_path):
    cert_p12_path = os.path.join(repo_root, cert_p12_path)

os.environ["APPLE_CERT_P12_PATH"] = cert_p12_path
os.environ["APPLE_WWDR_CERT_PATH"] = os.path.join(repo_root, "backend", "AppleWWDRCAG4.cer")

from app.services.passes.apple import AppleWalletService  # noqa: E402


# ── Minimal stand-in objects (no DB needed) ───────────────────────────────────

class FakeBrand:
    slug = args.brand
    name = cfg["name"]
    apple_pass_type_id = cfg["apple_pass_type_id"]
    apple_cert_s3_key = None
    apple_cert_password_encrypted = None
    primary_color = cfg["primary_color"]
    secondary_color = cfg["secondary_color"]
    reward_threshold = cfg["reward_threshold"]


class FakePass:
    serial_number = cfg.get("serial_number") or str(uuid.uuid4())
    points = 0


class FakeUser:
    email = cfg.get("test_user_email", "customer@example.com")
    phone = None


# ── Fetch images ──────────────────────────────────────────────────────────────

print(f"Brand: {cfg['name']} ({args.brand})")
print("Fetching images…")
_no_cache = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
with httpx.Client(timeout=10) as client:
    logo_resp = client.get(cfg["logo_url"], headers=_no_cache)
    logo_resp.raise_for_status()
    icon_bytes = logo_resp.content
    print(f"  logo:  {len(icon_bytes):,} bytes")

    hero_resp = client.get(cfg["hero_url"], headers=_no_cache)
    hero_resp.raise_for_status()
    strip_bytes = hero_resp.content
    print(f"  hero:  {len(strip_bytes):,} bytes")

# ── Build .pkpass ─────────────────────────────────────────────────────────────

svc = AppleWalletService(FakeBrand())

pkpass_bytes = svc.build_pkpass_bytes(
    FakePass(),
    FakeUser(),
    icon_bytes=icon_bytes,
    strip_bytes=strip_bytes,
)

output_path = os.path.join(repo_root, f"{args.brand}.pkpass")
with open(output_path, "wb") as fh:
    fh.write(pkpass_bytes)

print(f"\nSaved {len(pkpass_bytes):,} bytes -> {output_path}")
print("Transfer the .pkpass to your iPhone (AirDrop / Mail / etc.) to add it to Wallet.")
