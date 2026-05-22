from dotenv import load_dotenv
import os

load_dotenv()

API_URL = os.getenv("API_URL", "http://217.144.184.124")
MOCK_MODE = False
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
JWT_SECRET = os.getenv("JWT_SECRET", "wdqTMbBWv5ROvvhjg9MCBc3O4xGuXKXqyPjDHEaBHavOO1LhZgSoij9wVQx4rk8G")
APP_NAME = "PaymentPro"
APP_VERSION = "1.0.0"
