from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QDoubleSpinBox, QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from api.client import api_client, user_id_to_account_number
from ui.async_utils import run_async
from ui.responsive import configure_table

ROLE_LABELS = {"CLIENT": "Клиент", "BANKER": "Оператор", "ADMIN": "Администратор"}


def _mask_account(number: str) -> str:
    if len(number) < 8:
        return number
    return number[:4] + "••••••••••" + number[-4:]


def _rub(kopecks: int | float | None) -> str:
    return f"₽ {(kopecks or 0) / 100:,.2f}"


def _fmt_dt(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso[:16]


class EditLimitsDialog(QDialog):
    def __init__(self, user: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Изменить лимиты — {user.get('full_name', '')}")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        self.daily_spin = QDoubleSpinBox()
        self.daily_spin.setRange(0, 1_000_000_000)
        self.daily_spin.setDecimals(2)
        self.daily_spin.setSingleStep(1000)
        self.daily_spin.setPrefix("₽ ")
        self.daily_spin.setValue((user.get("daily_limit") or 0) / 100)
        self.daily_spin.setMinimumHeight(38)

        self.monthly_spin = QDoubleSpinBox()
        self.monthly_spin.setRange(0, 1_000_000_000)
        self.monthly_spin.setDecimals(2)
        self.monthly_spin.setSingleStep(10000)
        self.monthly_spin.setPrefix("₽ ")
        self.monthly_spin.setValue((user.get("monthly_limit") or 0) / 100)
        self.monthly_spin.setMinimumHeight(38)

        form.addRow("Дневной лимит:", self.daily_spin)
        form.addRow("Месячный лимит:", self.monthly_spin)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def daily_kopecks(self) -> int:
        return int(round(self.daily_spin.value() * 100))

    def monthly_kopecks(self) -> int:
        return int(round(self.monthly_spin.value() * 100))


class CreateUserDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Новый пользователь")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("user@test.ru")
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("Пароль")
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("ФИО")
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("+79990000000")

        self.role_combo = QComboBox()
        for key, label in ROLE_LABELS.items():
            self.role_combo.addItem(label, key)

        self.balance_spin = QDoubleSpinBox()
        self.balance_spin.setRange(0, 1_000_000_000)
        self.balance_spin.setDecimals(2)
        self.balance_spin.setSingleStep(1000)
        self.balance_spin.setPrefix("₽ ")

        form.addRow("Email *", self.email_edit)
        form.addRow("Пароль *", self.password_edit)
        form.addRow("ФИО *", self.name_edit)
        form.addRow("Телефон", self.phone_edit)
        form.addRow("Роль *", self.role_combo)
        form.addRow("Баланс", self.balance_spin)
        layout.addLayout(form)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self._validate_and_accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def payload(self) -> dict:
        payload = {
            "email": self.email_edit.text().strip(),
            "password": self.password_edit.text(),
            "full_name": self.name_edit.text().strip(),
            "role": self.role_combo.currentData(),
            "balance": int(round(self.balance_spin.value() * 100)),
        }
        phone = self.phone_edit.text().strip()
        if phone:
            payload["phone"] = phone
        return payload

    def _validate_and_accept(self):
        if not self.email_edit.text().strip():
            QMessageBox.warning(self, "Проверка", "Укажите email.")
            return
        if not self.password_edit.text():
            QMessageBox.warning(self, "Проверка", "Укажите пароль.")
            return
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Проверка", "Укажите ФИО.")
            return
        self.accept()


class AdminUsers(QWidget):
    def __init__(self):
        super().__init__()
        self._users = []
        self._load_worker = None
        self._action_worker = None
        self._load_seq = 0
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(350)
        self._search_timer.timeout.connect(self._load_data)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        hdr = QHBoxLayout()
        self.count_label = QLabel("Пользователи")
        self.count_label.setObjectName("sectionTitle")

        create_btn = QPushButton("Создать")
        create_btn.setObjectName("exportButton")
        create_btn.setMinimumHeight(38)
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.clicked.connect(self._create_user)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.setObjectName("filterButton")
        refresh_btn.setMinimumHeight(38)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.clicked.connect(self._load_data)

        hdr.addWidget(self.count_label)
        hdr.addStretch()
        hdr.addWidget(create_btn)
        hdr.addWidget(refresh_btn)
        layout.addLayout(hdr)

        filters = QFrame()
        filters.setObjectName("sectionCard")
        filters_layout = QHBoxLayout(filters)
        filters_layout.setContentsMargins(20, 16, 20, 16)
        filters_layout.setSpacing(12)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск по ID, ФИО, email или телефону")
        self.search_edit.setMinimumHeight(38)
        self.search_edit.returnPressed.connect(self._load_data)
        self.search_edit.textChanged.connect(lambda _: self._schedule_load())

        self.role_filter = QComboBox()
        self.role_filter.setMinimumHeight(38)
        self.role_filter.addItem("Все роли", "")
        for key, label in ROLE_LABELS.items():
            self.role_filter.addItem(label, key)
        self.role_filter.currentIndexChanged.connect(lambda _: self._schedule_load())

        filters_layout.addWidget(self.search_edit, stretch=1)
        filters_layout.addWidget(self.role_filter)
        layout.addWidget(filters)

        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Счёт", "ФИО", "Email", "Роль", "Баланс", "Лимит/день", "Статус", "История", "Лимиты", "Действия"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        configure_table(self.table, stretch_columns=(2, 3), min_height=300)
        card_layout.addWidget(self.table)

        layout.addWidget(card)

    def _load_data(self):
        self._load_seq += 1
        seq = self._load_seq
        q = self.search_edit.text().strip()
        role = self.role_filter.currentData() or ""
        self.count_label.setText("Пользователи (загрузка...)")
        self._load_worker = run_async(
            lambda: api_client.get_admin_users(q=q, role=role),
            on_success=lambda users, s=seq: self._on_users_loaded(s, users),
            on_error=lambda msg, s=seq: self._on_load_error(s, msg),
            on_finished=lambda: setattr(self, "_load_worker", None),
        )

    def _schedule_load(self):
        self._search_timer.start()

    def _on_users_loaded(self, seq: int, users: list):
        if seq != self._load_seq:
            return
        self._users = users
        self._render()

    def _on_load_error(self, seq: int, msg: str):
        if seq != self._load_seq:
            return
        QMessageBox.critical(self, "Ошибка", msg)

    def _render(self):
        self.count_label.setText(f"Пользователи ({len(self._users)})")
        self.table.setRowCount(len(self._users))

        for row, u in enumerate(self._users):
            is_blocked = u.get("is_blocked", False)
            role_raw = u.get("role", "")
            user_id = u.get("id", "")

            raw_account = user_id_to_account_number(user_id) if user_id != "" else "—"
            items = [
                QTableWidgetItem(str(user_id)),
                QTableWidgetItem(_mask_account(raw_account)),
                QTableWidgetItem(u.get("full_name", "—")),
                QTableWidgetItem(u.get("email", "—")),
                QTableWidgetItem(ROLE_LABELS.get(role_raw, role_raw or "—")),
                QTableWidgetItem(_rub(u.get("balance", 0))),
                QTableWidgetItem(_rub(u.get("daily_limit", 0))),
                QTableWidgetItem("Заблокирован" if is_blocked else "Активен"),
            ]
            items[5].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[6].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[7].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if is_blocked:
                items[7].setForeground(QColor("#EF4444"))

            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, col, item)

            hist_btn = QPushButton("Открыть")
            hist_btn.setEnabled(role_raw in {"CLIENT", "BANKER"})
            hist_btn.setStyleSheet(
                "QPushButton { border: 1px solid #E2E8F0; border-radius: 6px; "
                "padding: 4px 10px; font-size: 12px; color: #3B82F6; background: #EFF6FF; }"
                "QPushButton:hover { background: #DBEAFE; }"
                "QPushButton:disabled { color: #94A3B8; background: #F8FAFC; }"
            )
            hist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            hist_btn.clicked.connect(lambda _, uid=user_id, role=role_raw: self._show_history(uid, role))
            self.table.setCellWidget(row, 8, hist_btn)

            limits_btn = QPushButton("Изменить")
            limits_btn.setStyleSheet(
                "QPushButton { border: 1px solid #E2E8F0; border-radius: 6px; "
                "padding: 4px 10px; font-size: 12px; color: #8B5CF6; background: #F5F3FF; }"
                "QPushButton:hover { background: #EDE9FE; }"
            )
            limits_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            limits_btn.clicked.connect(lambda _, user=u: self._edit_limits(user))
            self.table.setCellWidget(row, 9, limits_btn)

            action_btn = QPushButton("Разблокировать" if is_blocked else "Заблокировать")
            action_btn.setStyleSheet(
                "QPushButton { border-radius: 6px; padding: 4px 10px; font-size: 12px; "
                + ("color: #10B981; background: #DCFCE7; border: 1px solid #10B98144; }"
                   "QPushButton:hover { background: #BBF7D0; }"
                   if is_blocked else
                   "color: #EF4444; background: #FEE2E2; border: 1px solid #EF444444; }"
                   "QPushButton:hover { background: #FECACA; }")
            )
            action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            action_btn.clicked.connect(
                lambda _, uid=user_id, blocked=is_blocked: self._toggle_block(uid, blocked)
            )
            self.table.setCellWidget(row, 10, action_btn)
            self.table.setRowHeight(row, 48)

        for col in [0, 1, 4, 6, 7, 8, 9, 10]:
            self.table.resizeColumnToContents(col)

    def _create_user(self):
        dlg = CreateUserDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            payload = dlg.payload()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
            return
        self._action_worker = run_async(
            lambda: api_client.create_admin_user(payload),
            on_success=lambda _: (QMessageBox.information(self, "Готово", "Пользователь создан."), self._load_data()),
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_action_worker", None),
        )

    def _toggle_block(self, user_id: int, is_blocked: bool):
        action = "разблокировать" if is_blocked else "заблокировать"
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Вы уверены, что хотите {action} пользователя #{user_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        action_fn = api_client.unblock_user if is_blocked else api_client.block_user
        self._action_worker = run_async(
            lambda: action_fn(user_id),
            on_success=lambda _: self._load_data(),
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_action_worker", None),
        )

    def _edit_limits(self, user: dict):
        dlg = EditLimitsDialog(user, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        user_id = user.get("id")
        daily = dlg.daily_kopecks()
        monthly = dlg.monthly_kopecks()
        self._action_worker = run_async(
            lambda: api_client.update_user_limits(user_id, daily, monthly),
            on_success=lambda _: (
                QMessageBox.information(self, "Готово", "Лимиты обновлены."),
                self._load_data(),
            ),
            on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
            on_finished=lambda: setattr(self, "_action_worker", None),
        )

    def _show_history(self, user_id: int, role: str):
        if role == "CLIENT":
            self._action_worker = run_async(
                lambda: api_client.get_admin_client_history(user_id),
                on_success=lambda data: self._show_client_history(data, user_id),
                on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
                on_finished=lambda: setattr(self, "_action_worker", None),
            )
        elif role == "BANKER":
            self._action_worker = run_async(
                lambda: api_client.get_admin_banker_history(user_id),
                on_success=lambda payments: self._show_banker_history(payments, user_id),
                on_error=lambda msg: QMessageBox.critical(self, "Ошибка", msg),
                on_finished=lambda: setattr(self, "_action_worker", None),
            )

    def _show_banker_history(self, payments: list, banker_id: int):
        banker = next((u for u in self._users if u.get("id") == banker_id), {})
        name = banker.get("full_name") or f"оператор #{banker_id}"
        user_map = {u["id"]: u.get("full_name", f"ID {u['id']}") for u in self._users if u.get("id")}
        dlg = QDialog(self)
        dlg.setWindowTitle(f"История оператора — {name}")
        dlg.resize(960, 560)
        layout = QVBoxLayout(dlg)
        layout.addWidget(self._payments_table(payments, user_map))
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    def _show_client_history(self, data: dict, client_id: int):
        profile = data.get("profile", {})
        user = profile.get("user", {})
        stats = profile.get("stats", {})
        payments = profile.get("payments", [])
        audit = data.get("audit", [])

        name = user.get("full_name") or f"клиент #{client_id}"
        user_map = {u["id"]: u.get("full_name", f"ID {u['id']}") for u in self._users if u.get("id")}

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Профиль клиента — {name}")
        dlg.resize(940, 620)
        layout = QVBoxLayout(dlg)

        tabs = QTabWidget()
        tabs.addTab(self._client_profile_tab(user, stats), "Профиль")
        tabs.addTab(self._payments_table(payments, user_map), "Платежи")
        tabs.addTab(self._audit_table(audit), "Аудит")
        layout.addWidget(tabs)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(dlg.reject)
        layout.addWidget(btns)
        dlg.exec()

    def _client_profile_tab(self, user: dict, stats: dict) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        user_id = user.get("id", "")
        lines = [
            ("ID", user_id or "—"),
            ("Счёт", user_id_to_account_number(user_id) if user_id != "" else "—"),
            ("ФИО", user.get("full_name", "—")),
            ("Email", user.get("email", "—")),
            ("Телефон", user.get("phone") or "—"),
            ("Баланс", _rub(user.get("balance", 0))),
            ("Дневной лимит", _rub(user.get("daily_limit", 0))),
            ("Месячный лимит", _rub(user.get("monthly_limit", 0))),
            ("Отправлено платежей", stats.get("sent_count", 0)),
            ("Получено платежей", stats.get("received_count", 0)),
            ("Сумма отправленных", _rub(stats.get("sent_amount", 0))),
            ("Сумма полученных", _rub(stats.get("received_amount", 0))),
            ("В ожидании", stats.get("pending_payments", 0)),
            ("Одобрено", stats.get("approved_payments", 0)),
            ("Отклонено", stats.get("rejected_payments", 0)),
        ]
        for label, value in lines:
            layout.addWidget(self._info_row(label, str(value)))
        layout.addStretch()
        return tab

    def _payments_table(self, payments: list, user_map: dict | None = None) -> QTableWidget:
        from api.client import PAYMENT_STATUS_RU
        from PyQt6.QtGui import QColor
        umap = user_map or {}

        def name(uid):
            if uid is None:
                return "—"
            return umap.get(uid, f"ID {uid}")

        def fraud_color(score):
            if score >= 70:
                return "#EF4444"
            if score >= 40:
                return "#F59E0B"
            return "#10B981"

        tbl = QTableWidget()
        tbl.setColumnCount(8)
        tbl.setHorizontalHeaderLabels(
            ["ID", "Дата", "Отправитель", "Получатель", "Сумма", "Статус", "Риск-балл", "Обработан"]
        )
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        configure_table(tbl, stretch_columns=(2, 3), min_height=320)
        tbl.setRowCount(len(payments))
        for row, p in enumerate(payments):
            fraud = p.get("fraud_score") or 0
            status_raw = p.get("status", "")
            items = [
                QTableWidgetItem(str(p.get("id", ""))),
                QTableWidgetItem(_fmt_dt(p.get("created_at"))),
                QTableWidgetItem(name(p.get("sender_id"))),
                QTableWidgetItem(name(p.get("recipient_id"))),
                QTableWidgetItem(_rub(p.get("amount", 0))),
                QTableWidgetItem(PAYMENT_STATUS_RU.get(status_raw, status_raw or "—")),
                QTableWidgetItem(str(fraud)),
                QTableWidgetItem(_fmt_dt(p.get("processed_at"))),
            ]
            items[4].setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            items[6].setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            items[6].setForeground(QColor(fraud_color(fraud)))
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(row, col, item)
            tbl.setRowHeight(row, 42)
        for col in [0, 4, 5, 6, 7]:
            tbl.resizeColumnToContents(col)
        return tbl

    def _audit_table(self, audit: list) -> QTableWidget:
        tbl = QTableWidget()
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels(["ID", "Действие", "Объект", "Детали", "Дата"])
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        tbl.verticalHeader().setVisible(False)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        tbl.setShowGrid(False)
        configure_table(tbl, stretch_columns=(3,), min_height=320)
        tbl.setRowCount(len(audit))
        for row, e in enumerate(audit):
            items = [
                QTableWidgetItem(str(e.get("id", ""))),
                QTableWidgetItem(e.get("action", "—")),
                QTableWidgetItem(f"{e.get('entity_type', '—')} #{e.get('entity_id', '—')}"),
                QTableWidgetItem(e.get("details", "—")),
                QTableWidgetItem(_fmt_dt(e.get("created_at"))),
            ]
            for col, item in enumerate(items):
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                tbl.setItem(row, col, item)
            tbl.setRowHeight(row, 42)
        for col in [0, 1, 2, 4]:
            tbl.resizeColumnToContents(col)
        return tbl

    def _info_row(self, label: str, value: str) -> QWidget:
        row_w = QWidget()
        row_l = QHBoxLayout(row_w)
        row_l.setContentsMargins(0, 2, 0, 2)
        lbl = QLabel(f"<b>{label}:</b>")
        lbl.setFixedWidth(180)
        val = QLabel(value)
        val.setWordWrap(True)
        row_l.addWidget(lbl)
        row_l.addWidget(val, stretch=1)
        return row_w
