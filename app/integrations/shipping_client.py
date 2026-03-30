"""
Shipping integration stub: label generation.

Replace with a real carrier API client in production.
"""

import logging
import uuid

logger = logging.getLogger(__name__)


def generate_label(return_id: str) -> dict:
    """
    Create a shipping label for the given return (mock implementation).

    Args:
        return_id: Internal return identifier.

    Returns:
        Dict with mock label metadata (tracking id, carrier, label URL placeholder).
    """
    tracking = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
    payload = {
        "return_id": return_id,
        "carrier": "mock_carrier",
        "tracking_number": tracking,
        "label_url": f"https://example.com/labels/{return_id}",
        "status": "created",
    }
    logger.info(
        "shipping_label_generated",
        extra={"return_id": return_id, "tracking_number": tracking},
    )
    return payload
