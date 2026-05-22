from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy, QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt
from api.client import api_client
from ui.async_utils import run_async
from ui.responsive import ResponsiveGrid


CURRENCY_ICONS = {"RUB": "₽", "USD": "$", "EUR": "€"}
CARD_COLORS = ["#3B82F6", "#10B981", "#8B5CF6", "#F59E0B"]


class AccountCard(QFrame):
    def __init__(self, account: dict, color: str):
        super().__init__()
        self._account = account
        self.setObjectName("accountCard")
        self.setMinimumHeight(160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        # Top row: icon + name
        top_row = QHBoxLayout()
        icon_box = QLabel(CURRENCY_ICONS.get(account["currency"], account["currency"]))
        icon_box.setFixedSize(44, 44)
        icon_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_box.setStyleSheet(
            f"background: {color}22; border-radius: 10px; "
            f"color: {color}; font-size: 22px;"
        )

        name_col = QVBoxLayout()
        name_lbl = QLabel(account["name"])
        name_lbl.setObjectName("accountName")
        number_lbl = QLabel(f"•••• •••• {account['number'][-4:]}")
        number_lbl.setObjectName("accountNumber")
        name_col.addWidget(name_lbl)
        name_col.addWidget(number_lbl)

        top_row.addWidget(icon_box)
        top_row.addLayout(name_col)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Balance
        balance_row = QHBoxLayout()
        balance_lbl = QLabel(f"{account['currency']} {account['balance']:,.2f}")
        balance_lbl.setObjectName("accountBalance")
        balance_lbl.setStyleSheet(f"color: {color};")
        currency_lbl = QLabel(account["currency"])
        currency_lbl.setObjectName("accountCurrency")
        balance_row.addWidget(balance_lbl)
        balance_row.addStretch()
        balance_row.addWidget(currency_lbl)
        layout.addLayout(balance_row)

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet("color: #E2E8F0;")
        layout.addWidget(divider)

        # Actions
        btn_row = QHBoxLayout()
        actions = [
            ("Пополнить", self._on_deposit),
            ("Перевести",  self._on_transfer),
            ("Реквизиты",  self._on_details),
        ]
        for label, handler in actions:
            btn = QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton {{ border: 1px solid {color}44; border-radius: 6px; "
                f"padding: 5px 12px; font-size: 12px; color: {color}; background: {color}11; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(handler)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)


    def _on_deposit(self):
        QMessageBox.information(
            self, "Пополнение счёта",
            f"Для пополнения счёта {self._account['number']}\n"
            "обратитесь в отделение банка или используйте интернет-банк.",
        )

    def _on_transfer(self):
        QMessageBox.information(
            self, "Перевод",
            f"Счёт отправителя: {self._account['number']}\n\n"
            "Для создания перевода воспользуйтесь разделом «Платежи».",
        )

    def _on_details(self):
        acc = self._account
        QMessageBox.information(
            self, "Реквизиты счёта",
            f"Наименование: {acc['name']}\n"
            f"Номер счёта: {acc['number']}\n"
            f"Валюта: {acc['currency']}\n"
            f"Баланс: {acc['currency']} {acc['balance']:,.2f}",
        )


class Accounts(QWidget):
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
        self.layout_.setSpacing(16)

        summary_frame = QFrame()
        summary_frame.setObjectName("sectionCard")
        summary_layout = QHBoxLayout(summary_frame)
        summary_layout.setContentsMargins(20, 16, 20, 16)

        self.summary_label = QLabel("Загрузка счетов...")
        self.summary_label.setObjectName("sectionTitle")
        summary_layout.addWidget(self.summary_label)
        summary_layout.addStretch()

        add_btn = QPushButton("+ Открыть счёт")
        add_btn.setObjectName("submitButton")
        add_btn.setMinimumHeight(38)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self._on_open_account)
        summary_layout.addWidget(add_btn)

        self.layout_.addWidget(summary_frame)

        self.cards_grid = ResponsiveGrid(min_item_width=320, max_columns=2)
        self.layout_.addWidget(self.cards_grid)
        self.layout_.addStretch()

    def _on_open_account(self):
        QMessageBox.information(
            self, "Открытие счёта",
            "Для открытия нового счёта обратитесь в отделение банка\n"
            "или свяжитесь с вашим персональным менеджером.",
        )

    def _load_data(self):
        self.summary_label.setText("Загрузка счетов...")
        self._load_worker = run_async(
            api_client.get_accounts,
            on_success=self._render_accounts,
            on_error=self._show_error,
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _show_error(self, msg: str):
        self.summary_label.setText(msg)
        self.summary_label.setStyleSheet("color: #EF4444;")

    def _render_accounts(self, accounts: list):
        self.summary_label.setStyleSheet("")
        total_rub = sum(a["balance"] for a in accounts if a["currency"] == "RUB")
        self.summary_label.setText(
            f"{len(accounts)} счёта   |   Общий баланс (RUB): ₽ {total_rub:,.2f}"
        )

        # Clear existing cards
        self.cards_grid.clear()
        color_idx = 0
        for acc in accounts:
            card = AccountCard(acc, CARD_COLORS[color_idx % len(CARD_COLORS)])
            self.cards_grid.add_card(card)
            color_idx += 1
