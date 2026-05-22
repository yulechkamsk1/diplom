import jwt


ROLE_LABELS = {
    "CLIENT": "Клиент",
    "BANKER": "Банкир",
    "ADMIN": "Администратор",
}


class JwtManager:
    def __init__(self):
        self._token: str | None = None
        self._payload: dict = {}
        self._user: dict = {}

    def set_token(self, token: str) -> None:
        self._token = token
        try:
            self._payload = jwt.decode(token, options={"verify_signature": False})
        except Exception:
            self._payload = {}

    def set_user(self, user: dict) -> None:
        self._user = user

    def get_token(self) -> str | None:
        return self._token

    def get_header(self) -> dict:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def get_username(self) -> str:
        return (
            self._user.get("full_name")
            or self._payload.get("name")
            or self._payload.get("sub", "Пользователь")
        )

    def get_role(self) -> str:
        raw = self._user.get("role") or self._payload.get("role", "")
        return ROLE_LABELS.get(raw, raw or "Оператор")

    def get_role_key(self) -> str:
        return self._user.get("role") or self._payload.get("role", "CLIENT")

    def get_user_id(self) -> int | None:
        return self._user.get("id") or self._payload.get("id")

    def is_authenticated(self) -> bool:
        return self._token is not None

    def clear(self) -> None:
        self._token = None
        self._payload = {}
        self._user = {}


jwt_manager = JwtManager()
