from __future__ import annotations

import hashlib
import io
import json
import logging
import zipfile
from typing import Any

import boto3
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives.serialization.pkcs7 import (
    PKCS7Options,
    PKCS7SignatureBuilder,
)
from cryptography.x509 import load_pem_x509_certificate

from app.config import get_settings
from app.models.brand import Brand
from app.models.pass_ import Pass
from app.models.user import User

logger = logging.getLogger(__name__)


class AppleWalletService:
    """
    Handles Apple Wallet (.pkpass) generation for a single Brand.

    Credential resolution order for the signing certificate:
    1. brand.apple_cert_s3_key  — .p12 key stored in S3/R2 (prod)
    2. settings.APPLE_CERT_P12_PATH  — local file path (dev fallback)

    Raises ValueError if neither source is available when build is attempted.

    Signing flow per Apple documentation
    (https://developer.apple.com/documentation/walletpasses/creating-a-store-card-pass):
      1. Build pass.json with a storeCard structure.
      2. Build manifest.json with SHA-1 hashes of every file in the bundle.
      3. Create a PKCS#7 detached signature of manifest.json using the brand's
         Pass Type ID certificate and Apple's WWDR intermediate certificate.
      4. Zip pass.json + manifest.json + signature → .pkpass archive.
      5. Upload to S3, return a presigned download URL.

    When a customer opens the URL on iPhone, iOS recognises the
    ``application/vnd.apple.pkpass`` content-type and adds the pass to Wallet.
    """

    def __init__(self, brand: Brand) -> None:
        self._brand = brand
        self._settings = get_settings()

    # ── Certificate loading ───────────────────────────────────────────────────

    def _load_p12_bytes(self) -> bytes:
        """Fetch the .p12 cert bytes from S3 or a local dev path."""
        if self._brand.apple_cert_s3_key:
            s = self._settings
            s3 = boto3.client(
                "s3",
                region_name=s.S3_REGION,
                aws_access_key_id=s.S3_ACCESS_KEY_ID,
                aws_secret_access_key=s.S3_SECRET_ACCESS_KEY,
                endpoint_url=s.S3_ENDPOINT_URL or None,
            )
            obj = s3.get_object(Bucket=s.S3_BUCKET, Key=self._brand.apple_cert_s3_key)
            return obj["Body"].read()

        path = self._settings.APPLE_CERT_P12_PATH
        if path:
            with open(path, "rb") as fh:
                return fh.read()

        raise ValueError(
            f"Brand '{self._brand.slug}' has no Apple Wallet cert configured. "
            "Set brand.apple_cert_s3_key in the database or "
            "APPLE_CERT_P12_PATH in settings."
        )

    def _cert_password(self) -> bytes | None:
        """Decrypt the stored cert password or fall back to the plain-text dev setting."""
        encrypted = self._brand.apple_cert_password_encrypted
        if encrypted:
            from cryptography.fernet import Fernet
            key = self._settings.APPLE_CERT_ENCRYPTION_KEY.encode()
            return Fernet(key).decrypt(encrypted.encode())

        plain = self._settings.APPLE_CERT_PASSWORD
        return plain.encode() if plain else None

    def _load_signing_material(self) -> tuple[Any, Any]:
        """Return (private_key, cert) extracted from the brand .p12 bundle."""
        p12_data = self._load_p12_bytes()
        password = self._cert_password()
        private_key, cert, _ = pkcs12.load_key_and_certificates(p12_data, password)
        return private_key, cert

    def _load_wwdr_cert(self) -> Any:
        """
        Load Apple's WWDR G4 intermediate certificate from the configured PEM path.

        Download from: https://www.apple.com/certificateauthority/
        (Apple Worldwide Developer Relations — G4, expires 2030-10-31)
        Set APPLE_WWDR_CERT_PATH in settings to point at the local file.
        """
        path = self._settings.APPLE_WWDR_CERT_PATH
        if not path:
            raise ValueError(
                "APPLE_WWDR_CERT_PATH is not set. "
                "Download the Apple WWDR G4 certificate and configure the path."
            )
        with open(path, "rb") as fh:
            return load_pem_x509_certificate(fh.read())

    # ── pass.json ─────────────────────────────────────────────────────────────

    @staticmethod
    def _hex_to_rgb(hex_color: str | None) -> str:
        """Convert '#RRGGBB' → 'rgb(R, G, B)' as required by Apple Wallet."""
        if not hex_color:
            return "rgb(0, 0, 0)"
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgb({r}, {g}, {b})"

    def _build_pass_json(self, pass_obj: Pass, user: User) -> dict[str, Any]:
        """
        Build the storeCard pass.json dictionary.

        Field layout on the front of the card:
        ┌─────────────────────────────────┐
        │ [logo]           STAMPS  <pts>  │  ← headerFields
        │         <brand name>            │  ← primaryFields (logoText)
        │ MEMBER           FREE REWARD AT │
        │ <email/phone>    <threshold>    │  ← secondaryFields
        └─────────────────────────────────┘
        Back of the card:
          • About blurb
          • Pass serial number
        """
        brand = self._brand
        s = self._settings
        points = pass_obj.points
        threshold = brand.reward_threshold
        remaining = max(0, threshold - points)

        return {
            "formatVersion": 1,
            "passTypeIdentifier": brand.apple_pass_type_id,
            "serialNumber": pass_obj.serial_number,
            "teamIdentifier": s.APPLE_TEAM_ID,
            "organizationName": brand.name,
            "description": f"{brand.name} Loyalty Card",
            "backgroundColor": self._hex_to_rgb(brand.primary_color),
            "foregroundColor": self._hex_to_rgb(brand.secondary_color),
            "labelColor": self._hex_to_rgb(brand.secondary_color),
            "logoText": brand.name,
            # webServiceURL enables Apple to call back for live pass updates via APNs
            "webServiceURL": f"{s.API_BASE_URL.rstrip('/')}/apple-wallet/",
            "authenticationToken": pass_obj.serial_number,
            "storeCard": {
                "headerFields": [
                    {
                        "key": "points",
                        "label": "STAMPS",
                        "value": str(points),
                        "textAlignment": "PKTextAlignmentRight",
                    }
                ],
                "primaryFields": [
                    {
                        "key": "member",
                        "label": "MEMBER",
                        "value": user.email or user.phone or "Customer",
                    }
                ],
                "secondaryFields": [
                    {
                        "key": "reward_at",
                        "label": "FREE REWARD AT",
                        "value": str(threshold),
                    },
                    {
                        "key": "stamps_to_go",
                        "label": "TO GO",
                        "value": str(remaining),
                    },
                ],
                "backFields": [
                    {
                        "key": "about",
                        "label": brand.name,
                        "value": (
                            f"Collect {threshold} stamps to earn a free reward. "
                            "Show this pass at the counter to get stamped."
                        ),
                    },
                    {
                        "key": "serial",
                        "label": "Pass ID",
                        "value": pass_obj.serial_number,
                    },
                ],
            },
            # barcodes (plural) is the modern key; Apple Wallet also reads the
            # legacy barcode (singular) key for backward compatibility.
            "barcodes": [
                {
                    "message": pass_obj.serial_number,
                    "format": "PKBarcodeFormatQR",
                    "messageEncoding": "iso-8859-1",
                    "altText": "Scan to earn stamps",
                }
            ],
        }

    # ── Bundle construction ───────────────────────────────────────────────────

    @staticmethod
    def _build_manifest(files: dict[str, bytes]) -> bytes:
        """
        Build manifest.json: a dict mapping filename → SHA-1 hex digest.
        Apple requires SHA-1 (not SHA-256) for the manifest hashes.
        """
        manifest = {name: hashlib.sha1(data).hexdigest() for name, data in files.items()}
        return json.dumps(manifest, separators=(",", ":")).encode()

    @staticmethod
    def _sign_manifest(
        manifest_bytes: bytes,
        private_key: Any,
        cert: Any,
        wwdr_cert: Any,
    ) -> bytes:
        """
        Return a DER-encoded PKCS#7 detached signature of manifest.json.

        The bundle must contain:
        - The brand's Pass Type ID signing certificate (added via add_signer).
        - Apple's WWDR intermediate certificate (added via add_certificate).
        """
        builder = (
            PKCS7SignatureBuilder()
            .set_data(manifest_bytes)
            .add_signer(cert, private_key, hashes.SHA256())
            .add_certificate(wwdr_cert)
        )
        return builder.sign(
            serialization.Encoding.DER,
            [PKCS7Options.DetachedSignature],
        )

    @staticmethod
    def _bundle_pkpass(files: dict[str, bytes]) -> bytes:
        """Zip all files into a .pkpass archive."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in files.items():
                zf.writestr(name, data)
        return buf.getvalue()

    # ── S3 persistence ────────────────────────────────────────────────────────

    def _s3_client(self) -> Any:
        s = self._settings
        return boto3.client(
            "s3",
            region_name=s.S3_REGION,
            aws_access_key_id=s.S3_ACCESS_KEY_ID,
            aws_secret_access_key=s.S3_SECRET_ACCESS_KEY,
            endpoint_url=s.S3_ENDPOINT_URL or None,
        )

    def _upload_pkpass(self, serial_number: str, pkpass_bytes: bytes) -> str:
        """
        Upload the .pkpass bundle to S3 and return a 1-hour presigned download URL.
        The object key is deterministic so re-uploads overwrite the previous version.
        """
        s = self._settings
        s3 = self._s3_client()
        key = f"passes/apple/{serial_number}.pkpass"
        s3.put_object(
            Bucket=s.S3_BUCKET,
            Key=key,
            Body=pkpass_bytes,
            ContentType="application/vnd.apple.pkpass",
        )
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": s.S3_BUCKET, "Key": key},
            ExpiresIn=3600,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_pass(self, pass_obj: Pass, user: User) -> str:
        """
        Build, sign, and upload a .pkpass bundle.
        Returns a presigned S3 URL the customer opens on iPhone to add the pass to Wallet.
        """
        if not self._brand.apple_pass_type_id:
            raise ValueError(
                f"Brand '{self._brand.slug}' has no apple_pass_type_id configured."
            )

        private_key, cert = self._load_signing_material()
        wwdr_cert = self._load_wwdr_cert()

        pass_json_bytes = json.dumps(
            self._build_pass_json(pass_obj, user), ensure_ascii=False
        ).encode()

        # content_files are the files that get hashed into manifest.json.
        # Add icon.png / logo.png here once brand image downloads are wired up.
        content_files: dict[str, bytes] = {"pass.json": pass_json_bytes}

        manifest_bytes = self._build_manifest(content_files)
        signature_bytes = self._sign_manifest(manifest_bytes, private_key, cert, wwdr_cert)

        bundle: dict[str, bytes] = {
            **content_files,
            "manifest.json": manifest_bytes,
            "signature": signature_bytes,
        }

        pkpass_bytes = self._bundle_pkpass(bundle)
        url = self._upload_pkpass(pass_obj.serial_number, pkpass_bytes)
        logger.info("Created Apple Wallet pass %s for brand %s.", pass_obj.serial_number, self._brand.slug)
        return url

    async def update_pass_points(self, pass_obj: Pass, user: User) -> None:
        """
        Rebuild and re-upload the .pkpass with the current point balance.

        The deterministic S3 key means the file is overwritten in place.
        Note: this does NOT push a live notification to the device — that requires
        the APNs push flow (implement webServiceURL endpoints to enable it).
        """
        await self.create_pass(pass_obj, user)
        logger.info(
            "Rebuilt Apple Wallet pass %s (points=%d). "
            "Device will pick up changes on next manual refresh.",
            pass_obj.serial_number,
            pass_obj.points,
        )
