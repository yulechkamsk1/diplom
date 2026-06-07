from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
)
from PyQt6.QtCore import Qt
from api.client import api_client
from ui.async_utils import run_async


class Settings(QWidget):
    def __init__(self):
        super().__init__()
        self._load_worker = None
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        card = QFrame()
        card.setObjectName("sectionCard")
        card.setMinimumWidth(300)
        card.setMaximumWidth(640)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(0)

        title = QLabel("Профиль пользователя")
        title.setObjectName("sectionTitle")
        card_layout.addWidget(title)
        card_layout.addSpacing(16)

        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(0)
        card_layout.addLayout(self.rows_layout)

        layout.addWidget(card)
        layout.addStretch()

    def _load_data(self):
        self._add_row("Профиль", "Загрузка...")
        self._load_worker = run_async(
            api_client.get_me,
            on_success=self._render_profile,
            on_error=lambda msg: self._add_row("Ошибка загрузки", msg, error=True),
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _render_profile(self, me: dict):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                while item.layout().count():
                    nested = item.layout().takeAt(0)
                    if nested.widget():
                        nested.widget().deleteLater()

        balance = me.get("balance", 0) / 100
        daily = me.get("daily_limit", 0) / 100
        monthly = me.get("monthly_limit", 0) / 100

        rows = [
            ("ФИО",               me.get("full_name", "—")),
            ("Email",             me.get("email", "—")),
            ("Телефон",           me.get("phone") or "—"),
            ("Баланс",            f"₽ {balance:,.2f}"),
            ("Дневной лимит",     f"₽ {daily:,.2f}"),
            ("Месячный лимит",    f"₽ {monthly:,.2f}"),
        ]

        for label, value in rows:
            self._add_row(label, value)

    def _add_row(self, label: str, value: str, error: bool = False):
        row = QHBoxLayout()
        row.setContentsMargins(0, 12, 0, 12)

        lbl = QLabel(label)
        lbl.setObjectName("fieldLabel")
        lbl.setMinimumWidth(130)
        lbl.setMaximumWidth(180)

        val = QLabel(value)
        if error:
            val.setStyleSheet("color: #EF4444;")

        row.addWidget(lbl)
        row.addWidget(val)
        row.addStretch()

        self.rows_layout.addLayout(row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #F1F5F9;")
        self.rows_layout.addWidget(divider)
