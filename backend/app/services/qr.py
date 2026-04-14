from __future__ import annotations

import io

import qrcode
from qrcode.image.pil import PilImage


def generate_qr_bytes(data: str, box_size: int = 10, border: int = 4) -> bytes:
    """
    Generate a PNG QR code for *data* and return it as raw bytes.

    Parameters
    ----------
    data:
        The string to encode (e.g. a URL or serial number).
    box_size:
        Pixel size of each QR module.
    border:
        Number of module-sized quiet-zone modules around the code.
    """
    qr = qrcode.QRCode(
        version=None,  # auto-determine version
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img: PilImage = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def enrollment_url(base_url: str, qr_token: str) -> str:
    """Return the public enrollment URL that gets embedded in the counter QR code."""
    return f"{base_url.rstrip('/')}/enroll/{qr_token}"


def pass_qr_content(serial_number: str) -> str:
    """
    Return the string encoded in the QR on the customer's pass.

    We use a plain serial number so any backend can resolve it; the
    mobile wallet app does not need an internet connection to display the QR.
    """
    return serial_number
