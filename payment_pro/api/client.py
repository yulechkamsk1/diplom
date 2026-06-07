import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from datetime import datetime
from time import sleep
from threading import RLock
from config import API_URL, REQUEST_TIMEOUT
from auth.jwt_manager import jwt_manager

ACCOUNT_PREFIX = "4070281"
ACCOUNT_USER_ID_WIDTH = 13


def _wrap_network_error(exc: Exception) -> RuntimeError:
    if isinstance(exc, Timeout):
        return RuntimeError("Сервер не отвечает. Проверьте соединение и попробуйте позже.")
    if isinstance(exc, ConnectionError):
        return RuntimeError("Сервер недоступен. Попробуйте позже.")
    if isinstance(exc, RequestException):
        return RuntimeError(f"Ошибка соединения: {exc}")
    return RuntimeError(str(exc))


def account_number_to_user_id(account_number: str) -> int:
    account = str(account_number).strip()
    if len(account) != len(ACCOUNT_PREFIX) + ACCOUNT_USER_ID_WIDTH or not account.isdigit():
        raise ValueError("Номер счёта должен содержать 20 цифр")
    if not account.startswith(ACCOUNT_PREFIX):
        raise ValueError(f"Номер счёта должен начинаться с {ACCOUNT_PREFIX}")

    user_id = int(account[len(ACCOUNT_PREFIX):])
    if user_id <= 0:
        raise ValueError("В номере счёта указан некорректный получатель")
    return user_id


def user_id_to_account_number(user_id: int | str) -> str:
    return f"{ACCOUNT_PREFIX}{str(user_id).zfill(ACCOUNT_USER_ID_WIDTH)}"


def _read_api_error(resp) -> str:
    try:
        return resp.json().get("error", resp.text)
    except Exception:
        return resp.text


def _translate_api_error(message: str) -> str:
    lower = message.lower()
    if "payments_recipient_id_fkey" in lower or "sqlstate 23503" in lower:
        return "Получатель с таким счётом не найден. Проверьте номер счёта получателя."
    return message


STATUS_MAP = {
    "PENDING": "processing",
    "APPROVED": "processing",
    "COMPLETED": "completed",
    "REJECTED": "failed",
    "CANCELLED": "failed",
}

PAYMENT_STATUS_RU = {
    "PENDING": "Ожидает проверки",
    "APPROVED": "Одобрен",
    "COMPLETED": "Завершён",
    "REJECTED": "Отклонён",
    "CANCELLED": "Отменён",
}


def _fmt_date(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y")
    except Exception:
        return iso[:10]


class ApiClient:
    def __init__(self):
        self._session = requests.Session()
        self._session.trust_env = False  # ignore system proxy settings
        self._lock = RLock()
        self._cache: dict[tuple, object] = {}

    def _headers(self) -> dict:
        return {"Content-Type": "application/json", **jwt_manager.get_header()}

    def clear_cache(self) -> None:
        self._cache.clear()

    def _cache_get(self, key: tuple):
        return self._cache.get(key)

    def _cache_set(self, key: tuple, value: object):
        self._cache[key] = value
        return value

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        try:
            with self._lock:
                resp = self._session.get(
                    f"{API_URL}{path}",
                    headers=self._headers(),
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )
        except (Timeout, ConnectionError, RequestException) as e:
            raise _wrap_network_error(e)
        if not resp.ok:
            raise RuntimeError(_translate_api_error(_read_api_error(resp)))
        return resp.json()

    def _put(self, path: str, data: dict) -> dict:
        try:
            with self._lock:
                resp = self._session.put(
                    f"{API_URL}{path}", json=data, headers=self._headers(), timeout=REQUEST_TIMEOUT
                )
        except (Timeout, ConnectionError, RequestException) as e:
            raise _wrap_network_error(e)
        if not resp.ok:
            raise RuntimeError(_translate_api_error(_read_api_error(resp)))
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        try:
            with self._lock:
                resp = self._session.post(
                    f"{API_URL}{path}", json=data, headers=self._headers(), timeout=REQUEST_TIMEOUT
                )
        except (Timeout, ConnectionError, RequestException) as e:
            raise _wrap_network_error(e)
        if not resp.ok:
            raise RuntimeError(_translate_api_error(_read_api_error(resp)))
        return resp.json()

    # --- Auth ---

    def login(self, username: str, password: str) -> dict:
        resp = self._post("/api/auth/login", {"email": username, "password": password})
        jwt_manager.set_token(resp["token"])
        jwt_manager.set_user(resp.get("user", {}))
        self.clear_cache()
        return {"access_token": resp["token"]}

    def get_me(self) -> dict:
        key = ("me", jwt_manager.get_token())
        cached = self._cache_get(key)
        if cached:
            return cached
        return self._cache_set(key, self._get("/api/auth/me"))

    # --- Dashboard ---

    def get_dashboard_stats(self) -> dict:
        role = jwt_manager.get_role_key()
        if role == "BANKER":
            try:
                s = self.get_banker_stats()
                queue = self.get_banker_queue()
                return {
                    "approved_count": s.get("approved", 0),
                    "rejected_count": s.get("rejected", 0),
                    "total_decisions": s.get("total", 0),
                    "pending_count": len(queue),
                    "last_decision": s.get("last_decision"),
                }
            except Exception:
                pass
        if role == "ADMIN":
            try:
                s = self.get_admin_stats()
                payments = s.get("payments", {})
                bankers = s.get("bankers", [])
                return {
                    "total_payments": payments.get("total", 0),
                    "pending_payments": payments.get("pending", 0),
                    "approved_payments": payments.get("approved", 0),
                    "rejected_payments": payments.get("rejected", 0),
                    "completed_payments": payments.get("completed", 0),
                    "bankers_count": len(bankers),
                }
            except Exception:
                pass
        me = self.get_me()
        payments = self._get("/api/payments")
        pending = sum(1 for p in payments if p.get("status") == "PENDING")
        return {
            "balance": me.get("balance", 0) / 100,
            "balance_change": 0.0,
            "transactions_count": len(payments),
            "transactions_change": 0.0,
            "pending_count": pending,
            "pending_change": 0.0,
            "accounts_count": 1,
        }

    def get_recent_transactions(self) -> list:
        role = jwt_manager.get_role_key()
        if role == "ADMIN":
            return []
        if role == "BANKER":
            return []
        payments = self._get("/api/payments")
        return [self._normalize_payment(p) for p in payments[:3]]

    # --- Payments ---

    def _create_payment(self, recipient_id: int, amount: float, purpose: str) -> dict:
        amount_kopecks = int(float(amount) * 100)
        api_payload = {
            "recipient_id": recipient_id,
            "amount": amount_kopecks,
            "description": purpose,
            "payment_type": "SINGLE",
        }
        resp = self._post("/api/payments", api_payload)
        return {"id": str(resp.get("id", "N/A")), "status": resp.get("status", "")}

    def send_payment(self, payload: dict) -> dict:
        try:
            recipient_id = account_number_to_user_id(str(payload.get("recipient_account", "")))
        except ValueError as e:
            raise RuntimeError(str(e))

        return self._create_payment(recipient_id, payload.get("amount", 0), payload.get("purpose", ""))

    def send_payment_by_email(self, payload: dict) -> dict:
        email = str(payload.get("recipient_email", "")).strip().lower()
        if not email:
            raise RuntimeError("Укажите email получателя.")
        amount_kopecks = int(float(payload.get("amount", 0)) * 100)
        resp = self._post("/api/payments/by-email", {
            "recipient_email": email,
            "amount": amount_kopecks,
            "description": payload.get("purpose", ""),
            "payment_type": "SINGLE",
        })
        return {"id": str(resp.get("id", "N/A")), "status": resp.get("status", "")}

    def resolve_recipient_by_email(self, email: str) -> dict:
        needle = email.strip().lower()
        if not needle:
            raise RuntimeError("Укажите email получателя.")

        role = jwt_manager.get_role_key()
        if role == "ADMIN":
            users = self.get_admin_users(q=needle, role="CLIENT", limit=10)
        elif role == "BANKER":
            users = self.get_banker_clients(q=needle, limit=10)
        else:
            raise RuntimeError(
                "Сервер пока не даёт клиентам поиск получателя по email. "
                "Нужен backend endpoint для получения id клиента по email."
            )

        for user in users:
            if str(user.get("email", "")).strip().lower() == needle:
                return user

        raise RuntimeError("Клиент с таким email не найден.")

    def get_payment(self, payment_id: int | str) -> dict:
        return self._get(f"/api/payments/{payment_id}")

    def wait_payment_status(self, payment_id: int | str, attempts: int = 4, delay: float = 0.8) -> dict:
        payment = {}
        for _ in range(attempts):
            payment = self.get_payment(payment_id)
            if payment.get("status") != "PENDING":
                break
            sleep(delay)
        return payment

    # --- History ---

    def get_transactions(self, filters: dict | None = None) -> list:
        role = jwt_manager.get_role_key()
        if role == "BANKER":
            return self.get_banker_history()
        payments = self._get("/api/payments")
        payments.sort(key=lambda p: p.get("created_at") or "", reverse=True)
        return [self._normalize_payment(p) for p in payments]

    # --- Accounts ---

    def get_accounts(self) -> list:
        me = self.get_me()
        user_id = me.get("id", 1)
        balance_kopecks = me.get("balance", 0)
        number = user_id_to_account_number(user_id)
        return [{
            "id": f"ACC-{user_id}",
            "name": "Основной счёт",
            "number": number,
            "balance": balance_kopecks / 100,
            "currency": "RUB",
        }]

    # --- Banker ---

    def get_banker_queue(self) -> list:
        return self._get("/api/banker/queue")

    def approve_payment(self, payment_id: int) -> dict:
        return self._post(f"/api/banker/approve/{payment_id}", {})

    def reject_payment(self, payment_id: int, reason: str = "") -> dict:
        body = {"reason": reason} if reason else {}
        return self._post(f"/api/banker/reject/{payment_id}", body)

    def get_banker_clients(self, q: str = "", limit: int = 100) -> list:
        params = {"limit": limit}
        if q:
            params["q"] = q
        return self._get("/api/banker/clients", params=params)

    def get_banker_client(self, client_id: int) -> dict:
        return self._get(f"/api/banker/clients/{client_id}")

    def get_banker_history(self) -> list:
        payments = self._get("/api/banker/history")
        payments.sort(key=lambda p: p.get("created_at") or "", reverse=True)
        return [self._normalize_payment(p) for p in payments]

    def get_banker_stats(self) -> dict:
        key = ("banker_stats", jwt_manager.get_token())
        cached = self._cache_get(key)
        if cached:
            return cached
        return self._cache_set(key, self._get("/api/banker/stats"))

    # --- Admin ---

    def get_admin_users(self, q: str = "", role: str = "", limit: int = 100) -> list:
        params = {"limit": limit}
        if q:
            params["q"] = q
        if role:
            params["role"] = role
        return self._get("/api/admin/users", params=params)

    def create_admin_user(self, payload: dict) -> dict:
        return self._post("/api/admin/users", payload)

    def get_admin_stats(self) -> dict:
        key = ("admin_stats", jwt_manager.get_token())
        cached = self._cache_get(key)
        if cached:
            return cached
        return self._cache_set(key, self._get("/api/admin/stats"))

    def get_admin_audit(self) -> list:
        return self._get("/api/admin/audit")

    def get_admin_banker_history(self, banker_id: int) -> list:
        return self._get(f"/api/admin/bankers/{banker_id}/history")

    def get_admin_client_history(self, client_id: int) -> list:
        return self._get(f"/api/admin/clients/{client_id}/history")

    def block_user(self, user_id: int) -> dict:
        return self._put(f"/api/admin/users/{user_id}/block", {})

    def unblock_user(self, user_id: int) -> dict:
        return self._put(f"/api/admin/users/{user_id}/unblock", {})

    # --- User map (id -> full_name) ---

    def get_user_map(self) -> dict[int, str]:
        role = jwt_manager.get_role_key()
        try:
            if role == "ADMIN":
                users = self._get("/api/admin/users")
            elif role == "BANKER":
                users = self._get("/api/banker/clients")
            else:
                return {}
            return {u["id"]: u.get("full_name") or f"ID {u['id']}" for u in users if u.get("id")}
        except Exception:
            return {}

    def update_user_limits(self, user_id: int, daily_limit: int, monthly_limit: int) -> dict:
        return self._put(f"/api/admin/users/{user_id}/limits", {
            "daily_limit": daily_limit,
            "monthly_limit": monthly_limit,
        })

    # --- Internal helpers ---

    def _normalize_payment(self, payment: dict) -> dict:
        me_id = jwt_manager.get_user_id()
        sender_id = payment.get("sender_id")
        amount_rub = payment.get("amount", 0) / 100
        if sender_id and sender_id == me_id:
            amount_rub = -amount_rub

        recipient_id = payment.get("recipient_id")
        recipient_label = f"Получатель #{recipient_id}" if recipient_id else "—"

        return {
            "id": str(payment.get("id", "")),
            "date": _fmt_date(payment.get("created_at")),
            "created_at": payment.get("created_at") or "",
            "recipient": recipient_label,
            "recipient_id": recipient_id,
            "amount": amount_rub,
            "status": STATUS_MAP.get(payment.get("status", ""), "processing"),
            "rejection_reason": payment.get("rejection_reason") or "",
        }


api_client = ApiClient()
