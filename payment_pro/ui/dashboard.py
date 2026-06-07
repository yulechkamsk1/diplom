from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from api.client import api_client
from auth.jwt_manager import jwt_manager
from ui.async_utils import run_async
from ui.responsive import ResponsiveGrid, configure_table
from ui.styles import badge_style


class StatCard(QFrame):
    def __init__(self, label: str, value: str, change: str, positive: bool, icon: str, icon_color: str):
        super().__init__()
        self.setObjectName("statCard")
        self.setMinimumWidth(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        # Icon box
        icon_box = QLabel(icon)
        icon_box.setObjectName("statIconBox")
        icon_box.setFixedSize(48, 48)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setFont(QFont("sans-serif", 20))
        icon_box.setStyleSheet(f"background:{icon_color}; border-radius: 10px;")
        layout.addWidget(icon_box)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        lbl = QLabel(label)
        lbl.setObjectName("statLabel")
        text_col.addWidget(lbl)

        val = QLabel(value)
        val.setObjectName("statValue")
        text_col.addWidget(val)

        color = "#10B981" if positive else "#EF4444"
        arrow = "▲" if positive else "▼"
        chg = QLabel(f"{arrow} {change}")
        chg.setObjectName("statChange")
        chg.setStyleSheet(f"color: {color};")
        text_col.addWidget(chg)

        layout.addLayout(text_col)
        layout.addStretch()


class Dashboard(QWidget):
    navigate = pyqtSignal(str)

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

        self.layout_ = QVBoxLayout(container)
        self.layout_.setContentsMargins(28, 24, 28, 24)
        self.layout_.setSpacing(24)

        self.cards_grid = ResponsiveGrid(min_item_width=230, max_columns=4)
        self.layout_.addWidget(self.cards_grid)

        # Quick actions
        qa_frame = QFrame()
        qa_frame.setObjectName("sectionCard")
        qa_layout = QVBoxLayout(qa_frame)
        qa_layout.setContentsMargins(20, 16, 20, 16)
        qa_layout.setSpacing(12)

        qa_title = QLabel("Быстрые действия")
        qa_title.setObjectName("sectionTitle")
        qa_layout.addWidget(qa_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        role = jwt_manager.get_role_key()
        if role == "CLIENT":
            btn_pay = QPushButton("Новый платёж по счёту")
            btn_pay.setObjectName("btnNewPayment")
            btn_pay.setMinimumHeight(44)
            btn_pay.setMinimumWidth(190)
            btn_pay.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_pay.clicked.connect(lambda: self.navigate.emit("payments"))
            btn_row.addWidget(btn_pay)

            btn_transfer = QPushButton("Перевод по email")
            btn_transfer.setObjectName("btnTransfer")
            btn_transfer.setMinimumHeight(44)
            btn_transfer.setMinimumWidth(160)
            btn_transfer.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_transfer.clicked.connect(lambda: self.navigate.emit("payments_email"))
            btn_row.addWidget(btn_transfer)
        elif role == "BANKER":
            btn_queue = QPushButton("Очередь платежей")
            btn_queue.setObjectName("btnNewPayment")
            btn_queue.setMinimumHeight(44)
            btn_queue.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_queue.clicked.connect(lambda: self.navigate.emit("queue"))
            btn_row.addWidget(btn_queue)

            btn_clients = QPushButton("Клиенты")
            btn_clients.setObjectName("btnTransfer")
            btn_clients.setMinimumHeight(44)
            btn_clients.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_clients.clicked.connect(lambda: self.navigate.emit("clients"))
            btn_row.addWidget(btn_clients)
        elif role == "ADMIN":
            btn_stats = QPushButton("Статистика")
            btn_stats.setObjectName("btnNewPayment")
            btn_stats.setMinimumHeight(44)
            btn_stats.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_stats.clicked.connect(lambda: self.navigate.emit("stats"))
            btn_row.addWidget(btn_stats)

            btn_users = QPushButton("Пользователи")
            btn_users.setObjectName("btnTransfer")
            btn_users.setMinimumHeight(44)
            btn_users.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_users.clicked.connect(lambda: self.navigate.emit("users"))
            btn_row.addWidget(btn_users)

            btn_audit = QPushButton("Журнал аудита")
            btn_audit.setObjectName("btnHistory")
            btn_audit.setMinimumHeight(44)
            btn_audit.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_audit.clicked.connect(lambda: self.navigate.emit("audit"))
            btn_row.addWidget(btn_audit)

        btn_hist = QPushButton("История")
        btn_hist.setObjectName("btnHistory")
        btn_hist.setMinimumHeight(44)
        btn_hist.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_hist.clicked.connect(lambda: self.navigate.emit("history"))

        btn_row.addWidget(btn_hist)
        btn_row.addStretch()
        qa_layout.addLayout(btn_row)
        self.layout_.addWidget(qa_frame)

        # Recent transactions
        txn_frame = QFrame()
        txn_frame.setObjectName("sectionCard")
        txn_layout = QVBoxLayout(txn_frame)
        txn_layout.setContentsMargins(20, 16, 20, 16)
        txn_layout.setSpacing(12)

        hdr_row = QHBoxLayout()
        txn_title = QLabel("Последние транзакции")
        txn_title.setObjectName("sectionTitle")
        show_all = QPushButton("Показать все")
        show_all.setObjectName("showAllLink")
        show_all.setCursor(Qt.CursorShape.PointingHandCursor)
        show_all.clicked.connect(lambda: self.navigate.emit("history"))
        hdr_row.addWidget(txn_title)
        hdr_row.addStretch()
        hdr_row.addWidget(show_all)
        txn_layout.addLayout(hdr_row)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Дата", "Получатель", "Сумма", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        configure_table(self.table, stretch_columns=(1,), min_height=180)
        txn_layout.addWidget(self.table)

        self.layout_.addWidget(txn_frame)
        self.layout_.addStretch()

    def _load_data(self):
        self.cards_grid.clear()
        for label in ["Показатели", "Операции", "Статус", "Сводка"]:
            self.cards_grid.add_card(StatCard(label, "…", "загрузка", True, "...", "#E2E8F0"))
        self.table.setRowCount(0)
        self._load_worker = run_async(
            lambda: {
                "stats": api_client.get_dashboard_stats(),
                "transactions": api_client.get_recent_transactions(),
            },
            on_success=self._render_data,
            on_error=self._show_error,
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _render_data(self, data: dict):
        role = jwt_manager.get_role_key()
        stats = data.get("stats", {})
        transactions = data.get("transactions", [])

        self.cards_grid.clear()
        if role == "BANKER":
            cards = [
                ("Одобрено", str(stats.get("approved_count", 0)), "решений", True, "OK", "#DCFCE7"),
                ("Отклонено", str(stats.get("rejected_count", 0)), "решений", False, "NO", "#FEE2E2"),
                ("Всего решений", str(stats.get("total_decisions", 0)), "за всё время", True, "Σ", "#DBEAFE"),
                ("В очереди", str(stats.get("pending_count", 0)), "ожидают проверки", True, "...", "#FEF3C7"),
            ]
        elif role == "ADMIN":
            cards = [
                ("Всего платежей", f"{stats.get('total_payments', 0):,}", "в системе", True, "TX", "#DBEAFE"),
                ("В ожидании", str(stats.get("pending_payments", 0)), "ожидают банкира", True, "...", "#FEF3C7"),
                ("Одобрено", str(stats.get("approved_payments", 0)), "решений", True, "OK", "#DCFCE7"),
                ("Отклонено", str(stats.get("rejected_payments", 0)), "решений", False, "NO", "#FEE2E2"),
            ]
        else:
            cards = [
                ("Баланс", f"₽ {stats.get('balance', 0):,.2f}", f"{abs(stats.get('balance_change', 0))}% за месяц",
                 stats.get('balance_change', 0) >= 0, "₽", "#DCFCE7"),
                ("Транзакции", f"{stats.get('transactions_count', 0):,}", f"{abs(stats.get('transactions_change', 0))}% за неделю",
                 stats.get('transactions_change', 0) >= 0, "TX", "#DBEAFE"),
                ("В обработке", str(stats.get("pending_count", 0)), f"{abs(stats.get('pending_change', 0))}% за день",
                 stats.get('pending_change', 0) >= 0, "...", "#FEF3C7"),
                ("Счета", f"{stats.get('accounts_count', 0)} активных", "активных счетов",
                 True, "Сч", "#EDE9FE"),
            ]

        for label, value, change, positive, icon, color in cards:
            card = StatCard(label, value, change, positive, icon, color)
            self.cards_grid.add_card(card)

        self.table.setRowCount(len(transactions))
        for row, txn in enumerate(transactions):
            amount = txn["amount"]
            amount_str = f"+₽ {amount:,.2f}" if amount > 0 else f"-₽ {abs(amount):,.2f}"
            amount_color = "#10B981" if amount > 0 else "#EF4444"

            date_item = QTableWidgetItem(txn["date"])
            recip_item = QTableWidgetItem(txn["recipient"])
            amount_item = QTableWidgetItem(amount_str)
            amount_item.setForeground(QColor(amount_color))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            status_item = QTableWidgetItem()
            style_str, label_str = badge_style(txn["status"])
            status_item.setText(label_str)

            for item in [date_item, recip_item, amount_item, status_item]:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.table.setItem(row, 0, date_item)
            self.table.setItem(row, 1, recip_item)
            self.table.setItem(row, 2, amount_item)
            self.table.setItem(row, 3, status_item)
            self.table.setRowHeight(row, 48)

        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(3)

    def _show_error(self, msg: str):
        self.cards_grid.clear()
        self.cards_grid.add_card(StatCard("Ошибка", "—", msg, False, "!", "#FEE2E2"))
