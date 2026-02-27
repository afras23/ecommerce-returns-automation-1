import json
from models.return_request import ReturnRequest
from config import CLAUDE_API_KEY
from utils.logger import log

def extract_return_data(email_text: str) -> ReturnRequest:
    log("Extracting structured data using AI model...")

    if CLAUDE_API_KEY == "mock-key":
        log("Using mock AI extraction.")
        return ReturnRequest(
            order_id="12345",
            reason="Item arrived damaged",
            preference="refund",
            purchase_date="2026-02-01",
            damaged=True
        )

    # If using real Claude:
    # Implement anthropic client here if desired.

    raise NotImplementedError("Real API integration not configured.")