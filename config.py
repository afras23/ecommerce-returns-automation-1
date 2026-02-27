import os
from dotenv import load_dotenv

load_dotenv()

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "mock-key")

RETURN_WINDOW_DAYS = 30