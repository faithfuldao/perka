"""
Generate Google Wallet (save URL + QR) and Apple Wallet (.pkpass + QR) for a brand.

Usage:
    python generate_wallet_link.py --brand unusual
    python generate_wallet_link.py --brand unusual --points 5
    python generate_wallet_link.py --brand unusual --port 9000

Both QR images are saved to the repo root. The Apple QR points to a temporary
local HTTP server — your iPhone must be on the same Wi-Fi. Press Ctrl+C when done.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
import socket
import sys
import threading
import time
import uuid

import httpx
import qrcode
import google.auth.crypt
import google.auth.jwt
import google.oauth2.service_account
import google.auth.transport.requests

# ── CLI ───────────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="Generate Apple + Google Wallet passes for a brand.")
parser.add_argument("--brand", required=True, help="Brand slug as defined in pass_brands.json")
parser.add_argument("--points", type=int, default=0, help="Stamp count to display on both passes (default: 0)")
parser.add_argument("--port", type=int, default=8765, help="Local port for the Apple pass server (default: 8765)")
parser.add_argument("--cert-password", default="", help="Apple .p12 cert password (overrides .env)")
args = parser.parse_args()

# ── Load brand config ─────────────────────────────────────────────────────────

repo_root = os.path.dirname(os.path.abspath(__file__))

config_path = os.path.join(repo_root, "pass_brands.json")
with open(config_path, encoding="utf-8") as fh:
    all_brands = json.load(fh)

if args.brand not in all_brands:
    available = ", ".join(all_brands.keys())
    sys.exit(f"Brand '{args.brand}' not found in pass_brands.json. Available: {available}")

cfg = all_brands[args.brand]
apple_cfg = cfg["apple"]
google_cfg = cfg["google"]
test_user = cfg["test_user"]

print(f"Brand: {cfg['name']} ({args.brand})  |  points: {args.points}\n")

# ── Fetch shared images ───────────────────────────────────────────────────────

print("Fetching images…")
with httpx.Client(timeout=30) as client:
    icon_bytes = client.get(cfg["logo_url"]).raise_for_status().content
    strip_bytes = client.get(cfg["hero_url"]).raise_for_status().content
    print(f"  logo: {len(icon_bytes):,} bytes")
    print(f"  hero: {len(strip_bytes):,} bytes")

# ── Google Wallet ─────────────────────────────────────────────────────────────

print("\n[Google Wallet]")

sa_path = google_cfg["service_account_json"]
if not os.path.isabs(sa_path):
    sa_path = os.path.join(repo_root, sa_path)

with open(sa_path, encoding="utf-8") as fh:
    sa = json.load(fh)

issuer_id = google_cfg["issuer_id"]
class_id = f"{issuer_id}.{google_cfg['class_suffix']}"
object_id = f"{issuer_id}.{google_cfg['object_suffix']}"

credentials = google.oauth2.service_account.Credentials.from_service_account_info(
    sa, scopes=["https://www.googleapis.com/auth/wallet_object.issuer"]
)
credentials.refresh(google.auth.transport.requests.Request())
g_headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}

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
        "balance": {"int": args.points},
        "label": "스탬프",
    },
}

rc = httpx.get(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass/{class_id}", headers=g_headers)
print(f"  Class check: {rc.status_code}")
if rc.status_code == 404:
    rc = httpx.post("https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass", headers=g_headers, json=class_payload)
    if rc.status_code not in (200, 201):
        sys.exit(f"Failed to create class: {rc.status_code} {rc.text}")
    print("  Class created.")
elif rc.status_code == 200:
    rc = httpx.put(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass/{class_id}", headers=g_headers, json=class_payload)
    if rc.status_code not in (200, 201):
        print(f"  Warning: class update returned {rc.status_code}")
    else:
        print("  Class updated.")
else:
    sys.exit(f"Unexpected class error: {rc.text}")

ro = httpx.get(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{object_id}", headers=g_headers)
if ro.status_code == 404:
    ro = httpx.post("https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject", headers=g_headers, json=object_payload)
    action = "created"
else:
    ro = httpx.put(f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{object_id}", headers=g_headers, json=object_payload)
    action = "updated"

if ro.status_code not in (200, 201):
    sys.exit(f"Failed to {action} object: {ro.status_code} {ro.text}")
print(f"  Pass object {action}.")

signer = google.auth.crypt.RSASigner.from_service_account_info(sa)
jwt_payload = {
    "iss": sa["client_email"],
    "aud": "google",
    "typ": "savetowallet",
    "iat": int(time.time()),
    "payload": {"loyaltyObjects": [{"id": object_id}]},
    "origins": [],
}
token = google.auth.jwt.encode(signer, jwt_payload)
if isinstance(token, bytes):
    token = token.decode("utf-8")
google_save_url = f"https://pay.google.com/gp/v/save/{token}"

google_qr_path = os.path.join(repo_root, f"{args.brand}_google_qr.png")
qrcode.make(google_save_url).save(google_qr_path)
print(f"  QR saved  -> {google_qr_path}")
print(f"  Link      -> {google_save_url}")

# ── Apple Wallet ──────────────────────────────────────────────────────────────

print("\n[Apple Wallet]")

apple_server = None
apple_qr_path = None

try:
    import hashlib
    import io
    import zipfile
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.serialization import pkcs12
    from cryptography.hazmat.primitives.serialization.pkcs7 import PKCS7Options, PKCS7SignatureBuilder
    from cryptography.x509 import load_der_x509_certificate, load_pem_x509_certificate

    # ── Read settings from backend/.env or .env.exemple as fallback ──────────
    env_vals: dict[str, str] = {}
    for _candidate in [
        os.path.join(repo_root, "backend", ".env"),
        os.path.join(repo_root, "backend", ".env.exemple"),
    ]:
        if os.path.exists(_candidate):
            with open(_candidate, encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _, _v = _line.partition("=")
                        env_vals.setdefault(_k.strip(), _v.strip())
            break

    # --cert-password flag takes priority over .env
    cert_password_str = args.cert_password or env_vals.get("APPLE_CERT_PASSWORD", "")
    cert_password = cert_password_str.encode() if cert_password_str else None
    team_id = env_vals.get("APPLE_TEAM_ID", "")
    api_base_url = env_vals.get("API_BASE_URL", "http://localhost:8000").rstrip("/")

    # ── Load cert materials ───────────────────────────────────────────────────
    cert_p12_path = apple_cfg["cert_p12_path"]
    if not os.path.isabs(cert_p12_path):
        cert_p12_path = os.path.join(repo_root, cert_p12_path)

    wwdr_path = os.path.join(repo_root, "backend", "AppleWWDRCAG4.cer")

    with open(cert_p12_path, "rb") as _f:
        private_key, signing_cert, _ = pkcs12.load_key_and_certificates(_f.read(), cert_password)

    with open(wwdr_path, "rb") as _f:
        wwdr_data = _f.read()
    wwdr_cert = (
        load_pem_x509_certificate(wwdr_data)
        if wwdr_data.lstrip().startswith(b"-----")
        else load_der_x509_certificate(wwdr_data)
    )

    # ── Build pass.json ───────────────────────────────────────────────────────
    def _hex_to_rgb(hex_color: str) -> str:
        h = hex_color.lstrip("#")
        return f"rgb({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)})"

    serial = apple_cfg.get("serial_number") or str(uuid.uuid4())
    threshold = cfg["reward_threshold"]
    remaining = max(0, threshold - args.points)

    pass_json_bytes = json.dumps({
        "formatVersion": 1,
        "passTypeIdentifier": apple_cfg["pass_type_id"],
        "serialNumber": serial,
        "teamIdentifier": team_id,
        "organizationName": cfg["name"],
        "description": f"{cfg['name']} Loyalty Card",
        "backgroundColor": _hex_to_rgb(cfg["primary_color"]),
        "foregroundColor": _hex_to_rgb(cfg.get("secondary_color", "#000000")),
        "labelColor": _hex_to_rgb(cfg.get("secondary_color", "#000000")),
        "logoText": cfg["name"],
        "storeCard": {
            "headerFields": [],
            "primaryFields": [],
            "secondaryFields": [
                {"key": "reward_at", "label": "무료 리워드", "value": str(threshold)},
                {"key": "stamps_to_go", "label": "남은 스탬프", "value": str(remaining)},
            ],
            "auxiliaryFields": [],
            "backFields": [
                {"key": "about", "label": cfg["name"], "value": f"Collect {threshold} stamps to earn a free reward."},
                {"key": "serial", "label": "Pass ID", "value": serial},
            ],
        },
        "barcodes": [{
            "message": f"{api_base_url}/scan/{serial}",
            "format": "PKBarcodeFormatQR",
            "messageEncoding": "iso-8859-1",
        }],
    }, ensure_ascii=False).encode()

    # ── Bundle .pkpass ────────────────────────────────────────────────────────
    content: dict[str, bytes] = {"pass.json": pass_json_bytes}
    if icon_bytes:
        content.update({"icon.png": icon_bytes, "icon@2x.png": icon_bytes,
                        "logo.png": icon_bytes, "logo@2x.png": icon_bytes})
    if strip_bytes:
        content.update({"strip.png": strip_bytes, "strip@2x.png": strip_bytes})

    manifest_bytes = json.dumps(
        {name: hashlib.sha1(data).hexdigest() for name, data in content.items()},
        separators=(",", ":"),
    ).encode()

    signature_bytes = (
        PKCS7SignatureBuilder()
        .set_data(manifest_bytes)
        .add_signer(signing_cert, private_key, hashes.SHA256())
        .add_certificate(wwdr_cert)
        .sign(serialization.Encoding.DER, [PKCS7Options.DetachedSignature])
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in {**content, "manifest.json": manifest_bytes, "signature": signature_bytes}.items():
            zf.writestr(name, data)
    pkpass_bytes = buf.getvalue()

    pkpass_filename = f"{args.brand}.pkpass"
    pkpass_path = os.path.join(repo_root, pkpass_filename)
    with open(pkpass_path, "wb") as fh:
        fh.write(pkpass_bytes)
    print(f"  .pkpass saved -> {pkpass_path}  ({len(pkpass_bytes):,} bytes)")

    # ── Local HTTP server so iPhone can download the .pkpass over Wi-Fi ───────
    def _get_local_ip() -> str:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        finally:
            s.close()

    class _PkpassHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=repo_root, **kw)

        def end_headers(self) -> None:
            if self.path.endswith(".pkpass"):
                self.send_header("Content-Type", "application/vnd.apple.pkpass")
            super().end_headers()

        def log_message(self, *_) -> None:
            pass  # silence access log spam

    local_ip = _get_local_ip()
    apple_server = http.server.HTTPServer(("0.0.0.0", args.port), _PkpassHandler)
    threading.Thread(target=apple_server.serve_forever, daemon=True).start()

    apple_url = f"http://{local_ip}:{args.port}/{pkpass_filename}"
    apple_qr_path = os.path.join(repo_root, f"{args.brand}_apple_qr.png")
    qrcode.make(apple_url).save(apple_qr_path)
    print(f"  QR saved  -> {apple_qr_path}")
    print(f"  URL       -> {apple_url}")
    print(f"  (iPhone must be on the same Wi-Fi as this machine)")

except Exception as exc:
    print(f"  Apple pass generation failed: {exc}")
    print("  Tip: check that backend/pass.p12 and backend/AppleWWDRCAG4.cer exist.")

# ── Summary ───────────────────────────────────────────────────────────────────

print("\n" + "─" * 50)
print(f"  Google QR  -> {args.brand}_google_qr.png   (scan with Android)")
if apple_qr_path:
    print(f"  Apple QR   -> {args.brand}_apple_qr.png    (scan with iPhone on same Wi-Fi)")
    print(f"  Apple file -> {args.brand}.pkpass           (or AirDrop / Mail to iPhone)")
print("─" * 50)

if apple_server:
    print("\nServing Apple pass locally — press Ctrl+C when your iPhone has scanned the QR.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopped.")
        apple_server.shutdown()
