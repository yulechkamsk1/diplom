from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from api.client import api_client

ROLE_LABELS = {"CLIENT": "Клиент", "BANKER": "Банкир", "ADMIN": "Администратор"}


class AdminUsers(QWidget):
    def __init__(self):
        super().__init__()
        self._users = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        hdr = QHBoxLayout()
        self.count_label = QLabel("Пользователи")
        self.count_label.setObjectName("sectionTitle")

        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("filterButton")
        refresh_btn.setMinimumHeight(38)
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
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "ФИО", "Email", "Роль", "Баланс", "Лимит/день", "Статус", "Действия"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setMinimumHeight(300)
        card_layout.addWidget(self.table)

        layout.addWidget(card)

    def _load_data(self):
        try:
            self._users = api_client.get_admin_users()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self._render()

    def _render(self):
        self.count_label.setText(f"Пользователи ({len(self._users)})")
        self.table.setRowCount(len(self._users))

        for row, u in enumerate(self._users):
            balance = u.get("balance", 0) / 100
            daily = u.get("daily_limit", 0) / 100
            is_blocked = u.get("is_blocked", False)
            role_raw = u.get("role", "")

            items = [
                QTableWidgetItem(str(u.get("id", ""))),
                QTableWidgetItem(u.get("full_name", "—")),
                QTableWidgetItem(u.get("email", "—")),
                QTableWidgetItem(ROLE_LABELS.get(role_raw, role_raw or "—")),
                QTableWidgetItem(f"₽ {balance:,.2f}"),
                QTableWidgetItem(f"₽ {daily:,.2f}"),
                QTableWidgetItem("Заблокирован" if is_blocked else "Активен"),
            ]
            items[4].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[5].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[6].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_blocked:
                items[6].setForeground(QColor("#EF4444"))

            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

            user_id = u.get("id")
            action_btn = QPushButton("Разблокировать" if is_blocked else "Заблокировать")
            action_btn.setStyleSheet(
                "QPushButton { border-radius: 6px; padding: 4px 10px; font-size: 12px; "
                + ("color: #10B981; background: #DCFCE7; border: 1px solid #10B98144; }"
                   "QPushButton:hover { background: #BBF7D0; }"
                   if is_blocked else
                   "color: #EF4444; background: #FEE2E2; border: 1px solid #EF444444; }"
                   "QPushButton:hover { background: #FECACA; }")
            )
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.clicked.connect(
                lambda _, uid=user_id, blocked=is_blocked: self._toggle_block(uid, blocked)
            )
            self.table.setCellWidget(row, 7, action_btn)
            self.table.setRowHeight(row, 48)

        for col in [0, 3, 5, 6, 7]:
            self.table.resizeColumnToContents(col)

    def _toggle_block(self, user_id: int, is_blocked: bool):
        action = "разблокировать" if is_blocked else "заблокировать"
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Вы уверены, что хотите {action} пользователя #{user_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            if is_blocked:
                api_client.unblock_user(user_id)
            else:
                api_client.block_user(user_id)
            self._load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
