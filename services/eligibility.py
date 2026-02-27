from datetime import datetime
from config import RETURN_WINDOW_DAYS
from utils.logger import log

def check_eligibility(purchase_date: str):
    log("Checking eligibility window...")

    purchase = datetime.strptime(purchase_date, "%Y-%m-%d")
    today = datetime.now()

    delta = (today - purchase).days

    if delta <= RETURN_WINDOW_DAYS:
        log("Return is within window.")
        return True
    else:
        log("Return outside allowed window.")
        return False