import requests
from requests.exceptions import ConnectionError, Timeout, RequestException
from datetime import datetime
from config import API_URL, REQUEST_TIMEOUT
from auth.jwt_manager import jwt_manager


def _wrap_network_error(exc: Exception) -> RuntimeError:
    if isinstance(exc, Timeout):
        return RuntimeError("Сервер не отвечает. Проверьте соединение и попробуйте позже.")
    if isinstance(exc, ConnectionError):
        return RuntimeError("Сервер недоступен. Попробуйте позже.")
    if isinstance(exc, RequestException):
        return RuntimeError(f"Ошибка соединения: {exc}")
    return RuntimeError(str(exc))


STATUS_MAP = {
    "PENDING": "processing",
    "APPROVED": "processing",
    "COMPLETED": "completed",
    "REJECTED": "failed",
    "CANCELLED": "failed",
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
    def _headers(self) -> dict:
        return {"Content-Type": "application/json", **jwt_manager.get_header()}

    def _get(self, path: str) -> dict | list:
        try:
            resp = requests.get(f"{API_URL}{path}", headers=self._headers(), timeout=REQUEST_TIMEOUT)
        except (Timeout, ConnectionError, RequestException) as e:
            raise _wrap_network_error(e)
        if not resp.ok:
            try:
                err = resp.json().get("error", resp.text)
            except Exception:
                err = resp.text
            raise RuntimeError(err)
        return resp.json()

    def _put(self, path: str, data: dict) -> dict:
        try:
            resp = requests.put(f"{API_URL}{path}", json=data, headers=self._headers(), timeout=REQUEST_TIMEOUT)
        except (Timeout, ConnectionError, RequestException) as e:
            raise _wrap_network_error(e)
        if not resp.ok:
            try:
                err = resp.json().get("error", resp.text)
            except Exception:
                err = resp.text
            raise RuntimeError(err)
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        try:
            resp = requests.post(f"{API_URL}{path}", json=data, headers=self._headers(), timeout=REQUEST_TIMEOUT)
        except (Timeout, ConnectionError, RequestException) as e:
            raise _wrap_network_error(e)
        if not resp.ok:
            try:
                err = resp.json().get("error", resp.text)
            except Exception:
                err = resp.text
            raise RuntimeError(err)
        return resp.json()

    # --- Auth ---

    def login(self, username: str, password: str) -> dict:
        resp = self._post("/api/auth/login", {"email": username, "password": password})
        jwt_manager.set_token(resp["token"])
        jwt_manager.set_user(resp.get("user", {}))
        return {"access_token": resp["token"]}

    def get_me(self) -> dict:
        return self._get("/api/auth/me")

    # --- Dashboard ---

    def get_dashboard_stats(self) -> dict:
        role = jwt_manager.get_role_key()
        if role == "BANKER":
            try:
                s = self.get_banker_stats()
                queue = self.get_banker_queue()
                return {
                    "balance": 0.0,
                    "balance_change": 0.0,
                    "transactions_count": s.get("total", 0),
                    "transactions_change": 0.0,
                    "pending_count": len(queue),
                    "pending_change": 0.0,
                    "accounts_count": s.get("approved", 0),
                }
            except Exception:
                pass
        if role == "ADMIN":
            try:
                s = self.get_admin_stats()
                return {
                    "balance": 0.0,
                    "balance_change": 0.0,
                    "transactions_count": s.get("total_payments", 0),
                    "transactions_change": 0.0,
                    "pending_count": s.get("pending_payments", 0),
                    "pending_change": 0.0,
                    "accounts_count": s.get("total_users", 0),
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
        if role == "BANKER":
            try:
                return self.get_banker_history()[:3]
            except Exception:
                return []
        payments = self._get("/api/payments")
        return [self._normalize_payment(p) for p in payments[:3]]

    # --- Payments ---

    def send_payment(self, payload: dict) -> dict:
        recipient_raw = str(payload.get("recipient_account", "1"))
        try:
            # Extract last 6 digits as recipient user ID
            recipient_id = int(recipient_raw[-6:].lstrip("0") or "1")
        except (ValueError, TypeError):
            recipient_id = 1

        amount_kopecks = int(float(payload.get("amount", 0)) * 100)

        api_payload = {
            "recipient_id": recipient_id,
            "amount": amount_kopecks,
            "description": payload.get("purpose", ""),
            "payment_type": "SINGLE",
        }
        resp = self._post("/api/payments", api_payload)
        return {"id": str(resp.get("id", "N/A")), "status": resp.get("status", "")}

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
        number = f"4070281{str(user_id).zfill(13)}"
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

    def get_banker_clients(self) -> list:
        return self._get("/api/banker/clients")

    def get_banker_client(self, client_id: int) -> dict:
        return self._get(f"/api/banker/clients/{client_id}")

    def get_banker_history(self) -> list:
        payments = self._get("/api/banker/history")
        payments.sort(key=lambda p: p.get("created_at") or "", reverse=True)
        return [self._normalize_payment(p) for p in payments]

    def get_banker_stats(self) -> dict:
        return self._get("/api/banker/stats")

    # --- Admin ---

    def get_admin_users(self) -> list:
        return self._get("/api/admin/users")

    def get_admin_stats(self) -> dict:
        return self._get("/api/admin/stats")

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

    # --- Internal helpers ---

    def _normalize_payment(self, payment: dict) -> dict:
        me_id = jwt_manager.get_user_id()
        sender_id = payment.get("sender_id")
        amount_rub = payment.get("amount", 0) / 100
        if sender_id and sender_id == me_id:
            amount_rub = -amount_rub

        return {
            "id": str(payment.get("id", "")),
            "date": _fmt_date(payment.get("created_at")),
            "created_at": payment.get("created_at") or "",
            "recipient": f"Получатель #{payment.get('recipient_id', '?')}",
            "amount": amount_rub,
            "status": STATUS_MAP.get(payment.get("status", ""), "processing"),
        }


api_client = ApiClient()
