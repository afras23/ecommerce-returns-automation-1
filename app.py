from services.ai_extractor import extract_return_data
from services.eligibility import check_eligibility
from services.router import route_request
from services.label_generator import generate_return_label
from services.inventory import update_inventory
from utils.logger import log

def load_email():
    with open("data/sample_email.txt", "r") as f:
        return f.read()

def main():
    log("Starting E-commerce Returns Automation...")

    email_text = load_email()

    return_request = extract_return_data(email_text)

    eligible = check_eligibility(return_request.purchase_date)

    route = route_request(return_request, eligible)

    log(f"Route decision: {route}")

    if route == "standard_processing":
        label_file = generate_return_label(return_request.order_id)
        update_inventory(return_request.order_id)
        log(f"Return processed successfully. Label: {label_file}")

    else:
        log(f"Escalated to: {route}")

if __name__ == "__main__":
    main()