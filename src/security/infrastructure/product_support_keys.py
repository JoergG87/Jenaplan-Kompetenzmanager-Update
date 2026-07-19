"""Released public support keys; private keys must never be added here.

Product activation is a deliberate source change reviewed with the public
descriptor created by the offline provisioning tool.  The empty tuple keeps
the application fail-closed until the Product Owner supplies that descriptor.
"""

from __future__ import annotations


PRODUCT_SUPPORT_KEY_REGISTRY = {
    "format_version": 1,
    "keys": (),
}
