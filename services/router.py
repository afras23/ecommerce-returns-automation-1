from utils.logger import log

def route_request(return_request, eligible: bool):
    log("Routing return request...")

    if not eligible:
        return "outside_window_review"

    if return_request.damaged:
        return "damage_claim_review"

    if return_request.reason.lower() == "wrong item":
        return "warehouse_investigation"

    return "standard_processing"