from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PyQt6.QtCore import Qt
from datetime import datetime
from api.client import api_client
from ui.async_utils import run_async
from ui.responsive import configure_table


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
        self.table.setHorizontalHeaderLabels(["ID", "Действие", "Пользователь", "Объект", "Дата"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        configure_table(self.table, stretch_columns=(1,), min_height=300)
        card_layout.addWidget(self.table)

        layout.addWidget(card)

    def _load_data(self):
        self.count_label.setText("Журнал аудита (загрузка...)")
        self._load_worker = run_async(
            api_client.get_admin_audit,
            on_success=self._on_audit_loaded,
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _on_audit_loaded(self, entries: list):
        self._entries = entries
        self._render()

    def _render(self):
        self.count_label.setText(f"Журнал аудита ({len(self._entries)})")
        self.table.setRowCount(len(self._entries))

        for row, e in enumerate(self._entries):
            user = e.get("user") or e.get("user_id") or "—"
            target = e.get("target") or e.get("entity_id") or "—"

            items = [
                QTableWidgetItem(str(e.get("id", ""))),
                QTableWidgetItem(e.get("action", "—")),
                QTableWidgetItem(str(user)),
                QTableWidgetItem(str(target)),
                QTableWidgetItem(_fmt_dt(e.get("created_at") or e.get("timestamp"))),
            ]

            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

        for col in [0, 3, 4]:
            self.table.resizeColumnToContents(col)
