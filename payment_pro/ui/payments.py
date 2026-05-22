from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QTextEdit, QScrollArea,
    QMessageBox, QSizePolicy,
)
from PyQt6.QtCore import Qt
from api.client import api_client


class Payments(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load_accounts()

    def _build_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        # Form card
        card = QFrame()
        card.setObjectName("sectionCard")
        card.setMaximumWidth(700)
        form = QVBoxLayout(card)
        form.setContentsMargins(28, 24, 28, 24)
        form.setSpacing(16)

        title = QLabel("Платёжное поручение")
        title.setObjectName("sectionTitle")
        form.addWidget(title)

        subtitle = QLabel("Заполните все обязательные поля для создания платежа")
        subtitle.setStyleSheet("color: #94A3B8; font-size: 13px;")
        form.addWidget(subtitle)

        form.addSpacing(4)

        # Sender account
        form.addWidget(self._field_label("Счёт отправителя *"))
        self.sender_combo = QComboBox()
        self.sender_combo.setMinimumHeight(44)
        form.addWidget(self.sender_combo)
        self.sender_error = self._error_label()
        form.addWidget(self.sender_error)

        # Recipient account
        form.addWidget(self._field_label("Счёт получателя *"))
        self.recipient_edit = QLineEdit()
        self.recipient_edit.setPlaceholderText("40702810000000001234")
        self.recipient_edit.setMinimumHeight(44)
        form.addWidget(self.recipient_edit)
        self.recipient_error = self._error_label()
        form.addWidget(self.recipient_error)

        # BIK
        form.addWidget(self._field_label("БИК банка получателя *"))
        self.bik_edit = QLineEdit()
        self.bik_edit.setPlaceholderText("044525225")
        self.bik_edit.setMinimumHeight(44)
        form.addWidget(self.bik_edit)
        self.bik_error = self._error_label()
        form.addWidget(self.bik_error)

        # Amount
        form.addWidget(self._field_label("Сумма (₽) *"))
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setMinimumHeight(44)
        form.addWidget(self.amount_edit)
        self.amount_error = self._error_label()
        form.addWidget(self.amount_error)

        # Purpose
        form.addWidget(self._field_label("Назначение платежа *"))
        self.purpose_edit = QTextEdit()
        self.purpose_edit.setPlaceholderText("Оплата по договору №...")
        self.purpose_edit.setMaximumHeight(90)
        form.addWidget(self.purpose_edit)
        self.purpose_error = self._error_label()
        form.addWidget(self.purpose_error)

        form.addSpacing(8)

        btn_row = QHBoxLayout()
        self.submit_btn = QPushButton("Отправить платёж")
        self.submit_btn.setObjectName("submitButton")
        self.submit_btn.setMinimumHeight(48)
        self.submit_btn.setMinimumWidth(200)
        self.submit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.submit_btn.clicked.connect(self._on_submit)

        clear_btn = QPushButton("Очистить")
        clear_btn.setStyleSheet(
            "QPushButton { border: 1.5px solid #E2E8F0; border-radius: 10px; "
            "padding: 13px 24px; font-size: 14px; font-weight: 600; color: #64748B; "
            "background: #FFFFFF; }"
            "QPushButton:hover { background: #F8FAFC; }"
        )
        clear_btn.setMinimumHeight(48)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_form)

        btn_row.addWidget(self.submit_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        form.addLayout(btn_row)

        layout.addWidget(card)
        layout.addStretch()

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("fieldLabel")
        return lbl

    def _error_label(self) -> QLabel:
        lbl = QLabel("")
        lbl.setObjectName("errorLabel")
        lbl.setVisible(False)
        return lbl

    def _load_accounts(self):
        try:
            accounts = api_client.get_accounts()
        except Exception as e:
            self.sender_combo.addItem(str(e))
            return
        for acc in accounts:
            self.sender_combo.addItem(
                f"{acc['name']} — {acc['number'][-4:]} ({acc['currency']})",
                userData=acc["id"],
            )

    def _show_field_error(self, widget, error_label, msg: str):
        widget.setStyleSheet(
            "border: 1.5px solid #EF4444; border-radius: 8px; "
            "padding: 10px 14px; font-size: 14px; background: #FFF;"
        )
        error_label.setText(msg)
        error_label.setVisible(True)

    def _clear_field_error(self, widget, error_label):
        widget.setStyleSheet("")
        error_label.setVisible(False)

    def _validate(self) -> bool:
        valid = True

        recipient = self.recipient_edit.text().strip()
        if len(recipient) != 20 or not recipient.isdigit():
            self._show_field_error(self.recipient_edit, self.recipient_error,
                                   "Номер счёта должен содержать 20 цифр")
            valid = False
        else:
            self._clear_field_error(self.recipient_edit, self.recipient_error)

        bik = self.bik_edit.text().strip()
        if len(bik) != 9 or not bik.isdigit():
            self._show_field_error(self.bik_edit, self.bik_error,
                                   "БИК должен содержать 9 цифр")
            valid = False
        else:
            self._clear_field_error(self.bik_edit, self.bik_error)

        amount_str = self.amount_edit.text().strip().replace(",", ".")
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
            self._clear_field_error(self.amount_edit, self.amount_error)
        except ValueError:
            self._show_field_error(self.amount_edit, self.amount_error,
                                   "Введите корректную сумму (больше 0)")
            valid = False

        purpose = self.purpose_edit.toPlainText().strip()
        if len(purpose) < 5:
            self.purpose_edit.setStyleSheet(
                "border: 1.5px solid #EF4444; border-radius: 8px; "
                "padding: 10px 14px; font-size: 14px; background: #FFF;"
            )
            self.purpose_error.setText("Укажите назначение платежа (минимум 5 символов)")
            self.purpose_error.setVisible(True)
            valid = False
        else:
            self.purpose_edit.setStyleSheet("")
            self.purpose_error.setVisible(False)

        return valid

    def _on_submit(self):
        if not self._validate():
            return

        payload = {
            "sender_account": self.sender_combo.currentData(),
            "recipient_account": self.recipient_edit.text().strip(),
            "bik": self.bik_edit.text().strip(),
            "amount": float(self.amount_edit.text().strip().replace(",", ".")),
            "purpose": self.purpose_edit.toPlainText().strip(),
        }

        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("Отправка...")
        try:
            result = api_client.send_payment(payload)
            QMessageBox.information(
                self, "Платёж отправлен",
                f"Платёж принят в обработку.\nИдентификатор: {result.get('id', 'N/A')}",
            )
            self._clear_form()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось отправить платёж:\n{e}")
        finally:
            self.submit_btn.setEnabled(True)
            self.submit_btn.setText("Отправить платёж")

    def _clear_form(self):
        self.recipient_edit.clear()
        self.bik_edit.clear()
        self.amount_edit.clear()
        self.purpose_edit.clear()
        for widget, err in [
            (self.recipient_edit, self.recipient_error),
            (self.bik_edit, self.bik_error),
            (self.amount_edit, self.amount_error),
        ]:
            self._clear_field_error(widget, err)
        self.purpose_edit.setStyleSheet("")
        self.purpose_error.setVisible(False)
