import csv
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QDateEdit, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from api.client import api_client
from ui.styles import badge_style
cv

_SORT_KEYS = {
    0: lambda t: int(t["id"]) if t["id"].isdigit() else 0,
    1: lambda t: t["created_at"],
    2: lambda t: t["recipient"].lower(),
    3: lambda t: t["amount"],
    4: lambda t: t["status"],
}

_COL_LABELS = ["ID", "Дата", "Получатель", "Сумма", "Статус", "Действия"]


class History(QWidget):
    def __init__(self):
        super().__init__()
        self._all_transactions = []
        self._sort_col = 1
        self._sort_asc = False
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Filters card
        filter_card = QFrame()
        filter_card.setObjectName("sectionCard")
        filter_layout = QVBoxLayout(filter_card)
        filter_layout.setContentsMargins(20, 16, 20, 16)
        filter_layout.setSpacing(12)

        filter_title = QLabel("Фильтры")
        filter_title.setObjectName("sectionTitle")
        filter_layout.addWidget(filter_title)

        row = QHBoxLayout()
        row.setSpacing(12)

        # Date from
        row.addWidget(QLabel("С:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-30))
        self.date_from.setMinimumHeight(38)
        self.date_from.setMinimumWidth(130)
        row.addWidget(self.date_from)

        # Date to
        row.addWidget(QLabel("По:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setMinimumHeight(38)
        self.date_to.setMinimumWidth(130)
        row.addWidget(self.date_to)

        # Status
        row.addWidget(QLabel("Статус:"))
        self.status_combo = QComboBox()
        self.status_combo.setMinimumHeight(38)
        self.status_combo.setMinimumWidth(140)
        self.status_combo.addItems(["Все", "Завершён", "Обработка", "Ошибка"])
        row.addWidget(self.status_combo)

        # Search
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по получателю...")
        self.search_edit.setMinimumHeight(38)
        self.search_edit.setMinimumWidth(200)
        self.search_edit.textChanged.connect(self._apply_filters)
        row.addWidget(self.search_edit)

        # Apply button
        apply_btn = QPushButton("Применить фильтры")
        apply_btn.setObjectName("filterButton")
        apply_btn.setMinimumHeight(38)
        apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        apply_btn.clicked.connect(self._apply_filters)
        row.addWidget(apply_btn)

        row.addStretch()

        # Export button
        export_btn = QPushButton("Экспорт CSV")
        export_btn.setObjectName("exportButton")
        export_btn.setMinimumHeight(38)
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.clicked.connect(self._export_csv)
        row.addWidget(export_btn)

        filter_layout.addLayout(row)
        layout.addWidget(filter_card)

        # Table card
        table_card = QFrame()
        table_card.setObjectName("sectionCard")
        table_layout = QVBoxLayout(table_card)
        table_layout.setContentsMargins(20, 16, 20, 16)
        table_layout.setSpacing(12)

        hdr_row = QHBoxLayout()
        self.count_label = QLabel("Транзакции")
        self.count_label.setObjectName("sectionTitle")
        hdr_row.addWidget(self.count_label)
        hdr_row.addStretch()
        table_layout.addLayout(hdr_row)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(_COL_LABELS)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setCursor(Qt.CursorShape.PointingHandCursor)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        table_layout.addWidget(self.table)

        layout.addWidget(table_card)

    def _load_data(self):
        try:
            self._all_transactions = api_client.get_transactions()
        except Exception as e:
            self._all_transactions = []
            self.count_label.setText(str(e))
            self.count_label.setStyleSheet("color: #EF4444;")
        self._render_table(self._all_transactions)

    def _on_header_clicked(self, col: int):
        if col not in _SORT_KEYS:
            return
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col
            self._sort_asc = True
        self._apply_filters()

    def _update_header_labels(self):
        for col, label in enumerate(_COL_LABELS):
            if col == self._sort_col:
                arrow = " ↑" if self._sort_asc else " ↓"
                self.table.horizontalHeaderItem(col).setText(label + arrow)
            else:
                item = self.table.horizontalHeaderItem(col)
                if item:
                    item.setText(label)

    def _apply_filters(self):
        search = self.search_edit.text().strip().lower()
        status_map = {
            "Завершён": "completed",
            "Обработка": "processing",
            "Ошибка": "failed",
        }
        selected_status = self.status_combo.currentText()
        status_filter = status_map.get(selected_status)

        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")

        filtered = [
            t for t in self._all_transactions
            if (not search or search in t["recipient"].lower())
            and (status_filter is None or t["status"] == status_filter)
            and (not t["created_at"] or t["created_at"][:10] >= date_from)
            and (not t["created_at"] or t["created_at"][:10] <= date_to)
        ]
        if self._sort_col in _SORT_KEYS:
            filtered.sort(key=_SORT_KEYS[self._sort_col], reverse=not self._sort_asc)
        self._render_table(filtered)

    def _render_table(self, transactions: list):
        self.count_label.setText(f"Транзакции ({len(transactions)})")
        self.table.setRowCount(len(transactions))

        for row, txn in enumerate(transactions):
            amount = txn["amount"]
            amount_str = f"+₽ {amount:,.2f}" if amount > 0 else f"-₽ {abs(amount):,.2f}"
            amount_color = "#10B981" if amount > 0 else "#EF4444"
            _, status_label = badge_style(txn["status"])

            items = [
                QTableWidgetItem(txn["id"]),
                QTableWidgetItem(txn["date"]),
                QTableWidgetItem(txn["recipient"]),
                QTableWidgetItem(amount_str),
                QTableWidgetItem(status_label),
            ]
            items[3].setForeground(QColor(amount_color))
            items[3].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

            # Actions button
            detail_btn = QPushButton("Подробнее")
            detail_btn.setStyleSheet(
                "QPushButton { border: 1px solid #E2E8F0; border-radius: 6px; "
                "padding: 4px 12px; font-size: 12px; color: #3B82F6; background: #EFF6FF; }"
                "QPushButton:hover { background: #DBEAFE; }"
            )
            detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            txn_id = txn["id"]
            detail_btn.clicked.connect(lambda checked, tid=txn_id: self._show_detail(tid))
            self.table.setCellWidget(row, 5, detail_btn)
            self.table.setRowHeight(row, 48)

        self.table.resizeColumnToContents(0)
        self.table.resizeColumnToContents(1)
        self.table.resizeColumnToContents(4)
        self.table.resizeColumnToContents(5)
        self._update_header_labels()

    def _show_detail(self, txn_id: str):
        txn = next((t for t in self._all_transactions if t["id"] == txn_id), None)
        if not txn:
            return
        _, status_label = badge_style(txn["status"])
        amount = txn["amount"]
        amount_str = f"+₽ {amount:,.2f}" if amount > 0 else f"-₽ {abs(amount):,.2f}"
        QMessageBox.information(
            self, f"Транзакция {txn_id}",
            f"ID: {txn['id']}\nДата: {txn['date']}\n"
            f"Получатель: {txn['recipient']}\nСумма: {amount_str}\nСтатус: {status_label}",
        )

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить CSV", "transactions.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Дата", "Получатель", "Сумма", "Статус"])
                for txn in self._all_transactions:
                    _, status_label = badge_style(txn["status"])
                    writer.writerow([
                        txn["id"], txn["date"], txn["recipient"],
                        txn["amount"], status_label,
                    ])
            QMessageBox.information(self, "Экспорт завершён", f"Файл сохранён:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", str(e))
