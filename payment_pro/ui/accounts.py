from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QScrollArea, QSizePolicy, QPushButton,
)
from PyQt6.QtCore import Qt
from api.client import api_client


CURRENCY_ICONS = {"RUB": "₽", "USD": "$", "EUR": "€"}
CARD_COLORS = ["#3B82F6", "#10B981", "#8B5CF6", "#F59E0B"]


class AccountCard(QFrame):
    def __init__(self, account: dict, color: str):
        super().__init__()
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
        for label in ["Пополнить", "Перевести", "Реквизиты"]:
            btn = QPushButton(label)
            btn.setStyleSheet(
                f"QPushButton {{ border: 1px solid {color}44; border-radius: 6px; "
                f"padding: 5px 12px; font-size: 12px; color: {color}; background: {color}11; }}"
                f"QPushButton:hover {{ background: {color}22; }}"
            )
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)


class Accounts(QWidget):
    def __init__(self):
        super().__init__()
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
        summary_layout.addWidget(add_btn)

        self.layout_.addWidget(summary_frame)

        self.cards_layout = QVBoxLayout()
        self.cards_layout.setSpacing(16)
        self.layout_.addLayout(self.cards_layout)
        self.layout_.addStretch()

    def _load_data(self):
        accounts = api_client.get_accounts()
        total_rub = sum(a["balance"] for a in accounts if a["currency"] == "RUB")
        self.summary_label.setText(
            f"{len(accounts)} счёта   |   Общий баланс (RUB): ₽ {total_rub:,.2f}"
        )

        # Clear existing cards
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Two-column grid using rows of HBoxLayout
        accounts_iter = iter(accounts)
        color_idx = 0
        for pair in zip(accounts_iter, accounts_iter):
            row = QHBoxLayout()
            row.setSpacing(16)
            for acc in pair:
                card = AccountCard(acc, CARD_COLORS[color_idx % len(CARD_COLORS)])
                row.addWidget(card)
                color_idx += 1
            self.cards_layout.addLayout(row)

        # Odd one out
        remaining = list(accounts_iter)
        if remaining:
            row = QHBoxLayout()
            row.setSpacing(16)
            card = AccountCard(remaining[0], CARD_COLORS[color_idx % len(CARD_COLORS)])
            row.addWidget(card)
            row.addStretch()
            self.cards_layout.addLayout(row)
