"""Released public support keys; private keys must never be added here.

Product activation is a deliberate source change reviewed with the public
descriptor created by the offline provisioning tool. Registry format 1
requires an upper time bound; year 9999 represents no scheduled expiry.
"""

from __future__ import annotations


PRODUCT_SUPPORT_KEY_REGISTRY = {
    "format_version": 1,
    "keys": (
        {
            "key_id": "support-2026-b",
            "algorithm": "Ed25519",
            "public_key": "qjrZixhRuZd7dGXIvpchvWAdGwGhtlFm2mVTHB0XVUU",
            "status": "active",
            "not_before": "2026-07-19T22:12:15Z",
            "not_after": "9999-12-31T23:59:59Z",
            "revoked_at": None,
            "fingerprint_sha256": (
                "76e619df93483de9313d5bf592fc852c"
                "88f1ba7ac5261018801c0fcd5e96be77"
            ),
        },
    ),
}
