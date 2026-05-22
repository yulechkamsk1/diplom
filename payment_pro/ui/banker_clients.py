from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QDialogButtonBox, QLineEdit, QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from api.client import api_client, _fmt_date, user_id_to_account_number
from ui.async_utils import run_async
from ui.responsive import configure_table


def _rub(kopecks: int | float | None) -> str:
    return f"₽ {(kopecks or 0) / 100:,.2f}"


class BankerClients(QWidget):
    def __init__(self):
        super().__init__()
        self._clients = []
        self._load_worker = None
        self._detail_worker = None
        self._load_seq = 0
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)
        self._search_timer.timeout.connect(self._load_data)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        hdr = QHBoxLayout()
        self.count_label = QLabel("Клиенты")
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

        search_card = QFrame()
        search_card.setObjectName("sectionCard")
        search_layout = QHBoxLayout(search_card)
        search_layout.setContentsMargins(20, 16, 20, 16)
        search_layout.setSpacing(12)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по ID, ФИО, email или телефону")
        self.search_edit.setMinimumHeight(38)
        self.search_edit.returnPressed.connect(self._load_data)
        self.search_edit.textChanged.connect(lambda _: self._schedule_load())

        search_btn = QPushButton("Найти")
        search_btn.setObjectName("filterButton")
        search_btn.setMinimumHeight(38)
        search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        search_btn.clicked.connect(self._load_data)

        clear_btn = QPushButton("Сброс")
        clear_btn.setObjectName("exportButton")
        clear_btn.setMinimumHeight(38)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_search)

        search_layout.addWidget(self.search_edit, stretch=1)
        search_layout.addWidget(search_btn)
        search_layout.addWidget(clear_btn)
        layout.addWidget(search_card)

        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["ID", "Счёт", "ФИО", "Email", "Телефон", "Баланс", "Статус", ""])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        configure_table(self.table, stretch_columns=(2, 3), min_height=300)
        card_layout.addWidget(self.table)

        layout.addWidget(card)

    def _clear_search(self):
        self.search_edit.clear()
        self._load_data()

    def _load_data(self):
        self._load_seq += 1
        seq = self._load_seq
        q = self.search_edit.text().strip()
        self.count_label.setText("Клиенты (загрузка...)")
        self._load_worker = run_async(
            lambda: api_client.get_banker_clients(q=q),
            on_success=lambda clients, s=seq: self._on_clients_loaded(s, clients),
            on_error=lambda msg, s=seq: self._on_load_error(s, msg),
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _schedule_load(self):
        self._search_timer.start()

    def _on_clients_loaded(self, seq: int, clients: list):
        if seq != self._load_seq:
            return
        self._clients = clients
        self._render()

    def _on_load_error(self, seq: int, msg: str):
        if seq != self._load_seq:
            return
        QMessageBox.critical(self, "Ошибка", msg)

    def _render(self):
        self.count_label.setText(f"Клиенты ({len(self._clients)})")
        self.table.setRowCount(len(self._clients))

        for row, c in enumerate(self._clients):
            user_id = c.get("id", "")
            is_blocked = c.get("is_blocked", False)

            items = [
                QTableWidgetItem(str(user_id)),
                QTableWidgetItem(user_id_to_account_number(user_id) if user_id != "" else "—"),
                QTableWidgetItem(c.get("full_name", "—")),
                QTableWidgetItem(c.get("email", "—")),
                QTableWidgetItem(c.get("phone") or "—"),
                QTableWidgetItem(_rub(c.get("balance", 0))),
                QTableWidgetItem("Заблокирован" if is_blocked else "Активен"),
            ]
            items[5].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[6].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_blocked:
                items[6].setForeground(QColor("#EF4444"))

            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

            detail_btn = QPushButton("Подробнее")
            detail_btn.setStyleSheet(
                "QPushButton { border: 1px solid #E2E8F0; border-radius: 6px; "
                "padding: 4px 12px; font-size: 12px; color: #3B82F6; background: #EFF6FF; }"
                "QPushButton:hover { background: #DBEAFE; }"
            )
            detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            detail_btn.clicked.connect(lambda _, cid=user_id: self._show_detail(cid))
            self.table.setCellWidget(row, 7, detail_btn)
            self.table.setRowHeight(row, 48)

        for col in [0, 1, 4, 5, 6, 7]:
            self.table.resizeColumnToContents(col)

    def _show_detail(self, client_id: int):
        self._detail_worker = run_async(
            lambda: api_client.get_banker_client(client_id),
            on_success=lambda profile: self._open_detail(client_id, profile),
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_detail_worker", None),
        )

    def _open_detail(self, client_id: int, profile: dict):
        client = profile.get("user", {})
        stats = profile.get("stats", {})
        payments = profile.get("payments", [])

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Клиент #{client_id}")
        dlg.resize(820, 560)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._profile_tab(client, stats), "Профиль")
        tabs.addTab(self._payments_tab(payments), "Платежи")
        layout.addWidget(tabs)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    def _profile_tab(self, client: dict, stats: dict) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        user_id = client.get("id", "")
        balance = client.get("balance", 0)
        daily = client.get("daily_limit", 0)
        monthly = client.get("monthly_limit", 0)
        is_blocked = client.get("is_blocked", False)

        info_lines = [
            ("ID", user_id or "—"),
            ("Счёт", user_id_to_account_number(user_id) if user_id != "" else "—"),
            ("ФИО", client.get("full_name", "—")),
            ("Email", client.get("email", "—")),
            ("Телефон", client.get("phone") or "—"),
            ("Баланс", _rub(balance)),
            ("Дневной лимит", _rub(daily)),
            ("Месячный лимит", _rub(monthly)),
            ("Статус", "Заблокирован" if is_blocked else "Активен"),
        ]
        for label, value in info_lines:
            layout.addWidget(self._info_row(label, str(value)))

        if stats:
            layout.addSpacing(10)
            title = QLabel("Статистика клиента")
            title.setObjectName("sectionTitle")
            layout.addWidget(title)
            stat_lines = [
                ("Отправлено платежей", stats.get("sent_count", 0)),
                ("Получено платежей", stats.get("received_count", 0)),
                ("Сумма отправленных", _rub(stats.get("sent_amount", 0))),
                ("Сумма полученных", _rub(stats.get("received_amount", 0))),
                ("В ожидании", stats.get("pending_payments", 0)),
                ("Одобрено", stats.get("approved_payments", 0)),
                ("Отклонено", stats.get("rejected_payments", 0)),
            ]
            for label, value in stat_lines:
                layout.addWidget(self._info_row(label, str(value)))

        layout.addStretch()
        return tab

    def _payments_tab(self, payments: list) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)

        tbl = QTableWidget()
        tbl.setColumnCount(7)
        tbl.setHorizontalHeaderLabels(["ID", "Дата", "Отправитель", "Получатель", "Сумма", "Статус", "Fraud"])
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        configure_table(tbl, stretch_columns=(1,), min_height=260)
        tbl.setRowCount(len(payments))

        for i, p in enumerate(payments):
            amount = p.get("amount", 0)
            items = [
                QTableWidgetItem(str(p.get("id", ""))),
                QTableWidgetItem(_fmt_date(p.get("created_at"))),
                QTableWidgetItem(str(p.get("sender_id", "—"))),
                QTableWidgetItem(str(p.get("recipient_id", "—"))),
                QTableWidgetItem(_rub(amount)),
                QTableWidgetItem(p.get("status", "—")),
                QTableWidgetItem(str(p.get("fraud_score", 0))),
            ]
            items[4].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[6].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(i, col, item)
            tbl.setRowHeight(i, 42)

        for col in [0, 2, 3, 4, 5, 6]:
            tbl.resizeColumnToContents(col)
        layout.addWidget(tbl)
        return tab

    def _info_row(self, label: str, value: str) -> QWidget:
        row_w = QWidget()
        row_l = QHBoxLayout(row_w)
        row_l.setContentsMargins(0, 2, 0, 2)
        lbl = QLabel(f"<b>{label}:</b>")
        lbl.setFixedWidth(170)
        val = QLabel(value)
        val.setWordWrap(True)
        row_l.addWidget(lbl)
        row_l.addWidget(val, stretch=1)
        return row_w
