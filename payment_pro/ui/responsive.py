from PyQt6.QtCore import Qt, QEvent, QObject
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QWidget,
)

_SKIP_HEADERS = {"Действия", "История", "Лимиты", ""}


class _RowPopup(QObject):
    def __init__(self, table: QTableWidget):
        super().__init__(table)
        self._table = table
        self._popup: QFrame | None = None
        table.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            row = self._table.rowAt(event.pos().y())
            if row >= 0:
                self._show(row, event.globalPosition().toPoint())
            else:
                self._close()
        return False

    def _close(self):
        if self._popup:
            self._popup.close()
            self._popup = None

    def _show(self, row: int, gpos):
        self._close()

        parts = []
        for col in range(self._table.columnCount()):
            h = self._table.horizontalHeaderItem(col)
            header = h.text().strip() if h else ""
            if header in _SKIP_HEADERS:
                continue
            item = self._table.item(row, col)
            val = item.text().strip() if item else ""
            if val and header:
                parts.append((header, val))

        if not parts:
            return

        popup = QFrame(None, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        popup.setStyleSheet("""
            QFrame {
                background: #1E293B;
                border: 1.5px solid #334155;
                border-radius: 10px;
            }
            QLabel { font-family: 'Segoe UI', Arial; }
        """)

        layout = QHBoxLayout(popup)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setStyleSheet("background:#3B82F6; border-radius:10px 0 0 10px;")
        layout.addWidget(accent)

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        inner_layout = QHBoxLayout(inner)
        inner_layout.setContentsMargins(14, 12, 18, 12)
        inner_layout.setSpacing(24)

        col_count = 2
        col_layouts = [QWidget() for _ in range(col_count)]
        for cw in col_layouts:
            cw.setStyleSheet("background:transparent;")
            inner_layout.addWidget(cw)

        for i, (header, val) in enumerate(parts):
            cw = col_layouts[i % col_count]
            if not cw.layout():
                from PyQt6.QtWidgets import QVBoxLayout
                QVBoxLayout(cw).setSpacing(4)
                cw.layout().setContentsMargins(0, 0, 0, 0)

            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(row_w)
            rl.setContentsMargins(0, 1, 0, 1)
            rl.setSpacing(8)

            lbl = QLabel(header + ":")
            lbl.setStyleSheet("color:#94A3B8; font-size:11px;")
            lbl.setMinimumWidth(90)

            val_lbl = QLabel(val)
            val_lbl.setStyleSheet("color:#F1F5F9; font-size:13px; font-weight:500;")
            val_lbl.setWordWrap(True)

            rl.addWidget(lbl)
            rl.addWidget(val_lbl, 1)
            cw.layout().addWidget(row_w)

        layout.addWidget(inner)
        popup.adjustSize()

        screen = QApplication.primaryScreen().geometry()
        x = gpos.x() + 14
        y = gpos.y() - popup.height() // 2
        if x + popup.width() > screen.right() - 10:
            x = gpos.x() - popup.width() - 14
        y = max(screen.top() + 10, min(y, screen.bottom() - popup.height() - 10))

        popup.move(x, y)
        popup.show()
        self._popup = popup


def configure_table(table: QTableWidget, stretch_columns: tuple[int, ...] = (), min_height: int = 260) -> None:
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    table.setHorizontalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
    table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    if min_height:
        table.setMinimumHeight(min_height)

    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(70)
    header.setDefaultSectionSize(130)
    for col in range(table.columnCount()):
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
    for col in stretch_columns:
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)

    _RowPopup(table)


class ResponsiveGrid(QWidget):
    def __init__(self, min_item_width: int = 220, max_columns: int = 4, parent=None):
        super().__init__(parent)
        self._items: list[QWidget] = []
        self._min_item_width = min_item_width
        self._max_columns = max_columns
        self._columns = 0

        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(16)

    def add_card(self, widget: QWidget) -> None:
        self._items.append(widget)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._relayout()

    def clear(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._items.clear()
        self._columns = 0

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        available = max(1, self.width())
        columns = max(1, min(self._max_columns, available // self._min_item_width))
        if columns == self._columns and self.grid.count() == len(self._items):
            return

        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        self._columns = columns
        for index, widget in enumerate(self._items):
            row = index // columns
            col = index % columns
            self.grid.addWidget(widget, row, col)
        for col in range(columns):
            self.grid.setColumnStretch(col, 1)
