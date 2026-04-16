from __future__ import annotations

import json
import logging
import time
from typing import Any

import google.auth.crypt
import google.auth.jwt
import google.auth.transport.requests
import google.oauth2.service_account
import httpx

from app.config import get_settings
from app.models.brand import Brand
from app.models.pass_ import Pass
from app.models.user import User

logger = logging.getLogger(__name__)

_WALLET_SCOPE = "https://www.googleapis.com/auth/wallet_object.issuer"
_BASE_URL = "https://walletobjects.googleapis.com/walletobjects/v1"
_LOYALTY_OBJECT_URL = f"{_BASE_URL}/loyaltyObject"
_LOYALTY_CLASS_URL = f"{_BASE_URL}/loyaltyClass"


class GoogleWalletService:
    """
    Handles all Google Wallet API interactions for a single Brand.

    Credential resolution order:
    1. brand.google_service_account_json  — dict stored in the DB column
    2. settings.GOOGLE_SERVICE_ACCOUNT_JSON_PATH  — file path (dev fallback)

    Raises ValueError on init if neither source is available.
    """

    def __init__(self, brand: Brand) -> None:
        self._brand = brand
        self._sa: dict[str, Any] = self._load_service_account()

    # ── Credential loading ────────────────────────────────────────────────────

    def _load_service_account(self) -> dict[str, Any]:
        if self._brand.google_service_account_json:
            return self._brand.google_service_account_json  # type: ignore[return-value]

        path = get_settings().GOOGLE_SERVICE_ACCOUNT_JSON_PATH
        if path:
            with open(path) as fh:
                return json.load(fh)

        raise ValueError(
            f"Brand '{self._brand.slug}' has no Google service account configured. "
            "Set brand.google_service_account_json in the database or "
            "GOOGLE_SERVICE_ACCOUNT_JSON_PATH in settings."
        )

    def _get_bearer_token(self) -> str:
        """Obtain a short-lived OAuth2 bearer token for the Wallet API."""
        credentials = google.oauth2.service_account.Credentials.from_service_account_info(
            self._sa, scopes=[_WALLET_SCOPE]
        )
        credentials.refresh(google.auth.transport.requests.Request())
        return credentials.token  # type: ignore[return-value]

    # ── ID helpers ────────────────────────────────────────────────────────────

    def object_id(self, pass_obj: Pass) -> str:
        return f"{self._brand.google_issuer_id}.{pass_obj.serial_number}"

    def _class_id(self) -> str:
        class_suffix = self._brand.google_wallet_class_id or f"{self._brand.slug}_loyalty"
        return f"{self._brand.google_issuer_id}.{class_suffix}"

    # ── Class management ──────────────────────────────────────────────────────

    def _build_class_payload(self) -> dict[str, Any]:
        """Build the loyalty class payload with full brand styling."""
        threshold = self._brand.reward_threshold
        payload: dict[str, Any] = {
            "id": self._class_id(),
            "issuerName": self._brand.name,
            "programName": self._brand.name,
            "reviewStatus": "underReview",
            # Reward tier text: "Collect 10 stamps to receive Free coffee"
            "rewardsTierLabel": "Collect stamps",
            "rewardsTier": f"Free reward at {threshold} stamps",
        }

        if self._brand.primary_color:
            payload["hexBackgroundColor"] = self._brand.primary_color

        if self._brand.logo_url:
            payload["programLogo"] = {
                "sourceUri": {"uri": self._brand.logo_url},
                "contentDescription": {"defaultValue": {"language": "en-US", "value": self._brand.name}},
            }

        # Hero photo at the bottom of the card (1032×336px recommended)
        if self._brand.google_hero_image_url:
            payload["heroImage"] = {
                "sourceUri": {"uri": self._brand.google_hero_image_url},
                "contentDescription": {"defaultValue": {"language": "en-US", "value": self._brand.name}},
            }

        # Large subtitle shown on the card front, e.g. "Specialty coffee & pastries"
        if self._brand.google_card_title:
            payload["textModulesData"] = [
                {
                    "id": "card_title",
                    "header": self._brand.google_card_title,
                    "body": f"Collect {threshold} stamps for a free reward.",
                }
            ]

        return payload

    async def _ensure_class(self, headers: dict[str, str]) -> None:
        """Create the loyalty class if it doesn't exist, or patch its styling."""
        class_id = self._class_id()
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{_LOYALTY_CLASS_URL}/{class_id}", headers=headers)
            payload = self._build_class_payload()
            if r.status_code == 404:
                await client.post(_LOYALTY_CLASS_URL, headers=headers, json=payload)
                logger.info("Created loyalty class %s", class_id)
            elif r.status_code == 200:
                # Patch visual fields only — don't touch reviewStatus if already approved
                existing = r.json()
                patch: dict[str, Any] = {
                    k: payload[k]
                    for k in ("hexBackgroundColor", "logo", "programLogo", "textModulesData", "programName", "issuerName")
                    if k in payload
                }
                if existing.get("reviewStatus") != "approved":
                    patch["reviewStatus"] = "underReview"
                await client.patch(
                    f"{_LOYALTY_CLASS_URL}/{class_id}", headers=headers, json=patch
                )

    # ── Public API ────────────────────────────────────────────────────────────

    async def create_pass(self, pass_obj: Pass, user: User) -> str:
        """
        Create a Google Wallet loyalty object for *user* and return the
        "Save to Wallet" URL.

        If the object already exists on Google's side (HTTP 409) the existing
        object is left as-is and the save URL is still generated and returned.
        """
        token = self._get_bearer_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        await self._ensure_class(headers)

        account_name = user.email or user.phone or "Customer"
        account_id = str(user.id)

        points = pass_obj.points
        threshold = self._brand.reward_threshold
        remaining = max(0, threshold - points)
        progress_msg = (
            "You've earned a reward! Redeem on your next visit."
            if remaining == 0
            else f"{remaining} more point{'s' if remaining != 1 else ''} until your next reward."
        )

        object_payload = {
            "id": self.object_id(pass_obj),
            "classId": self._class_id(),
            "state": "ACTIVE",
            "accountId": account_id,
            "accountName": account_name,
            # balance must be an integer (not a string) for Google to render
            # the stamp grid — it fills N stamps out of the total in stampInfos
            "loyaltyPoints": {
                "balance": {"int": points},
                "label": "Stamps",
            },
            "barcode": {
                "type": "QR_CODE",
                "value": f"{get_settings().API_BASE_URL.rstrip('/')}/scan/{pass_obj.serial_number}",
                "alternateText": "Scan to validate",
            },
            "textModulesData": [
                {
                    "id": "reward_progress",
                    "header": "Your Progress",
                    "body": progress_msg,
                }
            ],
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                _LOYALTY_OBJECT_URL, headers=headers, json=object_payload
            )

        if response.status_code == 409:
            # Object already exists — not an error; just continue to JWT generation.
            logger.info(
                "Google Wallet object %s already exists, skipping creation.",
                self.object_id(pass_obj),
            )
        elif response.status_code not in (200, 201):
            logger.error(
                "Failed to create Google Wallet object %s: %s %s",
                self.object_id(pass_obj),
                response.status_code,
                response.text,
            )
            response.raise_for_status()

        return self.build_save_url(pass_obj)

    async def update_pass_points(self, pass_obj: Pass) -> None:
        """
        PATCH the loyalty object on Google's side with the current points balance.

        Uses a partial PATCH so only loyaltyPoints is updated; all other fields
        on the object remain unchanged.
        """
        token = self._get_bearer_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        points = pass_obj.points
        threshold = self._brand.reward_threshold
        remaining = max(0, threshold - points)
        progress_msg = (
            "You've earned a reward! Redeem on your next visit."
            if remaining == 0
            else f"{remaining} more point{'s' if remaining != 1 else ''} until your next reward."
        )

        patch_payload = {
            "loyaltyPoints": {
                "balance": {"int": points},
                "label": "Stamps",
            },
            "textModulesData": [
                {
                    "id": "reward_progress",
                    "header": "Your Progress",
                    "body": progress_msg,
                }
            ],
        }

        object_id = self.object_id(pass_obj)
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.patch(
                f"{_LOYALTY_OBJECT_URL}/{object_id}",
                headers=headers,
                json=patch_payload,
            )

        if response.status_code not in (200, 201):
            logger.error(
                "Failed to PATCH Google Wallet object %s: %s %s",
                object_id,
                response.status_code,
                response.text,
            )
            response.raise_for_status()

    # ── JWT / save URL ────────────────────────────────────────────────────────

    def build_save_url(self, pass_obj: Pass) -> str:
        """Sign a JWT and return the https://pay.google.com/gp/v/save/<token> URL."""
        signer = google.auth.crypt.RSASigner.from_service_account_info(self._sa)
        jwt_payload = {
            "iss": self._sa["client_email"],
            "aud": "google",
            "typ": "savetowallet",
            "iat": int(time.time()),
            "payload": {
                "loyaltyObjects": [{"id": self.object_id(pass_obj)}]
            },
            "origins": [],
        }
        token = google.auth.jwt.encode(signer, jwt_payload).decode("utf-8")
        return f"https://pay.google.com/gp/v/save/{token}"
