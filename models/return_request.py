from pydantic import BaseModel
from typing import Optional

class ReturnRequest(BaseModel):
    order_id: str
    reason: str
    preference: str  # refund or exchange
    purchase_date: str
    damaged: Optional[bool] = False