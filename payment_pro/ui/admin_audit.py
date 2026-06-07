import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PyQt6.QtCore import Qt
from datetime import datetime
from api.client import api_client
from ui.async_utils import run_async
from ui.responsive import configure_table


ACTION_LABELS = {
    "login": "Вход в систему",
    "logout": "Выход из системы",
    "register": "Регистрация",
    "payment_created": "Создан платёж",
    "payment_approved": "Платёж одобрен",
    "payment_rejected": "Платёж отклонён",
    "payment_cancelled": "Платёж отменён",
    "payment_completed": "Платёж завершён",
    "user_blocked": "Пользователь заблокирован",
    "user_unblocked": "Пользователь разблокирован",
    "user_created": "Создан пользователь",
    "user_updated": "Изменён пользователь",
    "limit_updated": "Изменены лимиты",
    "balance_updated": "Изменён баланс",
    "password_changed": "Изменён пароль",
}

ENTITY_LABELS = {
    "payment": "Платёж",
    "user": "Пользователь",
    "account": "Счёт",
    "session": "Сессия",
    "limit": "Лимит",
}


def _translate_action(action: str) -> str:
    if not action:
        return "—"
    key = action.lower().replace(" ", "_").replace("-", "_")
    return ACTION_LABELS.get(key, action)


def _format_details(raw) -> str:
    if not raw:
        return "—"
    if isinstance(raw, dict):
        obj = raw
    elif isinstance(raw, str):
        try:
            obj = json.loads(raw)
        except Exception:
            return raw
    else:
        return str(raw)
    FIELD_LABELS = {
        "amount": "Сумма",
        "status": "Статус",
        "reason": "Причина",
        "email": "Email",
        "role": "Роль",
        "daily_limit": "Лимит/день",
        "monthly_limit": "Лимит/месяц",
        "ip": "IP",
        "description": "Описание",
        "balance": "Баланс",
        "recipient_id": "Получатель ID",
        "sender_id": "Отправитель ID",
    }
    parts = []
    for k, v in obj.items():
        label = FIELD_LABELS.get(k, k)
        if k in ("amount", "daily_limit", "monthly_limit") and isinstance(v, (int, float)):
            v = f"₽ {v / 100:,.2f}"
        parts.append(f"{label}: {v}")
    return " | ".join(parts) if parts else "—"


def _translate_entity(entity_type: str, entity_id) -> str:
    if not entity_type:
        return "—"
    label = ENTITY_LABELS.get(entity_type.lower(), entity_type)
    if entity_id:
        return f"{label} #{entity_id}"
    return label


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso[:16]


class AdminAudit(QWidget):
    def __init__(self):
        super().__init__()
        self._entries = []
        self._user_map: dict[int, str] = {}
        self._load_worker = None
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        hdr = QHBoxLayout()
        self.count_label = QLabel("Журнал аудита")
        self.count_label.setObjectName("sectionTitle")

        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("filterButton")
        refresh_btn.setMinimumHeight(38)
        refresh_btn.setMinimumWidth(100)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._load_data)

        hdr.addWidget(self.count_label)
        hdr.addStretch()
        hdr.addWidget(refresh_btn)
        layout.addLayout(hdr)

        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Дата", "Действие", "Пользователь", "Объект", "Детали"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        configure_table(self.table, stretch_columns=(1, 4), min_height=300)
        card_layout.addWidget(self.table)

        layout.addWidget(card)

    def _load_data(self):
        self.count_label.setText("Журнал аудита (загрузка...)")
        self._load_worker = run_async(
            lambda: {
                "entries": api_client.get_admin_audit(),
                "user_map": api_client.get_user_map(),
            },
            on_success=self._on_loaded,
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _on_loaded(self, data: dict):
        self._entries = data.get("entries", [])
        self._user_map = data.get("user_map", {})
        self._render()

    def _render(self):
        self.count_label.setText(f"Журнал аудита ({len(self._entries)})")
        self.table.setRowCount(len(self._entries))

        for row, e in enumerate(self._entries):
            user_id = e.get("user_id")
            if user_id and user_id in self._user_map:
                user_str = self._user_map[user_id]
            elif user_id:
                user_str = f"ID {user_id}"
            else:
                user_str = e.get("user") or "—"

            action_str = _translate_action(e.get("action", ""))
            entity_str = _translate_entity(
                e.get("entity_type", ""),
                e.get("entity_id") or e.get("target"),
            )
            details_str = _format_details(e.get("details") or e.get("metadata"))

            items = [
                QTableWidgetItem(_fmt_dt(e.get("created_at") or e.get("timestamp"))),
                QTableWidgetItem(action_str),
                QTableWidgetItem(user_str),
                QTableWidgetItem(entity_str),
                QTableWidgetItem(details_str),
            ]

            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(2)
        self.table.resizeColumnToContents(3)
