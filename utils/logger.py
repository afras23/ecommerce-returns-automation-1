import datetime

def log(message: str):
    timestamp = datetime.datetime.now().isoformat()
    print(f"[{timestamp}] {message}")