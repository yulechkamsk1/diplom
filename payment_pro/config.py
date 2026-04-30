from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
APP_NAME = "PaymentPro"
APP_VERSION = "1.0.0"
