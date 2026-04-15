"""
Generate both Apple Wallet (.pkpass) and Google Wallet (QR + link) for a brand.

Usage:
    python generate_pass.py --brand unusual
    python generate_pass.py --brand newshop

For quick Google-only design iteration use generate_wallet_link.py instead.
Add new brands by editing pass_brands.json — no Python changes needed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid

# Allow importing the backend app without installing it
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))
os.environ.setdefault("ENV_FILE", os.path.join(os.path.dirname(__file__), "backend", ".env"))

import httpx
import qrcode
import google.auth.crypt
import google.auth.jwt
import google.oauth2.service_account
import google.auth.transport.requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "backend", ".env"))

# ── CLI ───────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Generate Apple + Google Wallet passes for a brand.")
parser.add_argument("--brand", required=True, help="Brand slug as defined in pass_brands.json")
args = parser.parse_args()

# ── Load brand config ─────────────────────────────────────────────────────────

repo_root = os.path.dirname(__file__)
config_path = os.path.join(repo_root, "pass_brands.json")
with open(config_path) as fh:
    all_brands = json.load(fh)

if args.brand not in all_brands:
    available = ", ".join(all_brands.keys())
    sys.exit(f"Brand '{args.brand}' not found in pass_brands.json. Available: {available}")

cfg = all_brands[args.brand]
apple_cfg = cfg["apple"]
google_cfg = cfg["google"]
test_user = cfg["test_user"]

print(f"Brand: {cfg['name']} ({args.brand})\n")

# ── Fetch shared images ───────────────────────────────────────────────────────

print("Fetching images…")
with httpx.Client(timeout=10) as client:
    icon_bytes = client.get(cfg["logo_url"]).raise_for_status().content
    strip_bytes = client.get(cfg["hero_url"]).raise_for_status().content
    print(f"  logo: {len(icon_bytes):,} bytes")
    print(f"  hero: {len(strip_bytes):,} bytes")

# ── Apple Wallet ──────────────────────────────────────────────────────────────

print("\n[Apple Wallet]")

cert_p12_path = apple_cfg["cert_p12_path"]
if not os.path.isabs(cert_p12_path):
    cert_p12_path = os.path.join(repo_root, cert_p12_path)

os.environ["APPLE_CERT_P12_PATH"] = cert_p12_path
os.environ["APPLE_WWDR_CERT_PATH"] = os.path.join(repo_root, "backend", "AppleWWDRCAG4.cer")

from app.services.passes.apple import AppleWalletService  # noqa: E402


class FakeBrand:
    slug = args.brand
    name = cfg["name"]
    apple_pass_type_id = apple_cfg["pass_type_id"]
    apple_cert_s3_key = None
    apple_cert_password_encrypted = None
    primary_color = cfg["primary_color"]
    secondary_color = cfg["secondary_color"]
    reward_threshold = cfg["reward_threshold"]


class FakePass:
    serial_number = apple_cfg.get("serial_number") or str(uuid.uuid4())
    points = 0


class FakeUser:
    email = test_user.get("email", "customer@example.com")
    phone = None


svc = AppleWalletService(FakeBrand())
pkpass_bytes = svc.build_pkpass_bytes(FakePass(), FakeUser(), icon_bytes=icon_bytes, strip_bytes=strip_bytes)

apple_output = os.path.join(repo_root, f"{args.brand}.pkpass")
with open(apple_output, "wb") as fh:
    fh.write(pkpass_bytes)
print(f"  Saved {len(pkpass_bytes):,} bytes -> {apple_output}")

# ── Google Wallet ─────────────────────────────────────────────────────────────

print("\n[Google Wallet]")

sa_path = google_cfg["service_account_json"]
if not os.path.isabs(sa_path):
    sa_path = os.path.join(repo_root, sa_path)

with open(sa_path) as fh:
    sa = json.load(fh)

issuer_id = google_cfg["issuer_id"]
class_id = f"{issuer_id}.{google_cfg['class_suffix']}"
object_id = f"{issuer_id}.{google_cfg['object_suffix']}"

credentials = google.oauth2.service_account.Credentials.from_service_account_info(
    sa, scopes=["https://www.googleapis.com/auth/wallet_object.issuer"]
)
credentials.refresh(google.auth.transport.requests.Request())
headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}

class_payload = {
    "id": class_id,
    "issuerName": cfg["issuer_name"],
    "programName": "포인트 적립",
    "reviewStatus": "underReview",
    "rewardsTierLabel": "Collect stamps",
    "rewardsTier": f"Free reward at {cfg['reward_threshold']} stamps",
    "hexBackgroundColor": cfg["primary_color"],
    "programLogo": {
        "sourceUri": {"uri": cfg["logo_url"]},
        "contentDescription": {"defaultValue": {"language": "en-US", "value": cfg["name"]}},
    },
    "heroImage": {
        "sourceUri": {"uri": cfg["hero_url"]},
        "contentDescription": {"defaultValue": {"language": "en-US", "value": cfg["name"]}},
    },
    "wordMark": {
        "sourceUri": {"uri": cfg["logo_url"]},
        "contentDescription": {"defaultValue": {"language": "en-US", "value": cfg["name"]}},
    },
}

object_payload = {
    "id": object_id,
    "classId": class_id,
    "state": "ACTIVE",
    "accountId": test_user["account_id"],
    "accountName": test_user["account_name"],
    "loyaltyPoints": {
        "balance": {"int": 0},
        "label": "스탬프",
    },
}

# Upsert class
rc = httpx.get(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass/{class_id}", headers=headers)
print(f"  Class check: {rc.status_code}")
if rc.status_code == 404:
    rc = httpx.post("https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass", headers=headers, json=class_payload)
    if rc.status_code not in (200, 201):
        sys.exit(f"Failed to create class: {rc.status_code} {rc.text}")
    print("  Class created.")
elif rc.status_code == 200:
    print("  Class already exists.")
else:
    sys.exit(f"Unexpected error checking class: {rc.text}")

# Upsert object
ro = httpx.get(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{object_id}", headers=headers)
if ro.status_code == 404:
    ro = httpx.post("https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject", headers=headers, json=object_payload)
    action = "created"
else:
    ro = httpx.put(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{object_id}", headers=headers, json=object_payload)
    action = "updated"

if ro.status_code not in (200, 201):
    sys.exit(f"Failed to {action} object: {ro.status_code} {ro.text}")
print(f"  Pass object {action}.")

# JWT + QR
signer = google.auth.crypt.RSASigner.from_service_account_info(sa)
jwt_payload = {
    "iss": sa["client_email"],
    "aud": "google",
    "typ": "savetowallet",
    "iat": int(time.time()),
    "payload": {"loyaltyObjects": [{"id": object_id}]},
    "origins": [],
}
token = google.auth.jwt.encode(signer, jwt_payload).decode("utf-8")
save_url = f"https://pay.google.com/gp/v/save/{token}"

qr_output = os.path.join(repo_root, f"{args.brand}_wallet_qr.png")
qrcode.make(save_url).save(qr_output)
print(f"  QR saved -> {qr_output}")
print(f"  Link: {save_url}")

# ── Summary ───────────────────────────────────────────────────────────────────

print(f"""
Done!
  Apple: {apple_output}  → AirDrop / Mail to iPhone
  Google: {qr_output}    → scan with Android phone
""")
