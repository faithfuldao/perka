"""
Quick Google Wallet pass generator for design iteration.
Updates the class + object in-place and prints a fresh QR — no Apple cert needed.

Usage:
    python generate_wallet_link.py --brand unusual

For generating both Apple and Google passes together, use generate_pass.py.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import httpx
import qrcode
import google.auth.crypt
import google.auth.jwt
import google.oauth2.service_account
import google.auth.transport.requests

# ── CLI ───────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Quick Google Wallet pass for design testing.")
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
google_cfg = cfg["google"]
test_user = cfg["test_user"]

sa_path = google_cfg["service_account_json"]
if not os.path.isabs(sa_path):
    sa_path = os.path.join(repo_root, sa_path)

with open(sa_path) as fh:
    sa = json.load(fh)

issuer_id = google_cfg["issuer_id"]
class_id = f"{issuer_id}.{google_cfg['class_suffix']}"
object_id = f"{issuer_id}.{google_cfg['object_suffix']}"

# ── Auth ──────────────────────────────────────────────────────────────────────

credentials = google.oauth2.service_account.Credentials.from_service_account_info(
    sa, scopes=["https://www.googleapis.com/auth/wallet_object.issuer"]
)
credentials.refresh(google.auth.transport.requests.Request())
headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}

# ── Upsert class ──────────────────────────────────────────────────────────────

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

rc = httpx.get(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass/{class_id}", headers=headers)
print(f"Class check: {rc.status_code} — {class_id}")
if rc.status_code == 404:
    rc = httpx.post("https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass", headers=headers, json=class_payload)
    if rc.status_code not in (200, 201):
        sys.exit(f"Failed to create class: {rc.status_code} {rc.text}")
    print("Class created.")
elif rc.status_code == 200:
    rc = httpx.put(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass/{class_id}", headers=headers, json=class_payload)
    if rc.status_code not in (200, 201):
        sys.exit(f"Failed to update class: {rc.status_code} {rc.text}")
    print("Class updated.")
else:
    sys.exit(f"Unexpected error: {rc.text}")

# ── Upsert object ─────────────────────────────────────────────────────────────

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

ro = httpx.get(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{object_id}", headers=headers)
if ro.status_code == 404:
    ro = httpx.post("https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject", headers=headers, json=object_payload)
    action = "created"
else:
    ro = httpx.put(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{object_id}", headers=headers, json=object_payload)
    action = "updated"

if ro.status_code not in (200, 201):
    sys.exit(f"Failed to {action} object: {ro.status_code} {ro.text}")
print(f"Pass object {action}.")

# ── JWT + QR ──────────────────────────────────────────────────────────────────

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

qr_output = os.path.join(repo_root, "wallet_qr.png")
qrcode.make(save_url).save(qr_output)

print(f"\nLink: {save_url}")
print(f"QR saved -> {qr_output}")
