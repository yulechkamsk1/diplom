from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QInputDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from api.client import api_client
from ui.async_utils import run_async
from ui.responsive import configure_table


class BankerQueue(QWidget):
    def __init__(self):
        super().__init__()
        self._queue = []
        self._load_worker = None
        self._action_worker = None
        self._loading = False
        self._build_ui()
        self._load_data()
        self._auto_refresh = QTimer(self)
        self._auto_refresh.setInterval(10_000)
        self._auto_refresh.timeout.connect(lambda: self._load_data(show_errors=False))
        self._auto_refresh.start()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        hdr = QHBoxLayout()
        self.count_label = QLabel("Очередь платежей")
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
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Отправитель", "Сумма", "Описание", "Fraud", "Действия"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        configure_table(self.table, stretch_columns=(3,), min_height=300)
        card_layout.addWidget(self.table)

        layout.addWidget(card)

    def _load_data(self, show_errors: bool = True):
        if self._loading:
            return
        self._loading = True
        self.count_label.setText("Очередь платежей (загрузка...)")
        self._load_worker = run_async(
            api_client.get_banker_queue,
            on_success=self._on_queue_loaded,
            on_error=(lambda msg: QMessageBox.critical(self, "Ошибка", msg)) if show_errors else None,
            on_finished=self._on_load_finished,
        )

    def _on_queue_loaded(self, queue: list):
        self._queue = queue
        self._render()

    def _on_load_finished(self):
        self._loading = False
        self._load_worker = None

    def _render(self):
        self.count_label.setText(f"Очередь платежей ({len(self._queue)})")
        self.table.setRowCount(len(self._queue))

        for row, p in enumerate(self._queue):
            amount = p.get("amount", 0) / 100
            fraud = p.get("fraud_score", 0)
            fraud_color = "#EF4444" if fraud >= 70 else "#F59E0B" if fraud >= 40 else "#10B981"

            items = [
                QTableWidgetItem(str(p.get("id", ""))),
                QTableWidgetItem(f"ID {p.get('sender_id', '?')}"),
                QTableWidgetItem(f"₽ {amount:,.2f}"),
                QTableWidgetItem(p.get("description", "—")),
                QTableWidgetItem(str(fraud)),
            ]
            items[2].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[4].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items[4].setForeground(QColor(fraud_color))

            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

            btn_frame = QWidget()
            btn_layout = QHBoxLayout(btn_frame)
            btn_layout.setContentsMargins(6, 4, 6, 4)
            btn_layout.setSpacing(6)

            approve_btn = QPushButton("Одобрить")
            approve_btn.setStyleSheet(
                "QPushButton { border:1px solid #10B98144; border-radius:6px; "
                "padding:4px 10px; font-size:12px; color:#10B981; background:#DCFCE7; }"
                "QPushButton:hover { background:#BBF7D0; }"
            )
            approve_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            approve_btn.clicked.connect(lambda _, pid=p["id"]: self._approve(pid))

            reject_btn = QPushButton("Отклонить")
            reject_btn.setStyleSheet(
                "QPushButton { border:1px solid #EF444444; border-radius:6px; "
                "padding:4px 10px; font-size:12px; color:#EF4444; background:#FEE2E2; }"
                "QPushButton:hover { background:#FECACA; }"
            )
            reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            reject_btn.clicked.connect(lambda _, pid=p["id"]: self._reject(pid))

            btn_layout.addWidget(approve_btn)
            btn_layout.addWidget(reject_btn)
            self.table.setCellWidget(row, 5, btn_frame)
            self.table.setRowHeight(row, 52)

        for col in [0, 1, 2, 4]:
            self.table.resizeColumnToContents(col)

    def _approve(self, payment_id: int):
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Одобрить платёж #{payment_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._action_worker = run_async(
            lambda: api_client.approve_payment(payment_id),
            on_success=lambda _: (QMessageBox.information(self, "Готово", f"Платёж #{payment_id} одобрен."), self._load_data()),
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_action_worker", None),
        )

    def _reject(self, payment_id: int):
        reason, ok = QInputDialog.getText(
            self, "Причина отклонения",
            f"Укажите причину для платежа #{payment_id}:",
        )
        if not ok:
            return
        self._action_worker = run_async(
            lambda: api_client.reject_payment(payment_id, reason),
            on_success=lambda _: (QMessageBox.information(self, "Готово", f"Платёж #{payment_id} отклонён."), self._load_data()),
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_action_worker", None),
        )
