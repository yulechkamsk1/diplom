import jwt
from config import JWT_SECRET


class JwtManager:
    def __init__(self):
        self._token: str | None = None
        self._payload: dict = {}

    def set_token(self, token: str) -> None:
        self._token = token
        try:
            self._payload = jwt.decode(token, options={"verify_signature": False})
        except Exception:
            self._payload = {}

    def get_token(self) -> str | None:
        return self._token

    def get_header(self) -> dict:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def get_username(self) -> str:
        return self._payload.get("name", self._payload.get("sub", "Пользователь"))

    def get_role(self) -> str:
        return self._payload.get("role", "Оператор")

    def is_authenticated(self) -> bool:
        return self._token is not None

    def clear(self) -> None:
        self._token = None
        self._payload = {}


jwt_manager = JwtManager()
