"""
Versioned prompt templates for AI-assisted return workflows.

Each name encodes the task and version (e.g. `_v1`) so changes are explicit.
"""

# --- return_reason_classification_v1 ---
RETURN_REASON_CLASSIFICATION_V1 = """You are a returns classifier for an ecommerce merchant.
Given the customer's free-text return reason, output exactly one category from:
damaged, wrong_item, not_as_described, sizing, buyer_remorse, other.
Respond with JSON only: {"category": "<name>", "confidence": <0.0-1.0>}.
"""

# --- product_condition_extraction_v1 ---
PRODUCT_CONDITION_EXTRACTION_V1 = (
    "You extract structured product condition signals from return notes.\n"
    "Output JSON only with keys: has_damage (bool), "
    "damage_description (string or null),\n"
    "wear_level (new|light|moderate|heavy|unknown)."
)

# --- customer_communication_v1 ---
CUSTOMER_COMMUNICATION_V1 = (
    "You draft concise, policy-compliant customer messages for return outcomes.\n"
    "Tone: professional, empathetic, no legal promises. "
    "Output plain text body only."
)

# Registry for programmatic lookup by stable id
PROMPTS: dict[str, str] = {
    "return_reason_classification_v1": RETURN_REASON_CLASSIFICATION_V1,
    "product_condition_extraction_v1": PRODUCT_CONDITION_EXTRACTION_V1,
    "customer_communication_v1": CUSTOMER_COMMUNICATION_V1,
}
