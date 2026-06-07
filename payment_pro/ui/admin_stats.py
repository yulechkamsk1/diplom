from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QDialogButtonBox, QSizePolicy, QScrollArea,
)
from PyQt6.QtCore import Qt
from api.client import api_client
from ui.async_utils import run_async
from ui.responsive import ResponsiveGrid, configure_table


def _rub(kopecks: int | float | None) -> str:
    return f"₽ {(kopecks or 0) / 100:,.2f}"


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso[:16]


class AdminStats(QWidget):
    def __init__(self):
        super().__init__()
        self._stats = {}
        self._load_worker = None
        self._history_worker = None
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
        self.layout_.setSpacing(20)

        hdr = QHBoxLayout()
        title = QLabel("Статистика решений")
        title.setObjectName("sectionTitle")
        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("filterButton")
        refresh_btn.setMinimumHeight(38)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._load_data)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(refresh_btn)
        self.layout_.addLayout(hdr)

        self.cards_grid = ResponsiveGrid(min_item_width=200, max_columns=5)
        self.layout_.addWidget(self.cards_grid)

        table_card = QFrame()
        table_card.setObjectName("sectionCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 16, 20, 16)
        table_layout.setSpacing(12)

        table_title = QLabel("Решения по банкирам")
        table_title.setObjectName("sectionTitle")
        table_layout.addWidget(table_title)

        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Оператор", "Email", "Одобрено", "Отклонено", "Всего", "Последнее решение", "История"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        configure_table(self.table, stretch_columns=(1, 2), min_height=300)
        table_layout.addWidget(self.table)
        self.layout_.addWidget(table_card)
        self.layout_.addStretch()

    def _load_data(self):
        self._clear_cards()
        self.cards_grid.add_card(self._stat_card("Загрузка", "…", "получаем статистику", "#64748B"))
        self._load_worker = run_async(
            api_client.get_admin_stats,
            on_success=self._on_stats_loaded,
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _on_stats_loaded(self, stats: dict):
        self._stats = stats
        self._render()

    def _clear_cards(self):
        self.cards_grid.clear()

    def _render(self):
        self._clear_cards()
        payments = self._stats.get("payments", {})
        bankers = self._stats.get("bankers", [])

        cards = [
            ("Всего платежей", f"{payments.get('total', 0):,}", "в системе", "#3B82F6"),
            ("В ожидании", str(payments.get("pending", 0)), "требуют проверки", "#F59E0B"),
            ("Одобрено", str(payments.get("approved", 0)), "решений банкиров", "#10B981"),
            ("Отклонено", str(payments.get("rejected", 0)), "решений банкиров", "#EF4444"),
            ("Завершено", str(payments.get("completed", 0)), "автоматически/после обработки", "#64748B"),
        ]
        for label, value, sub, color in cards:
            self.cards_grid.add_card(self._stat_card(label, value, sub, color))

        self.table.setRowCount(len(bankers))
        for row, entry in enumerate(bankers):
            banker = entry.get("banker", {})
            banker_id = banker.get("id", "")
            items = [
                QTableWidgetItem(str(banker_id)),
                QTableWidgetItem(banker.get("full_name", "—")),
                QTableWidgetItem(banker.get("email", "—")),
                QTableWidgetItem(str(entry.get("approved", 0))),
                QTableWidgetItem(str(entry.get("rejected", 0))),
                QTableWidgetItem(str(entry.get("total", 0))),
                QTableWidgetItem(_fmt_dt(entry.get("last_decision"))),
            ]
            for col in [3, 4, 5]:
                items[col].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

            history_btn = QPushButton("Открыть")
            history_btn.setStyleSheet(
                "QPushButton { border: 1px solid #E2E8F0; border-radius: 6px; "
                "padding: 4px 10px; font-size: 12px; color: #3B82F6; background: #EFF6FF; }"
                "QPushButton:hover { background: #DBEAFE; }"
            )
            history_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            history_btn.clicked.connect(lambda _, bid=banker_id: self._show_banker_history(bid))
            self.table.setCellWidget(row, 7, history_btn)
            self.table.setRowHeight(row, 48)

        for col in [0, 3, 4, 5, 6, 7]:
            self.table.resizeColumnToContents(col)

    def _stat_card(self, label: str, value: str, sub: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("statCard")
        card.setMinimumWidth(160)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setObjectName("statLabel")
        val = QLabel(value)
        val.setObjectName("statValue")
        val.setStyleSheet(f"color: {color};")
        sub_lbl = QLabel(sub)
        sub_lbl.setObjectName("statChange")

        layout.addWidget(lbl)
        layout.addWidget(val)
        layout.addWidget(sub_lbl)
        return card

    def _show_banker_history(self, banker_id: int):
        self._history_worker = run_async(
            lambda: {
                "payments": api_client.get_admin_banker_history(banker_id),
                "user_map": api_client.get_user_map(),
            },
            on_success=lambda data: self._open_banker_history(banker_id, data["payments"], data["user_map"]),
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_history_worker", None),
        )

    def _open_banker_history(self, banker_id: int, payments: list, user_map: dict):
        from api.client import PAYMENT_STATUS_RU
        from PyQt6.QtGui import QColor

        def name(uid):
            if uid is None:
                return "—"
            return user_map.get(uid, f"ID {uid}")

        def fraud_color(score):
            if score >= 70:
                return "#EF4444"
            if score >= 40:
                return "#F59E0B"
            return "#10B981"

        banker_name = user_map.get(banker_id, f"оператор #{banker_id}")
        dlg = QDialog(self)
        dlg.setWindowTitle(f"История оператора — {banker_name}")
        dlg.resize(980, 560)
        layout = QVBoxLayout(dlg)

        tbl = QTableWidget()
        tbl.setColumnCount(8)
        tbl.setHorizontalHeaderLabels(
            ["ID", "Дата", "Отправитель", "Получатель", "Сумма", "Статус", "Риск-балл", "Обработан"]
        )
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        configure_table(tbl, stretch_columns=(2, 3), min_height=320)
        tbl.setRowCount(len(payments))
        for row, p in enumerate(payments):
            fraud = p.get("fraud_score") or 0
            status_raw = p.get("status", "")

            sender_btn = QPushButton(name(p.get("sender_id")))
            sender_btn.setStyleSheet(
                "QPushButton { border: none; background: transparent; color: #3B82F6; "
                "text-align: left; padding: 2px 4px; }"
                "QPushButton:hover { text-decoration: underline; }"
            )
            sender_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            sender_id = p.get("sender_id")
            if sender_id:
                sender_btn.clicked.connect(lambda _, uid=sender_id: self._open_client_profile(uid))

            recip_btn = QPushButton(name(p.get("recipient_id")))
            recip_btn.setStyleSheet(
                "QPushButton { border: none; background: transparent; color: #3B82F6; "
                "text-align: left; padding: 2px 4px; }"
                "QPushButton:hover { text-decoration: underline; }"
            )
            recip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            recip_id = p.get("recipient_id")
            if recip_id:
                recip_btn.clicked.connect(lambda _, uid=recip_id: self._open_client_profile(uid))

            items = [
                QTableWidgetItem(str(p.get("id", ""))),
                QTableWidgetItem(_fmt_dt(p.get("created_at"))),
                None,
                None,
                QTableWidgetItem(_rub(p.get("amount", 0))),
                QTableWidgetItem(PAYMENT_STATUS_RU.get(status_raw, status_raw or "—")),
                QTableWidgetItem(str(fraud)),
                QTableWidgetItem(_fmt_dt(p.get("processed_at"))),
            ]
            items[4].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[6].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items[6].setForeground(QColor(fraud_color(fraud)))
            for col, item in enumerate(items):
                if item is not None:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    tbl.setItem(row, col, item)
            tbl.setCellWidget(row, 2, sender_btn)
            tbl.setCellWidget(row, 3, recip_btn)
            tbl.setRowHeight(row, 42)
        for col in [0, 4, 5, 6, 7]:
            tbl.resizeColumnToContents(col)

        layout.addWidget(tbl)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    def _open_client_profile(self, client_id: int):
        self._history_worker = run_async(
            lambda: api_client.get_admin_client_history(client_id),
            on_success=lambda data: self._show_client_dialog(client_id, data),
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_history_worker", None),
        )

    def _show_client_dialog(self, client_id: int, data):
        from PyQt6.QtWidgets import QTabWidget, QDialogButtonBox, QTabWidget
        from PyQt6.QtGui import QColor
        from api.client import PAYMENT_STATUS_RU

        # data может быть dict {"profile": {...}, "payments": [...]} или list платежей
        if isinstance(data, dict):
            profile = data.get("profile", {})
            user = profile.get("user", profile)
            payments = data.get("payments", data.get("history", []))
        elif isinstance(data, list):
            user = {}
            payments = data
        else:
            user = {}
            payments = []

        name = user.get("full_name") or f"клиент #{client_id}"

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Профиль — {name}")
        dlg.resize(860, 560)
        outer = QVBoxLayout(dlg)

        tabs = QTabWidget()

        # --- Вкладка: Профиль ---
        profile_tab = QWidget()
        pt_layout = QVBoxLayout(profile_tab)
        pt_layout.setContentsMargins(20, 16, 20, 16)
        pt_layout.setSpacing(8)
        for label, value in [
            ("ФИО", user.get("full_name", "—")),
            ("Email", user.get("email", "—")),
            ("Телефон", user.get("phone") or "—"),
            ("Баланс", f"₽ {(user.get('balance', 0) or 0) / 100:,.2f}"),
            ("Роль", user.get("role", "—")),
        ]:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 2, 0, 2)
            lbl = QLabel(f"<b>{label}:</b>")
            lbl.setFixedWidth(130)
            row_l.addWidget(lbl)
            row_l.addWidget(QLabel(str(value)))
            row_l.addStretch()
            pt_layout.addWidget(row_w)
        pt_layout.addStretch()
        tabs.addTab(profile_tab, "Профиль")

        # --- Вкладка: История платежей ---
        hist_tab = QWidget()
        ht_layout = QVBoxLayout(hist_tab)
        ht_layout.setContentsMargins(0, 8, 0, 0)

        from ui.responsive import configure_table
        tbl = QTableWidget()
        tbl.setColumnCount(6)
        tbl.setHorizontalHeaderLabels(["ID", "Дата", "Сумма", "Статус", "Риск-балл", "Описание"])
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        configure_table(tbl, stretch_columns=(5,), min_height=320)

        tbl.setRowCount(len(payments))
        for row_i, p in enumerate(payments):
            status_raw = p.get("status", "")
            amount = p.get("amount", 0) / 100
            fraud = p.get("fraud_score") or 0
            fraud_color = "#EF4444" if fraud >= 70 else "#F59E0B" if fraud >= 40 else "#10B981"
            items = [
                QTableWidgetItem(str(p.get("id", ""))),
                QTableWidgetItem(_fmt_dt(p.get("created_at"))),
                QTableWidgetItem(f"₽ {amount:,.2f}"),
                QTableWidgetItem(PAYMENT_STATUS_RU.get(status_raw, status_raw or "—")),
                QTableWidgetItem(str(fraud)),
                QTableWidgetItem(p.get("description") or "—"),
            ]
            items[2].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[4].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items[4].setForeground(QColor(fraud_color))
            for col_i, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(row_i, col_i, item)
            tbl.setRowHeight(row_i, 40)

        ht_layout.addWidget(tbl)
        tabs.addTab(hist_tab, f"История ({len(payments)})")

        outer.addWidget(tabs)
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        outer.addWidget(btns)
        dlg.exec()
