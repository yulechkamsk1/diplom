from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGridLayout,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QWidget,
)


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
    for col in range(table.columnCount()):
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
    for col in stretch_columns:
        header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)


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
