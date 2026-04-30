import requests
from config import API_URL, MOCK_MODE, REQUEST_TIMEOUT
from auth.jwt_manager import jwt_manager
from datetime import datetime


MOCK_TRANSACTIONS = [
    {"id": "TXN-001", "date": "15 дек 2024", "recipient": 'ООО "Техком"', "amount": -12500.00, "status": "completed"},
    {"id": "TXN-002", "date": "14 дек 2024", "recipient": "Петров А.В.", "amount": 8750.00, "status": "completed"},
    {"id": "TXN-003", "date": "13 дек 2024", "recipient": 'Магазин "Элекс"', "amount": -3200.00, "status": "processing"},
    {"id": "TXN-004", "date": "12 дек 2024", "recipient": "Иванов С.П.", "amount": -1500.00, "status": "completed"},
    {"id": "TXN-005", "date": "11 дек 2024", "recipient": 'ЗАО "РосТех"', "amount": 25000.00, "status": "completed"},
    {"id": "TXN-006", "date": "10 дек 2024", "recipient": "Сидорова М.А.", "amount": -4800.00, "status": "failed"},
    {"id": "TXN-007", "date": "09 дек 2024", "recipient": 'ООО "АльфаСтрой"', "amount": -18300.00, "status": "processing"},
    {"id": "TXN-008", "date": "08 дек 2024", "recipient": "Козлов Д.И.", "amount": 3200.00, "status": "completed"},
]

MOCK_ACCOUNTS = [
    {"id": "ACC-001", "name": "Расчётный счёт", "number": "40702810000000001234", "balance": 45250.00, "currency": "RUB"},
    {"id": "ACC-002", "name": "Валютный счёт", "number": "40702840000000005678", "balance": 12800.00, "currency": "USD"},
    {"id": "ACC-003", "name": "Корреспондентский", "number": "40702978000000009012", "balance": 8500.00, "currency": "EUR"},
]


class ApiClient:
    def _headers(self) -> dict:
        return {"Content-Type": "application/json", **jwt_manager.get_header()}

    def _get(self, path: str) -> dict:
        resp = requests.get(f"{API_URL}{path}", headers=self._headers(), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        resp = requests.post(f"{API_URL}{path}", json=data, headers=self._headers(), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    # --- Auth ---

    def login(self, username: str, password: str) -> dict:
        if MOCK_MODE:
            if username and password:
                mock_token = (
                    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
                    "eyJzdWIiOiJ1c2VyMSIsIm5hbWUiOiLQkNC70LXQutGB"
                    "0LXQuSDQkC7Qki4iLCJyb2xlIjoi0J7Qv9C10YDQsNGC0L"
                    "jQstC90LjQuiIsImV4cCI6OTk5OTk5OTk5OX0."
                    "mock_signature"
                )
                return {"access_token": mock_token}
            raise ValueError("Неверный логин или пароль")
        return self._post("/api/auth/login", {"username": username, "password": password})

    # --- Dashboard ---

    def get_dashboard_stats(self) -> dict:
        if MOCK_MODE:
            return {
                "balance": 45250.00,
                "balance_change": 12.5,
                "transactions_count": 1234,
                "transactions_change": 8.2,
                "pending_count": 23,
                "pending_change": -2.1,
                "accounts_count": 8,
            }
        return self._get("/api/dashboard/stats")

    def get_recent_transactions(self) -> list:
        if MOCK_MODE:
            return MOCK_TRANSACTIONS[:3]
        return self._get("/api/transactions/recent")

    # --- Payments ---

    def send_payment(self, payload: dict) -> dict:
        if MOCK_MODE:
            return {"id": "TXN-NEW", "status": "processing", "message": "Платёж принят в обработку"}
        return self._post("/api/payments", payload)

    # --- History ---

    def get_transactions(self, filters: dict | None = None) -> list:
        if MOCK_MODE:
            return MOCK_TRANSACTIONS
        return self._get("/api/transactions")

    # --- Accounts ---

    def get_accounts(self) -> list:
        if MOCK_MODE:
            return MOCK_ACCOUNTS
        return self._get("/api/accounts")


api_client = ApiClient()
