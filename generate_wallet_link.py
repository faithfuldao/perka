import json
import time
import httpx
import google.auth.crypt
import google.auth.jwt
import google.oauth2.service_account
import google.auth.transport.requests

SERVICE_ACCOUNT_JSON = "backend/perka-493308-5232764f250e.json"
ISSUER_ID = "3388000000023114440"
CLASS_ID = f"{ISSUER_ID}.Unusual_Loyalt7"
OBJECT_ID = f"{ISSUER_ID}.victor_test_7"

with open(SERVICE_ACCOUNT_JSON) as f:
    sa = json.load(f)

# Authenticated HTTP client
credentials = google.oauth2.service_account.Credentials.from_service_account_info(
    sa,
    scopes=["https://www.googleapis.com/auth/wallet_object.issuer"]
)
credentials.refresh(google.auth.transport.requests.Request())
headers = {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}

# Create the pass object if it doesn't exist yet
object_payload = {
    "id": OBJECT_ID,
    "classId": CLASS_ID,
    "state": "ACTIVE",
    "accountId": "victor_test",
    "accountName": "Victor",
    "loyaltyPoints": {
        "balance": {"int": 0},
        "label": "스탬프"
    },
}

STAMP_IMAGE_URL = "https://raw.githubusercontent.com/FaithfulDao/perka/master/public/goldenRetreiverIcon.png"
LOGO_URL        = "https://raw.githubusercontent.com/FaithfulDao/perka/master/public/unusualFinalIcon.jpg"
PRIMARY_COLOR   = "#F9D3F9"#b47dcb
REWARD_THRESHOLD = 10

class_payload = {
    "id": CLASS_ID,
    "issuerName": "Unusual",
    "programName": "포인트 적립",
    "reviewStatus": "underReview",
    "rewardsTierLabel": "Collect stamps",
    "rewardsTier": f"Free reward at {REWARD_THRESHOLD} stamps",
    "hexBackgroundColor": PRIMARY_COLOR,
    "programLogo": {
        "sourceUri": {"uri": LOGO_URL},
        "contentDescription": {"defaultValue": {"language": "en-US", "value": "UNUSUAL"}},
    },
    "heroImage": {
        "sourceUri": {"uri": LOGO_URL},
        "contentDescription": {"defaultValue": {"language": "en-US", "value": "UNUSUAL"}},
    },
    "wordMark": {
        "sourceUri": {"uri": LOGO_URL},
        "contentDescription": {"defaultValue": {"language": "en-US", "value": "UNUSUAL"}},
    },
}

# Verify class exists, create it if not
rc = httpx.get(
    f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass/{CLASS_ID}",
    headers=headers
)
print(f"Class check: {rc.status_code} — ID used: {CLASS_ID}")
if rc.status_code == 404:
    rc = httpx.post(
        "https://walletobjects.googleapis.com/walletobjects/v1/loyaltyClass",
        headers=headers,
        json=class_payload,
    )
    if rc.status_code not in (200, 201):
        print(f"Failed to create class: {rc.status_code} {rc.text}")
        exit(1)
    print("Class created.")
elif rc.status_code != 200:
    print(f"Unexpected error checking class: {rc.text}")
    exit(1)
else:
    print("Class already exists.")

# Always overwrite the object with correct data
r = httpx.get(
    f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{OBJECT_ID}",
    headers=headers
)
if r.status_code == 404:
    r = httpx.post(
        "https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject",
        headers=headers,
        json=object_payload
    )
    action = "created"
else:
    r = httpx.put(
        f"https://walletobjects.googleapis.com/walletobjects/v1/loyaltyObject/{OBJECT_ID}",
        headers=headers,
        json=object_payload
    )
    action = "updated"

if r.status_code not in (200, 201):
    print(f"Failed to {action} object: {r.status_code} {r.text}")
    exit(1)
print(f"Pass object {action}.")

# Generate the Save to Wallet JWT
signer = google.auth.crypt.RSASigner.from_service_account_info(sa)
jwt_payload = {
    "iss": sa["client_email"],
    "aud": "google",
    "typ": "savetowallet",
    "iat": int(time.time()),
    "payload": {
        "loyaltyObjects": [{"id": OBJECT_ID}]
    },
    "origins": []
}

import qrcode

token = google.auth.jwt.encode(signer, jwt_payload).decode("utf-8")
save_url = f"https://pay.google.com/gp/v/save/{token}"

qr = qrcode.make(save_url)
qr.save("wallet_qr.png")

print(f"\nLink: {save_url}")
print("QR code saved to wallet_qr.png — scan it with your phone to add the pass.\n")
