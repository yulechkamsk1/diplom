from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from api.client import api_client


class BankerClients(QWidget):
    def __init__(self):
        super().__init__()
        self._clients = []
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

        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "ФИО", "Email", "Телефон", "Баланс", "Статус", ""])
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
            self._clients = api_client.get_banker_clients()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self._render()

    def _render(self):
        self.count_label.setText(f"Клиенты ({len(self._clients)})")
        self.table.setRowCount(len(self._clients))

        for row, c in enumerate(self._clients):
            balance = c.get("balance", 0) / 100
            is_blocked = c.get("is_blocked", False)

            items = [
                QTableWidgetItem(str(c.get("id", ""))),
                QTableWidgetItem(c.get("full_name", "—")),
                QTableWidgetItem(c.get("email", "—")),
                QTableWidgetItem(c.get("phone") or "—"),
                QTableWidgetItem(f"₽ {balance:,.2f}"),
                QTableWidgetItem("Заблокирован" if is_blocked else "Активен"),
            ]
            items[4].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[5].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_blocked:
                items[5].setForeground(QColor("#EF4444"))

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
            client_id = c.get("id")
            detail_btn.clicked.connect(lambda _, cid=client_id: self._show_detail(cid))
            self.table.setCellWidget(row, 6, detail_btn)
            self.table.setRowHeight(row, 48)

        for col in [0, 3, 4, 5, 6]:
            self.table.resizeColumnToContents(col)

    def _show_detail(self, client_id: int):
        try:
            client = api_client.get_banker_client(client_id)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return

        balance = client.get("balance", 0) / 100
        daily = client.get("daily_limit", 0) / 100
        is_blocked = client.get("is_blocked", False)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Клиент #{client_id}")
        dlg.setMinimumWidth(400)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)

        info_lines = [
            ("ФИО",             client.get("full_name", "—")),
            ("Email",           client.get("email", "—")),
            ("Телефон",         client.get("phone") or "—"),
            ("Баланс",          f"₽ {balance:,.2f}"),
            ("Дневной лимит",   f"₽ {daily:,.2f}"),
            ("Статус",          "Заблокирован" if is_blocked else "Активен"),
        ]
        for label, value in info_lines:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 2, 0, 2)
            lbl = QLabel(f"<b>{label}:</b>")
            lbl.setFixedWidth(140)
            val = QLabel(value)
            row_l.addWidget(lbl)
            row_l.addWidget(val)
            layout.addWidget(row_w)

        try:
            payments = api_client.get_admin_client_history(client_id)
        except Exception:
            payments = []

        if payments:
            layout.addSpacing(8)
            layout.addWidget(QLabel("<b>Последние платежи:</b>"))
            tbl = QTableWidget()
            tbl.setColumnCount(3)
            tbl.setHorizontalHeaderLabels(["Дата", "Сумма", "Статус"])
            tbl.verticalHeader().setVisible(False)
            tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            tbl.setMinimumHeight(150)
            tbl.setRowCount(min(len(payments), 10))
            for i, p in enumerate(payments[:10]):
                amount = p.get("amount", 0) / 100
                tbl.setItem(i, 0, QTableWidgetItem(p.get("date", "—")))
                amt_item = QTableWidgetItem(f"₽ {amount:,.2f}")
                amt_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                tbl.setItem(i, 1, amt_item)
                tbl.setItem(i, 2, QTableWidgetItem(p.get("status", "—")))
            tbl.resizeColumnsToContents()
            layout.addWidget(tbl)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()
