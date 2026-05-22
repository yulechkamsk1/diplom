from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QProgressBar,
)
from PyQt6.QtCore import Qt
from api.client import api_client
from ui.async_utils import run_async
from ui.responsive import ResponsiveGrid


class Analytics(QWidget):
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

        breakdown_frame = QFrame()
        breakdown_frame.setObjectName("sectionCard")
        bl = QVBoxLayout(breakdown_frame)
        bl.setContentsMargins(24, 20, 24, 20)
        bl.setSpacing(16)

        title = QLabel("Разбивка по статусам")
        title.setObjectName("sectionTitle")
        bl.addWidget(title)

        self.breakdown_layout = QVBoxLayout()
        self.breakdown_layout.setSpacing(12)
        bl.addLayout(self.breakdown_layout)

        self.layout_.addWidget(breakdown_frame)
        self.layout_.addStretch()

    def _load_data(self):
        self.cards_grid.clear()
        self.cards_grid.add_card(self._stat_card("Загрузка", "…", "получаем данные", "#64748B"))
        self._load_worker = run_async(
            api_client.get_transactions,
            on_success=self._render_data,
            on_error=lambda _: self._render_data([]),
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _render_data(self, payments: list):
        self.cards_grid.clear()
        sent_total = sum(abs(p["amount"]) for p in payments if p["amount"] < 0)
        recv_total = sum(p["amount"] for p in payments if p["amount"] > 0)
        sent_count = sum(1 for p in payments if p["amount"] < 0)
        recv_count = sum(1 for p in payments if p["amount"] > 0)
        processing = sum(1 for p in payments if p["status"] == "processing")
        failed = sum(1 for p in payments if p["status"] == "failed")

        cards = [
            ("Отправлено",    f"₽ {sent_total:,.2f}", f"{sent_count} операций",  "#EF4444"),
            ("Получено",      f"₽ {recv_total:,.2f}", f"{recv_count} операций",  "#10B981"),
            ("В обработке",   str(processing),         "платежей",               "#F59E0B"),
            ("Отклонено",     str(failed),              "платежей",               "#6B7280"),
        ]
        for label, value, sub, color in cards:
            self.cards_grid.add_card(self._stat_card(label, value, sub, color))

        while self.breakdown_layout.count():
            item = self.breakdown_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        total = len(payments) or 1
        statuses = [
            ("Завершён",     "completed",  "#10B981"),
            ("В обработке",  "processing", "#F59E0B"),
            ("Отклонён",     "failed",     "#EF4444"),
        ]
        for label, status, color in statuses:
            count = sum(1 for p in payments if p["status"] == status)
            self.breakdown_layout.addWidget(
                self._breakdown_row(label, count, count / total * 100, color)
            )

    def _stat_card(self, label: str, value: str, sub: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("statCard")
        card.setMinimumWidth(180)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
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

    def _breakdown_row(self, label: str, count: int, pct: float, color: str) -> QWidget:
        row = QWidget()
        hl = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(12)

        dot = QLabel("●")
        dot.setFixedWidth(16)
        dot.setStyleSheet(f"color: {color}; font-size: 14px;")

        lbl = QLabel(label)
        lbl.setFixedWidth(130)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(pct))
        bar.setFixedHeight(10)
        bar.setTextVisible(False)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        bar.setStyleSheet(
            f"QProgressBar {{ background: #F1F5F9; border-radius: 5px; border: none; }}"
            f"QProgressBar::chunk {{ background: {color}; border-radius: 5px; }}"
        )

        pct_lbl = QLabel(f"{count}  ({pct:.1f}%)")
        pct_lbl.setFixedWidth(110)
        pct_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        pct_lbl.setStyleSheet("color: #64748B; font-size: 13px;")

        hl.addWidget(dot)
        hl.addWidget(lbl)
        hl.addWidget(bar)
        hl.addWidget(pct_lbl)
        return row
