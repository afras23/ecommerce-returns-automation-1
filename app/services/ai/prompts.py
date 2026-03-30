"""
Versioned prompt templates for AI-assisted return workflows.

Each name encodes the task and version (e.g. `_v1`) so changes are explicit.
"""

# --- return_reason_classification_v2 (structured output) ---
RETURN_REASON_CLASSIFICATION_V2 = """You classify ecommerce return reasons.
Given the customer's free-text description, respond with JSON ONLY (no markdown) using this schema:
{"reason":"<one of>","confidence":<0.0-1.0>,"raw":"<verbatim user text>"}
Allowed values for "reason": damaged, wrong_item, no_longer_needed, defective, other.
"confidence" is your certainty in [0.0,1.0]. "raw" must echo the input description.
"""

# --- product_condition_extraction_v2 ---
PRODUCT_CONDITION_EXTRACTION_V2 = """You assess product condition for returns from notes.
Respond with JSON ONLY (no markdown):
{"condition":"<one of>","confidence":<0.0-1.0>}
Allowed "condition": unopened, opened_unused, used, damaged_by_customer.
Pick exactly one. confidence in [0.0,1.0].
"""

# --- Legacy / registry aliases ---
RETURN_REASON_CLASSIFICATION_V1 = RETURN_REASON_CLASSIFICATION_V2
PRODUCT_CONDITION_EXTRACTION_V1 = PRODUCT_CONDITION_EXTRACTION_V2

# --- customer_communication_v1 ---
CUSTOMER_COMMUNICATION_V1 = (
    "You draft concise, policy-compliant customer messages for return outcomes.\n"
    "Tone: professional, empathetic, no legal promises. "
    "Output plain text body only."
)

# Registry for programmatic lookup by stable id
PROMPTS: dict[str, str] = {
    "return_reason_classification_v1": RETURN_REASON_CLASSIFICATION_V1,
    "return_reason_classification_v2": RETURN_REASON_CLASSIFICATION_V2,
    "product_condition_extraction_v1": PRODUCT_CONDITION_EXTRACTION_V1,
    "product_condition_extraction_v2": PRODUCT_CONDITION_EXTRACTION_V2,
    "customer_communication_v1": CUSTOMER_COMMUNICATION_V1,
}
