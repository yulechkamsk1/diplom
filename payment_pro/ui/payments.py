import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QComboBox, QTextEdit, QScrollArea,
    QMessageBox, QSizePolicy, QTabWidget,
)

from api.client import ACCOUNT_PREFIX, account_number_to_user_id, api_client
from ui.async_utils import run_async

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

PAYMENT_STATUS_LABELS = {
    "PENDING": "ожидает проверки банкиром",
    "APPROVED": "одобрен, ожидает завершения",
    "COMPLETED": "завершён",
    "REJECTED": "отклонён",
    "CANCELLED": "отменён",
}


class Payments(QWidget):
    def __init__(self):
        super().__init__()
        self._load_worker = None
        self._submit_worker = None
        self._submitted_mode = None
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

        card = QFrame()
        card.setObjectName("sectionCard")
        card.setMaximumWidth(820)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        form = QVBoxLayout(card)
        form.setContentsMargins(28, 24, 28, 24)
        form.setSpacing(16)

        title = QLabel("Платежи и переводы")
        title.setObjectName("sectionTitle")
        form.addWidget(title)

        subtitle = QLabel(
            "«По счёту» — банковский платёж по 20-значному номеру счёта.   "
            "«По email» — быстрый перевод клиенту внутри системы."
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        subtitle.setWordWrap(True)
        form.addWidget(subtitle)

        form.addSpacing(4)
        form.addWidget(self._field_label("Счёт отправителя *"))
        self.sender_combo = QComboBox()
        self.sender_combo.setMinimumHeight(44)
        form.addWidget(self.sender_combo)
        self.sender_error = self._error_label()
        form.addWidget(self.sender_error)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabBar::tab { min-width: 140px; padding: 8px 20px; font-size: 13px; font-weight: 600; }"
            "QTabBar::tab:selected { color: #3B82F6; border-bottom: 2px solid #3B82F6; }"
        )
        self.tabs.addTab(self._build_account_tab(), "По счёту (банковский)")
        self.tabs.addTab(self._build_email_tab(), "По email (перевод клиенту)")
        form.addWidget(self.tabs)

        layout.addWidget(card)
        layout.addStretch()

    def _build_account_tab(self) -> QWidget:
        tab = QWidget()
        form = QVBoxLayout(tab)
        form.setContentsMargins(0, 16, 0, 0)
        form.setSpacing(14)

        form.addWidget(self._field_label("Счёт получателя *"))
        self.recipient_edit = QLineEdit()
        self.recipient_edit.setPlaceholderText("40702810000000001234")
        self.recipient_edit.setMinimumHeight(44)
        form.addWidget(self.recipient_edit)
        self.recipient_error = self._error_label()
        form.addWidget(self.recipient_error)

        form.addWidget(self._field_label("БИК банка получателя *"))
        self.bik_edit = QLineEdit()
        self.bik_edit.setPlaceholderText("044525225")
        self.bik_edit.setMinimumHeight(44)
        form.addWidget(self.bik_edit)
        self.bik_error = self._error_label()
        form.addWidget(self.bik_error)

        form.addWidget(self._field_label("Сумма (₽) *"))
        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("0.00")
        self.amount_edit.setMinimumHeight(44)
        form.addWidget(self.amount_edit)
        self.amount_error = self._error_label()
        form.addWidget(self.amount_error)

        form.addWidget(self._field_label("Назначение платежа *"))
        self.purpose_edit = QTextEdit()
        self.purpose_edit.setPlaceholderText("Оплата по договору №...")
        self.purpose_edit.setMaximumHeight(90)
        form.addWidget(self.purpose_edit)
        self.purpose_error = self._error_label()
        form.addWidget(self.purpose_error)

        btn_row = QHBoxLayout()
        self.account_submit_btn = QPushButton("Отправить платёж")
        self._configure_submit_button(self.account_submit_btn)
        self.account_submit_btn.clicked.connect(self._on_account_submit)

        self.account_clear_btn = self._secondary_button("Очистить")
        self.account_clear_btn.clicked.connect(self._clear_account_form)

        btn_row.addWidget(self.account_submit_btn)
        btn_row.addWidget(self.account_clear_btn)
        btn_row.addStretch()
        form.addSpacing(8)
        form.addLayout(btn_row)
        return tab

    def _build_email_tab(self) -> QWidget:
        tab = QWidget()
        form = QVBoxLayout(tab)
        form.setContentsMargins(0, 16, 0, 0)
        form.setSpacing(14)

        form.addWidget(self._field_label("Email получателя *"))
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("client@test.ru")
        self.email_edit.setMinimumHeight(44)
        form.addWidget(self.email_edit)
        self.email_error = self._error_label()
        form.addWidget(self.email_error)

        form.addWidget(self._field_label("Сумма (₽) *"))
        self.email_amount_edit = QLineEdit()
        self.email_amount_edit.setPlaceholderText("0.00")
        self.email_amount_edit.setMinimumHeight(44)
        form.addWidget(self.email_amount_edit)
        self.email_amount_error = self._error_label()
        form.addWidget(self.email_amount_error)

        form.addWidget(self._field_label("Назначение перевода *"))
        self.email_purpose_edit = QTextEdit()
        self.email_purpose_edit.setPlaceholderText("Перевод клиенту")
        self.email_purpose_edit.setMaximumHeight(90)
        form.addWidget(self.email_purpose_edit)
        self.email_purpose_error = self._error_label()
        form.addWidget(self.email_purpose_error)

        btn_row = QHBoxLayout()
        self.email_submit_btn = QPushButton("Перевести")
        self._configure_submit_button(self.email_submit_btn)
        self.email_submit_btn.clicked.connect(self._on_email_submit)

        self.email_clear_btn = self._secondary_button("Очистить")
        self.email_clear_btn.clicked.connect(self._clear_email_form)

        btn_row.addWidget(self.email_submit_btn)
        btn_row.addWidget(self.email_clear_btn)
        btn_row.addStretch()
        form.addSpacing(8)
        form.addLayout(btn_row)
        return tab

    def switch_to_account_tab(self):
        self.tabs.setCurrentIndex(0)

    def switch_to_email_tab(self):
        self.tabs.setCurrentIndex(1)

    def _configure_submit_button(self, button: QPushButton):
        button.setObjectName("submitButton")
        button.setMinimumHeight(48)
        button.setMinimumWidth(170)
        button.setCursor(Qt.CursorShape.PointingHandCursor)

    def _secondary_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setStyleSheet(
            "QPushButton { border: 1.5px solid #E2E8F0; border-radius: 10px; "
            "padding: 13px 24px; font-size: 14px; font-weight: 600; color: #64748B; "
            "background: #FFFFFF; }"
            "QPushButton:hover { background: #F8FAFC; }"
        )
        button.setMinimumHeight(48)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

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
        self.sender_combo.clear()
        self.sender_combo.addItem("Загрузка счетов...")
        self._load_worker = run_async(
            api_client.get_accounts,
            on_success=self._on_accounts_loaded,
            on_error=self._on_accounts_error,
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _on_accounts_loaded(self, accounts: list):
        self.sender_combo.clear()
        for acc in accounts:
            self.sender_combo.addItem(
                f"{acc['name']} — {acc['number'][-4:]} ({acc['currency']})",
                userData=acc["id"],
            )

    def _on_accounts_error(self, msg: str):
        self.sender_combo.clear()
        self.sender_combo.addItem(msg)

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

    def _validate_sender(self) -> bool:
        if self.sender_combo.currentData() is None:
            self._show_field_error(
                self.sender_combo,
                self.sender_error,
                "Счёт отправителя ещё не загружен",
            )
            return False
        self._clear_field_error(self.sender_combo, self.sender_error)
        return True

    def _validate_amount(self, widget: QLineEdit, error_label: QLabel) -> bool:
        amount_str = widget.text().strip().replace(",", ".")
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
            self._clear_field_error(widget, error_label)
            return True
        except ValueError:
            self._show_field_error(widget, error_label, "Введите корректную сумму (больше 0)")
            return False

    def _validate_purpose(self, widget: QTextEdit, error_label: QLabel) -> bool:
        purpose = widget.toPlainText().strip()
        if len(purpose) < 5:
            widget.setStyleSheet(
                "border: 1.5px solid #EF4444; border-radius: 8px; "
                "padding: 10px 14px; font-size: 14px; background: #FFF;"
            )
            error_label.setText("Укажите назначение платежа (минимум 5 символов)")
            error_label.setVisible(True)
            return False
        widget.setStyleSheet("")
        error_label.setVisible(False)
        return True

    def _validate_account_form(self) -> bool:
        valid = self._validate_sender()

        recipient = self.recipient_edit.text().strip()
        if len(recipient) != 20 or not recipient.isdigit():
            self._show_field_error(
                self.recipient_edit,
                self.recipient_error,
                "Номер счёта должен содержать 20 цифр",
            )
            valid = False
        elif not recipient.startswith(ACCOUNT_PREFIX):
            self._show_field_error(
                self.recipient_edit,
                self.recipient_error,
                f"Номер счёта должен начинаться с {ACCOUNT_PREFIX}",
            )
            valid = False
        else:
            try:
                account_number_to_user_id(recipient)
                self._clear_field_error(self.recipient_edit, self.recipient_error)
            except ValueError as e:
                self._show_field_error(self.recipient_edit, self.recipient_error, str(e))
                valid = False

        bik = self.bik_edit.text().strip()
        if len(bik) != 9 or not bik.isdigit():
            self._show_field_error(self.bik_edit, self.bik_error, "БИК должен содержать 9 цифр")
            valid = False
        else:
            self._clear_field_error(self.bik_edit, self.bik_error)

        valid = self._validate_amount(self.amount_edit, self.amount_error) and valid
        valid = self._validate_purpose(self.purpose_edit, self.purpose_error) and valid
        return valid

    def _validate_email_form(self) -> bool:
        valid = self._validate_sender()

        email = self.email_edit.text().strip()
        if not EMAIL_RE.match(email):
            self._show_field_error(self.email_edit, self.email_error, "Введите корректный email")
            valid = False
        else:
            self._clear_field_error(self.email_edit, self.email_error)

        valid = self._validate_amount(self.email_amount_edit, self.email_amount_error) and valid
        valid = self._validate_purpose(self.email_purpose_edit, self.email_purpose_error) and valid
        return valid

    def _on_account_submit(self):
        if not self._validate_account_form():
            return

        payload = {
            "sender_account": self.sender_combo.currentData(),
            "recipient_account": self.recipient_edit.text().strip(),
            "bik": self.bik_edit.text().strip(),
            "amount": float(self.amount_edit.text().strip().replace(",", ".")),
            "purpose": self.purpose_edit.toPlainText().strip(),
        }
        self._start_submit(
            "account",
            self.account_submit_btn,
            "Отправка...",
            lambda: self._send_account_and_wait(payload),
        )

    def _on_email_submit(self):
        if not self._validate_email_form():
            return

        payload = {
            "sender_account": self.sender_combo.currentData(),
            "recipient_email": self.email_edit.text().strip().lower(),
            "amount": float(self.email_amount_edit.text().strip().replace(",", ".")),
            "purpose": self.email_purpose_edit.toPlainText().strip(),
        }
        self._start_submit(
            "email",
            self.email_submit_btn,
            "Перевод...",
            lambda: self._send_email_and_wait(payload),
        )

    def _start_submit(self, mode: str, button: QPushButton, loading_text: str, task):
        self._submitted_mode = mode
        self.account_submit_btn.setEnabled(False)
        self.email_submit_btn.setEnabled(False)
        self.account_clear_btn.setEnabled(False)
        self.email_clear_btn.setEnabled(False)
        button.setText(loading_text)
        self._submit_worker = run_async(
            task,
            on_success=self._on_payment_sent,
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", f"Не удалось отправить платёж:\n{msg}"),
            on_finished=self._on_submit_finished,
        )

    def _send_account_and_wait(self, payload: dict) -> dict:
        result = api_client.send_payment(payload)
        return self._wait_payment(result)

    def _send_email_and_wait(self, payload: dict) -> dict:
        result = api_client.send_payment_by_email(payload)
        return self._wait_payment(result)

    def _wait_payment(self, result: dict) -> dict:
        payment_id = result.get("id", "N/A")
        if payment_id != "N/A":
            result = api_client.wait_payment_status(payment_id)
        result["display_id"] = payment_id
        return result

    def _on_payment_sent(self, result: dict):
        payment_id = result.get("id", "N/A")
        payment_id = result.get("display_id", payment_id)
        status = result.get("status") or "N/A"
        status_label = PAYMENT_STATUS_LABELS.get(status, status)
        hint = (
            "\nПлатёж появится в очереди банкира."
            if status == "PENDING"
            else "\nПлатёж обработан автоматически, поэтому в очереди банкира его не будет."
        )
        QMessageBox.information(
            self,
            "Платёж отправлен",
            f"Платёж принят в обработку.\n"
            f"Идентификатор: {payment_id}\n"
            f"Статус: {status_label}"
            f"{hint}",
        )
        if self._submitted_mode == "email":
            self._clear_email_form()
        else:
            self._clear_account_form()

    def _on_submit_finished(self):
        self.account_submit_btn.setEnabled(True)
        self.email_submit_btn.setEnabled(True)
        self.account_clear_btn.setEnabled(True)
        self.email_clear_btn.setEnabled(True)
        self.account_submit_btn.setText("Отправить платёж")
        self.email_submit_btn.setText("Перевести")
        self._submit_worker = None
        self._submitted_mode = None

    def _clear_account_form(self):
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

    def _clear_email_form(self):
        self.email_edit.clear()
        self.email_amount_edit.clear()
        self.email_purpose_edit.clear()
        for widget, err in [
            (self.email_edit, self.email_error),
            (self.email_amount_edit, self.email_amount_error),
        ]:
            self._clear_field_error(widget, err)
        self.email_purpose_edit.setStyleSheet("")
        self.email_purpose_error.setVisible(False)
