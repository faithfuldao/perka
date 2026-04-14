from __future__ import annotations

import json
import logging

from app.services.passes.base import PassBuildContext, PassBuilder

logger = logging.getLogger(__name__)


class ApplePassBuilder(PassBuilder):
    """
    Builds an Apple Wallet (.pkpass) pass.

    Full Apple Wallet signing requires:
    1. A pass.json manifest.
    2. SHA-1 hashes of all included files in a manifest.json.
    3. A PKCS#7 detached signature using the brand's .p12 certificate.
    4. Bundling everything into a ZIP archive with a .pkpass extension.

    This implementation produces the pass.json structure and documents
    the signing steps. Production signing should use the ``passkit-generator``
    approach or a dedicated library once a signing cert is available.

    See: https://developer.apple.com/documentation/walletpasses
    """

    def _hex_to_rgb(self, hex_color: str | None) -> str:
        """Convert '#RRGGBB' to 'rgb(R, G, B)' required by Apple Wallet."""
        if not hex_color:
            return "rgb(0, 0, 0)"
        hex_color = hex_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgb({r}, {g}, {b})"

    def _build_pass_json(self, ctx: PassBuildContext) -> dict:
        return {
            "formatVersion": 1,
            "passTypeIdentifier": ctx.apple_pass_type_id or "pass.com.perka.loyalty",
            "serialNumber": ctx.serial_number,
            "teamIdentifier": "REPLACE_WITH_TEAM_ID",
            "webServiceURL": "https://api.perka.app/apple-wallet/",
            "authenticationToken": ctx.serial_number,
            "organizationName": ctx.brand_name,
            "description": f"{ctx.brand_name} Loyalty Card",
            "foregroundColor": self._hex_to_rgb(ctx.secondary_color),
            "backgroundColor": self._hex_to_rgb(ctx.primary_color),
            "logoText": ctx.brand_name,
            "storeCard": {
                "headerFields": [
                    {
                        "key": "points",
                        "label": "POINTS",
                        "value": ctx.points,
                    }
                ],
                "secondaryFields": [
                    {
                        "key": "reward",
                        "label": "NEXT REWARD AT",
                        "value": ctx.reward_threshold,
                    }
                ],
                "backFields": [
                    {
                        "key": "brand",
                        "label": "Brand",
                        "value": ctx.brand_name,
                    }
                ],
            },
            "barcode": {
                "message": ctx.serial_number,
                "format": "PKBarcodeFormatQR",
                "messageEncoding": "iso-8859-1",
            },
        }

    async def build(self, ctx: PassBuildContext) -> str:
        """
        Return the pass.json as a JSON string.

        In production this would be signed and returned as a .pkpass download
        URL stored in S3. The signing flow is:

        1. Download brand .p12 from S3 using ``ctx.apple_cert_s3_key``.
        2. Decrypt password with application APPLE_CERT_ENCRYPTION_KEY.
        3. Build manifest.json with SHA-1 hashes.
        4. Create PKCS#7 detached signature.
        5. Bundle into .pkpass ZIP.
        6. Upload to S3, return presigned URL.
        """
        if not ctx.apple_pass_type_id:
            logger.warning(
                "Brand %s has no apple_pass_type_id configured.", ctx.brand_slug
            )
        pass_dict = self._build_pass_json(ctx)
        # Placeholder: return serialized pass.json until cert is configured.
        return json.dumps(pass_dict)


async def build_apple_pass(ctx: PassBuildContext) -> str:
    """Module-level convenience wrapper."""
    return await ApplePassBuilder().build(ctx)
