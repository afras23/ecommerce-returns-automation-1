from utils.logger import log

def generate_return_label(order_id: str):
    log("Generating return label (mock)...")

    label_content = f"""
    RETURN LABEL
    Order ID: {order_id}
    Ship To: Warehouse A
    """

    filename = f"return_label_{order_id}.txt"

    with open(filename, "w") as f:
        f.write(label_content)

    return filename